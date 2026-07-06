# Evidence Grading

Every claim in a diagnostic report gets one of three grades, and the grade is visible to the reader. This is the skill's spine — it's what makes the report trustworthy instead of confident-sounding.

## The three grades

### 사실 / fact (green)
The claim is backed by a source you can point to.
- Present in collector JSON with a non-null `source` (e.g. `og:title`, `jsonld.name`).
- Or independently verified this session (you fetched it, a search result confirmed it).
- In the report: state it plainly, attach the source (meta tag, reference number, URL).

Examples: "OG image is 1200×630" (from `seo_flags.og_image_dimensions_ok`), "네이버 예약 가능" (confirmed on the place page).

### 추정 / estimate (amber)
Your judgment, built on facts but not itself measured.
- Always qualitative: 강 / 보통 / 약, or 상 / 중 / 하. **Never a fake precise number.**
- Must name the facts it rests on ("자체 채널이 검색에 안 잡힘 → 활용도 약").
- In the report: label it estimate and show the reasoning in one line.

Examples: "스토리 활용도 = 약", "협찬 톤이라 신뢰 전환이 약할 것", "광고를 끊으면 단기 신규 유입이 준다".

### 데이터 없음 / no-data (red)
You cannot know this without data you don't have.
- Internal analytics, POS, ad spend, or a rendered crawl.
- In the report: mark it 미상, and **always pair it with a verification path** — what info + which URL/dashboard resolves it.

Examples: "예약 전환율", "재방문율", "실제 리뷰 수·평점" (if the place page wasn't opened), SPA body content.

## Hard rules

1. **No unverified numbers.** If you're about to write a number, ask: is it in the JSON or did I verify it? If not → it's an estimate (use a level) or no-data (say 미상). This rule exists because a wrong precise number ("58점·평가 1건") destroys trust faster than an honest gap.
2. **Never upgrade a grade.** The collector's `provenance.grading` sets the ceiling: fetched=fact, crawl=circumstantial, analysis=estimate. You can be more cautious, never less.
3. **Facts get sources; estimates get reasoning; no-data gets a path.** Each grade owes the reader a different thing.
4. **Absent ≠ zero.** A missing meta field means "not found", not "they have none". Say "미검출", not "없음", unless you confirmed absence.
5. **SPA honesty.** `render_required:true` means you did not read the rendered content. Body-level claims about that page are circumstantial at best. It does **NOT** tell you the site is "CSR-only" — the shell may be thin while sub-routes are server-rendered. Never escalate one thin-shell boolean into a claim about how the whole site renders.
6. **Target-fetch failure = the report says so, loudly.** The rules above about "blocked source → no-data" apply to *off-site* sources. They apply **doubly to the diagnostic's own homepage**: if the collector returned an `error` (403/timeout/WAF) or you could not read the live `<head>` this session, you MUST (a) state the block at the top of the report and in the footer, (b) mark every on-site fact that depends on the unread page as 미상 with a verify path, and (c) NOT backfill the unread page from memory, priors, or "what a site like this usually has". A report that hides that its subject was unreadable is the worst failure this skill can produce. If a secondary source did open (e.g. `sitemap.xml` alone), scope its facts to exactly what it contained — nothing more.
7. **No stack / framework / infra claims without a source field.** The collector JSON has **no** field for framework, rendering strategy, hosting, build tooling, or "SSG/ISR". Therefore statements like "Next.js를 쓴다", "SSG/ISR가 없다", "generateMetadata를 권장" are **inventions** — the schema cannot support them. Recommend outcomes ("페이지별 정적 메타가 필요"), never a named technology you did not verify in first-party source. Naming a framework you did not confirm is a hard violation, same tier as a fake number.

## Mapping collector JSON → grades

| Source in JSON | Default grade |
|---|---|
| `meta.*` with non-null `source` | fact |
| `seo_flags.*` (booleans) | fact |
| `crawl.pages[]` structure | circumstantial (≈ fact for "these paths exist", estimate for what they contain if `render_required`) |
| anything you infer (positioning, strength, risk) | estimate |
| metrics not present (rates, counts, revenue) | no-data |

## Off-site facts & citations

Off-site research (place page, review platforms, press, blogs) is where a diagnostic earns its authority — but only if each fact is **read on a public page and cited**.

- **A public page you actually read = fact.** Attach a numbered citation `<sup>N</sup>` where N is an entry in the report's References section. Every off-site fact owes the reader a link.
- **A plausible-but-unread number = no-data.** Review counts, ratings, and platform "scores" are often app/login-gated. If you did not read it on a public page, write 미상 and route it to the verification map — never transcribe it as fact.
- **A pattern inferred across sources = estimate.** e.g. "유입이 네이버에 편중", "협찬 톤이라 신뢰 전환 약". Name the sources it rests on.
- **Tone is a fact; quality is not.** "협찬·체험단 후기가 다수" is a verifiable fact about tone. It is NOT evidence the food/service is good — keep that distinction.

### Citation hard rules
1. Every `<sup>N</sup>` in the report MUST have a matching numbered entry in References. No orphan citations.
2. Every off-site fact in the Verified Facts / Scorecard sections MUST carry a citation. An uncited off-site claim is downgraded to estimate or dropped.
3. Reference entries say **what** was drawn from them (e.g. "주소·전화·영업시간·대표 경력"), so a reader can audit each fact to its source.
4. If two sources disagree (e.g. homepage JSON-LD hours vs place-page hours), show the discrepancy — do not silently pick one.
