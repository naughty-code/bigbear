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
    cursor.execute('SELECT * FROM db.features')
    data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/availability')
def availability():
    cursor.execute('SELECT * FROM db.availability')
    data = cursor.fetchall()
    # return json.dumps(data)
    return jsonify(data)

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