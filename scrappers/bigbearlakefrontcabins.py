#!/usr/bin/env python3

import requests as rq 
import json
import datetime
from scrappers import util
import re
import os
import psycopg2
from bs4 import BeautifulSoup
from collections import OrderedDict

OUTPUT_FILE = 'bigbearlakefrontcabins.json'
DATABASE_URL = os.environ['DATABASE_URL']
connection = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = connection.cursor()
DATE_FORMAT = '%Y-%m-%d'

def get_params(form):
    dic = {}
    for i in form.select('input'):
        if i.has_attr('name') and i['name'] != '':
            dic[i['name']] = i['value']
    return dic

def string_from_date(date):
    return '{}-{}-{}'.format(date.year, date.month, date.day)

def get_quote(unit_code, start_date, end_date, adults=1, children=0, pets=0):
    """
        dates_and_guests format example:
        {
            start_date: '2018-09-24',
            end_date: '2018-09-27',
            guests: '2,0,0' #adults, children, pets
        }
    """
    start_date_str = string_from_date(start_date) \
        if isinstance(start_date, datetime.date) else start_date
    end_date_str = string_from_date(end_date) \
        if isinstance(end_date, datetime.date) else end_date
    xhr = rq.get(
        'https://bigbearlakefrontcabins.com/wp-admin/admin-ajax.php',
        params={
            'post_type': 'vacation_rental',
            'action': 'q4vr_stay',
            'unit_code': unit_code,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'guests': '{},{},{}'.format(adults, children, pets)
        }
    )
    soup = BeautifulSoup(xhr.json()['data'], 'html.parser')
    total_price_tag = soup.select_one('h5.total-price')
    if total_price_tag:
        return total_price_tag.get_text()
    return soup.prettify()

def extract_costs():
    cabins = []
    with open('bigbearlakefrontcabins.json') as f:
        cabins = json.load(f)
    ids = [ cabin['unit_code'] for cabin in cabins ]
    return util.extract_costs(ids, get_quote)

def fix_booked():

    data = util.read_json(OUTPUT_FILE)
    for d in data:
        data = { 'id': d.get('unit_code') }
        data['url'] = d.get('url')
        data['booked'] = d['calendar']['unavailable']
        yield data

def format_rate(cabin):

    row = OrderedDict()
    hds = util.get_holidays()

    for x in cabin:
        startDate = datetime.datetime.strptime(x['startDate'], DATE_FORMAT)
        endDate   = datetime.datetime.strptime(x['endDate'], DATE_FORMAT)
        if not util.is_holiday(hds, startDate, endDate):
            continue

        quote = x['quote']
        if not re.search(r'^\$\d', quote):
            quote = None

        row['ID'] = x['id']
        row[startDate] = quote
        row[endDate]   = None
    return row

def fix_rates():

    RATES = './bigbearlakefrontcabins_dt.json'
    cabins = util.read_json(RATES)

    for x in cabins:
        yield format_rate(x)

def scrape(html):
    s = BeautifulSoup(html, 'html.parser')
    tag = s.find('h2', class_='entry-title')
    [name, *location] = tag.stripped_strings if tag else ['', '']
    [bedrooms, baths, sleeps] = [h3.string for h3 in s.select('div > small + h3')]
    description = s.find(id='unit-description').get_text()
    id = 'BBLFC' + s.select_one('input#unitCode')['value']
    amenities = []
    for li in s.select('ul.amenities-list li') :
        amenities.append([ id, li.get_text()])

    return {
        'id' : id,
        'name': name,
        'location': location,
        'bedrooms': bedrooms,
        'sleeps': sleeps,
        'description': description,
        'amenities': amenities
    }

def scrape_all_fixed_content():
    results = []
    with open('bigbearlakefrontcabins-urls.json', encoding='utf8') as f:
        urls = json.load(f)
    
    cursor.execute('UPDATE db.vrm SET ncabins=' + str(len(urls)) + ', last_scrape=CURRENT_TIMESTAMP WHERE idvrm = \'BBLFC\'')
    cursor.execute('DELETE FROM db.cabin WHERE idvrm=\'BBLFC\'')

    for url in urls:
        res = rq.get(url)
        print(url)
        if not res.ok:
            print('not')
            continue
        r = scrape(res.text)
        results.append(r)
        with open('bigbearlakefrontcabins_cabins_fixed_info.json', 'w', encoding='utf8') as f:
            json.dump(results, f, indent=2)

        str_sql = '''INSERT INTO db.cabin (idvrm, id, name, website, description, bedrooms, 
        occupancy, location) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);'''
        cabinInsert = [
            'BBLFC', 
            r.get('id'), 
            r.get('name'), 
            url, 
            r.get('description'), 
            int(r.get('bedrooms') or 0), 
            int(r.get('sleep') or 0),
            r.get('location')
        ]

        cursor.execute(str_sql, cabinInsert)
        connection.commit()
    cursor.close()
    connection.close()

def scrape_urls():
    res = rq.get('https://bigbearlakefrontcabins.com/vacation_rentals?post_type=vacation_rental&s=&action=&unit_code=&start_date=&end_date=&guests=&filter%5B%5D=&filter%5B%5D=')
    s = BeautifulSoup(res.text, 'html.parser')
    urls = [a['href'] for a in s.select('div.card > div.unit-card-details + a')]
    with open('bigbearlakefrontcabins-urls.json', 'w', encoding='utf8') as f:
        json.dump(urls, f, indent=2)

def update_database():
    pass

def main():
    urls = []
    action = 'q4vr_calendar'
    extracted_data = []
    with open('bigbearlakefrontcabins_urls.json', 'r', encoding='utf8') as f:
        urls = json.load(f)

    soup = BeautifulSoup(rq.get(urls[0]).text, 'html.parser')

    for url in urls:
        res = rq.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        unit_code = soup.select_one('input#unitCode')['value']
        params = {
            'action': action,
            'unit_code': unit_code
        }
        xhr = rq.get(
            'https://bigbearlakefrontcabins.com/wp-admin/admin-ajax.php',
            params=params
        )
        calendar = json.loads(xhr.text)
        if calendar['success'] == True:
            print('calendar extracted successfully')

        else:
            print('task failed successfully')
        extracted_data.append(
            {'url': url, 'unit_code': unit_code, 'calendar': calendar['data']}
        )
        with open(OUTPUT_FILE, 'w+', encoding='utf8') as f:
            json.dump(extracted_data, f, indent=4)

if __name__ == '__main__':
    # main()
    scrape_urls()
    scrape_all_fixed_content()

