import pandas as pd
import sys
import requests as rq
import re
import json
import multiprocessing as mp
import datetime as dt
import os
import time
import itertools
import psycopg2
from psycopg2.extras import execute_values
from splinter import Browser
from scrappers import util
from scrappers import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from scrappers.util import print

from bs4 import BeautifulSoup
from urllib.parse import urlparse

import itertools

# destinationbigbear -> dbb
# bigbearcoolcabins  -> bbc
# vacasa             -> vcs
# bigbearvacations   -> bbv
# Don't forget to handle exceptions

db_id = 'VACASA'

executable_path = {'executable_path': os.getenv('CHROME_DRIVER_EXECUTABLE_PATH')}

HEADERS = { 'accept-language': 'en', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36' }

DATE_FORMAT = '%Y/%m/%d'
OUTPUT_FILE = './scrappers/vacasa_cabins.json'
DATABASE_URI = os.getenv('DATABASE_URI')

def default_value(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e:
            pass
            # print(func)
            # print(e)
    return wrapper

def read_json(filename):
    with open(filename, encoding='utf8') as f:
        data = json.load(f)
    return data

def read_csv_cabins(filename):
    # Extract cabins website from csv
    df = pd.read_csv(filename)
    return df.Link

def extract_title(soup):
    elem = soup.find('h1', class_='type-heading-large')
    text = elem.get_text(strip=True)
    return text

def extract_description(soup):
    elem = soup.find(id='unit-desc')
    header = elem.find_previous_sibling('h2')
    text = elem.get_text('\n', strip=True)
    text = '\n'.join([ header.get_text(strip=True), text ])
    return text

def extract_amenities(soup):
    elems = soup.find_all(class_='amenity')
    return [ e.get_text(strip=True) for e in elems ]

def extract_features(soup):
    features = soup.select('.core-feature')
    return [ ' '.join(ft.text.split()) for ft in features ]

def extract_calendar(soup):
    elem = soup.find('script', text=re.compile(r'Availability'))
    text = elem.text
    match = re.search(r'Availability:\s*(\[[^\[]+\])', text)
    availability = match.group(1)
    return json.loads(availability)

def extract_rates(soup):

    elem = soup.find('script', text=re.compile(r'Rates'))
    text = elem.text

    match = re.search(r'Rates: (\{[^\{]+\})', text)
    rates = match.group(1)

    match = re.search(r'low: \'([^\']+)\'', rates)
    low = match.group(1)

    match = re.search(r'high: \'([^\']+)\'', rates)
    high = match.group(1)

    return { 'low': low, 'high': high }

def parse_data(html):

    data = {}
    soup = BeautifulSoup(html, 'html.parser')

    title = extract_title(soup)
    data['name'] = title

    description = extract_description(soup)
    data['description'] = description

    amenities = extract_amenities(soup)
    data['amenities'] = amenities

    features = extract_features(soup)
    data['features'] = features

    # calendar = extract_calendar(soup)
    # data['availability'] = calendar

    # rates = extract_rates(soup)
    # data['rates'] = rates

    occupancy = soup.find(class_='icon-people-family').next_sibling # sibling next to occupancy icon
    data['occupancy'] = re.search(r'\d+', occupancy).group(0) # digit in "Max Occupancy: \d+"
    
    bedrooms = soup.find(class_='icon-door').next_sibling
    data['bedrooms'] = re.search(r'\d+', bedrooms).group(0)

    address = soup.find(class_='icon-map-location').next_sibling
    data['address'] = address.strip()

    splitted_address = data['address'].split(',')

    data['location'] = splitted_address[1] if splitted_address[1:2] else ''
    return data

@util.ignore_errors
def fetch_cost(id_, start, end):


    if isinstance(start, dt.date):
        start = start.strftime(DATE_FORMAT)

    if isinstance(end, dt.date):
        end = end.strftime(DATE_FORMAT)

    API_URL = 'https://www.vacasa.com/guest-com-api/get-unit-price-quote'
    params = {
        'unit_id': id_,
        'check_in': start, # 2018/09/19
        'check_out': end,  # 2018/09/22
        'adults': 1,
        'children': 0,
        'pets': 0
    }

    resp = rq.get(API_URL, params=params)
    data = resp.json()

    return data

def extract_costs():

    cabins = load_cabins()

    ids = []
    for cabin in cabins:
        parsed = urlparse(cabin['url'])
        key, value = parsed.query.split('=')
        ids.append(value)

    return util.extract_costs(ids, fetch_cost)

def scrape_and_insert_rates():
    for costs in extract_costs_faster():
        if not costs:
            continue
        start_date = costs[0]['startDate']
        end_date = costs[0]['endDate']
        holiday = costs[0]['holiday']
        print(f'Scrapped range: {start_date} - {end_date} : {holiday}')
        insert_rates_faster(costs)

def extract_costs_faster():
    return util.extract_costs_faster(extract_costs_faster_function)

def extract_cabin_urls_splinter():
    url = 'https://www.vacasa.com/usa/Big-Bear/'
    base_url = 'https://www.vacasa.com'
    urls = []
    with Browser('chrome', headless=True, **executable_path) as b:
        b.visit(url)
        while True:
            soup = BeautifulSoup(b.html, 'html.parser')
            urls += [base_url + a['href'] for a in soup('a', class_='unit-listing-title')]
            while b.is_element_present_by_css('.loader.d-block'):
                pass
            next_button = b.find_link_by_text('next')
            if next_button:
                next_button[0].click()
            else:
                soup = BeautifulSoup(b.html, 'html.parser')
                urls += [base_url + a['href'] for a in soup('a', class_='unit-listing-title')]
                break
    urls = list(set(urls))
    with open('scrappers/vacasa_cabin_urls.json', 'w', encoding='utf8') as f:
        json.dump(urls, f, indent=2)


def rate_scrapper_single_threaded():
    df = pd.read_csv('scrappers/CEK_DB_-_Dates_CSV.csv', parse_dates=['PL', 'PR'])
    range_ = [(pl, pr, h) for i,pl,pr,h in df.itertuples()]
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    with Browser('chrome', headless=True, options=chrome_options,**executable_path) as b:
        for start, end, holiday in range_:
            if start < dt.datetime.now(): continue
            cabins = []
            start_string = start.strftime("%m/%d/%Y").replace('/', '%2F')
            end_string = end.strftime("%m/%d/%Y").replace('/', '%2F')
            url = f'https://www.vacasa.com/usa/Big-Bear/?arrival={start_string}&departure={end_string}'
            print(f'Splinter-visiting url: {url}')
            try:
                b.visit(url)
            except TimeoutException as e:
                print(e)
                return cabins
            page_num = 0
            while True:
                page_num+=1
                print('scraping page number: ', page_num)
                soup = BeautifulSoup(b.html, 'html.parser')
                cabin_tags = soup(class_='unit-result-list')
                if not cabin_tags:
                    break
                for c in cabin_tags:
                    id_ = c['data-unit-id']
                    pattern = re.compile(r'\$([\d,.]+)')
                    price_with_commas = pattern.match(c.find('a', text=pattern).get_text()).group(1)
                    price = price_with_commas.replace(',', '')
                    cabins.append({
                        'id': id_, 
                        'quote': price, 
                        'startDate': start, 
                        'endDate': end, 
                        'holiday': holiday,
                        'status': 'BOOKED' if c.find('a',class_='ribbon-content', text='BOOKED') else 'AVAILABLE'
                        })
                while b.is_element_present_by_css('.loader.d-block'):
                    pass
                next_button = b.find_link_by_text('next')
                if next_button:
                    next_button[0].click()
                else:
                    break
            insert_rates_faster(cabins)


def extract_costs_faster_function(range_tuple):
    (start, end, holiday) = range_tuple
    cabins = []
    start_string = start.strftime("%m/%d/%Y").replace('/', '%2F')
    end_string = end.strftime("%m/%d/%Y").replace('/', '%2F')
    with Browser('chrome', headless=True, **executable_path) as b:
        b.driver.set_window_size(1200, 600)
        url = f'https://www.vacasa.com/usa/Big-Bear/?arrival={start_string}&departure={end_string}'
        print(f'Splinter-visiting url: {url}')
        try:
            b.visit(url)
        except TimeoutException as e:
            print(e.stacktrace)
            return cabins
        while True:
            soup = BeautifulSoup(b.html, 'html.parser')
            cabin_tags = soup(class_='unit-result-list')
            if not cabin_tags:
                break
            for c in cabin_tags:
                id_ = c['data-unit-id']
                pattern = re.compile(r'\$(\d+[,]*\d+)')
                price = pattern.match(c.find('a', text=pattern).get_text()).group(1)
                cabins.append({
                    'id': id_, 
                    'quote': price, 
                    'startDate': start, 
                    'endDate': end, 
                    'holiday': holiday,
                    'status': 'BOOKED' if c.find('a', text='BOOKED') else 'AVAILABLE'
                    })
            while b.is_element_present_by_css('.loader.d-block'):
                pass
            next_button = b.find_link_by_text('next')
            if next_button:
                try:
                    next_button[0].click()
                except TimeoutException as e:
                    return cabins
            else:
                break
    return cabins
        

def scrape_cabin(url):

    try:
        # First try, not so elegant
        # Request for html
        print('Scraping...')
        resp = rq.get(url, headers=HEADERS)
        resp.raise_for_status()

        html = resp.text # raise for status
        data = parse_data(html)

        # Add data from extra requests
        # ...

        data['id'] = re.search(r'UnitID=(\d+)', url).group(1)
        data['url'] = url

        return data

    # Comment to debug better
    # except Exception as e:
    #     print('Exception!')
    #     print(url)
    #     print(e)

    except KeyboardInterrupt:
        pass

# Nothing to do here...
def crawl_cabins(urls):

    with mp.Pool() as p:
        yield from p.imap_unordered(scrape_cabin, urls)

def dump_from(filename, data):
    #name = os.path.basename(filename)
    #name = os.path.splitext(name)[0]
    #name = '{}.json'.format(name)
    with open(filename, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)
    return filename

def fix_booked():

    data = util.read_json(OUTPUT_FILE)
    for x in data:
        dates = x['availability']
        url   = x['url']
        match = re.search(r'UnitID\=(\w+)$', url)
        id_ = match.group()
        booked = [ d['date'] for d in dates if not d['is_available'] ]
        yield { 'id': id_, 'url': url, 'booked': booked }

def load_rates():
    with open('./scrappers/vacasa_quote_results.json', encoding='utf8') as f:
        rates = json.load(f)
    return rates

def insert_features():
    connection = psycopg2.connect(DATABASE_URI)
    cabins = load_cabins()
    features_tuples = []
    for c in cabins:
        for f in c['amenities'] + c['features']:
            id_ = 'VACASA' + re.search(r'UnitID=(\d+)', c['url']).group(1)
            features_tuples.append((id_, f))
    with connection, connection.cursor() as c:
        sql = "delete from db.features where id like 'VACASA%'"
        c.execute(sql)
        sql = '''INSERT INTO db.features (id, amenity) VALUES %s ON CONFLICT (id, amenity) DO NOTHING'''
        execute_values(c, sql, features_tuples)
    connection.close()
    

def insert_rates_faster(rates):
    tuples = []
    for rate in rates:
        id_ = 'VACASA' + rate['id']
        start = rate['startDate']
        end =  rate['endDate']
        tuples.append((id_, start, end, rate['status'], rate['quote'], rate['holiday']))
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        sql = '''INSERT INTO db.availability (id, check_in, check_out, status, rate, name) 
            VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id, check_in, check_out, name) DO UPDATE SET id = EXCLUDED.id, 
            check_in = EXCLUDED.check_in, check_out = EXCLUDED.check_out, status = EXCLUDED.status,
            rate = (case when excluded.status = 'AVAILABLE' then excluded.rate else 
            db.availability.rate end), name = EXCLUDED.name'''
        # execute_values(c, sql, tuples)
        for t in tuples:
            c.execute(sql, t)
    connection.close()

def insert_rates(*args):
    rates = []
    if len(args) == 0:
        rates = load_rates()
    elif len(args) == 1:
        rates = args[0]
    holidays = util.get_holidays_as_dict()
    tuples = []
    for rate in rates:
        id_ = 'VACASA' + rate['id']
        start = rate['startDate'].to_pydatetime()
        end =  rate['endDate'].to_pydatetime()
        name = rate['holiday']
        if rate.get('quote') and rate['quote'].get('raw') and  rate['quote']['raw'].get('Error') or not rate['quote'].get('raw'):
            booked = 'BOOKED'
            q = 0
        else:
            booked = 'AVAILABLE'
            q = rate['quote']['raw']['1']['Total']
        tuples.append((id_, start, end, booked, q, name))
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        """#this doesn't work, idk why
        sql = 
            INSERT INTO db.availability
            SELECT (val.id, val.check_in, val.check_out, val.status, val.rate, val.name) 
            FROM (VALUES %s) val (id, check_in, check_out, status, rate, name)
            JOIN db.cabin USING (id)
            ON CONFLICT DO NOTHING
        psycopg2.extras.execute_values(c, sql, tuples)
        """
        for t in tuples:
            c.execute('insert into db.availability values (%s,%s,%s,%s,%s,%s) on conflict do nothing', t)
    connection.close()

def load_cabins():
    cabins = read_json('./scrappers/vacasa_cabins.json')
    return cabins

def insert_cabins():
    cabins = load_cabins()
    connection = psycopg2.connect(DATABASE_URI)
    tuples = []
    for c in cabins:
        idvrm = 'VACASA'
        id_ = idvrm + re.search(r'UnitID=(\d+)', c['url']).group(1)
        name = c['name']
        website = c['url']
        description = c['description']
        address = c.get('address', '')
        location = c.get('location', '')
        pattern = re.compile(r'(\d+) Bedroom')
        bedroom_matches = (pattern.match(f) for f in c['features'])
        bedrooms = next((mo.group(1) for mo in bedroom_matches if mo), '0')
        pattern = re.compile(r'Max Occupancy: (\d+)')
        occupancy_matches = (pattern.match(f) for f in c['features'])
        occupancy = next((mo.group(1) for mo in occupancy_matches if mo), '0')
        tuples.append((idvrm, id_, name, website, description, address, location, bedrooms, occupancy))
    # print(tuples)
    # unique_tuples = set(t for t in tuples)
    with connection, connection.cursor() as cursor:
        sql = '''UPDATE db.cabin SET status = 'INACTIVE' WHERE idvrm = 'VACASA' '''
        cursor.execute(sql)
        sql = """ INSERT INTO db.cabin (idvrm, id, name, website, description, address, location, 
            bedrooms, occupancy) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET name = excluded.name, 
            website = excluded.website, description = excluded.description, bedrooms = 
            excluded.bedrooms, occupancy = excluded.occupancy, status = excluded.status, location = excluded.location, address = excluded.address;"""
        # execute_values(cursor, sql, unique_tuples)
        for t in tuples:
            cursor.execute(sql, t)

def update_last_scrape():
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        c.execute("""INSERT INTO db.vrm (idvrm, name, website, ncabins, last_scrape)
            VALUES (%s, %s, %s, (select count(id) from db.cabin where idvrm = 'VACASA' and 
            status='ACTIVE'), now()) ON CONFLICT (idvrm) DO UPDATE SET name = excluded.name, 
            website = excluded.website, ncabins = (select count(id) from db.cabin where idvrm = 'VACASA' and 
            status='ACTIVE'), last_scrape = now()""", 
            ('VACASA', 'Vacasa', 'https://www.vacasa.com/'))
    connection.close()

def insert():
    connection = psycopg2.connect(DATABASE_URI)
    cabins = load_cabins()
    with connection, connection.cursor() as c:
        c.execute("""
            INSERT INTO db.vrm
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, ('VACASA', 'vacasa', 'https://www.vacasa.com/', len(cabins), dt.datetime.now()))
    insert_cabins()
    insert_features()
    insert_rates()
    connection.close()

def scrape_cabin_urls():
    url = 'https://www.vacasa.com/usa/Big-Bear/'
    base_url = 'https://www.vacasa.com/unit.php?UnitID='
    res = rq.get(url)
    html = res.text
    uid_index = html.find('UnitIDs')
    first_bracket = uid_index + html[uid_index:].find('[')
    last_bracket = uid_index + html[uid_index:].find(']]') #array of arrays
    l = eval(html[first_bracket: last_bracket+2]) #transform parsed array of arrays in a python list of lists
    ids = itertools.chain(*l)
    urls = [base_url + id for id in ids]
    return urls

def scrape_and_store_urls():
    urls = scrape_cabin_urls()
    with open('./scrappers/vacasa_urls.json', 'w', encoding='utf8') as f:
        json.dump(urls, f, indent=2)
    return urls



def scrape_cabins(filename='./scrappers/vacasa_cabins.json'):
    
    links = read_json('./scrappers/vacasa_cabin_urls.json')

    total   = len(links)
    index   = 0
    results = []

    try:
        begin = time.time()
        for r in crawl_cabins(links):
            if r is None: continue
            results.append(r)
            index += 1

            lapse = time.time() - begin
            print('Scraped! {} {}/{}'.format(r['name'], index, total))
            print('Time: {}'.format(lapse))
            print('--------------------')

            if lapse > 10:
                dump_from(filename, results)
                begin = time.time()
                print('Dumped!\n')

    except KeyboardInterrupt: pass
    finally:
        # Write finally result
        name = dump_from(filename, results)
        print('Dumped', name)    

def run():
    try:
        extract_cabin_urls_splinter()
        scrape_cabins()
        insert_cabins()
        insert_features()
        rate_scrapper_single_threaded()
        update_last_scrape()
    except Exception as e:
        print('Error running vacasa scrapper')
        raise(e)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./vacasa.py [FILENAME]')
        return

    filename = sys.argv[1]
    scrape_cabins(filename)


if __name__ == '__main__':
    main()
