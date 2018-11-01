from flask import Flask
import psycopg2
from flask_cors import CORS
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URI = os.environ['DATABASE_URI']

app = Flask(__name__, static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
db = SQLAlchemy(app)
CORS(app)

class Vrm(db.Model):
    __table_args__ = {"schema":"db"}
    idvrm = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    website = db.Column(db.String(2083), unique=True, nullable=False)
    ncabins = db.Column(db.Integer)
    last_scrape = db.Column(db.DateTime)


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

@app.route('/')
def root():
    return app.send_static_file('vrm.html')

@app.route('/vrm')
def vrm_html():
    return app.send_static_file('vrm.html')

@app.route('/cabins')
def cabins_html():
    return app.send_static_file('cabins.html')
