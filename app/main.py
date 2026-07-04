import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.prompt import Prompt, IntPrompt
from rich.columns import Columns
from rich.table import Table
from rich.progress import ProgressBar
from rich.box import DOUBLE, ROUNDED

from app.engine import global_game_state, MONSTER_ASCII
from app.agent import root_agent, companion_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    banner = """
[bold red]  _  __          ___   ___ ___   _                    _      [/bold red]
[bold red] | |/ /___ _  _ / / | | _ | _ \ /_\  __ _ ___ _ _  __| |___  [/bold red]
[bold yellow] | ' </ _ | || < <| | |   |  _// _ \/ _` / -_) ' \/ _` (_-<  [/bold yellow]
[bold yellow] |_|\_\___/\_,_|_\|_| |_|_|_| /_/ \_\__, \___|_||_\__,_/__/  [/bold yellow]
[bold green]                                    |___/                    [/bold green]
    """
    console.print(Align.center(banner))
    console.print(Align.center("[bold cyan]Cooperative Multi-Agent RPG - Capstone Project[/bold cyan]\n"))

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
        table.add_row("Path", f"{g.selected_route.direction.capitalize()} ({g.selected_route.difficulty})")
        table.add_row("Progress", f"Room {g.current_room_index} / {g.selected_route.length}")
    else:
        table.add_row("Path", "None Selected")
        
    p = g.player
    p_status = f"HP: {p.hp}/{p.max_hp}"
    if p.char_class == "Wizard":
        p_status += f"  Mana: {p.mana}/{p.max_mana}"
    table.add_row(f"[bold green]Player: {p.name} ({p.char_class})[/bold green]", f"Lvl {p.level}  XP: {p.exp}/{p.level*100}\n{p_status}")
    
    c = g.companion
    c_status = f"HP: {c.hp}/{c.max_hp}"
    if c.char_class == "Wizard":
        c_status += f"  Mana: {c.mana}/{c.max_mana}"
    table.add_row(f"[bold magenta]NPC: {c.name} ({c.char_class})[/bold magenta]", f"Lvl {c.level}  XP: {c.exp}/{c.level*100}\n{c_status}")
    
    return Panel(table, title="[bold yellow]Party Status[/bold yellow]", border_style="yellow")

def get_monster_panel():
    g = global_game_state
    if not g.active_monster:
        return None
        
    m = g.active_monster
    art = MONSTER_ASCII.get(m.name, MONSTER_ASCII["Fallback"])
    
    # Calculate health bar
    hp_pct = max(0, m.hp / m.max_hp)
    bar = ProgressBar(total=100, completed=int(hp_pct * 100), width=20)
    
    desc = f"[bold red]{m.name}[/bold red]\nHP: {m.hp} / {m.max_hp}\nAttack: {m.attack}\n\n"
    
    art_lines = art.strip().split("\n")
    max_art_len = max(len(line) for line in art_lines)
    padded_art = "\n".join(line.ljust(max_art_len) for line in art_lines)
    
    grid = Table.grid(expand=True)
    grid.add_column("Art", width=max_art_len + 4)
    grid.add_column("Stats")
    grid.add_row(padded_art, desc)
    
    return Panel(grid, title="[bold red]Combat Encounter[/bold red]", border_style="red")

def run_agent_turn(runner, prompt, session_id, user_id):
    with console.status("[bold green]Agent thinking...[/bold green]"):
        events = runner.run(
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
            user_id=user_id,
            session_id=session_id
        )
    text_pieces = []
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    text_pieces.append(part.text)
    return "".join(text_pieces)

def main():
    clear_screen()
    show_banner()
    
    console.print("[bold yellow]Choose your class:[/bold yellow]")
    console.print("1. [bold green]Wizard[/bold green] (Casts Fireball, Shield, and Heal)")
    console.print("2. [bold red]Fighter[/bold red] (High HP, Slash, Taunt, and Shield Block)")
    class_choice = Prompt.ask("Enter choice (1-2)", choices=["1", "2"])
    
    player_class = "Wizard" if class_choice == "1" else "Fighter"
    player_name = Prompt.ask("Enter your character's name")
    if not player_name.strip():
        player_name = "Hero"
        
    # Select character
    global_game_state.select_character(player_class, player_name)
    
    # Setup ADK session and runners
    session_service = InMemorySessionService()
    session_id = "rpg_session_id"
    user_id = "player_user_id"
    session = session_service.get_or_create_session_sync(user_id=user_id, session_id=session_id, app_name="app")
    
    runner_gm = Runner(agent=root_agent, session_service=session_service, app_name="app")
    runner_companion = Runner(agent=companion_agent, session_service=session_service, app_name="app")
    
    # Introduce level 1
    gm_response = run_agent_turn(
        runner_gm, 
        f"Initialize level 1. Describe the story introduction, generate routes, and present the three available path choices (left, forward, right) to the user.", 
        session_id, 
        user_id
    )
    
    clear_screen()
    show_banner()
    console.print(Panel(gm_response, title="[bold blue]Game Master[/bold blue]", border_style="blue"))
    console.print(get_status_panel())
    
    while not global_game_state.game_over:
        # 1. Path Selection Loop
        if not global_game_state.selected_route:
            choice = Prompt.ask("\nChoose your path", choices=["left", "forward", "right"])
            gm_response = run_agent_turn(
                runner_gm,
                f"We select the {choice} path. Set the selected route and enter the first room. Start combat if a monster is encountered, otherwise describe the room.",
                session_id,
                user_id
            )
            clear_screen()
            show_banner()
            console.print(Panel(gm_response, title="[bold blue]Game Master[/bold blue]", border_style="blue"))
            console.print(get_status_panel())
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
                console.print("5. Use Health Potion")
                console.print("6. Use Mana Potion")
                combat_choice = Prompt.ask("Choose action", choices=["1", "2", "3", "4", "5", "6"])
                
                action_prompt = ""
                if combat_choice == "1":
                    action_prompt = "I cast Fireball at the monster."
                elif combat_choice == "2":
                    target = Prompt.ask("Heal target", choices=["player", "companion"])
                    action_prompt = f"I cast Heal on {target}."
                elif combat_choice == "3":
                    target = Prompt.ask("Shield target", choices=["player", "companion"])
                    action_prompt = f"I cast Shield on {target}."
                elif combat_choice == "4":
                    action_prompt = "I attack with my staff."
                elif combat_choice == "5":
                    action_prompt = "I use a Health Potion."
                elif combat_choice == "6":
                    action_prompt = "I use a Mana Potion."
            else: # Fighter
                console.print("1. Standard Melee Attack")
                console.print("2. Taunt Monster (protect ally)")
                console.print("3. Use Health Potion")
                combat_choice = Prompt.ask("Choose action", choices=["1", "2", "3"])
                
                action_prompt = ""
                if combat_choice == "1":
                    action_prompt = "I attack the monster with my Greatsword."
                elif combat_choice == "2":
                    global_game_state.player.is_taunting = True
                    action_prompt = "I use Taunt on the monster."
                elif combat_choice == "3":
                    action_prompt = "I use a Health Potion."
            
            # Execute player turn through the GM agent
            gm_combat_res = run_agent_turn(
                runner_gm,
                f"The player action is: '{action_prompt}'. Call the appropriate execution tool to resolve, check if combat ended, and narrate the outcome.",
                session_id,
                user_id
            )
            
            clear_screen()
            show_banner()
            console.print(Panel(gm_combat_res, title="[bold blue]Game Master (Player Action)[/bold blue]", border_style="blue"))
            console.print(get_status_panel())
            
            # Check if combat ended
            if not global_game_state.combat_active:
                continue
                
            # Companion's Turn
            console.print("\n[bold magenta]Companion's Turn...[/bold magenta]")
            time.sleep(1)
            companion_res = run_agent_turn(
                runner_companion,
                "It is your turn in combat. Get the current status, choose a cooperative tactical action, execute it via tool call, and say your in-character dialogue.",
                session_id,
                user_id
            )
            
            # Sync the GM with companion action
            gm_companion_narr = run_agent_turn(
                runner_gm,
                f"The companion agent performed this turn: '{companion_res}'. Narrate the action's visual effect, check if combat ended, and narrate the result.",
                session_id,
                user_id
            )
            
            clear_screen()
            show_banner()
            console.print(Panel(gm_companion_narr, title="[bold blue]Game Master (Companion Action)[/bold blue]", border_style="blue"))
            console.print(get_status_panel())
            
            if not global_game_state.combat_active:
                continue
                
            # Monster's Turn
            console.print("\n[bold red]Monster's Turn...[/bold red]")
            time.sleep(1)
            monster_log = global_game_state.monster_attack()
            gm_monster_narr = run_agent_turn(
                runner_gm,
                f"The monster attacked: '{monster_log}'. Resolve this action, check if anyone is dead, and narrate the monster's turn in a dramatic way.",
                session_id,
                user_id
            )
            
            clear_screen()
            show_banner()
            console.print(Panel(gm_monster_narr, title="[bold blue]Game Master (Monster Action)[/bold blue]", border_style="blue"))
            console.print(get_status_panel())
            
        else:
            # Exploration Room Selection
            console.print("\n[bold yellow]Exploration Action:[/bold yellow]")
            console.print("1. [bold green]Move Forward[/bold green] (Enter next room)")
            console.print("2. [bold cyan]Use Potion[/bold cyan]")
            explore_choice = Prompt.ask("Choose action", choices=["1", "2"])
            
            if explore_choice == "1":
                if global_game_state.current_room_index >= global_game_state.selected_route.length:
                    # Advance Level
                    gm_response = run_agent_turn(
                        runner_gm,
                        "We have cleared all rooms. Call execute_advance_level to move to the next level, then describe the story transition and generate the next level routes.",
                        session_id,
                        user_id
                    )
                else:
                    gm_response = run_agent_turn(
                        runner_gm,
                        "We move forward. Call enter_room, describe the next room, and tell us if a monster is encountered.",
                        session_id,
                        user_id
                    )
                clear_screen()
                show_banner()
                console.print(Panel(gm_response, title="[bold blue]Game Master[/bold blue]", border_style="blue"))
                console.print(get_status_panel())
            else:
                potion = Prompt.ask("Choose potion", choices=["Health Potion", "Mana Potion", "Cancel"])
                if potion != "Cancel":
                    gm_response = run_agent_turn(
                        runner_gm,
                        f"I use a {potion} during exploration. Call execute_use_item to apply it, and narrate its effect.",
                        session_id,
                        user_id
                    )
                    clear_screen()
                    show_banner()
                    console.print(Panel(gm_response, title="[bold blue]Game Master[/bold blue]", border_style="blue"))
                    console.print(get_status_panel())
                    
    console.print("\n[bold yellow]=================================================[/bold yellow]")
    if global_game_state.game_won:
        console.print("[bold green]CONGRATULATIONS! You survived the dungeon and reached the portal![/bold green]")
    else:
        console.print("[bold red]GAME OVER. The darkness consumes your souls...[/bold red]")
    console.print("[bold yellow]=================================================[/bold yellow]")

if __name__ == "__main__":
    main()
