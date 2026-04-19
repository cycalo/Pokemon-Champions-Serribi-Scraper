"""Entry point for the Pokemon Champions scraper.

Runs every individual scraper and writes the results to the repo's /data
folder as indented JSON files.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `python scraper/main.py` work without installing as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapers import scrape_abilities, scrape_items, scrape_moves, scrape_pokemon  # noqa: E402
from scrapers._utils import write_json  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(only: list[str] | None = None, pokemon_limit: int | None = None,
        pokemon_sleep: float = 1.5) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Pokemon Champions data from Serebii.")
    parser.add_argument(
        "--only",
        nargs="*",
        choices=["pokemon", "moves", "items", "abilities"],
        help="Restrict the run to a subset of scrapers.",
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

    args = parser.parse_args()
    run(only=args.only, pokemon_limit=args.pokemon_limit, pokemon_sleep=args.pokemon_sleep)


if __name__ == "__main__":
    main()
