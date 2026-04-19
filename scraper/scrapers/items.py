"""Scrape the Pokemon Champions items list from Serebii."""
from __future__ import annotations

import re
from typing import Any, Optional

from ._utils import (
    absolute_url,
    clean_text,
    fetch_html,
    make_soup,
)

ITEMS_URL = "https://www.serebii.net/pokemonchampions/items.shtml"


def _category_before(table) -> str:
    """Categories are marked with a <b> (e.g. 'Hold Items') directly above each table."""
    prev = table.find_previous(["b", "h1", "h2", "h3"])
    if prev is None:
        return "Miscellaneous"
    return clean_text(prev) or "Miscellaneous"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def scrape_items(url: str = ITEMS_URL) -> dict[str, Any]:
    html = fetch_html(url)
    soup = make_soup(html)

    categories: dict[str, list[dict[str, Any]]] = {}

    for table in soup.find_all("table", class_="dextable"):
        rows = table.find_all("tr", recursive=False)
        if not rows:
            continue

        header = [clean_text(c).lower() for c in rows[0].find_all(["td", "th"], recursive=False)]
        if not ("picture" in header and "name" in header and "effect" in header):
            continue

        category_name = _category_before(table)
        items: list[dict[str, Any]] = []

        for row in rows[1:]:
            cells = row.find_all(["td", "th"], recursive=False)
            if len(cells) < 3:
                continue

            pic_cell, name_cell, effect_cell = cells[0], cells[1], cells[2]
            location_cell = cells[3] if len(cells) > 3 else None

            name = clean_text(name_cell)
            if not name:
                continue

            sprite: Optional[str] = None
            img = pic_cell.find("img")
            if img and img.get("src"):
                sprite = absolute_url(img["src"])

            items.append(
                {
                    "slug": _slug(name),
                    "name": name,
                    "category": category_name,
                    "effect": clean_text(effect_cell) or None,
                    "location": clean_text(location_cell) if location_cell else None,
                    "sprite": sprite,
                }
            )

        if items:
            categories.setdefault(category_name, []).extend(items)

    flat_items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cat, items in categories.items():
        for it in items:
            if it["slug"] in seen:
                continue
            seen.add(it["slug"])
            flat_items.append(it)

    flat_items.sort(key=lambda m: m["name"].lower())

    return {
        "categories": sorted(categories.keys()),
        "items": flat_items,
    }
