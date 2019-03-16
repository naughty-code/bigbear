from flask import Flask
from flask import request
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_cors import CORS
from flask import jsonify
import os
import json
import scrapper
import sys
import logging
from multiprocessing import Process
import itertools as it
import re

from dotenv import load_dotenv
load_dotenv()

DATABASE_URI = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URI')

app = Flask(__name__, static_url_path='')
app.config['JSON_SORT_KEYS'] = False

CORS(app)


@app.route('/api/cabins')
def cabins():
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('''SELECT cabin.idvrm as "IDVRM", cabin.id as "ID", 
                cabin.name as "Name", cabin.website as "Website", cabin.description as "Description",
                cabin.address as "Address", cabin.location as "Location", cabin.bedrooms as "Bedrooms",
                cabin.occupancy as "Occupancy", cabin.tier as "Tier", cabin.status as "Status",
                vrm.last_scrape as "Last scrape" FROM db.cabin as cabin join db.vrm as vrm on 
                cabin.idvrm = vrm.idvrm''')
            data = cursor.fetchall()
    connection.close()
    return jsonify(data)

@app.route('/api/vrm')
def vrm():
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('''SELECT idvrm as "IDVRM", name as "Name", website as "Website",
                ncabins as "Cabins", last_scrape as "Last scrape" FROM db.vrm''')
            data = cursor.fetchall()
    connection.close()
    return jsonify(data)

@app.route('/api/features')
def features():
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('''select cabin.idvrm as "IDVRM", features.id as "ID", amenity as 
                "Amenity", cabin.name as "Name", website as "Website" from db.features inner join 
                db.cabin on cabin.id = features.id''')
            data = cursor.fetchall()
    connection.close()
    return jsonify(data)

@app.route('/api/availability')
def availability():
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('''SELECT id as "ID", check_in as "Date IN", check_out as "Date OUT", 
                status as "Status", '$' || round(rate, 2) as "Rate", name as "Name" FROM db.availability 
                order by name asc''')
            data = cursor.fetchall()
    connection.close()
    return jsonify(data)

@app.route('/api/advanced-report')
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
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            data = cursor.fetchall()
    connection.close()
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
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection:
        with connection.cursor() as cursor:
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

            cursor.execute('''select cabin.idvrm, cabin.id, cabin.name, cabin.website, check_in, check_out, availability.status, '$' || round(availability.rate, 2), availability.name from db.availability inner join db.cabin on cabin.id = availability.id order  by check_in asc''')
            table2 = cursor.fetchall()
    connection.close()
    result_json['table2'] = table2

    return jsonify(result_json)

@app.route('/api/update', methods=['POST'])
def update():
    data = request.get_json()
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('select status from db.status_update where id=1')
            result = cursor.fetchall()
            if result != 'Updating':
                print('Actualizar:')
                print(data['vrm'])
                cursor.execute("UPDATE db.status_update SET status='Updating'")
                scrapper_process = Process(target=scrapper.run, args=(data['vrm'],))
                scrapper_process.start()
    connection.close()
    return 'true'

@app.route('/api/check')
def check():
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('select status from db.status_update where id=1')
            result = cursor.fetchall()
            cursor.execute('select last_scrape from db.vrm order by last_scrape desc limit 1')
            result2 = cursor.fetchall()
    connection.close()
    result[0]['last_update'] = result2[0].get('last_scrape')
    return jsonify(result)

@app.route('/api/metrics1')
def metrics1():
    result = []
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection, connection.cursor() as c:
        c.execute('''select count(id), name from db.availability where "name" <> 'Weekend' and status = 'BOOKED' group by "name" order by count(id) desc''')
        result.append(c.fetchall())
        c.execute('''select '$' || round(MIN(rate), 2), name from db.availability where "name" <> 'Weekend' and status = 'AVAILABLE' group by "name" order by min(rate) asc limit 1''')
        result.append(c.fetchall())
        c.execute('''select '$' || round(MAX(rate), 2), name from db.availability where "name" <> 'Weekend' and status = 'AVAILABLE' group by "name" order by max(rate) desc limit 1''')
        result.append(c.fetchall())
        c.execute('''select count(id), check_in, check_out, name from db.availability where status = 'BOOKED' group by check_in, check_out, name order by count(id) desc
    ''')
        result.append(c.fetchall())
        c.execute('''select '$' || round(MIN(rate), 2), check_in, check_out, name from db.availability where status = 'AVAILABLE' group by check_in, check_out, name order by min(rate) asc limit 1''')
        result.append(c.fetchall())
        c.execute('''select '$' || round(MAX(rate), 2), check_in, check_out, name from db.availability where status = 'AVAILABLE' group by check_in, check_out, name order by MAX(rate) desc limit 1''')
        result.append(c.fetchall())
    connection.close()
    return jsonify(result)

@app.route('/api/metrics2')
def metrics2():
    result = []
    year = request.args.get('year')
    day = request.args.get('day')

    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
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

        sql = '''select '$' || COALESCE(round(avg(rate), 2), 0) AS avg from db.availability as a
        where a.status = 'AVAILABLE'
        and a.name=%s
        and DATE_PART('YEAR', a.check_in) = %s'''
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = '''select v.idvrm, '$' || coalesce((
            select round(avg(a.rate), 2) 
            from db.availability as a
            where a."name" = %s 
            and a.id like v.idvrm || '%%'
            and DATE_PART('YEAR', a.check_in) = %s
            and a.status = 'AVAILABLE'
        ), 0) as avg from db.vrm as v order by avg desc;'''
        c.execute(sql, [day, year])
        result.append(c.fetchall())

        sql = '''select a.id, '$' || round(a.rate, 2) as rate from db.availability as a 
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
    connection.close()
    return jsonify(result)

@app.route('/api/view1')
def view1():
    sql = '''with reservas as (
		select idvrm, bedrooms, availability.name, tier, features.amenity, count(availability.status), 
			max(availability.rate), min(availability.rate)
		from db.cabin
		inner join db.availability on cabin.id = availability.id
		inner join db.features on features.id = cabin.id
		where availability.status = 'BOOKED' 
		group by idvrm, bedrooms, availability.name, tier, amenity),
	vacantes as (
		select idvrm, bedrooms, availability.name, tier, features.amenity, count(availability.status), 
			max(availability.rate), min(availability.rate)
		from db.cabin
		inner join db.availability on cabin.id = availability.id
		inner join db.features on features.id = cabin.id
		where availability.status = 'AVAILABLE' 
		group by idvrm, bedrooms, availability.name, tier, amenity)
select reservas.idvrm as "IDVRM", reservas.bedrooms as "Bedrooms", reservas.name as "Date", 
reservas.tier as "Tier", reservas.amenity as "Amenity", reservas.count as "Booked",  
reservas.min as "Min Booked Rate", reservas.max as "Max Booked Rate", vacantes.count as "Vacants", 
vacantes.min as "Min Vacants Rate", vacantes.max as "Max Vacants Rate"
from reservas full outer join vacantes on reservas.idvrm = vacantes.idvrm 
and reservas.bedrooms = vacantes.bedrooms
and reservas.name = vacantes.name
and reservas.tier = vacantes.tier
and reservas.amenity = vacantes.amenity;'''
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection, connection.cursor() as c:
        c.execute(sql)
        result = c.fetchall()
    connection.close()
    return jsonify(result)

# API from view search
@app.route('/api/search/amenities')
def search_amenities():
    sql = '''SELECT amenity from db.features group by amenity order by amenity asc'''
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        c.execute(sql)
        result = [r[0] for r in c.fetchall()]
    connection.close()
    return jsonify(result)

@app.route('/api/search/vrms')
def search_vrms():
    sql = '''SELECT idvrm from db.vrm order by idvrm asc'''
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        c.execute(sql)
        result = [r[0] for r in c.fetchall()]
    connection.close()
    return jsonify(result)

@app.route('/api/search/bedrooms')
def search_bedrooms():
    sql = '''SELECT bedrooms from db.cabin where status = 'ACTIVE' group by bedrooms order by bedrooms asc'''
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        c.execute(sql)
        result = [r[0] for r in c.fetchall()]
    connection.close()
    return jsonify(result)

@app.route('/api/search/years')
def search_years():
    sql = '''select cast(DATE_PART('YEAR', check_in) as varchar) as year from db.availability group by DATE_PART('YEAR', check_in);'''
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        c.execute(sql)
        result = [r[0] for r in c.fetchall()]
    connection.close()
    return jsonify(result)

@app.route('/api/search/days')
def search_days():
    sql = '''SELECT name from db.availability group by name order by name asc'''
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        c.execute(sql)
        result = [r[0] for r in c.fetchall()]
    connection.close()
    return jsonify(result)

@app.route('/api/search/tiers')
def search_tiers():
    sql = '''SELECT tier from db.cabin group by tier order by tier asc'''
    connection = psycopg2.connect(DATABASE_URI)
    with connection, connection.cursor() as c:
        c.execute(sql)
        result = [r[0] for r in c.fetchall()]
    connection.close()
    return jsonify(result)

@app.route('/api/search/avg', methods = ['POST'])
def search_avg():
    data = request.get_json()
    sql = '''select c.idvrm, a.check_in, a.check_out, a."name", round(avg(a.rate) filter (where a.rate > 0))::money as average, round(min(a.rate) filter (where a.rate > 0))::money as minimum, round(max(a.rate) filter (where a.rate > 0))::money as maximum, count(a.id) filter (where a.status = 'BOOKED') as "Bookings", (count(a.id) filter (where a.status = 'BOOKED')) * 100 / count(a.id) as "Bookings %%", count(a.id) filter (where a.status = 'AVAILABLE') as "Vacants", (count(a.id) filter (where a.status = 'AVAILABLE')) * 100 / count(a.id) as "Vacants %%" from db.cabin as c join db.availability as a on c.id = a.id where (select count(*) from db.features as f where f.id = c.id and f.amenity = ANY (%s)) = %s and c.idvrm = ANY(%s) and c.bedrooms = %s and cast(DATE_PART('year',a.check_in) as varchar) = ANY(%s) and a.name = ANY(%s) and c.tier = ANY(%s) and c.status = 'ACTIVE' group by c.idvrm, a.check_in, a.check_out, a."name" order by c.idvrm;'''
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection, connection.cursor() as c:
        c.execute(sql, (
            '{' + ','.join(data['amenities']) + '}', 
            len(data['amenities']),
            '{' + ','.join(data['vrms']) + '}', 
            data['bedrooms'], 
            '{' + ','.join(data['years']) + '}', 
            '{' + ','.join(data['days']) + '}', 
            '{' + ','.join(data['tiers']) + '}'))
        result = c.fetchall()
    connection.close()
    return jsonify(result)

#search rate statistics by daterange and sort them by tier and vrm
@app.route('/api/search/daterange', methods = ['POST']) 
def get_rates_by_tier():
    data = request.get_json()
    start_date = data.get('startDate')
    end_date = data.get('endDate')
    vrms = data.get('vrms')
    tiers = data.get('tiers')
    connection = psycopg2.connect(DATABASE_URI, cursor_factory=RealDictCursor)
    with connection, connection.cursor() as c:
        # result
        sql = '''select c.bedrooms, c.tier, avg(avail.rate)::money from db.cabin as c 
            join db.availability as avail on avail.id = c.id 
            and avail.rate > 0 
            and avail.check_in >= %s
            and avail.check_out <= %s
            where c.location in ('Sugarloaf', 'Fawnskin', 'Big Bear City')  
            and c.tier = ANY(%s)
            and c.idvrm = ANY(%s)
            and c.status='ACTIVE' 
            group by bedrooms, tier;'''
        c.execute(sql, (start_date, end_date, '{' + ','.join(tiers) + '}', '{' + ','.join(vrms) + '}'))
        low_demand = c.fetchall()

        sql = '''select c.bedrooms, c.tier, avg(avail.rate)::money from db.cabin as c 
            join db.availability as avail on avail.id = c.id 
            and avail.rate > 0 
            and avail.check_in >= %s
            and avail.check_out <= %s
            where c.location in ('Moonridge')  
            and c.tier = ANY(%s)
            and c.idvrm = ANY(%s)
            and c.status='ACTIVE' 
            group by bedrooms, tier;'''
        c.execute(sql, (start_date, end_date, '{' + ','.join(tiers) + '}', '{' + ','.join(vrms) + '}'))
        medium_demand = c.fetchall()

        sql = '''select c.bedrooms, c.tier, avg(avail.rate)::money from db.cabin as c 
            join db.availability as avail on avail.id = c.id 
            and avail.rate > 0 
            and avail.check_in >= %s
            and avail.check_out <= %s
            where c.location in ('Big Bear Lake')  
            and c.tier = ANY(%s)
            and c.idvrm = ANY(%s)
            and c.status='ACTIVE' 
            group by bedrooms, tier;'''
        c.execute(sql, (start_date, end_date, '{' + ','.join(tiers) + '}', '{' + ','.join(vrms) + '}'))
        prime_demand = c.fetchall()
        # statistics
        statistics = list(())
        for vrm in vrms:
            vrm_dict = dict(name=vrm)
            total_category = list(())
            # Percent booked/Vacant shown
            sql = '''select
                round(count(a.id) filter (where a.status = 'BOOKED')::numeric * 100/ count(a.id), 2) as "booked",  
                round(count(a.id) filter (where a.status = 'AVAILABLE')::numeric * 100 / count(a.id), 2) as "vacant"
                from db.availability as a
                join db.cabin as c 
                on c.id = a.id and c.idvrm = %s and c.status = 'ACTIVE'
                where a.check_in >= %s and a.check_out <= %s;'''
            c.execute(sql, (vrm, start_date, end_date))
            booked_vacant = c.fetchone()
            vrm_dict['statistics'] = list(())
            vrm_dict['statistics'].append({
                "name": "Percent booked/Vacant shown",
                "value": str(booked_vacant.get('booked')) + ' / ' + str(booked_vacant.get('vacant'))
            })
            # Market Share
            sql = '''select
                round(count(c.id) filter (where c.idvrm = %s)::numeric * 100 / count(c.id), 2) as market_share
                from db.availability as a
                join db.cabin as c 
                on c.id = a.id and c.status = 'ACTIVE'
                where a.check_in >= %s and a.check_out <= %s;'''
            c.execute(sql, (vrm, start_date, end_date))
            vrm_dict['statistics'].append({
                "name": "Market Share",
                "value": str(c.fetchone().get('market_share')) + '%'
            })
            # Occupancy over or under ours
            sql = '''select
                count(c.id) filter (where c.idvrm = %s) - count(c.id) filter (where c.idvrm = 'BBV') as overunder
                from db.availability as a
                join db.cabin as c 
                on c.id = a.id and c.status = 'ACTIVE'
                where a.check_in >= %s and a.check_out <= %s and a.status='BOOKED';'''
            c.execute(sql, (vrm, start_date, end_date))
            vrm_dict['statistics'].append({
                "name": "Occupancy over or under ours",
                "value": c.fetchone().get('overunder')
            })
            # Bookings in last week
            sql = '''select count(a.id) 
                from db.availability as a
                join db.cabin as c 
                on c.id = a.id and c.status = 'ACTIVE' and c.idvrm = %s
                where a.check_in >= date_trunc('week', CURRENT_TIMESTAMP - interval '1 week') 
                and a.check_out <= date_trunc('week', CURRENT_TIMESTAMP) 
                and a.status='BOOKED';'''
            c.execute(sql, (vrm,))
            vrm_dict['statistics'].append({
                "name": "Bookings in last week",
                "value": c.fetchone().get('count')
            })
            # Bookings in last month
            sql = '''select count(a.id) 
                from db.availability as a
                join db.cabin as c 
                on c.id = a.id and c.status = 'ACTIVE' and c.idvrm = %s
                where a.check_in >= date_trunc('month', CURRENT_TIMESTAMP - interval '1 month') 
                and a.check_out <= date_trunc('month', CURRENT_TIMESTAMP) 
                and a.status='BOOKED';'''
            c.execute(sql, (vrm,))
            vrm_dict['statistics'].append({
                "name": "Bookings in last month",
                "value": c.fetchone().get('count')
            })
            # Bookings in last year
            sql = '''select count(a.id) 
                from db.availability as a
                join db.cabin as c 
                on c.id = a.id and c.status = 'ACTIVE' and c.idvrm = %s
                where a.check_in >= date_trunc('year', CURRENT_TIMESTAMP - interval '1 year') 
                and a.check_out <= date_trunc('year', CURRENT_TIMESTAMP) 
                and a.status='BOOKED';'''
            c.execute(sql, (vrm,))
            vrm_dict['statistics'].append({
                "name": "Bookings in last year",
                "value": c.fetchone().get('count')
            })
            # Total Units by tier category
            sql = '''select c.tier, count(c.tier) from db.cabin as c 
                join db.availability as a on a.id = c.id 
                and a.check_in >= %s and a.check_out <= %s
                where c.idvrm = %s and c.status = 'ACTIVE'
                group by tier;'''
            c.execute(sql, (start_date, end_date, vrm))
            vrm_dict['total_category'] = c.fetchall()
            # Total Units by Area
            sql = '''select count(c.id), 
                case 
                    when c.location in ('Sugarloaf', 'Fawnskin', 'Big Bear City') then 'Low demand area'
                    when c.location in ('Moonridge') then 'Medium demand area'
                    when c.location in ('Big Bear Lake') then 'Prime demand area'
                end as area from db.availability as a 
                join db.cabin as c 
                on c.id = a.id and c.idvrm = %s and c.status = 'ACTIVE'
                where a.check_in >= %s and a.check_out <= %s
                group by area;'''
            c.execute(sql, (vrm, start_date, end_date))
            vrm_dict['total_area'] = c.fetchall()

            statistics.append(vrm_dict)

    connection.close()
    result = {
        'result': [{
            'title': 'Low demand area',
            'values': low_demand
        },
        {
            'title': 'Medium demand area',
            'values': medium_demand
        },{

            'title': 'Prime demand area',
            'values': prime_demand
        },],
        'statistics': statistics
    }
    return jsonify(result)

# API from view search
@app.route('/')
def root():
    return app.send_static_file('index.html')

    # %load date_range_statistics.py
def get_availabilities_in_range(start, end, vrms=['BBV', 'BBCC', 'VACASA', 'DBB']):
    with psycopg2.connect(DATABASE_URI) as connection:
        with connection, connection.cursor() as c:
            sql = 'SELECT cabin.id,availability.rate, cabin.tier FROM db.availability, db.cabin where check_in = %s and check_out = %s and availability.id ilike any(%s) and rate > 0 and cabin.id = availability.id'
            c.execute(sql, (start, end, [f'{vrm}%' for vrm in vrms]))
            results = c.fetchall()
            return results


def calculate_means(availabilities):
    results = {}
    for g, v in it.groupby(availabilities, lambda tup: (re.match(r'[A-Z]+', tup[0]).group(0), tup[2])):
        for id_, rate, tier in v:
            if not results.get(g):
                results[g] = {
                    'rate': float(rate),
                    'count': 1,
                }
            else:
                results[g]['rate'] += float(rate)
                results[g]['count'] += 1
    for k, v in results.items():
        v['mean'] = v['rate'] / v['count']
    return results