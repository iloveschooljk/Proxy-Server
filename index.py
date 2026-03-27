from flask import Flask, request, Response
import requests

app = Flask(__name__)

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
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        content_type = resp.headers.get('Content-Type', 'text/html')
        return Response(resp.content, content_type=content_type)
    except Exception as e:
        return f'Error: {e}', 500
