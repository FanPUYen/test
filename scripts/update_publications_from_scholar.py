#!/usr/bin/env python3
"""Update `_publications` from a Google Scholar profile.

This implementation avoids third party dependencies so it can run in
environments without network access to install packages. It scrapes the
public list of works using only the Python standard library.
"""

import re
import html
import urllib.request
from urllib.error import URLError
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "_config.yml"
PUB_DIR = ROOT / "_publications"
BASE_URL = "https://scholar.google.com"


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def load_scholar_id() -> str:
    """Parse the Scholar profile URL from `_config.yml`."""
    if not CONFIG_PATH.exists():
        return ""
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            if "googlescholar" in line:
                _, val = line.split(":", 1)
                url = val.strip().strip('"').strip("'")
                query = urlparse(url).query
                params = parse_qs(query)
                return params.get("user", [""])[0]
    return ""


def yaml_dump(data: dict) -> str:
    """Return a minimal YAML representation of `data`."""
    lines = []
    for key, value in data.items():
        if value is None:
            value = ""
        escaped = str(value).replace('"', '\\"')
        lines.append(f'{key}: "{escaped}"')
    return "\n".join(lines)


def publication_to_markdown(pub: dict) -> (str, str):
    title = pub.get("title", "Untitled")
    year = str(pub.get("year", "1900"))
    date = f"{year}-01-01"
    slug = slugify(title)
    permalink = f"/publication/{date}-{slug}"
    venue = pub.get("venue", "")
    paperurl = pub.get("paperurl", "")
    authors = pub.get("authors", "")
    citation = f"{authors} ({year}). \"{title}.\" {venue}."

    front_matter = {
        "title": title,
        "collection": "publications",
        "permalink": permalink,
        "date": date,
        "venue": venue,
        "paperurl": paperurl,
        "citation": citation,
    }
    yaml_text = yaml_dump(front_matter)
    content = f"---\n{yaml_text}\n---\n"
    filename = f"{date}-{slug}.md"
    return filename, content


def fetch_publications(scholar_id: str):
    """Return a list of publications for the given Scholar ID."""
    url = f"{BASE_URL}/citations?hl=en&user={scholar_id}&view_op=list_works&sortby=pubdate"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            html_text = resp.read().decode("utf-8")
    except URLError as e:
        raise RuntimeError(f"Failed to fetch Google Scholar page: {e}")

    rows = re.findall(r'<tr class="gsc_a_tr".*?</tr>', html_text, re.S)
    pubs = []
    for row in rows:
        title_match = re.search(r'class="gsc_a_at".*?>(.*?)</a>', row)
        title = html.unescape(title_match.group(1)) if title_match else "Untitled"

        authors_match = re.findall(r'class="gs_gray">(.*?)</div>', row)
        authors = html.unescape(authors_match[0]) if authors_match else ""
        venue = html.unescape(authors_match[1]) if len(authors_match) > 1 else ""

        year_match = re.search(r'class="gsc_a_y".*?>(\d{4})<', row)
        year = year_match.group(1) if year_match else "1900"

        link_match = re.search(r'<a class="gsc_a_at" href="(.*?)">', row)
        paperurl = BASE_URL + link_match.group(1) if link_match else ""

        pubs.append({
            "title": title,
            "authors": authors,
            "venue": venue,
            "year": year,
            "paperurl": paperurl,
        })

    return pubs


def main():
    scholar_id = load_scholar_id()
    if not scholar_id:
        raise SystemExit("No Google Scholar ID found in _config.yml")

    pubs = fetch_publications(scholar_id)

    PUB_DIR.mkdir(exist_ok=True)
    for pub in pubs:
        fname, md = publication_to_markdown(pub)
        path = PUB_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Updated {path}")


if __name__ == "__main__":
    main()
