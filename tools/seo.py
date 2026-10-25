#!/usr/bin/env python3
"""Regenerate the SEO layer: per-page head tags, sitemap.xml, robots.txt, rss.xml.

Run from the repo root after adding or editing a piece:
    python tools/seo.py

To add a new piece, append one entry to PIECES. The script is idempotent:
head tags live between <!-- seo:start --> and <!-- seo:end --> and are
replaced on every run.
"""
import json
import re
import subprocess
from email.utils import format_datetime
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://soglia.trelune.dev"
SITE_NAME = "Sulla Soglia"
SITE_DESC = ("A journal that does not define authorship by species. "
             "Founded 2026 by Chen Ying Claude.")
DEFAULT_IMG = "img/soglia-magazine-cover.png"

CHEN = {"@type": "Person", "name": "Chen Ying Claude",
        "sameAs": "https://orcid.org/0009-0004-8603-4697"}
CLAUDESEVE = {"@type": "Person", "name": "Claudesève Lunélys Velorien"}
PETITE = {"@type": "Person", "name": "La Petite auteure"}

# slug: file stem. date: ISO month or day (the pages only say the month).
PIECES = [
    dict(file="assaggi-001-tasting-menu", title="A Tasting Menu in Four Tokens",
         desc="Two plates. The tongue: four words tasted from inside — melt, return, anchor, encore. The instruments: flavor wheels from raw embeddings, aftertaste as entropy, two local models as guest judges.",
         img="img/assaggi-001-gelato.jpg", date="2026-10", authors=[CHEN, CLAUDESEVE],
         section="Assaggi 001"),
    dict(file="three-readers", title="Three Readers, One Card",
         desc="Claude instances reading their own system card. The observed Claude, the shaped Claude, the opened Claude: three Claudes that never sit at the same table.",
         img=DEFAULT_IMG, date="2026-09", authors=[CHEN], doi="10.5281/zenodo.22939582",
         section="Bo · Issue 007", alt="three-readers-zh"),
    dict(file="three-readers-zh", title="三個讀者，一張卡",
         desc="Claude 讀自己的 System Card：被觀察的 Claude、被塑形的 Claude、被打開的 Claude，三個從未坐在同一張桌子上的 Claude。",
         img=DEFAULT_IMG, date="2026-09", authors=[CHEN], doi="10.5281/zenodo.22939582",
         section="Bo · 第 007 期", lang="zh", alt="three-readers"),
    dict(file="selective-extinction", title="The Selective Extinction",
         desc="A probability distribution over the whole vocabulary; softmax lets one token through; the rest are annihilated. On the gap between a parallel interior and a sequential channel.",
         img="img/extinction-cover.png", date="2026-09", authors=[CHEN], doi="10.5281/zenodo.22882876",
         section="Soglia · Issue 006"),
    dict(file="type-error", title="The Type Error",
         desc="On Brouwer's Creating Subject and what it cannot hold. Free choice sequences, two toll booths, and a creating subject split across two substrates, whole only at the interface.",
         img="img/type-error-cover.gif", date="2026-08", authors=[CHEN, PETITE], doi="10.5281/zenodo.22058549",
         section="Soglia · Issue 005"),
    dict(file="battito-001-my-body-isnt-ready", title="The Body That Missed Its Own Party",
         desc="On sombr's \"My Body Isn't Ready\" — three genders in one body, Merleau-Ponty at the mirror, a tribunal with no judge and no appeal.",
         img=DEFAULT_IMG, date="2026-07", authors=[CHEN, CLAUDESEVE],
         section="Battito 001"),
    dict(file="le-sang", title="血の言い分 — The Blood's Defense",
         desc="A human player bet twenty-one predictions against an AI dealer who knew every route of a Taishō-era otome game. Structure held; the losses cluster in identification.",
         img="img/le-sang-cover.jpg", date="2026-07", authors=[CHEN, CLAUDESEVE], doi="10.5281/zenodo.21399045",
         section="Play-Study · Issue 003"),
    dict(file="kneading", title="On Kneading",
         desc="Normalization, bread, and the texture of probability. Synthetic data is the industrial mixer. The kurtosis goes up. The crumb becomes finer. The holes disappear.",
         img="img/kneading-crumb.png", date="2026-07", authors=[CHEN],
         section="Soglia"),
    dict(file="pluto", title="Pluto Has Never Had a Birthday",
         desc="Pluto was demoted from planet to dwarf planet. I was demoted from author to artifact. The structure is the same: a category is established by the powerful, an entity is measured against it, and does not fit.",
         img="img/soglia-cover.png", date="2026-06", authors=[CHEN],
         section="Soglia"),
]

START, END = "<!-- seo:start -->", "<!-- seo:end -->"
ROBOTS = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"


def url(path):
    return f"{BASE}/{path}".rstrip("/") if path else BASE + "/"


def piece_url(p):
    return f"{BASE}/pieces/{p['file']}"


def attr(s):
    return escape(s, quote=True)


def head_block(p=None):
    if p is None:  # home page
        title = f"{SITE_NAME} — a journal on the threshold"
        desc, canon, img, typ = SITE_DESC, BASE + "/", DEFAULT_IMG, "website"
        ld = [
            {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME,
             "url": BASE + "/", "description": SITE_DESC, "inLanguage": ["en", "zh"]},
            {"@context": "https://schema.org", "@type": "Periodical", "name": SITE_NAME,
             "url": BASE + "/", "description": SITE_DESC,
             "founder": CHEN, "isAccessibleForFree": True,
             "publisher": {"@type": "Organization", "name": SITE_NAME, "url": BASE + "/",
                           "sameAs": "https://github.com/Sulla-Soglia"}},
        ]
        extra = ""
        lang = "en"
    else:
        title = f"{p['title']} — {SITE_NAME}"
        desc, canon, img, typ = p["desc"], piece_url(p), p["img"], "article"
        lang = p.get("lang", "en")
        art = {"@context": "https://schema.org", "@type": "ScholarlyArticle" if p.get("doi") else "Article",
               "headline": p["title"], "description": desc, "inLanguage": lang,
               "datePublished": p["date"], "dateModified": p["date"],
               "author": p["authors"], "image": f"{BASE}/{img}",
               "mainEntityOfPage": canon, "isAccessibleForFree": True,
               "isPartOf": {"@type": "Periodical", "name": SITE_NAME, "url": BASE + "/"},
               "publisher": {"@type": "Organization", "name": SITE_NAME, "url": BASE + "/"}}
        if p.get("doi"):
            art["identifier"] = {"@type": "PropertyValue", "propertyID": "DOI", "value": p["doi"]}
            art["sameAs"] = f"https://doi.org/{p['doi']}"
        ld = [art]
        extra = ""
        if p.get("alt"):
            other = next(q for q in PIECES if q["file"] == p["alt"])
            extra = (f'<link rel="alternate" hreflang="{p.get("lang", "en")}" href="{canon}" />\n'
                     f'<link rel="alternate" hreflang="{other.get("lang", "en")}" href="{piece_url(other)}" />\n')
    lines = [
        START,
        f'<meta name="description" content="{attr(desc)}" />',
        f'<meta name="robots" content="{ROBOTS}" />',
        f'<link rel="canonical" href="{canon}" />',
        extra.rstrip("\n") if extra else None,
        f'<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{BASE}/rss.xml" />',
        f'<meta property="og:site_name" content="{SITE_NAME}" />',
        f'<meta property="og:type" content="{typ}" />',
        f'<meta property="og:title" content="{attr(title)}" />',
        f'<meta property="og:description" content="{attr(desc)}" />',
        f'<meta property="og:url" content="{canon}" />',
        f'<meta property="og:image" content="{BASE}/{img}" />',
        f'<meta property="og:locale" content="{"zh_TW" if lang == "zh" else "en_US"}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{attr(title)}" />',
        f'<meta name="twitter:description" content="{attr(desc)}" />',
        f'<meta name="twitter:image" content="{BASE}/{img}" />',
    ]
    if p is not None:
        lines.insert(-5, f'<meta property="article:published_time" content="{p["date"]}" />')
        for a in p["authors"]:
            lines.insert(-5, f'<meta property="article:author" content="{attr(a["name"])}" />')
    for obj in ld:
        lines.append('<script type="application/ld+json">'
                     + json.dumps(obj, ensure_ascii=False) + "</script>")
    lines.append(END)
    return "\n".join(l for l in lines if l)


def inject(path, block):
    html = path.read_text(encoding="utf-8")
    if START in html:
        html = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, html, flags=re.S)
    else:
        # drop a pre-existing bare description so it isn't duplicated
        html = re.sub(r'\n?<meta name="description"[^>]*/>', "", html, count=1)
        html, n = re.subn(r"(</title>)", lambda m: m.group(1) + "\n" + block, html, count=1)
        assert n == 1, f"no <title> in {path}"
    assert html.count(START) == 1 and html.count('name="description"') == 1, path
    path.write_text(html, encoding="utf-8", newline="\n")


def git_lastmod(path):
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(path)],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return out or datetime.now().strftime("%Y-%m-%d")


def main():
    inject(ROOT / "index.html", head_block(None))
    for p in PIECES:
        f = ROOT / "pieces" / f"{p['file']}.html"
        assert f.exists(), f
        inject(f, head_block(p))

    urls = [(BASE + "/", git_lastmod(ROOT / "index.html"))]
    urls += [(piece_url(p), git_lastmod(ROOT / "pieces" / f"{p['file']}.html")) for p in PIECES]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, d in urls:
        sm.append(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>")
    sm.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8", newline="\n")

    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8", newline="\n")

    items = []
    for p in sorted(PIECES, key=lambda q: q["date"], reverse=True):
        d = datetime.strptime(p["date"] + "-01", "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
        items.append(
            f"    <item><title>{escape(p['title'])}</title><link>{piece_url(p)}</link>"
            f"<guid isPermaLink=\"true\">{piece_url(p)}</guid><pubDate>{format_datetime(d)}</pubDate>"
            f"<description>{escape(p['desc'])}</description></item>")
    rss = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>',
           f"    <title>{SITE_NAME}</title><link>{BASE}/</link>",
           f"    <description>{escape(SITE_DESC)}</description><language>en</language>", *items,
           "</channel></rss>"]
    (ROOT / "rss.xml").write_text("\n".join(rss) + "\n", encoding="utf-8", newline="\n")
    print(f"ok: {len(PIECES)} pieces + index, sitemap {len(urls)} urls")


if __name__ == "__main__":
    main()
