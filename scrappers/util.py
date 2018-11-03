import datetime as dt
from datetime import timedelta
import pandas as pd
import functools
import json
import multiprocessing as mp



DATE_FORMAT = '%Y-%m-%d'

def dict_from_table(soup):

    rows = soup.find_all('tr')

    # Header
    header = rows[0]
    th = header.find_all('th')
    th = [ x.get_text(strip=True) for x in th ]

    for r in rows[1:]:
        td = r.find_all('td')
        td = [ x.get_text(strip=True) for x in td ]
        yield { k: v for k, v in zip(th, td) }

def ignore_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Logger
            print('Error!', e)
            return None
    return wrapper

def scrape_ranges(id_, rgs, quote):
    results = []
    for i, start, end in rgs.itertuples():
        print(start, end)
        data = { 'id': id_,
            'startDate': start, 'endDate': end,
            'quote': quote(id_, start, end) }
        results.append(data)

    return results

def extract_costs(ids, quote):

    rg = pd.read_csv('./scrappers/merged.csv',
            parse_dates=['PL', 'PR'])

    with mp.Pool(8) as p:
        scraper = functools.partial(
                scrape_ranges, rgs=rg, quote=quote)
        yield from p.imap_unordered(scraper, ids)

def parse_dates(d):
    if isinstance(d, dt.date):
        return d.strftime(DATE_FORMAT)
    return str(d)

def write_json(filename, data, *args, **kwargs):
    with open(filename, 'w', encoding='utf8') as fp:
        json.dump(data, fp, *args, **kwargs)

def read_json(filename):
    data = None
    with open(filename, 'r', encoding='utf8') as fp:
        data = json.load(fp)
    return data

def is_holiday(holidays, start, end):
    return (start, end) in holidays

def get_holidays_as_dict(filename='./scrappers/holidays.csv'):
    df = pd.read_csv(filename)
    return dict(zip(zip(df.PL, df.PR), df.holiday))

def get_holidays(filename='./scrappers/holidays.csv'):
    df = pd.read_csv(filename)
    return set(zip(df.PL, df.PR))

def add_one_week(day):
  return day + timedelta(days=7)
