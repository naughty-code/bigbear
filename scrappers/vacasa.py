#!/usr/bin/env python3

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
from scrappers import util
from scrappers import settings

from bs4 import BeautifulSoup
from urllib.parse import urlparse

# destinationbigbear -> dbb
# bigbearcoolcabins  -> bbc
# vacasa             -> vcs
# bigbearvacations   -> bbv
# Don't forget to handle exceptions

HEADERS = { 'accept-language': 'en', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36' }

DATE_FORMAT = '%Y/%m/%d'
OUTPUT_FILE = 'vacasa.json'
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
    elems = soup.find_all(class_='featured-amenity')
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

    calendar = extract_calendar(soup)
    data['availability'] = calendar

    rates = extract_rates(soup)
    data['rates'] = rates

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

    cabins = []
    with open('./scrappers/vacasa.json') as f:
        cabins = json.load(f)

    ids = []
    for cabin in cabins:
        parsed = urlparse(cabin['url'])
        key, value = parsed.query.split('=')
        ids.append(value)

    return util.extract_costs(ids, fetch_cost)

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
def crawl_cabins(urls, N=8):

    with mp.Pool(N) as p:
        yield from p.imap_unordered(scrape_cabin, urls)

def dump_from(filename, data):
    name = os.path.basename(filename)
    name = os.path.splitext(name)[0]
    name = '{}.json'.format(name)
    with open(name, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)

    return name

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

def insert_rates():
    rates = load_rates()
    flat_rates = list(itertools.chain(*rates))
    holidays = util.get_holidays_as_dict()
    tuples = []
    for rate in flat_rates:
        start = rate['startDate']
        end = rate['endDate']
        name = holidays.get((start, end), 'weekend')
        if rate['quote']['raw'].get('Error'):
            booked = 'BOOKED'
            q = 0
        else:
            booked = 'AVAILABLE'
            q = rate['quote']['raw']['1']['Total']
            id_ = 'VACASAListing #' + rate['quote']['raw']['1']['UnitID']
        tuples.append(id_, start, end, booked, q, name)
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        sql = """
            INSERT INTO db.availability VALUES %s
        """
        psycopg2.extras.execute_values(c, sql, tuples)


def scrape_cabin_urls():
    url = 'https://www.vacasa.com/usa/Big-Bear/'
    base_url = 'https://www.vacasa.com/unit.php?UnitID='
    res = rq.get(url)
    html = res.html
    uid_index = html.find('UnitIDs')
    first_bracket = uid_index + html[uid_index:].find('[')
    last_bracket = uid_index + html[uid_index:].find(']]') #array of arrays
    l = eval(html[first_bracket: last_bracket+2]) #transform parsed array of arrays in a python list of lists
    ids = itertools.chain(*l)
    urls = [base_url + id for id in ids]
    return urls

def scrape_and_store_urls():
    urls = scrape_cabin_urls()
    with open('vacasa_cabin_urls.json', 'w', encoding='utf8') as f:
        json.dump(urls, f, indent=2)



def scrape_cabins(filename='vacasa_cabins'):
    
    links = read_json('./scrappers/vacasa_urls.json')

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
    

def main():

    if len(sys.argv) != 2:
        print('Usage: ./vacasa.py [FILENAME]')
        return

    filename = sys.argv[1]
    scrape_cabins(filename)


if __name__ == '__main__':
    main()
