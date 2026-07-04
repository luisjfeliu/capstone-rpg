import json
import logging
import os
import sys
import textwrap
import warnings
from pathlib import Path

import readchar
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.segment import Segment, Segments
from rich.table import Table
from rich.text import Text

from app.agent import companion_agent, root_agent
from app.engine import MONSTER_ASCII, global_game_state

console = Console()

# Save games hold the engine snapshot only (party, gold, level, routes).
# The LLM conversation lives in an in-memory ADK session and is not saved -
# on resume the GM re-orients itself from get_game_status.
SAVE_PATH = Path(__file__).resolve().parent.parent / "savegame.json"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def show_banner():
    # figlet "small" font: uvx pyfiglet -f small "FORGOTTEN KING"
    banner = r"""
[bold red] ___ ___  ___  ___  ___ _____ _____ ___ _  _   _  _____ _  _  ___ [/bold red]
[bold red]| __/ _ \| _ \/ __|/ _ \_   _|_   _| __| \| | | |/ /_ _| \| |/ __|[/bold red]
[bold yellow]| _| (_) |   / (_ | (_) || |   | | | _|| .` | | ' < | || .` | (_ |[/bold yellow]
[bold yellow]|_| \___/|_|_\\___|\___/ |_|   |_| |___|_|\_| |_|\_\___|_|\_|\___|[/bold yellow]
    """
    console.print(Align.center(banner))
    console.print(Align.center("[bold cyan]Cooperative Multi-Agent RPG[/bold cyan]\n"))


def gm_panel(text: str, title: str = "Game Master") -> Panel:
    """Renders a GM response as a panel.

    The model narrates in Markdown (**bold**, lists, headers), so wrap the
    text in rich's Markdown renderer instead of printing it raw.
    """
    return Panel(
        Markdown(text), title=f"[bold blue]{title}[/bold blue]", border_style="blue"
    )


BANNER_HEIGHT = 8  # art (1 leading blank + 4 lines + 1 trailing) + subtitle + blank


def _render_lines(renderable, width: int) -> list:
    """Renders any rich renderable to a list of terminal lines."""
    options = console.options.update_width(width)
    return console.render_lines(renderable, options, pad=False)


def _lines_renderable(lines: list) -> Segments:
    """Re-packages rendered lines so they can be printed inside a Panel."""
    segments = []
    for line in lines:
        segments.extend(line)
        segments.append(Segment.line())
    return Segments(segments)


def show_scene(gm_text: str, title: str = "Game Master"):
    """Redraws the screen: banner, GM narration, and the party status panel.

    The scene is sized to the terminal: banner and status panel are fixed,
    and the GM narration gets whatever height is left between them. When the
    narration is taller than that, it becomes a scrollable viewport
    (arrows / j / k / PgUp / PgDn, Enter to continue) with a line-range
    indicator, so the player never has to scroll the terminal itself.
    Non-interactive runs (piped stdin, CI) fall back to a plain print.
    """
    status = get_status_panel()
    term = console.size
    status_height = len(_render_lines(status, term.width))
    inner_width = term.width - 4  # panel borders + padding
    lines = _render_lines(Markdown(gm_text), inner_width)
    # Space for narration = terminal minus banner, status, panel borders,
    # and one line of breathing room for the upcoming input prompt.
    viewport = max(5, term.height - BANNER_HEIGHT - status_height - 2 - 1)

    if len(lines) <= viewport or not sys.stdin.isatty():
        clear_screen()
        show_banner()
        console.print(gm_panel(gm_text, title))
        console.print(status)
        return

    offset = 0
    max_offset = len(lines) - viewport
    while True:
        clear_screen()
        show_banner()
        visible = lines[offset : offset + viewport]
        indicator = (
            f"{'▲ ' if offset else ''}{'▼ ' if offset < max_offset else ''}"
            f"lines {offset + 1}-{offset + len(visible)} of {len(lines)}"
            " · ↑/↓ scroll · Enter continue"
        )
        console.print(
            Panel(
                _lines_renderable(visible),
                title=f"[bold blue]{title}[/bold blue]",
                border_style="blue",
                subtitle=f"[bold yellow]{indicator}[/bold yellow]",
                height=viewport + 2,
            )
        )
        console.print(status)
        key = readchar.readkey()
        if key in (readchar.key.UP, "k"):
            offset = max(0, offset - 1)
        elif key in (readchar.key.DOWN, "j"):
            offset = min(max_offset, offset + 1)
        elif key in (readchar.key.PAGE_DOWN, " "):
            offset = min(max_offset, offset + viewport)
        elif key == readchar.key.PAGE_UP:
            offset = max(0, offset - viewport)
        elif key in (readchar.key.ENTER, "\r", "q"):
            break


def save_game() -> None:
    SAVE_PATH.write_text(json.dumps(global_game_state.to_save_dict(), indent=2))
    console.print(f"[bold green]Game saved to {SAVE_PATH.name}. Farewell![/bold green]")


def try_resume_game() -> bool:
    """Offers to resume a saved game. Returns True if state was restored."""
    if not SAVE_PATH.exists():
        return False
    try:
        data = json.loads(SAVE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        console.print("[yellow]Found a corrupted save file - starting fresh.[/yellow]")
        return False
    name = data.get("player", {}).get("name", "?")
    level = data.get("current_level", "?")
    if not Confirm.ask(
        f"Found a saved game ({name}, dungeon level {level}). Resume it?",
        default=True,
    ):
        return False
    global_game_state.restore_save_dict(data)
    return True


def get_status_panel():
    g = global_game_state
    if not g.player:
        return Panel("No game active", title="Party Status")

    table = Table(show_header=False, box=ROUNDED, expand=True)
    table.add_column("Stat", style="bold cyan")
    table.add_column("Value", style="bold white")

    # Level / Gold
    table.add_row("Game Level", f"{g.current_level} / 7")
    table.add_row("Party Gold", f"{g.gold} GP")
    table.add_row("Inventory", ", ".join(g.inventory) if g.inventory else "Empty")

    # Route Status
    if g.selected_route:
        table.add_row(
            "Path",
            f"{g.selected_route.direction.capitalize()} ({g.selected_route.difficulty})",
        )
        table.add_row(
            "Progress", f"Room {g.current_room_index} / {g.selected_route.length}"
        )
    else:
        table.add_row("Path", "None Selected")

    p = g.player
    p_status = f"HP: {p.hp}/{p.max_hp}"
    if p.char_class == "Wizard":
        p_status += f"  Mana: {p.mana}/{p.max_mana}"
    table.add_row(
        f"[bold green]Player: {p.name} ({p.char_class})[/bold green]",
        f"Lvl {p.level}  XP: {p.exp}/{p.level * 100}\n{p_status}",
    )

    c = g.companion
    c_status = f"HP: {c.hp}/{c.max_hp}"
    if c.char_class == "Wizard":
        c_status += f"  Mana: {c.mana}/{c.max_mana}"
    table.add_row(
        f"[bold magenta]NPC: {c.name} ({c.char_class})[/bold magenta]",
        f"Lvl {c.level}  XP: {c.exp}/{c.level * 100}\n{c_status}",
    )

    return Panel(
        table, title="[bold yellow]Party Status[/bold yellow]", border_style="yellow"
    )


def get_monster_panel():
    g = global_game_state
    if not g.active_monster:
        return None

    m = g.active_monster
    art = MONSTER_ASCII.get(m.name, MONSTER_ASCII["Fallback"])

    desc = f"[bold red]{m.name}[/bold red]\nHP: {m.hp} / {m.max_hp}\nAttack: {m.attack}\n\n"

    # Dedent instead of strip(): strip() removed only the FIRST line's
    # leading spaces, knocking the sprite's head out of alignment.
    art_lines = textwrap.dedent(art).strip("\n").split("\n")
    max_art_len = max(len(line) for line in art_lines)
    padded_art = "\n".join(line.ljust(max_art_len) for line in art_lines)

    grid = Table.grid(expand=True)
    grid.add_column("Art", width=max_art_len + 4)
    grid.add_column("Stats")
    # Text() renders the art verbatim - as a plain string, rich would parse
    # bracketed face parts like "[o o]" as markup tags and swallow them.
    grid.add_row(Text(padded_art, style="bold green"), desc)

    return Panel(
        grid, title="[bold red]Combat Encounter[/bold red]", border_style="red"
    )


def choose_item() -> str | None:
    """Numbered pick from the actual inventory. Returns the item or None.

    The old menu hardcoded "Health Potion/Mana Potion" (making treasure like
    the Elixir of Life unreachable) and required typing the exact item name.
    """
    items = list(dict.fromkeys(global_game_state.inventory))
    if not items:
        console.print("[yellow]Your inventory is empty.[/yellow]")
        return None
    console.print("\n[bold cyan]Inventory:[/bold cyan]")
    for i, item in enumerate(items, 1):
        count = global_game_state.inventory.count(item)
        label = f"{item} (x{count})" if count > 1 else item
        console.print(f"{i}. {label}")
    console.print(f"{len(items) + 1}. Cancel")
    pick = Prompt.ask(
        "Use which item", choices=[str(n) for n in range(1, len(items) + 2)]
    )
    if int(pick) == len(items) + 1:
        return None
    return items[int(pick) - 1]


def wait_for_player():
    """Pauses until the player presses Enter.

    Combat narration used to be wiped after ~1s when the next phase cleared
    the screen; gating each phase on Enter lets the player read the outcome.
    """
    console.input("\n[dim]Press Enter to continue...[/dim]")


def run_agent_turn(runner, prompt, session_id, user_id):
    with console.status("[bold green]Agent thinking...[/bold green]"):
        events = runner.run(
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text=prompt)]
            ),
            user_id=user_id,
            session_id=session_id,
        )
    text_pieces = []
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    text_pieces.append(part.text)
    return "".join(text_pieces)


def main():
    # Keep ADK's internal chatter off the game screen: the sync session API
    # logs a "migrate to async" deprecation warning and the function-
    # declaration builder emits an [EXPERIMENTAL] UserWarning. Neither is
    # actionable for the player, so silence them for the CLI only.
    logging.getLogger("google_adk").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", message=r".*\[EXPERIMENTAL\].*")

    clear_screen()
    show_banner()

    # Setup ADK session and runners
    session_service = InMemorySessionService()
    session_id = "rpg_session_id"
    user_id = "player_user_id"
    session_service.create_session_sync(
        user_id=user_id, session_id=session_id, app_name="app"
    )

    runner_gm = Runner(
        agent=root_agent, session_service=session_service, app_name="app"
    )
    runner_companion = Runner(
        agent=companion_agent, session_service=session_service, app_name="app"
    )

    resumed = try_resume_game()
    if resumed:
        # The world is restored; the GM (fresh conversation) re-orients
        # itself from the game status and recaps where the party stands.
        gm_response = run_agent_turn(
            runner_gm,
            "The party has returned to the dungeon to resume their saved quest. "
            "Call get_game_status, recap their situation in a few sentences "
            "(who they are, dungeon level, chosen path and progress), and ask "
            "them to continue onward.",
            session_id,
            user_id,
        )
    else:
        # The GM initiates the game: it greets the adventurer and asks them
        # to choose a character (Wizard or Fighter) plus a name. The
        # conversation loops until the GM has called the select_character
        # tool, which populates global_game_state.player.
        gm_response = run_agent_turn(
            runner_gm,
            "A new adventurer has arrived at the dungeon entrance. Greet them, set the scene, and ask them to choose their character.",
            session_id,
            user_id,
        )
        console.print(gm_panel(gm_response))

        # Bounded free-text loop: after a few failed rounds fall back to
        # creating the character directly so the game can never wedge on a
        # misbehaving turn.
        for _ in range(4):
            if global_game_state.player:
                break
            answer = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            gm_response = run_agent_turn(runner_gm, answer, session_id, user_id)
            console.print(gm_panel(gm_response))
        if not global_game_state.player:
            console.print(
                "[yellow]The GM seems distracted - let's set up your hero directly.[/yellow]"
            )
            class_choice = Prompt.ask(
                "Choose your class", choices=["Wizard", "Fighter"]
            )
            player_name = Prompt.ask("Enter your character's name") or "Hero"
            global_game_state.select_character(class_choice, player_name)

        # Introduce level 1. Skipped when the GM already generated and
        # presented the routes as part of its character-selection follow-through.
        if not global_game_state.routes:
            gm_response = run_agent_turn(
                runner_gm,
                "Initialize level 1. Describe the story introduction, generate routes, and present the three available path choices (left, forward, right) to the user.",
                session_id,
                user_id,
            )

    player_class = global_game_state.player.char_class
    show_scene(gm_response)

    while not global_game_state.game_over:
        # 1. Path Selection Loop
        if not global_game_state.selected_route:
            choice = Prompt.ask(
                "\nChoose your path ('quit' to save & exit)",
                choices=["left", "forward", "right", "quit"],
            )
            if choice == "quit":
                save_game()
                return
            gm_response = run_agent_turn(
                runner_gm,
                f"We select the {choice} path. Set the selected route and enter the first room. Start combat if a monster is encountered, otherwise describe the room.",
                session_id,
                user_id,
            )
            show_scene(gm_response)
            continue

        # 2. Combat Loop
        if global_game_state.combat_active:
            m_panel = get_monster_panel()
            if m_panel:
                console.print(m_panel)

            console.print("\n[bold yellow]Your Turn![/bold yellow]")
            if player_class == "Wizard":
                console.print("1. Cast Fireball (10 mana)")
                console.print("2. Cast Heal (8 mana)")
                console.print("3. Cast Shield (5 mana)")
                console.print("4. Weapon Attack (Staff)")
                console.print("5. Use Item")
                combat_choice = Prompt.ask(
                    "Choose action", choices=["1", "2", "3", "4", "5"]
                )

                action_prompt = ""
                if combat_choice == "1":
                    action_prompt = "I cast Fireball at the monster."
                elif combat_choice == "2":
                    target = Prompt.ask("Heal target", choices=["player", "companion"])
                    action_prompt = f"I cast Heal on {target}."
                elif combat_choice == "3":
                    target = Prompt.ask(
                        "Shield target", choices=["player", "companion"]
                    )
                    action_prompt = f"I cast Shield on {target}."
                elif combat_choice == "4":
                    action_prompt = "I attack with my staff."
                elif combat_choice == "5":
                    item = choose_item()
                    if item is None:
                        continue
                    action_prompt = f"I use a {item}."
            else:  # Fighter
                console.print("1. Standard Melee Attack")
                console.print("2. Taunt Monster (protect ally)")
                console.print("3. Use Item")
                combat_choice = Prompt.ask("Choose action", choices=["1", "2", "3"])

                action_prompt = ""
                if combat_choice == "1":
                    action_prompt = "I attack the monster with my Greatsword."
                elif combat_choice == "2":
                    global_game_state.player.is_taunting = True
                    action_prompt = "I use Taunt on the monster."
                elif combat_choice == "3":
                    item = choose_item()
                    if item is None:
                        continue
                    action_prompt = f"I use a {item}."

            # Execute player turn through the GM agent
            gm_combat_res = run_agent_turn(
                runner_gm,
                f"The player action is: '{action_prompt}'. Call the appropriate execution tool to resolve, check if combat ended, and narrate the outcome.",
                session_id,
                user_id,
            )
            show_scene(gm_combat_res, title="Game Master (Player Action)")

            # Check if combat ended
            if not global_game_state.combat_active:
                continue

            # Companion's Turn - gated on Enter so the player can read the
            # outcome of their own action first.
            wait_for_player()
            console.print("\n[bold magenta]Companion's Turn...[/bold magenta]")
            companion_res = run_agent_turn(
                runner_companion,
                "It is your turn in combat. Get the current status, choose a cooperative tactical action, execute it via tool call, and say your in-character dialogue.",
                session_id,
                user_id,
            )

            # Sync the GM with companion action
            gm_companion_narr = run_agent_turn(
                runner_gm,
                f"The companion agent performed this turn: '{companion_res}'. Narrate the action's visual effect, check if combat ended, and narrate the result.",
                session_id,
                user_id,
            )
            show_scene(gm_companion_narr, title="Game Master (Companion Action)")

            if not global_game_state.combat_active:
                continue

            # Monster's Turn - gated on Enter so the companion's action stays
            # readable before the screen refreshes.
            wait_for_player()
            console.print("\n[bold red]Monster's Turn...[/bold red]")
            monster_log = global_game_state.monster_attack()
            gm_monster_narr = run_agent_turn(
                runner_gm,
                f"The monster attacked: '{monster_log}'. Resolve this action, check if anyone is dead, and narrate the monster's turn in a dramatic way.",
                session_id,
                user_id,
            )
            show_scene(gm_monster_narr, title="Game Master (Monster Action)")

        else:
            # Exploration Room Selection (safe between fights - saving is
            # only offered here, never mid-combat)
            console.print("\n[bold yellow]Exploration Action:[/bold yellow]")
            console.print("1. [bold green]Move Forward[/bold green] (Enter next room)")
            console.print("2. [bold cyan]Use Item[/bold cyan]")
            console.print(
                "3. [bold magenta]Act / Talk to the GM[/bold magenta] (free text - e.g. cast Heal, ask about the party)"
            )
            console.print("4. [bold white]Save & Quit[/bold white]")
            explore_choice = Prompt.ask("Choose action", choices=["1", "2", "3", "4"])

            if explore_choice == "1":
                if (
                    global_game_state.current_room_index
                    >= global_game_state.selected_route.length
                ):
                    # Advance Level
                    gm_response = run_agent_turn(
                        runner_gm,
                        "We have cleared all rooms. Call execute_advance_level to move to the next level, then describe the story transition and generate the next level routes.",
                        session_id,
                        user_id,
                    )
                else:
                    gm_response = run_agent_turn(
                        runner_gm,
                        "We move forward. Call enter_room, describe the next room, and tell us if a monster is encountered.",
                        session_id,
                        user_id,
                    )
                show_scene(gm_response)
            elif explore_choice == "2":
                item = choose_item()
                if item is not None:
                    gm_response = run_agent_turn(
                        runner_gm,
                        f"I use a {item} during exploration. Call execute_use_item to apply it, and narrate its effect.",
                        session_id,
                        user_id,
                    )
                    show_scene(gm_response)
            elif explore_choice == "3":
                # Free-text turn: lets the player do anything the tools
                # support outside combat - cast Heal/Shield, take stock,
                # or simply talk to the GM in character.
                request = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                if request.strip():
                    gm_response = run_agent_turn(
                        runner_gm,
                        f"During exploration (no combat) the player says: '{request}'. "
                        "If this asks for a concrete action (casting Heal or Shield, using an item, checking status), "
                        "call the matching tool and narrate the result. Do not enter rooms or advance levels unless explicitly asked. "
                        "Otherwise just respond in character.",
                        session_id,
                        user_id,
                    )
                    show_scene(gm_response)
            else:
                save_game()
                return

    # The run ended for real (victory or defeat) - a finished game should not
    # resume, so clear any leftover save.
    SAVE_PATH.unlink(missing_ok=True)

    console.print(
        "\n[bold yellow]=================================================[/bold yellow]"
    )
    if global_game_state.game_won:
        console.print(
            "[bold green]CONGRATULATIONS! You survived the dungeon and reached the portal![/bold green]"
        )
    else:
        console.print(
            "[bold red]GAME OVER. The darkness consumes your souls...[/bold red]"
        )
    console.print(
        "[bold yellow]=================================================[/bold yellow]"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Exiting without saving - use 'Save & Quit' in-game to keep your progress.[/yellow]"
        )
