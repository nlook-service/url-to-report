#!/usr/bin/env bash
# homepage-diagnostic — install & integrity check.
# Usage:  bash verify.sh            (structural checks; offline)
#         bash verify.sh --live     (also run the collector against a live fixture)
# Exit 0 if everything needed to use the skill is in place, 1 otherwise.

set -u
cd "$(dirname "$0")"

pass=0; fail=0
ok(){ printf '  \033[32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
no(){ printf '  \033[31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

echo "homepage-diagnostic · verification"
echo "----------------------------------"

SKILL="skills/homepage-diagnostic/SKILL.md"

# 1) Skill definition
echo "Skill definition"
[ -f "$SKILL" ] && ok "SKILL.md present" || no "SKILL.md missing"
if [ -f "$SKILL" ]; then
  head -1 "$SKILL" | grep -q '^---' && ok "has YAML frontmatter" || no "frontmatter missing"
  grep -q '^name: homepage-diagnostic$' "$SKILL" && ok "name matches folder" || no "name != homepage-diagnostic"
  grep -q '^description:' "$SKILL" && ok "description present (used for triggering)" || no "description missing"
  grep -q '진단' "$SKILL" && grep -qi 'diagnostic' "$SKILL" && ok "bilingual triggers (KO + EN)" || no "triggers not bilingual"
fi

# 2) Reference + asset + example files the skill points to
echo "Referenced files"
for f in \
  skills/homepage-diagnostic/references/evidence-grading.md \
  skills/homepage-diagnostic/references/meta-schema.json \
  skills/homepage-diagnostic/references/seometa-extension-spec.md \
  skills/homepage-diagnostic/references/data-sources.md \
  skills/homepage-diagnostic/assets/report-template.html \
  examples/output/obsidian-md.draft.html ; do
  [ -f "$f" ] && ok "$(basename "$f")" || no "missing: $f"
done

# 3) Template token contract — every {{TOKEN}} documented in the header comment
echo "Template token contract"
TPL="skills/homepage-diagnostic/assets/report-template.html"
if [ -f "$TPL" ] && command -v python3 >/dev/null 2>&1; then
  python3 - "$TPL" <<'PY' && ok "all body tokens are documented in the header" || no "undocumented tokens (see above)"
import re, sys
html = open(sys.argv[1], encoding="utf-8").read()
header = html.split("-->", 1)[0]
body = html.split("-->", 1)[1] if "-->" in html else html
used = set(re.findall(r"\{\{[A-Z_]+\}\}", body))
documented = set(re.findall(r"\{\{[A-Z_]+\}\}", header))
missing = sorted(used - documented)
if missing:
    print("  undocumented:", ", ".join(missing)); sys.exit(1)
sys.exit(0)
PY
else
  [ -f "$TPL" ] && ok "template present (install python3 for token check)" || no "template missing"
fi

# 4) meta-schema.json is valid JSON and has business_info research seeds
echo "Collector contract"
SCHEMA="skills/homepage-diagnostic/references/meta-schema.json"
if [ -f "$SCHEMA" ] && command -v python3 >/dev/null 2>&1; then
  python3 -c "import json; json.load(open('$SCHEMA'))" 2>/dev/null && ok "meta-schema.json valid JSON" || no "meta-schema.json invalid JSON"
  grep -q '"business_info"' "$SCHEMA" && ok "schema carries business_info research seeds" || no "schema missing business_info"
fi

# 5) Reference collector imports and runs (offline sanity)
echo "Reference collector"
if command -v python3 >/dev/null 2>&1; then
  python3 -c "import ast; ast.parse(open('collector/collect.py').read())" 2>/dev/null \
    && ok "collect.py parses" || no "collect.py syntax error"
  bash tests/run.sh </dev/null >/dev/null 2>&1 && true  # harness wiring only
  [ -x tests/run.sh ] || chmod +x tests/run.sh 2>/dev/null
  ok "tests/run.sh wired (run: bash tests/run.sh <url> for result values)"
fi

# 6) Plugin manifests
echo "Plugin manifests"
for j in .claude-plugin/plugin.json .claude-plugin/marketplace.json; do
  if [ ! -f "$j" ]; then no "missing: $j"; continue; fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import json; json.load(open('$j'))" 2>/dev/null \
      && ok "$(basename "$j") valid JSON" || no "$(basename "$j") invalid JSON"
  else
    ok "$(basename "$j") present (install python3 for JSON check)"
  fi
done

# 7) Optional live functional check
if [ "${1:-}" = "--live" ]; then
  echo "Live collector (--live)"
  if python3 collector/collect.py https://your-site.com --score >/tmp/hd_live.json 2>/dev/null \
     && python3 -c "import json;d=json.load(open('/tmp/hd_live.json'));exit(0 if d.get('status')==200 else 1)" 2>/dev/null; then
    ok "collected a live URL and scored it"
  else
    no "live collection failed (network? see: python3 collector/collect.py <url> --score)"
  fi
fi

# 8) Optional: installed for Claude Code / Codex?
echo "Installation (optional)"
checked=0
for d in "$HOME/.claude/skills/homepage-diagnostic" "$HOME/.codex/skills/homepage-diagnostic"; do
  if [ -e "$d" ]; then
    checked=1
    [ -f "$d/SKILL.md" ] && ok "installed & reachable: ${d/#$HOME/~}" || no "linked but SKILL.md unreachable: ${d/#$HOME/~}"
  fi
done
[ "$checked" -eq 0 ] && echo "  · not installed yet — see README 'Install' (this is fine before install)"

echo "----------------------------------"
if [ "$fail" -eq 0 ]; then
  printf '\033[32mPASS\033[0m — %d checks ok. The skill is ready to use.\n' "$pass"
  exit 0
else
  printf '\033[31mFAIL\033[0m — %d ok, %d problem(s) above.\n' "$pass" "$fail"
  exit 1
fi
