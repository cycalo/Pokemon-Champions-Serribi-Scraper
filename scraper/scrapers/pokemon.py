"""Scrape the Pokemon Champions pokedex listing plus each Pokémon's detail page."""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urljoin

from bs4 import Tag

from ._utils import (
    BASE_URL,
    absolute_url,
    clean_text,
    fetch_html,
    make_soup,
    parse_number,
    polite_sleep,
    slug_from_href,
)

LIST_URL = "https://www.serebii.net/pokemonchampions/pokemon.shtml"

STAT_KEYS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]

TYPE_COLUMN_ORDER = [
    "normal", "fire", "water", "electric", "grass", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "dark", "steel", "fairy",
]


def _extract_types_from_cell(cell: Optional[Tag]) -> list[str]:
    if cell is None:
        return []
    types: list[str] = []
    for img in cell.find_all("img"):
        src = img.get("src", "")
        m = re.search(r"/type/([a-zA-Z]+)\.gif", src)
        if m:
            t = m.group(1).lower()
            if t not in types and t not in {"physical", "special", "other"}:
                types.append(t)
    return types


def scrape_pokemon_list(url: str = LIST_URL) -> list[dict[str, Any]]:
    """Return compact list of every Pokémon listed on the Champions dex page.

    Each entry is either a base-form Pokémon (e.g. Venusaur) or a Mega form
    sharing the same national dex number/slug. Full details come from the
    per-Pokémon page.
    """
    html = fetch_html(url)
    soup = make_soup(html)

    target = None
    for table in soup.find_all("table", class_="tab"):
        rows = table.find_all("tr", recursive=False)
        if len(rows) < 10:
            continue
        hdr = [clean_text(c).lower() for c in rows[0].find_all(["td", "th"], recursive=False)]
        if "no." in hdr and "name" in hdr and "type" in hdr:
            target = table
            break

    if target is None:
        raise RuntimeError("Could not locate Pokémon listing table on pokemon.shtml")

    entries: list[dict[str, Any]] = []
    for row in target.find_all("tr", recursive=False)[1:]:
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 4:
            continue

        no_cell, pic_cell, name_cell, type_cell = cells[:4]

        name = clean_text(name_cell)
        if not name:
            continue

        dex_raw = clean_text(no_cell).lstrip("#")
        dex = int(dex_raw) if dex_raw.isdigit() else None

        anchor = name_cell.find("a")
        href = anchor.get("href") if anchor else None

        sprite_img = pic_cell.find("img")
        sprite = absolute_url(sprite_img.get("src")) if sprite_img else None

        types = _extract_types_from_cell(type_cell)

        entries.append(
            {
                "national_dex": dex,
                "name": name,
                "slug": slug_from_href(href),
                "page_url": absolute_url(href),
                "types": types,
                "sprite": sprite,
                "is_mega": name.lower().startswith("mega "),
            }
        )

    return entries


def _parse_name_table(table: Tag) -> dict[str, Any]:
    """Parse the 'Name / Other Names / No. / Gender Ratio / Type' info block."""
    info: dict[str, Any] = {}
    rows = table.find_all("tr", recursive=False)
    if not rows:
        return info

    # Row 0 has header labels like ["Name", "Other Names", "No.", "Gender Ratio", "Type"].
    labels: list[str] = []
    for cell in rows[0].find_all(["td", "th"], recursive=False):
        labels.append(clean_text(cell).lower())

    if len(rows) >= 2:
        value_cells = rows[1].find_all(["td", "th"], recursive=False)
        for label, cell in zip(labels, value_cells):
            if label == "name":
                info["name"] = clean_text(cell)
            elif label == "no.":
                txt = clean_text(cell)
                m = re.search(r"#(\d+)", txt)
                info["national_dex"] = int(m.group(1)) if m else None
            elif label == "type":
                info["types"] = _extract_types_from_cell(cell)
            elif label == "gender ratio":
                info["gender_ratio"] = clean_text(cell) or None
            elif label == "other names":
                info["other_names"] = clean_text(cell) or None

    if len(rows) >= 4:
        labels2 = [clean_text(c).lower() for c in rows[2].find_all(["td", "th"], recursive=False)]
        values2 = rows[3].find_all(["td", "th"], recursive=False)
        for label, cell in zip(labels2, values2):
            if label == "classification":
                info["classification"] = clean_text(cell) or None
            elif label == "height":
                info["height"] = clean_text(cell) or None
            elif label == "weight":
                info["weight"] = clean_text(cell) or None
            elif label == "capture rate":
                info["capture_rate"] = clean_text(cell) or None

    return info


def _parse_abilities_table(table: Tag) -> list[dict[str, Any]]:
    """Parse the abilities dextable. Returns list of {slug, name, description}."""
    abilities: list[dict[str, Any]] = []
    rows = table.find_all("tr", recursive=False)
    if len(rows) < 1:
        return abilities

    # First cell: 'Abilities : A - B - C' with <a> per ability.
    first_cells = rows[0].find_all(["td", "th"], recursive=False)
    if not first_cells:
        return abilities
    ability_links = first_cells[0].find_all("a")

    for link in ability_links:
        abilities.append(
            {
                "slug": slug_from_href(link.get("href")),
                "name": clean_text(link),
                "url": absolute_url(link.get("href")),
                "description": None,
            }
        )

    # Row 2 has: "<b>Ability</b> : description" for each one.
    if len(rows) >= 2:
        info_cells = rows[1].find_all(["td", "th"], recursive=False)
        if info_cells:
            descriptions_text = info_cells[0].get_text("\n", strip=False)
            # Split by ability name occurrences to capture each description.
            for ab in abilities:
                name = ab["name"]
                pattern = rf"{re.escape(name)}\s*:\s*(.*?)(?=(?:\n{{0,2}}[A-Z][A-Za-z \-']*\s*:\s)|\Z)"
                m = re.search(pattern, descriptions_text, flags=re.DOTALL)
                if m:
                    desc = " ".join(m.group(1).split())
                    ab["description"] = desc or None
    return abilities


def _parse_weakness_table(table: Tag) -> Optional[dict[str, float]]:
    """Parse the 18-column type-effectiveness table."""
    rows = table.find_all("tr", recursive=False)
    if len(rows) < 3:
        return None

    # Row 1: type icons, row 2: multipliers (*1, *2, *0.5, etc.)
    icon_cells = rows[1].find_all(["td", "th"], recursive=False)
    value_cells = rows[2].find_all(["td", "th"], recursive=False)
    if not icon_cells or not value_cells:
        return None

    types_order: list[str] = []
    for c in icon_cells:
        img = c.find("img")
        if img and img.get("src"):
            m = re.search(r"/type/(?:icon/)?([a-zA-Z]+)\.(?:gif|png)", img["src"])
            if m:
                types_order.append(m.group(1).lower())
                continue
        types_order.append("")

    result: dict[str, float] = {}
    for type_name, cell in zip(types_order, value_cells):
        if not type_name:
            continue
        txt = clean_text(cell).replace("*", "").strip()
        if not txt:
            continue
        try:
            result[type_name] = float(txt)
        except ValueError:
            continue

    return result or None


def _parse_stats_table(table: Tag) -> Optional[dict[str, Any]]:
    """Parse the 'Stats' dextable including base stats and max-level ranges."""
    rows = table.find_all("tr", recursive=False)
    # Expect: caption row, stat label row (HP/Atk/...), base stat row, then up to 3 max-stat rows.
    if len(rows) < 3:
        return None

    # Find the row containing stat labels.
    label_row = None
    base_row = None
    max_rows: list[Tag] = []
    for row in rows:
        cells = row.find_all(["td", "th"], recursive=False)
        cell_texts = [clean_text(c) for c in cells]
        lowered = [t.lower() for t in cell_texts]
        if "hp" in lowered and "attack" in lowered and label_row is None:
            label_row = row
            continue
        if label_row is not None and base_row is None and cells and "base stats" in cell_texts[0].lower():
            base_row = row
            continue
        if label_row is not None and base_row is not None and cells and "max stats" in cell_texts[0].lower():
            max_rows.append(row)

    if label_row is None or base_row is None:
        return None

    label_cells = [clean_text(c).lower() for c in label_row.find_all(["td", "th"], recursive=False)]
    base_cells = [clean_text(c) for c in base_row.find_all(["td", "th"], recursive=False)]

    # label_cells typically starts with an empty cell before HP. Align by matching known labels.
    label_to_key = {
        "hp": "hp",
        "attack": "attack",
        "defense": "defense",
        "sp. attack": "sp_attack",
        "sp. defense": "sp_defense",
        "speed": "speed",
    }

    base_stats: dict[str, Optional[int]] = {k: None for k in STAT_KEYS}
    for label, value in zip(label_cells, base_cells):
        key = label_to_key.get(label)
        if key is not None:
            base_stats[key] = parse_number(value)

    total_text = base_cells[0] if base_cells else ""
    total_match = re.search(r"Total:\s*(\d+)", total_text)
    total = int(total_match.group(1)) if total_match else (
        sum(v for v in base_stats.values() if v is not None) or None
    )

    max_stats: dict[str, dict[str, Optional[str]]] = {}
    for mrow in max_rows:
        cells = [clean_text(c) for c in mrow.find_all(["td", "th"], recursive=False)]
        if not cells:
            continue
        label = cells[0]
        nature_key = "hindering"
        if "neutral" in label.lower():
            nature_key = "neutral"
        elif "beneficial" in label.lower():
            nature_key = "beneficial"

        # Values may start at index 1 or 2 depending on whether there's a "Standard" column.
        offset = 1
        if len(cells) > 7 and cells[1].lower() == "standard":
            offset = 2

        entry: dict[str, Optional[str]] = {}
        for i, key in enumerate(STAT_KEYS):
            if offset + i < len(cells):
                entry[key] = cells[offset + i] or None
        max_stats[nature_key] = entry

    return {
        "base": base_stats,
        "total": total,
        "max_at_level_100": max_stats or None,
    }


KNOWN_SECTION_HEADS = {
    "standard moves",
    "evolutionary chain",
    "gender differences",
    "alternate forms",
    "picture",
    "name",
    "stats",
    "other names",
    "no.",
    "gender ratio",
    "type",
    "abilities",
    "classification",
    "height",
    "weight",
    "capture rate",
}


def _is_form_caption(table: Tag) -> Optional[str]:
    """Return the form title if this dextable is a form-separator (e.g. 'Mega Venusaur')."""
    rows = table.find_all("tr", recursive=False)
    if not rows:
        return None

    first_row_cells = rows[0].find_all(["td", "th"], recursive=False)
    if not first_row_cells:
        return None

    first_cell = first_row_cells[0]
    if "fooevo" not in (first_cell.get("class") or []):
        return None
    if len(first_row_cells) != 1:
        return None

    title = clean_text(first_cell)
    if not title or title.lower() in KNOWN_SECTION_HEADS or title.lower().startswith("stats"):
        return None
    if len(rows) > 1:
        # A form-caption table may contain the form banner + picture. Other tables
        # with useful content have labelled columns; if subsequent rows contain
        # tabular info (multiple cells per row), skip classifying as caption.
        for other in rows[1:]:
            cells = other.find_all(["td", "th"], recursive=False)
            if len(cells) > 1:
                return None

    return title


def _classify_dextable(table: Tag) -> str:
    """Label a dextable by what content it holds."""
    heads = [clean_text(h) for h in table.find_all("td", class_="fooevo", recursive=True)]
    first_head = heads[0] if heads else ""
    head_low = first_head.lower()

    if head_low == "picture":
        return "picture"
    if head_low.startswith("stats"):
        return "stats"
    if head_low.startswith("standard moves"):
        return "moves"
    if head_low == "evolutionary chain":
        return "evolution"
    if head_low == "gender differences":
        return "gender_differences"
    if head_low == "alternate forms":
        return "alternate_forms"

    # Name info block
    rows = table.find_all("tr", recursive=False)
    if rows:
        hdr = [clean_text(c).lower() for c in rows[0].find_all(["td", "th"], recursive=False)]
        if "name" in hdr and any(h in hdr for h in ("no.", "type")):
            return "name"

    # Abilities / Weakness look similar (fooleft td). Use text content.
    text = table.get_text(" ", strip=True).lower()
    if text.startswith("abilities"):
        return "abilities"
    if text.startswith("weakness"):
        return "weakness"

    # Form caption table (single cell with form name).
    if _is_form_caption(table):
        return "form_caption"

    return "unknown"


def _parse_moves_table(table: Tag) -> list[dict[str, Any]]:
    """Parse the big Standard Moves table for a Pokémon.

    Each move spans two rows: an info row (name/type/cat/power/acc/pp/effect%) then
    a full-width effect row.
    """
    rows = table.find_all("tr", recursive=False)
    if len(rows) < 3:
        return []

    moves: list[dict[str, Any]] = []
    i = 0
    while i < len(rows):
        cells = rows[i].find_all(["td", "th"], recursive=False)
        if len(cells) == 7 and clean_text(cells[0]).lower() != "attack name":
            name = clean_text(cells[0])
            if name:
                anchor = cells[0].find("a")
                href = anchor.get("href") if anchor else None

                type_img = cells[1].find("img")
                move_type = None
                if type_img and type_img.get("src"):
                    m = re.search(r"/type/([a-zA-Z]+)\.gif", type_img["src"])
                    if m:
                        move_type = m.group(1).lower()

                cat_img = cells[2].find("img")
                category = None
                if cat_img and cat_img.get("src"):
                    m = re.search(r"/type/(physical|special|other)\.png", cat_img["src"])
                    if m:
                        raw = m.group(1).lower()
                        category = "status" if raw == "other" else raw

                power = parse_number(clean_text(cells[3]))
                if category == "status":
                    power = None

                acc_text = clean_text(cells[4])
                accuracy: Optional[int] = None
                if acc_text and acc_text != "--":
                    try:
                        acc_val = int(acc_text)
                        accuracy = None if acc_val >= 101 else acc_val
                    except ValueError:
                        accuracy = None

                pp = parse_number(clean_text(cells[5]))
                effect_pct_text = clean_text(cells[6])
                effect_pct: Optional[int] = None
                if effect_pct_text and effect_pct_text not in {"--", "-"}:
                    effect_pct = parse_number(effect_pct_text)

                # Look for effect description on the next row.
                description: Optional[str] = None
                if i + 1 < len(rows):
                    next_cells = rows[i + 1].find_all(["td", "th"], recursive=False)
                    if len(next_cells) == 1:
                        description = clean_text(next_cells[0]) or None

                moves.append(
                    {
                        "slug": slug_from_href(href),
                        "name": name,
                        "type": move_type,
                        "category": category,
                        "power": power,
                        "accuracy": accuracy,
                        "pp": pp,
                        "effect_chance": effect_pct,
                        "description": description,
                        "url": absolute_url(href),
                    }
                )
                i += 2
                continue
        i += 1

    return moves


def _split_into_forms(tables: list[Tag]) -> list[tuple[Optional[str], list[Tag]]]:
    """Split the dextables into (form_title or None, tables) groups.

    The first group covers the base Pokémon (title=None). Any subsequent group
    starts at a form-caption table like 'Mega Venusaur'.
    """
    groups: list[tuple[Optional[str], list[Tag]]] = [(None, [])]
    for table in tables:
        form_title = _is_form_caption(table)
        if form_title:
            groups.append((form_title, []))
        else:
            groups[-1][1].append(table)
    # Strip empty groups.
    return [g for g in groups if g[1]]


def _form_from_group(title: Optional[str], tables: list[Tag]) -> dict[str, Any]:
    form: dict[str, Any] = {
        "name": title,
        "types": [],
        "abilities": [],
        "stats": None,
        "type_effectiveness": None,
        "info": {},
    }

    for table in tables:
        kind = _classify_dextable(table)
        if kind == "name":
            info = _parse_name_table(table)
            if not form["name"] and info.get("name"):
                form["name"] = info["name"]
            if info.get("types"):
                form["types"] = info["types"]
            # Merge selected info fields
            for key in ("classification", "height", "weight", "gender_ratio",
                         "other_names", "national_dex", "capture_rate"):
                if info.get(key) is not None:
                    form["info"][key] = info[key]
        elif kind == "abilities":
            form["abilities"] = _parse_abilities_table(table)
        elif kind == "weakness":
            form["type_effectiveness"] = _parse_weakness_table(table)
        elif kind == "stats":
            form["stats"] = _parse_stats_table(table)

    return form


def scrape_pokemon_details(slug: str, page_url: str) -> Optional[dict[str, Any]]:
    """Scrape a single Pokémon page: base info + every form + full learnset."""
    html = fetch_html(page_url)
    soup = make_soup(html)

    dextables = soup.find_all("table", class_="dextable")
    if not dextables:
        return None

    groups = _split_into_forms(dextables)
    if not groups:
        return None

    forms: list[dict[str, Any]] = []
    moves: list[dict[str, Any]] = []

    for title, tables in groups:
        form = _form_from_group(title, tables)
        if form.get("name") or form.get("types") or form.get("stats"):
            forms.append(form)
        # The learnset lives in the base form group only.
        for table in tables:
            if _classify_dextable(table) == "moves":
                moves = _parse_moves_table(table)

    if not forms:
        return None

    base = forms[0]
    base_info = base.get("info", {})

    return {
        "slug": slug,
        "name": base.get("name"),
        "national_dex": base_info.get("national_dex"),
        "types": base.get("types"),
        "abilities": base.get("abilities"),
        "stats": base.get("stats"),
        "type_effectiveness": base.get("type_effectiveness"),
        "classification": base_info.get("classification"),
        "height": base_info.get("height"),
        "weight": base_info.get("weight"),
        "gender_ratio": base_info.get("gender_ratio"),
        "other_names": base_info.get("other_names"),
        "forms": [
            {
                "name": f.get("name"),
                "types": f.get("types"),
                "abilities": f.get("abilities"),
                "stats": f.get("stats"),
                "type_effectiveness": f.get("type_effectiveness"),
                "classification": f.get("info", {}).get("classification"),
                "height": f.get("info", {}).get("height"),
                "weight": f.get("info", {}).get("weight"),
            }
            for f in forms[1:]
        ],
        "moves": moves,
        "page_url": page_url,
    }


def scrape_pokemon(*, sleep_between: float = 0.5, limit: Optional[int] = None) -> dict[str, Any]:
    """Full Pokémon scrape: fetch the listing, then every Pokémon's detail page.

    Returns a dict with two keys: `pokedex` (detailed per-slug data) and
    `listing` (the raw listing including every mega row from the dex page).
    """
    listing = scrape_pokemon_list()

    # Group listing entries by slug so we only fetch each detail page once.
    seen_slugs: dict[str, dict[str, Any]] = {}
    for entry in listing:
        slug = entry.get("slug")
        if not slug:
            continue
        if slug not in seen_slugs:
            seen_slugs[slug] = entry

    slugs = list(seen_slugs.keys())
    if limit is not None:
        slugs = slugs[:limit]

    pokedex: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for index, slug in enumerate(slugs):
        entry = seen_slugs[slug]
        page_url = entry["page_url"]
        if not page_url:
            continue

        print(f"[pokemon] ({index + 1}/{len(slugs)}) {slug}", flush=True)

        try:
            details = scrape_pokemon_details(slug, page_url)
            if details is None:
                failures.append({"slug": slug, "url": page_url, "reason": "no dextables"})
                continue

            details["sprite"] = entry.get("sprite")
            pokedex.append(details)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[pokemon]   failed: {exc}", flush=True)
            failures.append({"slug": slug, "url": page_url, "reason": str(exc)})

        if index < len(slugs) - 1:
            polite_sleep(sleep_between)

    pokedex.sort(key=lambda p: (p.get("national_dex") or 9999, p.get("slug") or ""))

    return {
        "pokedex": pokedex,
        "listing": listing,
        "failures": failures,
    }
