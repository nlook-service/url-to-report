#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
homepage-diagnostic — draft renderer.

Turns collector JSON into a DRAFT HTML report by filling ONLY the fact layer
(verified <head> + JSON-LD facts, cited to the site itself). The estimate /
strategy / channel / priority sections are marked "스킬 분석 대기" — those are
the skill's (Claude's) job, not the collector's. This lets `tests/run.sh --render`
produce a real, openable HTML you can eyeball, without inventing analysis.

Usage:
  python3 collector/render.py https://example.com -o out.html
  python3 collector/render.py --json collected.json -o out.html
"""
import sys, os, re, json, html

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, "..", "skills", "homepage-diagnostic", "assets", "report-template.html")


def esc(v):
    return html.escape(str(v)) if v is not None else ""


def split_brand(name):
    if not name:
        return "사이트", ""
    m = re.match(r"^(.*?)(\d+)\s*$", name)
    if m and m.group(1).strip():
        return m.group(1).strip(), m.group(2)
    return name, ""


def fact_item(k, v, sup=1):
    return ('<div class="fact-item"><span class="fk">%s</span>'
            '<span class="fv">%s<sup>%d</sup></span></div>' % (esc(k), esc(v), sup))


def sc_row(lbl, segs, lv, lvtxt, grade, gtxt, basis):
    return ('<div class="sc-row"><span class="sc-lbl">%s</span>'
            '<div class="sc-meta">%s<span class="lvl-text %s">%s</span>'
            '<span class="pill %s on-dark">%s</span></div>'
            '<div class="sc-basis">%s</div></div>'
            % (lbl, segs, lv, lvtxt, grade, gtxt, basis))


def segs(a, b, c):
    def s(x):
        return '<span class="seg %s"></span>' % x if x else '<span class="seg"></span>'
    return '<span class="level">%s%s%s</span>' % (s(a), s(b), s(c))


def render(out):
    tpl = open(TPL, encoding="utf-8").read()
    tpl = re.sub(r"<!--\s*LOCAL MARKETING DIAGNOSTIC.*?-->",
                 "<!-- COLLECTOR DRAFT — fact layer only; analysis pending the skill -->",
                 tpl, flags=re.S)
    site = out["target"]
    meta = site["meta"]
    biz = site.get("business_info") or {}
    flags = site["seo_flags"]

    def mv(key):
        f = meta.get(key) or {}
        return f.get("value")

    name = biz.get("name") or mv("site_name") or mv("title") or site["final_url"]
    brand, tail = split_brand(name)

    # ---- FACT ITEMS (all cite the site: 1 = JSON-LD, 2 = <head>) ----
    items = []
    if biz.get("name"):
        alt = " · 별칭 %s" % biz["alternate_name"] if biz.get("alternate_name") else ""
        items.append(fact_item("상호", "%s%s" % (biz["name"], alt)))
    if biz.get("address"):
        items.append(fact_item("주소", biz["address"]))
    if biz.get("telephone"):
        items.append(fact_item("전화", biz["telephone"]))
    if biz.get("opening_hours"):
        items.append(fact_item("영업", " · ".join(biz["opening_hours"])))
    if biz.get("price_range"):
        items.append(fact_item("가격대", biz["price_range"]))
    if biz.get("accepts_reservations") is not None:
        items.append(fact_item("예약", "예약 가능" if biz["accepts_reservations"] else "예약 정보 없음"))
    if biz.get("serves_cuisine"):
        items.append(fact_item("업종", ", ".join(biz["serves_cuisine"])))
    if biz.get("geo") and biz["geo"].get("lat"):
        items.append(fact_item("좌표", "%s, %s" % (biz["geo"]["lat"], biz["geo"]["lng"])))
    if biz.get("founding_date"):
        items.append(fact_item("창업연도(JSON-LD)", biz["founding_date"]))
    if biz.get("same_as"):
        items.append(fact_item("연동 프로필", "%d개 (sameAs)" % len(biz["same_as"])))
    # meta / seo facts cite <head> (ref 2)
    og = meta["og_image"]
    if og.get("url"):
        dim = " %sx%s" % (og["width"], og["height"]) if og.get("width") else ""
        items.append(fact_item("OG 이미지", "있음%s" % dim, 2))
    items.append(fact_item("검색 위생",
                           "메타 %d/8 · SEO 플래그 %d/7 · JSON-LD %d블록"
                           % (sum(1 for k, v in meta.items() if isinstance(v, dict) and v.get("value")),
                              sum(1 for v in flags.values() if v), len(meta["jsonld"])), 2))
    FACT_ITEMS = "".join(items)

    # ---- SCORECARD (only collector-derivable rows are graded; rest = 미상/대기) ----
    hygiene_lv = "hi" if sum(flags.values()) >= 6 else ("mid" if sum(flags.values()) >= 4 else "lo")
    hygiene_txt = {"hi": "강", "mid": "보통", "lo": "약"}[hygiene_lv]
    hygiene_seg = {"hi": segs("on-hi", "on-hi", "on-hi"),
                   "mid": segs("on-hi", "on-hi", ""), "lo": segs("on-lo", "", "")}[hygiene_lv]
    rows = [sc_row("홈페이지 메타·SEO 위생", hygiene_seg, hygiene_lv, hygiene_txt, "fact", "사실",
                   "근거: SEO 플래그 %d/7 통과.<sup>2</sup>" % sum(flags.values()))]
    if biz:
        rows.append(sc_row("구조화 데이터·플레이스 연동", segs("on-hi", "on-hi", "on-hi"), "hi", "강", "fact", "사실",
                           "근거: JSON-LD에 %s.<sup>1</sup>"
                           % ", ".join(k for k in ("address", "telephone", "opening_hours", "geo") if biz.get(k))))
    else:
        rows.append(sc_row("구조화 데이터·플레이스 연동", segs("on-lo", "", ""), "lo", "약", "est", "추정",
                           "LocalBusiness/Restaurant JSON-LD 미검출 → 검색엔진이 업체정보를 구조적으로 못 읽음."))
    for lbl in ("실제 리뷰·평판 자산", "예약·전환 성과", "오운드 채널·스토리 활용", "로컬 밀착(당근·회식)"):
        rows.append(sc_row(lbl, segs("", "", ""), "na", "미상", "none", "데이터 없음",
                           "외부 리서치·내부 데이터 필요 — 스킬 분석 단계에서 등급화."))
    SCORECARD_ROWS = "".join(rows)

    pending = ('<tr><td class="ch">— 스킬 분석 대기 —</td><td class="role">이 초안은 수집기가 채운 '
               '<b>사실 레이어</b>입니다.</td><td class="act">외부 리서치·채널 진단·우선순위는 Claude가 채웁니다.</td>'
               '<td><span class="pill on-dark est">대기</span></td></tr>')
    VERIFY_ROWS = pending
    CHANNEL_ROWS = ('<tr><td class="ch">— 스킬 분석 대기 —</td><td class="role">채널별 로컬 적합도·권장 액션</td>'
                    '<td><span class="fit mid">···</span></td><td><span class="st gap">대기</span></td>'
                    '<td class="act">Claude 분석 단계에서 채워짐</td></tr>')
    PRIORITY_ITEMS = ('<div class="p-item"><span class="rank">·</span><div><h3>스킬 분석 대기</h3>'
                      '<p>우선순위는 위 사실 + 외부 리서치를 근거로 Claude가 작성합니다. 이 초안은 '
                      '수집기가 자동 렌더한 사실 레이어입니다.</p></div></div>')

    refs = ['<div class="ref"><span class="rn">1</span><div><div class="rt">%s — 홈페이지 JSON-LD</div>'
            '<div class="rd">상호·주소·전화·영업시간·좌표·예약·연동 프로필 등</div>'
            '<a href="%s" target="_blank" rel="noopener">%s</a></div></div>'
            % (esc(name), esc(site["final_url"]), esc(site["final_url"]))]
    refs.append('<div class="ref"><span class="rn">2</span><div><div class="rt">%s — &lt;head&gt; 메타</div>'
                '<div class="rd">OG·canonical·twitter·SEO 플래그</div>'
                '<a href="%s" target="_blank" rel="noopener">%s</a></div></div>'
                % (esc(name), esc(site["final_url"]), esc(site["final_url"])))
    REFERENCE_ITEMS = "".join(refs)

    repl = {
        "{{BRAND}}": esc(brand), "{{BRAND_TAIL}}": esc(tail),
        "{{DOC_LABEL}}": "Collector Draft · 사실 레이어 (분석 전)",
        "{{HERO_EYEBROW}}": esc(", ".join(biz.get("serves_cuisine", [])) or (mv("site_name") or "")),
        "{{HERO_H1}}": "수집기가 확인한 <span class=\"accent\">사실</span>만 먼저",
        "{{HERO_THESIS}}": ("이 문서는 <b>수집기 자동 초안</b>입니다. 홈페이지 &lt;head&gt;와 JSON-LD로 "
                            "확인된 것만 사실(각주)로 채웠고, <b>추정·전략·채널·우선순위는 스킬(Claude)이 채웁니다.</b> "
                            "수집기는 없는 값을 지어내지 않습니다."),
        "{{HERO_SUBJECT}}": esc(name),
        "{{HERO_MARKET}}": esc(biz.get("address") or site["final_url"]),
        "{{HERO_DATE}}": "collector draft",
        "{{SCORECARD_SUMMARY}}": ("수집기가 채운 <b>사실</b>: 메타·구조화 데이터. 평판·전환·오운드는 "
                                  "<b>미상</b> — 스킬 분석 대기."),
        "{{FACT_ITEMS}}": FACT_ITEMS,
        "{{FACTS_NOTE}}": ("※ 이 표는 수집기(collector)가 자동 추출한 사실 레이어입니다. 리뷰 수·평점 등 "
                           "외부·내부 지표는 스킬 분석 단계에서 채워집니다."),
        "{{SCORECARD_ROWS}}": SCORECARD_ROWS,
        "{{QUESTION_SECTION}}": "",
        "{{CHANNEL_ROWS}}": CHANNEL_ROWS,
        "{{CHANNEL_NOTE}}": "채널 진단은 스킬 분석 단계에서 외부 리서치를 근거로 채워집니다.",
        "{{PRIORITY_ITEMS}}": PRIORITY_ITEMS,
        "{{NOT_NOW_TITLE}}": "분석 전 초안",
        "{{NOT_NOW_BODY}}": "우선순위·‘지금 아님’ 판단은 스킬(Claude)이 사실 + 외부 리서치를 근거로 작성합니다.",
        "{{VERIFY_ROWS}}": VERIFY_ROWS,
        "{{REFERENCE_ITEMS}}": REFERENCE_ITEMS,
        "{{FOOT_DISC}}": ("수집기 자동 초안 — 사실 레이어만 채워졌습니다. 완성 리포트는 스킬(Claude)이 "
                          "외부 공개출처 리서치·추정·전략을 더해 생성합니다."),
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    return tpl


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    out_path = None
    if "-o" in sys.argv:
        out_path = sys.argv[sys.argv.index("-o") + 1]
    if "--json" in sys.argv:
        data = json.load(open(sys.argv[sys.argv.index("--json") + 1], encoding="utf-8"))
    else:
        if not args:
            print(__doc__); sys.exit(2)
        sys.path.insert(0, HERE)
        import collect
        data = collect.collect(args[0])
    htmlout = render(data)
    if out_path:
        open(out_path, "w", encoding="utf-8").write(htmlout)
        print("wrote %s (%d bytes)" % (out_path, len(htmlout)))
    else:
        sys.stdout.write(htmlout)


if __name__ == "__main__":
    main()
