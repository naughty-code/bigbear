#!/usr/bin/env python3

import requests as rq
import pandas as pd
import json
import datetime
import util

from bs4 import BeautifulSoup
from collections import OrderedDict

OUTPUT_FILE = 'village.json'

def get_params(form):
    dic = {}
    for i in form.select('input'):
        if i.has_attr('name') and i['name'] != '' and i.has_attr('value'):
            dic[i['name']] = i['value']
    return dic

def string_from_date(date):
    return '{}/{}/{}'.format(date.month, date.day, date.year)

@util.ignore_errors
def get_quote(id, start_date, end_date, occupants=1, occupants_small=0, pets=0):
    #date formats month/day/year
    #occupants_small: children
    start_date_str = string_from_date(start_date) \
        if isinstance(start_date, datetime.date) else start_date
    end_date_str = string_from_date(end_date) \
        if isinstance(end_date, datetime.date) else end_date
    data = {
        "methodName":"GetPreReservationPrice",
        "params":{
            "unit_id": id,
            "startdate": start_date_str,
            "enddate": end_date_str,
            "occupants": occupants,
            "occupants_small": occupants_small,
            "pets": pets,
            "company_code":"ae6f4537f6e81a7b3af1e815f5bd594"
        }
    }
    res = rq.post('https://web.streamlinevrs.com/api/json', json=data)
    return res.json()['data']

def extract_costs():
    cabins = []
    with open('village.json') as f:
        cabins = json.load(f)
    ids = [ cabin['id'] for cabin in cabins ]
    return util.extract_costs(ids, get_quote)

def fix_booked():

    def expand_periods(period):

        if not period: return
        if isinstance(period, dict):
            period = [ period ]

        for p in period:
            start = p['startdate']
            end = p['enddate']
            rg = pd.date_range(start=start, end=end)
            rg = rg.map(lambda x: x.strftime('%Y-%m-%d'))

            yield from rg.tolist()

    data = util.read_json(OUTPUT_FILE)
    for d in data:
        period = d['blocked_period']
        data = { 'id': d['id'], 'url': d['url:'] } # NICE!
        data['booked'] = list(expand_periods(period))
        yield data

def format_rate(cabin):

    row = OrderedDict()
    hds = util.get_holidays()

    for x in cabin:
        startDate = x['startDate']
        endDate   = x['endDate']
        if not util.is_holiday(hds, startDate, endDate):
            continue

        quote = x['quote']
        quote = quote.get('price')

        row['ID'] = x['id']
        row[startDate] = quote
        row[endDate]   = None

    return row

def fix_rates():

    RATES  = './village_dt.json'
    cabins = util.read_json(RATES)
    for x in cabins:
        yield format_rate(x)

def main():
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
    }
    urls = []
    scraped = []
    with open('villagereservations-urls.json', 'r', encoding='utf8') as f:
        urls = json.load(f)
    for url in urls:
        res = rq.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        form = soup.select_one('form#resortpro_form_checkout')
        params = get_params(form)
        id = params['book_unit']
        data = {
            "methodName":"GetPropertyAvailabilityCalendarRawData",
            "params":{
                "unit_id":id,"company_code":"ae6f4537f6e81a7b3af1e815f5bd594"
            }
        }
        xhr = rq.post('https://web.streamlinevrs.com/api/json', json=data)

        scraped.append({
            'id': id,
            'url:': url,
            **xhr.json()['data']
        })
        with open(OUTPUT_FILE, 'w+', encoding='utf8') as f:
            json.dump(scraped, f, indent=4)

if __name__ == '__main__':
    main()
