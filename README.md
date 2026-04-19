# Pokémon Champions — Serebii Data Scraper

Scrapes battle-relevant data for the mobile game **Pokémon Champions** from
[Serebii.net](https://www.serebii.net/pokemonchampions/) and writes it to JSON
files in [`data/`](./data) that can be shipped as-is to a Flutter team-builder
app. A GitHub Action refreshes the data every Monday.

## What gets scraped

| Source page | Output file | What's in it |
| --- | --- | --- |
| [`/pokemonchampions/pokemon.shtml`](https://www.serebii.net/pokemonchampions/pokemon.shtml) + every `/pokedex-champions/<slug>/` page | `data/pokemon.json` | Full pokédex: types, abilities, base stats, max-stat ranges, type matchups, Mega/alternate forms, full learnset |
| same as above (raw listing only) | `data/pokemon_listing.json` | Flat list of every row on the dex page (one entry per form, including Megas) |
| [`/pokemonchampions/moves.shtml`](https://www.serebii.net/pokemonchampions/moves.shtml) | `data/moves.json` | Every move's type, category, power, accuracy, PP and effect |
| [`/pokemonchampions/items.shtml`](https://www.serebii.net/pokemonchampions/items.shtml) | `data/items.json` | Hold items, Mega Stones, Berries and Misc items |
| [`/pokemonchampions/newabilities.shtml`](https://www.serebii.net/pokemonchampions/newabilities.shtml) + [`/pokemonchampions/megaabilities.shtml`](https://www.serebii.net/pokemonchampions/megaabilities.shtml) | `data/abilities.json` | Champions-exclusive new abilities + which Pokémon gain which ability when Mega-Evolving |

All numeric fields that aren't applicable (e.g. the power of a status move, or
the accuracy of a never-miss move) are stored as `null`, **not** `0` or `100`.

## Output schemas

Every output file is wrapped with a `scraped_at` ISO-8601 timestamp and a
`count` (where meaningful) so consumers can cheap-check freshness without
parsing the whole file.

### `data/pokemon.json`

```json
{
  "scraped_at": "2026-04-19T19:57:00+00:00",
  "count": 186,
  "pokemon": [
    {
      "slug": "venusaur",
      "name": "Venusaur",
      "national_dex": 3,
      "types": ["grass", "poison"],
      "abilities": [
        {
          "slug": "overgrow",
          "name": "Overgrow",
          "url": "https://www.serebii.net/abilitydex/overgrow.shtml",
          "description": "When HP is below 1/3rd its maximum, power of Grass-type moves is increased by 50%."
        }
      ],
      "stats": {
        "base": {
          "hp": 80, "attack": 82, "defense": 83,
          "sp_attack": 100, "sp_defense": 100, "speed": 80
        },
        "total": 525,
        "max_at_level_100": {
          "hindering":  { "hp": "155 - 187", "attack": "91 - 120", "...": "..." },
          "neutral":    { "hp": "155 - 187", "attack": "102 - 134", "...": "..." },
          "beneficial": { "hp": "155 - 187", "attack": "112 - 147", "...": "..." }
        }
      },
      "type_effectiveness": {
        "normal": 1.0, "fire": 2.0, "water": 0.5, "...": "..."
      },
      "classification": "Seed Pokémon",
      "height": "6'07\" 2m",
      "weight": "220.5lbs 100kg",
      "gender_ratio": "Male ♂ : 88% Female ♀ : 12%",
      "other_names": "Japan : Fushigibana フシギバナ French : Florizarre ...",
      "sprite": "https://www.serebii.net/pokemonhome/pokemon/small/003.png",
      "forms": [
        {
          "name": "Mega Venusaur",
          "types": ["grass", "poison"],
          "abilities": [
            { "slug": "thickfat", "name": "Thick Fat", "url": "...", "description": "Fire and Ice-type moves deal 50% damage." }
          ],
          "stats": { "base": { "hp": 80, "attack": 100, "...": "..." }, "total": 625, "max_at_level_100": { "...": "..." } },
          "type_effectiveness": { "...": "..." },
          "classification": "Seed Pokémon",
          "height": "7'10\" 2.4m",
          "weight": "342.8lbs 155.5kg"
        }
      ],
      "moves": [
        {
          "slug": "bodyslam",
          "name": "Body Slam",
          "type": "normal",
          "category": "physical",
          "power": 85,
          "accuracy": 100,
          "pp": 16,
          "effect_chance": 30,
          "description": "Has a 30% chance of paralyzing the target…",
          "url": "https://www.serebii.net/attackdex-champions/bodyslam.shtml"
        }
      ],
      "page_url": "https://www.serebii.net/pokedex-champions/venusaur/"
    }
  ]
}
```

Notes:

- `category` is one of `"physical"`, `"special"`, `"status"`. Status moves have
  `power: null`.
- `accuracy` is `null` for moves that can't miss (Serebii marks them as `101`).
- `type_effectiveness` is a map from attacking type to damage multiplier
  (`0`, `0.25`, `0.5`, `1`, `2`, `4`). Values of `0` correspond to immunities.
- `forms[]` contains Mega Evolutions and game-canonical alternate forms whose
  types, stats or abilities differ from the base form.
- `moves[]` is the complete learnset of the **base form**. Mega-form learnsets
  are identical in practice so they're not duplicated.

### `data/pokemon_listing.json`

A thin wrapper around the raw dex-listing page, one entry per row (so both
`Venusaur` and `Mega Venusaur` get their own entry). Useful if you want sprites
for Megas without walking `pokemon.json`.

```json
{
  "national_dex": 3,
  "name": "Mega Venusaur",
  "slug": "venusaur",
  "page_url": "https://www.serebii.net/pokedex-champions/venusaur/",
  "types": ["grass", "poison"],
  "sprite": "https://www.serebii.net/pokemonhome/pokemon/small/003-m.png",
  "is_mega": true
}
```

### `data/moves.json`

```json
{
  "scraped_at": "...",
  "count": 494,
  "moves": [
    {
      "slug": "acidspray",
      "name": "Acid Spray",
      "type": "poison",
      "category": "special",
      "power": 40,
      "accuracy": 100,
      "pp": 20,
      "effect": "Lowers the target's Sp. Def stat by 2 stages.",
      "url": "https://www.serebii.net/attackdex-champions/acidspray.shtml"
    }
  ]
}
```

Same rules as per-Pokémon moves: `power` is `null` for status moves, and
`accuracy` is `null` for never-miss moves.

### `data/items.json`

```json
{
  "scraped_at": "...",
  "count": 138,
  "categories": ["Berries", "Hold Items", "Mega Stone", "Miscellaneous Items"],
  "items": [
    {
      "slug": "abomasite",
      "name": "Abomasite",
      "category": "Mega Stone",
      "effect": "One of a variety of mysterious Mega Stones…",
      "location": "Mega Evolution Tutorial",
      "sprite": "https://www.serebii.net/itemdex/sprites/abomasite.png"
    }
  ]
}
```

### `data/abilities.json`

```json
{
  "scraped_at": "...",
  "new_abilities": [
    {
      "slug": "piercingdrill",
      "name": "Piercing Drill",
      "effect": "When the Pokémon uses contact moves…",
      "new_in_champions": true,
      "url": "https://www.serebii.net/abilitydex/piercingdrill.shtml"
    }
  ],
  "mega_abilities": [
    {
      "national_dex": 36,
      "pokemon": "Mega Clefable",
      "pokemon_slug": "clefable",
      "types": ["fairy"],
      "abilities": [
        { "slug": "magicbounce", "name": "Magic Bounce", "url": "..." }
      ]
    }
  ]
}
```

`mega_abilities[]` is the mapping from a Mega form to the ability it gains on
Mega-Evolution. Cross-reference with `pokemon.json → forms[]` in a
team-builder: when a player equips a Mega Stone, swap in the ability here.

## Running locally

Python 3.12+ is recommended.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r scraper/requirements.txt

# Scrape everything (takes ~5–7 minutes due to the per-Pokémon sleep)
python scraper/main.py

# Faster iteration: scrape a single source
python scraper/main.py --only moves items abilities

# Smoke-test the per-Pokémon parser on a handful of pages
python scraper/main.py --only pokemon --pokemon-limit 10

# Override the politeness delay between detail-page requests
# (defaults to 1.5s + up to ~0.5s jitter; don't lower this unless you know
# what you're doing — Serebii has been known to IP-ban aggressive scrapers)
python scraper/main.py --pokemon-sleep 2.0
```

Output JSON is written to [`./data`](./data) with `indent=2`.

### How the scraper stays polite

- Every request uses the exact User-Agent Serebii requires:
  `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36`
- Between individual Pokémon page requests the scraper sleeps for a base of
  **1.5s plus up to ~0.5s of random jitter** (so roughly 1.5–2.0s per page).
  This is intentionally conservative: Serebii has historically rate-limited
  or IP-banned aggressive scrapers. Override with `--pokemon-sleep` if needed.
- Each per-Pokémon scrape is wrapped in `try/except`; failures are recorded to
  `data/pokemon_failures.json` instead of crashing the run.

## GitHub Actions

The workflow in [`.github/workflows/scrape.yml`](./.github/workflows/scrape.yml):

- Runs every **Monday at 06:00 UTC** and also exposes a manual
  `workflow_dispatch` trigger.
- Uses **Python 3.12 on `ubuntu-latest`**.
- Installs `scraper/requirements.txt`, runs `python scraper/main.py`, and only
  commits + pushes if the files in `data/` actually changed.
- Uses `permissions: contents: write` so the commit step can push back to the
  repo.

## Repo layout

```
pokemon-champions-data/
├── .github/
│   └── workflows/
│       └── scrape.yml
├── scraper/
│   ├── main.py
│   ├── requirements.txt
│   └── scrapers/
│       ├── __init__.py
│       ├── _utils.py
│       ├── abilities.py
│       ├── items.py
│       ├── moves.py
│       └── pokemon.py
├── data/
│   ├── abilities.json
│   ├── items.json
│   ├── moves.json
│   ├── pokemon.json
│   └── pokemon_listing.json
└── README.md
```
