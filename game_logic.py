"""
Game logic module for Tron Snake.
Contains Player, Game, and Explosion classes.
"""
import copy
import datetime
import math
import signal
import sys
import time
import types
from collections import deque
from config import (
    EMP_RADIUS, EMP_STUN_DURATION, EMP_DETONATION_TIME, 
    EMP_COOLDOWN, EMP_HIT_BONUS, PLAYER_COLORS
)
from loader import build_full_map


TURN_WARNING_SECONDS = 0.5
TURN_DESTROY_SECONDS = 2.0
MAX_TURN_WARNINGS = 5
MEMORY_CHECK_INTERVAL_TICKS = 50
BOT_MEMORY_LIMIT_BYTES = 256 * 1024 * 1024


class BotTurnTimeoutError(TimeoutError):
    """Raised when a bot exceeds the hard turn time limit."""


def _handle_bot_timeout(signum, frame):
    raise BotTurnTimeoutError()


def _estimate_object_size(obj, seen):
    """Approximate the deep size of Python data reachable from an object."""
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)

    if isinstance(
        obj,
        (
            type,
            types.ModuleType,
            types.FunctionType,
            types.BuiltinFunctionType,
            types.MethodType,
            types.BuiltinMethodType,
            types.CodeType,
        ),
    ):
        return 0

    size = sys.getsizeof(obj)

    if isinstance(obj, dict):
        for key, value in obj.items():
            size += _estimate_object_size(key, seen)
            size += _estimate_object_size(value, seen)
        return size

    if isinstance(obj, (list, tuple, set, frozenset, deque)):
        for item in obj:
            size += _estimate_object_size(item, seen)
        return size

    if hasattr(obj, "__dict__"):
        size += _estimate_object_size(vars(obj), seen)

    slots = getattr(type(obj), "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    for slot in slots:
        if hasattr(obj, slot):
            size += _estimate_object_size(getattr(obj, slot), seen)

    return size


def estimate_bot_state_size(bot):
    """Approximate the persistent Python memory owned by a bot instance."""
    return _estimate_object_size(bot, set())


class Explosion:
    """Visual effect for EMP explosions."""
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.life = 5
        self.max_life = 5


class Player:
    """Represents a player in the game."""
    def __init__(self, id, start_pos, bot_class, bot_name_str, map_name):
        self.id = id
        self.pos = start_pos
        self.bot = bot_class()
        self.bot_name = bot_name_str 
        self.map_name = map_name
        self.alive = True
        self.score = 0
        self.color = PLAYER_COLORS[id - 1]
        self.death_tick = None 
        
        if self.id in [1, 2]:
            self.direction = 'S'
        else:
            self.direction = 'N'
        
        self.phase_charges = 3
        self.emp_charges = 1 
        self.loss_of_control_turns = 0
        self.turn_warnings = 0
        
        # Track used EMPs to return them later
        self.recharge_timers = [] 
        
    def get_move(self, internal_grid, players, active_emps):
        """Get the next move from the bot."""
        view_grid = copy.deepcopy(internal_grid)
        for p in players:
            if p.alive:
                px, py = p.pos
                view_grid[py][px] = f"p{p.id}"

        opponents_info = []
        for p in players:
            if p.id != self.id:
                opponents_info.append({
                    'id': p.id,
                    'pos': p.pos,
                    'alive': p.alive,
                    'direction': p.direction
                })

        safe_emps = [{'pos': e['pos'], 'timer': e['timer']} for e in active_emps]

        info = {
            'map_name': self.map_name,
            'my_score': self.score,
            'my_direction': self.direction,
            'phase_charges': self.phase_charges,
            'emp_charges': self.emp_charges,
            'emp_radius': EMP_RADIUS,
            'stun_duration': EMP_STUN_DURATION,
            'active_emps': safe_emps,
            'opponents': opponents_info
        }
        
        previous_handler = None
        used_timeout_handler = False
        start_time = time.perf_counter()

        try:
            if hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer"):
                previous_handler = signal.getsignal(signal.SIGALRM)
                signal.signal(signal.SIGALRM, _handle_bot_timeout)
                signal.setitimer(signal.ITIMER_REAL, TURN_DESTROY_SECONDS)
                used_timeout_handler = True

            move = self.bot.get_move(view_grid, self.id, self.pos, info)
            elapsed = time.perf_counter() - start_time

            if elapsed > TURN_WARNING_SECONDS:
                self.turn_warnings += 1
                if self.turn_warnings >= MAX_TURN_WARNINGS:
                    return 'TIMEOUT_DESTROY'

            return move
        except BotTurnTimeoutError:
            return 'TIMEOUT_DESTROY'
        except Exception:
            return self.direction
        finally:
            if used_timeout_handler:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous_handler)

    def exceeds_memory_limit(self):
        """Return True if the bot's persistent state estimate exceeds the cap."""
        try:
            return estimate_bot_state_size(self.bot) > BOT_MEMORY_LIMIT_BYTES
        except Exception:
            return False


class Game:
    """Main game logic class."""
    def __init__(self, map_name, bot_data, speed_fps):
        self.map_name = map_name
        self.raw_grid = build_full_map(map_name)
        self.rows = len(self.raw_grid)
        self.cols = len(self.raw_grid[0])
        self.fps = speed_fps
        self.players = []
        self.tick_count = 0
        self.game_over = False
        self.grid = [row[:] for row in self.raw_grid] 
        self.bonuses_applied = False 
        self.active_emps = []
        self.explosions = [] 
        self.death_reasons = {}

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_filename = f"game_log_{timestamp}.txt"
        with open(self.log_filename, "w") as f:
            f.write(f"Game Started: {timestamp}\nMap: {map_name}\n")
            f.write("Format: Turn | P1 | P2 | P3 | P4\n")
            f.write("-" * 40 + "\n")

        self.timed_walls = {} 
        start_positions = []
        
        for y in range(self.rows):
            for x in range(self.cols):
                char = self.grid[y][x]
                if char == 'S':
                    start_positions.append((x, y))
                    self.grid[y][x] = '.' 
                elif str(char).isdigit():
                    digit = int(char)
                    if 1 <= digit <= 9:
                        self.timed_walls[(x,y)] = digit * 10
        
        for i in range(min(4, len(start_positions))):
            p_id = i + 1
            if bot_data[i]:
                b_name, b_class = bot_data[i]
                self.players.append(Player(p_id, start_positions[i], b_class, b_name, map_name))

        self.dirs = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}

    def is_valid(self, x, y):
        """Check if coordinates are within the grid."""
        return 0 <= x < self.cols and 0 <= y < self.rows

    def log_turn(self, moves_dict):
        """Log the current turn's moves to file."""
        log_line = [f"{self.tick_count:04d}"]
        for p in self.players:
            if not p.alive:
                log_line.append("-")
            else:
                log_line.append(str(moves_dict.get(p, "?")))
        with open(self.log_filename, "a") as f:
            f.write("\t".join(log_line) + "\n")

    def parse_action(self, player, action):
        """Parse a raw bot action into EMP + movement components.

        Supported formats:
        - `N/S/E/W`: normal move
        - `+`: boost
        - `P`: phase
        - `XN/XS/XE/XW`: EMP + normal move
        - `X+`: EMP + boost
        - `XP`: EMP + phase
        """
        if not isinstance(action, str):
            return {'valid': False, 'emp': False, 'move': None}

        action = action.strip().upper()
        if not action:
            return {'valid': False, 'emp': False, 'move': None}

        use_emp = False
        if action.startswith('X'):
            use_emp = True
            action = action[1:]

        if action in self.dirs or action in ['+', 'P']:
            move_action = action
        else:
            return {'valid': False, 'emp': False, 'move': None}

        if move_action == 'P' and player.phase_charges == 0:
            move_action = player.direction

        if use_emp and player.emp_charges == 0:
            use_emp = False

        return {'valid': True, 'emp': use_emp, 'move': move_action}

    @staticmethod
    def action_points(parsed_action):
        """Return the per-turn movement points for a parsed action."""
        if parsed_action['move'] in ['+', 'P']:
            return 2
        return 1

    def kill_player(self, p):
        """Mark a player as dead."""
        if p.alive:
            p.alive = False
            p.death_tick = self.tick_count 

    def mark_for_death(self, players_to_be_killed, player, reason):
        """Track a pending death with a short reason for debugging."""
        players_to_be_killed.add(player)
        if player not in self.death_reasons:
            self.death_reasons[player] = f"tick {self.tick_count}: {reason}"

    def apply_end_game_bonuses(self):
        """Apply survival bonuses at end of game."""
        if self.bonuses_applied:
            return
        self.bonuses_applied = True
        stats = []
        for p in self.players:
            dt = p.death_tick if not p.alive else float('inf')
            stats.append({'player': p, 'dt': dt})
        # Sort by death_tick in DESCENDING order (survivors first/best)
        stats.sort(key=lambda x: x['dt'], reverse=True)
        # Bonus: 50 for survivor, 25 for 2nd, 10 for 3rd, 0 for 4th
        
        bonus_map = {0: 50, 1: 25, 2: 10, 3: 0}
        current_rank = 0
        for i in range(len(stats)):
            # If it's not the first player, and their death tick is lower than the previous player,
            # drop their rank to the current index (standard competition ranking).
            if i > 0 and stats[i]['dt'] < stats[i-1]['dt']:
                current_rank = i
                
            bonus = bonus_map.get(current_rank, 0)
            stats[i]['player'].score += bonus
            
            # Using (current_rank + 1) purely so your print statement reads naturally (Rank 1, 2, 3...)
            display_rank = current_rank + 1

    def check_game_over(self):
        """Check if the game should end (all players dead)."""
        alive_count = sum(1 for p in self.players if p.alive)
        return alive_count == 0

    def update(self):
        """Update game state for one tick."""
        if self.game_over:
            return
        self.tick_count += 1
        
        # 0. Update Timed Walls / EMPs / Explosions / Recharge Timers
        to_open = []
        for pos, turns in self.timed_walls.items():
            self.timed_walls[pos] -= 1
            remaining = self.timed_walls[pos]
            wx, wy = pos
            if remaining <= 0:
                to_open.append(pos)
                self.grid[wy][wx] = '.'
            else:
                strength = math.ceil(remaining / 10)
                self.grid[wy][wx] = int(strength) 
        for pos in to_open:
            del self.timed_walls[pos]
        
        detonated_emps = []
        still_active = []
        for emp in self.active_emps:
            emp['timer'] -= 1
            if emp['timer'] <= 0:
                detonated_emps.append(emp)
            else:
                still_active.append(emp)
        self.active_emps = still_active

        for emp in detonated_emps:
            ex, ey = emp['pos']
            owner_id = emp['owner_id']
            self.explosions.append(Explosion(ex, ey, EMP_RADIUS))
            owner = next((p for p in self.players if p.id == owner_id), None)
            hits = 0
            for p in self.players:
                if p.alive:
                    if p.id == owner_id:
                        continue 
                    px, py = p.pos
                    if max(abs(px - ex), abs(py - ey)) <= EMP_RADIUS:
                        p.loss_of_control_turns = EMP_STUN_DURATION
                        hits += 1
            # Award EMP points even if owner died (earned when EMP was placed)
            if owner:
                owner.score += hits * EMP_HIT_BONUS
        
        active_explosions = []
        for exp in self.explosions:
            exp.life -= 1
            if exp.life > 0:
                active_explosions.append(exp)
        self.explosions = active_explosions

        for p in self.players:
            if not p.alive:
                continue
            new_timers = []
            for t in p.recharge_timers:
                t -= 1
                if t <= 0:
                    p.emp_charges += 1
                else:
                    new_timers.append(t)
            p.recharge_timers = new_timers

        # 5. Get Intentions
        moves = {}
        for p in self.players:
            if not p.alive:
                continue
            if p.loss_of_control_turns > 0:
                moves[p] = p.direction
                p.loss_of_control_turns -= 1
            else:
                moves[p] = p.get_move(self.grid, self.players, self.active_emps)

            if moves[p] == 'TIMEOUT_DESTROY':
                self.kill_player(p)
                continue

            if self.tick_count % MEMORY_CHECK_INTERVAL_TICKS == 0 and p.exceeds_memory_limit():
                moves[p] = 'MEMORY_DESTROY'
                self.kill_player(p)
                continue

        self.log_turn(moves)

        # 6. Parse Actions and Determine Execution Steps
        final_actions = {}
        for p, raw_action in moves.items():
            if not p.alive:
                continue
            parsed_action = self.parse_action(p, raw_action)
            if not parsed_action['valid']:
                self.kill_player(p)
                final_actions[p] = {'valid': False, 'emp': False, 'move': None}
                continue
            final_actions[p] = parsed_action
            p.score += self.action_points(parsed_action)

        # 7. Execute Moves (Hybrid Serial Execution with Delayed Head Commit)
        players_to_be_killed = set() 
        temp_move_data = {} 
        
        for p, parsed_action in final_actions.items():
            if not p.alive or not parsed_action['valid']:
                continue

            # --- Steps Generation ---
            steps = []
            if parsed_action['emp']:
                p.emp_charges -= 1
                p.recharge_timers.append(EMP_DETONATION_TIME + EMP_COOLDOWN)
                self.active_emps.append({
                    'owner_id': p.id, 'pos': p.pos, 'timer': EMP_DETONATION_TIME
                })
            action = parsed_action['move']
            if action == 'P':
                p.phase_charges -= 1
                steps.append({'type': 'phase', 'dir': p.direction})
                steps.append({'type': 'normal', 'dir': p.direction})
            elif action == '+':
                steps.append({'type': 'normal', 'dir': p.direction})
                steps.append({'type': 'normal', 'dir': p.direction})
            elif action in self.dirs:
                p.direction = action
                steps.append({'type': 'normal', 'dir': action})

            current_pos = p.pos
            path_to_commit = [] 

            for step in steps:
                if p in players_to_be_killed:
                    break

                dx, dy = self.dirs[step['dir']]
                nx, ny = current_pos[0] + dx, current_pos[1] + dy
                
                # 1. Collision Check (Instant Death)
                if not self.is_valid(nx, ny):
                    self.mark_for_death(players_to_be_killed, p, f"out_of_bounds via {parsed_action}")
                    break
                
                cell = self.grid[ny][nx]
                
                if step['type'] != 'phase':
                    if cell == '#' or (isinstance(cell, int) and cell > 0):
                        self.mark_for_death(players_to_be_killed, p, f"blocked_cell {cell!r} at {(nx, ny)} via {parsed_action}")
                        break
                    if isinstance(cell, str) and cell.startswith('t'):
                        self.mark_for_death(players_to_be_killed, p, f"trail_collision {cell!r} at {(nx, ny)} via {parsed_action}")
                        break
                
                # 2. Item Collection & Clear
                if cell == 'c':
                    p.score += 20
                    self.grid[ny][nx] = '.'
                elif cell == 'D':
                    p.score += 50
                    self.grid[ny][nx] = '.'
                
                # 3. Record Path & Update Head
                path_to_commit.append(current_pos)
                current_pos = (nx, ny)
            
            if p not in players_to_be_killed:
                temp_move_data[p] = {'new_pos': current_pos, 'path': path_to_commit}

        # 8. Collision Resolution (Simultaneous Head-to-Head Check)
        head_map = {} 

        for p, data in temp_move_data.items():
            if p in players_to_be_killed:
                continue
            
            pos = data['new_pos']
            if pos in head_map:
                head_map[pos].append(p)
            else:
                head_map[pos] = [p]

        # Final Kill Sweep (Head-to-Head & Trail Commit)
        for pos, players_at_cell in head_map.items():
            
            # 1. Head-to-Head Collision Check (If > 1 player lands on same spot)
            if len(players_at_cell) > 1:
                for p in players_at_cell:
                    self.mark_for_death(players_to_be_killed, p, f"head_to_head at {pos}")
            
            # 2. Final Commit (If only one player landed there)
            else:
                p = players_at_cell[0]
                
                if p not in players_to_be_killed:
                    
                    # Commit all intermediate path points to the grid
                    for old_pos in temp_move_data[p]['path']:
                        self.grid[old_pos[1]][old_pos[0]] = f"t{p.id}"
                    
                    # Update player head position
                    p.pos = pos
        
        # 9. Final Kill Execution
        for p in players_to_be_killed:
            self.kill_player(p)

        # 10. Move EMP to follow the user
        still_active = []
        for emp in self.active_emps:
            emp["pos"] = None
            for p in self.players:
                if p.id == emp["owner_id"] and p.alive:
                    emp["pos"] = p.pos
            if emp["pos"]:
                still_active.append(emp)
        self.active_emps = still_active
        
        # 11. Check if game should end and apply bonuses
        if self.check_game_over():
            self.game_over = True
            self.apply_end_game_bonuses()
