#!/usr/bin/env python3
import datetime as dt
import requests as rq
import itertools
import re
import util
import json
import multiprocessing as mp
import os
import psycopg2

from bs4 import BeautifulSoup
from collections import OrderedDict

DATABASE_URL = os.environ['DATABASE_URL']
connection = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = connection.cursor()

HEADERS = {
    'accept-language': 'en',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
}

MONTHS = {
    'January':  1, 'February':  2, 'March':      3,
    'April':    4, 'May':       5, 'June':       6,
    'July':     7, 'August':    8, 'September':  9,
    'October': 10, 'November': 11, 'December':  12
}

def chain_iterable(it):
    return list(itertools.chain.from_iterable(it))

def parse_month(soup):

    header = soup.find('strong')
    title  = header.get_text(strip=True)

    match = re.search(r'(\w+) (\d+)', title)

    if match is None:
        raise('Date pattern not found!')

    name = match.group(1)
    year = match.group(2)

    month = MONTHS[name]

    return { 'month': month, 'year': int(year) }

def extract_booked(soup, dparams: dict):

    booked = soup.find_all('td', class_='booked')
    for d in booked:
        dparams['day'] = int(d.get_text(strip=True))
        yield dt.date(**dparams)

def extract_rates(soup, dparams: dict):

    available_days = soup.select('td > span')
    for d in available_days:

        dparams['day'] = int(d.get_text(strip=True))
        date = dt.date(**dparams)
        rate = d['title']

        yield { 'date': date, 'rate': rate }

def parse_calendar(soup):

    data = { 'booked': [], 'rates_per_day': [] }
    months = soup.select('#t-calendar .cal-container')

    booked = []
    rates  = []

    for m in months:
        date = parse_month(m)

        b = extract_booked(m, date)
        booked.append(b)

        r = extract_rates(m, date)
        rates.append(r)

    data['booked'] = chain_iterable(booked)
    data['rates_per_day'] = chain_iterable(rates)

    return data

def extract_data(soup):

    data = {}

    id_ = soup.find('input', { 'name': 'unitcode' })
    data['idvrm'] = '5STAR'
    data['id'] = '5STAR' + id_['value']
    data['name'] = soup.select('.panel-heading > h1')[0].find('span').previous_sibling.strip()
    data['description'] = ''
    for p in soup.select('.description p') :
        data['description'] = data['description'] + p.get_text()

    divs = soup.select('.col-md-2.col-sm-2.col-xs-2')
    data['occupancy'] = divs[0].div.h2.get_text()
    data['bedrooms'] = divs[1].div.h2.get_text()
    data['amenities'] = []
    for li in soup.select('.amenities-list li') :
        data['amenities'].append([ data['id'], li.get_text()])
    d_data = parse_calendar(soup)
    data.update(d_data)

    rates = soup.find(id='t-rates')
    table = rates.find('table')

    records = util.dict_from_table(table)
    data['rates'] = list(records)

    return data

def table_to_dict(table):
    dic = {}
    for tr in table.select('tr'):
        key, value = tr.stripped_strings
        dic[key] = value
    return dic

def get_quote(unit_code, start_date, end_date):
    data = {
        'formtype': 'details-datepicker',
        'page': 0,
        'unitcode': unit_code,
        'strCheckin': start_date,
        'strCheckout': end_date,
        'flexible_dates': 'No'
    }
    xhr = rq.post(
        'https://www.fivestarvacationrental.com/booking/api/EVRN_UnitStayRQ-detail-post.cfm',
        data=data,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
        }
    )

    soup = BeautifulSoup(xhr.text, 'html.parser')
    if soup.find('table'): 
        return table_to_dict(soup)

    return soup

def extract_costs():
    cabins = []
    with open('fivestar.json') as f:
        cabins = json.load(f)
    ids = [ cabin['id'] for cabin in cabins ]
    return util.extract_costs(ids, get_quote)

def format_rate(cabin):

    row = OrderedDict()
    hds = util.get_holidays()

    for x in cabin:
        startDate = x['startDate']
        endDate   = x['endDate']
        if not util.is_holiday(hds, startDate, endDate):
            continue

        quote = x['quote']
        quote = quote['Base Rate'] \
                if isinstance(quote, dict) else None

        row['ID'] = x['id']
        row[startDate] = quote
        row[endDate]   = None

    return row

def fix_rates():

    RATES  = './fivestar_dt.json'
    cabins = util.read_json(RATES)
    for x in cabins:
        yield format_rate(x)

def scrape_cabin(url):

    data = { 'url': url }
    resp = rq.get(url, headers=HEADERS)
    html = resp.text

    soup = BeautifulSoup(html, 'html.parser')
    info = extract_data(soup)
    data.update(info)

    # Fetch prices here
    return data

def scrape_all_cabins(urls):

    with mp.Pool(8) as p:
        yield from p.imap(scrape_cabin, urls)


def main():
    urls = []
    results = []
    amenities = []
    with open('fivestar-urls.json') as target:
        urls = json.load(target)
    cursor.execute('UPDATE db.vrm SET ncabins=' + str(len(urls)) + ', last_scrape=CURRENT_TIMESTAMP WHERE idvrm = \'5STAR\'')
    for r in scrape_all_cabins(urls):
        results.append(r)
        print(r.get('id'), len(r.get('booked', [])))

        str_sql = '''INSERT INTO db.cabin (idvrm, id, name, website, description, bedrooms, 
        occupancy) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET name = 
        excluded.name, website = excluded.website, description = excluded.description, bedrooms = 
        excluded.bedrooms, occupancy = excluded.occupancy;'''

        cabinInsert = [
            r.get('idvrm'), 
            r.get('id'), 
            r.get('name'), 
            r.get('url'), 
            r.get('description'), 
            int(r.get('bedrooms') or 0), 
            int(r.get('occupancy') or 0)
        ]

        cursor.execute(str_sql, cabinInsert)

        for amenity in r.get('amenities') :
            amenities.append(amenity)

    util.write_json('fivestar.json', results, indent=2, default=util.parse_dates)
    cursor.executemany("INSERT INTO db.features (id, amenity) VALUES (%s, %s) ON CONFLICT (id, amenity) DO NOTHING", amenities)
    connection.commit()
    cursor.close()
    connection.close()

if __name__ == '__main__':
    main()
