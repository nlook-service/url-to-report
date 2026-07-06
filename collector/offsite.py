#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
homepage-diagnostic — off-site insight probe.

Given a homepage URL, this collects the business's public OFF-SITE footprint —
the data a plain <head> fetch can never reach: Naver blog review volume, Naver
Place review count, etc. It seeds itself from the homepage JSON-LD
(business name + Naver Place id in same_as/has_map).

Reach technique follows insane-search's `references/naver.md` (curl_cffi TLS
impersonation + cookie warming). We DEPEND on curl_cffi (a public library); we do
NOT copy insane-search code. If curl_cffi is absent, each probe degrades to
{"grade": "no-data"} with a verification URL — never a guess.

Honesty: a number READ on a public page = fact (with source URL). A number we
could not read = no-data. Tone/volume is a fact; quality is not.

Usage:
  python3 collector/offsite.py https://your-site.com
  python3 collector/offsite.py https://your-site.com --json offsite.json
"""
import sys, os, re, json
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import collect  # reuse the on-site collector for seeds


def _session():
    try:
        from curl_cffi import requests
    except Exception:
        return None
    s = requests.Session(impersonate="chrome124")
    s.headers.update({"Accept-Language": "ko-KR,ko;q=0.9", "Referer": "https://www.google.com/"})
    try:
        s.get("https://www.naver.com/", timeout=10)  # cookie warm (naver.md)
    except Exception:
        pass
    return s


def _nodata(need, url):
    return {"grade": "no-data", "need": need, "verify_url": url, "value": None}


def naver_blog_signal(s, name):
    """Public blog review VOLUME + sample post URLs (tone is fact, quality is not)."""
    q = quote(name)
    url = "https://search.naver.com/search.naver?where=blog&query=%s" % q
    if s is None:
        return _nodata("자체·협찬 블로그 후기 volume", url)
    try:
        html = s.get(url, timeout=12).text
    except Exception as e:
        return {"grade": "no-data", "error": str(e), "verify_url": url, "value": None}
    posts = re.findall(r"blog\.naver\.com/([\w-]+)/(\d+)", html)
    uniq = []
    seen = set()
    for b, n in posts:
        key = "%s/%s" % (b, n)
        if key not in seen:
            seen.add(key); uniq.append("https://blog.naver.com/%s/%s" % (b, n))
    return {
        "grade": "fact",
        "source_url": url,
        "mention_count": html.count(name),
        "blog_post_links": len(uniq),
        "sample_posts": uniq[:5],
        "note": "존재/volume/tone은 사실. 품질·평판은 추정하지 말 것.",
    }


def naver_place_signal(s, place_id):
    """Review count as printed on the public place page (label what it counts)."""
    url = "https://m.place.naver.com/restaurant/%s/home" % place_id
    if s is None:
        return _nodata("네이버 플레이스 리뷰 수·평점", url)
    try:
        html = s.get(url, timeout=12).text
    except Exception as e:
        return {"grade": "no-data", "error": str(e), "verify_url": url, "value": None}
    out = {"grade": "no-data", "verify_url": url}
    for pat, lbl in [(r'"reviewCount":"?(\d+)', "review_count"),
                     (r'"visitorReviewCount":"?(\d+)', "visitor_review_count"),
                     (r'"blogCafeReviewCount":"?(\d+)', "blog_cafe_review_count"),
                     (r'"totalCount":"?(\d+)', "total_count")]:
        m = re.search(pat, html)
        if m:
            out[lbl] = int(m.group(1))
            out["grade"] = "fact"
            out["source_url"] = url
    if out["grade"] == "fact":
        out["note"] = "페이지에 표기된 수치. 무엇을 세는지(방문자/블로그 합산)는 확인 후 라벨링."
    return out


def daangn_signal(s, name):
    """당근 local-profile: discover the URL via web search (당근 own search is app-gated),
    then read 단골(followerCount)·후기(reviewCount)·별점(ratingValue) from the public page."""
    disco = "https://search.naver.com/search.naver?query=%s" % quote(name + " 당근")
    if s is None:
        return _nodata("당근 단골·후기·별점", disco)
    try:
        h = s.get(disco, timeout=12).text
    except Exception as e:
        return {"grade": "no-data", "error": str(e), "verify_url": disco, "value": None}
    m = re.search(r"https://www\.daangn\.com/kr/local-profile/[\w%\-]+/", h)
    if not m:
        return {"grade": "no-data", "need": "당근 local-profile URL (검색 미발견)", "verify_url": disco, "value": None}
    prof = m.group(0)
    try:
        ph = s.get(prof, timeout=12).text
    except Exception as e:
        return {"grade": "no-data", "error": str(e), "verify_url": prof, "value": None}
    out = {"grade": "no-data", "profile_url": prof, "verify_url": prof}
    for pat, lbl in [(r'"followerCount"\s*:\s*"?(\d+)', "단골_followers"),
                     (r'"reviewCount"\s*:\s*"?(\d+)', "후기_reviews"),
                     (r'"ratingValue"\s*:\s*"?([0-9.]+)', "별점_rating")]:
        mm = re.search(pat, ph)
        if mm:
            out[lbl] = mm.group(1)
            out["grade"] = "fact"
            out["source_url"] = prof
    if out["grade"] == "fact":
        out["note"] = "당근 공개 프로필 표기값. 단골 0 = 당근 채널 미활용 신호(사실)."
    return out


def threads_signal(s, name):
    """Threads search is JS/login-gated → not extractable via curl. Honest no-data +
    a weak web-mention proxy. Real distribution needs the app or a rendered fetch."""
    verify = "https://www.threads.com/search?q=%s" % quote(name)
    out = {"grade": "no-data", "verify_url": verify,
           "note": "스레드 검색은 앱/JS 게이트 — 분포는 앱 또는 렌더 크롤 필요."}
    if s is not None:
        try:
            web = s.get("https://search.naver.com/search.naver?query=%s" % quote(name + " 스레드"), timeout=10).text
            out["web_mention_proxy"] = web.count(name)  # weak, estimate only
            out["grade_proxy"] = "estimate"
        except Exception:
            pass
    return out


def keyword_signal(s, name, homepage_keywords):
    """검색 태그 시장: the site's declared keywords (fact) + naver autocomplete demand
    signal (best-effort). Search VOLUME needs 네이버 searchad 키워드도구 (login) → tool."""
    out = {"declared_keywords_count": len(homepage_keywords),
           "declared_keywords": homepage_keywords[:20],
           "grade": "fact",  # the site DECLARED these (cite homepage)
           "volume_grade": "no-data",
           "volume_verify": "https://searchad.naver.com (키워드도구) · https://datalab.naver.com"}
    if s is not None:
        demand = {}
        for seed in (homepage_keywords[:6] or [name]):
            try:
                j = s.get("https://ac.search.naver.com/nx/ac?q=%s&st=100&r_format=json&r_enc=UTF-8&frm=nv"
                          % quote(seed), timeout=6).json()
                sug = [i[0] for grp in j.get("items", []) for i in grp][:6]
                if sug:
                    demand[seed] = sug
            except Exception:
                pass
        if demand:
            out["autocomplete_demand"] = demand  # estimate: which seeds have live demand
    return out


def place_id_from(biz):
    for u in (biz.get("same_as") or []) + ([biz.get("has_map")] if biz.get("has_map") else []):
        m = re.search(r"place\.naver\.com/[a-z]+/(\d+)", u or "")
        if m:
            return m.group(1)
    return None


def probe(url):
    on = collect.collect(url)
    biz = on["target"].get("business_info") or {}
    name = biz.get("name") or (on["target"]["meta"].get("site_name") or {}).get("value")
    pid = place_id_from(biz)
    kw = [k for k in re.split(r"\s*,\s*", (biz.get("_keywords") or "")) if k]
    if not kw:
        # pull keywords meta straight from the fetched homepage
        try:
            import collect as _c
            _, _, _html = _c.fetch(url)
            m = re.search(r'<meta name="keywords" content="([^"]+)"', _html)
            kw = [x.strip() for x in m.group(1).split(",")] if m else []
        except Exception:
            kw = []
    s = _session()
    result = {
        "seed": {"name": name, "naver_place_id": pid, "curl_cffi": s is not None},
        "naver_blog": naver_blog_signal(s, name) if name else {"grade": "no-data", "need": "business name"},
        "naver_place": naver_place_signal(s, pid) if pid else _nodata("네이버 플레이스 id (same_as/has_map)", url),
        "daangn": daangn_signal(s, name) if name else {"grade": "no-data", "need": "business name"},
        "threads": threads_signal(s, name) if name else {"grade": "no-data", "need": "business name"},
        "keywords": keyword_signal(s, name, kw),
    }
    return result


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__); sys.exit(2)
    out = probe(args[0])
    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("wrote %s" % p)
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
