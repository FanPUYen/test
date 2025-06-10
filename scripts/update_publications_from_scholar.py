#!/usr/bin/env python3
"""Update _publications from Google Scholar profile."""

import os
import re
import yaml
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    from scholarly import scholarly
except ImportError:
    raise SystemExit("Please install the 'scholarly' package")

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "_config.yml"
PUB_DIR = ROOT / "_publications"


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def load_scholar_id() -> str:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file {CONFIG_PATH} not found")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    url = cfg.get("author", {}).get("googlescholar", "")
    if not url:
        return ""
    query = urlparse(url).query
    params = parse_qs(query)
    return params.get("user", [""])[0]


def publication_to_markdown(pub: dict) -> (str, str):
    bib = pub.get("bib", {})
    title = bib.get("title", "Untitled")
    year = str(bib.get("pub_year", "1900"))
    date = f"{year}-01-01"
    slug = slugify(title)
    permalink = f"/publication/{date}-{slug}"
    excerpt = bib.get("abstract", "")
    venue = bib.get("venue", "")
    paperurl = pub.get("pub_url", "") or pub.get("eprint_url", "")
    authors = bib.get("author", "")
    citation = f"{authors} ({year}). \"{title}.\" {venue}."

    front_matter = {
        "title": title,
        "collection": "publications",
        "permalink": permalink,
        "excerpt": excerpt,
        "date": date,
        "venue": venue,
        "paperurl": paperurl,
        "citation": citation,
    }
    yaml_text = yaml.safe_dump(front_matter, sort_keys=False, allow_unicode=True)
    content = f"---\n{yaml_text}---\n"
    filename = f"{date}-{slug}.md"
    return filename, content


def main():
    scholar_id = load_scholar_id()
    if not scholar_id:
        raise SystemExit("No Google Scholar ID found in _config.yml")

    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=["publications"])
    publications = author.get("publications", [])

    PUB_DIR.mkdir(exist_ok=True)
    for pub in publications:
        filled = scholarly.fill(pub)
        fname, md = publication_to_markdown(filled)
        path = PUB_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Updated {path}")


if __name__ == "__main__":
    main()
