import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
import re
import sys
import time

base = 'http://127.0.0.1:5000'

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def open_url(req_or_url, data=None, headers=None, timeout=5):
    if isinstance(req_or_url, str):
        req = urllib.request.Request(req_or_url, data=data, headers=headers or {})
    else:
        req = req_or_url
    return opener.open(req, timeout=timeout)


def read_error_body(exc):
    try:
        return exc.read().decode('utf-8', errors='replace')
    except Exception:
        return ''


print('Waiting for server...')
for _ in range(10):
    try:
        r = open_url(base + '/login', timeout=2)
        if r.status == 200:
            break
    except Exception:
        pass
    time.sleep(0.5)
else:
    print('Server did not respond on', base)
    sys.exit(1)

print('Logging in as doctor...')
login_data = urllib.parse.urlencode({'username': 'doctor', 'password': '1234'}).encode('utf-8')
try:
    resp = open_url(base + '/login', data=login_data, timeout=5)
    print('Login HTTP status:', resp.status)
except urllib.error.HTTPError as e:
    print('Login failed with status:', e.code)
    body = read_error_body(e)
    if body:
        print('Login error body:\n', body[:2000])
    raise

print('Fetching review page...')
try:
    r = open_url(base + '/review', timeout=5)
    html = r.read().decode('utf-8', errors='replace')
except urllib.error.HTTPError as e:
    print('Review page returned HTTP error:', e.code)
    body = read_error_body(e)
    if body:
        print('Server error body:\n', body[:2000])
    raise

m = re.search(r'name="id"\s+value="(\d+)"', html)
if not m:
    print('No pending analysis found on review page.')
    sys.exit(0)

analysis_id = m.group(1)
print('Found pending analysis id:', analysis_id)

print('Submitting approval (AJAX)...')
approve_data = urllib.parse.urlencode({'id': analysis_id, 'label': 'NORMAL'}).encode('utf-8')
approve_req = urllib.request.Request(
    base + '/approve',
    data=approve_data,
    headers={'X-Requested-With': 'XMLHttpRequest'}
)
try:
    resp2 = open_url(approve_req, timeout=5)
    print('Approve HTTP status:', resp2.status)
    try:
        body = resp2.read().decode('utf-8', errors='replace')
        print('Response body:', body[:400])
    except Exception:
        pass
except urllib.error.HTTPError as e:
    print('Approve failed with status:', e.code)
    body = read_error_body(e)
    if body:
        print('Approve error body:\n', body[:2000])
    raise

print('Re-fetching review page to confirm removal...')
r3 = open_url(base + '/review', timeout=5)
text = r3.read().decode('utf-8', errors='replace')
if analysis_id in text:
    print('Approval DID NOT remove entry from review page.')
else:
    print('Approval removed from review page. Live flow OK.')

print('Done.')
