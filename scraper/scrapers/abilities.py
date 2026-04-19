"""Scrape abilities (new abilities and mega-granted abilities) from Serebii."""
from __future__ import annotations

from typing import Any

from ._utils import (
    absolute_url,
    clean_text,
    fetch_html,
    make_soup,
    slug_from_href,
)

NEW_ABILITIES_URL = "https://www.serebii.net/pokemonchampions/newabilities.shtml"
MEGA_ABILITIES_URL = "https://www.serebii.net/pokemonchampions/megaabilities.shtml"


def _scrape_new_abilities(url: str = NEW_ABILITIES_URL) -> list[dict[str, Any]]:
    html = fetch_html(url)
    soup = make_soup(html)

    target = None
    for table in soup.find_all("table", class_="tab"):
        rows = table.find_all("tr", recursive=False)
        if not rows:
            continue
        hdr = [clean_text(c).lower() for c in rows[0].find_all(["td", "th"], recursive=False)]
        if "name" in hdr and "effect" in hdr:
            target = table
            break

    if target is None:
        return []

    abilities: list[dict[str, Any]] = []
    for row in target.find_all("tr", recursive=False)[1:]:
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 2:
            continue

        name_cell, effect_cell = cells[0], cells[1]
        anchor = name_cell.find("a")
        href = anchor.get("href") if anchor else None
        name = clean_text(name_cell)
        if not name:
            continue

        abilities.append(
            {
                "slug": slug_from_href(href) or name.lower().replace(" ", ""),
                "name": name,
                "effect": clean_text(effect_cell) or None,
                "new_in_champions": True,
                "url": absolute_url(href),
            }
        )

    return abilities


def _scrape_mega_abilities(url: str = MEGA_ABILITIES_URL) -> list[dict[str, Any]]:
    """Mega-ability table lists the Pokémon that gain a given ability upon Mega Evolving."""
    html = fetch_html(url)
    soup = make_soup(html)

    target = None
    for table in soup.find_all("table", class_="tab"):
        rows = table.find_all("tr", recursive=False)
        if len(rows) < 3:
            continue
        hdr = [clean_text(c).lower() for c in rows[0].find_all(["td", "th"], recursive=False)]
        if "no." in hdr and "name" in hdr and "abilities" in hdr:
            target = table
            break

    if target is None:
        return []

    entries: list[dict[str, Any]] = []
    for row in target.find_all("tr", recursive=False)[1:]:
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 5:
            continue

        no_cell, _pic_cell, name_cell, type_cell, abilities_cell = cells[:5]

        name = clean_text(name_cell)
        if not name:
            continue

        dex = clean_text(no_cell).lstrip("#") or None

        pokemon_anchor = name_cell.find("a")
        pokemon_href = pokemon_anchor.get("href") if pokemon_anchor else None

        type_slugs: list[str] = []
        for img in type_cell.find_all("img"):
            src = img.get("src", "")
            if "/type/" in src and src.endswith(".gif"):
                slug = src.rsplit("/", 1)[-1].replace(".gif", "").lower()
                if slug:
                    type_slugs.append(slug)

        ability_links: list[dict[str, Any]] = []
        for a in abilities_cell.find_all("a"):
            ability_name = clean_text(a)
            if not ability_name:
                continue
            ability_links.append(
                {
                    "slug": slug_from_href(a.get("href")),
                    "name": ability_name,
                    "url": absolute_url(a.get("href")),
                }
            )

        if not ability_links:
            # Fallback to plain text if no links.
            text = clean_text(abilities_cell)
            if text:
                ability_links.append({"slug": None, "name": text, "url": None})

        entries.append(
            {
                "national_dex": int(dex) if dex and dex.isdigit() else None,
                "pokemon": name,
                "pokemon_slug": slug_from_href(pokemon_href),
                "types": type_slugs or None,
                "abilities": ability_links,
            }
        )

    return entries


def scrape_abilities() -> dict[str, Any]:
    """Returns both Champions-exclusive new abilities and the mega->ability mapping."""
    return {
        "new_abilities": _scrape_new_abilities(),
        "mega_abilities": _scrape_mega_abilities(),
    }
