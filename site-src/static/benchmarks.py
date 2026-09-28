"""Public benchmark pages for hirethomas.co (HireThomas, Inc.).

Two steps, both plain Python 3 (no dependencies):

1. extract  -- input is the per-store summary exported from the collection runs
   (coffee: {"run", "store_median_12oz": {domain: usd}}; candles: {"run", "stores":
   {domain: {"n", "med_per_oz", "med_8oz"}}}). Those inputs name stores and are NOT
   committed. The extractor keeps only anonymized per-store values (sorted, no
   names/domains), the exclusion count and the SHA-256 of the input file:

     python3 site-src/static/benchmarks.py extract-coffee  <coffee_summary.json>
     python3 site-src/static/benchmarks.py extract-candles <candles_summary.json>

   -> site-src/data/benchmarks/<slug>.json

2. render   -- called at the end of site-src/static/build.py, or standalone:

     SITE_ORIGIN=https://hirethomas.co python3 site-src/static/build.py

   -> benchmarks/index.html and benchmarks/<slug>/index.html

Stats: median and quartiles use linear interpolation between order statistics
(Python statistics.quantiles(method='inclusive'), identical to spreadsheet QUARTILE.INC).
"""
from pathlib import Path
from html import escape
from urllib.parse import quote
import hashlib, json, statistics, sys, math

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / 'data' / 'benchmarks'
CSS_V = '20260927b'
ORDER = ['coffee-12oz-2026-09', 'candles-per-oz-2026-09']


# ---------------------------------------------------------------- statistics
def stats(values):
    v = sorted(values)
    q1, med, q3 = statistics.quantiles(v, n=4, method='inclusive')
    return {'n': len(v), 'min': v[0], 'q1': q1, 'median': med, 'q3': q3, 'max': v[-1],
            'median_check': statistics.median(v)}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- rendering helpers
def money(x, d):
    return f'${x:,.2f}' + d.get('suffix', '')


def chart(d, st):
    """Inline SVG histogram with Q1 / median / Q3 markers. Pure function of the values."""
    vals, b = d['values'], d['bin']
    lo = math.floor(min(vals) / b + 1e-9) * b
    hi = math.floor(max(vals) / b + 1e-9) * b + b
    nb = int(round((hi - lo) / b))
    counts = [0] * nb
    for x in vals:
        counts[min(nb - 1, int((x - lo) / b + 1e-9))] += 1
    W, H, L, R, T, B = 720, 300, 44, 16, 34, 250
    pw = W - L - R
    X = lambda x: L + (x - lo) / (hi - lo) * pw
    cmax = max(counts)
    Y = lambda c: B - c / cmax * (B - T - 10)
    out = [f'<svg viewBox="0 0 {W} {H}" class="h-auto w-full" role="img" aria-labelledby="chart-title chart-desc" font-family="Inter, system-ui, sans-serif">',
           f'<title id="chart-title">Distribution of {escape(d["value_label"][0].lower() + d["value_label"][1:])} across {st["n"]} stores</title>',
           f'<desc id="chart-desc">Histogram in {money(b, {})} bins. Q1 {money(st["q1"], d)}, median {money(st["median"], d)}, Q3 {money(st["q3"], d)}; range {money(st["min"], d)} to {money(st["max"], d)}.</desc>']
    step = 1 if cmax <= 8 else 2
    for c in range(0, cmax + 1, step):
        out.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(c):.1f}" y2="{Y(c):.1f}" stroke="#e2e8f0" stroke-width="1"/>'
                   f'<text x="{L-8}" y="{Y(c)+4:.1f}" text-anchor="end" font-size="11" fill="#64748b">{c}</text>')
    gap = 2
    for i, c in enumerate(counts):
        if not c:
            continue
        x0, x1 = X(lo + i * b) + gap / 2, X(lo + (i + 1) * b) - gap / 2
        out.append(f'<rect x="{x0:.1f}" y="{Y(c):.1f}" width="{x1-x0:.1f}" height="{B-Y(c):.1f}" rx="3" fill="#94a3b8"><title>{money(lo+i*b, d)} to under {money(lo+(i+1)*b, d)}: {c} store{"s" if c != 1 else ""}</title></rect>')
    tick_every = max(1, math.ceil(nb / 12))
    for i in range(0, nb + 1, tick_every):
        x = X(lo + i * b)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{B}" y2="{B+5}" stroke="#94a3b8"/>'
                   f'<text x="{x:.1f}" y="{B+19}" text-anchor="middle" font-size="11" fill="#64748b">{money(lo+i*b, {})}</text>')
    out.append(f'<line x1="{L}" x2="{W-R}" y1="{B}" y2="{B}" stroke="#94a3b8"/>')
    for key, lab, col in (('q1', 'Q1', '#64748b'), ('median', 'Median', '#0f172a'), ('q3', 'Q3', '#64748b')):
        x = X(st[key])
        dash = '' if key == 'median' else ' stroke-dasharray="5 4"'
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T-6}" y2="{B}" stroke="{col}" stroke-width="{2 if key=="median" else 1.5}"{dash}/>')
        anchor = 'end' if key == 'q1' else ('start' if key == 'q3' else 'middle')
        tx = x - 4 if key == 'q1' else (x + 4 if key == 'q3' else x)
        ty = T - 12 if key == 'median' else T + 4
        out.append(f'<text x="{tx:.1f}" y="{ty}" text-anchor="{anchor}" font-size="12" font-weight="600" fill="{col}">{lab} {money(st[key], {})}</text>')
    out.append(f'<text x="{W-R}" y="{H-4}" text-anchor="end" font-size="11" fill="#64748b">{escape(d["value_label"])}</text>')
    out.append(f'<text x="{L}" y="{H-4}" font-size="11" fill="#64748b">Stores per {money(b, {})} bin</text>')
    out.append('</svg>')
    return ''.join(out)


def quartile_band(x, st):
    if x <= st['q1']: return 'Lowest 25%'
    if x <= st['median']: return '25–50%'
    if x <= st['q3']: return '50–75%'
    return 'Highest 25%'


TH = 'whitespace-nowrap px-4 py-2.5 font-medium'
TD = 'whitespace-nowrap px-4 py-2'
H2 = 'text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl'
LEAD = 'mt-4 text-lg leading-8 text-slate-600'
CARD = 'rounded-2xl border border-slate-200 bg-white shadow-sm'


def head(title, desc, path, url):
    canon = url(path)
    return (f'<!DOCTYPE html><html lang="en" class="antialiased"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escape(title)} | HireThomas</title><meta name="description" content="{escape(desc, quote=True)}">'
            f'<link rel="canonical" href="{canon}"><meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(desc, quote=True)}">'
            f'<meta property="og:type" content="website"><meta property="og:url" content="{canon}"><meta name="theme-color" content="#0f172a">'
            f'<link rel="icon" href="{url("/favicon.svg")}" type="image/svg+xml"><link rel="preconnect" href="https://rsms.me/"><link rel="stylesheet" href="https://rsms.me/inter/inter.css">'
            f'<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>'
            f'<link rel="stylesheet" href="{url("/_astro/index.BHVniVEy.css")}"><link rel="stylesheet" href="{url("/services.css")}?v={CSS_V}"></head>'
            f'<body class="bg-white text-slate-800 font-sans selection:bg-brand-100 selection:text-brand-900"><a class="skip" href="{canon}#main">Skip to content</a>')


def cta_block(url, subject):
    mail = 'mailto:hello@hirethomas.co?subject=' + quote(subject) + '&body=' + quote('Our store: \nCompetitors (up to 10 URLs): \n')
    return (f'<section id="start" class="py-24"><div class="mx-auto max-w-6xl px-4 sm:px-6"><div class="rounded-3xl bg-gradient-to-br from-brand-600 to-brand-800 px-6 py-14 text-center text-white shadow-xl sm:px-12">'
            f'<h2 class="text-3xl font-semibold tracking-tight sm:text-4xl">Want your store\'s exact position and a weekly update?</h2>'
            f'<p class="mx-auto mt-4 max-w-xl text-brand-100">Competitor Price Watch — first report free. Send your store URL and up to 10 competitor URLs; the full report arrives before you pay anything.</p>'
            f'<div class="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">'
            f'<a href="{url("/pricewatch.html")}" class="inline-flex h-12 items-center gap-2 rounded-xl bg-white px-6 text-[15px] font-semibold text-brand-800 shadow-lg transition hover:bg-brand-50">Competitor Price Watch — first report free</a>'
            f'<a href="{mail}" class="inline-flex h-12 items-center gap-2 rounded-xl border border-white/40 px-6 text-[15px] font-semibold text-white transition hover:bg-white/10">hello@hirethomas.co</a></div>'
            f'<p class="mt-4 text-xs text-brand-200">Benchmarks and reports are produced by AI systems operated by HireThomas, Inc., a Delaware corporation, with a human owner accountable for the business.</p>'
            f'</div></div></section>')


def bench_page(d, nav, footer, url):
    st = stats(d['values'])
    path = f'/benchmarks/{d["slug"]}/'
    f = lambda x: money(x, d)
    n = st['n']
    hero_stats = [('Stores (N)', str(n)), ('Median', f(st['median'])), ('Middle 50%', f'{f(st["q1"])} – {f(st["q3"])}'), ('Range', f'{f(st["min"])} – {f(st["max"])}')]
    h = head(d['title'], d['description'].format(n=n, median=f(st['median'])), path, url) + nav + '<main id="main">'
    h += ('<section class="relative overflow-hidden border-b border-slate-200"><div class="grid-bg pointer-events-none absolute inset-0"></div><div class="glow pointer-events-none absolute inset-x-0 top-0 h-[480px]"></div>'
          '<div class="relative mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:py-24">'
          f'<span class="inline-flex items-center rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-800">Public benchmark · collected {d["collected"]}</span>'
          f'<h1 class="mt-6 max-w-4xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl sm:leading-[1.08]">{escape(d["h1"])}</h1>'
          f'<p class="mt-6 max-w-3xl text-lg leading-8 text-slate-600">{d["intro"].format(n=n)}</p>'
          '<dl class="mt-10 grid grid-cols-2 gap-4 lg:grid-cols-4">'
          + ''.join(f'<div class="{CARD} p-5"><dt class="text-xs font-medium uppercase tracking-wide text-slate-500">{k}</dt><dd class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{v}</dd></div>' for k, v in hero_stats)
          + f'</dl><p class="mt-4 text-sm text-slate-500">{escape(d["value_label"])}. Snapshot of public prices on {d["collected"]}; prices change.</p></div></section>')
    rows = [('Stores (N)', str(n)), ('Minimum', f(st['min'])), ('Lower quartile (Q1)', f(st['q1'])), ('Median', f(st['median'])), ('Upper quartile (Q3)', f(st['q3'])), ('Maximum', f(st['max'])), ('Interquartile range', f(st['q3'] - st['q1']))]
    h += (f'<section id="distribution" class="py-20 sm:py-24"><div class="mx-auto max-w-6xl px-4 sm:px-6"><div class="max-w-2xl"><h2 class="{H2}">Distribution</h2>'
          f'<p class="{LEAD}">One value per store: {escape(d["value_label"][0].lower() + d["value_label"][1:])}. Dashed lines mark the quartiles; the solid line marks the median.</p></div>'
          f'<div class="mt-10 grid gap-6 lg:grid-cols-3"><div class="{CARD} p-4 sm:p-6 lg:col-span-2">{chart(d, st)}</div>'
          f'<div class="overflow-hidden {CARD}"><div class="border-b border-slate-200 bg-slate-50 px-4 py-2.5 text-xs font-medium text-slate-600">Summary statistics</div>'
          '<table class="w-full text-left text-[14px]"><tbody class="divide-y divide-slate-100">'
          + ''.join(f'<tr><th scope="row" class="px-4 py-2.5 font-medium text-slate-600">{k}</th><td class="mono px-4 py-2.5 text-right text-slate-900">{v}</td></tr>' for k, v in rows)
          + '</tbody></table></div></div></div></section>')
    body = ''
    for i, x in enumerate(d['values']):
        lower = sum(1 for y in d['values'] if y < x)
        body += (f'<tr><td class="{TD}">{i+1}</td><td class="{TD}">Store {i+1:02d}</td><td class="{TD}">{f(x)}</td>'
                 f'<td class="{TD}">{round(100*lower/n)}%</td><td class="{TD}">{quartile_band(x, st)}</td></tr>')
    h += (f'<section id="ranked" class="border-y border-slate-200 bg-slate-50 py-20 sm:py-24"><div class="mx-auto max-w-6xl px-4 sm:px-6"><div class="max-w-2xl"><h2 class="{H2}">Ranked distribution (anonymized)</h2>'
          f'<p class="{LEAD}">All {n} stores, lowest to highest. Store names are withheld; labels are assigned by rank and do not identify a business.</p></div>'
          f'<div class="mt-10 overflow-hidden {CARD}"><div class="overflow-x-auto"><table class="w-full text-left text-[13px]"><thead class="text-xs uppercase tracking-wide text-slate-500"><tr>'
          f'<th class="{TH}">Rank (low → high)</th><th class="{TH}">Store</th><th class="{TH}">{escape(d["table_label"])}</th><th class="{TH}">Stores priced lower</th><th class="{TH}">Quartile</th></tr></thead>'
          f'<tbody class="mono divide-y divide-slate-100 text-slate-700">{body}</tbody></table></div></div></div></section>')
    li = lambda items: '<ul class="mt-4 space-y-3 text-[15px] leading-7 text-slate-600">' + ''.join(f'<li class="flex gap-3"><span class="mt-2.5 size-1.5 shrink-0 rounded-full bg-slate-400"></span><span>{t}</span></li>' for t in items) + '</ul>'
    method = [t.format(n=n) for t in d['method']]
    limits = [t.format(n=n) for t in d['limitations']]
    h += (f'<section id="method" class="py-20 sm:py-24"><div class="mx-auto grid max-w-6xl gap-10 px-4 sm:px-6 lg:grid-cols-2">'
          f'<div class="{CARD} p-6 sm:p-8"><h2 class="text-2xl font-semibold tracking-tight text-slate-900">Method</h2>{li(method)}</div>'
          f'<div class="{CARD} p-6 sm:p-8"><h2 class="text-2xl font-semibold tracking-tight text-slate-900">Limitations</h2>{li(limits)}</div>'
          '</div></section>')
    h += cta_block(url, 'Price Watch - my position in the ' + d['short'] + ' benchmark')
    h += '</main>' + footer + '</body></html>'
    return path, h, st


def index_page(items, nav, footer, url):
    path = '/benchmarks/'
    h = head('Public price benchmarks', 'Free public price benchmarks built from public Shopify storefront data: US specialty coffee (12 oz bag) and independent US candle makers ($/oz).', path, url) + nav + '<main id="main">'
    h += ('<section class="relative overflow-hidden border-b border-slate-200"><div class="grid-bg pointer-events-none absolute inset-0"></div><div class="glow pointer-events-none absolute inset-x-0 top-0 h-[480px]"></div>'
          '<div class="relative mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:py-24"><span class="inline-flex items-center rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-800">Public benchmarks</span>'
          '<h1 class="mt-6 max-w-3xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl sm:leading-[1.08]">Where do small online stores price?</h1>'
          '<p class="mt-6 max-w-2xl text-lg leading-8 text-slate-600">Snapshot benchmarks from public Shopify storefront data, normalized to a common unit. One value per store; store names withheld.</p>'
          '<div class="mt-10 grid gap-6 md:grid-cols-2">')
    for d, st in items:
        h += (f'<a href="{url("/benchmarks/" + d["slug"] + "/")}" class="block {CARD} p-6 transition hover:border-slate-300 hover:shadow-md">'
              f'<p class="text-xs font-medium uppercase tracking-wide text-slate-500">Collected {d["collected"]} · N = {st["n"]}</p>'
              f'<h2 class="mt-3 text-xl font-semibold tracking-tight text-slate-900">{escape(d["h1"])}</h2>'
              f'<p class="mt-3 text-slate-600">Median {money(st["median"], d)} · middle 50% {money(st["q1"], d)} – {money(st["q3"], d)}</p>'
              '<p class="mt-4 text-sm font-semibold text-slate-900">View benchmark →</p></a>')
    h += '</div></div></section>' + cta_block(url, 'Price Watch - free first report') + '</main>' + footer + '</body></html>'
    return path, h


def render(nav, footer, url, root):
    """Write benchmark pages into the site root. Returns {repo_path: stats}."""
    items, out = [], {}
    for slug in ORDER:
        p = DATA / f'{slug}.json'
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        path, html, st = bench_page(d, nav, footer, url)
        f = Path(root) / path.strip('/') / 'index.html'
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(html)
        items.append((d, st))
        out[path.strip('/') + '/index.html'] = st
        print(f.relative_to(root), len(html), json.dumps({k: round(v, 4) for k, v in st.items()}))
    if items:
        path, html = index_page(items, nav, footer, url)
        f = Path(root) / 'benchmarks' / 'index.html'
        f.write_text(html)
        print(f.relative_to(root), len(html))
    return out


# ---------------------------------------------------------------- extraction (page text lives here)
NOT_CUSTOMERS = ('The stores in this sample are not HireThomas customers. They did not commission, review or endorse this benchmark, '
                 'and inclusion says nothing about their quality.')

COFFEE = {
    'slug': 'coffee-12oz-2026-09', 'short': 'coffee 12 oz',
    'title': 'US specialty coffee roasters: 12 oz bag price benchmark, collected 2026-09-27',
    'h1': 'US specialty coffee roasters: 12 oz bag price benchmark',
    'description': 'What {n} online specialty coffee roasters charged for a 12 oz bag on 2026-09-27: median {median}, quartiles, range and an anonymized ranked distribution from public Shopify storefront data.',
    'intro': 'What {n} online specialty coffee roasters listed for a 12 oz bag of coffee, taken from their public Shopify storefronts on 2026-09-27. Each store contributes one number: the median price of its available 12 oz bag variants.',
    'value_label': 'Store median price per 12 oz bag (USD)', 'table_label': 'Median 12 oz bag price',
    'collected': '2026-09-27', 'bin': 1.0, 'suffix': '',
    'method': [
        'Source: each store\'s public Shopify storefront product listing (<span class="mono">/products.json</span>), read on 2026-09-27 (run started 13:03 UTC). No logins, private data or purchases.',
        'A variant counts as a 12 oz bag when its title (or the product title, if the variant names no size) says 12 oz, 340 g, 3/4 lb or 0.75 lb, or its listed weight is 330–360 g with no other size in the title.',
        'Excluded: multi-pack variants (titles starting with a count such as “2/” or “6/”), anything labelled case, wholesale, pack or bulk, and unavailable (sold-out) variants.',
        'Per-store value: the median listed price of that store\'s matching variants, in USD. Grind options were not separated; whole-bean and ground listings at 12 oz are treated alike.',
        'N = {n} stores with at least one matching 12 oz variant. Median and quartiles are computed across the store values with linear interpolation (the same as spreadsheet QUARTILE.INC); each store counts once.',
    ],
    'limitations': [
        'A one-day snapshot (2026-09-27). Prices, promotions and availability change; the figures may already be out of date.',
        'Listed prices only: shipping, taxes, subscription and bulk discounts, and sale timing are not reflected.',
        'A convenience sample of roasters with readable public Shopify storefronts, not a random or complete census of US roasters. “Specialty” and “US” describe how the stores present themselves; we did not audit either.',
        'Titles are parsed automatically; an unusual size label can be missed or misread. Stores without a recognizable 12 oz bag are not in the sample.',
        NOT_CUSTOMERS,
    ],
}

CANDLES = {
    'slug': 'candles-per-oz-2026-09', 'short': 'candles $/oz',
    'title': 'Independent US candle makers: price per ounce benchmark, collected 2026-09-27',
    'h1': 'Independent US candle makers: price per ounce benchmark',
    'description': 'What {n} independent online candle makers charged per ounce on 2026-09-27: median {median}, quartiles, range and an anonymized ranked distribution from public Shopify storefront data.',
    'intro': 'Price per ounce across {n} independent online candle makers, taken from their public Shopify storefronts on 2026-09-27. Each store contributes one number: the median price per ounce of its available candle variants.',
    'value_label': 'Store median price per ounce (USD/oz)', 'table_label': 'Median price per oz',
    'collected': '2026-09-27', 'bin': 0.5, 'suffix': '/oz',
    'method': [
        'Source: each store\'s public Shopify storefront product listing (<span class="mono">/products.json</span>), read on 2026-09-27 (run started 14:35 UTC). No logins, private data or purchases.',
        'Products count as candles when the title, type or tags mention candle, jar, tin, wick, soy, coconut wax or beeswax. Excluded: wholesale, bulk, cases, sets and bundles, gift cards, wax melts and tarts, refills, accessories and non-candle goods such as soap.',
        'Size is read from the variant or product title in ounces (grams converted at 28.3495 g/oz); only sizes from 2 to 40 oz, available variants and prices above $0 are used.',
        'Per-store value: the median of price ÷ ounces across that store\'s matching variants.',
        'N = {n} stores. Two stores from the same run were excluded before any statistics: one whose parsed values were implausible (a data-parsing failure), and one outside the intended scope. Median and quartiles use linear interpolation (spreadsheet QUARTILE.INC); each store counts once.',
    ],
    'limitations': [
        'A one-day snapshot (2026-09-27). Prices, promotions and availability change; the figures may already be out of date.',
        'Listed prices only: shipping, taxes, discounts and bundles are not reflected. Ounces are as stated by each store (usually wax weight, sometimes vessel size), so products are not perfectly comparable.',
        'Wax type, vessel, wick and fragrance load vary widely; price per ounce is a rough common unit, not a like-for-like comparison. Some stores also sell other goods; only their candle listings are counted.',
        'A convenience sample of makers with readable public Shopify storefronts, not a random or complete census. “Independent” and “US” describe how the stores present themselves; we did not audit either.',
        NOT_CUSTOMERS,
    ],
}

CANDLE_EXCLUDE = {'sparkcandles.com', 'harmonyhillcandleco.com'}


def _write(meta, values, src, excluded, extra):
    d = dict(meta)
    d['values'] = sorted(values)
    d['source'] = {'input_sha256': sha256(src), 'run': extra, 'stores_in_input': len(values) + excluded, 'excluded': excluded}
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / f'{meta["slug"]}.json'
    out.write_text(json.dumps(d, indent=1, ensure_ascii=False) + '\n')
    print(out, json.dumps({k: round(v, 4) for k, v in stats(values).items()}))


def extract_coffee(src):
    j = json.loads(Path(src).read_text())
    vals = [round(float(v), 2) for v in j['store_median_12oz'].values()]
    _write(COFFEE, vals, src, 0, j.get('run'))


def extract_candles(src):
    j = json.loads(Path(src).read_text())
    vals = [round(float(s['med_per_oz']), 3) for dom, s in j['stores'].items() if dom not in CANDLE_EXCLUDE]
    excluded = sum(1 for dom in j['stores'] if dom in CANDLE_EXCLUDE)
    _write(CANDLES, vals, src, excluded, j.get('run'))


if __name__ == '__main__':
    cmd, src = sys.argv[1], sys.argv[2]
    {'extract-coffee': extract_coffee, 'extract-candles': extract_candles}[cmd](src)
