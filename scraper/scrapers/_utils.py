"""Shared helpers for all Serebii scrapers."""
from __future__ import annotations

import random
import re
import time
from pathlib import Path
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://www.serebii.net"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_html(url: str, *, timeout: int = 30, retries: int = 3, backoff: float = 2.0) -> str:
    """Fetch a URL and return its text content. Retries on network errors."""
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def absolute_url(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return f"{BASE_URL}/{href}"


def clean_text(node: Optional[Tag]) -> str:
    if node is None:
        return ""
    return " ".join(node.get_text(" ", strip=True).split())


def extract_type_from_img(img_src: str) -> Optional[str]:
    """Type images live at /pokedex-bw/type/<type>.gif or /pokedex-sv/type/icon/<type>.png."""
    if not img_src:
        return None
    m = re.search(r"/type(?:/icon)?/([a-zA-Z]+)\.(?:gif|png)", img_src)
    if not m:
        return None
    value = m.group(1).lower()
    if value in {"physical", "special", "other"}:
        return None
    return value


def extract_category_from_img(img_src: str) -> Optional[str]:
    """Returns one of physical, special, status (other -> status)."""
    if not img_src:
        return None
    m = re.search(r"/type/(physical|special|other)\.png", img_src)
    if not m:
        return None
    raw = m.group(1).lower()
    return "status" if raw == "other" else raw


def parse_number(text: str) -> Optional[int]:
    text = (text or "").strip()
    if not text or text in {"--", "-", ""}:
        return None
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return None


def parse_stat_range_low(text: str) -> Optional[int]:
    """First integer in a Serebii stat cell: '153 - 185' -> 153, '104' -> 104."""
    text = (text or "").strip()
    if not text or text in {"--", "-"}:
        return None
    m = re.match(r"^(\d[\d,]*)\s*-\s*(\d[\d,]*)", text.replace(",", ""))
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return parse_number(text)


def slug_from_href(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    # e.g. /attackdex-champions/accelerock.shtml -> accelerock
    # e.g. /pokedex-champions/venusaur/ -> venusaur
    # e.g. /abilitydex/overgrow.shtml -> overgrow
    m = re.search(r"/([^/]+?)(?:\.shtml)?/?$", href.rstrip("/"))
    if not m:
        return None
    slug = m.group(1).lower()
    if slug.endswith(".shtml"):
        slug = slug[:-6]
    return slug


def write_json(path: Path, data: Any) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def polite_sleep(seconds: float = 1.5, jitter: float = 0.5) -> None:
    """Sleep for roughly ``seconds`` (+ up to ``jitter`` seconds of randomness).

    Defaults to 1.5–2.0s so Serebii doesn't IP-ban the scraper.
    """
    extra = random.uniform(0, max(0.0, jitter))
    time.sleep(max(0.0, seconds) + extra)
