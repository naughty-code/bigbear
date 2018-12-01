import requests as rq
import json
from scrappers import util
from psycopg2 import connect
from psycopg2.extras import execute_values
from datetime import datetime
from scrappers import settings
import os

DB_URI = os.getenv('DATABASE_URI')

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

def load_cabins():
    cabins = []
    with open('./scrappers/bbv_cabins.json', 'r', encoding='utf8') as f:
        cabins = json.load(f)
    return cabins

def scrape_and_store_cabins():
    store_cabins(scrape_cabins())

def get_cabins_from_db():
    cabins = []
    connection = connect(DB_URI)
    with connection, connection.cursor() as cursor:
        cursor.execute('SELECT * FROM db.cabin')
        cabins = cursor.fetchall() 
    return cabins

def scrape_and_insert_rates():
    cabin_ids = {id_ for [idvrm, id_,*rest] in get_cabins_from_db()}
    dates = util.get_date_ranges()
    for start, end, holiday in dates:
        results = scrape_rates(start, end, holiday)
        filtered_results = [r for r in results if r['id'] in cabin_ids]
        #process not found results
        found_ids = {r['id'] for r in filtered_results}
        not_found_ids = cabin_ids - found_ids
        for id_ in not_found_ids:
            filtered_results.append({'id': id_, 'start_date': start, 'end_date': end, 'status': 'BOOKED', 'total': 0, 'holiday': holiday})
        insert_rates(filtered_results)

def scrape_rates(start_date, end_date, holiday):
    start_str = start_date.strftime('%m/%d/%Y')
    end_str = end_date.strftime('%m/%d/%Y')
    res = rq.post(
        'https://www.bigbearvacations.com/wp-admin/admin-ajax.php',
        params={ 'action':'streamlinecore-api-request', 
        'params':'{"methodName":"GetPropertyAvailabilityWithRatesWordPress", "params": {"startdate":"'+start_str+'", "enddate":"'+end_str+'"}}'},
        headers=HEADERS
        )
    property_rates = res.json()['data']['available_properties']['property']
    rates = [{**r, 'start_date': start_date, 'end_date': end_date, 'holiday': holiday, 'id': 'BBV' + str(r['id']), 'status': 'AVAILABLE' } for r in property_rates]
    return rates


def db_format_rate(rate):
    id_ = rate['id']
    start_date = rate['start_date']
    end_date = rate['end_date']
    status = rate['status']
    total = rate['total']
    holiday = rate['holiday']
    return (id_, start_date, end_date, status, total, holiday)

def db_format_amenity(cabin):
    tuples = []
    id_ = 'BBV' + str(cabin['id'])
    for amenity in cabin['unit_amenities']['amenity']:
        amenity_name = amenity.get('amenity_name', '')
        tuples.append((id_, amenity_name))
    return tuples

def db_format_cabin(cabin):
    id_ = 'BBV' + str(cabin['id'])
    name = cabin['name']
    website = cabin.get('flyer_url', '') or ''
    description = cabin['short_description']
    address = f'{cabin.get("city", "")}, {cabin.get("neightborhood_name", "")}, {cabin.get("neightborhood_area_id","")}'
    location = cabin.get('city', '')
    bedrooms = cabin['bedrooms_number']
    occupancy = cabin['max_occupants']
    tier = cabin['condo_type_group_name'].upper()
    status = 'ACTIVE'
    return ('BBV', id_, name, website, description, address, location, bedrooms, occupancy, tier, status)

def insert_cabins(cabins):
    connection = connect(DB_URI)
    tuples = [db_format_cabin(c) for c in cabins]
    with connection, connection.cursor() as cursor:
        str_sql = '''UPDATE db.cabin SET status = 'INACTIVE' WHERE idvrm = 'DBB' '''
        cursor.execute(str_sql)
        # Update cabins
        str_sql = '''INSERT INTO db.cabin (idvrm, id, name, website, description, address, location, bedrooms, 
            occupancy, tier, status) VALUES %s ON CONFLICT (id) DO UPDATE SET 
            name = excluded.name, website = excluded.website, description = 
            excluded.description, bedrooms = excluded.bedrooms, occupancy = excluded.occupancy,
            address = excluded.address, status = excluded.status, location = excluded.location;'''
        execute_values(cursor, str_sql, tuples)
    connection.close()

def insert_amenities(cabins):
    tuples = [amenity for cabin in cabins for amenity in db_format_amenity(cabin)]
    # Update amenities
    connection = connect(DB_URI)
    with connection, connection.cursor() as cursor:
        str_sql = '''INSERT INTO db.features (id, amenity) VALUES %s ON CONFLICT (id, amenity) DO NOTHING'''
        execute_values(cursor, str_sql, tuples)
    connection.close()

def insert_rates(rates):
    tuples = set(db_format_rate(r) for r in rates)
    connection = connect(DB_URI)
    with connection, connection.cursor() as cursor:
        str_sql = '''INSERT INTO db.availability (id, check_in, check_out, status, rate, name) 
        VALUES %s ON CONFLICT (id, check_in, check_out, name) DO UPDATE SET id = EXCLUDED.id, 
        check_in = EXCLUDED.check_in, check_out = EXCLUDED.check_out, status = EXCLUDED.status,
        rate = (case when excluded.status = 'AVAILABLE' then excluded.rate else 
        db.availability.rate end), name = EXCLUDED.name'''
        execute_values(cursor, str_sql, tuples)

def scrape_and_insert():
    cabins = scrape_cabins()
    insert_cabins(cabins)
    insert_amenities(cabins)
    scrape_and_insert_rates()

def update_last_scrape():
    connection = connect(DB_URI)
    with connection, connection.cursor() as c:
        c.execute("""INSERT INTO db.vrm (idvrm, name, website, ncabins, last_scrape)
            VALUES (%s, %s, %s, (select count(id) from db.cabin where idvrm = 'DBB' and 
            status='ACTIVE'), now()) ON CONFLICT (idvrm) DO UPDATE SET name = excluded.name, 
            website = excluded.website, ncabins = excluded.ncabins, last_scrape = 
            excluded.last_scrape""", ('BBV', 'Big Bear Vacations', 
            'https://www.bigbearvacations.com/'))
    connection.close()