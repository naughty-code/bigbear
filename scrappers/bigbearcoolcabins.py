import pandas as pd
import multiprocessing as mp
import requests as rq
import os
import sys
import json
import psycopg2
import html
import re
import itertools
from decimal import Decimal
from scrappers import util

from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from calendar import month_name
from bs4 import BeautifulSoup
from psycopg2.extras import execute_values

BASE_URL = 'https://www.bigbearcoolcabins.com'
CABIN_URLS_FILE = './scrappers/bbcc_cabin_urls.json'

# Read step
def read_csv_cabins(filename):
    # Extract cabins website from csv
    df = pd.read_csv(filename)
    return df.Link

def load_cabins(filename='./scrappers/bbcc_cabins.json'):
    cabins = []
    with open(filename) as f:
        cabins = json.load(f)
    return cabins

# Output step
def dump_from(filename, data):
    #name = os.path.basename(filename)
    #name = os.path.splitext(name)[0]
    #name = f'{name}.json'
    with open(filename, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)
    return filename

def scrape_cabin_urls():
    base_url = 'https://www.bigbearcoolcabins.com'
    pagination_url = 'https://www.bigbearcoolcabins.com/big-bear-cabin-rentals?avail_filter%5Brcav%5D%5Bbegin%5D=&avail_filter%5Brcav%5D%5Bend%5D=&avail_filter%5Brcav%5D%5Bflex_type%5D=d&occ_total_numeric=&beds_numeric=&ldrc_location=All&sort_by=field_listing_sort_weight_value&items_per_page=50&page='
    urls = []
    for page_number in itertools.count():
        res = rq.get(pagination_url + str(page_number))
        soup = BeautifulSoup(res.text, 'html.parser')
        urls += (base_url + a['href'] for a in soup('a', text='View Details'))
        if soup(class_=['current last']):
            break
    return urls

def scrape_cabin_urls_and_store():
    urls = scrape_cabin_urls()
    dump_from(CABIN_URLS_FILE, urls)

def get_availability_weekends_friday(id, booked):
    availability = []
    today = datetime.now()
    friday = today + timedelta( (4-today.weekday()) % 7 )

    while friday.year == 2018:
        saturday = friday + timedelta(days=1)
        if (
            friday.strftime("%Y-%m-%d") not in booked
            and saturday.strftime("%Y-%m-%d") not in booked
        ):
            status = 'AVAILABLE'
        else:
            status = 'BOOKED'
        
        sunday = friday + timedelta(days=2)
        rate = '0'
        actual = [
            'BBCC' + id,
            friday.strftime("%Y-%m-%d"),
            sunday.strftime("%Y-%m-%d"),
            status,
            rate,
            'Weekend'
        ]
        availability.append(actual)
        friday = util.add_one_week(friday)
    return availability

def get_availability_MLK(id, booked):
    availability = []
    day1 = datetime(2018, 1, 12)
    day2 = datetime(2018, 1, 13)
    day3 = datetime(2018, 1, 14)

    if datetime.now() > day1:
        return []

    if (
        day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked
        and day3.strftime("%Y-%m-%d") not in booked
    ):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day3 + timedelta(days=1)
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'MLK Day'
    ]
    availability.append(actual)
    return availability

def get_availability_president(id, booked):
    availability = []
    day1 = datetime(2018, 2, 16)
    day2 = datetime(2018, 2, 19)
    if datetime.now() > day1:
        return []

    if (
        day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked
    ):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day2 + timedelta(days=1)
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'President\'s Day'
    ]
    availability.append(actual)
    return availability

def get_availability_patrick(id, booked):
    availability = []
    day = datetime(2018, 3, 16)
    if datetime.now() > day:
        return []

    if day.strftime("%Y-%m-%d") not in booked:
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day + timedelta(days=1)
    actual = [
        'BBCC' + id,
        day.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'St Patrick\'s Day'
    ]
    availability.append(actual)
    return availability

def get_availability_easter(id, booked):
    availability = []
    day1 = datetime(2018, 3, 30)
    day2 = datetime(2018, 3, 31)
    if datetime.now() > day1:
        return []

    if ( day1.strftime("%Y-%m-%d") not in booked 
        and day2.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day2 + timedelta(days=1)
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'Easter'
    ]
    availability.append(actual)
    return availability

def get_availability_cincomayo(id, booked):
    availability = []
    day = datetime(2018, 5, 4)
    if datetime.now() > day:
        return []

    if day.strftime("%Y-%m-%d") not in booked:
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day + timedelta(days=1)
    actual = [
        'BBCC' + id,
        day.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'Cinco de Mayo'
    ]
    availability.append(actual)
    return availability

def get_availability_memorial(id, booked):
    availability = []
    day1 = datetime(2018, 5, 25)
    day2 = datetime(2018, 5, 26)
    day3 = datetime(2018, 5, 27)
    if datetime.now() > day1:
        return []

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked
        and day3.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    nextday = day3 + timedelta(days=1)
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        nextday.strftime("%Y-%m-%d"),
        status,
        rate,
        'Memorial Day'
    ]
    availability.append(actual)
    return availability

def get_availability_4july(id, booked):
    availability = []
    day1 = datetime(2018, 7, 4)
    day2 = datetime(2018, 7, 7)
    if datetime.now() > day1:
        return []
    if day1.strftime("%Y-%m-%d") not in booked:
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        day2.strftime("%Y-%m-%d"),
        status,
        rate,
        '4th of July'
    ]
    availability.append(actual)
    return availability

def get_availability_labor(id, booked):
    availability = []
    day1 = datetime(2018, 8, 31)
    day2 = datetime(2018, 9, 1)
    day3 = datetime(2018, 9, 3)
    if datetime.now() > day1:
        return []

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked ):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        day3.strftime("%Y-%m-%d"),
        status,
        rate,
        'Labor Day'
    ]
    availability.append(actual)
    return availability

def get_availability_columbus(id, booked):
    availability = []
    day1 = datetime(2018, 10, 5)
    day2 = datetime(2018, 10, 6)
    day3 = datetime(2018, 10, 7)
    day4 = datetime(2018, 10, 8)
    if datetime.now() > day1:
        return []

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked 
        and day3.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        day4.strftime("%Y-%m-%d"),
        status,
        rate,
        'Columbus Day'
    ]
    availability.append(actual)
    return availability

def get_availability_veterans(id, booked):
    availability = []
    day1 = datetime(2018, 11, 9)
    day2 = datetime(2018, 11, 10)
    day3 = datetime(2018, 11, 11)
    day4 = datetime(2018, 11, 12)
    if datetime.now() > day1:
        return []

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked 
        and day3.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        day4.strftime("%Y-%m-%d"),
        status,
        rate,
        'Veteran\'s Day'
    ]
    availability.append(actual)
    return availability

def get_availability_thanksgiving(id, booked):
    availability = []
    day1 = datetime(2018, 11, 22)
    day2 = datetime(2018, 11, 23)
    day3 = datetime(2018, 11, 24)
    if datetime.now() > day1:
        return []

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked 
        and day3.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        day3.strftime("%Y-%m-%d"),
        status,
        rate,
        'Thanksgiving'
    ]
    availability.append(actual)
    return availability

def get_availability_christmas(id, booked):
    availability = []
    day1 = datetime(2018, 12, 21)
    day2 = datetime(2018, 12, 22)
    day3 = datetime(2018, 12, 23)
    day4 = datetime(2018, 12, 24)
    day5 = datetime(2018, 12, 25)
    day6 = datetime(2018, 12, 26)
    day7 = datetime(2018, 12, 27)
    day8 = datetime(2018, 12, 28)
    day9 = datetime(2018, 12, 29)
    day10 = datetime(2018, 12, 30)
    day11 = datetime(2018, 12, 31)
    day12 = datetime(2019, 1, 1)
    if datetime.now() > day1:
        return []

    if ( day1.strftime("%Y-%m-%d") not in booked
        and day2.strftime("%Y-%m-%d") not in booked 
        and day3.strftime("%Y-%m-%d") not in booked
        and day3.strftime("%Y-%m-%d") not in booked 
        and day4.strftime("%Y-%m-%d") not in booked
        and day5.strftime("%Y-%m-%d") not in booked 
        and day6.strftime("%Y-%m-%d") not in booked
        and day7.strftime("%Y-%m-%d") not in booked 
        and day8.strftime("%Y-%m-%d") not in booked
        and day9.strftime("%Y-%m-%d") not in booked 
        and day10.strftime("%Y-%m-%d") not in booked
        and day11.strftime("%Y-%m-%d") not in booked 
        and day12.strftime("%Y-%m-%d") not in booked):
        status = 'AVAILABLE'
    else:
        status = 'BOOKED'
    rate = '0'
    actual = [
        'BBCC' + id,
        day1.strftime("%Y-%m-%d"),
        day12.strftime("%Y-%m-%d"),
        status,
        rate,
        'Christmas Season'
    ]
    availability.append(actual)
    return availability



def get_quote(id_, start_date, end_date):
    """
        dates_and_guests format example:
        {
            start_date: '2018-09-24',
            end_date: '2018-09-27',
            guests: '2,0,0' #adults, children, pets
        }
    """
    start_date_str = start_date.strftime('%m-%d-%Y') \
        if isinstance(start_date, datetime) else start_date
    end_date_str = end_date.strftime('%m-%d-%Y') \
        if isinstance(end_date, datetime) else end_date
    xhr = rq.get(
        'https://www.bigbearcoolcabins.com/rescms/ajax/item/pricing/simple',
        params = {                        
            'rcav[begin]': start_date_str,  
            'rcav[end]': end_date_str,    
            'rcav[eid]': id_    
        }                                 
    )
    soup = BeautifulSoup(xhr.json()['content'])
    total_price_tag = soup.find(class_='rc-price')
    if total_price_tag:
        return total_price_tag.get_text()
    return soup.prettify()

def extract_costs():
    cabins = load_cabins()
    ids = [ cabin['_params']['rcav[eid]'] for cabin in cabins ]
    return util.extract_costs(ids, get_quote)


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
    
    _params = extract_form(html)
    #available
    #(PD: rates shouldn't be scrapped alongside the cabin info scrapper)
    #Obviously this needs to be changed but not tonight fellas 
    #availabilities_weekends = get_availability_weekends_friday(_params['rcav[eid]'], unavailable_dates)
    #availabilities_MLK = get_availability_MLK(_params['rcav[eid]'], unavailable_dates)
    #availabilities_president = get_availability_president(_params['rcav[eid]'], unavailable_dates)
    #availabilities_patrick = get_availability_patrick(_params['rcav[eid]'], unavailable_dates)
    #availabilities_easter = get_availability_easter(_params['rcav[eid]'], unavailable_dates)
    #availabilities_cincomayo = get_availability_cincomayo(_params['rcav[eid]'], unavailable_dates)
    #availabilities_memorial = get_availability_memorial(_params['rcav[eid]'], unavailable_dates)
    #availabilities_4july = get_availability_4july(_params['rcav[eid]'], unavailable_dates)
    #availabilities_labor = get_availability_labor(_params['rcav[eid]'], unavailable_dates)
    #availabilities_columbus = get_availability_columbus(_params['rcav[eid]'], unavailable_dates)
    #availabilities_veterans = get_availability_veterans(_params['rcav[eid]'], unavailable_dates)
    #availability_thanksgiving = get_availability_thanksgiving(_params['rcav[eid]'], unavailable_dates)
    #availabilities_christmas = get_availability_christmas(_params['rcav[eid]'], unavailable_dates)


    return {
        'name': page_title,
        'bedrooms': bedrooms,
        'bathrooms': bathrooms,
        'amenities': amenities,
        'sleeps': sleeps,
        'description': description,
        'amenities_section': amenities_dict,
        'unavailable_dates': unavailable_dates,
        'half_dates': half_dates,
        '_params': _params,
        #'availabilities': availabilities_weekends + availabilities_MLK + availabilities_president + availabilities_patrick + availabilities_easter + availabilities_cincomayo + availabilities_memorial + availabilities_4july + availabilities_labor + availabilities_columbus + availabilities_veterans + availability_thanksgiving + availabilities_christmas
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

        return data
    
    # Comment to debug better
    except Exception as e: print(e)
    except KeyboardInterrupt: pass

# Nothing to do here...
# Parallel step
def crawl_cabins(urls, N=8):

    with mp.Pool(N) as p:
        yield from p.imap_unordered(scrape_cabin, urls)

def insert_availabilities(availabilities):
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    insertAvailabilities = []
    for availability in availabilities:
        insertAvailabilities.append(availability)
    with connection:
        with connection.cursor() as cursor:
            str_sql = '''INSERT INTO db.availability (id, check_in, check_out, status, rate, name) VALUES %s ON CONFLICT (id, check_in, check_out, name) DO UPDATE SET rate = excluded.rate;'''
            execute_values(cursor, str_sql, insertAvailabilities)
    connection.close()

def load_rates():
    rates = []
    with open('scrappers/bbcc_quote_results.json', encoding='utf8') as f:
        rates = json.load(f)
    return list(itertools.chain(*rates));

def rate_to_tuple(rate):
    id_ = 'BBCC' + rate['id'] if 'BBCC' not in rate['id'] else rate['id']
    start = rate['startDate']
    end = rate['endDate']
    pattern = re.compile(r'\$(\d+,\d+|\d+)')
    mo = pattern.match(rate['quote']) 
    status = 'BOOKED' if not mo else 'AVAILABLE'
    pattern = re.compile(r'[^\d.]')
    rate_value = 0 if not mo else pattern.sub('', rate['quote'])
    name = rate['holiday']
    return (id_, start, end, status, rate_value, name)


def insert_rates_faster(rates):
    tupled_rates = [(r['id'], r['startDate'], r['endDate'], r['status'], r['quote'], r['holiday']) for r in rates]
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    with connection, connection.cursor() as cursor:
        str_sql = '''INSERT INTO db.availability (id, check_in, check_out, status, rate, name) 
            VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id, check_in, check_out, name) DO UPDATE SET id = EXCLUDED.id, 
            check_in = EXCLUDED.check_in, check_out = EXCLUDED.check_out, status = EXCLUDED.status,
            rate = (case when excluded.status = 'AVAILABLE' then excluded.rate else 
            db.availability.rate end), name = EXCLUDED.name'''
        for t in tupled_rates:
            cursor.execute(str_sql, t)
        # execute_values(cursor, str_sql, tupled_rates)
    connection.close()

def insert_rates(*args):
    rates = []
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    if len(args) == 0:
        rates = load_rates()
    elif len(args) == 1:
        rates = args[0]
    tupled_rates = [rate_to_tuple(r) for r in rates]
    with connection, connection.cursor() as cursor:
        str_sql = '''INSERT INTO db.availability (id, check_in, check_out, status, rate, name) 
                     VALUES %s 
                     ON CONFLICT DO UPDATE
                     SET id = EXCLUDED.id, check_in = EXCLUDED.check_in, check_out = EXCLUDED.check_out, status = EXCLUDED.status, rate = EXCLUDED.rate, name = EXCLUDED.name'''
        execute_values(cursor, str_sql, tupled_rates)
    connection.close()

def insert_amenities(cabins=None):
    if not cabins:
        cabins = load_cabins()
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    insertAmenities = []
    for cabin in cabins:
        id = cabin['_params']['rcav[eid]']
        amenities_section = ( f'{k}: {v}' if v else k for k,v in cabin['amenities_section'].items())
        amenities_section_res = []
        for am in amenities_section:
            amenities_section_res.append((am))
        data = cabin['amenities'] + amenities_section_res
        for d in data:
            insertAmenities.append(('BBCC' + id, d))
    with connection:
        with connection.cursor() as cursor:
            str_sql = '''INSERT INTO db.features (id, amenity)
                    VALUES %s
                    ON CONFLICT (id, amenity) DO NOTHING'''
            execute_values(cursor, str_sql, insertAmenities)
    connection.close()

def insert_cabins(cabins=None):
    if not cabins:
        cabins = load_cabins()
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    insertCabins = []
    for cabin in cabins:
        id = 'BBCC' + cabin['_params']['rcav[eid]']
        name = cabin['name']
        url = cabin['url']
        description = BeautifulSoup(cabin['description'], "html.parser").text
        location = cabin['amenities_section'].get('Area', '')
        bedrooms = re.match(r'\d+',cabin['bedrooms']).group()
        occupancy = re.search(r'\d+', cabin['sleeps']).group()
        insertCabins.append([
            id,
            name,
            url,
            description,
            location,
            bedrooms,
            occupancy,
            'ACTIVE',
            'BBCC'
        ])
    with connection:
        with connection.cursor() as cursor:
            str_sql = '''UPDATE db.cabin SET status = 'INACTIVE' WHERE idvrm = 'BBCC' '''
            cursor.execute(str_sql)
            str_sql = '''INSERT INTO db.cabin (id, name, website, description, location, bedrooms, 
                occupancy,status, idvrm) VALUES %s ON CONFLICT (id) DO UPDATE SET name = 
                excluded.name, website = excluded.website, description = excluded.description, 
                bedrooms = excluded.bedrooms, occupancy = excluded.occupancy, status = 
                excluded.status;'''
            execute_values(cursor, str_sql, insertCabins)
    connection.close()

def get_rates(availability):
    # availability
    url = 'https://www.bigbearcoolcabins.com/rescms/ajax/item/pricing/quote'
    url += '?rcav%5Bbegin%5D=' + datetime.strptime(availability[1], '%Y-%m-%d').strftime('%m/%d/%Y')
    url += '&rcav%5Bend%5D=' + datetime.strptime(availability[2], '%Y-%m-%d').strftime('%m/%d/%Y')
    url += '&rcav%5Beid%5D=' + availability[0][4:]

    try:
        if availability[3] == 'AVAILABLE': #status
            resp_hell = rq.get(url)
            resp_json = resp_hell.json()
            content = resp_json['content']
            content_soup = BeautifulSoup(content, 'html.parser')
            text = content_soup.select_one('.total').get_text(strip=True)[6:].replace(',', '')
            availability[4] = float(text)
    except:
        pass
    finally:
        return availability

def get_rates_multi(availabilities, N=8):
    with mp.Pool(N) as p:
        yield from p.imap_unordered(get_rates, availabilities)

def upload_to_database():
    cabins = load_cabins()
    insert_cabins(cabins)

def update_last_scrape():
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    with connection, connection.cursor() as c:
        c.execute("""INSERT INTO db.vrm (idvrm, name, website, ncabins, last_scrape)
            VALUES (%s, %s, %s, (select count(id) from db.cabin where idvrm = 'DBB' and 
            status='ACTIVE'), now()) ON CONFLICT (idvrm) DO UPDATE SET name = excluded.name, 
            website = excluded.website, ncabins = excluded.ncabins, last_scrape = 
            excluded.last_scrape""", ('BBCC', 'Big Bear Cool Cabins', 
            'https://www.bigbearcoolcabins.com'))
    connection.close()

def insert():
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    cabins = load_cabins()
    with connection, connection.cursor() as c:
        c.execute("""
            INSERT INTO db.vrm
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (idvrm) DO UPDATE SET name = excluded.name, website = excluded.website, ncabins = excluded.ncabins, last_scrape = excluded.last_scrape;
        """, ('BBCC', 'big bear cool cabins', 'https://www.bigbearcoolcabins.com', len(cabins), datetime.now()))
    connection.close()
    insert_cabins(cabins)
    insert_amenities(cabins)
    insert_rates()

def get_cabins_from_db(): #returns a dict with name of cabin as key and id as value
    data = {}
    connection = psycopg2.connect(os.getenv('DATABASE_URI'))
    with connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM db.cabin WHERE idvrm='BBCC'")
        for id, name in  cursor.fetchall():
            data[name] = id
    return data

def extract_costs_faster():
    return util.extract_costs_faster(extract_costs_faster_function)

def extract_costs_and_insert():
    cabin_name_to_id = get_cabins_from_db()
    cabin_ids = set(cabin_name_to_id.values())
    costs_with_ids = []
    for costs in extract_costs_faster():
        if not costs:
            continue
        start_date = costs[0]['startDate']
        end_date = costs[0]['endDate']
        holiday = costs[0]['holiday']
        print(f'scraping rate: start:{start_date}, end: {end_date}, holiday: {holiday}')
        for cost in costs: #inserting costs of found cabins
            cabin_id = cabin_name_to_id.get(cost['name'])
            if cabin_id:    
                costs_with_ids.append({'id': cabin_id, **cost})
        #inserting not found cabins
        ids_found = set(cabin_name_to_id[c['name']] for c in costs if cabin_name_to_id.get(c['name']))
        ids_not_found = cabin_ids - ids_found
        for id_ in ids_not_found:
            costs_with_ids.append({
                'id': id_,
                'startDate': start_date,
                'endDate': end_date,
                'quote': 0,
                'status': 'BOOKED',
                'holiday': holiday
            })
        insert_rates_faster(costs_with_ids)

def extract_costs_faster_function(range_tuple):
    (start, end, holiday) = range_tuple
    results = []
    url = 'https://www.bigbearcoolcabins.com/big-bear-cabin-rentals'
    params = {
        'avail_filter[rcav][begin]': start.strftime('%m/%d/%Y'),
        'avail_filter[rcav][end]': end.strftime('%m/%d/%Y'),
        'avail_filter[rcav][flex_type]': 'd',
        'ldrc_location': 'All',
        'items_per_page': 50
    }
    for page in itertools.count(1):
        params['page'] = page
        res = rq.get(url, params=params)
        soup = BeautifulSoup(res.text, 'html.parser')
        name_tags = soup(class_='rc-core-item-name')
        price_tags = soup(class_='rc-price')
        for name_tag, price_tag in zip(name_tags, price_tags):
            name = name_tag.get_text()
            price = Decimal(re.sub(r'[^\d.]', '', price_tag.get_text()))
            results.append({
                'startDate': start,
                'endDate': end,
                'name': name,
                'quote': price,
                'holiday': holiday,
                'status': 'AVAILABLE'
            })
        if soup(class_='current last') or page >= 8 or not name_tags:
            break
    return results
    
def scrape_cabins(filename='./scrappers/bbcc_cabins.js'):
    with open(CABIN_URLS_FILE) as f:
        links = json.load(f)

    total   = len(links)
    index   = 0
    results = []

    #availabilities = []

    try:
        for r in crawl_cabins(links):
            if r is None: continue
            results.append(r)
            index += 1
            print(f'Scraped! {r["name"]} {index}/{total}')
        #    for availability in r.get('availabilities') :
        #        availabilities.append(availability)
        #new_availabilities = []
        #total = len(availabilities)
        #for gr in get_rates_multi(availabilities):
        #    index += 1
        #    new_availabilities.append(gr)
        #    print(f'Availability {index}/{total}')

    except KeyboardInterrupt: pass
    finally: 
        # Write finally result
        name = dump_from(filename, results)
        print('Dumped', name)
        #upload_to_database()
        #insert_availabilities(new_availabilities)

def main():
    if len(sys.argv) != 2:
        print('Usage: ./bigbearcoolcabins.py [FILENAME]')
        return
    filename = sys.argv[1]
    scrape_cabins(filename)

if __name__ == '__main__':
    main()

