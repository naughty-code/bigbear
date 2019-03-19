from shapely.geometry.polygon import Polygon
from psycopg2.extras import RealDictCursor
from shapely.geometry import Point
import requests as rq
import psycopg2
import json
import re
import os

HEADERS = {'user-agent': 
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'}

'''polygon = Polygon(moonridge)
point = Point(34.245384, -116.828366)
point.within(polygon)


geolocator = Nominatim(user_agent="BigBear")
location = geolocator.reverse(lat, lon)
address = location.address'''

DATABASE_URI = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URI')

def failsafe(func):
	def wrapper(*args, **kwargs):
		retry = 2
		fail = True
		result = None
		for x in range(retry):
			try:
				result = func(*args, **kwargs)
				break;
			except Exception as e:
				print(e)
				print('Retrying')
		return result
	return wrapper

def load_polygons(file='polygons.json'):
	with open(file,'r') as f:
		locations = json.load(f)
	keys = locations.keys()
	polygons = {}
	for key in keys:
		polygons[key] = Polygon(locations[key])
	return polygons

def location_extract(lat,lon):
	locations = load_polygons()

	if lat and lon:
		point = Point(lat, lon)
		keys = locations.keys()
		for key in keys: 
			if point.within(locations[key]): return key
	return None

def BBV_address_extract(html):
	match = re.search(r'"streetAddress":[\s]*"([^"]+)',html)
	street = match.group(1) if match else None
	match = re.search(r'"postalCode":[\s]*"([^"]+)',html)
	postal = match.group(1) if match else None
	address = f'{street}, {postal}' if street and postal else street
	return address

def BBV_lat_lon_extract(html):
	match = re.search(r'"latitude":[\s]*([^,]+)',html)
	lat = float(match.group(1).strip().replace('"','')) if match else None
	match = re.search(r'"longitude":[\s]*([^}|^,]+)',html)
	lon = float(match.group(1).strip().replace('"','')) if match else None
	return lat, lon

@failsafe
def BBV_location_address(url):
	res = rq.get(url,headers=HEADERS)
	address = ''
	location = ''
	if res.ok:
		address = BBV_address_extract(res.text)
		lat, lon = BBV_lat_lon_extract(res.text)
		location = location_extract(lat,lon)
	return address, location

@failsafe
def updateall(address,location,idd):
	connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
	cursor = connection.cursor()
	cursor.execute(f"update db.cabin as cabin set address = '{address}', location = '{location}' where id = '{idd}';")
	connection.commit()
	connection.close()

def get_active_cabins(IDVRM):
	connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
	cursor = connection.cursor() if connection else None
	if cursor: cursor.execute('''SELECT cabin.idvrm as "IDVRM", cabin.id as "ID", 
                cabin.name as "Name", cabin.website as "Website", cabin.description as "Description",
                cabin.address as "Address", cabin.location as "Location", cabin.bedrooms as "Bedrooms",
                cabin.occupancy as "Occupancy", cabin.tier as "Tier", cabin.status as "Status",
                vrm.last_scrape as "Last scrape" FROM db.cabin as cabin join db.vrm as vrm on 
                cabin.idvrm = vrm.idvrm''')
	data = cursor.fetchall() if cursor else None
	if connection: connection.close()
	data = [d for d in data if d['IDVRM'] == IDVRM and d['Status'] == 'ACTIVE'] if data else None
	return data

def modify_active_BBV():
	data = get_active_cabins('BBV')
	for dat in data:
		website = f"http://{dat['Website']}" if 'http://' not in dat['Website'] and 'https://' not in dat['Website'] else dat['Website']
		print(website)
		location_address = BBV_location_address(website)
		address, location = location_address if location_address else (None,None)
		print(address,'/',location)
		if address or location:
			updateall(address,location,dat['ID'])
			print('Updated')