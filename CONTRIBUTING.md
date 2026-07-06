# Contributing to homepage-diagnostic

Thanks for helping improve the skill. It stays useful only if it stays **honest** —
every number in a report must be traceable to a source, or labeled 미상.

## Setup & checks

```bash
git clone https://github.com/nlook-service/url-to-report.git
cd homepage-diagnostic
bash verify.sh            # structural + token-contract + collector checks (must PASS)
bash tests/run.sh https://obsidian.md   # result values for a neutral site
```

`collector/*.py` is stdlib-only (an optional `curl_cffi` path activates when the
[insane-search](https://github.com/fivetaku/insane-search) engine is installed).

## Ground rules

- **Never invent a number.** If it isn't read from a public page you can cite, or
  from an owner-supplied token, it is `no-data` + a verification path. See
  [`references/evidence-grading.md`](skills/homepage-diagnostic/references/evidence-grading.md).
- **No client data in the repo.** Real reports contain owner-gated data (Search
  Console, place metrics). They are gitignored — keep it that way. Use a neutral
  public site (e.g. obsidian.md) for any committed example.
- **Don't vendor other projects.** Reach engines (insane-search) are imported, not copied.

## Adding a data source

1. Add a probe to `collector/offsite.py` (or `exposure.py`) that returns
   `{"grade": "fact"|"estimate"|"no-data", "source_url": ...}` — gated values must
   degrade to `no-data`, never a guess.
2. Document it in [`references/data-sources.md`](skills/homepage-diagnostic/references/data-sources.md)
   (reach technique · yield · default grade).
3. Run `bash verify.sh` and open a PR describing what it detects and its evidence grade.
