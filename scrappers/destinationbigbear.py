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
from scrappers import util
from psycopg2.extras import execute_values
from datetime import datetime
from datetime import timedelta
from bs4 import BeautifulSoup

DATABASE_URL = os.environ['DATABASE_URL']
connection = psycopg2.connect(DATABASE_URL)
cursor = connection.cursor()

# destinationbigbear -> dbb
# bigbearcoolcabins  -> bbc
# vacasa             -> vcs
# bigbearvacations   -> bbv
# Don't forget to handle exceptions

def default_value(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e: 
            pass
            # print(func)
            # print(e)
    return wrapper

def read_csv_cabins(filename):
    # Extract cabins website from csv
    df = pd.read_csv(filename)
    return df.Link

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
    return  html.escape(desc)

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
        yield from ( dt.date(year, i, d) for d in days )

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

    amenities = extract_amenities(data['site_id'], soup)
    data['amenities'] = amenities

    booked = extract_calendar(soup)
    data['booked'] = parse_dates(booked)
    # Obviously this needs to be changed but not tonight fellas
    availabilities_weekends = get_availability_weekends_friday(id_, data['booked'])
    availabilities_MLK = get_availability_MLK(id_, data['booked'])
    availabilities_president = get_availability_president(id_, data['booked'])
    availabilities_patrick = get_availability_patrick(id_, data['booked'])
    availabilities_easter = get_availability_easter(id_, data['booked'])
    availabilities_cincomayo = get_availability_cincomayo(id_, data['booked'])
    availabilities_memorial = get_availability_memorial(id_, data['booked'])
    availabilities_4july = get_availability_4july(id_, data['booked'])
    availabilities_labor = get_availability_labor(id_, data['booked'])
    availabilities_columbus = get_availability_columbus(id_, data['booked'])
    availabilities_veterans = get_availability_veterans(id_, data['booked'])
    availability_thanksgiving = get_availability_thanksgiving(id_, data['booked'])
    availabilities_christmas = get_availability_christmas(id_, data['booked'])

    data['availabilities'] = availabilities_weekends + availabilities_MLK + availabilities_president + availabilities_patrick + availabilities_easter + availabilities_cincomayo + availabilities_memorial + availabilities_4july + availabilities_labor + availabilities_columbus + availabilities_veterans + availability_thanksgiving + availabilities_christmas

    return data

# First for destinationbigbear
def scrape_cabin(url):

    try:
        # First try, not so elegant
        # Request for html
        print('Scraping...' + url) 
        resp = rq.get(url)
        html = resp.text # raise for status

        data = parse_data(html)
        data['url'] = url
        return data
    
    except Exception as e: print(e)
    except KeyboardInterrupt: pass

# Nothing to do here...
def crawl_cabins(urls, N=4):

    with mp.Pool(N) as p:
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

def get_rates_multi(availabilities, N=4):
    with mp.Pool(N) as p:
        yield from p.imap_unordered(get_rates, availabilities)

def update_database(cabins, amenities, availabilities):
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
    cursor.close()
    connection.close()


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

            for availability in r.get('availabilities') :
                availabilities.append(availability)

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

        new_availabilities = []
        total = len(availabilities)
        index = 0
        for gr in get_rates_multi(availabilities):
            index += 1
            new_availabilities.append(gr)
            print(f'Availability {index}/{total}')


    except KeyboardInterrupt: pass
    finally: 
        # Write finally result
        name = dump_from(filename, results)
        print('Dumped', name)

        update_database(cabins, amenities, new_availabilities)
        print('Database updated')
        cursor.close()
        connection.close()

if __name__ == '__main__':
    main()

