#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
homepage-diagnostic — make a rendered report fully self-contained.

Removes every external dependency so the HTML opens offline, prints to PDF, and
survives a strict CSP (e.g. published as an Artifact):
  1) drops the Google-Fonts / Pretendard <link> tags and adds a system-font
     fallback stack (Korean text uses the OS font; no network needed),
  2) inlines remote <img> (og:image, etc.) as base64 data URIs.

Full brand-font embedding is intentionally skipped — Korean webfonts are multi-MB
per weight; the system stack keeps the file small and the layout intact.

Usage:
  python3 collector/selfcontain.py report.html -o report.offline.html
"""
import sys, re, base64, ssl
from urllib import request
from urllib.error import URLError

SYS = ("-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic',"
       "'Segoe UI','Noto Sans KR',system-ui,sans-serif")
SYS_SERIF = ("'Apple SD Gothic Neo',Georgia,'Times New Roman','Nanum Myeongjo',serif")


def _fetch_bytes(url):
    try:
        ctx = ssl.create_default_context()
    except Exception:
        ctx = ssl._create_unverified_context()
    try:
        req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            r = request.urlopen(req, timeout=20, context=ctx)
        except URLError:
            r = request.urlopen(req, timeout=20, context=ssl._create_unverified_context())
        return r.read(), r.headers.get_content_type()
    except Exception:
        return None, None


def selfcontain(html):
    # 1) drop external stylesheet/font links
    html = re.sub(r'<link[^>]+(?:fonts\.googleapis|fonts\.gstatic|jsdelivr[^>]*pretendard)[^>]*>\s*', "", html, flags=re.I)
    html = re.sub(r'<link[^>]+rel="preconnect"[^>]*>\s*', "", html, flags=re.I)
    # 2) rewrite the font-family vars to system stacks (keep --display serif-ish)
    html = html.replace('--sans:"Pretendard","Noto Sans KR",-apple-system,system-ui,sans-serif;',
                        f'--sans:{SYS};')
    html = html.replace('--serif:"Noto Serif KR",serif;', f'--serif:{SYS_SERIF};')
    html = html.replace('--display:"Playfair Display",serif;', '--display:Georgia,"Times New Roman",serif;')
    # 3) inline remote images
    imgs = set(re.findall(r'<img[^>]+src="(https?://[^"]+)"', html))
    inlined = 0
    for u in imgs:
        data, ct = _fetch_bytes(u)
        if data and ct and ct.startswith("image"):
            b64 = base64.b64encode(data).decode()
            html = html.replace('src="%s"' % u, 'src="data:%s;base64,%s"' % (ct, b64))
            inlined += 1
    return html, len(imgs), inlined


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__); sys.exit(2)
    src = args[0]
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else src.replace(".html", ".offline.html")
    html = open(src, encoding="utf-8").read()
    html, total, inlined = selfcontain(html)
    open(out, "w", encoding="utf-8").write(html)
    remaining = len(re.findall(r'(?:src|href)="https?://', html))
    print("wrote %s · images inlined %d/%d · remaining external refs: %d" % (out, inlined, total, remaining))


if __name__ == "__main__":
    main()
