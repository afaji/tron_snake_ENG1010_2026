import pygame
import pygame_menu
import sys

from config import (
    CELL_SIZE, COLORS, PLAYER_COLORS, EMP_RADIUS,
    FPS_SLOWEST, FPS_SLOW, FPS_MEDIUM, FPS_FAST,
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
)
from loader import load_bot_classes, load_maps, get_map_choices, get_bot_choices, MapValidationError
from game_logic import Game


def draw_game(game, screen, offset_x, offset_y):
    """Draw the game grid and all game elements."""
    map_w = game.cols * CELL_SIZE
    map_h = game.rows * CELL_SIZE
    
    pygame.draw.rect(screen, COLORS['border'], (offset_x - 2, offset_y - 2, map_w + 4, map_h + 4))
    pygame.draw.rect(screen, COLORS['grid_bg'], (offset_x, offset_y, map_w, map_h))
    
    # Draw grid lines
    for y in range(game.rows):
        for x in range(game.cols):
            rect = (offset_x + x * CELL_SIZE, offset_y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, COLORS['grid_lines'], rect, 1)

    # Draw cells
    for y in range(game.rows):
        for x in range(game.cols):
            rect = (offset_x + x * CELL_SIZE, offset_y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            cx, cy = rect[0] + CELL_SIZE//2, rect[1] + CELL_SIZE//2
            cell = game.grid[y][x]
            if cell == '#':
                pygame.draw.rect(screen, COLORS['wall'], rect)
            elif isinstance(cell, int):
                pygame.draw.rect(screen, COLORS['timed_wall'], rect)
                pygame.draw.rect(screen, (200, 100, 100), rect, 1)
                font = pygame.font.SysFont('Arial', 12)
                txt = font.render(str(cell), True, (255, 255, 255))
                screen.blit(txt, (rect[0] + 5, rect[1] + 2))
            elif cell == 'c':
                pygame.draw.circle(screen, COLORS['coin'], (cx, cy), CELL_SIZE//3)
            elif cell == 'D':
                pts = [(cx, rect[1]+2), (rect[0]+CELL_SIZE-2, cy), (cx, rect[1]+CELL_SIZE-2), (rect[0]+2, cy)]
                pygame.draw.polygon(screen, COLORS['diamond'], pts)
            elif isinstance(cell, str) and cell.startswith('t'):
                try:
                    pid = int(cell[1:]) 
                    color = PLAYER_COLORS[pid - 1]
                    dark_color = (max(0, color[0]-50), max(0, color[1]-50), max(0, color[2]-50))
                    pygame.draw.rect(screen, dark_color, rect)
                    pygame.draw.rect(screen, COLORS['grid_lines'], rect, 1)
                except:
                    pass

    # Draw players
    for p in game.players:
        if p.alive:
            px, py = p.pos
            rect_x = offset_x + px * CELL_SIZE
            rect_y = offset_y + py * CELL_SIZE
            rect = (rect_x, rect_y, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, p.color, rect)
            dx, dy = game.dirs[p.direction]
            eye_x = rect_x + CELL_SIZE//2 + dx * 5
            eye_y = rect_y + CELL_SIZE//2 + dy * 5
            pygame.draw.circle(screen, (255,255,255), (eye_x, eye_y), 3)

            if p.loss_of_control_turns > 0:
                start_pos = (rect_x, rect_y)
                end_pos = (rect_x + CELL_SIZE, rect_y + CELL_SIZE)
                pygame.draw.line(screen, COLORS['emp_shock'], start_pos, end_pos, 3)
                pygame.draw.line(screen, COLORS['emp_shock'], (rect_x + CELL_SIZE, rect_y), (rect_x, rect_y + CELL_SIZE), 3)
                pygame.draw.rect(screen, COLORS['emp_shock'], rect, 2)

    # Draw EMPs
    font_emp = pygame.font.SysFont('Arial', 14, bold=True)
    s = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
    for emp in game.active_emps:
        ex, ey = emp['pos']
        timer = emp['timer']
        start_x = max(0, ex - EMP_RADIUS)
        end_x = min(game.cols - 1, ex + EMP_RADIUS)
        start_y = max(0, ey - EMP_RADIUS)
        end_y = min(game.rows - 1, ey + EMP_RADIUS)

        for y in range(start_y, end_y + 1):
            for x in range(start_x, end_x + 1):
                rect = (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(s, COLORS['emp_target'], rect)
                pygame.draw.rect(s, COLORS['emp_target_border'], rect, 1)

        cx = ex * CELL_SIZE + CELL_SIZE // 2
        cy = ey * CELL_SIZE + CELL_SIZE // 2
        txt = font_emp.render(str(timer), True, (255, 255, 255))
        screen.blit(s, (offset_x, offset_y))
        screen.blit(txt, (offset_x + cx - txt.get_width() // 2, offset_y + cy - txt.get_height() // 2))

    # Draw explosions
    exp_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
    for exp in game.explosions:
        alpha = int((exp.life / exp.max_life) * 255)
        ex, ey = exp.x, exp.y
        start_x = max(0, ex - exp.radius)
        end_x = min(game.cols - 1, ex + exp.radius)
        start_y = max(0, ey - exp.radius)
        end_y = min(game.rows - 1, ey + exp.radius)
        
        for y in range(start_y, end_y + 1):
            for x in range(start_x, end_x + 1):
                rect = (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                color = list(COLORS['explosion_outer']) 
                color[3] = alpha 
                if x == ex and y == ey:
                    pygame.draw.rect(exp_surf, (255, 255, 255, alpha), rect)
                else:
                    pygame.draw.rect(exp_surf, tuple(color), rect)
    screen.blit(exp_surf, (offset_x, offset_y))


def draw_ui(game, screen, win_width, win_height, ui_height):
    """Draw the UI panel at the bottom of the screen."""
    ui_y = win_height - ui_height
    pygame.draw.rect(screen, COLORS['ui_bg'], (0, ui_y, win_width, ui_height))
    pygame.draw.line(screen, COLORS['ui_border'], (0, ui_y), (win_width, ui_y), 2)
    slot_width = win_width // 4
    font_name = pygame.font.SysFont('Arial', 18, bold=True)
    font_bot = pygame.font.SysFont('Arial', 14, italic=True) 
    font_stats = pygame.font.SysFont('Arial', 14)

    for i, p in enumerate(game.players):
        slot_x = i * slot_width
        if not p.alive:
            pygame.draw.rect(screen, (20, 20, 25), (slot_x, ui_y, slot_width, ui_height))
        pygame.draw.rect(screen, p.color, (slot_x + 5, ui_y + 10, 5, ui_height - 20))
        cx = slot_x + 20
        
        title = f"PLAYER {p.id}"
        surf_title = font_name.render(title, True, p.color)
        screen.blit(surf_title, (cx, ui_y + 8))
        bot_str = p.bot_name if p.bot_name else "Unknown"
        surf_bot = font_bot.render(f"({bot_str})", True, (180, 180, 180))
        screen.blit(surf_bot, (cx, ui_y + 28))
        state_text = "DEAD" if not p.alive else ("STUNNED" if p.loss_of_control_turns > 0 else "ALIVE")
        state_color = (150, 50, 50) if not p.alive else ((255, 255, 0) if p.loss_of_control_turns > 0 else (100, 255, 100))
        surf_state = font_stats.render(state_text, True, state_color)
        screen.blit(surf_state, (cx + 100, ui_y + 10))
        surf_score = font_name.render(f"Score: {p.score}", True, (255, 255, 255))
        surf_phase = font_stats.render(f"Phase: {p.phase_charges}/3", True, (200, 200, 200))
        
        emp_str = f"EMP: {p.emp_charges}"
        if p.recharge_timers:
            min_timer = min(p.recharge_timers)
            emp_str += f" (+1 in {min_timer})"
        surf_emp = font_stats.render(emp_str, True, (200, 200, 200))
        
        screen.blit(surf_score, (cx, ui_y + 50))
        screen.blit(surf_phase, (cx + 100, ui_y + 50))
        screen.blit(surf_emp, (cx + 100, ui_y + 65))
        if i < 3:
            pygame.draw.line(screen, COLORS['ui_border'], (slot_x + slot_width, ui_y), (slot_x + slot_width, ui_y + ui_height), 1)


def draw_game_over(screen, win_width, win_height):
    """Draw the game over overlay."""
    go_font = pygame.font.SysFont('Arial', 60, bold=True)
    text_str = "GAME OVER"
    go_text_shadow = go_font.render(text_str, True, (0, 0, 0))
    center_x, center_y = win_width // 2, win_height // 2
    screen.blit(go_text_shadow, (center_x - go_text_shadow.get_width()//2 + 2, center_y - 20 + 2))
    go_text = go_font.render(text_str, True, (255, 50, 50))
    screen.blit(go_text, (center_x - go_text.get_width()//2, center_y - 20))
    sub_font = pygame.font.SysFont('Arial', 24)
    restart_str = "Press SPACE to return to menu"
    restart_shadow = sub_font.render(restart_str, True, (0,0,0))
    restart_label = sub_font.render(restart_str, True, (200, 200, 200))
    screen.blit(restart_shadow, (center_x - restart_shadow.get_width()//2 + 1, center_y + 50 + 1))
    screen.blit(restart_label, (center_x - restart_label.get_width()//2, center_y + 50))


# --- Game Configuration ---
game_config = {'map': '', 'p1': '', 'p2': '', 'p3': '', 'p4': '', 'speed': FPS_MEDIUM}


def set_map(value, map_name, **kwargs):
    # Accept extra kwargs from pygame_menu (e.g., 'search') and be flexible
    if map_name:
        game_config['map'] = map_name
    else:
        # Fallback: try to extract from value
        sel = value
        if isinstance(sel, (list, tuple)) and len(sel) >= 2:
            game_config['map'] = sel[1]


def set_bot(value, bot_name, player_key, **kwargs):
    key = f"p{player_key}"
    if bot_name:
        game_config[key] = bot_name
    else:
        sel = value
        if isinstance(sel, (list, tuple)) and len(sel) >= 2:
            game_config[key] = sel[1]


def set_speed(value, speed_val, **kwargs):
    game_config['speed'] = speed_val


def _extract_drop_value(args, kwargs):
    """Extract the logical value from various DropSelect callback signatures."""
    # Check common kw names
    for k in ('selected_item', 'selected', 'value'):
        if k in kwargs:
            return kwargs[k]

    if not args:
        return None

    a0 = args[0]
    # Case: onchange receives ((item, index), ) where item is (display, value)
    if isinstance(a0, tuple) and len(a0) == 2 and isinstance(a0[0], (list, tuple)):
        item = a0[0]
        if len(item) >= 2:
            return item[1]

    # Case: onchange receives (item, index) where item is (display, value)
    if isinstance(a0, (list, tuple)) and len(a0) >= 2 and len(args) > 1 and isinstance(args[1], int):
        item = a0
        return item[1]

    # Case: onchange receives item directly as (display, value)
    if isinstance(a0, (list, tuple)) and len(a0) >= 2:
        return a0[1]

    # Case: simple value or string
    return a0


def make_map_callback():
    def cb(*args, **kwargs):
        val = _extract_drop_value(args, kwargs)
        if val:
            game_config['map'] = val
    return cb


def make_bot_callback(player_key):
    def cb(*args, **kwargs):
        val = _extract_drop_value(args, kwargs)
        if val:
            game_config[f'p{player_key}'] = val
    return cb


def make_speed_callback():
    def cb(*args, **kwargs):
        val = _extract_drop_value(args, kwargs)
        if val is not None:
            # val might be the speed value or a tuple (label, value)
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                game_config['speed'] = val[1]
            else:
                game_config['speed'] = val
    return cb


def _apply_dropselect_value(sel):
    """Extract selected item from DropSelect and update game_config accordingly."""
    try:
        item, idx = sel.get_value()
    except Exception:
        return
    # item may be like (label, value) or a simple string
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        value = item[1]
    else:
        value = item

    title = ''
    try:
        title = sel.get_title() or ''
    except Exception:
        pass
    t = title.lower()
    if t.startswith('map'):
        game_config['map'] = value
    elif t.startswith('player'):
        # extract player number
        import re
        m = re.search(r'(\d+)', title)
        if m:
            p = int(m.group(1))
            game_config[f'p{p}'] = value
    elif t.startswith('speed'):
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            game_config['speed'] = value[1]
        else:
            game_config['speed'] = value


def start_the_game(use_source=False):
    """Start the game with current configuration."""
    all_bots = load_bot_classes(use_source=use_source)
    selected_bots = []
    for key in ['p1', 'p2', 'p3', 'p4']:
        name = game_config[key]
        if name and name in all_bots:
            selected_bots.append((name, all_bots[name]))
        else:
            selected_bots.append(None) 
    map_file = game_config['map']
    if not map_file:
        maps = load_maps()
        if maps:
            map_file = maps[0]
    run_game(map_file, selected_bots, game_config['speed'])


def show_error_screen(screen, title, message):
    """Display an error message screen."""
    screen.fill(COLORS['window_bg'])
    
    title_font = pygame.font.SysFont('Arial', 36, bold=True)
    msg_font = pygame.font.SysFont('Arial', 18)
    hint_font = pygame.font.SysFont('Arial', 16)
    
    # Title
    title_surf = title_font.render(title, True, (255, 80, 80))
    screen.blit(title_surf, (400 - title_surf.get_width() // 2, 150))
    
    # Message (split into lines)
    lines = message.split('\n')
    y_offset = 220
    for line in lines:
        line_surf = msg_font.render(line, True, (255, 255, 255))
        screen.blit(line_surf, (50, y_offset))
        y_offset += 25
    
    # Hint
    hint_surf = hint_font.render("Press any key to return to menu", True, (150, 150, 150))
    screen.blit(hint_surf, (400 - hint_surf.get_width() // 2, 500))
    
    pygame.display.flip()
    
    # Wait for key press
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                waiting = False


def run_game(map_name, bot_data, speed):
    """Run the main game loop."""
    screen = pygame.display.set_mode((800, 600))
    
    try:
        game = Game(map_name, bot_data, speed)
    except MapValidationError as e:
        show_error_screen(screen, "Invalid Map", str(e))
        return
    except Exception as e:
        show_error_screen(screen, "Error Loading Game", str(e))
        return
    
    map_width = game.cols * CELL_SIZE
    map_height = game.rows * CELL_SIZE
    ui_height = 100
    win_width = max(MIN_WINDOW_WIDTH, map_width + 50)
    win_height = max(MIN_WINDOW_HEIGHT, map_height + ui_height + 50)
    offset_x = (win_width - map_width) // 2
    offset_y = (win_height - ui_height - map_height) // 2
    if offset_y < 10:
        offset_y = 10

    screen = pygame.display.set_mode((win_width, win_height))
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if game.game_over and event.key == pygame.K_SPACE:
                    running = False 
        
        game.update()
        screen.fill(COLORS['window_bg'])
        draw_game(game, screen, offset_x, offset_y)
        draw_ui(game, screen, win_width, win_height, ui_height)
        
        if game.game_over:
            draw_game_over(screen, win_width, win_height)
            
        pygame.display.flip()
        clock.tick(speed)
    pygame.display.set_mode((800, 600))


def main_menu(use_source=False):
    """Display the main menu."""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Tron Snake AI Arena")
    maps = get_map_choices()
    bots = get_bot_choices(use_source=use_source)
    if maps:
        game_config['map'] = maps[0][1]

    # Default all players to the "Drunk" bot if available, otherwise fallback to first bot
    drunk_idx = 0
    for i, (name, val) in enumerate(bots):
        try:
            if name.lower() == 'drunk':
                drunk_idx = i
                break
        except Exception:
            continue
    for k in ['p1', 'p2', 'p3', 'p4']:
        if bots:
            game_config[k] = bots[drunk_idx][1]
    menu = pygame_menu.Menu('Game Setup', 800, 600, theme=pygame_menu.themes.THEME_DARK)
    # Enable searchable dropselects (where supported) and default players to Drunk
    menu.add.dropselect('Map :', maps, onchange=make_map_callback(), selection_box_height=5)
    menu.add.dropselect('Player 1 :', bots, default=drunk_idx, onchange=make_bot_callback(1), selection_box_height=5)
    menu.add.dropselect('Player 2 :', bots, default=drunk_idx, onchange=make_bot_callback(2), selection_box_height=5)
    menu.add.dropselect('Player 3 :', bots, default=drunk_idx, onchange=make_bot_callback(3), selection_box_height=5)
    menu.add.dropselect('Player 4 :', bots, default=drunk_idx, onchange=make_bot_callback(4), selection_box_height=5)
    # Set default speed to Medium (index 2)
    menu.add.dropselect('Speed :', [('Slowest', FPS_SLOWEST), ('Slow', FPS_SLOW), ('Medium', FPS_MEDIUM), ('Fast', FPS_FAST)], default=2, onchange=make_speed_callback())
    menu.add.button('START GAME', lambda: start_the_game(use_source=use_source))
    menu.add.button('Quit', pygame_menu.events.EXIT)

    # Custom main loop to provide simple typeahead for DropSelect widgets
    from pygame_menu.widgets import DropSelect
    typed_buf = ''
    last_typed = 0
    clock = pygame.time.Clock()
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                try:
                    sel = menu.get_selected_widget()
                    if isinstance(sel, DropSelect):
                        # Enter/Return should apply current highlighted value
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            try:
                                if hasattr(sel, 'apply'):
                                    sel.apply()
                                # Also explicitly update game_config from the widget
                                _apply_dropselect_value(sel)
                            except Exception:
                                pass
                            continue

                        ch = event.unicode if hasattr(event, 'unicode') else None
                        if ch and ch.isprintable():
                            now = pygame.time.get_ticks()
                            if now - last_typed > 1000:
                                typed_buf = ''
                            typed_buf += ch
                            last_typed = now
                            items = sel.get_items()
                            for i, it in enumerate(items):
                                text = it[0] if isinstance(it, (list, tuple)) else str(it)
                                if text.lower().startswith(typed_buf.lower()):
                                    try:
                                        sel.set_value(i)
                                        # apply selection immediately so keyboard selection is active
                                        if hasattr(sel, 'apply'):
                                            sel.apply()
                                    except Exception:
                                        pass
                                    break
                except Exception:
                    pass

        menu.update(events)
        screen.fill(COLORS['window_bg'])
        menu.draw(screen)
        pygame.display.flip()
        clock.tick(60)
        if not menu.is_enabled():
            running = False
