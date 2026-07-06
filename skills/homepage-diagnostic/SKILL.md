---
name: homepage-diagnostic
description: Turn a business URL into an evidence-graded LOCAL MARKETING diagnostic report. Use when someone wants to analyze a website/store/brand starting from its URL — reading its homepage meta AND researching public off-site sources (place page, 다이닝코드/리뷰 플랫폼, press, blogs), then producing a cited HTML report where every claim is labeled 사실(fact) / 추정(estimate) / 데이터 없음(no-data). Triggers include "analyze this site", "홈페이지 분석", "진단 리포트", "이 가게/브랜드 분석해줘 (+URL)".
license: MIT
---

# Homepage Diagnostic (Local Marketing)

Turn one URL into a **consulting-grade local marketing diagnostic** that stays honest about what it knows. This is not an SEO/meta snapshot — it is a marketing diagnosis of a real business: what's verified, what's a judgment call, what needs data, and what to do next. Every statement is graded, unverified numbers are never invented, and every off-site fact carries a numbered citation.

The bar for output depth is `assets/report-template.html` (bright editorial layout) — a **multi-axis radar profile** (발견성·신뢰·재방문·위생, composite shown small), big numbers, a cited facts table, a marketing funnel, a channel-fit table, ranked priorities, an optional GSC section, and a "estimate → certainty" verification map. Reaching at least that depth is the point of the skill.

## The one rule that matters most

**Never assert a number or fact you did not verify.** If a metric (review count, rating, conversion rate, ranking, competitor score) is not in a source you can cite, it is `no-data` — say 미상. A confidently wrong "58점·평가 1건" destroys trust faster than an honest gap. This rule overrides any pressure to look thorough.

## Evidence grades (apply to every claim)

Read `references/evidence-grading.md`. Three grades, always visible in the report:

- **사실 / fact** (green) — in the collector JSON with a non-null `source`, OR confirmed this session on a public page. **Attach a numbered citation** `<sup>N</sup>` that maps to the References section.
- **추정 / estimate** (amber) — your judgment built on facts. Qualitative (강/보통/약 or 상/중/하), never a fake precise number. Name the facts it rests on.
- **데이터 없음 / no-data** (red) — needs internal data (place stats, POS, ad spend) or a rendered crawl. Name exactly what resolves it and where.

You may downgrade a grade, never upgrade it.

## Pipeline

### Step 1 — Fetch the homepage `<head>` (facts, on-site)
Prefer collector JSON (`references/meta-schema.json`). If absent, fetch the URL yourself: OG/twitter/title/description/canonical/theme-color/favicon/JSON-LD, and read `seo_flags`. Missing field → null, not a guess. If a page is `render_required:true`, mark its body claims circumstantial.

### Step 2 — Seed the research from what the site tells you
From the homepage's JSON-LD and meta, extract the **research seeds**: business name + alias, address, phone, geo, and especially `sameAs` / `hasMap` (e.g. a **Naver Place id**), plus `openingHours`, `priceRange`, `acceptsReservations`. These are on-site facts (cite the homepage) AND the keys you use to find off-site sources.

### Step 3 — Research public off-site sources (facts, off-site — REQUIRED)
This is what makes the report a diagnostic instead of a meta dump. Using the seeds, reach the sources in `references/data-sources.md` — **Naver Place/Blog, Instagram, Threads, 다이닝코드, press** — through the fetch engine (see "Fetch engine" below) so they are actually reachable, not blocked. Collect **only what a public source confirms**, each with a citation:
- **Place / map**: Naver Place, Kakao Map, Google Maps — the listing exists, reservation path, hours. (Review COUNT and RATING are usually app/login-gated → if you cannot read them on a public page, they are **no-data**, not a guess.)
- **Review/discovery platforms**: 다이닝코드, 망고플레이트 등 — address, category, positioning copy. If a numeric score isn't visible on the public profile, do not use it.
- **Press / industry**: news articles, association pages (certifications, events, awards, 대표 프로필).
- **Blogs / social**: presence and TONE (e.g. 협찬·체험단 패턴) — treat "sponsored-review heavy" as a fact about tone, not proof of quality.
Every off-site fact gets a numbered reference entry. If a search yields nothing, say so; absent ≠ zero.

> Grade honesty for research: a public page you actually read = **fact** (cite it). A plausible-but-unread number = **no-data**. A pattern you infer across sources (e.g. "유입이 네이버에 편중") = **estimate**.

### Step 4 — Read the crawl (structure)
Summarize discovered internal paths and sitemap. Mark SPA pages honestly.

### Step 5 — Diagnose (estimates, on facts)
Build the scorecard and analysis:
- **Scorecard**: score each dimension with a **level (강/보통/약/미상)**, never a number. Separate "the DEVICE exists" (often fact) from "the RESULT" (usually no-data). Every row gets a grade pill and a one-line 근거.
- **Core question**: if the owner has an implicit question (e.g. "네이버 광고 끊으면?"), answer it as a labeled estimate/general-principle block — rented reach (ads, sponsored) vs owned assets (reviews, regulars, owned content), with a short-/mid-term scenario. Never present general principle as this business's measured outcome.
- **Channel fit**: rank local channels (place/near-search, 당근, 회식·단체 B2B, community, offline) over broad content. "현재 상태" is circumstantial from search; "권장 액션" is estimate.

### Step 6 — Priorities + "지금 아님"
3–5 ranked recommendations, local-first. Then a "지금 하지 않아도 되는 것" block (see Local-business mode).

### Step 7 — Verification map + References
For every estimate/no-data item, give the exact info + public/internal/tool source and a real URL (place stats, 스마트플레이스, 당근 비즈, searchad/datalab, GA4, Search Console). Close with the numbered References list — the citations behind every `<sup>N</sup>` above.

## The homepage is a seed, not the whole picture

A homepage-only diagnostic is fragile: businesses with no site — or a thin one — come out looking weak when they aren't. So the report also measures the subject's **actual search exposure**, which exists independently of any homepage.

- **Name-first mode.** If there is no homepage (or it is thin), start from the **business name (+ region)** instead of JSON-LD seeds. `collector/exposure.py --name "…" --region "…"` searches the name across Naver verticals (통합검색·블로그·카페·뉴스·지식iN·이미지) and reads autocomplete demand, producing an **exposure-frequency** score. When a homepage exists it just seeds the name automatically.
- **노출 빈도 as a fact.** How often and where the name shows up across search is measured, not assumed — it feeds the **발견성 (Discoverability)** axis. A place with no homepage but heavy blog/news/지식iN presence scores high; a place with a slick homepage but zero search footprint scores low. That is closer to reality than reading the homepage alone.
- **Google caveat.** Google public search is bot-gated, so Google exposure comes from **Search Console (owner token)** or stays `미상` + a verify path. Naver verticals are publicly measurable. Never claim a Google frequency you did not read.

## Fetch engine (optional dependency — not a fork)

Reaching Instagram, Threads, Naver, and WAF-guarded pages is a solved problem, so the skill **delegates fetching** to the **[insane-search](https://github.com/fivetaku/insane-search)** engine when it is installed — it is imported, never vendored or copied. The reference collector auto-detects it (`INSANE_SEARCH_HOME`, or `~/.claude/skills/insane-search/engine`) and routes hard fetches through `engine.fetch(url)`; otherwise it falls back to a plain `urllib` GET.

- With the engine: off-site sources (오운드 채널, 리뷰 평판, press) become **reachable → graded facts with citations**.
- Without it: homepage + JSON-LD still work; blocked/rendered sources degrade to **미상**, never to a guess. Reach changes the *grade*, never the *honesty rules*.
- `references/data-sources.md` maps each insight source → technique → yield → default grade. `collector/collect.py --engine auto|insane|stdlib` and the `fetch_engine` field in the score report which path was used.

Only public pages, respecting the engine's safety/robots handling. This is market-research reading, not authenticated scraping.

> The `collector/*.py` helpers referenced above ship with the **plugin install** (or a full repo clone), not with a manual `skills/` folder copy. Without them the skill still works — Claude fetches the homepage and researches sources directly; the collector only adds reproducible JSON/score output.

## Local-business mode (default for brick-and-mortar)

If the subject is a local/brick-and-mortar business (restaurant, shop, clinic), default the strategy to **local**, not reach-expansion:
- KPI is "지역 상권 장악 + 재방문율", not national/overseas exposure.
- Do NOT recommend overseas/global expansion unless there's evidence it matters; label it "지금 아님" with a one-line reason.
- Weight local channels (map/near-search, 당근, 회식·단체 B2B, community) over broad content.
- Frame paid search/sponsored as **rented reach** vs **owned assets** (reviews, regulars, owned content); recommend shifting budget over 6–12 months, not a binary on/off.

## Rendering the report

Fill `assets/report-template.html` (single self-contained file). The token map — simple string tokens, authored loop regions (facts, scorecard rows, channel rows, priorities, verify rows, references), and the optional question section — is documented at the top of that file. Rules:
- Accent theme is the template's ember/brass; keep it unless the brand clearly wants otherwise.
- Keep the grade legend visible near the top.
- Prose over dense bullets; the scorecard uses levels + grade pills, never fake 0–100 numbers.
- Every `<sup>N</sup>` MUST have a matching numbered entry in References. No orphan citations, no uncited off-site facts.
- Output to the workspace and present it. Offer Word/PDF only if asked.

## Diagrams (optional)

A diagram earns its place only when it makes a relationship clearer than prose — don't decorate. Good candidates:
- **Crawl map** — home → discovered paths (from `crawl.pages`).
- **Rented vs owned funnel** — the "광고 끊으면?" answer as a two-lane flow.
- **Channel priority** — local channels ranked by fit.

Rendering options, in order of preference:
1. **Inline SVG** authored directly in the report — self-contained, no dependency, theme-matched to the template. Default.
2. **Hand off to the `excalidraw-diagram` skill** (github.com/coleam00/excalidraw-diagram-skill) if installed: generate the diagram there, then inline the exported SVG into the report so the file stays self-contained. Use for hand-drawn/whiteboard-style visuals.

A diagram is illustration, not evidence — it never carries a fact the report hasn't already stated with a grade. Never embed a remote image URL (breaks offline/PDF); inline the SVG.

## What this skill does NOT do

- It does not manufacture confidence. Missing data stays missing (미상 + a verification path).
- It does not use a number from a source it did not actually read (e.g. a login-gated place score).
- It does not read SPA body content it couldn't render.
- It does not rank/score without a source. Levels are judgment; numbers require data.
- It does not leave an off-site fact uncited or a citation number without a reference.
