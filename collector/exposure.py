#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
homepage-diagnostic — search exposure probe (works WITHOUT a homepage).

The homepage is only a seed. A business with no site — or a thin one — still has a
real footprint across search. This measures **exposure frequency** by actually
searching the name across Naver verticals (blog / cafe / news / 지식iN / image /
통합검색) and reading autocomplete demand. Google public search is bot-gated, so
Google exposure comes from Search Console (owner token) or stays 미상.

Input is just a NAME (+ optional region). If you have a homepage, seed the name
from its JSON-LD; if you don't, pass --name directly.

Usage:
  python3 collector/exposure.py --name "브랜드명" --region "지역"
  python3 collector/exposure.py https://site.com          # seed name from homepage
"""
import sys, os, re, json
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import offsite  # reuse the warmed curl_cffi session
import collect


NAVER = {
    "통합검색": "https://search.naver.com/search.naver?query=",
    "블로그": "https://search.naver.com/search.naver?where=blog&query=",
    "카페": "https://search.naver.com/search.naver?where=article&query=",
    "뉴스": "https://search.naver.com/search.naver?where=news&query=",
    "지식iN": "https://search.naver.com/search.naver?where=kin&query=",
    "이미지": "https://search.naver.com/search.naver?where=image&query=",
}


def naver_footprint(s, name):
    out = {}
    if s is None:
        return {"grade": "no-data", "need": "curl_cffi (insane-search) for search reads"}
    for label, base in NAVER.items():
        try:
            h = s.get(base + quote(name), timeout=12).text
        except Exception as e:
            out[label] = {"error": str(e)[:60]}
            continue
        mentions = h.count(name)
        signals = {
            "mentions": mentions,
            "blog_posts": len(set(re.findall(r"blog\.naver\.com/[\w-]+/\d+", h))),
            "cafe": len(set(re.findall(r"cafe\.naver\.com/[\w/]+", h))),
            "news": len(set(re.findall(r"n\.news\.naver\.com/[\w/]+|/news/articleView", h))),
            "images": len(set(re.findall(r"(?:pstatic|phinf)\.net/[^\"']+\.(?:jpg|jpeg|png)", h))),
            "present": mentions > 0,
        }
        out[label] = signals
    out["grade"] = "fact"
    out["source_url"] = NAVER["통합검색"] + quote(name)
    return out


def naver_demand(s, seeds):
    if s is None:
        return {"grade": "no-data"}
    demand = {}
    for seed in seeds:
        try:
            j = s.get("https://ac.search.naver.com/nx/ac?q=%s&st=100&r_format=json&r_enc=UTF-8&frm=nv"
                      % quote(seed), timeout=6).json()
            sug = [i[0] for g in j.get("items", []) for i in g]
            demand[seed] = {"suggestions": sug[:6], "has_demand": bool(sug)}
        except Exception:
            demand[seed] = {"suggestions": [], "has_demand": None}
    return {"grade": "estimate", "signals": demand}


def exposure_score(nf):
    """Transparent 0-100 exposure index from Naver footprint breadth + depth."""
    if not nf or nf.get("grade") != "fact":
        return None, []
    parts = []
    uni = nf.get("통합검색", {})
    parts.append(("통합검색 언급", min(uni.get("mentions", 0) / 193 * 30, 30)))
    parts.append(("블로그 포스트", min(nf.get("블로그", {}).get("blog_posts", 0) * 3, 18)))
    parts.append(("뉴스 노출", min(nf.get("뉴스", {}).get("news", 0) * 3, 20)))
    parts.append(("지식iN 언급", min(nf.get("지식iN", {}).get("mentions", 0), 12)))
    parts.append(("이미지 노출", min(nf.get("이미지", {}).get("images", 0), 10)))
    parts.append(("카페 노출", min(nf.get("카페", {}).get("cafe", 0) * 5, 10)))
    return round(min(100, sum(p for _, p in parts))), [(n, round(p)) for n, p in parts]


def probe(name=None, region=None, url=None):
    seeds_extra = []
    if url:
        on = collect.collect(url)
        biz = on["target"].get("business_info") or {}
        name = name or biz.get("name") or (on["target"]["meta"].get("site_name") or {}).get("value")
        seeds_extra = biz.get("serves_cuisine", []) or []
    if not name:
        return {"error": "name required (or a homepage URL to seed it)"}
    s = offsite._session()
    seeds = [name] + ([region + " " + (seeds_extra[0] if seeds_extra else "맛집")] if region else [])
    nf = naver_footprint(s, name)
    score, inputs = exposure_score(nf)
    return {
        "name": name, "region": region, "seeded_from_homepage": bool(url),
        "naver_footprint": nf,
        "naver_demand": naver_demand(s, seeds + ([region + " 맛집"] if region else [])),
        "google": {"grade": "no-data",
                   "need": "Google 공개검색은 봇 차단 → Search Console 토큰 필요 (collector/searchconsole.py)",
                   "verify_url": "https://search.google.com/search-console"},
        "exposure_score": {"value": score, "grade": "fact" if score is not None else "no-data",
                           "inputs": inputs, "note": "네이버 버티컬 노출 폭·깊이의 투명 가중 합. 구글은 별도(GSC)."},
    }


def main():
    args = sys.argv[1:]
    name = args[args.index("--name") + 1] if "--name" in args else None
    region = args[args.index("--region") + 1] if "--region" in args else None
    url = next((a for a in args if a.startswith("http")), None)
    out = probe(name=name, region=region, url=url)
    if "--json" in args:
        p = args[args.index("--json") + 1]
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("wrote", p)
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
