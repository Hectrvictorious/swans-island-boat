#!/usr/bin/env python3
"""Copy the app's sealed messages from the ntfy.sh relay into site/data/sync.json.

The phones send planned trips, the Facebook reservation counts and the boat of the day through a public
ntfy.sh topic as encrypted envelopes. ntfy only keeps messages for about 12 hours, so the site's workflow
runs this every half hour and the phones read the archive for anything older. This script never sees the
family key: it only checks each envelope's shape and its key fingerprint, and keeps the archive small.

Usage: merge_sync.py site/data/sync.json   (env SYNC_TOPIC, SYNC_FP)
Prints "changed" when the file was rewritten."""
import json, os, re, subprocess, sys, time

OUT = sys.argv[1] if len(sys.argv) > 1 else 'site/data/sync.json'
TOPIC = os.environ.get('SYNC_TOPIC', '').strip()
FP = os.environ.get('SYNC_FP', '').strip()
UA = 'swans-island-boat archive (personal use)'
B64 = re.compile(r'^[A-Za-z0-9_-]+$')
DAY = 86400

if not re.fullmatch(r'[A-Za-z0-9_-]{8,64}', TOPIC) or not re.fullmatch(r'[0-9a-f]{8}', FP):
    print('SYNC_TOPIC / SYNC_FP not set; nothing to do', file=sys.stderr); sys.exit(0)

def valid(e):
    return (isinstance(e, dict) and e.get('v') == 1 and e.get('fp') == FP
            and isinstance(e.get('id'), str) and 8 <= len(e['id']) <= 40 and B64.match(e['id'])
            and e.get('k') in ('t', 'x', 'b', 'p', 'r', 'f') and isinstance(e.get('ts'), int)
            and isinstance(e.get('iv'), str) and len(e['iv']) <= 24 and B64.match(e['iv'])
            and isinstance(e.get('ct'), str) and len(e['ct']) <= 8000 and B64.match(e['ct']))

try:
    with open(OUT) as fh: archive = json.load(fh)
    raw = archive.get('events', []) if isinstance(archive, dict) else []
except FileNotFoundError:
    archive, raw = {}, []
except Exception as err:
    print('archive unreadable, starting over:', err, file=sys.stderr); archive, raw = {}, []
before = json.dumps(raw, sort_keys=True)
events = [e for e in raw if valid(e)]
have = {e['id'] for e in events}

r = subprocess.run(['curl', '-sS', '-m', '40', '-A', UA, f'https://ntfy.sh/{TOPIC}/json?poll=1&since=12h'],
                   capture_output=True, text=True, timeout=60)
if r.returncode != 0:
    print('relay did not answer:', r.stderr[:200], file=sys.stderr)
added = 0
for line in (r.stdout or '').splitlines():
    try:
        m = json.loads(line)
        if m.get('event') != 'message': continue
        e = json.loads(m.get('message') or '')
    except Exception:
        continue
    if not valid(e) or e['id'] in have: continue
    keep = {k: e[k] for k in ('v', 'fp', 'id', 'k', 'ts', 'iv', 'ct')}
    keep['rt'] = int(m.get('time') or time.time())
    events.append(keep); have.add(e['id']); added += 1

# Keep it small: trips for 400 days, ride counts for 3 years, reservation posts and package lists for 3 weeks, the last few boat and problem notes.
now = time.time()
age = lambda e: now - (e.get('rt') or e['ts'] / 1000)
trips = [e for e in events if e['k'] == 't' and age(e) < 400 * DAY]
traffic = [e for e in events if e['k'] == 'x' and age(e) < 21 * DAY]
rides = [e for e in events if e['k'] == 'r' and age(e) < 1100 * DAY]
pkgs = [e for e in events if e['k'] == 'f' and age(e) < 21 * DAY]
recent = lambda k: sorted([e for e in events if e['k'] == k], key=lambda e: e['ts'])[-6:]
events = sorted(trips + traffic + rides + pkgs + recent('b') + recent('p'), key=lambda e: e['ts'])

if json.dumps(events, sort_keys=True) != before:
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, 'w') as fh:
        json.dump({'v': 1, 'note': 'Sealed messages for the Swan’s Island Boat app. Only the family phones can read them.', 'events': events}, fh, separators=(',', ':'))
    print('changed', f'(+{added}, {len(events)} kept)')
else:
    print('unchanged', f'({len(events)} kept)')
