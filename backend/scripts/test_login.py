import urllib.request, json

def do_login():
    url = 'http://127.0.0.1:5000/api/login'
    data = {'email': 'makanakakanyai@gmail.com', 'password': 'Business7mogul'}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print('STATUS', resp.getcode())
            print(resp.read().decode())
    except Exception as e:
        # Try to print response body for HTTPError
        try:
            body = e.read().decode()
            print('HTTP ERROR BODY:', body)
        except Exception:
            pass
        print('ERROR', e)
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    do_login()
