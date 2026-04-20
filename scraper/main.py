"""Entry point for the Pokemon Champions scraper.

Runs every individual scraper and writes the results to the repo's /data
folder as indented JSON files. Images (Pokémon sprites, type icons, move
category icons, and item sprites) live under /images and are managed by the
``images`` step.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `python scraper/main.py` work without installing as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapers import (  # noqa: E402
    attach_sprite_paths,
    download_images,
    scrape_abilities,
    scrape_items,
    scrape_moves,
    scrape_pokemon,
    summarize,
)
from scrapers._utils import write_json  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

VALID_STEPS = ("pokemon", "moves", "items", "abilities", "images")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(
    only: list[str] | None = None,
    pokemon_limit: int | None = None,
    pokemon_sleep: float = 1.5,
    image_sleep: float = 0.25,
    force_images: bool = False,
) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    only_set = set(only) if only else None

    def should_run(name: str) -> bool:
        return only_set is None or name in only_set

    if should_run("moves"):
        print("=> Scraping moves...", flush=True)
        moves = scrape_moves()
        write_json(
            DATA_DIR / "moves.json",
            {"scraped_at": _now(), "count": len(moves), "moves": moves},
        )
        print(f"   {len(moves)} moves written", flush=True)

    if should_run("items"):
        print("=> Scraping items...", flush=True)
        items = scrape_items()
        write_json(
            DATA_DIR / "items.json",
            {
                "scraped_at": _now(),
                "count": len(items["items"]),
                "categories": items["categories"],
                "items": items["items"],
            },
        )
        print(f"   {len(items['items'])} items written", flush=True)

    if should_run("abilities"):
        print("=> Scraping abilities...", flush=True)
        abilities = scrape_abilities()
        write_json(
            DATA_DIR / "abilities.json",
            {
                "scraped_at": _now(),
                "new_abilities": abilities["new_abilities"],
                "mega_abilities": abilities["mega_abilities"],
            },
        )
        print(
            f"   {len(abilities['new_abilities'])} new abilities, "
            f"{len(abilities['mega_abilities'])} mega entries written",
            flush=True,
        )

    if should_run("pokemon"):
        print("=> Scraping Pokémon...", flush=True)
        result = scrape_pokemon(sleep_between=pokemon_sleep, limit=pokemon_limit)
        write_json(
            DATA_DIR / "pokemon.json",
            {
                "scraped_at": _now(),
                "count": len(result["pokedex"]),
                "pokemon": result["pokedex"],
            },
        )
        write_json(
            DATA_DIR / "pokemon_listing.json",
            {
                "scraped_at": _now(),
                "count": len(result["listing"]),
                "entries": result["listing"],
            },
        )
        if result["failures"]:
            write_json(
                DATA_DIR / "pokemon_failures.json",
                {
                    "scraped_at": _now(),
                    "count": len(result["failures"]),
                    "failures": result["failures"],
                },
            )
        print(
            f"   {len(result['pokedex'])} Pokémon written "
            f"({len(result['failures'])} failed)",
            flush=True,
        )

    if should_run("images"):
        print("=> Downloading images...", flush=True)
        listing_file = DATA_DIR / "pokemon_listing.json"
        items_file = DATA_DIR / "items.json"
        if not listing_file.exists() or not items_file.exists():
            print(
                "   Skipping: pokemon_listing.json and items.json must exist. "
                "Run the pokemon and items steps first.",
                flush=True,
            )
        else:
            listing_blob = json.loads(listing_file.read_text(encoding="utf-8"))
            items_blob = json.loads(items_file.read_text(encoding="utf-8"))
            manifest = download_images(
                repo_root=REPO_ROOT,
                pokemon_listing=listing_blob.get("entries", []),
                items=items_blob.get("items", []),
                sleep_between=image_sleep,
                force=force_images,
            )

            summary = summarize(manifest)
            write_json(
                DATA_DIR / "images.json",
                {
                    "scraped_at": _now(),
                    "summary": summary,
                    "pokemon": manifest["pokemon"],
                    "types": manifest["types"],
                    "move_categories": manifest["move_categories"],
                    "items": manifest["items"],
                },
            )

            attach_sprite_paths(
                repo_root=REPO_ROOT,
                pokemon_file=DATA_DIR / "pokemon.json",
                pokemon_listing_file=listing_file,
                items_file=items_file,
                manifest=manifest,
            )

            parts = ", ".join(
                f"{kind}: {info['with_local_path']}/{info['total']}"
                for kind, info in summary.items()
            )
            print(f"   images ready ({parts})", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Pokemon Champions data from Serebii.")
    parser.add_argument(
        "--only",
        nargs="*",
        choices=list(VALID_STEPS),
        help="Restrict the run to a subset of steps.",
    )
    parser.add_argument(
        "--pokemon-limit",
        type=int,
        default=None,
        help="Limit the number of Pokémon detail pages fetched (useful for testing).",
    )
    parser.add_argument(
        "--pokemon-sleep",
        type=float,
        default=1.5,
        help=(
            "Base seconds to sleep between per-Pokémon page requests "
            "(default 1.5; up to ~0.5s of random jitter is added on top to "
            "stay roughly in the 1.5–2.0s range and avoid tripping Serebii's "
            "rate limiter)."
        ),
    )
    parser.add_argument(
        "--image-sleep",
        type=float,
        default=0.25,
        help=(
            "Base seconds to sleep between individual image downloads "
            "(default 0.25). Images are static assets so they're throttled "
            "less aggressively than detail pages, but the flag is exposed "
            "for users who want to be extra polite."
        ),
    )
    parser.add_argument(
        "--force-images",
        action="store_true",
        help="Re-download images even if they already exist on disk.",
    )

    args = parser.parse_args()
    run(
        only=args.only,
        pokemon_limit=args.pokemon_limit,
        pokemon_sleep=args.pokemon_sleep,
        image_sleep=args.image_sleep,
        force_images=args.force_images,
    )


if __name__ == "__main__":
    main()
