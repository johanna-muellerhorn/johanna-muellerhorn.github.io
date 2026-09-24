"""
generate_webpage_publist.py  v1
--------------------------------
Queries NASA ADS / SciX for all papers by Johanna Müller-Horn and generates
the HTML publications section for johanna-muellerhorn.github.io — formatted
exactly to match the existing <div class="publications-by-year"> structure.

TWO integration modes:
  1. Standalone snippet  →  _publications_snippet.html  (always written)
  2. In-place update     →  index.html updated directly, if you add the two
                            marker comments described in HOW TO USE below.

HOW TO USE:
  pip install ads
  export ADS_DEV_KEY="your_token"   # from ui.adsabs.harvard.edu/user/settings/token

  In your index.html, wrap the publications div with the two marker comments:
    <!-- PUBLIST:START -->
    <div class="publications-by-year">
      ...
    </div>
    <!-- PUBLIST:END -->

  Then run:
    python generate_webpage_publist.py

  The script replaces everything between the markers and writes
  _publications_snippet.html as a backup.
"""

import ads
import os
import re
from datetime import datetime
from collections import defaultdict
from urllib.parse import quote

# ══════════════════════════════════════════════════════════════════════════════
# Configuration — edit this section
# ══════════════════════════════════════════════════════════════════════════════

ADS_TOKEN    = os.environ.get("ADS_DEV_KEY", "kJxCI26lUNiRhI4LeZf4RtjRpm71xCXICAPdUqpu")
AUTHOR_QUERY = "Müller-Horn, J"

# Name variants used to identify you as first author
BOLD_PATTERNS = [
    "Müller-Horn, J",
    "Mueller-Horn, J",
    "Müller-Horn, Johanna",
]

INCLUDE_ARXIV = True   # include arXiv-only / preprint papers
MIN_YEAR      = 2018   # ignore papers before this year (0 = no limit)

# Wrap your name in <strong> in co-author lists?
# False matches the current website style (plain text); True adds bold.
BOLD_NAME_HTML = False

# Path to index.html relative to where you run this script
INDEX_HTML_PATH = "index.html"

# ── arXiv / accepted paper notes ───────────────────────────────────────────────
# For preprints and accepted-but-not-published papers, set the text shown
# in the publication-journal field. Use HTML entities (& → &amp;).
#
# Key:   arXiv short ID (e.g. "2601.14403") OR full ADS bibcode
# Value: shown verbatim in the publication-journal div
PAPER_NOTES = {
    "2026arXiv260901822P": r"accepted, \textit{A\&A}",
    "2026arXiv260806453E": r"submitted to \textit{OJAp}",
    "2026arXiv260805276M": r"accepted, \textit{A\&A}",
    "2026arXiv260726149S": r"submitted to \textit{ApJS}",
}

# ── Year overrides ─────────────────────────────────────────────────────────────
# Force a paper into a specific year group, overriding what ADS reports.
# Useful for papers accepted/published in a later year than their arXiv date.
#
# Key:   arXiv short ID or ADS bibcode
# Value: year string, e.g. "2026"
PAPER_YEAR_OVERRIDES = {
    "2510.05982": "2026",   # posted arXiv Oct 2025, accepted A&A 2026
}

# ── Journal display names (HTML) ───────────────────────────────────────────────
# These are the abbreviated names shown on the website.
# Note: "A&A" must be written as "A&amp;A" for valid HTML.
HTML_JOURNAL_ABBREV = {
    "The Astrophysical Journal":                   "ApJ",
    "The Astrophysical Journal Letters":           "ApJ Letters",
    "The Astrophysical Journal Supplement Series": "ApJS",
    "Astronomy and Astrophysics":                  "A&amp;A",
    "Monthly Notices of the Royal Astronomical Society": "MNRAS",
    "The Astronomical Journal":                    "AJ",
    "Nature":                                      "Nature",
    "Nature Astronomy":                            "Nature Astronomy",
    "Science":                                     "Science",
    "Publications of the Astronomical Society of the Pacific": "PASP",
    "arXiv e-prints":                              "arXiv",
}

# ══════════════════════════════════════════════════════════════════════════════
# ADS query
# ══════════════════════════════════════════════════════════════════════════════

def fetch_papers(token: str, author: str) -> list:
    ads.config.token = token
    fields = ["title", "author", "year", "pub", "volume", "page",
              "doi", "identifier", "bibcode", "pubdate", "doctype",
              "citation_count"]
    return list(ads.SearchQuery(
        q=f'author:"{author}"',
        fl=fields,
        rows=200,
        sort="date desc",
    ))

# ══════════════════════════════════════════════════════════════════════════════
# Paper utilities (shared logic with generate_publist.py)
# ══════════════════════════════════════════════════════════════════════════════

def get_paper_keys(paper) -> list[str]:
    """All lookup keys for this paper: bibcode + arXiv ID variants."""
    keys = []
    if paper.bibcode:
        keys.append(paper.bibcode)
    if paper.identifier:
        for ident in paper.identifier:
            if "arXiv:" in ident:
                short = ident.replace("arXiv:", "")
                keys.append(short)       # "2601.14403"
                keys.append(ident)       # "arXiv:2601.14403"
    return keys

def lookup(mapping: dict, paper) -> str | None:
    """Return the first matching value in mapping for this paper, or None."""
    for k in get_paper_keys(paper):
        if k in mapping:
            return mapping[k]
    return None

def is_target_author(name: str) -> bool:
    return any(
        re.search(re.escape(p), name, re.IGNORECASE)
        for p in BOLD_PATTERNS
    )

def is_first_author(paper) -> bool:
    return bool(paper.author) and is_target_author(paper.author[0])

def is_refereed(paper) -> bool:
    return paper.doctype in ("article", "inbook", "proceedings") or (
        paper.doctype == "eprint" and INCLUDE_ARXIV
    )

def filter_papers(papers: list) -> list:
    kept = []
    for p in papers:
        if MIN_YEAR and p.year and int(p.year) < MIN_YEAR:
            continue
        if not is_refereed(p):
            continue
        kept.append(p)
    return kept

def paper_year(paper) -> str:
    """Return the year to use for grouping (honoring PAPER_YEAR_OVERRIDES)."""
    override = lookup(PAPER_YEAR_OVERRIDES, paper)
    return override if override else (paper.year or "0000")

# ══════════════════════════════════════════════════════════════════════════════
# HTML formatting helpers
# ══════════════════════════════════════════════════════════════════════════════

def he(text: str) -> str:
    """Minimal HTML escaping for text content (not attributes)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def abbreviate_journal(journal: str) -> str:
    if not journal:
        return ""
    for full, abbr in HTML_JOURNAL_ABBREV.items():
        if full.lower() in journal.lower():
            return abbr
    return he(journal)

def format_title(paper) -> str:
    t = paper.title
    if isinstance(t, list):
        t = t[0] if t else "Untitled"
    return he(t or "Untitled")

def format_authors(paper) -> str:
    """Full author list, semicolon-separated, optionally with your name in bold."""
    authors = paper.author or []
    if not authors:
        return "Unknown"
    parts = []
    for a in authors:
        escaped = he(a)
        if BOLD_NAME_HTML and is_target_author(a):
            parts.append(f"<strong>{escaped}</strong>")
        else:
            parts.append(escaped)
    return " ; ".join(parts)

def format_journal(paper) -> str:
    """
    Journal field shown under the title.
    Priority: PAPER_NOTES entry → formatted journal/volume/page → fallback.
    """
    note = lookup(PAPER_NOTES, paper)
    if note:
        return note   # already HTML-safe (user writes &amp; directly)

    journal = abbreviate_journal(paper.pub or "")
    volume  = paper.volume or ""
    page    = (paper.page[0] if isinstance(paper.page, list) else paper.page) \
              if paper.page else ""

    if not journal or journal in ("arXiv", ""):
        return "arXiv preprint"

    parts = [journal]
    if volume:
        parts.append(f"Volume {volume}")
    if page:
        parts.append(he(str(page)))
    return " ".join(parts)

def ads_url(bibcode: str) -> str:
    """ADS abstract URL with URL-encoded bibcode (e.g. A%26A for A&A)."""
    return f"https://ui.adsabs.harvard.edu/abs/{quote(bibcode, safe='')}/abstract"

# ══════════════════════════════════════════════════════════════════════════════
# HTML block builders — indentation mirrors the existing index.html structure
# ══════════════════════════════════════════════════════════════════════════════

I0 = ""          # publications-by-year
I1 = "\t\t\t\t"  # div.year
I2 = "\t\t\t\t\t"  # h5, div.year-group
I3 = "\t\t\t\t\t\t"  # year-box, ul.paper-list
I4 = "\t\t\t\t\t\t\t"  # li.enumerated-item
I5 = "\t\t\t\t\t\t\t\t"  # div.publication-entry
I6 = "\t\t\t\t\t\t\t\t\t"  # content divs inside entry


def render_paper(paper) -> str:
    bibcode = paper.bibcode or ""
    url     = ads_url(bibcode)
    title   = format_title(paper)
    authors = format_authors(paper)
    journal = format_journal(paper)

    return "\n".join([
        f'{I4}<li class="enumerated-item">',
        f'{I5}<div class="publication-entry">',
        f'{I6}<a href="{url}" class="publication-title-link">'
            f'{title} <i class="fas fa-external-link-alt external-icon"></i></a>',
        f'{I6}<div class="publication-authors">{authors}</div>',
        f'{I6}<div class="publication-journal">{journal}</div>',
        f'{I6}<div class="publication-link"><a href="{url}">{he(bibcode)}</a></div>',
        f'{I5}</div>',
        f'{I4}</li>',
    ])


def render_year_group(year: str, papers: list) -> str:
    paper_html = "\n".join(render_paper(p) for p in papers)
    return "\n".join([
        f'{I2}<div class="year-group">',
        f'{I3}<div class="publication-year-box">{year}</div>',
        f'{I3}<ul class="paper-list">',
        paper_html,
        f'{I3}</ul>',
        f'{I2}</div>',
    ])


def render_section(label: str, papers: list) -> str:
    """One <div class="year"> section with year subgroups."""
    # Group by display year, preserve descending sort
    by_year: dict[str, list] = defaultdict(list)
    for p in papers:
        by_year[paper_year(p)].append(p)

    year_groups = "\n".join(
        render_year_group(yr, by_year[yr])
        for yr in sorted(by_year.keys(), reverse=True)
    )

    return "\n".join([
        f'{I1}<div class="year">',
        f'{I2}<h5>{label}</h5>',
        year_groups,
        f'{I1}</div>',
    ])


def build_snippet(first_author: list, co_author: list) -> str:
    today = datetime.today().strftime("%B %Y")
    return "\n".join([
        f'<!-- Publications generated by generate_webpage_publist.py — {today} -->',
        f'<div class="publications-by-year">',
        render_section("First-author papers", first_author),
        render_section("Co-author papers",    co_author),
        f'</div>',
        f'<!-- End of generated publications -->',
    ])

# ══════════════════════════════════════════════════════════════════════════════
# index.html in-place updater
# ══════════════════════════════════════════════════════════════════════════════

START_MARKER = "<!-- PUBLIST:START -->"
END_MARKER   = "<!-- PUBLIST:END -->"

_MARKER_INSTRUCTIONS = f"""
  To enable auto-update of index.html, wrap your publications div with:

    {START_MARKER}
    <div class="publications-by-year">
      ...existing content...
    </div>
    {END_MARKER}

  Then re-run this script. Everything between the markers will be replaced.
"""

def update_index_html(snippet: str, path: str) -> bool:
    if not os.path.exists(path):
        print(f"  ℹ️  {path} not found — only snippet file written.")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        print(f"  ℹ️  Marker comments not found in {path}.")
        print(_MARKER_INSTRUCTIONS)
        return False

    # Replace everything between (and including) the markers
    pattern  = re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER)
    replaced = re.sub(
        pattern,
        f"{START_MARKER}\n{snippet}\n{END_MARKER}",
        content,
        flags=re.DOTALL,
    )

    # Safety check: don't write if nothing changed or pattern matched twice
    if replaced == content:
        print(f"  ℹ️  {path} is already up to date.")
        return True
    if replaced.count(START_MARKER) != 1:
        print(f"  ⚠️  Multiple marker pairs found in {path} — not updating. Check your HTML.")
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(replaced)

    print(f"  ✅  {path} updated in place.")
    return True

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print(f"Querying ADS for: {AUTHOR_QUERY} ...")

    if ADS_TOKEN == "YOUR_TOKEN_HERE":
        print("\n⚠️  No ADS token set.")
        print("   Get one at: https://ui.adsabs.harvard.edu/user/settings/token")
        print("   Then:  export ADS_DEV_KEY='your_token'\n")
        return

    papers = fetch_papers(ADS_TOKEN, AUTHOR_QUERY)
    papers = filter_papers(papers)
    print(f"  Found {len(papers)} papers after filtering.")

    first_author = [p for p in papers if is_first_author(p)]
    co_author    = [p for p in papers if not is_first_author(p)]
    print(f"  First-author: {len(first_author)},  Co-author: {len(co_author)}")

    # Remind about arXiv papers without notes
    arxiv_without_note = [
        p for p in papers
        if p.doctype == "eprint" and lookup(PAPER_NOTES, p) is None
    ]
    if arxiv_without_note:
        print(f"\n  ℹ️  {len(arxiv_without_note)} arXiv-only paper(s) with no PAPER_NOTES entry "
              f"(will show as 'arXiv preprint'):")
        for p in arxiv_without_note:
            keys   = get_paper_keys(p)
            title  = (p.title[0] if p.title else "???")[:65]
            print(f"    Keys: {keys}")
            print(f"    → {title}")

    # Report year overrides applied
    overridden = [p for p in papers if lookup(PAPER_YEAR_OVERRIDES, p)]
    if overridden:
        print(f"\n  📅  Year overrides applied:")
        for p in overridden:
            yr = lookup(PAPER_YEAR_OVERRIDES, p)
            print(f"    {p.bibcode}: ADS year {p.year} → displayed as {yr}")

    snippet = build_snippet(first_author, co_author)

    # Always write standalone snippet
    snippet_path = "_publications_snippet.html"
    with open(snippet_path, "w", encoding="utf-8") as f:
        f.write(snippet)
    print(f"\n  ✅  {snippet_path} written.")

    # Try to update index.html in place
    update_index_html(snippet, INDEX_HTML_PATH)

    print("\nDone.")
    print(f"Compile check: open {snippet_path} in a browser to preview the snippet.")


if __name__ == "__main__":
    main()