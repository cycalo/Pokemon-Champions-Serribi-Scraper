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
    parse_stat_range_low,
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
    """Parse the Stats dextable for Pokémon Champions.

    In-game stats match the **low** end of each range on the **Max Stats /
    Neutral Nature** row (not the classic BST row). If that row is missing,
    fall back to the traditional Base Stats row.
    """
    rows = table.find_all("tr", recursive=False)
    if len(rows) < 3:
        return None

    label_row = None
    serebii_bst_row = None
    neutral_max_row = None
    for row in rows:
        cells = row.find_all(["td", "th"], recursive=False)
        cell_texts = [clean_text(c) for c in cells]
        lowered = [t.lower() for t in cell_texts]
        if "hp" in lowered and "attack" in lowered and label_row is None:
            label_row = row
            continue
        if label_row is not None and cells:
            c0 = cell_texts[0].lower()
            if serebii_bst_row is None and "base stats" in c0:
                serebii_bst_row = row
                continue
            if "max stats" in c0 and "neutral" in c0:
                neutral_max_row = row
                continue

    if label_row is None:
        return None

    label_to_key = {
        "hp": "hp",
        "attack": "attack",
        "defense": "defense",
        "sp. attack": "sp_attack",
        "sp. defense": "sp_defense",
        "speed": "speed",
    }

    base_stats: dict[str, Optional[int]] = {k: None for k in STAT_KEYS}

    if neutral_max_row is not None:
        cells = [clean_text(c) for c in neutral_max_row.find_all(["td", "th"], recursive=False)]
        offset = 2 if len(cells) > 7 and cells[1].lower() == "standard" else 1
        for i, key in enumerate(STAT_KEYS):
            if offset + i < len(cells):
                base_stats[key] = parse_stat_range_low(cells[offset + i])
    elif serebii_bst_row is not None:
        label_cells = [clean_text(c).lower() for c in label_row.find_all(["td", "th"], recursive=False)]
        bst_cells = [clean_text(c) for c in serebii_bst_row.find_all(["td", "th"], recursive=False)]
        for label, value in zip(label_cells, bst_cells):
            key = label_to_key.get(label)
            if key is not None:
                base_stats[key] = parse_number(value)
    else:
        return None

    total = sum(v for v in base_stats.values() if v is not None) or None

    return {
        "base": base_stats,
        "total": total,
    }


def _stats_variant_form_title(table: Tag) -> Optional[str]:
    """If this is a secondary stats block (e.g. 'Stats - Galarian Slowking'), return the subtitle."""
    for cell in table.find_all(["td", "th"], class_="fooevo", recursive=True):
        raw = clean_text(cell).strip()
        m = re.match(r"(?i)stats\s*-\s*(.+)", raw)
        if m:
            title = m.group(1).strip()
            # Serebii uses 'Stats - ' with nothing after for some Megas; do not start a new form group.
            return title or None
    return None


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


def _is_regional_form_standard_moves_table(table: Tag) -> bool:
    """Serebii uses headers like *Alola Form Standard Moves* / *Galarian Form Standard Moves* for regional learnsets.

    The plain *Standard Moves* table is the default species learnset; these regional tables are a separate
    dextable and must be classified as *moves* (not *unknown*).
    """
    heads = [clean_text(h) for h in table.find_all("td", class_="fooevo", recursive=True)]
    h0 = (heads[0] or "").lower() if heads else ""
    if h0 == "standard moves":
        return False
    if "standard moves" in h0 and "form" in h0:
        return True
    if "form standard moves" in h0:
        return True
    return False


def _is_plain_base_stats_dextable(table: Tag) -> bool:
    """True for the dextable headed exactly ``Stats`` (the default form), not ``Stats - Alolan *`` style."""
    for cell in table.find_all(["td", "th"], class_="fooevo", recursive=True):
        raw = clean_text(cell)
        if re.match(r"(?i)^stats\s*$", raw):
            return True
    return False


def _find_regional_learnset_split(
    dextables: list[Tag],
) -> Optional[tuple[int, int, int]]:
    """If the page has a regional *Form Standard Moves* block, return (r, b, a) indices in ``dextables``.

    Serebii interleaves: ... default learnset, regional learnset, **Stats** (default), **Stats - Regional**.
    The old parser kept regional moves in the first form group, wrongfully merging learnsets. We split the
    first group at ``r`` and pull the plain **Stats** row (``b``) into the default form only.
    """
    for r, table in enumerate(dextables):
        if not _is_regional_form_standard_moves_table(table):
            continue
        if r + 2 < len(dextables):
            t_stats = dextables[r + 1]
            t_regional = dextables[r + 2]
            if _is_plain_base_stats_dextable(t_stats) and _stats_variant_form_title(t_regional):
                return (r, r + 1, r + 2)
    return None


def _resplit_forms_for_regional_learnsets(
    dextables: list[Tag],
) -> list[tuple[Optional[str], list[Tag]]]:
    """Split the default form group when Serebii gives a second learnset (Alola / Galar, etc.) on the same page."""
    tri = _find_regional_learnset_split(dextables)
    if not tri:
        return _split_into_forms(dextables)
    r, b, a = tri
    variant_title = _stats_variant_form_title(dextables[a])
    kanto_tables = dextables[0:r] + [dextables[b]]
    regional_tables = [dextables[r], dextables[a]]
    tail = dextables[a + 1 :]
    groups: list[tuple[Optional[str], list[Tag]]] = [
        (None, kanto_tables),
        (variant_title, regional_tables),
    ]
    groups.extend(_split_into_forms(tail))
    return [g for g in groups if g[1]]


def _classify_dextable(table: Tag) -> str:
    """Label a dextable by what content it holds."""
    heads = [clean_text(h) for h in table.find_all("td", class_="fooevo", recursive=True)]
    first_head = heads[0] if heads else ""
    head_low = first_head.lower()

    if head_low == "picture":
        return "picture"
    if head_low.startswith("stats"):
        return "stats"
    if head_low.startswith("standard moves") or _is_regional_form_standard_moves_table(table):
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

    The first group covers the base Pokémon (title=None). A new group starts at
    a form-caption table (e.g. Mega) or at a ``Stats - <variant>`` dextable
    (e.g. Galarian Slowking on the same page as the standard form).
    """
    groups: list[tuple[Optional[str], list[Tag]]] = [(None, [])]
    for table in tables:
        form_title = _is_form_caption(table)
        if form_title:
            groups.append((form_title, []))
        elif _classify_dextable(table) == "stats":
            stats_variant = _stats_variant_form_title(table)
            if stats_variant:
                groups.append((stats_variant, []))
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


def _learnset_move_slugs_in_order(moves: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(m.get("slug") or "" for m in moves)


def _group_last_moves_table(
    title: Optional[str], tables: list[Tag]
) -> tuple[Optional[Tag], list[dict[str, Any]]]:
    """Return the last *Standard Moves* dextable in a form group and its parse (the effective learnset)."""
    move_tables: list[Tag] = [t for t in tables if _classify_dextable(t) == "moves"]
    if not move_tables:
        return None, []
    last = move_tables[-1]
    return last, _parse_moves_table(last)


def _is_mega_form_name(name: Optional[str]) -> bool:
    n = (name or "").lower().strip()
    return n.startswith("mega ")


def scrape_pokemon_details(slug: str, page_url: str) -> Optional[dict[str, Any]]:
    """Scrape a single Pokémon page: base info + every form + full learnset."""
    html = fetch_html(page_url)
    soup = make_soup(html)

    dextables = soup.find_all("table", class_="dextable")
    if not dextables:
        return None

    groups = _resplit_forms_for_regional_learnsets(dextables)
    if not groups:
        return None

    forms: list[dict[str, Any]] = []
    group_moves: list[list[dict[str, Any]]] = []
    for title, tables in groups:
        form = _form_from_group(title, tables)
        if form.get("name") or form.get("types") or form.get("stats"):
            forms.append(form)
            _, mlist = _group_last_moves_table(title, tables)
            group_moves.append(mlist)

    if not forms:
        return None

    base = forms[0]
    base_info = base.get("info", {})
    species_moves = group_moves[0] if group_moves else []

    form_entries: list[dict[str, Any]] = []
    for form_data, f_moves in zip(forms[1:], group_moves[1:]):
        entry: dict[str, Any] = {
            "name": form_data.get("name"),
            "types": form_data.get("types"),
            "abilities": form_data.get("abilities"),
            "stats": form_data.get("stats"),
            "type_effectiveness": form_data.get("type_effectiveness"),
            "classification": form_data.get("info", {}).get("classification"),
            "height": form_data.get("info", {}).get("height"),
            "weight": form_data.get("info", {}).get("weight"),
            "is_mega": _is_mega_form_name(form_data.get("name")),
        }
        if f_moves and _learnset_move_slugs_in_order(f_moves) != _learnset_move_slugs_in_order(
            species_moves
        ):
            entry["moves"] = f_moves
        form_entries.append(entry)

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
        "forms": form_entries,
        "moves": species_moves,
        "page_url": page_url,
    }


def scrape_pokemon(*, sleep_between: float = 1.5, limit: Optional[int] = None) -> dict[str, Any]:
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
