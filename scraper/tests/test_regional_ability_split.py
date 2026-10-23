"""Form ownership for a shared Serebii abilities table.

Parentheticals in the header and bold headings in the description name the
owner. An even split is only the fallback when neither signal is present.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from scrapers.pokemon import _parse_abilities_table, _split_default_and_alternate_abilities


def _abilities(*names: str) -> list[dict]:
    rows = []
    for name in names:
        slug = name.lower().replace(" ", "")
        rows.append(
            {
                "slug": slug,
                "name": name,
                "url": f"https://www.serebii.net/abilitydex/{slug}.shtml",
                "description": f"desc:{name}",
            }
        )
    return rows


def _result(name: str, ability_names: list[str], forms: list[tuple[str, list[str], bool]]):
    return {
        "name": name,
        "abilities": _abilities(*ability_names),
        "forms": [
            {
                "name": form_name,
                "abilities": _abilities(*form_abilities),
                "is_mega": is_mega,
            }
            for form_name, form_abilities, is_mega in forms
        ],
    }


def _table(html: str):
    return BeautifulSoup(html, "lxml").find("table")


def _names(abilities: list[dict]) -> list[str]:
    return [ability["name"] for ability in abilities]


def _apply(result: dict, html: str) -> None:
    _split_default_and_alternate_abilities(result, _table(html))


STUNFISK_HTML = """
<table class="dextable">
<tr>
<td><b>Abilities</b>:
<a href="/abilitydex/static.shtml"><b>Static</b></a> -
<a href="/abilitydex/limber.shtml"><b>Limber</b></a> -
<a href="/abilitydex/sandveil.shtml"><b>Sand Veil</b></a> <i></i> (Stunfisk) -
<a href="/abilitydex/mimicry.shtml"><b>Mimicry</b></a> (Galarian Form)</td>
</tr>
<tr>
<td>
<a href="/abilitydex/static.shtml"><b>Static</b></a>: contact paralysis<br/>
<a href="/abilitydex/limber.shtml"><b>Limber</b></a>: cannot be paralysed<br/>
<a href="/abilitydex/sandveil.shtml"><b>Sand Veil</b></a>: evasion in sand<br/>
<b>Galarian Form Abilities</b>:<br/>
<a href="/abilitydex/mimicry.shtml"><b>Mimicry</b></a>: terrain type change
</td>
</tr>
</table>
"""

NINETALES_HTML = """
<table class="dextable">
<tr>
<td><b>Abilities</b>:
<a href="/abilitydex/flashfire.shtml"><b>Flash Fire</b></a> -
<a href="/abilitydex/drought.shtml"><b>Drought</b></a> <i></i> (Ninetales) -
<a href="/abilitydex/snowcloak.shtml"><b>Snow Cloak</b></a>-
<a href="/abilitydex/snowwarning.shtml"><b>Snow Warning</b></a> <i></i> (Alola Form)</td>
</tr>
<tr>
<td>
<a href="/abilitydex/flashfire.shtml"><b>Flash Fire</b></a>: fire boost<br/>
<a href="/abilitydex/drought.shtml"><b>Drought</b></a>: sun<br/>
<b>Alola Form Abilities</b>:<br/>
<a href="/abilitydex/snowcloak.shtml"><b>Snow Cloak</b></a>: evasion in snow<br/>
<a href="/abilitydex/snowwarning.shtml"><b>Snow Warning</b></a>: snow
</td>
</tr>
</table>
"""

TYPHLOSION_HTML = """
<table class="dextable">
<tr>
<td><b>Abilities</b>:
<a href="/abilitydex/blaze.shtml"><b>Blaze</b></a> -
<a href="/abilitydex/flashfire.shtml"><b>Flash Fire</b></a> <i></i> (Typhlosion) -
<a href="/abilitydex/blaze.shtml"><b>Blaze</b></a>-
<a href="/abilitydex/frisk.shtml"><b>Frisk</b></a> <i></i> (Hisuian Form)</td>
</tr>
<tr>
<td>
<a href="/abilitydex/blaze.shtml"><b>Blaze</b></a>: fire when hurt<br/>
<a href="/abilitydex/flashfire.shtml"><b>Flash Fire</b></a>: fire boost<br/>
<b>Hisuian Form Abilities</b>:<br/>
<a href="/abilitydex/blaze.shtml"><b>Blaze</b></a>: fire when hurt<br/>
<a href="/abilitydex/frisk.shtml"><b>Frisk</b></a>: reveals item
</td>
</tr>
</table>
"""

SAMUROTT_HTML = """
<table class="dextable">
<tr>
<td><b>Abilities</b>:
<a href="/abilitydex/torrent.shtml"><b>Torrent</b></a> -
<a href="/abilitydex/shellarmor.shtml"><b>Shell Armor</b></a> <i></i> (Samurott) -
<a href="/abilitydex/torrent.shtml"><b>Torrent</b></a>-
<a href="/abilitydex/sharpness.shtml"><b>Sharpness</b></a> <i></i> (Hisuian Form)</td>
</tr>
<tr>
<td>
<a href="/abilitydex/torrent.shtml"><b>Torrent</b></a>: water when hurt<br/>
<a href="/abilitydex/shellarmor.shtml"><b>Shell Armor</b></a>: no crits<br/>
<b>Hisuian Form Abilities</b>:<br/>
<a href="/abilitydex/torrent.shtml"><b>Torrent</b></a>: water when hurt<br/>
<a href="/abilitydex/sharpness.shtml"><b>Sharpness</b></a>: slicing boost
</td>
</tr>
</table>
"""

DECIDUEYE_HTML = """
<table class="dextable">
<tr>
<td><b>Abilities</b>:
<a href="/abilitydex/overgrow.shtml"><b>Overgrow</b></a> -
<a href="/abilitydex/longreach.shtml"><b>Long Reach</b></a> <i></i> (Decidueye) -
<a href="/abilitydex/overgrow.shtml"><b>Overgrow</b></a>-
<a href="/abilitydex/scrappy.shtml"><b>Scrappy</b></a> <i></i> (Hisuian Form)</td>
</tr>
<tr>
<td>
<a href="/abilitydex/overgrow.shtml"><b>Overgrow</b></a>: grass when hurt<br/>
<a href="/abilitydex/longreach.shtml"><b>Long Reach</b></a>: no contact<br/>
<b>Hisuian Form Abilities</b>:<br/>
<a href="/abilitydex/overgrow.shtml"><b>Overgrow</b></a>: grass when hurt<br/>
<a href="/abilitydex/scrappy.shtml"><b>Scrappy</b></a>: hits ghosts
</td>
</tr>
</table>
"""


def test_stunfisk_keeps_sand_veil_on_the_base_form():
    result = _result(
        "Stunfisk",
        ["Static", "Limber", "Sand Veil", "Mimicry"],
        [("Galarian Stunfisk", [], False)],
    )
    _apply(result, STUNFISK_HTML)

    assert _names(result["abilities"]) == ["Static", "Limber", "Sand Veil"]
    assert _names(result["forms"][0]["abilities"]) == ["Mimicry"]
    assert result["abilities"][2]["description"] == "desc:Sand Veil"


def test_regional_even_pairs_stay_on_their_forms():
    cases = [
        (
            "Ninetales",
            ["Flash Fire", "Drought", "Snow Cloak", "Snow Warning"],
            "Alolan Ninetales",
            ["Flash Fire", "Drought"],
            ["Snow Cloak", "Snow Warning"],
            NINETALES_HTML,
        ),
        (
            "Typhlosion",
            ["Blaze", "Flash Fire", "Blaze", "Frisk"],
            "Hisuian Typhlosion",
            ["Blaze", "Flash Fire"],
            ["Blaze", "Frisk"],
            TYPHLOSION_HTML,
        ),
        (
            "Samurott",
            ["Torrent", "Shell Armor", "Torrent", "Sharpness"],
            "Hisuian Samurott",
            ["Torrent", "Shell Armor"],
            ["Torrent", "Sharpness"],
            SAMUROTT_HTML,
        ),
        (
            "Decidueye",
            ["Overgrow", "Long Reach", "Overgrow", "Scrappy"],
            "Hisuian Decidueye",
            ["Overgrow", "Long Reach"],
            ["Overgrow", "Scrappy"],
            DECIDUEYE_HTML,
        ),
    ]
    for species, all_names, form_name, base_names, form_names, html in cases:
        result = _result(species, all_names, [(form_name, [], False)])
        _apply(result, html)
        assert _names(result["abilities"]) == base_names
        assert _names(result["forms"][0]["abilities"]) == form_names
        if species == "Typhlosion":
            assert result["abilities"][0] is not result["forms"][0]["abilities"][0]


def test_header_group_alone_assigns_the_preceding_run():
    html = """
    <table>
    <tr><td><b>Abilities</b>:
    <a href="/abilitydex/static.shtml">Static</a> -
    <a href="/abilitydex/limber.shtml">Limber</a> -
    <a href="/abilitydex/sandveil.shtml">Sand Veil</a> (Stunfisk) -
    <a href="/abilitydex/mimicry.shtml">Mimicry</a> (Galarian Form)
    </td></tr>
    <tr><td>
    <a href="/abilitydex/static.shtml">Static</a>: a
    <a href="/abilitydex/limber.shtml">Limber</a>: b
    <a href="/abilitydex/sandveil.shtml">Sand Veil</a>: c
    <a href="/abilitydex/mimicry.shtml">Mimicry</a>: d
    </td></tr>
    </table>
    """
    result = _result(
        "Stunfisk",
        ["Static", "Limber", "Sand Veil", "Mimicry"],
        [("Galarian Stunfisk", [], False)],
    )
    _apply(result, html)
    assert _names(result["abilities"]) == ["Static", "Limber", "Sand Veil"]
    assert _names(result["forms"][0]["abilities"]) == ["Mimicry"]


def test_description_heading_alone_assigns_following_links():
    html = """
    <table>
    <tr><td><b>Abilities</b>:
    <a href="/abilitydex/static.shtml">Static</a> -
    <a href="/abilitydex/limber.shtml">Limber</a> -
    <a href="/abilitydex/sandveil.shtml">Sand Veil</a> -
    <a href="/abilitydex/mimicry.shtml">Mimicry</a>
    </td></tr>
    <tr><td>
    <a href="/abilitydex/static.shtml">Static</a>: a<br/>
    <a href="/abilitydex/limber.shtml">Limber</a>: b<br/>
    <a href="/abilitydex/sandveil.shtml">Sand Veil</a>: c<br/>
    <b>Galarian Form Abilities</b>:<br/>
    <a href="/abilitydex/mimicry.shtml">Mimicry</a>: d
    </td></tr>
    </table>
    """
    result = _result(
        "Stunfisk",
        ["Static", "Limber", "Sand Veil", "Mimicry"],
        [("Galarian Stunfisk", [], False)],
    )
    _apply(result, html)
    assert _names(result["abilities"]) == ["Static", "Limber", "Sand Veil"]
    assert _names(result["forms"][0]["abilities"]) == ["Mimicry"]


def test_unlabeled_abilities_stay_on_the_species():
    html = """
    <table>
    <tr><td><b>Abilities</b>:
    <a href="/abilitydex/flowerveil.shtml">Flower Veil</a> -
    <a href="/abilitydex/symbiosis.shtml">Symbiosis</a>
    </td></tr>
    <tr><td>
    <a href="/abilitydex/flowerveil.shtml">Flower Veil</a>: flowers
    <a href="/abilitydex/symbiosis.shtml">Symbiosis</a>: share
    </td></tr>
    </table>
    """
    result = _result(
        "Floette",
        ["Flower Veil", "Symbiosis"],
        [("Eternal Floette", [], False), ("Mega Floette", ["Fairy Aura"], True)],
    )
    mega = result["forms"][1]["abilities"]
    _apply(result, html)
    assert _names(result["abilities"]) == ["Flower Veil", "Symbiosis"]
    assert result["forms"][0]["abilities"] == []
    assert result["forms"][1]["abilities"] == mega


def test_gender_notes_share_unmarked_abilities_and_keep_hidden_abilities_separate():
    html = """
    <table>
    <tr><td><b>Abilities</b>:
    <a href="/abilitydex/keeneye.shtml">Keen Eye</a> -
    <a href="/abilitydex/infiltrator.shtml">Infiltrator</a> -
    <a href="/abilitydex/prankster.shtml">Prankster</a> <i>(Male Hidden Ability)</i> -
    <a href="/abilitydex/competitive.shtml">Competitive</a> <i>(Female Hidden Ability)</i>
    </td></tr>
    <tr><td>
    <a href="/abilitydex/keeneye.shtml"><b>Keen Eye</b></a>: accuracy<br/>
    <a href="/abilitydex/infiltrator.shtml"><b>Infiltrator</b></a>: screens<br/>
    <a href="/abilitydex/prankster.shtml"><b>Prankster</b> (Male)</a>: priority<br/>
    <a href="/abilitydex/competitive.shtml"><b>Competitive</b> (Female)</a>: special attack
    </td></tr>
    </table>
    """
    result = _result(
        "Meowstic",
        ["Keen Eye", "Infiltrator", "Prankster", "Competitive"],
        [("Female", ["Keen Eye", "Infiltrator", "Prankster", "Competitive"], False)],
    )
    _apply(result, html)
    assert _names(result["abilities"]) == ["Keen Eye", "Infiltrator", "Prankster"]
    assert _names(result["forms"][0]["abilities"]) == ["Keen Eye", "Infiltrator", "Competitive"]


def test_descriptions_stop_at_the_next_ability_link():
    html = """
    <table>
    <tr><td>
    <a href="/abilitydex/waterabsorb.shtml">Water Absorb</a> -
    <a href="/abilitydex/hydration.shtml">Hydration</a>
    </td></tr>
    <tr><td>
    <a href="/abilitydex/waterabsorb.shtml"><b>Water Absorb</b></a>: Heals from Water-type moves.<br/>
    <a href="/abilitydex/hydration.shtml"><b>Hydration</b></a>: All status problems: Burn, Paralysis, Sleep, Frozen and Poison, are healed when raining.
    </td></tr>
    </table>
    """
    abilities = _parse_abilities_table(_table(html))
    assert abilities[0]["description"] == "Heals from Water-type moves."
    assert abilities[1]["description"] == (
        "All status problems: Burn, Paralysis, Sleep, Frozen and Poison, are healed when raining."
    )

    gendered = """
    <table>
    <tr><td>
    <a href="/abilitydex/infiltrator.shtml">Infiltrator</a> -
    <a href="/abilitydex/prankster.shtml">Prankster</a> -
    <a href="/abilitydex/competitive.shtml">Competitive</a>
    </td></tr>
    <tr><td>
    <a href="/abilitydex/infiltrator.shtml"><b>Infiltrator</b></a>: Ignores screens.<br/>
    <a href="/abilitydex/prankster.shtml"><b>Prankster</b> (Male)</a>: Raises priority of status moves.<br/>
    <a href="/abilitydex/competitive.shtml"><b>Competitive</b> (Female)</a>: Raises Special Attack when a stat is lowered.
    </td></tr>
    </table>
    """
    abilities = _parse_abilities_table(_table(gendered))
    assert [a["name"] for a in abilities] == ["Infiltrator", "Prankster", "Competitive"]
    assert abilities[0]["description"] == "Ignores screens."
    assert abilities[1]["description"] == "Raises priority of status moves."
    assert abilities[2]["description"] == "Raises Special Attack when a stat is lowered."


def test_already_normalized_list_is_left_alone_when_the_table_is_longer():
    html = """
    <table>
    <tr><td><b>Abilities</b>:
    <a href="/abilitydex/punkrock.shtml">Punk Rock</a> -
    <a href="/abilitydex/plus.shtml">Plus</a> -
    <a href="/abilitydex/technician.shtml">Technician</a> <i></i> (Amped Form) -
    <a href="/abilitydex/punkrock.shtml">Punk Rock</a> -
    <a href="/abilitydex/minus.shtml">Minus</a> -
    <a href="/abilitydex/technician.shtml">Technician</a> <i></i> (Low Key Form)
    </td></tr>
    <tr><td>
    <a href="/abilitydex/punkrock.shtml">Punk Rock</a>: sound<br/>
    <a href="/abilitydex/plus.shtml">Plus</a>: plus<br/>
    <a href="/abilitydex/technician.shtml">Technician</a>: weak moves<br/>
    <b>Low Key Form Abilities</b>:<br/>
    <a href="/abilitydex/punkrock.shtml">Punk Rock</a>: sound<br/>
    <a href="/abilitydex/minus.shtml">Minus</a>: minus<br/>
    <a href="/abilitydex/technician.shtml">Technician</a>: weak moves
    </td></tr>
    </table>
    """
    result = _result(
        "Toxtricity",
        ["Punk Rock", "Plus", "Technician"],
        [("Low Key Form", ["Punk Rock", "Minus", "Technician"], False)],
    )
    _apply(result, html)
    assert _names(result["abilities"]) == ["Punk Rock", "Plus", "Technician"]
    assert _names(result["forms"][0]["abilities"]) == ["Punk Rock", "Minus", "Technician"]


def test_conflicting_signals_do_not_even_split():
    html = """
    <table>
    <tr><td><b>Abilities</b>:
    <a href="/abilitydex/static.shtml">Static</a> -
    <a href="/abilitydex/limber.shtml">Limber</a> (Stunfisk) -
    <a href="/abilitydex/sandveil.shtml">Sand Veil</a> -
    <a href="/abilitydex/mimicry.shtml">Mimicry</a> (Galarian Form)
    </td></tr>
    <tr><td>
    <a href="/abilitydex/static.shtml">Static</a>: a<br/>
    <b>Galarian Form Abilities</b>:<br/>
    <a href="/abilitydex/limber.shtml">Limber</a>: b<br/>
    <a href="/abilitydex/sandveil.shtml">Sand Veil</a>: c<br/>
    <a href="/abilitydex/mimicry.shtml">Mimicry</a>: d
    </td></tr>
    </table>
    """
    result = _result(
        "Stunfisk",
        ["Static", "Limber", "Sand Veil", "Mimicry"],
        [("Galarian Stunfisk", [], False)],
    )
    _apply(result, html)
    assert _names(result["abilities"]) == ["Static", "Limber", "Sand Veil", "Mimicry"]
    assert result["forms"][0]["abilities"] == []


def test_lycanroc_headings_cover_midday_when_the_header_label_does_not_match():
    html = """
    <table>
    <tr><td><b>Abilities</b>:
    <a href="/abilitydex/keeneye.shtml">Keen Eye</a> -
    <a href="/abilitydex/sandrush.shtml">Sand Rush</a> -
    <a href="/abilitydex/steadfast.shtml">Steadfast</a> <i></i> (Midday Form) -
    <a href="/abilitydex/keeneye.shtml">Keen Eye</a> -
    <a href="/abilitydex/vitalspirit.shtml">Vital Spirit</a> -
    <a href="/abilitydex/noguard.shtml">No Guard</a> <i></i> (Midnight Form) -
    <a href="/abilitydex/toughclaws.shtml">Tough Claws</a> (Dusk Form)
    </td></tr>
    <tr><td>
    <a href="/abilitydex/keeneye.shtml">Keen Eye</a>: accuracy<br/>
    <a href="/abilitydex/sandrush.shtml">Sand Rush</a>: sand speed<br/>
    <a href="/abilitydex/steadfast.shtml">Steadfast</a>: flinch speed<br/>
    <b>Midnight Form Abilities</b>:<br/>
    <a href="/abilitydex/keeneye.shtml">Keen Eye</a>: accuracy<br/>
    <a href="/abilitydex/vitalspirit.shtml">Vital Spirit</a>: sleep<br/>
    <a href="/abilitydex/noguard.shtml">No Guard</a>: accuracy<br/>
    <b>Dusk Form Abilities</b>:<br/>
    <a href="/abilitydex/toughclaws.shtml">Tough Claws</a>: contact
    </td></tr>
    </table>
    """
    result = _result(
        "Lycanroc",
        [
            "Keen Eye",
            "Sand Rush",
            "Steadfast",
            "Keen Eye",
            "Vital Spirit",
            "No Guard",
            "Tough Claws",
        ],
        [("Midnight Form", [], False), ("Dusk Form", [], False)],
    )
    _apply(result, html)
    assert _names(result["abilities"]) == ["Keen Eye", "Sand Rush", "Steadfast"]
    assert _names(result["forms"][0]["abilities"]) == ["Keen Eye", "Vital Spirit", "No Guard"]
    assert _names(result["forms"][1]["abilities"]) == ["Tough Claws"]


def test_raichu_signal_split_is_not_blocked_by_an_uneven_count():
    html = """
    <table>
    <tr><td><b>Abilities</b>:
    <a href="/abilitydex/static.shtml">Static</a> -
    <a href="/abilitydex/lightningrod.shtml">Lightning Rod</a> <i></i> (Raichu) -
    <a href="/abilitydex/surgesurfer.shtml">Surge Surfer</a> (Alola Form)
    </td></tr>
    <tr><td>
    <a href="/abilitydex/static.shtml">Static</a>: paralysis<br/>
    <a href="/abilitydex/lightningrod.shtml">Lightning Rod</a>: draws electric<br/>
    <b>Alola Form Abilities</b>:<br/>
    <a href="/abilitydex/surgesurfer.shtml">Surge Surfer</a>: terrain speed
    </td></tr>
    </table>
    """
    result = _result(
        "Raichu",
        ["Static", "Lightning Rod", "Surge Surfer"],
        [
            ("Alolan Raichu", [], False),
            ("Mega Raichu X", ["Electric Surge"], True),
            ("Mega Raichu Y", ["No Guard"], True),
        ],
    )
    _apply(result, html)
    assert _names(result["abilities"]) == ["Static", "Lightning Rod"]
    assert _names(result["forms"][0]["abilities"]) == ["Surge Surfer"]
    assert _names(result["forms"][1]["abilities"]) == ["Electric Surge"]
    assert _names(result["forms"][2]["abilities"]) == ["No Guard"]
