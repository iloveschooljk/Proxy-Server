from flask import Flask, request, Response
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

BASE = "/browse?url="

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>My Proxy</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #111; color: white; }
        input { width: 70%; padding: 10px; font-size: 16px; background: #222; color: white; border: 1px solid #444; border-radius: 4px; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; background: #0070f3; color: white; border: none; border-radius: 4px; }
        h2 { color: #0070f3; }
    </style>
</head>
<body>
    <h2>Web Proxy</h2>
    <form method="GET" action="/browse">
        <input type="text" name="url" placeholder="Search or enter a URL..." />
        <button type="submit">Go</button>
    </form>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML

@app.route('/search')
def search():
    # Catches Google's search form submitting q= instead of url=
    q = request.args.get('q', '').strip()
    if q:
        url = 'https://www.google.com/search?q=' + requests.utils.quote(q)
        return browse_url(url)
    return 'No query provided', 400

@app.route('/browse')
def browse():
    url = request.args.get('url', '').strip()
    if not url:
        return 'No URL provided', 400
    if ' ' in url or '.' not in url:
        url = 'https://www.google.com/search?q=' + requests.utils.quote(url)
    elif not url.startswith('http'):
        url = 'https://' + url
    return browse_url(url)

def browse_url(url):
    try:
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }, allow_redirects=True)
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

        # Rewrite all forms
        for form in soup.find_all('form'):
            action = form.get('action', '')
            method = form.get('method', 'get').lower()

            # Check if this is Google's search form
            q_input = form.find('input', {'name': 'q'})
            if q_input:
                form['action'] = '/search'
                form['method'] = 'get'
                continue

            if action.startswith('http'):
                form['action'] = BASE + action
            elif action.startswith('/'):
                base_url = '/'.join(url.split('/')[:3])
                form['action'] = BASE + base_url + action

            hidden = soup.new_tag('input')
            hidden['type'] = 'hidden'
            hidden['name'] = 'url'
            form.append(hidden)

        return Response(str(soup), content_type='text/html')

    except Exception as e:
        return f'Error: {e}', 500

handler = app
