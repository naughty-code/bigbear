import datetime as dt
from datetime import timedelta
import pandas as pd
import functools
import json
import multiprocessing as mp
import builtins


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
    for start, end, holiday_or_weekend in rgs:
        print(start, end, holiday_or_weekend)
        try:
            data = { 'id': id_,
                'startDate': start, 'endDate': end,
                'quote': quote(id_, start, end),
                'holiday': holiday_or_weekend
                }
            results.append(data)
        except Exception as e:
            print(e)
            print('quote(cabin id): ', id_, start, end, holiday_or_weekend)
    return results

def extract_costs(ids, quote, date_ranges_=None):
    #if not date_ranges_:
    #    start = dt.datetime.now()
    #    end = start + timedelta(days=450)
    #    range_ = get_weekends_from_to(start, end) + get_holidays_in_range(start, end)
    df = pd.read_csv('scrappers/CEK_DB_-_Dates_CSV.csv', parse_dates=['PL', 'PR'])
    range_ = [(pl, pr, h) for i,pl,pr,h in df.itertuples()]
    
    with mp.Pool(8) as p:
        scraper = functools.partial(
                scrape_ranges, rgs=range_, quote=quote)
        yield from p.imap_unordered(scraper, ids)

def extract_costs_faster(quote, date_ranges_=None):
    #if not date_ranges_:
    #    start = dt.datetime.now()
    #    end = start + timedelta(days=450)
    #    range_ = get_weekends_from_to(start, end) + get_holidays_in_range(start, end)
    range_ = get_date_ranges()
    with mp.Pool(1) as p:
        yield from p.imap_unordered(quote, range_)

def get_date_ranges():
    df = pd.read_csv('scrappers/CEK_DB_-_Dates_CSV.csv', parse_dates=['PL', 'PR'])
    range_ = [(pl, pr, h) for i,pl,pr,h in df.itertuples()]
    return range_

def get_weekends_from_to(start_date, end_date):
    weekends = []
    friday = get_closest_friday()
    sunday = friday + timedelta(days=2)
    while sunday <= end_date:
        weekends.append((friday, sunday, 'weekend'))
        friday = add_one_week(friday)
        sunday = add_one_week(sunday)
    return weekends

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

def get_closest_friday():
    today = dt.datetime.now()
    friday = today + timedelta( days=(4-today.weekday()) % 7 )
    return friday

def is_holiday(holidays, start, end):
    startString = start.strftime('%m-%d')
    endString = end.strftime('%m-%d')
    return (startString, endString) in holidays

def get_holidays_as_dict(filename='./scrappers/holidays.csv'):
    df = pd.read_csv(filename)
    return dict(zip(zip(df.PL, df.PR), df.holiday))

def get_holidays(filename='./scrappers/holidays.csv'):
    df = pd.read_csv(filename)
    return set(zip(df.PL, df.PR, df.holiday))

def get_holidays_in_range(start, end, holidays_filename='./scrappers/holidays.csv'):
    holidays_dates = []
    holidays = get_holidays()
    for year in range(start.year, end.year+1):
        for start_string, end_string, holiday in holidays:
            start_month, start_day = [int(e) for e in start_string.split('-')]
            end_month, end_day = [int(e) for e in end_string.split('-')]
            start_holiday = dt.datetime(year, start_month, start_day)
            if holiday != 'christmas season' and (year+1) <= end.year:
                end_holiday = dt.datetime(year+1, end_month, end_day)
            else:
                end_holiday = dt.datetime(year, end_month, end_day)
            if (start <= start_holiday <= end) and (start <= end_holiday <=  end):
                holidays_dates.append((start_holiday, end_holiday, holiday))
    return holidays_dates
        

def add_one_week(day):
  return day + timedelta(days=7)

  
def print(*args, **kwargs):
    sep = kwargs.get('sep')
    end = kwargs.get('end')
    if sep is None:
        sep = ' '
    if end is None:
        end = '\n'
    with open('debug.txt', 'a', encoding='utf8') as f:
        f.write(sep.join(map(str, args)) + end)
    builtins.print(*args,**kwargs)
