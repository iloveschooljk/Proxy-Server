from flask import Flask, request, Response
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote, urljoin, urlparse, urlencode, parse_qs

app = Flask(__name__)

TOOLBAR = '''
<div id="__proxy_bar__" style="position:fixed;top:0;left:0;width:100%;background:#1a1a1a;padding:6px 10px;z-index:2147483647;box-shadow:0 2px 8px rgba(0,0,0,0.6);display:flex;align-items:center;gap:8px;box-sizing:border-box;font-family:Arial,sans-serif;">
    <a href="/" style="color:#0070f3;text-decoration:none;font-weight:bold;font-size:18px;padding:4px 8px;flex-shrink:0;">🌐</a>
    <form method="GET" action="/browse" style="display:flex;flex:1;gap:6px;margin:0;">
        <input type="text" name="url" placeholder="Search or enter URL..." 
               style="flex:1;padding:7px 10px;font-size:14px;background:#2a2a2a;color:white;border:1px solid #555;border-radius:5px;min-width:0;outline:none;" />
        <button type="submit" 
                style="padding:7px 16px;background:#0070f3;color:white;border:none;border-radius:5px;cursor:pointer;font-size:14px;flex-shrink:0;">Go</button>
    </form>
</div>
<div style="height:46px;"></div>
'''

HOME = '''<!DOCTYPE html>
<html>
<head>
    <title>Proxy</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; background: #111; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; gap: 20px; padding: 20px; }
        h1 { color: #0070f3; font-size: 2rem; }
        form { display: flex; width: 100%; max-width: 600px; gap: 8px; }
        input { flex: 1; padding: 12px 16px; font-size: 16px; background: #222; color: white; border: 1px solid #444; border-radius: 6px; outline: none; }
        button { padding: 12px 20px; background: #0070f3; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }
    </style>
</head>
<body>
    <h1>🌐 Web Proxy</h1>
    <form method="GET" action="/browse">
        <input type="text" name="url" placeholder="Search anything or enter a URL..." autofocus />
        <button type="submit">Go</button>
    </form>
</body>
</html>'''

def is_valid_url(s):
    try:
        result = urlparse(s)
        return result.scheme in ('http', 'https') and bool(result.netloc)
    except:
        return False

def resolve_url(input_str, base_url=None):
    s = input_str.strip()
    # Already a full valid URL
    if is_valid_url(s):
        return s
    # Relative URL - resolve against base
    if base_url and (s.startswith('/') or not s.startswith('http')):
        if s.startswith('/'):
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{s}"
    # Has a dot and no spaces - treat as domain
    if '.' in s and ' ' not in s:
        return 'https://' + s
    # Everything else - Google search
    return 'https://www.google.com/search?q=' + quote(s)

@app.route('/')
def home():
    return HOME

@app.route('/browse')
def browse():
    raw = request.args.get('url', '').strip()
    if not raw:
        return HOME
    url = resolve_url(raw)
    return fetch_and_rewrite(url)

def fetch_and_rewrite(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        resp = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
        content_type = resp.headers.get('Content-Type', 'text/html')

        # Non-HTML — return as-is (images, css, js, etc.)
        if 'text/html' not in content_type:
            return Response(resp.content, content_type=content_type)

        soup = BeautifulSoup(resp.content, 'html.parser')
        parsed_base = urlparse(url)
        base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

        # Remove existing base tags to avoid conflicts
        for tag in soup.find_all('base'):
            tag.decompose()

        # Fix viewport — only add if missing, never override
        if not soup.find('meta', attrs={'name': 'viewport'}):
            head = soup.find('head')
            if head:
                vp = soup.new_tag('meta')
                vp['name'] = 'viewport'
                vp['content'] = 'width=device-width, initial-scale=1'
                head.insert(0, vp)

        # Rewrite all <a> hrefs
        for tag in soup.find_all('a', href=True):
            href = tag['href'].strip()
            if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            if href.startswith('http'):
                full = href
            elif href.startswith('//'):
                full = 'https:' + href
            elif href.startswith('/'):
                full = base_origin + href
            else:
                full = urljoin(url, href)
            tag['href'] = '/browse?url=' + quote(full, safe='')

        # Rewrite static assets to load directly (not through proxy)
        for tag in soup.find_all(['script', 'img', 'source'], src=True):
            src = tag.get('src', '').strip()
            if src.startswith('//'):
                tag['src'] = 'https:' + src
            elif src.startswith('/') and not src.startswith('//'):
                tag['src'] = base_origin + src

        for tag in soup.find_all('link', href=True):
            href = tag.get('href', '').strip()
            if href.startswith('//'):
                tag['href'] = 'https:' + href
            elif href.startswith('/') and not href.startswith('//'):
                tag['href'] = base_origin + href

        # Rewrite srcset attributes
        for tag in soup.find_all(srcset=True):
            parts = tag['srcset'].split(',')
            new_parts = []
            for part in parts:
                bits = part.strip().split()
                if bits:
                    src = bits[0]
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = base_origin + src
                    bits[0] = src
                new_parts.append(' '.join(bits))
            tag['srcset'] = ', '.join(new_parts)

        # Inject toolbar at top of body
        if soup.body:
            toolbar_soup = BeautifulSoup(TOOLBAR, 'html.parser')
            soup.body.insert(0, toolbar_soup)

        return Response(str(soup), content_type='text/html; charset=utf-8')

    except Exception as e:
        return f'''<!DOCTYPE html>
<html><body style="background:#111;color:white;font-family:Arial;padding:40px;">
{TOOLBAR}
<h2 style="color:red;">Error loading page</h2>
<p>{str(e)}</p>
<p>Try a different URL or check your connection.</p>
</body></html>''', 500

handler = app
