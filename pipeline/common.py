"""Shared fetch and text helpers for the collectors. Standard library only, so a runner needs no install."""
import gzip, html, io, json, re, time, urllib.error, urllib.request
from datetime import datetime, timezone

UA='vmax-corpus-collector/1.0'
TAG=re.compile('<[^>]+>')
BREAK=re.compile(r'</p>|<br\s*/?>|</blockquote>',re.I)
HARD=(401,403,404,410)

class Unreachable(Exception):
    """The host answered, but not with data we may collect."""

def clean_html(markup):
    """Keep paragraph breaks, drop the rest, unescape entities."""
    return html.unescape(TAG.sub('',BREAK.sub('\n',markup or ''))).strip()

def get_json(url,headers=None,timeout=30,attempts=4):
    request=urllib.request.Request(url,headers={'Accept':'application/json','Accept-Encoding':'gzip',
                                                'User-Agent':UA,**(headers or {})})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request,timeout=timeout) as response:
                raw=response.read()
                # The Stack Exchange API always gzips, whatever the request asked for.
                if response.headers.get('Content-Encoding')=='gzip':raw=gzip.decompress(raw)
                return json.loads(raw.decode('utf-8','replace'))
        except urllib.error.HTTPError as e:
            # A closed or missing endpoint will not open on a retry; only transient codes are worth one.
            if e.code in HARD:raise Unreachable(f'HTTP {e.code}') from None
            if attempt==attempts-1:raise Unreachable(f'HTTP {e.code}') from None
            time.sleep(min(16,2**attempt))
        except Exception as e:
            if attempt==attempts-1:raise Unreachable(type(e).__name__) from None
            time.sleep(min(16,2**attempt))

def iso_z(value):
    """Normalize a timestamp to UTC with a Z suffix, from an ISO string or epoch seconds."""
    if isinstance(value,(int,float)):
        moment=datetime.fromtimestamp(value,timezone.utc)
    else:
        text=str(value)
        if text.endswith('Z'):text=text[:-1]+'+00:00'
        moment=datetime.fromisoformat(text)
        if moment.tzinfo is None:moment=moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def usable(body):
    """index_corpus.normalize() rejects anything outside this range; drop it before paying for it."""
    return 40<=len(body)<=12000
