import requests, time, re, sys

base = 'http://127.0.0.1:5000'
print('Waiting for server...')
for i in range(10):
    try:
        r = requests.get(base + '/dashboard', timeout=2)
        if r.status_code == 200:
            break
    except Exception:
        pass
    time.sleep(0.5)
else:
    print('Server did not respond on', base)
    sys.exit(1)

s = requests.Session()
print('Logging in as doctor...')
r = s.post(base + '/login', data={'username': 'doctor', 'password': '1234'})
print('Login status:', r.status_code)

print('Fetching review page...')
r = s.get(base + '/review')
if r.status_code != 200:
    print('Failed to load review page:', r.status_code)
    sys.exit(1)

html = r.text
m = re.search(r'name="id"\s+value="(\d+)"', html)
if not m:
    print('No pending analysis found on review page.')
    sys.exit(0)

analysis_id = m.group(1)
print('Found pending analysis id:', analysis_id)

print('Submitting approval (AJAX)...')
r2 = s.post(base + '/approve', data={'id': analysis_id, 'label': 'NORMAL'}, headers={'X-Requested-With': 'XMLHttpRequest'})
print('Approve HTTP status:', r2.status_code)
try:
    print('Response:', r2.json())
except Exception:
    print('Response text:', r2.text[:400])

print('Re-fetching review page to confirm removal...')
r3 = s.get(base + '/review')
if analysis_id in r3.text:
    print('Approval DID NOT remove entry from review page.')
else:
    print('Approval removed from review page. Live flow OK.')

print('Done.')
