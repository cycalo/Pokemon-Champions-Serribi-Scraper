# Pokémon Champions — Serebii data scraper

Scrapes **Pokémon Champions** data from [Serebii.net](https://www.serebii.net/pokemonchampions/) into [`data/`](./data) and downloads sprites and icons into [`images/`](./images), for use as bundled assets (e.g. in a Flutter app). A [GitHub Action](.github/workflows/scrape.yml) refreshes data **every Monday at 06:00 UTC** (and can be run manually).

## Outputs

| Step | Files | Contents |
| --- | --- | --- |
| `pokemon` | `pokemon.json`, `pokemon_listing.json` | Full dex (types, abilities, stats, matchups, forms, learnsets) plus a flat listing (one row per form). Failures → `pokemon_failures.json`. |
| `moves` | `moves.json` | All moves: type, category, power, accuracy, PP, effect. |
| `items` | `items.json` | Hold items, Mega Stones, Berries, misc. |
| `abilities` | `abilities.json` | Champions-only abilities and Mega ability mappings. |
| `images` | `images/**`, `images.json` | Local sprites/icons and a manifest; adds `sprite_path` to Pokémon and item JSON when present. |

Sources are the Champions section on Serebii (dex listing, per-species pages, moves/items/abilities pages, and asset URLs referenced from those pages).

**Conventions:** N/A numeric fields (e.g. status move power, never-miss accuracy) are `null`, not `0` or `100`. Most top-level JSON includes `scraped_at` (ISO-8601) and `count` where it helps consumers check freshness. In `pokemon.json`, each `stats` object has **`base`** (six integers) and **`total`** (their sum). Those six values are the **low** end of each range on Serebii’s **Max Stats — Neutral Nature** row (what Champions uses as combat stats), not the small “Base Stats” BST row on the page.

**Images:** Layout under `images/` is `pokemon/`, `types/` (+ `types/icons/`), `move-categories/`, `items/`. Downloads are **idempotent** (existing files skipped); use `--force-images` to re-fetch all. The `images` step needs existing `pokemon_listing.json` and `items.json` (run `pokemon` and `items` first, or a full run).

## Running locally

Python **3.12+** recommended.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r scraper/requirements.txt

python scraper/main.py
```

Useful flags:

| Flag | Purpose |
| --- | --- |
| `--only pokemon moves …` | Subset of: `pokemon`, `moves`, `items`, `abilities`, `images` |
| `--pokemon-limit N` | Only fetch N Pokémon detail pages (quick parser tests) |
| `--pokemon-sleep SEC` | Delay between dex detail requests (default `1.5` s + jitter) |
| `--image-sleep SEC` | Delay between image downloads (default `0.25` s) |
| `--force-images` | Re-download images even if already on disk |

Full runs are slow on a cold tree (many HTTP requests + first-time images); later runs reuse `images/` and are faster.

**Politeness:** Requests use Serebii’s expected User-Agent. Default Pokémon pacing is conservative (~1.5–2 s between detail pages including jitter); lowering delays risks rate limits or blocks. Per-species errors are recorded in `pokemon_failures.json` without stopping the whole run.

## GitHub Actions

[`.github/workflows/scrape.yml`](.github/workflows/scrape.yml): schedule **Monday 06:00 UTC**, `workflow_dispatch`, Python 3.12, `pip install -r scraper/requirements.txt`, `python scraper/main.py`, then commit/push only if `data/` or `images/` changed (`contents: write`).

## Layout

```
├── .github/workflows/scrape.yml
├── scraper/           # main.py, requirements.txt, scrapers/
├── data/              # *.json outputs
├── images/            # downloaded assets
└── README.md
```

For field-level structure, open the JSON under `data/` or read the scrapers under `scraper/scrapers/`.
