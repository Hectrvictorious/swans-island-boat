#!/usr/bin/env python3
"""Build conditions.json for the Swan's Island Boat page.
Sources: NWS marine forecast + alerts (zone ANZ052), NWS hourly forecast for Swan's Island
(CAR grid 83,47), NOAA tide predictions for Bass Harbor (8413651), and New England 511's
public ferry-terminal status feed (ids 2971 SI->BH, 2972 BH->SI, 2976 BH->Frenchboro, 2980 FB->BH).
Writes ./boat-conditions/conditions.json. Any source that fails is left out; the page copes."""
import json, subprocess, sys, os, datetime, re

OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), 'boat-conditions', 'conditions.json')
OUT_DIR = os.path.dirname(os.path.abspath(OUT_PATH))
os.makedirs(OUT_DIR, exist_ok=True)
UA = 'swans-island-boat page updater (personal use)'

def get(url, accept=None):
    cmd = ['curl', '-sS', '-m', '40', '-A', UA]
    if accept: cmd += ['-H', 'Accept: ' + accept]
    cmd += [url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if out.returncode != 0 or not out.stdout.strip():
            print('fetch failed', url, out.stderr[:200], file=sys.stderr); return None
        return json.loads(out.stdout)
    except Exception as e:
        print('fetch error', url, e, file=sys.stderr); return None

data = {'generatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}

# 1. Marine forecast
m = get('https://api.weather.gov/zones/forecast/ANZ052/forecast', 'application/geo+json')
if m and m.get('properties', {}).get('periods'):
    p = m['properties']
    data['marine'] = {'zone': 'ANZ052', 'updated': p.get('updated') or p.get('updateTime'),
                      'periods': [{'name': x.get('name'), 'text': x.get('detailedForecast')} for x in p['periods'][:5]]}

# 2. Marine alerts
a = get('https://api.weather.gov/alerts/active?zone=ANZ052', 'application/geo+json')
if a is not None and 'features' in a:
    data['alerts'] = [{'event': f['properties'].get('event'), 'headline': f['properties'].get('headline'),
                       'ends': f['properties'].get('ends') or f['properties'].get('expires')} for f in a['features']]

# 3. Hourly forecast at Swan's Island
h = get('https://api.weather.gov/gridpoints/CAR/83,47/forecast/hourly', 'application/geo+json')
if h and h.get('properties', {}).get('periods'):
    data['hourly'] = [{'t': x.get('startTime'), 'wind': x.get('windSpeed'), 'dir': x.get('windDirection'),
                       'temp': x.get('temperature'), 'short': x.get('shortForecast'),
                       'pop': (x.get('probabilityOfPrecipitation') or {}).get('value')} for x in h['properties']['periods'][:36]]

# 4. Tides at Bass Harbor (today and tomorrow, local time)
try:
    from zoneinfo import ZoneInfo
    today_me = datetime.datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d')
except Exception:
    today_me = datetime.datetime.utcnow().strftime('%Y%m%d')
t = get('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&station=8413651&begin_date=' + today_me + '&range=48&datum=MLLW&time_zone=lst_ldt&units=english&interval=hilo&format=json')
if not (t and t.get('predictions')):
    t = get('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&station=8413651&date=today&datum=MLLW&time_zone=lst_ldt&units=english&interval=hilo&format=json')
if t and t.get('predictions'):
    data['tides'] = [{'t': x['t'], 'type': x['type'], 'v': round(float(x['v']), 1)} for x in t['predictions']]

# 5. New England 511 ferry status
ferry = []
for fid in ('2971', '2972', '2976', '2980'):
    d = get('https://newengland511.org/map/data/FerryTerminals/' + fid)
    if not d: continue
    props = {p.get('name'): p.get('value') for p in d.get('properties', [])}
    notices = []
    md = props.get('messageData') or ''
    try:
        for item in json.loads(md) if md else []:
            if item.get('Desc'): notices.append(item['Desc'])
    except Exception:
        pass
    if props.get('serviceDisruption') and props['serviceDisruption'] not in notices:
        notices.insert(0, props['serviceDisruption'])
    ferry.append({'id': fid, 'route': d.get('filterAndOrderProperty1'), 'status': props.get('status') or '',
                  'notices': notices, 'updated': d.get('lastUpdated')})
icons = get('https://newengland511.org/map/mapIcons/FerryTerminals')
if icons and icons.get('item2'):
    colour = {it['itemId']: re.sub(r'.*map_ferry(\w+)\.svg', r'\1', it.get('icon', {}).get('url', '')).lower() for it in icons['item2']}
    for f in ferry: f['icon'] = colour.get(f['id'], '')
if ferry: data['ferry511'] = ferry

sections = [k for k in data if k not in ('generatedAt', 'alerts')]
if not sections:
    print('no feed answered; leaving the existing file alone', file=sys.stderr); sys.exit(1)
with open(OUT_PATH, 'w') as fh: json.dump(data, fh, separators=(',', ':'))
print('wrote', OUT_PATH, os.path.getsize(OUT_PATH), 'bytes; sections:', ', '.join(k for k in data if k != 'generatedAt'))
