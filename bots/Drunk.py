import random

class Bot:
    def get_move(self, board, id, pos, info):
        x, y = pos
        dirs = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
        valid_moves = []
        
        rows = len(board)
        cols = len(board[0])
        
        # Check all 4 directions
        for d, (dx, dy) in dirs.items():
            nx, ny = x + dx, y + dy
            
            # Bounds check
            if 0 <= nx < cols and 0 <= ny < rows:
                cell = board[ny][nx]
                # Avoid Walls, Trails, and Players
                if cell not in ['#', 't1', 't2', 't3', 't4', 'p1', 'p2', 'p3', 'p4']:
                    # Also avoid timed walls (integers)
                    if not isinstance(cell, int):
                        valid_moves.append(d)
        
        # If we have valid moves, pick one random
        if valid_moves:
            return random.choice(valid_moves)
        
        # If stuck, just go North (and likely die)
        return 'N'