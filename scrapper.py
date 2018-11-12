import os
import itertools
import psycopg2
from psycopg2.extras import RealDictCursor
from scrappers import vacasa, bigbearcoolcabins

DATABASE_URI = os.environ['DATABASE_URL']

def update_cabin_urls():
    vacasa_cabin_urls = vacasa.scrape_and_store_urls()
    bbcc_cabin_urls = bigbearcoolcabins.scrape_cabin_urls_and_store()

def scrape_cabins():
    vacasa_cabins = vacasa.scrape_cabins()
    bbcc_cabins = bigbearcoolcabins.scrape_cabins()
    return vacasa_cabins + bbcc_cabins

def scrape_rates():
    vacasa_rates = [c for c in vacasa.extract_costs()]
    bbcc_rates = [c for c in bigbearcoolcabins.extract_costs()]
    return vacasa_rates + bbcc_rates

def update_database():
    bigbearcoolcabins.insert()
    vacasa.insert()

def update():
    scrape_cabins()
    scrape_rates()
    update_database()

    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    cursor = connection.cursor()
    with connection:
        cursor.execute("UPDATE db.status_update SET status = 'Updated' WHERE id=1;")

if __name__ == "__main__":
    update()



