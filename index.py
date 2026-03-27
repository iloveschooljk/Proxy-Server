from flask import Flask, request, Response
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

BASE = "/browse?url="

TOOLBAR = '''
<div style="position:fixed;top:0;left:0;width:100%;background:#1a1a1a;padding:8px;z-index:999999;box-shadow:0 2px 8px rgba(0,0,0,0.5);display:flex;gap:8px;">
    <a href="/" style="color:#0070f3;text-decoration:none;font-weight:bold;font-family:Arial;padding:8px;">🌐 Proxy</a>
    <form method="GET" action="/browse" style="display:flex;flex:1;gap:8px;">
        <input type="text" name="url" placeholder="Search or enter URL..." style="flex:1;padding:8px;font-size:14px;background:#333;color:white;border:1px solid #555;border-radius:4px;" />
        <button type="submit" style="padding:8px 16px;background:#0070f3;color:white;border:none;border-radius:4px;cursor:pointer;">Go</button>
    </form>
</div>
<div style="height:50px;"></div>
'''

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>My Proxy</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 100px auto; padding: 20px; background: #111; color: white; }
        input { width: 70%; padding: 10px; font-size: 16px; background: #222; color: white; border: 1px solid #444; border-radius: 4px; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; background: #0070f3; color: white; border: none; border-radius: 4px; }
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

        # Inject our toolbar at the top of body
        toolbar = BeautifulSoup(TOOLBAR, 'html.parser')
        if soup.body:
            soup.body.insert(0, toolbar)

        # Rewrite all links
        for tag in soup.find_all('a', href=True):
            href = tag['href']
            if href.startswith('http'):
                tag['href'] = BASE + href
            elif href.startswith('/'):
                base_url = '/'.join(url.split('/')[:3])
                tag['href'] = BASE + base_url + href

        return Response(str(soup), content_type='text/html')

    except Exception as e:
        return f'Error: {e}', 500

handler = app
