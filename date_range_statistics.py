# coding: utf-8
def get_availabilities_in_range():
    with connection, connection.cursor() as c:
        debug = c.mogrify('SELECT id,rate FROM db.availability where check_in = %s and check_out = %s and id ilike any(%s)', ('2019-03-15', '2019-03-16', ['BBV%', 'VACASA%']))
        print(debug)
        c.execute('SELECT id,rate FROM db.availability where check_in = %s and check_out = %s and id ilike any(%s)', ('2019-03-15', '2019-03-16', ['BBV%', 'VACASA%']))
        results = c.fetchall()
        return results
        
        
def calculate_means():
    means = {}
    for g, v in it.groupby(results, lambda tup: re.match(r'[A-Z]+', tup[0]).group(0)):
        for id_, rate in v:
            if not means.get(g):
                means[g] = {
                    'rate': rate,
                    'count': 1
                }
            else:
                means[g]['rate'] += rate
                means[g]['count'] += 1
    for k, v in means.items():
        v['mean'] = v['rate'] / v['count']
    return means
    
