"""Scrape the Pokemon Champions items list from Serebii."""
from __future__ import annotations

import re
from typing import Any, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from ._utils import (
    absolute_url,
    clean_text,
    fetch_html,
    make_soup,
    polite_sleep,
)

ITEMS_URL = "https://www.serebii.net/pokemonchampions/items.shtml"

# Categories that keep the Champions list-page effect (no ItemDex in-depth scrape).
_SKIP_IN_DEPTH_CATEGORIES = frozenset({"Miscellaneous Items", "Mega Stone"})

# Serebii repeats the same boilerplate at the start of many item blurbs on the list page.
_HOLD_ITEM_PREFIX = re.compile(
    r"^\s*An item to be held by (?:a )?(?:Pokémon|Pokemon|Pikachu)\.\s*",
    re.IGNORECASE,
)
_MEGA_STONE_PREFIX = re.compile(
    r"^\s*One of a variety of mysterious Mega Stones\.\s*",
    re.IGNORECASE,
)


def _strip_item_effect_boilerplate(effect: Optional[str], category: str) -> Optional[str]:
    """Remove category-specific filler that Serebii prepends to every list row."""
    if not effect:
        return None
    text = effect.strip()
    if not text:
        return None

    if category == "Hold Items":
        text = _HOLD_ITEM_PREFIX.sub("", text)
    elif category == "Mega Stone":
        text = _MEGA_STONE_PREFIX.sub("", text)

    text = " ".join(text.split())
    return text or None


def _category_before(table: Tag) -> str:
    """Categories are marked with a <b> (e.g. 'Hold Items') directly above each table."""
    prev = table.find_previous(["b", "h1", "h2", "h3"])
    if prev is None:
        return "Miscellaneous"
    return clean_text(prev) or "Miscellaneous"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _first_paragraph_text(cell: Tag) -> str:
    """Text before the first <br> in an ItemDex fooinfo cell (Champions-relevant blurb)."""
    parts: list[str] = []
    for child in cell.children:
        if isinstance(child, Tag) and child.name == "br":
            break
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            parts.append(child.get_text(" ", strip=True))
    return " ".join("".join(parts).split())


def _parse_item_detail(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """Return (sprite_url, in_depth_effect) from an ItemDex detail page."""
    sprite: Optional[str] = None
    effect: Optional[str] = None

    for table in soup.find_all("table", class_="dextable"):
        rows = table.find_all("tr", recursive=False)
        if not rows:
            continue
        header_cells = rows[0].find_all(["td", "th"], recursive=False)
        if not header_cells:
            continue
        header = clean_text(header_cells[0])

        if header == "Sprites":
            img = table.find("img")
            if img and img.get("src"):
                sprite = absolute_url(img["src"])
        elif header == "In-Depth Effect" and len(rows) > 1:
            effect_cells = rows[1].find_all("td", recursive=False)
            if effect_cells:
                raw = _first_paragraph_text(effect_cells[0])
                effect = raw.strip() or None

    return sprite, effect


def scrape_items(
    url: str = ITEMS_URL,
    *,
    detail_sleep: float = 1.5,
) -> dict[str, Any]:
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

            anchor = name_cell.find("a")
            page_url = absolute_url(anchor.get("href")) if anchor and anchor.get("href") else None

            sprite: Optional[str] = None
            img = pic_cell.find("img")
            if img and img.get("src"):
                sprite = absolute_url(img["src"])

            raw_effect = clean_text(effect_cell) or None
            items.append(
                {
                    "slug": _slug(name),
                    "name": name,
                    "category": category_name,
                    "effect": _strip_item_effect_boilerplate(raw_effect, category_name),
                    "location": clean_text(location_cell) if location_cell else None,
                    "sprite": sprite,
                    "page_url": page_url,
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

    use_in_depth = [it for it in flat_items if it["category"] not in _SKIP_IN_DEPTH_CATEGORIES]
    fetch_for_sprite = [it for it in flat_items if it.get("page_url")]

    print(
        f"   fetching {len(fetch_for_sprite)} item detail pages "
        f"({len(use_in_depth)} for in-depth effects)...",
        flush=True,
    )

    def _apply_detail(item: dict[str, Any], detail_url: str) -> bool:
        detail_html = fetch_html(detail_url)
        detail_sprite, in_depth = _parse_item_detail(make_soup(detail_html))
        if detail_sprite:
            item["sprite"] = detail_sprite
        if item["category"] not in _SKIP_IN_DEPTH_CATEGORIES and in_depth:
            item["effect"] = in_depth
        return bool(detail_sprite or in_depth)

    failed: list[dict[str, Any]] = []
    for i, item in enumerate(fetch_for_sprite):
        detail_url = item.get("page_url")
        if not detail_url:
            continue
        try:
            if not _apply_detail(item, detail_url):
                failed.append(item)
        except Exception:
            failed.append(item)
        if i < len(fetch_for_sprite) - 1:
            polite_sleep(detail_sleep)

    if failed:
        print(f"   retrying {len(failed)} item detail pages...", flush=True)
        still_failed: list[dict[str, Any]] = []
        for j, item in enumerate(failed):
            detail_url = item.get("page_url")
            if not detail_url:
                continue
            try:
                if j > 0:
                    polite_sleep(detail_sleep * 2)
                if not _apply_detail(item, detail_url):
                    still_failed.append(item)
            except Exception:
                still_failed.append(item)
        failed = still_failed

    missing_sprite = sum(1 for it in fetch_for_sprite if it.get("page_url") and not it.get("sprite"))
    missing_effect = sum(
        1
        for it in flat_items
        if it["category"] not in _SKIP_IN_DEPTH_CATEGORIES and not it.get("effect")
    )

    for item in flat_items:
        item.pop("page_url", None)

    if missing_sprite or missing_effect or failed:
        print(
            f"   warning: {missing_sprite} items missing detail-page sprite, "
            f"{missing_effect} missing in-depth effect (list fallback kept)"
            + (f"; {len(failed)} ItemDex pages unavailable" if failed else ""),
            flush=True,
        )

    return {
        "categories": sorted(categories.keys()),
        "items": flat_items,
    }
