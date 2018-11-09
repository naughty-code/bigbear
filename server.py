from flask import Flask
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_cors import CORS
from flask import jsonify
import os
import json
from dotenv import load_dotenv
load_dotenv()

DATABASE_URI = os.environ['DATABASE_URL']

app = Flask(__name__, static_url_path='')
app.config['JSON_SORT_KEYS'] = False

CORS(app)


connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
cursor = connection.cursor()

@app.route('/api/cabins')
def cabins():
    cursor.execute('SELECT * FROM db.cabin')
    data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/vrm')
def vrm():
    cursor.execute('SELECT * FROM db.vrm')
    data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/features')
def features():
    cursor.execute('select cabin.idvrm, features.id, amenity, cabin.name, website from db.features inner join db.cabin on cabin.id = features.id')
    data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/availability')
def availability():
    cursor.execute('SELECT * FROM db.availability')
    data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/report')
def report():
    cursor.execute('SELECT idvrm FROM db.vrm')
    vrms = cursor.fetchall()
    result = []
    result_json = {}

    for vrm in vrms:
        row = {}
        cursor.execute('select ncabins from db.vrm where idvrm = %s', (vrm['idvrm'], ))
        total_units = cursor.fetchall()
        cursor.execute('select count(availability.id) as booked from db.availability inner join db.cabin on cabin.id = availability.id where idvrm = %s and availability.status = \'BOOKED\'', (vrm['idvrm'], ))
        booked = cursor.fetchall()
        cursor.execute('select count(availability.id) as available from db.availability inner join db.cabin on cabin.id = availability.id where idvrm = %s and availability.status = \'AVAILABLE\'', (vrm['idvrm'], ))
        available = cursor.fetchall()
        row['idvrm'] = vrm['idvrm']
        row['ncabins'] = total_units[0]['ncabins']
        row['booked'] = booked[0]['booked']
        row['available'] = available[0]['available']
        result.append(row)
    
    result_json['table1'] = result

    cursor.execute('select cabin.idvrm, cabin.id, cabin.name, cabin.website, check_in, check_out, availability.status, availability.rate, availability.name from db.availability inner join db.cabin on cabin.id = availability.id order  by check_in asc')
    table2 = cursor.fetchall()
    result_json['table2'] = table2

    return jsonify(result_json)

@app.route('/')
def root():
    return app.send_static_file('index.html')