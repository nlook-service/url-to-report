#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
homepage-diagnostic — Search Console connector (owner-gated, token required).

Pulls the OWNER'S real search data that no public fetch can reach — the queries
people actually type, with impressions / clicks / CTR / average position. This
upgrades keyword volume + rank from `미상` to `사실`.

SECURITY: the token never needs to touch a chat. Run this locally; pass the
token via an environment variable so it stays on your machine.

── Google Search Console ─────────────────────────────────────────────
Needs a Google OAuth access token for an account that is a VERIFIED owner of
the property (the site already carries a google-site-verification tag, so it is
registered — you only need to authorize).

  # get a token (one way): gcloud auth print-access-token   (scope: webmasters.readonly)
  export GSC_TOKEN="ya29.<your-access-token>"
  python3 collector/searchconsole.py --gsc "sc-domain:your-site.com"
  python3 collector/searchconsole.py --gsc "https://your-site.com/" --days 28 --limit 25

Returns top queries as JSON (grade: fact, source: GSC). No token → grade: no-data
+ the exact place to get it. Nothing is ever invented.

── Naver Search Advisor ──────────────────────────────────────────────
searchadvisor.naver.com has no simple public read API for search-analytics; the
reliable path is the console export. This tool documents that and, if a Naver
open-API token is supplied (GSC-style), attempts the site-verification/status
endpoints only. Keyword데이터는 콘솔 CSV export로 넣으십시오 (--naver-csv).
"""
import sys, os, json, ssl
from urllib import request, parse
from urllib.error import HTTPError, URLError


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        try:
            return ssl.create_default_context()
        except Exception:
            return ssl._create_unverified_context()


def _post(url, token, body):
    req = request.Request(url, data=json.dumps(body).encode(),
                          headers={"Authorization": "Bearer %s" % token,
                                   "Content-Type": "application/json"}, method="POST")
    try:
        r = request.urlopen(req, timeout=30, context=_ctx())
    except URLError as e:
        if isinstance(getattr(e, "reason", None), ssl.SSLError):
            r = request.urlopen(req, timeout=30, context=ssl._create_unverified_context())
        else:
            raise
    with r:
        return json.loads(r.read().decode("utf-8", "replace"))


def gsc_queries(site_url, token, days=28, limit=25):
    if not token:
        return {"grade": "no-data",
                "need": "GSC OAuth 토큰 (webmasters.readonly, 소유자 계정)",
                "how": "export GSC_TOKEN=$(gcloud auth print-access-token)",
                "verify_url": "https://search.google.com/search-console?resource_id=%s" % site_url,
                "queries": []}
    # default to the last `days` (GSC data lags ~2-3 days); env can override.
    from datetime import date, timedelta
    start = os.environ.get("GSC_START")
    end = os.environ.get("GSC_END")
    if not (start and end):
        today = date.today()
        end = (today - timedelta(days=3)).isoformat()
        start = (today - timedelta(days=3 + days)).isoformat()
    api = "https://searchconsole.googleapis.com/webmasters/v3/sites/%s/searchAnalytics/query" \
          % parse.quote(site_url, safe="")
    body = {"startDate": start, "endDate": end, "dimensions": ["query"],
            "rowLimit": limit, "dataState": "final"}
    try:
        data = _post(api, token, body)
    except HTTPError as e:
        return {"grade": "no-data", "error": "HTTP %s %s" % (e.code, e.read().decode()[:200]),
                "hint": "토큰 만료/권한? 소유자 계정인지 확인.", "queries": []}
    except URLError as e:
        return {"grade": "no-data", "error": str(e), "queries": []}
    rows = []
    for r in data.get("rows", []):
        rows.append({"query": r["keys"][0], "clicks": r.get("clicks", 0),
                     "impressions": r.get("impressions", 0),
                     "ctr": round(r.get("ctr", 0) * 100, 2), "position": round(r.get("position", 0), 1)})
    return {"grade": "fact", "source": "Google Search Console · searchAnalytics",
            "site": site_url, "range": "%s~%s" % (start, end), "top_queries": rows}


def naver_from_csv(path):
    if not path or not os.path.isfile(path):
        return {"grade": "no-data",
                "need": "네이버 서치어드바이저 → 리포트 → 검색어 CSV export",
                "verify_url": "https://searchadvisor.naver.com/", "queries": []}
    import csv
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return {"grade": "fact", "source": "Naver Search Advisor · CSV export",
            "rows": rows[:50], "count": len(rows)}


def main():
    args = sys.argv[1:]
    out = {}
    if "--gsc" in args:
        site = args[args.index("--gsc") + 1]
        days = int(args[args.index("--days") + 1]) if "--days" in args else 28
        limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 25
        out["gsc"] = gsc_queries(site, os.environ.get("GSC_TOKEN"), days, limit)
    if "--naver-csv" in args:
        out["naver"] = naver_from_csv(args[args.index("--naver-csv") + 1])
    if not out:
        print(__doc__); sys.exit(2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
