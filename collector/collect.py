#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
homepage-diagnostic — reference collector (stdlib only).

Emulates pipeline Step 1-2: fetch the homepage <head>, parse meta + JSON-LD
business_info + seo_flags, detect SPA, read sitemap. Emits JSON conforming to
references/meta-schema.json, plus a --score metrics summary you can diff over time.

This is the FACT layer. It never invents values: absent field => null + a flag.
Estimates/analysis are the skill's job, not the collector's.

Usage:
  python3 collect.py https://example.com            # print collector JSON
  python3 collect.py https://example.com --score     # print metrics summary (result values)
  python3 collect.py https://example.com --score --json out.json
"""
import sys, os, re, json, socket, ipaddress, ssl
from urllib import request, parse
from urllib.error import URLError, HTTPError

UA = "homepage-diagnostic-collector/1.0 (+https://nlook.me)"
TIMEOUT = 15

# TLS context: prefer verified (certifi if present), fall back to unverified for
# public-page collection on hosts with an incomplete local CA bundle (common on macOS).
def _ssl_ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        try:
            return ssl.create_default_context()
        except Exception:
            return ssl._create_unverified_context()

SSL_CTX = _ssl_ctx()


# ---------- safety ----------
def guard(u: str) -> str:
    p = parse.urlsplit(u if "://" in u else "https://" + u)
    if p.scheme not in ("http", "https"):
        raise ValueError("scheme must be http/https")
    host = p.hostname or ""
    try:
        for res in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(res[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError("blocked private/loopback host (SSRF guard): %s" % host)
    except socket.gaierror:
        pass  # let the fetch surface the DNS error
    return parse.urlunsplit(("https", p.netloc, p.path or "/", p.query, ""))


# ---- fetch engine (optional: insane-search) ----
# We DELEGATE hard fetches (WAF, mobile-only, JS-rendered, Instagram/Threads/Naver)
# to the insane-search engine when it is installed. We do NOT vendor its code —
# we import it. When absent, we fall back to a plain urllib GET.
#   https://github.com/fivetaku/insane-search
ENGINE_USED = "stdlib"

def _find_engine():
    import glob
    cands = []
    env = os.environ.get("INSANE_SEARCH_HOME")
    if env:
        cands.append(os.path.join(env, "engine"))
        cands.append(os.path.join(env, "skills", "insane-search", "engine"))
    for base in ("~/.claude/skills/insane-search", "~/.codex/skills/insane-search",
                 "~/.claude/plugins/*/skills/insane-search"):
        for p in glob.glob(os.path.expanduser(base)):
            cands.append(os.path.join(p, "engine"))
    for c in cands:
        if os.path.isdir(c) and os.path.isfile(os.path.join(c, "__init__.py")):
            return os.path.dirname(c)  # parent so `import engine` works
    return None

def _engine_fetch(u: str):
    """Try the insane-search engine. Returns (code, final_url, html) or None to fall back."""
    parent = _find_engine()
    if not parent:
        return None
    try:
        if parent not in sys.path:
            sys.path.insert(0, parent)
        import engine  # noqa
        res = engine.fetch(u, timeout=TIMEOUT)
        html = getattr(res, "content", None) or getattr(res, "text", None)
        ok = getattr(res, "ok", None)
        if html and (ok is None or ok):
            global ENGINE_USED
            ENGINE_USED = "insane-search"
            final = getattr(res, "final_url", None) or getattr(res, "url", u)
            code = getattr(res, "status", None) or 200
            return int(code), final, html
    except Exception:
        return None
    return None


def _stdlib_fetch(u: str):
    req = request.Request(u, headers={"User-Agent": UA})
    try:
        r = request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX)
    except URLError as e:
        if isinstance(getattr(e, "reason", None), ssl.SSLError):
            r = request.urlopen(req, timeout=TIMEOUT, context=ssl._create_unverified_context())
        else:
            raise
    body = r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    return r.getcode(), r.geturl(), body


def fetch(u: str, engine_mode: str = "auto"):
    # engine_mode: auto (engine if present, else stdlib) | insane (engine only) | stdlib
    if engine_mode in ("auto", "insane"):
        got = _engine_fetch(u)
        if got:
            return got
        if engine_mode == "insane":
            raise URLError("insane-search engine not available (set INSANE_SEARCH_HOME or install the skill)")
    return _stdlib_fetch(u)


# ---------- parse ----------
def _attr(tag: str, name: str):
    m = re.search(r'%s\s*=\s*"([^"]*)"' % name, tag, re.I) or \
        re.search(r"%s\s*=\s*'([^']*)'" % name, tag, re.I)
    return m.group(1).strip() if m else None


def _meta(html: str, key_attr: str, key_val: str):
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        if (_attr(tag, "property") or _attr(tag, "name") or "").lower() == key_val.lower():
            v = _attr(tag, "content")
            if v and v.strip():
                return v.strip()
    return None


def field(value, source):
    return {"value": value, "source": source if value is not None else None}


def parse_meta(html: str):
    head = html.split("</head>", 1)[0]
    title_og = _meta(head, "property", "og:title")
    title_tag = None
    mt = re.search(r"<title[^>]*>(.*?)</title>", head, re.I | re.S)
    if mt:
        title_tag = re.sub(r"\s+", " ", mt.group(1)).strip() or None
    title = field(title_og, "og:title") if title_og else field(title_tag, "title-tag")

    desc = _meta(head, "name", "description")
    desc_src = "meta:description"
    if not desc:
        desc = _meta(head, "name", "twitter:description")
        desc_src = "twitter:description"

    og_img = _meta(head, "property", "og:image")
    def _int(v):
        try: return int(v)
        except (TypeError, ValueError): return None
    ogw = _int(_meta(head, "property", "og:image:width"))
    ogh = _int(_meta(head, "property", "og:image:height"))

    jsonld = []
    for m in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', head + html, re.I | re.S):
        try:
            jsonld.append(json.loads(m.strip()))
        except Exception:
            pass

    canonical = _attr(
        next((t for t in re.findall(r"<link\b[^>]*>", head, re.I)
              if (_attr(t, "rel") or "").lower() == "canonical"), ""), "href")
    favicon = None
    for t in re.findall(r"<link\b[^>]*>", head, re.I):
        if "icon" in (_attr(t, "rel") or "").lower():
            favicon = _attr(t, "href"); break

    meta = {
        "title": title,
        "description": field(desc, desc_src),
        "site_name": field(_meta(head, "property", "og:site_name"), "og:site_name"),
        "canonical": field(canonical, "link:canonical"),
        "locale": field(_meta(head, "property", "og:locale"), "og:locale"),
        "theme_color": field(_meta(head, "name", "theme-color"), "theme-color"),
        "favicon": field(favicon, "link:icon"),
        "twitter_card": field(_meta(head, "name", "twitter:card"), "twitter:card"),
        "og_image": {"url": og_img, "width": ogw, "height": ogh,
                     "type": _meta(head, "property", "og:image:type"),
                     "alt": _meta(head, "property", "og:image:alt")},
        "jsonld": jsonld,
    }
    return meta


def parse_business_info(jsonld):
    biz = next((o for o in jsonld if isinstance(o, dict)
                and "restaurant" in str(o.get("@type", "")).lower()
                or (isinstance(o, dict) and "localbusiness" in str(o.get("@type", "")).lower())), None)
    if not biz:
        biz = next((o for o in jsonld if isinstance(o, dict) and o.get("address")), None)
    if not biz:
        return None
    addr = biz.get("address") or {}
    if isinstance(addr, dict):
        addr = " ".join(str(addr.get(k, "")) for k in
                        ("streetAddress", "addressLocality", "addressRegion") if addr.get(k)).strip() or None
    geo = biz.get("geo") or {}
    hours = []
    for h in (biz.get("openingHoursSpecification") or []):
        if isinstance(h, dict) and h.get("opens"):
            hours.append("%s-%s" % (h.get("opens"), h.get("closes")))
    same = biz.get("sameAs") or []
    if isinstance(same, str):
        same = [same]
    return {
        "name": biz.get("name"),
        "alternate_name": biz.get("alternateName"),
        "address": addr,
        "geo": {"lat": geo.get("latitude"), "lng": geo.get("longitude")} if geo else None,
        "telephone": biz.get("telephone"),
        "price_range": biz.get("priceRange"),
        "serves_cuisine": biz.get("servesCuisine") if isinstance(biz.get("servesCuisine"), list) else ([biz["servesCuisine"]] if biz.get("servesCuisine") else []),
        "opening_hours": hours,
        "accepts_reservations": biz.get("acceptsReservations"),
        "founding_date": biz.get("foundingDate"),
        "same_as": same,
        "has_map": biz.get("hasMap"),
    }


def seo_flags(meta):
    og = meta["og_image"]
    title = (meta["title"]["value"] or "")
    desc = (meta["description"]["value"] or "")
    dims_ok = bool(og["width"] and og["height"] and og["width"] >= 600 and 1.7 <= (og["width"] / og["height"]) <= 2.1)
    return {
        "has_og_image": bool(og["url"]),
        "og_image_dimensions_ok": dims_ok,
        "has_jsonld": len(meta["jsonld"]) > 0,
        "has_standard_description": bool(desc),
        "title_length_ok": 10 <= len(title) <= 60,
        "has_canonical": bool(meta["canonical"]["value"]),
        "has_favicon": bool(meta["favicon"]["value"]),
    }


def detect_spa(html: str) -> bool:
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.I | re.S)
    body = body.group(1) if body else html
    text = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    scripts = "".join(re.findall(r"<script.*?</script>", html, flags=re.S))
    return len(text) < 400 and len(scripts) > 2000


def read_sitemap(base: str):
    try:
        u = parse.urljoin(base, "/sitemap.xml")
        code, _, body = fetch(u)
        if code != 200:
            return False, []
        locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", body)
        return True, locs
    except Exception:
        return False, []


def collect(url: str, engine_mode: str = "auto"):
    u = guard(url)
    code, final, html = fetch(u, engine_mode=engine_mode)
    meta = parse_meta(html)
    biz = parse_business_info(meta["jsonld"])
    flags = seo_flags(meta)
    spa = detect_spa(html)
    sm_used, locs = read_sitemap(final)
    base = parse.urlsplit(final)
    pages = []
    for loc in locs:
        p = parse.urlsplit(loc)
        pages.append({"path": p.path or "/", "title": None, "source": "sitemap", "render_required": None})
    site = {
        "url": u, "final_url": final, "fetched_at": None, "status": code,
        "render_required": spa, "meta": meta, "seo_flags": flags,
        "fetch_engine": ENGINE_USED,
    }
    if biz:
        site["business_info"] = biz
    return {
        "target": site,
        "crawl": {"depth": 0, "max_pages": 0, "sitemap_used": sm_used,
                  "internal_links_found": len(pages), "pages": pages,
                  "notes": (["body_thin_spa"] if spa else [])},
        "provenance": {"collector": "homepage-diagnostic/reference-collector v1",
                       "grading": {"fetched_fields": "fact",
                                   "crawl_structure": "fact", "analysis": "estimate"}},
    }


# ---------- scoring (result values) ----------
def score(out):
    site = out["target"]
    meta = site["meta"]
    fields = {k: (v["value"] is not None) for k, v in meta.items() if isinstance(v, dict) and "value" in v}
    fields_found = sum(fields.values())
    fields_total = len(fields)
    flags = site["seo_flags"]
    flags_pass = sum(1 for v in flags.values() if v)
    biz = site.get("business_info") or {}
    biz_filled = sum(1 for k, v in biz.items() if v) if biz else 0
    biz_total = len(biz) if biz else 0
    # grade-able facts = meta fields present + seo flags + business_info values + og dims
    fact_count = fields_found + flags_pass + biz_filled + (1 if meta["og_image"]["url"] else 0)
    return {
        "url": site["final_url"],
        "status": site["status"],
        "fetch_engine": site.get("fetch_engine", "stdlib"),
        "render_required": site["render_required"],
        "meta_fields": "%d/%d" % (fields_found, fields_total),
        "seo_flags_pass": "%d/%d" % (flags_pass, len(flags)),
        "jsonld_blocks": len(meta["jsonld"]),
        "business_info": ("%d/%d" % (biz_filled, biz_total)) if biz else "none",
        "sitemap_pages": len(out["crawl"]["pages"]),
        "research_seeds": len((biz.get("same_as") or [])) + (1 if biz.get("has_map") else 0) if biz else 0,
        "gradeable_facts": fact_count,
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__); sys.exit(2)
    url = args[0]
    want_score = "--score" in sys.argv
    engine_mode = "auto"
    if "--engine" in sys.argv:
        i = sys.argv.index("--engine")
        if i + 1 < len(sys.argv):
            engine_mode = sys.argv[i + 1]
    json_out = None
    if "--json" in sys.argv:
        i = sys.argv.index("--json")
        if i + 1 < len(sys.argv):
            json_out = sys.argv[i + 1]
    try:
        out = collect(url, engine_mode=engine_mode)
    except (URLError, HTTPError, ValueError) as e:
        print(json.dumps({"error": str(e), "url": url}, ensure_ascii=False))
        sys.exit(1)
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    if want_score:
        print(json.dumps(score(out), ensure_ascii=False, indent=2))
    elif not json_out:
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
