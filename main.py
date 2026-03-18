#!/usr/bin/env python3
"""
Tron Snake AI Arena
Main entry point for the game.
"""

import argparse
from gui import main_menu

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tron Snake AI Arena')
    parser.add_argument(
        '--usesource',
        action='store_true',
        help='Load bots from bots/*.py instead of compiled_bots/*.so'
    )
    args = parser.parse_args()
    
    main_menu(use_source=args.usesource)
