from flask import Flask
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_cors import CORS
from flask import jsonify
import os
import json
import scrapper
from multiprocessing import Process

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

@app.route('/api/advance-report')
def report2():
    sql = '''select a.check_in as date_in, a.check_out as date_out, a.name as note, c.idvrm as VRM,
count(a.id) as units, count(a.id) filter (where a.status = 'AVAILABLE') as vacant,
count(a.id) filter (where a.status = 'BOOKED') as booked,
count(a.id) filter (where a.status = 'BOOKED') - (select count(a2.id) filter (where a2.status = 'BOOKED') 
from db.availability as a2
join db.cabin as c2 on c2.id = a2.id
where a2.check_in = a.check_in - interval '1 WEEK'
and c2.idvrm = c.idvrm) as "change from LW",
(count(a.id) filter (where a.status = 'BOOKED')) * 100 / count(a.id) as occupancy,
0 as "% of bookings",
(select count(a2.id) filter (where a2.status = 'BOOKED') 
from db.availability as a2
join db.cabin as c2 on c2.id = a2.id
where a2.check_in = a.check_in - interval '1 YEAR'
and c2.idvrm = c.idvrm) as "booked LY",
count(a.id) filter (where a.status = 'BOOKED') - (select count(a2.id) filter (where a2.status = 'BOOKED') 
from db.availability as a2
join db.cabin as c2 on c2.id = a2.id
where a2.check_in = a.check_in - interval '1 YEAR'
and c2.idvrm = c.idvrm) as "change from LY"
from db.availability as a
join db.cabin as c on c.id = a.id
where DATE_PART('YEAR',a.check_in) = DATE_PART('YEAR',now())
group by c.idvrm, a.check_in, a.check_out, a.name;'''
    cursor.execute(sql)
    data = cursor.fetchall()
    aux = []
    aux_bool = False
    for d in data:
        if len(aux) > 0:
            for a in aux:
                if d['date_in'] == a['date_in'] and d['date_out'] == a['date_out']:
                    a['total'] += d['booked']
                    aux_bool = True
                    break
            if aux_bool is False:
                aux.append({
                'date_in': d['date_in'],
                'date_out': d['date_out'],
                'total': d['booked']
                })
            aux_bool = False
        else:
            aux.append({
                'date_in': d['date_in'],
                'date_out': d['date_out'],
                'total': d['booked']
            })
    for d in data:
        for a in aux:
            if d['date_in'] == a['date_in'] and d['date_out'] == a['date_out']:
                if a['total'] > 0:
                    d['% of bookings'] = format(d['booked'] * 100 / a['total'], '.2f')
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

@app.route('/api/update')
def update():
    # here we execute the scrappers and update database
    cursor.execute('select status from db.status_update where id=1')
    result = cursor.fetchall()
    if result != 'Updating':
        with connection:
            cursor.execute("UPDATE db.status_update SET status='Updating'")
        scrapper_process = Process(target=scrapper.update)
        scrapper_process.start()
    return 'true'

@app.route('/api/check')
def check():
    cursor.execute('select status from db.status_update where id=1')
    result = cursor.fetchall()
    print(result)
    return jsonify(result)

@app.route('/')
def root():
    return app.send_static_file('index.html')