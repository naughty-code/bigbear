import pandas as pd
import sys
import requests as rq
import re
import json
import multiprocessing as mp
import datetime as dt
import os
import psycopg2
from psycopg2.extras import execute_values
import html
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

    return data

# First for destinationbigbear
def scrape_cabin(url):

    try:
        # First try, not so elegant
        # Request for html
        print('Scraping...') 
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

def update_database(cursor, cabins, amenities):
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

    # Update vrm ncabins and last_scrape
    cursor.execute('UPDATE db.vrm SET ncabins=' + str(len(cabins)) + ', last_scrape=CURRENT_TIMESTAMP WHERE idvrm = \'DBB\'')

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
        for r in crawl_cabins(links):
            if r["site_id"] is None: continue
            results.append(r)
            index += 1
            ncabins +=1
            print(f'Scraped! {r["name"]} {r["site_id"]} {index}/{total}')

            for amenity in r.get('amenities') :
                amenities.append(amenity)

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
            if index == 10:
                break

    except KeyboardInterrupt: pass
    finally: 
        # Write finally result
        name = dump_from(filename, results)
        print('Dumped', name)

        update_database(cursor, cabins, amenities)
        print('Database updated')
        connection.commit()
        cursor.close()
        connection.close()

if __name__ == '__main__':
    main()

