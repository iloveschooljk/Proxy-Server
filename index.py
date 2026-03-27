from flask import Flask, request, Response
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote, unquote, urlparse, urljoin

app = Flask(__name__)

def wrap(url):
    return '/browse?url=' + quote(url, safe='')

def unwrap(raw):
    # Decode any percent-encoding so we always work with a clean URL
    return unquote(raw.strip())

def is_url(s):
    if ' ' in s:
        return False
    parsed = urlparse(s)
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        return True
    # Bare domain like google.com or youtube.com
    if '.' in s and not s.startswith('.'):
        return True
    return False

TOOLBAR = '''<div id="__ptb" style="position:fixed;top:0;left:0;right:0;height:44px;background:#18181b;display:flex;align-items:center;gap:8px;padding:0 12px;z-index:2147483647;box-shadow:0 2px 10px rgba(0,0,0,0.7);font-family:Arial,sans-serif;">
  <a href="/" style="color:#3b82f6;font-size:20px;text-decoration:none;flex-shrink:0;">🌐</a>
  <form method="GET" action="/browse" style="display:flex;flex:1;gap:6px;margin:0;" onsubmit="var v=this.querySelector('input').value.trim();if(v&&v.indexOf('.')===-1&&v.indexOf(' ')===-1){this.querySelector('input').value='https://www.google.com/search?q='+encodeURIComponent(v);return true;}">
    <input name="url" type="text" placeholder="Search or enter URL..." autocomplete="off"
      style="flex:1;min-width:0;padding:6px 10px;font-size:14px;background:#27272a;color:#fff;border:1px solid #3f3f46;border-radius:5px;outline:none;" />
    <button type="submit" style="padding:6px 14px;background:#3b82f6;color:#fff;border:none;border-radius:5px;cursor:pointer;font-size:14px;flex-shrink:0;">Go</button>
  </form>
</div>
<div style="height:44px"></div>'''

HOME = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Proxy</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#09090b;color:#fff;font-family:Arial,sans-serif;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px;padding:20px}
h1{font-size:2rem;color:#3b82f6}
p{color:#a1a1aa;font-size:14px}
form{display:flex;width:100%;max-width:560px;gap:8px}
input{flex:1;padding:12px 16px;font-size:16px;background:#18181b;color:#fff;border:1px solid #3f3f46;border-radius:6px;outline:none}
button{padding:12px 20px;background:#3b82f6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:16px}
</style></head>
<body>
<h1>🌐 Proxy</h1>
<p>Type anything — a search term or a full URL</p>
<form method="GET" action="/browse">
  <input name="url" type="text" placeholder="youtube.com or search anything..." autofocus/>
  <button>Go</button>
</form>
</body></html>'''

@app.route('/')
def home():
    return HOME

@app.route('/browse')
def browse():
    raw = request.args.get('url', '').strip()
    if not raw:
        return HOME

    url = unwrap(raw)

    # If it's already a full valid URL, use it directly
    if url.startswith('http://') or url.startswith('https://'):
        pass
    elif is_url(url):
        url = 'https://' + url
    else:
        # Treat as search query
        url = 'https://www.google.com/search?q=' + quote(url)

    return fetch_page(url)

def fetch_page(url):
    try:
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }, allow_redirects=True)

        content_type = resp.headers.get('Content-Type', '')

        # Pass through non-HTML content directly
        if 'text/html' not in content_type:
            return Response(resp.content, content_type=content_type)

        final_url = resp.url
        parsed = urlparse(final_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        soup = BeautifulSoup(resp.content, 'html.parser')

        # Remove base tags
        for t in soup.find_all('base'):
            t.decompose()

        # Rewrite <a> links
        for tag in soup.find_all('a', href=True):
            href = tag['href'].strip()
            if not href or href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('#'):
                continue
            if href.startswith('//'):
                full = 'https:' + href
            elif href.startswith('http'):
                full = href
            elif href.startswith('/'):
                full = origin + href
            else:
                full = urljoin(final_url, href)
            tag['href'] = wrap(full)

        # Rewrite src attributes (load assets directly, not through proxy)
        for tag in soup.find_all(True):
            for attr in ['src', 'data-src']:
                val = tag.get(attr, '')
                if not val:
                    continue
                if val.startswith('//'):
                    tag[attr] = 'https:' + val
                elif val.startswith('/') and not val.startswith('//'):
                    tag[attr] = origin + val

        # Rewrite link hrefs (CSS etc)
        for tag in soup.find_all('link', href=True):
            href = tag['href']
            if href.startswith('//'):
                tag['href'] = 'https:' + href
            elif href.startswith('/'):
                tag['href'] = origin + href

        # Inject scale fix + toolbar
        scale_fix = soup.new_tag('style')
        scale_fix.string = '#__ptb{zoom:1!important;transform:none!important}'
        if soup.head:
            soup.head.append(scale_fix)

        if soup.body:
            tb = BeautifulSoup(TOOLBAR, 'html.parser')
            soup.body.insert(0, tb)

        return Response(str(soup), content_type='text/html; charset=utf-8')

    except Exception as e:
        return f'''<!DOCTYPE html><html><body style="background:#09090b;color:#fff;font-family:Arial;padding:60px 20px;">
{TOOLBAR}
<h2 style="color:#ef4444;margin-bottom:12px">Failed to load page</h2>
<p style="color:#a1a1aa">{str(e)}</p>
</body></html>''', 500

handler = app
