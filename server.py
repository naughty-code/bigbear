from flask import Flask
from flask import request
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
    with connection:
        cursor.execute('''SELECT cabin.idvrm as "IDVRM", cabin.id as "ID", 
            cabin.name as "Name", cabin.website as "Website", cabin.description as "Description",
            cabin.address as "Address", cabin.location as "Location", cabin.bedrooms as "Bedrooms",
            cabin.occupancy as "Occupancy", cabin.tier as "Tier", cabin.status as "Status",
            vrm.last_scrape as "Last scrape" FROM db.cabin as cabin join db.vrm as vrm on 
            cabin.idvrm = vrm.idvrm''')
        data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/vrm')
def vrm():
    with connection:
        cursor.execute('''SELECT idvrm as "IDVRM", name as "Name", website as "Website",
            ncabins as "Cabins", last_scrape as "Last scrape" FROM db.vrm''')
        data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/features')
def features():
    with connection:
        cursor.execute('''select cabin.idvrm as "IDVRM", features.id as "ID", amenity as "Amenity",
            cabin.name as "Name", website as "Website" from db.features inner join db.cabin on 
            cabin.id = features.id''')
        data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/availability')
def availability():
    with connection:
        cursor.execute('''SELECT id as "ID", check_in as "Date IN", check_out as "Date OUT", 
            status as "Status", '$' || rate as "Rate", name as "Name" FROM db.availability order 
            by name asc''')
        data = cursor.fetchall()
    return jsonify(data)

@app.route('/api/advance-report')
def report2():
    sql = '''select a.check_in as "Date IN", a.check_out as "Date OUT", a.name as "Note", c.idvrm as "VRM",
count(a.id) as "Units", count(a.id) filter (where a.status = 'AVAILABLE') as "Vacant",
count(a.id) filter (where a.status = 'BOOKED') as "Booked",
count(a.id) filter (where a.status = 'BOOKED') - (select count(a2.id) filter (where a2.status = 'BOOKED') 
from db.availability as a2
join db.cabin as c2 on c2.id = a2.id
where a2.check_in = a.check_in - interval '1 WEEK'
and c2.idvrm = c.idvrm) as "Change from LW",
(count(a.id) filter (where a.status = 'BOOKED')) * 100 / count(a.id) as "Occupancy",
0 as "% of Bookings",
(select count(a2.id) filter (where a2.status = 'BOOKED') 
from db.availability as a2
join db.cabin as c2 on c2.id = a2.id
where a2.check_in = a.check_in - interval '1 YEAR'
and c2.idvrm = c.idvrm) as "Booked LY",
count(a.id) filter (where a.status = 'BOOKED') - (select count(a2.id) filter (where a2.status = 'BOOKED') 
from db.availability as a2
join db.cabin as c2 on c2.id = a2.id
where a2.check_in = a.check_in - interval '1 YEAR'
and c2.idvrm = c.idvrm) as "Change from LY"
from db.availability as a
join db.cabin as c on c.id = a.id
group by c.idvrm, a.check_in, a.check_out, a.name;'''
    with connection:
        cursor.execute(sql)
        data = cursor.fetchall()
    aux = []
    aux_bool = False
    for d in data:
        if len(aux) > 0:
            for a in aux:
                if d['Date IN'] == a['Date IN'] and d['Date OUT'] == a['Date OUT']:
                    a['total'] += d['Booked']
                    aux_bool = True
                    break
            if aux_bool is False:
                aux.append({
                'Date IN': d['Date IN'],
                'Date OUT': d['Date OUT'],
                'total': d['Booked']
                })
            aux_bool = False
        else:
            aux.append({
                'Date IN': d['Date IN'],
                'Date OUT': d['Date OUT'],
                'total': d['Booked']
            })
    for d in data:
        for a in aux:
            if d['Date IN'] == a['Date IN'] and d['Date OUT'] == a['Date OUT']:
                if a['total'] > 0:
                    d['% of Bookings'] = format(d['Booked'] * 100 / a['total'], '.2f')
    return jsonify(data)

@app.route('/api/report')
def report():
    with connection:
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

        cursor.execute('''select cabin.idvrm, cabin.id, cabin.name, cabin.website, check_in, check_out, availability.status, '$' || availability.rate, availability.name from db.availability inner join db.cabin on cabin.id = availability.id order  by check_in asc''')
        table2 = cursor.fetchall()
    result_json['table2'] = table2

    return jsonify(result_json)

@app.route('/api/update')
def update():
    # here we execute the scrappers and update database
    with connection:
        cursor.execute('select status from db.status_update where id=1')
        result = cursor.fetchall()
        if result != 'Updating':
            cursor.execute("UPDATE db.status_update SET status='Updating'")
            scrapper_process = Process(target=scrapper.update)
            scrapper_process.start()
    return 'true'

@app.route('/api/check')
def check():
    with connection:
        cursor.execute('select status from db.status_update where id=1')
        result = cursor.fetchall()
    return jsonify(result)

@app.route('/api/metrics1')
def metrics1():
    result = []
    with connection, connection.cursor() as c:
        c.execute('''select count(id), name from db.availability where "name" <> 'Weekend' and status = 'BOOKED' group by "name" order by count(id) desc''')
        result.append(c.fetchall())
        c.execute('''select '$' || MIN(rate), name from db.availability where "name" <> 'Weekend' and status = 'AVAILABLE' group by "name" order by min(rate) asc limit 1''')
        result.append(c.fetchall())
        c.execute('''select '$' || MAX(rate), name from db.availability where "name" <> 'Weekend' and status = 'AVAILABLE' group by "name" order by max(rate) desc limit 1''')
        result.append(c.fetchall())
        c.execute('''select count(id), check_in, check_out, name from db.availability where status = 'BOOKED' group by check_in, check_out, name order by count(id) desc
    ''')
        result.append(c.fetchall())
        c.execute('''select '$' || MIN(rate), check_in, check_out, name from db.availability where status = 'AVAILABLE' group by check_in, check_out, name order by min(rate) asc limit 1''')
        result.append(c.fetchall())
        c.execute('''select '$' || MAX(rate), check_in, check_out, name from db.availability where status = 'AVAILABLE' group by check_in, check_out, name order by MAX(rate) desc limit 1''')
        result.append(c.fetchall())
    return jsonify(result)

@app.route('/api/metrics2')
def metrics2():
    result = []
    year = request.args.get('year')
    day = request.args.get('day')

    with connection, connection.cursor() as c:
        sql = "select COUNT(status) as bookings from db.availability where status = 'BOOKED' and name=%s and DATE_PART('YEAR', check_in) = %s"
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = "select COUNT(status) as vacants from db.availability where status = 'AVAILABLE' and name=%s and DATE_PART('YEAR', check_in) = %s"
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = '''select c.idvrm, count(a.id) from db.availability as a 
            join db.cabin as c on a.id = c.id 
            where a.status = 'BOOKED'
            and a.name=%s 
            and DATE_PART('YEAR', a.check_in) = %s
            group by c.idvrm 
            order by count(a.id) desc'''
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = '''select '$' || COALESCE(avg(rate), 0) AS avg from db.availability as a
        where a.status = 'AVAILABLE'
        and a.name=%s
        and DATE_PART('YEAR', a.check_in) = %s'''
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = '''select v.idvrm, '$' || coalesce((
            select avg(a.rate) 
            from db.availability as a
            where a."name" = %s 
            and a.id like v.idvrm || '%%'
            and DATE_PART('YEAR', a.check_in) = %s
            and a.status = 'AVAILABLE'
        ), 0) as avg from db.vrm as v order by avg desc;'''
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = '''select a.id, '$' || a.rate from db.availability as a 
            where a.status = 'AVAILABLE'
            and a.name=%s
            and DATE_PART('YEAR', a.check_in) = %s
            order by a.rate desc;'''
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = '''select count(c.id), c.location from db.availability as a
            join db.cabin as c on a.id = c.id 
            where a.status = 'BOOKED'
            and a.name=%s
            and DATE_PART('YEAR', a.check_in) = %s
            group by c.location order by count(c.id) desc;'''
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = '''SELECT count(c.idvrm), occupancy from db.availability as a 
            join db.cabin as c on c.id = a.id 
            where a.status = 'BOOKED'
            and a.name=%s
            and DATE_PART('YEAR', a.check_in) = %s
            group by c.occupancy 
            order by count(c.idvrm) desc;'''
        c.execute(sql, [day, year])
        result.append(c.fetchall())

    return jsonify(result)

@app.route('/')
def root():
    return app.send_static_file('index.html')