"""
generate_publist.py  v2
-----------------------
Queries NASA ADS / SciX for all papers by an author and generates a
formatted LaTeX publication list, split into first-author and co-author
sections, with the author's name automatically bolded.

Generates TWO output files in one run:
  publist_citations.tex    – includes citation counts
  publist_nocitations.tex  – without citation counts

SETUP:
  pip install ads

  Get a free ADS API token at:
  https://ui.adsabs.harvard.edu/user/settings/token
  Then set:  export ADS_DEV_KEY="your_token_here"
  Or paste it directly into ADS_TOKEN below.

USAGE:
  python generate_publist.py
"""

import ads
import os
import re
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────

ADS_TOKEN     = os.environ.get("ADS_DEV_KEY", "kJxCI26lUNiRhI4LeZf4RtjRpm71xCXICAPdUqpu")
AUTHOR_QUERY  = "Müller-Horn, J"           # ADS author search string
BOLD_PATTERNS = [                           # strings to match your name in author lists
    "Müller-Horn, J",
    "Mueller-Horn, J",
    "Müller-Horn, Johanna",
]
BOLD_SHORT    = r"J.~Müller-Horn"          # short form used in "et al. [N others incl. X]"
MAX_AUTHORS   = 4                           # authors shown before "et al."
INCLUDE_ARXIV = True                        # include arXiv-only papers
MIN_YEAR      = 2018                        # ignore papers before this year (0 = no limit)

# ── arXiv / in-prep paper notes ────────────────────────────────────────────────
# For papers not yet published, add a note here so it appears after the entry.
# Key: arXiv ID short form (e.g. "2401.12345") OR ADS bibcode.
# Value: LaTeX string — will be rendered as italics in parentheses.
#
# Examples:
#   "2401.12345": r"submitted to \textit{A\&A}",
#   "2312.67890": r"accepted, \textit{MNRAS}",
#   "2024arXiv240112345M": r"in preparation",
PAPER_NOTES = {
    "2026arXiv260901822P": r"accepted, \textit{A\&A}",
    "2026arXiv260806453E": r"submitted to \textit{OJAp}",
    "2026arXiv260805276M": r"accepted, \textit{A\&A}",
    "2026arXiv260726149S": r"submitted to \textit{ApJS}",
}

# ── ADS query ──────────────────────────────────────────────────────────────────

def fetch_papers(token: str, author: str) -> list:
    ads.config.token = token
    fields = ["title", "author", "year", "pub", "volume", "page",
              "doi", "identifier", "bibcode", "pubdate", "doctype",
              "citation_count", "arxiv_class"]
    results = list(ads.SearchQuery(
        q=f'author:"{author}"',
        fl=fields,
        rows=200,
        sort="date desc"
    ))
    return results


# ── Paper note lookup ──────────────────────────────────────────────────────────

def get_paper_keys(paper) -> list:
    """Return all possible lookup keys for PAPER_NOTES (bibcode + arXiv IDs)."""
    keys = []
    if paper.bibcode:
        keys.append(paper.bibcode)
    if paper.identifier:
        for ident in paper.identifier:
            if "arXiv:" in ident:
                short = ident.replace("arXiv:", "")
                keys.append(short)   # "2401.12345"
                keys.append(ident)   # "arXiv:2401.12345"
    return keys

def get_paper_note(paper) -> str | None:
    """Return the manual note for this paper, or None."""
    for key in get_paper_keys(paper):
        if key in PAPER_NOTES:
            return PAPER_NOTES[key]
    return None


# ── Formatting helpers ──────────────────────────────────────────────────────────

JOURNAL_ABBREV = {
    "The Astrophysical Journal":                   r"ApJ",
    "The Astrophysical Journal Letters":           r"ApJL",
    "The Astrophysical Journal Supplement Series": r"ApJS",
    "Astronomy and Astrophysics":                  r"A\&A",
    "Monthly Notices of the Royal Astronomical Society": r"MNRAS",
    "The Astronomical Journal":                    r"AJ",
    "Nature":                                      r"Nature",
    "Nature Astronomy":                            r"Nat.\ Astron.",
    "Science":                                     r"Science",
    "Publications of the Astronomical Society of the Pacific": r"PASP",
    "arXiv e-prints":                              r"arXiv",
}

def abbreviate_journal(journal: str) -> str:
    if not journal:
        return ""
    for full, abbr in JOURNAL_ABBREV.items():
        if full.lower() in journal.lower():
            return abbr
    return journal

def bold_author(name: str) -> str:
    for pat in BOLD_PATTERNS:
        if re.search(re.escape(pat), name, re.IGNORECASE):
            return r"\textbf{" + name + r"}"
    return name

def is_target_author(name: str) -> bool:
    for pat in BOLD_PATTERNS:
        if re.search(re.escape(pat), name, re.IGNORECASE):
            return True
    return False

def format_authors(authors: list, max_n: int) -> str:
    """
    Format author list. If the target author falls beyond max_n, append
    "et al. [N others incl. J. Müller-Horn]" so her name is always visible.
    """
    if not authors:
        return "Unknown"

    # Find whether target author appears beyond the shown window
    hidden_position = None
    for i, author in enumerate(authors[max_n:], start=max_n):
        if is_target_author(author):
            hidden_position = i
            break

    shown = authors[:max_n]
    formatted = [bold_author(a) for a in shown]
    author_str = ", ".join(formatted)

    if len(authors) > max_n:
        n_hidden = len(authors) - max_n
        if hidden_position is not None:
            # Author is hidden behind et al. — make her visible
            author_str += (
                r", et~al. ["
                + str(n_hidden)
                + r"~others incl.\ \textbf{"
                + BOLD_SHORT
                + r"}]"
            )
        else:
            author_str += r", et~al."

    return author_str

def get_doi_url(paper):
    if paper.doi:
        doi = paper.doi[0] if isinstance(paper.doi, list) else paper.doi
        return doi, f"https://doi.org/{doi}"
    if paper.identifier:
        for ident in paper.identifier:
            if ident.startswith("arXiv:"):
                arxiv_id = ident.replace("arXiv:", "")
                return arxiv_id, f"https://arxiv.org/abs/{arxiv_id}"
    return None, None

def format_paper_latex(paper, show_citations: bool) -> str:
    authors   = format_authors(paper.author or [], MAX_AUTHORS)
    year      = paper.year or "????"
    title     = (paper.title[0] if isinstance(paper.title, list)
                 else paper.title or "Untitled").replace("&", r"\&")
    journal   = abbreviate_journal(paper.pub or "")
    volume    = paper.volume or ""
    page      = (paper.page[0] if isinstance(paper.page, list)
                 else paper.page) if paper.page else ""
    doi, url  = get_doi_url(paper)
    citations = paper.citation_count or 0
    note      = get_paper_note(paper)

    parts = [f"{authors} ({year}),"]
    parts.append(r"  \textit{" + title + r"},")

    journal_info = r"  \textit{" + journal + r"}"
    if volume:
        journal_info += f", {volume}"
    if page:
        journal_info += f", {page}"
    parts.append(journal_info + ",")

    if url and doi:
        link_line = r"  \href{" + url + r"}{" + doi + r"}"
        if show_citations and citations > 0:
            link_line += f" [cited {citations}\\texttimes]"
        parts.append(link_line)
    elif show_citations and citations > 0:
        parts.append(f"  [cited {citations}\\texttimes]")

    # Append manual note (submitted / accepted / in prep) if present
    if note:
        parts.append(r"  \textit{(" + note + r")}")

    return "\n".join(parts)


# ── Paper classification ────────────────────────────────────────────────────────

def is_first_author(paper) -> bool:
    if not paper.author:
        return False
    return is_target_author(paper.author[0])

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


# ── LaTeX document builder ──────────────────────────────────────────────────────

LATEX_PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{enumitem}
\usepackage[margin=2.5cm]{geometry}

\hypersetup{
  colorlinks=true,
  urlcolor=blue,
  linkcolor=black,
}

\begin{document}

% ── Auto-generated by generate_publist.py ──
% Generated: DATE

\section*{List of Publications}

\noindent\textit{Last updated: DATE.}
\bigskip

"""

LATEX_FOOTER = r"""
\end{document}
"""

def build_latex(first_author_papers: list, coauthor_papers: list,
                show_citations: bool) -> str:
    today  = datetime.today().strftime("%B %Y")
    header = LATEX_PREAMBLE.replace("DATE", today)

    lines = [header]

    # ── First-author section ──
    lines.append(r"\subsection*{First-Author Papers}")
    if first_author_papers:
        lines.append(r"\begin{enumerate}[leftmargin=*, label={[\arabic*]}, itemsep=6pt]")
        for p in first_author_papers:
            lines.append(r"\item " + format_paper_latex(p, show_citations))
        lines.append(r"\end{enumerate}")
    else:
        lines.append(r"\textit{No first-author papers found.}")
    lines.append("")

    # ── Co-author section ──
    lines.append(r"\subsection*{Co-Authored Papers}")
    if coauthor_papers:
        lines.append(r"\begin{enumerate}[leftmargin=*, label={[\arabic*]}, itemsep=6pt]")
        for p in coauthor_papers:
            lines.append(r"\item " + format_paper_latex(p, show_citations))
        lines.append(r"\end{enumerate}")
    else:
        lines.append(r"\textit{No co-authored papers found.}")

    lines.append(LATEX_FOOTER)
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"Querying ADS for author: {AUTHOR_QUERY} ...")

    if ADS_TOKEN == "YOUR_TOKEN_HERE":
        print("\n⚠️  No ADS API token set.")
        print("   Get one free at: https://ui.adsabs.harvard.edu/user/settings/token")
        print("   Then set:  export ADS_DEV_KEY='your_token'")
        print("   Or paste it into ADS_TOKEN at the top of this script.\n")
        return

    papers = fetch_papers(ADS_TOKEN, AUTHOR_QUERY)
    papers = filter_papers(papers)
    print(f"  Found {len(papers)} papers after filtering.")

    first_author = [p for p in papers if is_first_author(p)]
    co_author    = [p for p in papers if not is_first_author(p)]
    print(f"  First-author: {len(first_author)},  Co-author: {len(co_author)}")

    # Warn about any arXiv-only papers with no note set
    arxiv_only = [
        p for p in papers
        if p.doctype == "eprint" and get_paper_note(p) is None
    ]
    if arxiv_only:
        print(f"\n  ℹ️  {len(arxiv_only)} arXiv-only paper(s) have no status note.")
        print("  Add entries to PAPER_NOTES in the config section to annotate them:")
        for p in arxiv_only:
            keys = get_paper_keys(p)
            title_short = (p.title[0] if p.title else "???")[:60]
            print(f"    Keys: {keys}")
            print(f"    Title: {title_short}...")

    # Generate both versions
    outputs = [
        ("publist_citations.tex",   True,  "with citations"),
        ("publist_nocitations.tex", False, "without citations"),
    ]
    for filename, show_cit, label in outputs:
        latex = build_latex(first_author, co_author, show_citations=show_cit)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(latex)
        print(f"\n✅  {filename}  ({label})")

    print("\nCompile with:  pdflatex publist_citations.tex")
    print("Or use:        \\input{publist_citations.tex}  in your CV.")


if __name__ == "__main__":
    main()
