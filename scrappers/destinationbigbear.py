import pandas as pd
import sys
import requests as rq
import re
import json
import multiprocessing as mp
import datetime as dt
import os
import psycopg2
import html
import logging
import time
from scrappers import util
from psycopg2.extras import execute_values
from datetime import datetime
from datetime import timedelta
from bs4 import BeautifulSoup
from splinter import Browser
from scrappers import settings
from selenium import webdriver

CABIN_URLS_FILE = './scrappers/dbb_cabin_urls.json'
DATABASE_URI = os.environ.get('DATABASE_URL', None) or os.getenv('DATABASE_URI')

db_id = 'DBB'

executable_path = {'executable_path': os.getenv('CHROME_DRIVER_EXECUTABLE_PATH')}

def load_cabins():
    cabins = []
    with open('./scrappers/dbb.json', encoding='utf8') as f:
        cabins = json.load(f)
    return cabins

def default_value(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e: 
            pass
    return wrapper

def read_csv_cabins(filename):
    # Extract cabins website from csv
    df = pd.read_csv(filename)
    return df.Link

def scrape_cabin_urls():
    base_url = 'https://www.destinationbigbear.com/'
    res = rq.get('https://www.destinationbigbear.com/AllCabinList.aspx')
    soup = BeautifulSoup(res.text, 'html.parser')
    urls = [base_url + a['href'] for a in soup('a', href=lambda href: 'Property_detail' in href if href else False)]
    with open(CABIN_URLS_FILE, 'w', encoding='utf8') as f:
        json.dump(urls, f, indent=2)

def select_cabins():
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    with connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, name from db.cabin WHERE cabin.idvrm='DBB'")
        cabins = cursor.fetchall()
    connection.close()
    return cabins

def scrape_rates_and_insert_faster():
    cabins = select_cabins()
    id_from_name = { name: id_ for id_, name in cabins}
    print(id_from_name)
    names = set(name for id_, name in cabins)
    print(len(id_from_name.keys()))
    for rates in get_quote_single_threaded():
        if not rates: continue
        start_date = rates[0]['start']
        end_date = rates[0]['end']
        holiday = rates[0]['holiday']
        print(f'scrapped rates: {start_date} {end_date} - {holiday}')
        rates_with_id = []
        for r in rates:
            id_ = id_from_name.get(r['name'])
            if id_:
                rates_with_id.append({**r, 'id': id_})
        #preparing not found results
        scraped_names = set(r['name'] for r in rates)
        not_found_names = names - scraped_names
        for name in not_found_names:
            rates_with_id.append({
                'id': id_from_name[name],
                'start': start_date,
                'end': end_date,
                'status': 'BOOKED',
                'holiday': holiday,
                'price': 0
            })
        insert_rates_faster(rates_with_id)

def initializer():
    global b
    prefs = {"profile.managed_default_content_settings.images":2}
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", prefs)
    b = Browser('chrome', headless=False, options=options, **executable_path)

def get_quote_worker(date_range):
    start_date, end_date, holiday = date_range
    results = []
    start = start_date.strftime('%m/%d/%Y')
    end = end_date.strftime('%m/%d/%Y')
    try:
        url = f'https://www.destinationbigbear.com/FindCabin.aspx?firstnight={start}&lastnight={end}'
        b.visit(url)
        while True:
            while b.is_element_present_by_css('body.loading'):
                pass
            while b.is_element_not_present_by_css('.panel-overlay-bottom > h4'):
                pass
            prices_with_dollar = [e.text for e in b.find_by_css('.panel-overlay-bottom > h4') if e.text]
            prices = [re.sub(r'[\$,]', '', price_with_dollar) for price_with_dollar in prices_with_dollar]
            names = [e.text for e in b.find_by_css('.caption.header > h3') if e.text]
            results+= [{'name': name, 'price':price, 'start': start, 'end':end, 'holiday': holiday, 'status': 'AVAILABLE'} for name, price in zip(names, prices)]
            next_ = b.find_by_css('.btn.next')
            if next_.has_class('disabled'):
                break
            else:
                next_.click()
        return results
    except Exception as e:
        print(e)
        return []
    

def get_quote_from_pool(processes = None):
    date_ranges = util.get_date_ranges()
    with mp.Pool(processes, initializer=initializer) as p:
        yield from p.imap_unordered(get_quote_worker, date_ranges)

def get_quote_single_threaded():
    date_ranges = util.get_date_ranges()
    prefs = {"profile.managed_default_content_settings.images":2}
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs",prefs)
    with Browser('chrome', headless=True, options=options, **executable_path) as b:
        for start_date, end_date, holiday in date_ranges:
            results = []
            start = start_date.strftime('%m/%d/%Y')
            end = end_date.strftime('%m/%d/%Y')
            url = f'https://www.destinationbigbear.com/FindCabin.aspx?firstnight={start}&lastnight={end}'
            try:
                b.visit(url)
                while True:
                    while b.is_element_present_by_css('body.loading'):
                        pass
                    tries = 0
                    while b.is_element_not_present_by_css('.panel-overlay-bottom > h4'):
                        tries += 1
                        if tries > 10:
                            return results
                    prices_with_dollar = [e.text for e in b.find_by_css('.panel-overlay-bottom > h4') if e.text]
                    prices = [re.sub(r'[\$,]', '', price_with_dollar).split()[0] for price_with_dollar in prices_with_dollar]
                    names = [e.text for e in b.find_by_css('.caption.header > h3') if e.text]
                    results+= [{'name': name, 'price':price, 'start': start, 'end':end, 'holiday': holiday, 'status': 'AVAILABLE'} for name, price in zip(names, prices)]
                    next_ = b.find_by_css('.btn.next')
                    if next_.has_class('disabled'):
                        break
                    else:
                        next_.click()
                yield results
            except Exception as e:
                print(e)
                yield results

def insert_rates_faster(rates):
    tupled_rates = set((r['id'], r['start'], r['end'], r['status'], r['price'], r['holiday']) for r in rates)
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    with connection, connection.cursor() as cursor:
        str_sql = '''INSERT INTO db.availability (id, check_in, check_out, status, rate, name) 
            VALUES %s ON CONFLICT (id, check_in, check_out, name) DO UPDATE SET id = EXCLUDED.id, 
            check_in = EXCLUDED.check_in, check_out = EXCLUDED.check_out, status = EXCLUDED.status,
            rate = (case when excluded.status = 'AVAILABLE' then excluded.rate else 
            db.availability.rate end), name = EXCLUDED.name'''
        execute_values(cursor, str_sql, tupled_rates)
    connection.close()

def get_quote():
    pass

def extract_costs():
    cabins = load_cabins()
    pattern = re.compile(r'propid=(\d+)')
    ids = [ re.search(pattern, cabin['url']).group(1) for cabin in cabins ]
    return util.extract_costs(ids, get_quote)

@default_value
def extract_name(soup):
    elem = soup.find(id='ctl00_ContentPlaceHolder1_lblDetailName')
    name = elem.get_text(strip=True)
    return name

@default_value
def extract_subtitle(soup):
    elem = soup.select_one('.fav-headding > p')
    addr = elem.get_text('\n', strip=True)
    return addr

@default_value
def extract_description(soup):
    elem = soup.find(id='ctl00_ContentPlaceHolder1_hdnDesc')
    desc = elem.get('value')
    return BeautifulSoup(desc, "html.parser").text

@default_value
def extract_full_address(soup):
    elem = soup.find(id='ctl00_ContentPlaceHolder1_hdnFullAdd')
    addr = elem.get('value')
    return addr

@default_value
def extract_properties(soup):
    elem = soup.find(id='ctl00_ContentPlaceHolder1_Property')
    props = elem.get_text('\n', strip=True)
    props = re.sub(r'\:\n+', r': ', props)
    props = re.findall(r'\s*([^\n]+)\s*\:\s*(.+)', props)
    props = dict(props)
    return props

@default_value
def extract_arrangements(soup):
    elem = soup.select_one('#About-the-cabin blockquote > p > p')
    props = elem.get_text('\n', strip=True)
    props = re.sub(r'\:\n', r': ', props)
    props = re.findall(r'\s*([^\n]+)\s*\:\s*(.+)', props)
    props = dict(props)
    return props

@default_value
def extract_rates(soup):

    rates = {}
    elem  = soup.find(id='ctl00_ContentPlaceHolder1_Record1')
    rows  = elem.find_all('tr', id=None, class_=None) 

    for row in rows:
        # Here we assume it doesn't have a ":"
        # If there is one, it would not work properly
        text = row.get_text(': ', strip=True)
        match = re.search(r'\s*([^\n]+)\s*\:\s*(.+)', text)

        if match:
            key, val = match.groups()
            key = key.replace(':', '') # Trying to hide
            rates[key] = val

    return rates

@default_value
def extract_amenities(id, soup):
    elem = soup.find('li', string=re.compile(r'Amenities'))
    parent = elem.find_parent('div')
    amenities = parent.find_all(lambda t: t.name == 'li' and t.i)
    amenities = [ (id, x.get_text(strip=True)) for x in amenities ]
    #amenities from details section
    detail_list_tag = soup.find('div', class_='detail-list')
    if detail_list_tag:
        for li in detail_list_tag('li'):
            amenity = li.get_text(strip=True)
            amenities.append( (id, amenity) )
    return amenities

@default_value
def extract_id(soup):
    elem = soup.find(id='ctl00_ContentPlaceHolder1_hdnPropId')
    return elem.get('value')

def extract_calendar(soup):
    months = soup.select('.CalendarCompact tr[valign] > td')
    red  = re.compile('red')
    year = dt.date.today().year

    for i, month in enumerate(months, 1):
        days = month.find_all('td', style=red)
        days = [ d.get_text(strip=True) for d in days ]
        days = map(int, days)
        try:
            yield from ( dt.date(year, i, d) for d in days )
        except ValueError as e:
            print(e)
            

def parse_dates(dates):
    return [ str(d) for d in dates ]

def get_availability_weekends_friday(id, booked):
    availability = []
    today = datetime(2018, 1, 1)
    friday = today + timedelta( (4-today.weekday()) % 7 )

    while friday.year == 2018:
        saturday = friday + timedelta(days=1)
        if (
            friday.strftime("%Y-%m-%d") not in booked
            and saturday.strftime("%Y-%m-%d") not in booked
        ):
            status = 'AVAILABLE'
        else:
            status = 'BOOKED'
        
        sunday = friday + timedelta(days=2)
        rate = '0'
        actual = [
            'DBB' + id,
            friday.strftime("%Y-%m-%d"),
            sunday.strftime("%Y-%m-%d"),
            status,
            rate,
            'Weekend'
        ]
        availability.append(actual)
        friday = util.add_one_week(friday)
    return availability

def get_availability_MLK(id, booked):
    availability = []
    day1 = datetime(2018, 1, 12)
    day2 = datetime(2018, 1, 13)
    day3 = datetime(2018, 1, 14)

    if (
        day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked
        and day3.strftime("%Y-%m-%d") not in booked
    ):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day3 + timedelta(days=1)
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'MLK Day'
    ]
    availability.append(actual)
    return availability

def get_availability_president(id, booked):
    availability = []
    day1 = datetime(2018, 2, 16)
    day2 = datetime(2018, 2, 19)

    if (
        day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked
    ):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day2 + timedelta(days=1)
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'President\'s Day'
    ]
    availability.append(actual)
    return availability

def get_availability_patrick(id, booked):
    availability = []
    day = datetime(2018, 3, 16)

    if day.strftime("%Y-%m-%d") not in booked:
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day + timedelta(days=1)
    actual = [
        'DBB' + id,
        day.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'St Patrick\'s Day'
    ]
    availability.append(actual)
    return availability

def get_availability_easter(id, booked):
    availability = []
    day1 = datetime(2018, 3, 30)
    day2 = datetime(2018, 3, 31)

    if ( day1.strftime("%Y-%m-%d") not in booked 
        and day2.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day2 + timedelta(days=1)
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'Easter'
    ]
    availability.append(actual)
    return availability

def get_availability_cincomayo(id, booked):
    availability = []
    day = datetime(2018, 5, 4)

    if day.strftime("%Y-%m-%d") not in booked:
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day + timedelta(days=1)
    actual = [
        'DBB' + id,
        day.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'Cinco de Mayo'
    ]
    availability.append(actual)
    return availability

def get_availability_memorial(id, booked):
    availability = []
    day1 = datetime(2018, 5, 25)
    day2 = datetime(2018, 5, 26)
    day3 = datetime(2018, 5, 27)

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked
        and day3.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day3 + timedelta(days=1)
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'Memorial Day'
    ]
    availability.append(actual)
    return availability

def get_availability_4july(id, booked):
    availability = []
    day1 = datetime(2018, 7, 4)
    day2 = datetime(2018, 7, 7)

    if day1.strftime("%Y-%m-%d") not in booked:
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        day2.strftime("%Y-%m-%d"),
        status,
        rate,
        '4th of July'
    ]
    availability.append(actual)
    return availability

def get_availability_labor(id, booked):
    availability = []
    day1 = datetime(2018, 8, 31)
    day2 = datetime(2018, 9, 1)
    day3 = datetime(2018, 9, 3)

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked ):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        day3.strftime("%Y-%m-%d"),
        status,
        rate,
        'Labor Day'
    ]
    availability.append(actual)
    return availability

def get_availability_columbus(id, booked):
    availability = []
    day1 = datetime(2018, 10, 5)
    day2 = datetime(2018, 10, 6)
    day3 = datetime(2018, 10, 7)
    day4 = datetime(2018, 10, 8)

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked 
        and day3.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        day4.strftime("%Y-%m-%d"),
        status,
        rate,
        'Columbus Day'
    ]
    availability.append(actual)
    return availability

def get_availability_veterans(id, booked):
    availability = []
    day1 = datetime(2018, 11, 9)
    day2 = datetime(2018, 11, 10)
    day3 = datetime(2018, 11, 11)
    day4 = datetime(2018, 11, 12)

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked 
        and day3.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        day4.strftime("%Y-%m-%d"),
        status,
        rate,
        'Veteran\'s Day'
    ]
    availability.append(actual)
    return availability

def get_availability_thanksgiving(id, booked):
    availability = []
    day1 = datetime(2018, 11, 22)
    day2 = datetime(2018, 11, 23)
    day3 = datetime(2018, 11, 24)

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked 
        and day3.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        day3.strftime("%Y-%m-%d"),
        status,
        rate,
        'Thanksgiving'
    ]
    availability.append(actual)
    return availability

def get_availability_christmas(id, booked):
    availability = []
    day1 = datetime(2018, 12, 21)
    day2 = datetime(2018, 12, 22)
    day3 = datetime(2018, 12, 23)
    day4 = datetime(2018, 12, 24)
    day5 = datetime(2018, 12, 25)
    day6 = datetime(2018, 12, 26)
    day7 = datetime(2018, 12, 27)
    day8 = datetime(2018, 12, 28)
    day9 = datetime(2018, 12, 29)
    day10 = datetime(2018, 12, 30)
    day11 = datetime(2018, 12, 31)
    day12 = datetime(2019, 1, 1)

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked 
        and day3.strftime("%Y-%m-%d") not in booked
        and day3.strftime("%Y-%m-%d") not in booked 
        and day4.strftime("%Y-%m-%d") not in booked
        and day5.strftime("%Y-%m-%d") not in booked 
        and day6.strftime("%Y-%m-%d") not in booked
        and day7.strftime("%Y-%m-%d") not in booked 
        and day8.strftime("%Y-%m-%d") not in booked
        and day9.strftime("%Y-%m-%d") not in booked 
        and day10.strftime("%Y-%m-%d") not in booked
        and day11.strftime("%Y-%m-%d") not in booked 
        and day12.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'DBB' + id,
        day1.strftime("%Y-%m-%d"),
        day12.strftime("%Y-%m-%d"),
        status,
        rate,
        'Christmas Season'
    ]
    availability.append(actual)
    return availability

def parse_data(html):

    keys = ['name', 'subtitle', 'properties', 'arrangements', 
            'rates', 'amenities', 'site_id', 'url', 'booked' ]
    data = dict.fromkeys(keys)

    # Extract data
    soup = BeautifulSoup(html, 'html.parser')

    id_ = extract_id(soup)
    data['site_id'] = 'DBB' + id_

    name = extract_name(soup)
    data['name'] = name

    sub = extract_subtitle(soup)
    data['subtitle'] = sub

    props = extract_properties(soup)
    data['properties'] = props

    arrangements = extract_arrangements(soup)
    data['arrangements'] = arrangements

    rates = extract_rates(soup)
    data['rates'] = rates

    desc = extract_description(soup)
    data['description'] = desc

    addr = extract_full_address(soup)
    data['address'] = addr

    amenities = extract_amenities(data['site_id'], soup)
    data['amenities'] = amenities

    return data

# First for destinationbigbear
def scrape_cabin(url):

    try:
        # First try, not so elegant
        # Request for html
        print('Scraping...' + url) 
        resp = rq.get(url)
        time.sleep(0.8)
        html = resp.text # raise for status

        data = parse_data(html)
        data['url'] = url
        return data
    
    # except Exception as e: print(e)
    except Exception as e:
        print(f'Exception scraping url:{url}')
        print(e)
        logging.exception("error aqui")
        return None
    except KeyboardInterrupt: pass

# Nothing to do here...
def crawl_cabins(urls):

    with mp.Pool() as p:
        yield from p.imap_unordered(scrape_cabin, urls)

def dump_from(filename, data):
    name = os.path.basename(filename)
    name = os.path.splitext(name)[0]
    name = f'{name}.json'
    with open(name, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)
    return name

def get_rates(availability):
    # availability
    url = 'http://www.destinationbigbear.com/Property_detail_v.aspx/SearchQuote'
    try:
        if availability[3] == 'AVAILABLE': #status
            date_from = datetime.strptime(availability[1], '%Y-%m-%d').strftime('%m/%d/%Y')
            date_to = datetime.strptime(availability[2], '%Y-%m-%d').strftime('%m/%d/%Y')
            object_request = json.dumps({
                "from": date_from, #check_in
                "id": availability[0][3:], #id
                "to": date_to #check_out
            })
            header_content = {'Content-type': 'application/json'} 
            resp_hell = rq.post(url, data = object_request, headers = header_content)
            resp_json = resp_hell.json()
            availability[4] = float(resp_json['TotalRates'][1:].replace(',', ''))
    except:
        pass
    finally:
        return availability

def get_rates_multi(availabilities):
    with mp.Pool() as p:
        yield from p.imap_unordered(get_rates, availabilities)

def update_database(cabins, amenities, availabilities=None):
    connection = psycopg2.connect(os.getenv('DATABASE_URL'))
    with connection:
        with connection.cursor() as cursor:
            # Update cabins
            cursor.execute('DELETE FROM db.cabin WHERE idvrm=\'DBB\'')
            str_sql = '''INSERT INTO db.cabin (idvrm, id, name, website, description, bedrooms, 
                occupancy) VALUES %s ON CONFLICT (id) DO UPDATE SET name = 
                excluded.name, website = excluded.website, description = excluded.description, bedrooms = 
                excluded.bedrooms, occupancy = excluded.occupancy;'''
            execute_values(cursor, str_sql, cabins)

            # Update amenities
            str_sql = 'INSERT INTO db.features (id, amenity) VALUES %s ON CONFLICT (id, amenity) DO NOTHING'
            execute_values(cursor, str_sql, amenities)

            # Update availabilities
            str_sql = '''INSERT INTO db.availability (id, check_in, check_out, status, rate, name) VALUES %s ON CONFLICT (id, check_in, check_out, name) DO UPDATE SET rate = excluded.rate;'''
            execute_values(cursor, str_sql, availabilities)

            # Update vrm ncabins and last_scrape
            cursor.execute('UPDATE db.vrm SET ncabins=' + str(len(cabins)) + ', last_scrape=CURRENT_TIMESTAMP WHERE idvrm = \'DBB\'')
    connection.close()

def scrape_cabins():
    filename = './scrappers/dbb.json'
    with open(CABIN_URLS_FILE) as f:
        links = json.load(f)
    total   = len(links)
    index   = 0
    results = []

    try:
        for r in crawl_cabins(links):
            if r is None: continue
            results.append(r)
            index += 1
            print(f'Scraped! {r["name"]} {r["site_id"]} {index}/{total}')
    except KeyboardInterrupt: pass
    finally: 
        # Write finally result
        with open(filename, 'w', encoding='utf8') as fl:
            json.dump(results, fl, indent=2)
            print('Dumped', filename)

def insert_cabins():
    cabins = load_cabins()
    insertCabins = []
    for cabin in cabins:
        cabinInsert = (
                'DBB', 
                cabin.get('site_id'), 
                cabin.get('name').split(' - ')[0], 
                cabin.get('url'), 
                cabin.get('description'), 
                cabin.get('properties').get('Bedrooms'), 
                cabin.get('properties').get('Occupancy'),
                cabin.get('address'),
                'ACTIVE',
                cabin.get('name').split(' - ')[1]
            )
        insertCabins.append(cabinInsert)
    connection = psycopg2.connect(DATABASE_URI)
    with connection:
        with connection.cursor() as cursor:
            str_sql = '''UPDATE db.cabin SET status = 'INACTIVE' WHERE idvrm = 'DBB' '''
            cursor.execute(str_sql)
            # Update cabins
            str_sql = '''INSERT INTO db.cabin (idvrm, id, name, website, description, bedrooms, 
                occupancy, address, status, location) VALUES %s ON CONFLICT (id) DO UPDATE SET 
                name = excluded.name, website = excluded.website, description = 
                excluded.description, bedrooms = excluded.bedrooms, occupancy = excluded.occupancy,
                address = excluded.address, status = excluded.status, location = excluded.location;'''
            execute_values(cursor, str_sql, insertCabins)
    connection.close()

def insert_amenities():
    cabins = load_cabins()
    amenities = []
    for cabin in cabins:
        cabin_id = cabin['site_id']
        for amenity in cabin.get('amenities') :
                amenities.append(amenity)
        for k, v in cabin['properties'].items():
            if 'Game' in k and v == 'Yes':
                amenities.append((cabin_id,'Games'))
            elif k == 'Internet' and v == 'Yes':
                amenities.append((cabin_id, 'WIFI/Internet'))
            elif k == 'Hot Tub' and v == 'Yes':
                amenities.append((cabin_id,'SPA/Hot Tub/Jacuzzi'))
            elif k == 'Pet Friendly' and v == 'Yes':
                amenities.append((cabin_id,'PETS'))
    # Update amenities
    connection = psycopg2.connect(DATABASE_URI)
    with connection:
        with connection.cursor() as cursor:
            str_sql = '''INSERT INTO db.features (id, amenity) VALUES %s ON CONFLICT (id, amenity) DO NOTHING'''
            execute_values(cursor, str_sql, amenities)
    connection.close()

def update_last_scrape():
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        c.execute("""INSERT INTO db.vrm (idvrm, name, website, ncabins, last_scrape)
            VALUES (%s, %s, %s, (select count(id) from db.cabin where idvrm = 'DBB' and 
            status='ACTIVE'), now()) ON CONFLICT (idvrm) DO UPDATE SET name = excluded.name, 
            website = excluded.website, ncabins = (select count(id) from db.cabin where idvrm = 'DBB' and 
            status='ACTIVE'), last_scrape = now()""", 
            ('DBB', 'Destination Big Bear', 
            'http://www.destinationbigbear.com'))
    connection.close()

def run():
    try:
        scrape_cabin_urls()
        scrape_cabins()
        insert_cabins()
        insert_amenities()
        scrape_rates_and_insert_faster()
        update_last_scrape()
    except Exception as e:
        print('Error in Destination Big Bear scrapper:')
        raise(e)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./destinationbigbear.py [FILENAME]')
        return

    filename = sys.argv[1]
    links = read_csv_cabins(filename)

    total   = len(links)
    index   = 0
    results = []

    try:
        ncabins = 0
        amenities = []
        cabins = []
        availabilities = []
        for r in crawl_cabins(links):
            if r is None: continue
            results.append(r)
            index += 1
            ncabins +=1
            print(f'Scraped! {r["name"]} {r["site_id"]} {index}/{total}')

            for amenity in r.get('amenities') :
                amenities.append(amenity)

           # for availability in r.get('availabilities') :
           #     availabilities.append(availability)

            cabinInsert = (
                'DBB', 
                r.get('site_id'), 
                r.get('name'), 
                r.get('url'), 
                r.get('description'), 
                r.get('properties').get('Bedrooms'), 
                r.get('properties').get('Occupancy')
            )
            cabins.append(cabinInsert)

        #new_availabilities = []
        #total = len(availabilities)
        #index = 0
        #for gr in get_rates_multi(availabilities):
        #    index += 1
        #    new_availabilities.append(gr)
        #    print(f'Availability {index}/{total}')


    except KeyboardInterrupt: pass
    finally: 
        # Write finally result
        name = dump_from(filename, results)
        print('Dumped', name)

        update_database(cabins, amenities)#, new_availabilities)
        print('Database updated')
        #cursor.close()
        #connection.close()

if __name__ == '__main__':
    main()

