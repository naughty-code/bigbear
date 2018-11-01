#!/usr/bin/env python3

import datetime as dt
import requests as rq
import pandas as pd
import re
import json
import util
import multiprocessing as mp
import settings
import os
import psycopg2
import util

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
from functools import partial

BASE_URL = 'https://www.rsvacations.net'
HEADERS  = { 
    'accept-language': 'en', 
    'referer': BASE_URL,
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36' 
}

OUTPUT_FILE = 'rsvacations.json'

MONTHS = {
    'Jan':  1, 'Feb':  2, 'Mar':  3,
    'Apr':  4, 'May':  5, 'Jun':  6,
    'Jul':  7, 'Aug':  8, 'Sep':  9,
    'Oct': 10, 'Nov': 11, 'Dec': 12
}

DATE_FORMAT = '%m/%d/%Y'

def parse_month(soup):

    header = soup.find(class_='property-calendar-td-month')
    name   = header.get_text(strip=True)

    match = re.search(r'(\w+) - (\d+)', name)

    if match is None: 
        raise('Date pattern not found!')

    abbr = match.group(1)
    year = match.group(2)
    month = MONTHS[abbr]
    
    booked = soup.find_all('td', 
            style=re.compile(r'#FFCC66'))

    for d in booked:
        day = d.get_text(strip=True)
        yield dt.date(int(year), month, int(day))

def extract_booked(soup):

    months = soup.select('.outer-calendar-table')
    for m in months:
        yield from parse_month(m)

@util.ignore_errors
def fetch_cost(id_, start, end):

    if isinstance(start, dt.date):
        start = start.strftime(DATE_FORMAT)

    if isinstance(end, dt.date):
        end = end.strftime(DATE_FORMAT)

    RS_API = 'https://www.rsvacations.net/inc/api/webservices.aspx'
    params = {
        'method': 'instantquote',
        'AdminCustDataID': 11474, # Rsvacations
        'DynSiteID': 500, # I dunno
        'PageDataID': id_,
        'ad': start,
        'dd': end,
        'adults': 0,
        'children': 0,
        'checkAvailable': True,
        'LiveNetID': 0
    }

    resp = rq.get(RS_API, params=params, 
            headers=HEADERS, timeout=10)

    data = resp.json()
    return data

def extract_data(soup):
    
    data = {}

    # Cabin id
    id_ = soup.find('input', { 'name': 'PageDataID' })
    data['id'] = id_['value']

    data['name'] = soup.find('h1', {'class': 'property-page-title'}).string
    for tr in soup.select('tr.property-page-details-item'):
            key, value = (td.string for td in tr.select('td'))
            data[key] = value
    data['description'] = soup.select_one('h3.property-page-subtitle').string

    location = soup.find('strong', text='Location:')
    data['location'] = location.nextSibling if location else ''

    data['amenities'] = {}

    for strong in soup.select('#Amenities + div > strong'):
        if strong.next_sibling:

            data['amenities'][strong.string] = strong.next_sibling.string
        else:
            data['amenities'][strong.string] = ''

    booked = extract_booked(soup)
    data['booked'] = [ str(x) for x in booked ]

    return data

def extract_cabins(url, params={}):

    print(url)
    resp = rq.get(url, params=params, headers=HEADERS)
    html = resp.text

    # Duplicated
    soup = BeautifulSoup(html, 'html.parser')
    hrefs = set(a['href'] for a in soup.select('h4.property-list-title > a'))
    for href in hrefs:
        yield urljoin(BASE_URL, href)

def extract_all_cabins():

    params  = { 'cat': 3080, 'o': -1 }
    rentals = urljoin(BASE_URL, '/vacation-rentals-homes.asp?')

    for x in range(1, 3):
        params['page'] = x
        query = urlencode(params)
        url = '{}?{}'.format(rentals, query)
        yield from extract_cabins(url)

def scrape_cabin(url):

    data = { 'url': url }
    resp = rq.get(url, headers=HEADERS)
    html = resp.text

    soup = BeautifulSoup(html, 'html.parser')
    info = extract_data(soup)
    data.update(info)

    # Fetch prices here
    id_ = data['id']
    data['_price'] = fetch_cost(id_, '9/16/2018', '9/19/2018')

    return data

def write_json(filename, data):
    with open(filename, 'w', encoding='utf8') as fp:
        json.dump(data, fp, indent=2)

def extract_costs():

    df  = pd.read_json(OUTPUT_FILE)
    ids = df.id.tolist()
    return util.extract_costs(ids, fetch_cost)

def update_cabin_database_table(cabins):
    connection = psycopg2.connect(dsn=os.getenv('DATABASE_URL'), sslmode=os.getenv('DB_SSL_MODE'))
    with connection:
        with connection.cursor() as cursor:
            for cabin in cabins:
                address = cabin.get('address', '')
                cursor.execute("""
                INSERT INTO db.cabin (id, name, website, description, address, location, bedrooms, occupancy, tier, status, idvrm)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET name = excluded.name, website = excluded.website, description = excluded.description, address=excluded.address, location=excluded.location, bedrooms = excluded.bedrooms, occupancy = excluded.occupancy;
                """,
                (cabin['id'], cabin['name'][:100], cabin['url'][-100:], cabin['description'][:200], address,cabin['location'], cabin['Bedrooms'], cabin['Guests'], 'BRONZE', 'ACTIVE','rsvacations')
                )
    connection.close()

def update_amenities_database_table(cabins):
    connection = psycopg2.connect(dsn=os.getenv('DATABASE_URL'), sslmode=os.getenv('DB_SSL_MODE'))
    with connection:
        with connection.cursor() as cursor:
            for cabin in cabins:
                for key, value in cabin['amenities'].items():
                    cursor.execute("""
                    INSERT INTO db.features (id, amenity)
                    VALUES (%s, %s)
                    ON CONFLICT (id, amenity) DO NOTHING;
                    """,
                    (cabin['id'], f'{key}{value}'[:30])
                    )
    connection.close()


def load_cabins_and_update_database():
    cabins = util.read_json(OUTPUT_FILE)
    #update_cabin_database_table(cabins)
    update_amenities_database_table(cabins)


def scrape_and_update_database():
    scrape_and_store()
    load_cabins_and_update_database()

def scrape_and_store():
    results = []
    cabins = extract_all_cabins()
    for url in cabins:
        result = scrape_cabin(url)
        print('Cabin', result['id'], 'extracted!')
        results.append(result)
    write_json(OUTPUT_FILE, results)

def main():
    scrape_and_store()
"""
    with mp.Pool(8) as p:
        scraped = p.imap_unordered(scrape_cabin, cabins)
        for r in scraped:
            print('Cabin', r['id'], 'extracted!')
            results.append(r)
"""

if __name__ == '__main__':
    main()

