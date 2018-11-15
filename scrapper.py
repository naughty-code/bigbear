import os
import itertools
import psycopg2
from psycopg2.extras import RealDictCursor
from scrappers import vacasa, bigbearcoolcabins

DATABASE_URI = os.environ.get('DATABASE_URL', None) or os.getenv('DATABASE_URI')

def update_cabin_urls():
    vacasa_cabin_urls = vacasa.scrape_and_store_urls()
    bbcc_cabin_urls = bigbearcoolcabins.scrape_cabin_urls_and_store()

def scrape_rates():
    bigbearcoolcabins.extract_costs_and_insert()
    for rate in vacasa.extract_costs():
        print('----------checkpoint------------')
        vacasa.insert_rates(rate)


def scrape_cabins():
    vacasa_cabins = vacasa.scrape_cabins()
    bbcc_cabins = bigbearcoolcabins.scrape_cabins()
    return vacasa_cabins + bbcc_cabins

def update_database():
    bigbearcoolcabins.insert()
    vacasa.insert()

def insert_cabins():
    vacasa.insert_cabins()
    bigbearcoolcabins.insert_cabins()

def insert_amenities():
    bigbearcoolcabins.insert_amenities()
    vacasa.insert_features()


def update():
    scrape_cabins()
    insert_cabins()
    scrape_rates()
    bigbearcoolcabins.update_last_scrape()
    vacasa.update_last_scrape()
    insert_amenities()
    #update_database()

    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    cursor = connection.cursor()
    with connection:
        cursor.execute("UPDATE db.status_update SET status = 'Updated' WHERE id=1;")

if __name__ == "__main__":
    update()



