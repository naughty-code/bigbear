#!/usr/bin/env python3

import pandas as pd
import multiprocessing as mp
import requests as rq
import os
import sys
import json
import psycopg2
import html
from scrappers import settings
import re
import itertools

from urllib.parse import urljoin
from datetime import date, datetime
from calendar import month_name
from bs4 import BeautifulSoup
from psycopg2.extras import execute_batch

BASE_URL = 'https://www.bigbearcoolcabins.com'

# Read step
def read_csv_cabins(filename):
    # Extract cabins website from csv
    df = pd.read_csv(filename)
    return df.Link

# Output step
def dump_from(filename, data):
    name = os.path.basename(filename)
    name = os.path.splitext(name)[0]
    name = f'{name}.json'
    with open(name, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)
    return name

# Parse step
def parse_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    page_title = soup.find('h1', id='page-title').get_text()
    bedrooms = soup.find('div', class_='rc-lodging-beds rc-lodging-detail').get_text()
    bathrooms = soup.find('div', class_='rc-lodging-baths rc-lodging-detail').get_text()
    #amenities
    ams1 = soup.select('div.view-vr-listing-featured-amenities > div.view-content > ul > li')
    amenities_list = [list_elem.get_text(strip=True) for list_elem in ams1]
    ams2 = soup.select_one('div.field-name-field-vr-extra-featured-amenitie')
    amenities_br = [ amenity for amenity in ams2.stripped_strings ] \
            if ams2 else []

    amenities = [*amenities_list, *amenities_br]
    sleeps = soup.find('div', class_='rc-lodging-occ rc-lodging-detail').get_text()
    #description
    description = soup.select_one('div.content > div.field-name-body').get_text('\n\n', strip=True)
    #more amenities (from amenities tab)
    amenities_tab = soup.select('div.item-list > ul li')
    amenities_dict = {}
    for amen_li_elem in amenities_tab:
        k, *v = amen_li_elem.stripped_strings
        amenities_dict[k] = v[0] if v else None
    #calendars
    month_num = {name: num for num, name in enumerate(month_name)}
    unavailable_dates = []
    cals = soup.find_all('table', class_='rc-calendar rcav-month')
    half_dates = []
    for cal in cals:
        caption, dayname_row, *daynum_rows = cal
        month, year = caption.get_text().split()
        for daynum_row in daynum_rows:
            for daynum in daynum_row:
                if not daynum.has_attr('colspan'):
                    unavailable = 'av-X' in daynum['class']
                    day = int(daynum.get_text())
                    year = int(year)    
                    if unavailable:
                        unavailable_dates.append(str(date(year, month_num[month], day)))
                    availability_type = None
                    if 'av-IN' in daynum['class']:
                        availability_type = 'av-IN'
                    elif 'av-OUT' in daynum['class']:
                        availability_type = 'av-OUT'
                    if availability_type:
                        half_dates.append({
                            'date': str(date(year, month_num[month], day)),
                            'available': availability_type
                        })

    #reviews section tab
    #rating
    rating_span = soup.find('span', class_='rating-d')
    average_rating = ' '.join(rating_span.stripped_strings) \
            if rating_span else ''

    #reviews
    reviews = soup.select('div.budy-review-container > div.body-review')
    review_data = []
    for review in reviews:
        review_title = review.h3.get_text()
        rating = ' '.join(review.span.stripped_strings)
        review_text = review.find('p', class_='review_text').get_text()
        review_heading_span = review.find('p', class_='review-heading-span').get_text()
        review_data.append({
            'title': review_title,
            'rating': rating,
            'text': review_text,
            'heading': review_heading_span
        })

    return {
        'name': page_title,
        'bedrooms': bedrooms,
        'bathrooms': bathrooms,
        'amenities': amenities,
        'sleeps': sleeps,
        'description': description,
        'amenities_section': amenities_dict,
        'unavailable_dates': unavailable_dates,
        'half_dates': half_dates

    }

    #raise NotImplementedError('Oops! He did it again...')

# Params
# rcav[begin]: 09/08/2018
# rcav[end]: 09/09/2018
# rcav[flex_type]: d
# rcav[eid]: 68
# form_build_id: form-Q4Et3fAn4plrcoqWJl6WysA4Fbu5AqrYdPXJnw8rGbg
# form_id: rc_core_item_avail_form
# url: 

def extract_cabins(soup):

    divs = soup.select('#page-content div.view-content > div')

    for div in divs:
        anchor = div.select_one('h3 > a')
        if not anchor: continue 

        yield { 
            'name': anchor.get_text(strip=True), 
            'url': anchor['href'] 
        }

def fetch_cabins():

    url = urljoin(BASE_URL, '/big-bear-cabin-rentals?items_per_page=50')
    while True:

        resp = rq.get(url)
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        yield from extract_cabins(soup)

        # Pagination
        next_ = soup.select_one('li.current + li > a')
        if not next_: break

        href = next_.get('href')
        url  = urljoin(BASE_URL, href)

def extract_form(html):

    soup = BeautifulSoup(html, 'html.parser')
    form = soup.find(id='rc-core-item-avail-form')
    inputs = form.find_all('input')
    return { x.get('name'): x.get('value') for x in inputs }

# Date format %m/%d/%Y
def fetch_rate(begin, end, params):

    params['rcav[begin]'] = begin
    params['rcav[end]']   = end

    url = urljoin(BASE_URL, '/rescms/ajax/item/pricing/simple')
    resp = rq.get(url, params=params)

    data = resp.json()
    html = data['content']

    soup  = BeautifulSoup(html, 'html.parser')
    price = soup.find(class_='rc-price')

    return price.get_text(strip=True) if price else None

# Scrape step
def scrape_cabin(url):

    try:
        # First try, not so elegant
        # Request for html
        print('Scraping...') 
        resp = rq.get(url)
        html = resp.text # raise for status

        data = parse_data(html)
        data['url'] = url
        data['_params'] = extract_form(html)

        return data
    
    # Comment to debug better
    except Exception as e: print(e)
    except KeyboardInterrupt: pass

# Nothing to do here...
# Parallel step
def crawl_cabins(urls, N=8):

    with mp.Pool(N) as p:
        yield from p.imap_unordered(scrape_cabin, urls)

def insert_amenities(cabins):
    connection = psycopg2.connect(os.getenv('DATABASE_URL'), sslmode=os.getenv('DB_SSL_MODE'))
    with connection:
        with connection.cursor() as cursor:
            for cabin in cabins:
                id = cabin['_params']['rcav[eid]']
                amenities_section = ( f'{k}: {v}' if v else k for k,v in cabin['amenities_section'].items())
                data = ((id, amenity) for amenity in itertools.chain(cabin['amenities'], amenities_section))
                execute_batch(
                        cursor,
                        """INSERT INTO db.features (id, amenity)
                            VALUES (%s, %s)
                            ON CONFLICT (id, amenity) DO NOTHING
                        """,
                        data,
                        page_size=10000
                    )
    connection.close()

def insert_cabins(cabins):
    connection = psycopg2.connect(os.getenv('DATABASE_URL'), sslmode=os.getenv('DB_SSL_MODE'))
    with connection:
        with connection.cursor() as cursor:
            for cabin in cabins:
                id = cabin['_params']['rcav[eid]']
                name = cabin['name']
                url = cabin['url']
                description = html.escape(cabin['description'])
                address = ''
                location = cabin['amenities_section'].get('Area', '')
                bedrooms = re.match(r'\d+',cabin['bedrooms']).group()
                occupancy = re.search(r'\d+', cabin['sleeps']).group()
                cursor.execute(
                    """INSERT INTO db.cabin (id, name, website, description, location, bedrooms, occupancy,status, idvrm)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, 
                    (id, name, url, description, location, bedrooms, occupancy, 'ACTIVE', 'BBCC')
                )
    connection.close()

def insert_rates(rates):
    pass

def upload_to_database():
    with open('bbcc_cabin_urls.json') as f:
        cabins = json.load(f)
    connection = psycopg2.connect(os.getenv('DATABASE_URL'), sslmode=os.getenv('DB_SSL_MODE'))
    connection.close()
    insert_cabins(cabins)
    insert_amenities(cabins)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./bigbearcoolcabins.py [FILENAME]')
        return

    filename = sys.argv[1]
    links = read_csv_cabins(filename)

    total   = len(links)
    index   = 0
    results = []

    try:
        for r in crawl_cabins(links):
            if r is None: continue
            results.append(r)
            index += 1
            print(f'Scraped! {r["name"]} {index}/{total}')
            dump_from(filename, results)

    except KeyboardInterrupt: pass
    finally: 
        # Write finally result
        name = dump_from(filename, results)
        print('Dumped', name)

if __name__ == '__main__':
    main()

