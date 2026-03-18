#!/usr/bin/env python3
"""
Tron Snake Runner
Runs the game without visualization and outputs rankings and scores.

Usage:
    # Run with default settings (first available map, first 4 bots)
    python runner.py
    
    # Or import and customize:
    from runner import main
    main(map_name="arena.txt", bot_names=["Axiom", "Stingray", "Lucre", "Wraith"])
    main(map_name="maze.txt", bot_names=["random_bot", "Axiom"], max_ticks=5000)

Features:
    - Runs game headlessly (no GUI)
    - Displays final rankings sorted by survival time and score
    - Shows player scores, status, and death tick
    - Creates a game log file for detailed turn-by-turn analysis
    - Configurable map, bots, and maximum tick limit
"""

import argparse

from game_logic import Game
from loader import load_bot_classes, load_maps


def run_game_headless(map_name, bot_data, max_ticks=10000):
    """
    Run the game without visualization.
    
    Args:
        map_name: Name of the map file to use
        bot_data: List of tuples (bot_name, bot_class) or None for each player
        max_ticks: Maximum number of game ticks before ending the game
        
    Returns:
        Dictionary containing rankings and scores
    """
    # Create the game (FPS doesn't matter for headless mode)
    game = Game(map_name, bot_data, speed_fps=60)
    
    # Run the game loop
    while not game.game_over and game.tick_count < max_ticks:
        game.update()
        
        # Check if game should end (all players dead)
        if game.check_game_over():
            game.game_over = True
    
    # Handle timeout case (game didn't end naturally)
    if game.tick_count >= max_ticks and not game.game_over:
        print(f"\n⚠️  Game reached maximum ticks ({max_ticks}) without ending")
        game.game_over = True
        game.apply_end_game_bonuses()
    
    # Collect results
    results = []
    for p in game.players:
        results.append({
            'player_id': p.id,
            'bot_name': p.bot_name,
            'score': p.score,
            'alive': p.alive,
            'death_tick': p.death_tick if not p.alive else None
        })
    
    # Sort by survival time (death_tick, None means survived to the end)
    # Then by score as tiebreaker
    results.sort(key=lambda x: (x['score'], x['death_tick'] if x['death_tick'] is not None else float('inf')), reverse=True)
    
    return {
        'map': map_name,
        'total_ticks': game.tick_count,
        'results': results,
        'log_file': game.log_filename
    }


def print_results(results):
    """Print the game results in a formatted way."""
    print("\n" + "="*60)
    print(f"GAME RESULTS - Map: {results['map']}")
    print(f"Total Ticks: {results['total_ticks']}")
    print("="*60)
    print()
    
    print("RANKINGS:")
    print("-" * 60)
    print(f"{'Rank':<6} {'Player':<10} {'Bot':<20} {'Score':<8} {'Status':<12} {'Death Tick':<12}")
    print("-" * 60)
    
    for rank, player in enumerate(results['results'], 1):
        status = "ALIVE" if player['alive'] else "DEAD"
        death_tick = "-" if player['death_tick'] is None else str(player['death_tick'])
        print(f"{rank:<6} P{player['player_id']:<9} {player['bot_name']:<20} {player['score']:<8} {status:<12} {death_tick:<12}")
    
    print("-" * 60)
    print()
    print(f"Log saved to: {results['log_file']}")
    print("="*60 + "\n")


def main(map_name=None, bot_names=None, max_ticks=10000, use_source=False):
    """
    Main entry point for the runner.
    
    Args:
        map_name: Name of the map to use (default: first available)
        bot_names: List of bot names for players 1-4 (default: first 4 available)
        max_ticks: Maximum number of ticks before ending the game
        use_source: If True, load bots from bots/*.py instead of compiled_bots/*.so
    """
    # Load available bots and maps
    all_bots = load_bot_classes(use_source=use_source)
    all_maps = load_maps()
    
    if not all_maps:
        print("Error: No maps found!")
        return
    
    if not all_bots:
        print("Error: No bots found!")
        return
    
    # Display available options
    print("Available maps:", ", ".join(all_maps))
    print("Available bots:", ", ".join(all_bots.keys()))
    print()
    
    # Select map
    if map_name is None:
        map_name = all_maps[0]
    elif map_name not in all_maps:
        print(f"Error: Map '{map_name}' not found!")
        return
    
    # Select bots
    if bot_names is None:
        # Default: use first 4 bots
        bot_names_list = list(all_bots.keys())[:4]
    else:
        bot_names_list = bot_names
    
    # Build bot data list (pad with None if fewer than 4)
    selected_bots = []
    for i in range(4):
        if i < len(bot_names_list) and bot_names_list[i] in all_bots:
            bot_name = bot_names_list[i]
            selected_bots.append((bot_name, all_bots[bot_name]))
        else:
            selected_bots.append(None)
    
    print(f"Running game on map: {map_name}")
    for i, bot_data in enumerate(selected_bots, 1):
        if bot_data:
            print(f"  Player {i}: {bot_data[0]}")
        else:
            print(f"  Player {i}: (empty)")
    print()
    
    # Run the game
    results = run_game_headless(map_name, selected_bots, max_ticks=max_ticks)
    
    # Print results
    print_results(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Tron Snake headless and print results.")
    parser.add_argument(
        "--map", "-m",
        dest="map_name",
        help="Map filename to use (e.g. s_choice_2.txt)",
    )
    parser.add_argument(
        "--bots", "-b",
        dest="bot_names",
        nargs="*",
        help="Bot names for players 1-4 in order (e.g. Stingray Wraith Lucre Axiom)",
    )
    parser.add_argument(
        "--max-ticks",
        dest="max_ticks",
        type=int,
        default=10000,
        help="Maximum number of ticks before forcing game end (default: 10000)",
    )
    parser.add_argument(
        "--usesource",
        action="store_true",
        help="Load bots from bots/*.py instead of compiled_bots/*.so",
    )

    args = parser.parse_args()

    # If no args are given, this behaves like the old default: first map, first 4 bots
    main(map_name=args.map_name, bot_names=args.bot_names, max_ticks=args.max_ticks, use_source=args.usesource)
