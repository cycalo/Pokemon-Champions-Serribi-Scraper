"""Download sprite/icon assets (Pokémon, types, move categories, items) locally.

The downloader is **idempotent**: any image already present on disk is skipped,
so re-runs only fetch what's new. Each download sleeps for a small amount of
time to stay polite, but far less than the 1.5–2s detail-page throttle because
these are static assets.

All assets land under the repo-root ``images/`` directory with a stable,
human-readable layout documented in the README. A manifest is written to
``data/images.json`` and every public-facing JSON (``pokemon.json``,
``pokemon_listing.json``, ``items.json``) gains a ``sprite_path`` field
pointing at the local asset.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import requests

from ._utils import DEFAULT_HEADERS, absolute_url

BASE_URL = "https://www.serebii.net"


# All 18 Pokémon types — drives the type-icon and move-category downloads.
TYPE_NAMES = [
    "normal", "fire", "water", "electric", "grass", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "dark", "steel", "fairy",
]

MOVE_CATEGORY_URLS = {
    # local-filename -> remote-filename (Serebii calls "status" moves "other").
    "physical": "physical.png",
    "special": "special.png",
    "status": "other.png",
}


def _session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(DEFAULT_HEADERS)
    return sess


def _polite_image_sleep(base: float, jitter: float = 0.15) -> None:
    if base <= 0:
        return
    time.sleep(base + random.uniform(0, max(0.0, jitter)))


def _download(
    session: requests.Session,
    url: str,
    target: Path,
    *,
    force: bool,
    sleep_between: float,
) -> dict[str, Any]:
    """Download a single image. Returns a status dict."""
    status: dict[str, Any] = {"url": url, "path": str(target), "status": "skipped"}
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and target.stat().st_size > 0 and not force:
        return status

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 404:
            status["status"] = "missing"
            return status
        resp.raise_for_status()
        target.write_bytes(resp.content)
        status["status"] = "downloaded"
        status["bytes"] = len(resp.content)
    except requests.RequestException as exc:  # pragma: no cover - defensive
        status["status"] = "failed"
        status["error"] = str(exc)
    finally:
        # Only sleep if we actually hit the network.
        if status["status"] in {"downloaded", "failed", "missing"}:
            _polite_image_sleep(sleep_between)

    return status


def _download_batch(
    session: requests.Session,
    items: Iterable[tuple[str, Path]],
    *,
    force: bool,
    sleep_between: float,
    label: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    items_list = list(items)
    total = len(items_list)
    for index, (url, target) in enumerate(items_list):
        info = _download(session, url, target, force=force, sleep_between=sleep_between)
        info["label"] = label
        results.append(info)
        if info["status"] == "downloaded":
            print(f"[images/{label}] ({index + 1}/{total}) + {target.name}", flush=True)
        elif info["status"] == "missing":
            print(f"[images/{label}] ({index + 1}/{total}) 404 {url}", flush=True)
        elif info["status"] == "failed":
            print(f"[images/{label}] ({index + 1}/{total}) FAIL {url}: {info.get('error')}", flush=True)
    return results


def _pokemon_targets(
    listing: list[dict[str, Any]], images_root: Path
) -> list[tuple[str, Path]]:
    """Collect (url, local_path) tuples for every Pokémon sprite.

    The listing has one entry per form, so every Mega and regional variant is
    represented. Filenames preserve Serebii's convention (``003.png``,
    ``003-m.png``, ``006-mx.png`` …).
    """
    targets: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for entry in listing:
        sprite = entry.get("sprite")
        if not sprite:
            continue
        filename = Path(urlparse(sprite).path).name
        if not filename:
            continue
        target = images_root / "pokemon" / filename
        if target in seen:
            continue
        seen.add(target)
        targets.append((sprite, target))
    return targets


def _type_targets(images_root: Path) -> list[tuple[str, Path]]:
    """Type icons come in two flavours; grab both."""
    targets: list[tuple[str, Path]] = []
    for name in TYPE_NAMES:
        # Inline GIF (used in dex tables and move list).
        targets.append(
            (
                f"{BASE_URL}/pokedex-bw/type/{name}.gif",
                images_root / "types" / f"{name}.gif",
            )
        )
        # SV-style PNG (used in weakness table).
        targets.append(
            (
                f"{BASE_URL}/pokedex-sv/type/icon/{name}.png",
                images_root / "types" / "icons" / f"{name}.png",
            )
        )
    return targets


def _move_category_targets(images_root: Path) -> list[tuple[str, Path]]:
    targets: list[tuple[str, Path]] = []
    for local_name, remote_name in MOVE_CATEGORY_URLS.items():
        targets.append(
            (
                f"{BASE_URL}/pokedex-bw/type/{remote_name}",
                images_root / "move-categories" / f"{local_name}.png",
            )
        )
    return targets


def _item_targets(
    items: list[dict[str, Any]], images_root: Path
) -> list[tuple[str, Path]]:
    targets: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for item in items:
        sprite = item.get("sprite")
        slug = item.get("slug")
        if not sprite or not slug:
            continue
        filename = Path(urlparse(sprite).path).name or f"{slug}.png"
        suffix = Path(filename).suffix or ".png"
        target = images_root / "items" / f"{slug}{suffix}"
        if target in seen:
            continue
        seen.add(target)
        targets.append((sprite, target))
    return targets


def _relpath(target: Path, repo_root: Path) -> str:
    """Stable POSIX-style path relative to the repo root (for Flutter asset paths)."""
    return target.resolve().relative_to(repo_root.resolve()).as_posix()


def download_images(
    *,
    repo_root: Path,
    pokemon_listing: list[dict[str, Any]],
    items: list[dict[str, Any]],
    sleep_between: float = 0.25,
    force: bool = False,
) -> dict[str, Any]:
    """Download every supported image asset.

    Returns a manifest keyed by asset kind. Missing/failed downloads are kept
    in the manifest so callers can inspect what didn't make it.
    """
    images_root = repo_root / "images"
    images_root.mkdir(parents=True, exist_ok=True)

    session = _session()

    pokemon_items = _pokemon_targets(pokemon_listing, images_root)
    type_items = _type_targets(images_root)
    category_items = _move_category_targets(images_root)
    item_images = _item_targets(items, images_root)

    manifest: dict[str, Any] = {
        "pokemon": [],
        "types": [],
        "move_categories": [],
        "items": [],
    }

    # --- Pokémon ----------------------------------------------------------------
    results = _download_batch(
        session, pokemon_items, force=force, sleep_between=sleep_between, label="pokemon"
    )
    # Build slug -> list of sprite paths.
    # We need to know which listing row each path came from so we pair them up.
    pokemon_manifest: list[dict[str, Any]] = []
    # Map URL -> status for quick lookup.
    url_status = {r["url"]: r for r in results}
    for entry in pokemon_listing:
        sprite = entry.get("sprite")
        if not sprite:
            continue
        target = images_root / "pokemon" / Path(urlparse(sprite).path).name
        status = url_status.get(sprite, {}).get("status", "skipped")
        pokemon_manifest.append(
            {
                "slug": entry.get("slug"),
                "name": entry.get("name"),
                "national_dex": entry.get("national_dex"),
                "is_mega": entry.get("is_mega"),
                "source_url": sprite,
                "sprite_path": _relpath(target, repo_root) if target.exists() else None,
                "status": status,
            }
        )
    manifest["pokemon"] = pokemon_manifest

    # --- Types ------------------------------------------------------------------
    results = _download_batch(
        session, type_items, force=force, sleep_between=sleep_between, label="types"
    )
    for name in TYPE_NAMES:
        gif_path = images_root / "types" / f"{name}.gif"
        icon_path = images_root / "types" / "icons" / f"{name}.png"
        manifest["types"].append(
            {
                "type": name,
                "gif_path": _relpath(gif_path, repo_root) if gif_path.exists() else None,
                "icon_path": _relpath(icon_path, repo_root) if icon_path.exists() else None,
            }
        )

    # --- Move categories --------------------------------------------------------
    results = _download_batch(
        session,
        category_items,
        force=force,
        sleep_between=sleep_between,
        label="move-categories",
    )
    for local_name in MOVE_CATEGORY_URLS:
        path = images_root / "move-categories" / f"{local_name}.png"
        manifest["move_categories"].append(
            {
                "category": local_name,
                "sprite_path": _relpath(path, repo_root) if path.exists() else None,
            }
        )

    # --- Items ------------------------------------------------------------------
    results = _download_batch(
        session, item_images, force=force, sleep_between=sleep_between, label="items"
    )
    url_status = {r["url"]: r for r in results}
    for item in items:
        sprite = item.get("sprite")
        slug = item.get("slug")
        if not sprite or not slug:
            continue
        filename = Path(urlparse(sprite).path).name or f"{slug}.png"
        suffix = Path(filename).suffix or ".png"
        target = images_root / "items" / f"{slug}{suffix}"
        status = url_status.get(sprite, {}).get("status", "skipped")
        manifest["items"].append(
            {
                "slug": slug,
                "name": item.get("name"),
                "source_url": sprite,
                "sprite_path": _relpath(target, repo_root) if target.exists() else None,
                "status": status,
            }
        )

    return manifest


def attach_sprite_paths(
    *,
    repo_root: Path,
    pokemon_file: Path,
    pokemon_listing_file: Path,
    items_file: Path,
    manifest: dict[str, Any],
) -> None:
    """Inject ``sprite_path`` fields into the existing JSON files based on the manifest.

    Matching rules:
    - ``pokemon_listing.json`` entries are keyed on the remote sprite URL (always
      unique, so X/Y Mega Charizard rows stay distinct).
    - ``pokemon.json`` entries have their base sprite picked from the first
      non-Mega listing row for that slug; each ``forms[]`` entry is assigned the
      next Mega/alt-form sprite in listing order. This matches Serebii's own
      rendering order on both the listing and the detail page (Charizard → X → Y).
    - ``items.json`` entries are matched by slug.
    """

    # Listing sprite-url -> local path.
    url_to_local: dict[str, str] = {}
    for entry in manifest.get("pokemon", []):
        src = entry.get("source_url")
        local = entry.get("sprite_path")
        if src and local:
            url_to_local[src] = local

    # Group manifest entries by slug, preserving insertion order so "first
    # non-mega" and "mega in order" semantics hold.
    by_slug: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest.get("pokemon", []):
        slug = entry.get("slug")
        if not slug:
            continue
        by_slug.setdefault(slug, []).append(entry)

    base_for_slug: dict[str, Optional[str]] = {}
    forms_for_slug: dict[str, list[str]] = {}
    for slug, entries in by_slug.items():
        base_path: Optional[str] = None
        form_paths: list[str] = []
        for entry in entries:
            local = entry.get("sprite_path")
            if not local:
                continue
            if not entry.get("is_mega") and base_path is None:
                base_path = local
            else:
                form_paths.append(local)
        # Some Pokémon only have a Mega row (rare, but possible for future data).
        if base_path is None and form_paths:
            base_path = form_paths.pop(0)
        base_for_slug[slug] = base_path
        forms_for_slug[slug] = form_paths

    item_paths_by_slug: dict[str, str] = {
        entry["slug"]: entry["sprite_path"]
        for entry in manifest.get("items", [])
        if entry.get("slug") and entry.get("sprite_path")
    }

    # --- pokemon_listing.json -------------------------------------------------
    if pokemon_listing_file.exists():
        listing_blob = json.loads(pokemon_listing_file.read_text(encoding="utf-8"))
        for entry in listing_blob.get("entries", []):
            sprite = entry.get("sprite")
            if sprite and sprite in url_to_local:
                entry["sprite_path"] = url_to_local[sprite]
        pokemon_listing_file.write_text(
            json.dumps(listing_blob, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # --- pokemon.json ---------------------------------------------------------
    if pokemon_file.exists():
        pokemon_blob = json.loads(pokemon_file.read_text(encoding="utf-8"))
        for poke in pokemon_blob.get("pokemon", []):
            slug = poke.get("slug")
            if slug:
                base = base_for_slug.get(slug)
                if base:
                    poke["sprite_path"] = base
                for form, form_path in zip(poke.get("forms", []), forms_for_slug.get(slug, [])):
                    form["sprite_path"] = form_path
        pokemon_file.write_text(
            json.dumps(pokemon_blob, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # --- items.json -----------------------------------------------------------
    if items_file.exists():
        items_blob = json.loads(items_file.read_text(encoding="utf-8"))
        for item in items_blob.get("items", []):
            slug = item.get("slug")
            if slug and slug in item_paths_by_slug:
                item["sprite_path"] = item_paths_by_slug[slug]
        items_file.write_text(
            json.dumps(items_blob, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def summarize(manifest: dict[str, Any]) -> dict[str, Any]:
    """Compact counts summary for logging / CI output."""
    summary: dict[str, Any] = {}
    for kind, entries in manifest.items():
        total = len(entries)
        with_path = sum(1 for e in entries if e.get("sprite_path") or e.get("gif_path") or e.get("icon_path"))
        summary[kind] = {"total": total, "with_local_path": with_path}
    return summary
