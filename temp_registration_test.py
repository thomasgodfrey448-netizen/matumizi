import urllib.request, urllib.parse, re

url = 'http://127.0.0.1:8001/accounts/register/'
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
html = opener.open(urllib.request.Request(url)).read().decode('utf-8')
match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
print('csrf', bool(match))
if not match:
    raise SystemExit('no csrf token')

csrf = match.group(1)
data = {
    'csrfmiddlewaretoken': csrf,
    'first_name': 'Test',
    'last_name': 'User',
    'username': 'testuser999',
    'phone_number': '+255123456789',
    'password': 'secret123',
    'confirm_password': 'secret123',
    'registration_code': 'INVALIDCODE',
    'department': '1',
}
encoded = urllib.parse.urlencode(data).encode('utf-8')
req = urllib.request.Request(url, data=encoded, headers={'Referer': url})
resp = opener.open(req)
print('status', resp.status)
print(resp.geturl())
print(resp.read(200).decode('utf-8', errors='ignore'))
