"""Learnset ownership when one Serebii page has several Standard Moves tables.

"Standard Moves - Midnight Form" is a secondary learnset. "Alola Form Standard
Moves" and "Galarian Form Standard Moves" stay on the regional form.
"""

from __future__ import annotations

import pytest

from scrapers.pokemon import scrape_pokemon_details


def _move_rows(moves: list[tuple[str, str]]) -> str:
    rows = []
    for slug, name in moves:
        rows.append(
            f"""
            <tr>
              <td><a href="/attackdex-champions/{slug}.shtml">{name}</a></td>
              <td><img src="/pokedex-bw/type/rock.gif" alt="Rock"></td>
              <td><img src="/pokedex-bw/type/physical.png" alt="Physical"></td>
              <td>40</td>
              <td>100</td>
              <td>20</td>
              <td>--</td>
            </tr>
            <tr><td colspan="7">Effect of {name}.</td></tr>
            """
        )
    return "\n".join(rows)


def _moves_table(header: str, moves: list[tuple[str, str]]) -> str:
    return f"""
    <table class="dextable">
      <tr><td class="fooevo" colspan="7">{header}</td></tr>
      {_move_rows(moves)}
    </table>
    """


def _name_table(name: str, dex: int) -> str:
    return f"""
    <table class="dextable">
      <tr><td>Name</td><td>No.</td><td>Type</td></tr>
      <tr>
        <td>{name}</td>
        <td>#{dex}</td>
        <td><img src="/pokedex-bw/type/rock.gif" alt="Rock"></td>
      </tr>
    </table>
    """


def _stats_table(header: str) -> str:
    return f"""
    <table class="dextable">
      <tr><td class="fooevo" colspan="8">{header}</td></tr>
    </table>
    """


def _page(*tables: str) -> str:
    return "<html><body>" + "\n".join(tables) + "</body></html>"


def _slugs(moves: list[dict]) -> set[str]:
    return {move["slug"] for move in moves}


def _form(result: dict, name: str) -> dict:
    matches = [entry for entry in result["forms"] if entry.get("name") == name]
    assert len(matches) == 1, result["forms"]
    return matches[0]


def _scrape(monkeypatch: pytest.MonkeyPatch, slug: str, html: str) -> dict:
    monkeypatch.setattr("scrapers.pokemon.fetch_html", lambda url: html)
    result = scrape_pokemon_details(slug, f"https://www.serebii.net/pokedex-champions/{slug}/")
    assert result is not None
    return result


def test_lycanroc_secondary_learnsets_stay_with_each_form(monkeypatch: pytest.MonkeyPatch):
    """Midday, Midnight, and Dusk each keep the table Serebii gives them.

    Page order matches the Champions Lycanroc dex: plain Standard Moves, then
    Standard Moves - Midnight Form, Standard Moves - Dusk Form, Stats, and the
    two Stats - form tables.
    """
    html = _page(
        _name_table("Lycanroc", 745),
        _moves_table(
            "Standard Moves",
            [("accelerock", "Accelerock"), ("tackle", "Tackle")],
        ),
        _moves_table(
            "Standard Moves - Midnight Form",
            [("firepunch", "Fire Punch"), ("knockoff", "Knock Off"), ("tackle", "Tackle")],
        ),
        _moves_table(
            "Standard Moves - Dusk Form",
            [("accelerock", "Accelerock"), ("crushclaw", "Crush Claw"), ("tackle", "Tackle")],
        ),
        _stats_table("Stats"),
        _stats_table("Stats - Midnight Form"),
        _stats_table("Stats - Dusk Form"),
    )

    result = _scrape(monkeypatch, "lycanroc", html)
    species = _slugs(result["moves"])
    midnight = _slugs(_form(result, "Midnight Form")["moves"])
    dusk = _slugs(_form(result, "Dusk Form")["moves"])

    assert "accelerock" in species
    assert "firepunch" not in species
    assert "knockoff" not in species

    assert "accelerock" not in midnight
    assert "firepunch" in midnight
    assert "knockoff" in midnight

    assert "accelerock" in dusk
    assert "crushclaw" in dusk

    assert species != midnight
    assert species != dusk
    assert midnight != dusk


@pytest.mark.parametrize(
    ("slug", "species", "dex", "regional_header", "stats_header", "form_name", "regional_move"),
    [
        (
            "meowth",
            "Meowth",
            52,
            "Alola Form Standard Moves",
            "Stats - Alolan Meowth",
            "Alolan Meowth",
            ("payback", "Payback"),
        ),
        (
            "slowpoke",
            "Slowpoke",
            79,
            "Galarian Form Standard Moves",
            "Stats - Galarian Slowpoke",
            "Galarian Slowpoke",
            ("shellsidearm", "Shell Side Arm"),
        ),
    ],
)
def test_regional_form_standard_moves_stay_on_the_regional_form(
    monkeypatch: pytest.MonkeyPatch,
    slug: str,
    species: str,
    dex: int,
    regional_header: str,
    stats_header: str,
    form_name: str,
    regional_move: tuple[str, str],
):
    html = _page(
        _name_table(species, dex),
        _moves_table(
            "Standard Moves",
            [("tackle", "Tackle"), ("payday", "Pay Day")],
        ),
        _moves_table(
            regional_header,
            [("tackle", "Tackle"), regional_move],
        ),
        _stats_table("Stats"),
        _stats_table(stats_header),
    )

    result = _scrape(monkeypatch, slug, html)
    species_moves = _slugs(result["moves"])
    regional = _slugs(_form(result, form_name)["moves"])

    assert "payday" in species_moves
    assert regional_move[0] not in species_moves
    assert regional_move[0] in regional
    assert "payday" not in regional
    assert species_moves != regional
