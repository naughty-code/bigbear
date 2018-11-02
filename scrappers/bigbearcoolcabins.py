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
import util

from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from calendar import month_name
from bs4 import BeautifulSoup
from psycopg2.extras import execute_values

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
    # Obviously this needs to be changed but not tonight fellas
    availabilities_weekends = get_availability_weekends_friday(_params['rcav[eid]'], unavailable_dates)
    availabilities_MLK = get_availability_MLK(_params['rcav[eid]'], unavailable_dates)
    availabilities_president = get_availability_president(_params['rcav[eid]'], unavailable_dates)
    availabilities_patrick = get_availability_patrick(_params['rcav[eid]'], unavailable_dates)
    availabilities_easter = get_availability_easter(_params['rcav[eid]'], unavailable_dates)
    availabilities_cincomayo = get_availability_cincomayo(_params['rcav[eid]'], unavailable_dates)
    availabilities_memorial = get_availability_memorial(_params['rcav[eid]'], unavailable_dates)
    availabilities_4july = get_availability_4july(_params['rcav[eid]'], unavailable_dates)
    availabilities_labor = get_availability_labor(_params['rcav[eid]'], unavailable_dates)
    availabilities_columbus = get_availability_columbus(_params['rcav[eid]'], unavailable_dates)
    availabilities_veterans = get_availability_veterans(_params['rcav[eid]'], unavailable_dates)
    availability_thanksgiving = get_availability_thanksgiving(_params['rcav[eid]'], unavailable_dates)
    availabilities_christmas = get_availability_christmas(_params['rcav[eid]'], unavailable_dates)

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
        'availabilities' :availabilities_weekends + availabilities_MLK + availabilities_president + availabilities_patrick + availabilities_easter + availabilities_cincomayo + availabilities_memorial + availabilities_4july + availabilities_labor + availabilities_columbus + availabilities_veterans + availability_thanksgiving + availabilities_christmas
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
def crawl_cabins(urls, N=4):

    with mp.Pool(N) as p:
        yield from p.imap_unordered(scrape_cabin, urls)

def insert_amenities(cabins):
    connection = psycopg2.connect(os.getenv('DATABASE_URL'))
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

def insert_cabins(cabins):
    connection = psycopg2.connect(os.getenv('DATABASE_URL'))
    insertCabins = []
    for cabin in cabins:
        id = 'BBCC' + cabin['_params']['rcav[eid]']
        name = cabin['name']
        url = cabin['url']
        description = html.escape(cabin['description'])
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
            str_sql = '''INSERT INTO db.cabin (id, name, website, description, location, bedrooms, occupancy,status, idvrm) VALUES %s ON CONFLICT (id) DO UPDATE SET name = 
                excluded.name, website = excluded.website, description = excluded.description, bedrooms = 
                excluded.bedrooms, occupancy = excluded.occupancy;'''
            execute_values(cursor, str_sql, insertCabins)
    connection.close()

def insert_availabilities(availabilities):
    connection = psycopg2.connect(os.getenv('DATABASE_URL'))
    insertAvailabilities = []
    for availability in availabilities:
        insertAvailabilities.append(availability)
    with connection:
        with connection.cursor() as cursor:
            str_sql = '''INSERT INTO db.availability (id, check_in, check_out, status, rate, name) VALUES %s ON CONFLICT (id, check_in, check_out, name) DO UPDATE SET rate = excluded.rate;'''
            execute_values(cursor, str_sql, insertAvailabilities)
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

def get_rates_multi(availabilities, N=4):
    with mp.Pool(N) as p:
        yield from p.imap_unordered(get_rates, availabilities)

def upload_to_database():
    with open('bbcc_cabin_urls.json') as f:
        cabins = json.load(f)
    insert_cabins(cabins)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./bigbearcoolcabins.py [FILENAME]')
        return

    filename = sys.argv[1]
    links = read_csv_cabins(filename)

    total   = len(links)
    index   = 0
    results = []

    availabilities = []

    try:
        for r in crawl_cabins(links):
            if r is None: continue
            results.append(r)
            index += 1
            print(f'Scraped! {r["name"]} {index}/{total}')
            for availability in r.get('availabilities') :
                availabilities.append(availability)
        new_availabilities = []
        total = len(availabilities)
        for gr in get_rates_multi(availabilities):
            index += 1
            new_availabilities.append(gr)
            print(f'Availability {index}/{total}')

    except KeyboardInterrupt: pass
    finally: 
        # Write finally result
        name = dump_from(filename, results)
        print('Dumped', name)
        upload_to_database()
        insert_availabilities(new_availabilities)

if __name__ == '__main__':
    main()

