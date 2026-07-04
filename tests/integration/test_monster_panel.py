"""Regression test: monster ASCII art must render verbatim.

Two bugs used to mangle the sprites: rich parsed bracketed face parts like
"[o o]" as markup tags and swallowed them, and str.strip() removed only the
first line's indentation, knocking the head out of alignment.
"""

import io

from rich.console import Console

from app.engine import Monster, global_game_state
from app.main import get_monster_panel


def _render(monster_name: str) -> str:
    global_game_state.select_character("Wizard", "Test")
    global_game_state.active_monster = Monster(
        monster_name, hp=45, attack=10, xp_reward=20, gold_reward=10
    )
    console = Console(width=70, file=io.StringIO(), record=True)
    console.print(get_monster_panel())
    return console.export_text()


def test_stone_golem_face_survives_markup():
    out = _render("Stone Golem")
    assert "|[o o]|" in out  # the bracketed face must not be parsed as markup
    assert ".=====." in out


def test_sprite_head_stays_aligned():
    out = _render("Goblin Scout")
    lines = out.splitlines()
    head = next(line for line in lines if ",-." in line)
    eyes = next(line for line in lines if "(o.o)" in line)
    # the head sits one column right of the eyes in the source art
    assert head.index(",-.") == eyes.index("(o.o)") + 1
