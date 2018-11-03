from flask import Flask
import psycopg2
from flask_cors import CORS
from flask import jsonify
import os
import json
from dotenv import load_dotenv
load_dotenv()

DATABASE_URI = os.environ['DATABASE_URL']

app = Flask(__name__, static_url_path='')

CORS(app)


connection = psycopg2.connect(DATABASE_URI)
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
        row = []
        cursor.execute('select ncabins from db.vrm where idvrm = %s', vrm)
        total_units = cursor.fetchall()
        cursor.execute('select count(availability.id) from db.availability inner join db.cabin on cabin.id = availability.id where idvrm = %s and availability.status = \'BOOKED\'', vrm)
        booked = cursor.fetchall()
        cursor.execute('select count(availability.id) from db.availability inner join db.cabin on cabin.id = availability.id where idvrm = %s and availability.status = \'AVAILABLE\'', vrm)
        available = cursor.fetchall()
        row.append(vrm[0])
        row.append(total_units[0][0])
        row.append(booked[0][0])
        row.append(available[0][0])
        result.append(row)
    
    result_json['table1'] = result

    cursor.execute('select cabin.idvrm, cabin.id, cabin.name, cabin.website, check_in, check_out, availability.status, availability.rate, availability.name from db.availability inner join db.cabin on cabin.id = availability.id order  by check_in asc')
    table2 = cursor.fetchall()
    result_json['table2'] = table2

    return jsonify(result_json)

@app.route('/')
def root():
    return app.send_static_file('vrm.html')

@app.route('/vrm')
def vrm_html():
    return app.send_static_file('vrm.html')

@app.route('/cabins')
def cabins_html():
    return app.send_static_file('cabins.html')

@app.route('/features')
def features_html():
    return app.send_static_file('features.html')

@app.route('/availability')
def availability_html():
    return app.send_static_file('availability.html')

@app.route('/report')
def report_html():
    return app.send_static_file('report.html')