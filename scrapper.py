import os
import itertools
import psycopg2
from psycopg2.extras import RealDictCursor
from scrappers import destinationbigbear, vacasa, bigbearcoolcabins, bigbearvacations
from scrappers.util import print
from functools import partial

DATABASE_URI = os.environ.get('DATABASE_URL', None) or os.getenv('DATABASE_URI')

log_file = 'errors.log'

def log(e):
    with open(log_file, 'a', encoding='utf8') as f:
        f.write(str(e))

def run(scrappers_to_run):
    scrapers = [destinationbigbear, vacasa, bigbearcoolcabins, bigbearvacations]
    for scraper in scrapers:
        try:
            if 'ALL' in scrappers_to_run or scraper.db_id in scrappers_to_run:
                scraper.run()
        except Exception as e:
            print(e)
    print('scraping process finished')
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection, connection.cursor() as c:
        c.execute("UPDATE db.status_update SET status = 'Updated' WHERE id=1;")
    connection.close()

def get_category(amenities):
    categories = [
                    ['PLATINUM', { 'Hot Tub', 
                                'Pool/Game Room',
                                'WiFi',
                                'Pets',
                                'BBQ',
                                'TV/DVD/Cable',
                                'Kitchen/Dining',
                                'Dishwasher',
                                'Washer/Dryer',
                                'Sauna',
                                'Spa Tub',
                                'Bedding',
                                'TV in All Rooms',
                                'No Bunks/Sleepers',
                                'Master Suite Avail',
                                'Walk to Lake',
                                'Walk to Village',
                                'Walk to Ski',
                                'Lakefront',
                                'Log Home',
                                'Castle Glen',
                                'Eagle Point',
                                'Fox Farm',
                                'Village'
                    }],
                    ['GOLD', {   'Hot Tub', 
                                'Pool/Game Room',
                                'WiFi',
                                'Pets',
                                'BBQ',
                                'TV/DVD/Cable',
                                'Kitchen/Dining',
                                'Dishwasher',
                                'Washer/Dryer',
                                'Spa Tub',
                                'Walk to Lake',
                                'Walk to Village',
                                'Walk to Ski',
                                'Lakefront',
                                'Log Home',
                                'Castle Glen',
                                'Eagle Point',
                                'Fox Farm',
                                'Village'
                    }],
                    ['SILVER', { 'Hot Tub', 
                                'WiFi',
                                'Pets',
                                'BBQ',
                                'TV/DVD/Cable',
                                'Kitchen/Dining',
                                'Walk to Lake',
                                'Walk to Village',
                                'Walk to Ski',
                                'Bear City',
                                'Sugarloaf',
                                'Fawnskin',
                                'Moonridge'
                    }],
                    ['BRONZE', { 'Pets',
                                'BBQ',
                                'TV/DVD/Cable',
                                'Kitchen/Dining',
                                'Bear City',
                                'Sugarloaf',
                                'Fawnskin',
                                'Moonridge'
                    }]
    ]
    for category, cat_amenities in categories:
        if all(a in cat_amenities for a in amenities):
            return category
    return 'UNCLASSIFIED'                

def categorize_cabins():
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=psycopg2.extras.RealDictCursor)
    with connection, connection.cursor() as c:
        c.execute('SELECT * FROM db.cabin')
        cabins = c.fetchall()
        for cabin in cabins:
            c.execute('SELECT amenity from db.features WHERE id = %s', (cabin['id'],))
            amenities = c.fetchall()
            category =  get_category([a['amenity'] for a in amenities])
            c.execute('UPDATE db.features SET tier = %s WHERE id=%s', (category, cabin['id']))
        

def update_cabin_urls():
    destinationbigbear.scrape_cabin_urls()
    vacasa.extract_cabin_urls_splinter()
    bigbearcoolcabins.scrape_cabin_urls_and_store()

def scrape_and_insert_rates():
    destinationbigbear.scrape_rates_and_insert_faster()
    bigbearcoolcabins.extract_costs_and_insert()
    vacasa.rate_scrapper_single_threaded()
    bigbearvacations.scrape_and_insert_rates()

def scrape_cabins():
    destinationbigbear.scrape_cabins()
    vacasa.scrape_cabins()
    bigbearcoolcabins.scrape_cabins()
    bigbearvacations.scrape_and_store_cabins()

def update_database():
    bigbearcoolcabins.insert()
    vacasa.insert()

def insert_cabins():
    destinationbigbear.insert_cabins()
    vacasa.insert_cabins()
    bigbearcoolcabins.insert_cabins()
    bigbearvacations.insert_cabins(bigbearvacations.load_cabins())

def insert_amenities():
    destinationbigbear.insert_amenities()
    bigbearcoolcabins.insert_amenities()
    vacasa.insert_features()
    bigbearvacations.insert_amenities(bigbearvacations.load_cabins())

def update_last_scrape():
    destinationbigbear.update_last_scrape()
    bigbearcoolcabins.update_last_scrape()
    vacasa.update_last_scrape()
    bigbearvacations.update_last_scrape()

def update():
    update_cabin_urls()
    scrape_cabins()
    insert_cabins()
    scrape_and_insert_rates() # both scrape and insert rates
    insert_amenities()
    update_last_scrape()
    #update_database()

    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection, connection.cursor() as c:
        c.execute("UPDATE db.status_update SET status = 'Updated' WHERE id=1;")
    connection.close()

if __name__ == "__main__":
    update()



