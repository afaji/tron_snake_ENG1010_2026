# --- Configuration ---
CELL_SIZE = 15
FPS_SLOWEST = 1
FPS_SLOW = 5
FPS_MEDIUM = 15
FPS_FAST = 60
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600

# Game Mechanics Config
EMP_RADIUS = 3          
EMP_STUN_DURATION = 7
EMP_DETONATION_TIME = 5 
EMP_COOLDOWN = 15       # Turns to auto-recharge after explosion
EMP_HIT_BONUS = 50

COLORS = {
    'window_bg': (15, 15, 25),      
    'grid_bg': (40, 40, 40),        
    'grid_lines': (50, 50, 50),
    'border': (200, 200, 200),      
    'wall': (100, 100, 100),
    'timed_wall': (150, 50, 50),
    'coin': (255, 215, 0),
    'diamond': (0, 255, 255),
    'text': (255, 255, 255),
    'ui_bg': (30, 30, 40),
    'ui_border': (100, 100, 100),
    'emp_shock': (255, 255, 0),
    'emp_target': (50, 50, 255, 30), 
    'emp_target_border': (100, 100, 255, 100),
    'explosion_core': (150, 150, 255), 
    'explosion_outer': (255, 100, 0, 150) 
}

PLAYER_COLORS = [(0, 255, 255), (255, 0, 255), (50, 205, 50), (255, 165, 0)]
