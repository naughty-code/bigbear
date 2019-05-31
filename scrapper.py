import os
import settings
import itertools
import psycopg2
from psycopg2.extras import RealDictCursor
from scrappers import destinationbigbear, vacasa, bigbearcoolcabins, bigbearvacations
from scrappers.util import print
from functools import partial

scraper_modules = [destinationbigbear, vacasa, bigbearcoolcabins, bigbearvacations]

DATABASE_URI = os.environ.get('DATABASE_URL', None) or os.getenv('DATABASE_URI')

log_file = 'errors.log'

def log(e):
    with open(log_file, 'a', encoding='utf8') as f:
        f.write(str(e))

def run(scrappers_to_run):
    for scraper in scraper_modules:
        try:
            if 'ALL' in scrappers_to_run or scraper.db_id in scrappers_to_run:
                scraper.run()
        except Exception as e:
            print(e)
    print('scraping process finished')
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    categorize_cabins()
    with connection, connection.cursor() as c:
        c.execute("UPDATE db.status_update SET status = 'Updated' WHERE id=1;")
    connection.close()

def get_category(cabin_amenities, vrm):
    categories = [
                    ['PLATINUM', {
                                'BBV': {
                                    'SPA/Hot Tub/Jacuzzi', 
                                    'Games',
                                    'WiFi/Internet',
                                    'Dishwasher',
                                    'Washer/Dryer',
                                    'Sauna',
                                    #'Spa Tub', #possible conflict with SPA/Hot Tub/Jacuzzi
                                    #'Bedding',
                                    #'TV in All Rooms',
                                    #'No Bunks/Sleepers',
                                    #'Master Suite Avail',
                                },
                                'BBCC': {                                    
                                    'Hot Tub'
                                },
                                'DBB': {
                                    'Hot Tub: Yes',
                                    'Spa Jacurzzi: Yes'
                                },
                                'VACASA':{
                                    'Hot tub :Private'
                                }
                    }],
                    ['GOLD', {
                            'BBV': {  'SPA/Hot Tub/Jacuzzi', 
                                'Games',
                                'WiFi/Internet',
                                'Dishwasher',
                                'Washer/Dryer',
                                #'Spa Tub', #possible conflict with SPA/Hot Tub/Jacuzzi
                            },
                            'BBCC': {
                                'Dock',
                                'Fenced Yard',
                                'Fireplace',
                                'Internet',
                                'Lakefront',
                                'Lakeviews',
                                'Walking Distance to Lake'
                            },
                            'DBB': {
                                'Fireplace',
                                'Water Front'
                            },
                            'VACASA': {
                                'Dock',
                                'Fireplace',
                                'Waterfront'
                            }
                    }],
                    ['SILVER', {
                                'BBV': { 
                                    'SPA/Hot Tub/Jacuzzi', 
                                    'WiFi/Internet',
                                },
                                'BBCC': {
                                    'Game Room',
                                    'Foosball',
                                    'Pool Table',
                                    'WiFi',
                                    'Wood Burning Fireplace'
                                },
                                'DBB': {
                                    'Internet: Yes',
                                    'Parking'
                                },
                                'VACASA':{
                                    'Foosball Table',
                                    'Internet',
                                    'Wood-burning fireplace'
                                }
                    }],
                    ['BRONZE', {
                        'BBV': {
                            #'PETS',
                            #'BBQ',
                            #'TV/DVD/Cable',
                            #'Kitchen/Dining',
                        },
                        'BBCC': {},
                        'DBB': {},
                        'VACASA': {}
                    }]
    ]
    #print(f'cabin_amenities: {cabin_amenities}')
    for category, cat_amenities in categories:
        match_count = sum(1 for cat_amenity in cat_amenities[vrm] if cat_amenity in cabin_amenities)
        if  match_count >= 3 or match_count == len(cat_amenities):
            return category
    return 'BRONZE'                

def categorize_cabins():
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=psycopg2.extras.RealDictCursor)
    with connection, connection.cursor() as c:
        c.execute("SELECT * FROM db.cabin WHERE status = 'ACTIVE' and id not like 'BBV%'")
        cabins = c.fetchall()
        for cabin in cabins:
            c.execute('SELECT amenity from db.features WHERE id = %s', (cabin['id'],))
            amenities = c.fetchall()
            amenities_list = [a['amenity'] for a in amenities]
            category = get_category(amenities_list)
            if not amenities_list:
                print(f'cabin without amenities - id:{cabin["id"]}, category: {category}, url:{cabin["website"]}')
            c.execute('UPDATE db.cabin SET tier = %s WHERE id=%s', (category, cabin['id']))


#def categorize_cabins_from_json():
#    bbv_cabins = bigbearvacations.load_cabins()
#    bbcc_cabins = bigbearcoolcabins.load_cabins()
#    dbb_cabins = destinationbigbear.load_cabins()
#    vacasa_cabins = vacasa.load_cabins()
#    for c in bbcc_cabins:

        

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



