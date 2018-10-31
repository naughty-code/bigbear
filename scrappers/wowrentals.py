#!/usr/bin/env python3

import requests as rq
import datetime as dt
import pandas as pd
import json
import re
import multiprocessing as mp
import util
from bs4 import BeautifulSoup

HEADERS = {
    'accept-language': 'en',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
}

LODGIX_API  = 'https://www.lodgix.com/system/api-lite/xml'
DATE_FORMAT = '%Y-%m-%d'
OUTPUT_FILE = 'wowrentals.json'

def periods_to_dates(periods):

    if isinstance(periods, dict):
        periods = [periods]

    for p in periods:

        start = p['FromDate']
        end = p['ToDate']
        dates = pd.date_range(start, end)

        yield from dates.tolist()

def jsonp_dict(text):

    text = re.sub(r'^\w*\(', '', text)
    text = re.sub(r'\);$', '', text)
    return json.loads(text)

def fetch_booked(id_):

    params = {
        'Action': 'GetReservations',
        'PropertyOwnerID': 13341, # WoW Rentals
        'PropertyID': id_,
        'IncludeReservations': 'Separate',
        'FromDate': '2018-9-15',
        'ToDate': '2019-9-10',
        'JSONP': True,
        'jsoncallback': 'ng_jsonp_callback_1'
    }

    resp = rq.get(LODGIX_API, params=params)
    data = jsonp_dict(resp.text)

    periods = data['Response']['Results']\
            ['Reservations']['Reservation']

    return periods_to_dates(periods)

@util.ignore_errors
def fetch_cost(id_, start, end):

    if isinstance(start, dt.date):
        start = start.strftime(DATE_FORMAT)

    if isinstance(end, dt.date):
        end = end.strftime(DATE_FORMAT)

    params = {
        'Action': 'ReserveMulti',
        'PropertyOwnerID': 13341,
        'PropertyID': id_,
        'FromDate': start, # 2018-9-28
        'ToDate': end,     # 2018-9-30
        'adult': 1,
        'children': 0,
        'tax': None,
        'gift': None,
        'discount': None,
        'Costs': 'New',
        'JSONP': True,
        'jsoncallback': 'ng_jsonp_callback_15',
    }

    resp = rq.get(LODGIX_API, params=params, timeout=10)
    data = jsonp_dict(resp.text)

    if data['Response']['Errors']:
        return None

    costs = data['Response']['Results']\
            ['Costs']['Totals']

    total = costs['Total']
    return total

def fetch_property(id_):

    params = {
        'Action': 'GetPropertyOwner',
        'PropertyOwnerID': 13341,
        'PropertyID': id_,
        'SingleUnit': 'Yes',
        'JSONP': True,
        'jsoncallback': 'ng_jsonp_callback_0'
    }

    resp = rq.get(LODGIX_API, params=params)
    data = jsonp_dict(resp.text)

    if data['Response']['Errors']:
        return None

    prop = data['Response']['Results']\
            ['Properties']['Property']

    return prop

def extract_id(soup):

    elem = soup.find(id='booking')

    pattern = re.compile(r'properties/(\d+)')
    script = elem.find('script', string=pattern)

    match = pattern.search(script.string)
    id_ = match.group(1)

    return id_

def scrape_cabin(url):

    data = { 'url': url, 'errors': None }
    resp = rq.get(url, headers=HEADERS)

    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')

    try:
        id_  = extract_id(soup)
    except AttributeError:
        data['errors'] = 'No ID Found!'
        return data

    booked = fetch_booked(id_)

    data['url'] = url
    data['id'] = id_
    data['property'] = fetch_property(id_)
    data['booked'] = [ x.strftime(DATE_FORMAT) for x in booked ]

    return data

def extract_cabins(url):

    resp = rq.get(url, headers=HEADERS)
    html = resp.text

    soup = BeautifulSoup(html, 'html.parser')
    anchors = soup.select('li.project > a')
    cabins  = [ a['href'] for a in anchors ]

    return cabins

def scrape_all_cabins(urls):

    with mp.Pool(8) as p:
        yield from p.imap(scrape_cabin, urls)

def write_json(filename, data):
    with open(filename, 'w', encoding='utf8') as fp:
        json.dump(data, fp, indent=2)

def extract_costs():

    df  = pd.read_json(OUTPUT_FILE)
    ids = df.id.dropna()
    ids = ids.astype(int)
    ids = ids.tolist()

    return util.extract_costs(ids, fetch_cost)

def main():

    bb_url = 'https://wowrentals.com/big-bear-cabins/'

    cabins = extract_cabins(bb_url)
    print(len(cabins), 'cabins extracted!')

    results = []
    scraped = scrape_all_cabins(cabins)

    for r in scraped:
        results.append(r)
        print(r.get('id'), len(r.get('booked', [])))

    write_json('wowrentals.json', results)

if __name__ == '__main__':
    main()
