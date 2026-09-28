# Service-site static build (2026-09-27)

> **Subdomain layout (2026-09-28, owner request).** Each service now lives on its own subdomain, served by its own
> GitHub Pages repo: obituaries.hirethomas.co (hirethomas-inc/obituaries), menus.hirethomas.co (menus),
> agencies.hirethomas.co (agencies), pricewatch.hirethomas.co (pricewatch; root index.html = former /pricewatch.html),
> benchmarks.hirethomas.co (benchmarks; index plus /coffee-12oz-2026-09/ and /candles-per-oz-2026-09/).
> This repo keeps the apex home (/) and /contact/; the old service paths here are generated redirect pages
> (meta refresh + canonical + visible link). `python3 site-src/static/build.py` now always emits absolute URLs
> (SITE_ORIGIN defaults to https://hirethomas.co; HOST_<NAME> overrides a subdomain origin) and writes:
> apex pages + redirect stubs into this repo, and one standalone site root per service into `$SUBSITES_OUT`
> (default `<repo>/../subsites/<name>/`: index.html, referenced assets, CNAME, .nojekyll). Deploy each subsite
> root to the root of its repo on branch main. The section below describes the earlier single-site layout.

Node/npm were unavailable on the service-page worker's seat. Per the deployment brief, this is the active **no-Node fallback**, using Inter, Tailwind v4 browser CDN, local critical CSS, and inline Lucide-style SVG icons. It introduces no JS requirement for reading, navigation or email links. Existing Astro 5 sources and assets remain for reference; running only `astro build` will NOT include these service pages and will restore the old home/contact shell.

## Build

From the repository root, with Python 3:

```
python3 site-src/static/build.py
```

This emits root-relative links while the custom domain is unavailable. Once `curl -L https://hirethomas.co/` verifies that the domain is serving the company site (not just a parking page), use:

```
SITE_ORIGIN=https://hirethomas.co python3 site-src/static/build.py
```

The builder writes `index.html`, `obituaries/index.html`, `menus/index.html`, `agencies/index.html`, `contact/index.html`, `pricewatch.html`, and `services.css`. Deploy all seven outputs together. Directory index pages expose extensionless service URLs. Preserve `.nojekyll`, `favicon.svg`, the existing `_astro/` asset directory, and the other worker's `CNAME`. Do not deploy or change DNS or provider settings from this script.

## Sources

Owner-directed product identities (updated after initial deployment): obituary pages use Source Serif 4, ivory/charcoal, a centered editorial hero and newspaper-style notice; menus use terracotta/olive/cream and a printed-menu sample card; agencies use a navy/electric-blue workspace, illustrative report table and pricing cards. The neutral homepage previews these accent palettes. Price Watch retains its data/chart content and original compiled asset. AI disclosure and company nav/footer remain consistent.

- `build.py`: common navigation/footer and new page content.
- `services.css`: responsive styles, including critical local layout.
- `pricewatch-original.html`: saved original compiled Price Watch page. Its main content is preserved; build replaces its common shell, email and links.
- Original Astro pages remain under `src/`; migrate these static sources before returning to an Astro-only build.

## Deploy and verify

The private deploy helper uses GitHub's documented Contents API: GET each file's SHA, then PUT base64 content on `main` with that SHA. Credentials are outside the repository in the company seat's private token file; never publish them. Commit these source files under `site-src/static/` too. No dependencies or paid services were purchased.

After GitHub Pages builds, curl each route with redirects enabled; expect 200. Check all href paths and fragments, stylesheet/icon resources, footer identity and service prices. Screenshot the live pages on desktop and a narrow window. Email links must target `hello@hirethomas.co` with service-specific subjects. Do not send test emails from this build task.

## Page inventory

- `/benchmarks/`, `/benchmarks/coffee-12oz-2026-09/`, `/benchmarks/candles-per-oz-2026-09/`: public price benchmarks (snapshot 2026-09-27) rendered by `benchmarks.py` from anonymized per-store values in `site-src/data/benchmarks/*.json` (no store names in the repo). `build.py` calls it automatically; re-extract with `python3 site-src/static/benchmarks.py extract-coffee|extract-candles <summary.json>`. Every store counts once; quartiles are QUARTILE.INC. Stores are not customers; pages say so.

- `/`: service overview; original data extraction and script offers retained.
- `/obituaries/`: $40 each, first two free, 2-hour draft, revisions included, monthly ACH/check invoice; labeled fictional Peggy Lindqvist sample.
- `/menus/`: $99 full rewrite / $149 with complete Spanish or English translation; 48 hours, one corrections round, invoice after delivery, ACH/check; fictional menu example.
- `/agencies/`: white-label public-data collection, competitor price/SERP monitoring, company-level lead lists, weekly reports; from $49/report and $39/month per monitor, first deliverable free; no personal scraping, login-walled sites or CAPTCHA bypass.
- `/contact/` and `/#contact`: email and company address.
- `/pricewatch.html`: preserved existing offer, updated navigation/contact/footer.

All pages have the specified company footer and “Operated by AI; a human owner is accountable”. No testimonials, logos, people or results have been fabricated.
