"""Scrape the Pokemon Champions move list from Serebii."""
from __future__ import annotations

import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from ._utils import (
    absolute_url,
    clean_text,
    extract_category_from_img,
    extract_type_from_img,
    fetch_html,
    make_soup,
    parse_number,
    polite_sleep,
    slug_from_href,
)

MOVES_URL = "https://www.serebii.net/pokemonchampions/moves.shtml"


def _extract_speed_priority_from_soup(soup: BeautifulSoup) -> Optional[int]:
    """Parse the Speed Priority integer from a Champions AttackDex detail page."""
    for table in soup.find_all("table"):
        rows = table.find_all("tr", recursive=False)
        for idx, row in enumerate(rows):
            cells = row.find_all(["td", "th"], recursive=False)
            if len(cells) < 2:
                continue
            labels = [clean_text(c).lower() for c in cells]
            if not any("speed priority" in lab for lab in labels):
                continue
            if idx + 1 >= len(rows):
                continue
            value_cells = rows[idx + 1].find_all(["td", "th"], recursive=False)
            if len(value_cells) < 2:
                continue
            raw = clean_text(value_cells[1]).strip()
            if re.fullmatch(r"-?\d+", raw):
                return int(raw)
    return None


def _parse_accuracy(raw: str) -> Any:
    """Accuracy column uses 101 for moves that always hit / can't miss."""
    raw = (raw or "").strip()
    if not raw or raw == "--":
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if value >= 101:
        return None
    return value


def scrape_moves(url: str = MOVES_URL, *, detail_sleep: float = 1.5) -> list[dict[str, Any]]:
    html = fetch_html(url)
    soup = make_soup(html)

    # Main listing is in table class="tab" with a sortable 7-column layout.
    target_table = None
    for table in soup.find_all("table", class_="tab"):
        rows = table.find_all("tr", recursive=False)
        if len(rows) < 5:
            continue
        header_cells = rows[0].find_all(["td", "th"], recursive=False)
        headers = [clean_text(c).lower() for c in header_cells]
        if "name" in headers and "type" in headers and "base power" in headers:
            target_table = table
            break

    if target_table is None:
        raise RuntimeError("Could not locate moves table on moves.shtml")

    moves: list[dict[str, Any]] = []
    rows = target_table.find_all("tr", recursive=False)[1:]

    for row in rows:
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 7:
            continue

        name_cell, type_cell, cat_cell, pp_cell, power_cell, acc_cell, effect_cell = cells[:7]

        name = clean_text(name_cell)
        if not name:
            continue

        anchor = name_cell.find("a")
        href = anchor.get("href") if anchor else None

        type_img = type_cell.find("img")
        move_type = extract_type_from_img(type_img.get("src", "") if type_img else "")

        cat_img = cat_cell.find("img")
        category = extract_category_from_img(cat_img.get("src", "") if cat_img else "")

        pp = parse_number(clean_text(pp_cell))
        power_text = clean_text(power_cell)
        power = parse_number(power_text)
        if category == "status":
            power = None

        accuracy = _parse_accuracy(clean_text(acc_cell))
        effect = clean_text(effect_cell) or None

        moves.append(
            {
                "slug": slug_from_href(href) or name.lower().replace(" ", "-"),
                "name": name,
                "type": move_type,
                "category": category,
                "power": power,
                "accuracy": accuracy,
                "pp": pp,
                "effect": effect,
                "url": absolute_url(href),
                "speed_priority": None,
            }
        )

    moves.sort(key=lambda m: m["name"].lower())

    missing = 0
    for i, move in enumerate(moves):
        detail_url = move.get("url")
        if not detail_url:
            missing += 1
            continue
        try:
            html = fetch_html(detail_url)
            pri = _extract_speed_priority_from_soup(make_soup(html))
            move["speed_priority"] = pri
            if pri is None:
                missing += 1
        except Exception:
            missing += 1
        if i < len(moves) - 1:
            polite_sleep(detail_sleep)

    if missing:
        print(f"   warning: {missing} moves missing speed_priority after detail scrape", flush=True)

    return moves
