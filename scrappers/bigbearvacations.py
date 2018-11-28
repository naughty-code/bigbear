import requests as rq
import json
from datetime import datetime

HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
}

def scrape_cabins():
    res = rq.post(
        'https://www.bigbearvacations.com/wp-admin/admin-ajax.php',
        params={
            'action':'streamlinecore-api-request',
            'params':'{"methodName":"GetPropertyListWordPress"}'
        },
        headers=HEADERS
    )
    return res.json()['data']['property']

def store_cabins(cabins):
    with open('./scrappers/bbv_cabins.json', 'w', encoding='utf8') as f:
        json.dump(cabins, f, indent=2)

def scrape_and_store_cabins():
    store_cabins(scrape_cabins())

def scrape_rates(start_date, end_date, holiday):
    start_str = start_date.strftime('%m/%d/%Y')
    end_str = end_date.strftime('%m/%d/%Y')
    res = rq.post(
        'https://www.bigbearvacations.com/wp-admin/admin-ajax.php',
        params={ 'action':'streamlinecore-api-request', 
        'params':'{"methodName":"GetPropertyAvailabilityWithRatesWordPress", "params": {"startdate":"'+start_str+'", "enddate":"'+end_str+'"}}'},
        headers=HEADERS
        )
    rates = [{**r, 'start_date': start_date, 'end_date': end_date, 'holiday': holiday } for r in res.json()['data']['available_properties']['property']]
    return rates


def db_format_rate(rate):
    id_ = rate['id']
    start_date = rate['start_date']
    end_date = rate['end_date']
    status = 'AVAILABLE'
    total = rate['total']
    holiday = rate['holiday']
    return (id_, start_date, end_date, status, total, holiday)
