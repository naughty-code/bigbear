#!/usr/bin/env python3

import requests as rq
import pandas as pd
import json
import datetime
from scrappers import util

from bs4 import BeautifulSoup
from collections import OrderedDict

OUTPUT_FILE = 'turnkey.json'

@util.ignore_errors
def get_quote(id, start_date, end_date, adults = 1, children = 0, pets=None):
    """not just the men but the woman and the children too"""
    #id is the same as UnitCode
    #date format moth_day_year
    start_date_str = '{}_{}_{}'.format(start_date.month,start_date.day,start_date.year) \
        if isinstance(start_date, datetime.date) else start_date
    end_date_str = '{}_{}_{}'.format(end_date.month, end_date.day, end_date.year) \
        if isinstance(end_date, datetime.date) else end_date
    data = {
        "propertyId": id,
        "startDate": start_date_str,
        "endDate": end_date_str,
        "adults": adults,
        "children": children
    }
    if pets: data['pets'] = pets
    res = rq.post('https://www.turnkeyvr.com/mainDataClient/getQuote', json=data)
    return res.json()

def extract_costs():
    cabins = []
    with open('turnkey.json') as f:
        cabins = json.load(f)
    ids = [ cabin['UnitCode'] for cabin in cabins ]
    return util.extract_costs(ids, get_quote)

def fix_booked():

    data = util.read_json(OUTPUT_FILE)
    for x in data:

        cl = x['CalendarObject']
        status = cl['DailyAvailability']
        start  = cl['CalendarStartDate']

        # I don't know man...
        dates = pd.date_range(start=start, periods=len(status))
        dates = dates.tolist()
        booked = [ d.strftime('%Y-%m-%d') \
                for s, d in zip(status, dates) if s == 'U' ]

        result = { 'id': x['UnitCode'], 'url': x['url'] }
        result['booked'] = booked

        yield result

def format_rate(cabin):

    row = OrderedDict()
    hds = util.get_holidays()

    for x in cabin:
        startDate = x['startDate']
        endDate   = x['endDate']
        if not util.is_holiday(hds, startDate, endDate):
            continue

        quote = x['quote']
        quote = quote.get('AmountBeforeTax')

        row['ID'] = x['id']
        row[startDate] = quote
        row[endDate]   = None

    return row

def fix_rates():

    RATES  = './turnkey_dt.json'
    cabins = util.read_json(RATES)
    for x in cabins:
        yield format_rate(x)

def main():
    res = rq.get('https://www.turnkeyvr.com/mainDataClient/getAllSearchProperties?lat=34.2438963&long=-116.91142150000002&radius=30')
    cabins = res.json()
    base_url = 'https://www.turnkeyvr.com/'
    for cabin in cabins:
        cabin['url'] = base_url + cabin['websiteUrl']
    with open(OUTPUT_FILE, 'w+', encoding='utf8') as f:
        json.dump(cabins, f, indent=4)

if __name__ == '__main__':
    main()
