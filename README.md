<div align="center">

# url-to-report

### One business URL → a cited, evidence-graded local marketing diagnostic.

Ships the **`homepage-diagnostic`** skill for **Claude Code** and **OpenAI Codex** — it diagnoses a business from its **real homepage and public sources** and never invents a number it did not verify.

<p>
  <a href="https://nlook.me"><img alt="Made by nlook" src="https://img.shields.io/badge/made%20by-nlook.me-0a0a0b"></a>
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-2563eb">
  <img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-86efac">
  <img alt="Codex skill" src="https://img.shields.io/badge/Codex-skill-fcd34d">
</p>

</div>

Every claim in the report is labeled **사실 (fact)** / **추정 (estimate)** / **데이터 없음 (no-data)**. Facts drawn from off-site sources carry numbered citations. A confidently wrong "58점·평가 1건" is worse than an honest "미상" — so the skill refuses to guess.

> Built and maintained by the team behind **[nlook.me](https://nlook.me)**.

---

## Why this exists

Most "analyze this website" prompts fail the same two ways:

1. **The model invents metrics.** Review counts, ratings, conversion rates, competitor "scores" — if it wasn't read on a page you can cite, it's a hallucination. This skill grades it `데이터 없음` and hands you the exact URL to check.
2. **It stops at the homepage.** A real diagnostic reads the `<head>` **and** researches the place page, review platforms, press, and blogs — then cites each fact. Off-site evidence is where authority comes from.

For brick-and-mortar businesses it defaults to **local strategy** (지역 상권 장악 + 재방문), frames paid reach as *rented* vs *owned* assets, and marks national/overseas expansion "지금 아님" unless there's evidence.

## What you get

- A **7-step workflow**: fetch `<head>` → seed research from JSON-LD → **cited off-site research** → crawl → diagnose (levels scorecard, core-question, channel-fit) → priorities + "지금 아님" → verification map + references
- A **bright, editorial HTML report** ([template](skills/homepage-diagnostic/assets/report-template.html)): a **multi-axis radar profile** (발견성·신뢰·재방문·위생 — composite shown small, unmeasured axes left unscored), big numbers, cited facts, a marketing funnel, a channel-fit table, ranked priorities, an optional Search-Console section, an **estimate → certainty** verification map with real URLs, and numbered references
- A **reference collector** ([`collector/collect.py`](collector/collect.py), stdlib only) that turns a URL into schema-conformant JSON + a **score** you can diff over time
- A **test harness** that prints comparable **result values** per URL — so you can measure whether a change improved the output
- Neutral committed example ([`examples/output/obsidian-md.draft.html`](examples/output/obsidian-md.draft.html))

## Install

This repo is both a **Claude Code plugin** and a plain **skill folder**. Pick one path.

### Option A — Claude Code plugin (recommended)

From inside Claude Code, run these **two separate commands** — one at a time, not pasted together:

**1. Register this repo as a marketplace:**

```
/plugin marketplace add nlook-service/url-to-report
```

> If Claude Code opens an **"Add Marketplace"** dialog, type only the repo into the source field — `nlook-service/url-to-report` — **not** the `/plugin install …` line below.

**2. Install the bundled skill:**

```
/plugin install homepage-diagnostic@homepage-diagnostic
```

Restart the session and the `homepage-diagnostic` skill is available.

> Replace `nlook-service/url-to-report` with your fork's `owner/repo` if you forked it.

### Option B — Manual skill install (Claude Code **or** Codex)

Both tools read the same `SKILL.md` format and load skills from a `skills/` directory.

```bash
git clone https://github.com/nlook-service/url-to-report.git
cd url-to-report

# Claude Code (user-wide)
mkdir -p ~/.claude/skills
cp -R skills/homepage-diagnostic ~/.claude/skills/

# OpenAI Codex (user-wide)
mkdir -p ~/.codex/skills
cp -R skills/homepage-diagnostic ~/.codex/skills/
```

Then verify:

```bash
bash verify.sh
```

## Use it

In Claude Code or Codex, just point it at a URL:

```
이 가게 분석해줘 https://your-site.com
analyze this site https://example.com
```

The skill fetches the homepage, researches public sources, and renders the report to your workspace.

## Test & measure (so you can improve it)

The collector produces **result values** you can compare across sites and across versions:

```bash
bash tests/run.sh https://your-site.com
```

```
▶ https://obsidian.md          # committed neutral example
   status             200
   fetch_engine       stdlib
   render_required    False
   meta_fields        5/8        # <head> fields present
   seo_flags_pass     4/7        # hygiene checks passed
   jsonld_blocks      0
   business_info      none       # no LocalBusiness JSON-LD → thin
   sitemap_pages      0
   research_seeds     0
   gradeable_facts    10         # total 사실-grade items the report can cite
```

A local business with full `LocalBusiness` JSON-LD (address, hours, geo,
reservations, `sameAs`) scores far higher — typically 25–30 gradeable facts.

`gradeable_facts` is the headline number: **higher = a richer, more-cited report**. A site with no `LocalBusiness` JSON-LD scores lower — which tells you exactly what to add. Raw JSON for one URL:

```bash
python3 collector/collect.py https://your-site.com            # full collector JSON
python3 collector/collect.py https://your-site.com --score     # just the metrics
```

### Get an actual HTML report from the test

Add `--render` to also write a **draft HTML report** — the collector fills the
**fact layer** (verified `<head>` + JSON-LD facts, cited to the site), and marks
the estimate/strategy/channel sections "스킬 분석 대기" (those are Claude's job).

```bash
bash tests/run.sh --render https://your-site.com
# → examples/output/your-site-com.draft.html   (openable HTML)
# → examples/output/your-site-com.collect.json  (schema JSON)
```

Or one URL directly:

```bash
python3 collector/render.py https://your-site.com -o report.draft.html
```

### Example results (committed, reproducible)

[`examples/output/`](examples/output/) holds ready-to-open results you can diff
against your own runs:

| file | what it shows |
|---|---|
| `obsidian-md.draft.html` | a thin site (no LocalBusiness JSON-LD) → 10 gradeable facts |
| `obsidian-md.collect.json` | the collector JSON behind it |

> The **full** analyst report (off-site research + estimates + strategy + radar
> profile) is what the skill produces once Claude runs the research and diagnosis
> steps on top of this fact layer. Real client reports are kept out of this repo
> (they contain owner-gated data); run the skill on your own subject to generate one.

## Reaching Instagram, Threads, Naver… (fetch engine)

A diagnostic is only as good as the sources it can actually load. The homepage is
easy; **Instagram, Threads, Naver Place/Blog, and WAF-guarded pages are not.** So
the skill delegates fetching to the **[insane-search](https://github.com/fivetaku/insane-search)**
engine when it's installed — **imported as an optional dependency, never forked or
copied.** Install that skill and the collector auto-detects it:

```bash
# collector routes hard fetches through insane-search if present
python3 collector/collect.py https://your-site.com --score   # see "fetch_engine"
python3 collector/collect.py https://site.com --engine stdlib     # force plain urllib
export INSANE_SEARCH_HOME=/path/to/insane-search                  # or point at it explicitly
```

Which insight source is reached how — Naver Place/Blog, Instagram, Threads,
다이닝코드, press via Jina — is catalogued in
[`references/data-sources.md`](skills/homepage-diagnostic/references/data-sources.md),
with the evidence grade for each. **Reach changes the grade, never the honesty
rules:** a source you can't load becomes `미상` + a verification path, never a guess.

## Diagrams (optional)

The report can embed diagrams — the crawl map, the channel strategy, the
rented-vs-owned funnel. They render as **inline SVG** (self-contained, no library).
If you have the [`excalidraw-diagram`](https://github.com/coleam00/excalidraw-diagram-skill)
skill installed, the skill can hand off diagram generation to it and inline the
result. See `SKILL.md` → "Diagrams".

## Owner-gated data (Search Console)

The single most valuable data — the queries people actually type, with impressions,
clicks, CTR, and average position — lives in the owner's **Google Search Console** and
cannot be read from the public web at any reach level. `collector/searchconsole.py`
ingests it when you supply your own token (kept local, never in a prompt):

```bash
export GSC_TOKEN="ya29.<access-token-from-oauth-playground-or-gcloud>"
python3 collector/searchconsole.py --gsc "sc-domain:your-site.com" --limit 30
```

Without a token these stay `미상` + a verification path. The homepage's
`google-site-verification` / `naver-site-verification` meta tags are a public fact that
the site is **already registered** — only the read token is missing. Naver Search Advisor
data comes in via CSV export (`--naver-csv`).

## One score hides the truth — use a profile

A single "digital presence: 62" is misleading (real case: "reach 92" was Naver-only; GSC
showed Google reach near zero). So the report leads with a **multi-axis radar** — 발견성 ·
신뢰·평판 · 재방문·오운드 · 정보 위생 — each with its own confidence grade, composite shown
small, and **unmeasured axes (성과·수익) left unscored** rather than invented.

## Share it anywhere (self-contained)

```bash
python3 collector/selfcontain.py report.html -o report.offline.html
```

Inlines images and drops CDN font/CSS deps → the `.offline.html` opens with no internet,
prints to PDF, and survives a strict CSP. Send the `.offline.html` to others; keep the
plain `.html` for online hosting (nicer webfonts, smaller file).

## How it stays honest

- **No unverified numbers.** Not in a source you read → 미상 + a verification path. ([evidence-grading.md](skills/homepage-diagnostic/references/evidence-grading.md))
- **Every off-site fact is cited.** No orphan citations, no uncited claims.
- **Tone is a fact; quality is not.** "협찬 후기가 다수" is verifiable; it is not proof the food is good.
- **Absent ≠ zero.** A missing field is "미검출", not "없음".
- **SPA honesty.** Body claims about an un-rendered SPA page are circumstantial.

## Layout

```
.claude-plugin/                 plugin.json · marketplace.json
skills/homepage-diagnostic/
  SKILL.md                      the workflow
  references/                   evidence-grading · meta-schema · data-sources · collector spec
  assets/report-template.html   the radar-profile report (tokenized)
collector/                      collect · offsite · exposure · searchconsole · render · selfcontain
examples/output/                obsidian-md.* — neutral committed example
tests/run.sh                    result-value harness
verify.sh                       integrity check
```

## License

MIT — see [LICENSE](LICENSE).
