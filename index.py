from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE = "/browse?url="

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>My Proxy</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #111; color: white; }
        input { width: 70%; padding: 10px; font-size: 16px; background: #222; color: white; border: 1px solid #444; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; background: #0070f3; color: white; border: none; }
    </style>
</head>
<body>
    <h2>Web Proxy</h2>
    <form method="GET" action="/browse">
        <input type="text" name="url" placeholder="https://example.com" />
        <button type="submit">Go</button>
    </form>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

@app.route('/browse')
def browse():
    url = request.args.get('url', '')
    if not url:
        return 'No URL provided', 400
    if not url.startswith('http'):
        url = 'https://' + url
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
        content_type = resp.headers.get('Content-Type', 'text/html')

        if 'text/html' not in content_type:
            return Response(resp.content, content_type=content_type)

        soup = BeautifulSoup(resp.content, 'html.parser')

        # Rewrite all links
        for tag in soup.find_all('a', href=True):
            href = tag['href']
            if href.startswith('http'):
                tag['href'] = BASE + href
            elif href.startswith('/'):
                base_url = '/'.join(url.split('/')[:3])
                tag['href'] = BASE + base_url + href

        # Rewrite form actions (so search works)
        for form in soup.find_all('form'):
            action = form.get('action', '')
            if action.startswith('http'):
                form['action'] = BASE + action
            elif action.startswith('/'):
                base_url = '/'.join(url.split('/')[:3])
                form['action'] = BASE + base_url + action
            # Add hidden field to carry url context
            hidden = soup.new_tag('input', type='hidden', name='url')
            form.append(hidden)

        return Response(str(soup), content_type='text/html')

    except Exception as e:
        return f'Error: {e}', 500
```

Also update `requirements.txt`:
```
flask
requests
bs4
