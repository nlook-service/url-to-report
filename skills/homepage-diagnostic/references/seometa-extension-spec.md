# seometa.go 확장 스펙 — Diagnostic Collector (v1)

목표: **URL 하나를 받아 `meta-schema.json` 계약에 맞는 진단용 JSON을 반환**하는 수집 층.
이 JSON이 곧 `homepage-diagnostic` 스킬의 입력이다. 수집 층은 **분석하지 않는다** — 사실만 긁고, 없으면 `null` + 플래그로 정직하게 비운다. (추정은 스킬이 한다.)

기존 seometa.go(OG/JSON-LD 처리, 마크다운 새니타이즈)를 재사용해 head 파싱 부분을 그대로 얹는다.

---

## 1. 엔드포인트

```
POST /api/diagnostic/collect
Content-Type: application/json
```

### 요청

```json
{
  "url": "https://nlook.me",
  "crawl": { "depth": 1, "max_pages": 20, "use_sitemap": true },
  "references": ["https://obsidian.md/publish"],
  "allow_domains": []          // 비우면 대상 등록 도메인만 (SSRF 방지)
}
```

### 응답
`meta-schema.json`을 그대로 따른다. (`target`, `references[]`, `crawl`, `provenance`)

---

## 2. 파이프라인

```
resolve/guard → fetch(head+body) → parse meta → detect SPA
      → extract links → sitemap merge → BFS crawl(depth) → assemble
```

1. **resolve & guard**: URL 정규화, 스킴 https 강제, 사설 IP/localhost 차단(SSRF), `allow_domains` 화이트리스트.
2. **fetch**: 타임아웃 있는 `http.Client`, UA 지정, 리다이렉트 추적(`final_url`), `status` 기록.
3. **parse meta**: goquery로 `<head>` 파싱 → og:* / twitter:* / title / description / canonical / theme-color / favicon / JSON-LD.
4. **detect SPA**: 본문 텍스트 길이 대비 `<script>` 바이트 비율로 `render_required` 판정(휴리스틱).
5. **links**: 내부 링크(같은 호스트) 수집 → 정규화·중복제거.
6. **sitemap**: `use_sitemap`이면 `/sitemap.xml` 가져와 URL 인덱스 병합(우선순위 높음).
7. **crawl**: depth 제한 BFS, `max_pages` 상한, 워커풀 동시성, 페이지별 `title`/`render_required`만 얕게 수집.
8. **references**: 각 레퍼런스 URL을 1~4단계만(크롤 없이) 수집해 동일 shape로.
9. **assemble**: 계약 JSON 조립 + `provenance.grading` 기본값 부여.

---

## 3. Go 스케치

> 전체 구현이 아니라 계약을 만족하는 골격. 필드명은 `meta-schema.json`과 일치.

```go
package diagnostic

import (
	"context"
	"encoding/json"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
)

type Field struct {
	Value  *string `json:"value"`
	Source *string `json:"source"`
}

type OGImage struct {
	URL    *string `json:"url"`
	Width  *int    `json:"width"`
	Height *int    `json:"height"`
	Type   *string `json:"type"`
	Alt    *string `json:"alt"`
}

type Meta struct {
	Title       Field           `json:"title"`
	Description Field           `json:"description"`
	SiteName    Field           `json:"site_name"`
	Canonical   Field           `json:"canonical"`
	Locale      Field           `json:"locale"`
	ThemeColor  Field           `json:"theme_color"`
	Favicon     Field           `json:"favicon"`
	TwitterCard Field           `json:"twitter_card"`
	OGImage     OGImage         `json:"og_image"`
	JSONLD      []map[string]any `json:"jsonld"`
}

type SEOFlags struct {
	HasOGImage           bool `json:"has_og_image"`
	OGImageDimensionsOK  bool `json:"og_image_dimensions_ok"`
	HasJSONLD            bool `json:"has_jsonld"`
	HasStandardDesc      bool `json:"has_standard_description"`
	TitleLengthOK        bool `json:"title_length_ok"`
	HasCanonical         bool `json:"has_canonical"`
	HasFavicon           bool `json:"has_favicon"`
}

type Site struct {
	URL            string    `json:"url"`
	FinalURL       string    `json:"final_url"`
	FetchedAt      time.Time `json:"fetched_at"`
	Status         int       `json:"status"`
	RenderRequired bool      `json:"render_required"`
	Meta           Meta      `json:"meta"`
	SEOFlags       SEOFlags  `json:"seo_flags"`
}

type Page struct {
	Path           string  `json:"path"`
	Title          *string `json:"title"`
	Source         string  `json:"source"` // "link" | "sitemap"
	RenderRequired bool    `json:"render_required"`
}

type Crawl struct {
	Depth              int      `json:"depth"`
	MaxPages           int      `json:"max_pages"`
	SitemapUsed        bool     `json:"sitemap_used"`
	InternalLinksFound int      `json:"internal_links_found"`
	Pages              []Page   `json:"pages"`
	Notes              []string `json:"notes"`
}

type Output struct {
	Target     Site       `json:"target"`
	References []Site     `json:"references,omitempty"`
	Crawl      Crawl      `json:"crawl"`
	Provenance Provenance `json:"provenance"`
}

type Provenance struct {
	Collector string            `json:"collector"`
	Grading   map[string]string `json:"grading"`
}

// --- fetch + parse ---

var client = &http.Client{Timeout: 15 * time.Second}

func fetchDoc(ctx context.Context, raw string) (*goquery.Document, *http.Response, error) {
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, raw, nil)
	req.Header.Set("User-Agent", "seometa-diagnostic/1.0 (+https://nlook.me)")
	resp, err := client.Do(req)
	if err != nil {
		return nil, nil, err
	}
	doc, err := goquery.NewDocumentFromReader(resp.Body)
	return doc, resp, err
}

// parseMeta reads only what exists; missing => Field{nil,nil}. Never guesses.
func parseMeta(doc *goquery.Document) Meta {
	m := Meta{}
	prop := func(sel, attr string) *string {
		if v, ok := doc.Find(sel).Attr(attr); ok && strings.TrimSpace(v) != "" {
			v = strings.TrimSpace(v)
			return &v
		}
		return nil
	}
	setField := func(f *Field, val *string, src string) {
		if val != nil {
			f.Value = val
			s := src
			f.Source = &s
		}
	}
	// title: prefer og:title, fall back to <title>
	if v := prop(`meta[property="og:title"]`, "content"); v != nil {
		setField(&m.Title, v, "og:title")
	} else if t := strings.TrimSpace(doc.Find("title").Text()); t != "" {
		setField(&m.Title, &t, "title-tag")
	}
	// description: standard meta, else twitter:description
	if v := prop(`meta[name="description"]`, "content"); v != nil {
		setField(&m.Description, v, "meta:description")
	} else if v := prop(`meta[name="twitter:description"]`, "content"); v != nil {
		setField(&m.Description, v, "twitter:description")
	}
	setField(&m.SiteName, prop(`meta[property="og:site_name"]`, "content"), "og:site_name")
	setField(&m.Locale, prop(`meta[property="og:locale"]`, "content"), "og:locale")
	setField(&m.ThemeColor, prop(`meta[name="theme-color"]`, "content"), "theme-color")
	setField(&m.Canonical, prop(`link[rel="canonical"]`, "href"), "link:canonical")
	setField(&m.TwitterCard, prop(`meta[name="twitter:card"]`, "content"), "twitter:card")

	m.OGImage = OGImage{
		URL:  prop(`meta[property="og:image"]`, "content"),
		Type: prop(`meta[property="og:image:type"]`, "content"),
		Alt:  prop(`meta[property="og:image:alt"]`, "content"),
	}
	// width/height parse omitted for brevity (atoi of og:image:width/height)

	doc.Find(`script[type="application/ld+json"]`).Each(func(_ int, s *goquery.Selection) {
		var obj map[string]any
		if json.Unmarshal([]byte(s.Text()), &obj) == nil {
			m.JSONLD = append(m.JSONLD, obj)
		}
	})
	return m
}

// detectSPA: thin visible text vs heavy scripts => render likely needed.
func detectSPA(doc *goquery.Document) bool {
	text := strings.TrimSpace(doc.Find("body").Text())
	var scriptBytes int
	doc.Find("script").Each(func(_ int, s *goquery.Selection) { scriptBytes += len(s.Text()) })
	return len([]rune(text)) < 400 && scriptBytes > 2000
}
```

### 크롤 (depth 제한 BFS, 워커풀)

```go
func crawl(ctx context.Context, base *url.URL, seeds []string, depth, maxPages int) []Page {
	seen := map[string]bool{}
	var mu sync.Mutex
	var pages []Page
	queue := seeds
	for d := 0; d < depth && len(queue) > 0 && len(pages) < maxPages; d++ {
		next := []string{}
		sem := make(chan struct{}, 6) // 동시성 6
		var wg sync.WaitGroup
		for _, u := range queue {
			if seen[u] || len(pages) >= maxPages {
				continue
			}
			seen[u] = true
			wg.Add(1)
			sem <- struct{}{}
			go func(u string) {
				defer wg.Done(); defer func() { <-sem }()
				doc, _, err := fetchDoc(ctx, u)
				if err != nil { return }
				title := strings.TrimSpace(doc.Find("title").Text())
				mu.Lock()
				pages = append(pages, Page{Path: pathOf(base, u), Title: &title, Source: "link", RenderRequired: detectSPA(doc)})
				// collect only same-host links for next depth
				doc.Find(`a[href]`).Each(func(_ int, s *goquery.Selection) {
					if href, ok := s.Attr("href"); ok {
						if abs := sameHostAbs(base, href); abs != "" && !seen[abs] {
							next = append(next, abs)
						}
					}
				})
				mu.Unlock()
			}(u)
		}
		wg.Wait()
		queue = dedupe(next)
	}
	return pages
}
```

---

## 4. 안전·정직 규칙 (필수)

- **SSRF 차단**: 사설/루프백 IP, 메타데이터 엔드포인트, 스킴 http→https 강제, `allow_domains` 화이트리스트.
- **robots.txt 존중**: disallow면 크롤 스킵하고 `notes:["robots_disallow"]`.
- **상한**: `max_pages`, depth≤2 권장, 전체 요청 타임아웃, 페이지당 타임아웃.
- **없으면 null**: 못 찾은 필드는 절대 채우지 않는다. `source:null`. (스킬의 근거 등급이 여기 의존)
- **SPA 정직 표기**: `render_required:true`면 스킬이 "본문 = 정황"으로 낮춰 표기.
- 캐시: 동일 URL 단기 캐시(예: 6h)로 재수집 비용 절감.

## 5. 렌더링 필요 시(선택 확장)
`render_required:true`가 많으면 헤드리스(rod/chromedp) 렌더 후 재파싱하는 `?render=true` 옵션을 둔다. 기본은 off(비용). nlook은 메타가 SSR이라 히어로/메타는 render 없이 정확.
