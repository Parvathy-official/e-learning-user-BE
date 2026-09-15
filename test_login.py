import urllib.request
import json
import time

url = 'https://e-learning-user-be-x0nb.onrender.com/api/auth/login/'
payload = json.dumps({'email': 'admin@learnflow.com', 'password': 'admin123'}).encode('utf-8')
headers = {'Content-Type': 'application/json'}

for attempt in range(1, 15):
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req) as res:
            if res.status == 200:
                print(f"SUCCESS on attempt {attempt}!")
                print(res.read().decode())
                break
    except urllib.error.HTTPError as e:
        print(f"Attempt {attempt}: HTTP {e.code}")
    except Exception as e:
        print(f"Attempt {attempt}: {e}")
    time.sleep(10)
