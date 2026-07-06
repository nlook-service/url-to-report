#!/usr/bin/env bash
# homepage-diagnostic — functional test harness.
# Runs the reference collector against one or more URLs and prints a result-value
# table you can diff over time to see whether the pipeline improved.
#
# Usage:
#   bash tests/run.sh                         # default fixtures
#   bash tests/run.sh https://your-site.com   # ad-hoc URL(s)
set -u
cd "$(dirname "$0")/.."

COLLECT="collector/collect.py"
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 required" >&2; exit 1
fi

RENDER=0
OFFSITE=0
ARGS=()
for a in "$@"; do
  if [ "$a" = "--render" ]; then RENDER=1
  elif [ "$a" = "--offsite" ]; then OFFSITE=1
  else ARGS+=("$a"); fi
done
URLS=("${ARGS[@]}")
if [ "${#URLS[@]}" -eq 0 ]; then
  URLS=("https://your-site.com")
fi

echo "homepage-diagnostic · collector result values"
echo "============================================="
fails=0
for u in "${URLS[@]}"; do
  echo
  echo "▶ $u"
  out=$(python3 "$COLLECT" "$u" --score 2>&1)
  if echo "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(1 if d.get("error") else 0)' 2>/dev/null; then
    echo "$out" | python3 -c '
import sys, json
d = json.load(sys.stdin)
order = ["status","fetch_engine","render_required","meta_fields","seo_flags_pass","jsonld_blocks",
         "business_info","sitemap_pages","research_seeds","gradeable_facts"]
for k in order:
    print("   %-18s %s" % (k, d.get(k)))
'
    if [ "$RENDER" -eq 1 ]; then
      slug=$(echo "$u" | sed -E 's#https?://##; s#/.*##; s#[^a-zA-Z0-9]#-#g')
      mkdir -p examples/output
      python3 collector/render.py "$u" -o "examples/output/${slug}.draft.html" 2>&1 | sed 's/^/   ↳ /'
      python3 collector/collect.py "$u" --json "examples/output/${slug}.collect.json" >/dev/null 2>&1 \
        && echo "   ↳ wrote examples/output/${slug}.collect.json"
    fi
    if [ "$OFFSITE" -eq 1 ]; then
      slug=$(echo "$u" | sed -E 's#https?://##; s#/.*##; s#[^a-zA-Z0-9]#-#g')
      mkdir -p examples/output
      python3 collector/offsite.py "$u" --json "examples/output/${slug}.offsite.json" >/dev/null 2>&1
      python3 -c '
import json,sys
d=json.load(open("examples/output/'"${slug}"'.offsite.json"))
b=d.get("naver_blog",{}); p=d.get("naver_place",{})
print("   off-site (engine):")
print("     naver_blog     %s · mentions=%s posts=%s" % (b.get("grade"), b.get("mention_count"), b.get("blog_post_links")))
print("     naver_place    %s · review_count=%s total=%s" % (p.get("grade"), p.get("review_count"), p.get("total_count")))
print("     curl_cffi=%s (없으면 no-data로 정직 처리)" % d.get("seed",{}).get("curl_cffi"))
' 2>/dev/null || echo "     (offsite probe unavailable)"
    fi
  else
    echo "   ✗ $out"
    fails=$((fails+1))
  fi
done
echo
echo "---------------------------------------------"
echo "Legend: meta_fields = <head> fields present · seo_flags_pass = hygiene checks ok"
echo "        business_info = JSON-LD facts filled · research_seeds = off-site links (sameAs/hasMap)"
echo "        gradeable_facts = total 사실-grade items the report can cite (higher = richer report)"
[ "$fails" -eq 0 ] && echo "OK" || { echo "FAIL ($fails url error(s))"; exit 1; }
