# Insight Data Sources — what to detect, where, and how honestly

The diagnostic's authority comes from **breadth of public evidence**, not from the homepage alone. This catalog lists the insight sources the skill should try, the reach technique for each, what data it yields, and its evidence grade.

> **Fetch engine, not a fork.** The hard part — getting past WAFs, mobile-only pages, and JS-rendered content — is delegated to the **[insane-search](https://github.com/fivetaku/insane-search)** engine when it is installed (`python3 -m engine <url> --json`). We **do not vendor or copy** its code; we call it as an optional transport and point to its `references/*` for per-platform technique. When it is absent, the collector falls back to a plain `urllib` fetch (homepage + JSON-LD still work; blocked/rendered sources degrade to `no-data`, never to a guess).

## Grading rule for every source below

- Read it on a public page → **사실 (fact)**, cite the URL.
- Gated behind login/app, or only inferable → **데이터 없음 (미상)** + a verification path. Never transcribe a number you did not see.
- A pattern across sources (tone, channel skew) → **추정 (estimate)**, name the sources.
- **Tone is a fact; quality is not.** "협찬 후기 다수" is verifiable; it is not proof the business is good.

Only public pages. Respect the engine's safety/robots handling. This is market-research reading, not authenticated scraping.

---

## Tier 1 — the business's own graph (seed from homepage JSON-LD `same_as` / `has_map`)

| Source | Reach technique (engine ref) | Yields (insight) | Default grade |
|---|---|---|---|
| **Naver Place** | place id from `has_map`/`same_as`; public place page | 카테고리·영업정보 확인, 예약 경로, 사진 수 | fact (listing) / **미상 (리뷰수·평점 if app-gated)** |
| **Naver Blog** (협찬/후기) | mobile URL + iPhone UA, or `rss.blog.naver.com/{id}.xml` — see insane `references/naver.md` | 후기 **톤**(협찬·체험단 패턴), 노출 빈도, 언급 키워드 | fact (톤/존재) / estimate (활용도) |
| **Instagram** (business) | public profile via engine; OGP/JSON-LD `Person`/`Organization` — see `references/metadata.md` | 계정 존재, 게시물 유무, 최근 활동, bio 링크 | fact (존재/활동) / **미상 (팔로워·인게이지먼트 if gated)** |
| **Threads** | public profile page via engine (mobile-friendly) | 계정 존재, 크로스포스트 여부, 활동성 | fact (존재/활동) / 미상 (metrics if gated) |
| **YouTube / TikTok** | public channel page, OGP | 오운드 영상 자산 유무 | fact (존재) / 미상 (조회수 if not shown) |

## Tier 2 — discovery & reputation platforms

| Source | Reach technique | Yields | Default grade |
|---|---|---|---|
| **다이닝코드 / 망고플레이트** | public profile via engine | 주소·카테고리·포지셔닝 카피, (점수는 공개 노출 시에만) | fact (profile) / **미상 (score if not public)** |
| **Kakao Map / 카카오채널** | public place page | 존재·평점 표시 여부, 채널 소식 | fact if visible / 미상 |
| **Google Maps / Business** | public place page, `?hl=ko` | 평점·리뷰 수(표기 시)·사진 | fact if visible / 미상 |
| **배달의민족 / 요기요** | public store page (mobile) via engine | 배달 운영 여부·메뉴·최소주문·(별점 표기 시) | fact (운영/메뉴) / 미상 (주문수) |
| **Press / 협회 / 뉴스** | Jina Reader (`r.jina.ai/…`) — see `references/jina.md` | 인증·수상·행사·대표 프로필 (강한 신뢰 자산) | fact (cite article) |
| **인스타 해시태그 / 지역태그** | public tag page via engine | UGC volume(게시물 수 표기 시), 지역 노출 | fact (volume if shown) / 추정 |

## Tier 3 — structured & unofficial data

| Source | Reach technique | Yields | Default grade |
|---|---|---|---|
| **JSON-LD on any page** | `metadata.md` extractor (already in our collector) | 상호·주소·시간·가격·예약·`sameAs` | fact |
| **Sitemap / RSS** | direct fetch | 사이트 구조, 콘텐츠 발행 빈도 | fact (structure) |
| **Public JSON APIs** | `references/json-api.md`, `public-api.md` | 도메인별 무인증 데이터 (예: 시세) | fact if official-ish |

---

## Confirmed techniques (validated on a real local restaurant)

These are the reach methods that actually returned data in testing. `collector/offsite.py`
implements them (curl_cffi TLS-impersonation + naver.com cookie-warming, per
insane-search `naver.md` — a public library + a documented method, not copied code).

- **Naver blog search** `search.naver.com/search.naver?where=blog&query=<name>` →
  works. Yields **mention volume + real post URLs** (tone/volume = fact; quality ≠ fact).
  Validated: strong blog mention volume with real post URLs surfaced.
- **Naver Place** `m.place.naver.com/restaurant/<id>/home` → the initial HTML embeds
  `reviewCount` / `totalCount` embedded in the initial HTML. Label
  what it counts (visitor vs blog) before presenting; if the field is absent → 미상.
- **Generic `engine.fetch`** confirms the homepage (`fetch_engine: insane-search`) but
  returns `ok=False` on Naver *search/place* because the useful data is JS/API-loaded —
  that is why `offsite.py` uses the naver.md recipe directly for those hosts.
- **당근 local-profile** → discover the URL via web search (당근's own search is app-gated,
  404), then read the public profile: it embeds a full **LocalBusiness JSON-LD** with
  `review[]` (author, date, rating), `followerCount` (단골), `reviewCount`, price range.
  Validated: 단골(followerCount)·후기·별점·가격대·리뷰 날짜·소식 수가 공개 JSON-LD로 노출됨.
  (예: 단골 수가 0이면 "당근 채널 미활용" 같은 actionable fact — 모두 표기값 기반.)
- **Threads** → search page is JS/login-gated; curl gets a 548KB app shell with 0 results.
  Distribution stays **미상** (needs the app or a Playwright render). Web-mention count is a
  weak estimate proxy only.
- **Keyword / 검색 태그 시장** → the homepage's `keywords` meta is a **fact** (what the site
  targets, e.g. a couple dozen declared keywords), and Naver autocomplete (`ac.search.naver.com`, unauth)
  gives a **demand signal** (which seeds actually autocomplete). Real search **volume** needs
  네이버 searchad 키워드도구 (login) → **도구/미상**. Note: Google ignores `keywords` meta —
  it is a targeting hint, not an SEO ranking factor.
- **Dependency:** these need `curl_cffi` (auto-installed by the insane-search skill). If
  it is missing, every off-site probe returns `no-data` + a verify URL — never a guess.

> Legal/ethical: public pages only, read for market-research analysis. Respect each
> platform's robots/rate limits. Do not authenticate, and do not present a scraped
> number as more certain than "표기된 값".

## Search exposure frequency (name-first — no homepage needed)

The homepage is a seed, not the footprint. `collector/exposure.py` measures how often the **name** appears across search, so it works even when there is no site:

| Vertical | Signal | Grade |
|---|---|---|
| 네이버 통합검색 | 언급 수, 결과 폭 | fact |
| 네이버 블로그 | 후기 포스트 수 (톤=fact, 품질≠fact) | fact |
| 네이버 카페 / 지식iN | 커뮤니티 언급 | fact |
| 네이버 뉴스 | 언론 노출 수 | fact |
| 네이버 이미지 | 이미지 노출 수 | fact |
| 자동완성 (ac.search.naver) | 검색 수요 존재 | estimate |
| **Google** | 노출·순위 | **미상 → GSC 토큰** (공개검색 봇 차단) |

These roll up into a transparent **exposure-frequency score** (inputs shown) that feeds the 발견성 axis — measurable across blog · news · 지식iN · image · cafe. A homepage-less business is scored the same way from its name (Google exposure is separate, via GSC).

## Authenticated connectors (optional — owner token required)

Some of the most valuable data is **owner-gated**: it lives in the site owner's console and cannot be read from the public web at any reach level. These are NOT bypassable by the fetch engine — they need the owner's auth token. Without a token they stay `no-data` + a verification path; with one, they upgrade to **fact**.

| Connector | Upgrades to fact | Auth | API |
|---|---|---|---|
| **Google Search Console** | 검색어별 노출·클릭·CTR·평균순위, 색인 상태, CWV | Google OAuth (verified owner) | Search Analytics API `searchanalytics.query` |
| **Naver Search Advisor** (searchadvisor.naver.com) | 네이버 유입 키워드·노출·클릭, 색인/수집 현황 | 네이버 로그인 + 소유확인 | 제한적 API / 콘솔 export |
| **Bing Webmaster** | 빙 검색 쿼리·순위 | 계정 토큰 | Webmaster API |
| **GA4** | 유입 채널·전환·재방문 | Google OAuth (property access) | Data API |

**Detecting registration from the outside (fact, no token):** the homepage `<head>` often already carries `google-site-verification` and `naver-site-verification` meta tags. Their *presence* is a public fact — it means the site is **already verified/registered** with GSC / 서치어드바이저, so the console data exists; only the token to *read* it is missing. Report this as a fact ("이미 등록됨") and route the actual metrics to the verification map as "도구/내부 (토큰)".

> Common case: a homepage already carries both `google-site-verification` and `naver-site-verification` tags → registered on both; keyword volume/rank still stays 미상 until the owner supplies a token.

The registration checklist (sitemap.xml, robots.txt, favicon, Open Graph, JSON-LD, GSC/서치어드바이저 소유확인) is itself an auditable **SEO hygiene** section — grade each item fact/미검출 from what the collector actually found.

## How the skill uses this

1. **Seed** from homepage JSON-LD (`same_as`, `has_map`, name, geo).
2. For each Tier-1/2 source that applies, attempt fetch **through the engine** (so Instagram/Threads/Naver are reachable, not blocked).
3. Record each hit as a **numbered citation**; record each miss as `미상` + the exact URL to check.
4. Turn the set into the report's **Verified Facts** (cited), **Scorecard** (오운드 채널·평판 rows graded from what was actually reachable), and **Verification Map** (the misses).

The point of the engine is **reach**: without it, "오운드 채널 활용" and "리뷰 평판" collapse to 미상 because we couldn't even load the page. With it, those become graded facts backed by a link. Reach changes the grade; it never changes the honesty rules.
