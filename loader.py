import os
import copy
import importlib.util


class MapValidationError(Exception):
    """Exception raised when a map file is invalid."""
    pass


def validate_map(filename, map_folder='maps'):
    """
    Validate a map file and return a list of errors (empty if valid).
    
    Valid characters:
        '.' - empty space
        '#' - wall
        'S' - spawn point
        'c' - coin
        'D' - diamond
        '1'-'9' - timed walls (disappear after N*10 turns)
    
    Map formats:
        - Quarter map (1 spawn): Will be mirrored to create full 4-player map
        - Full map (4 spawns): Used as-is, players ordered top-left to bottom-right
    
    Requirements:
        - All rows must have the same length
        - Must have at least 1 row and 1 column
        - Must have exactly 1 or 4 spawn points 'S'
        - Only valid characters allowed
    """
    errors = []
    filepath = os.path.join(map_folder, filename)
    
    if not os.path.exists(filepath):
        return [f"Map file '{filename}' does not exist"]
    
    try:
        with open(filepath, 'r') as f:
            lines = [line.rstrip('\n\r') for line in f]
    except Exception as e:
        return [f"Failed to read map file: {e}"]
    
    # Remove empty lines at end but preserve internal structure
    while lines and not lines[-1].strip():
        lines.pop()
    
    if not lines:
        return [f"Map file '{filename}' is empty"]
    
    # Check for consistent row lengths
    row_lengths = [len(line) for line in lines]
    if len(set(row_lengths)) > 1:
        errors.append(f"Inconsistent row lengths: {row_lengths}")
    
    if row_lengths and row_lengths[0] == 0:
        errors.append("Map has zero width")
    
    # Valid characters
    valid_chars = set('.#ScD0123456789')
    
    spawn_count = 0
    invalid_chars = set()
    
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char == 'S':
                spawn_count += 1
            if char not in valid_chars:
                invalid_chars.add(char)
    
    if invalid_chars:
        errors.append(f"Invalid characters found: {invalid_chars}")
    
    if spawn_count == 0:
        errors.append("No spawn point 'S' found (need exactly 1 for quarter map or 4 for full map)")
    elif spawn_count not in [1, 4]:
        errors.append(f"Invalid spawn count: {spawn_count} (need exactly 1 for quarter map or 4 for full map)")
    
    return errors


def get_spawn_count(filename, map_folder='maps'):
    """Get the number of spawn points in a map file."""
    filepath = os.path.join(map_folder, filename)
    spawn_count = 0
    try:
        with open(filepath, 'r') as f:
            for line in f:
                spawn_count += line.count('S')
    except:
        pass
    return spawn_count


def validate_all_maps(map_folder='maps'):
    """
    Validate all maps in the folder and return a dict of {filename: [errors]}.
    Only includes maps with errors.
    """
    results = {}
    maps = load_maps(map_folder)
    for map_file in maps:
        errors = validate_map(map_file, map_folder)
        if errors:
            results[map_file] = errors
    return results


def load_bot_classes(bot_folder='bots', compiled_folder='compiled_bots', use_source=False):
    """
    Load all bot classes from the bots and compiled_bots folders.
    
    Args:
        bot_folder: Folder containing source .py files
        compiled_folder: Folder containing compiled .so/.pyd files
        use_source: If True, only load from bot_folder (.py files), skip compiled_folder
    
    By default, checks compiled_bots/ first (compiled .so/.pyd), then bots/ (.py or .so/.pyd).
    With use_source=True, only loads from bots/ (.py files).
    """
    bots = {}
    if not os.path.exists(bot_folder):
        os.makedirs(bot_folder)
    
    # Track which bot names we've loaded (to avoid loading both .py and .so)
    loaded_names = set()
    
    # First, check compiled_bots folder for compiled extensions (unless use_source is True)
    if not use_source and os.path.exists(compiled_folder):
        for file in os.listdir(compiled_folder):
            if '.cpython-' in file and (file.endswith('.so') or file.endswith('.pyd')):
                name = file.split('.')[0]
                if name in loaded_names:
                    continue
                path = os.path.join(compiled_folder, file)
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                    if hasattr(module, 'Bot'):
                        bots[name] = module.Bot
                        loaded_names.add(name)
                except Exception as e:
                    print(f"Failed to load {file}: {e}")
    
    for file in os.listdir(bot_folder):
        # Skip helper files
        if file.startswith('_') or file.startswith('compile'):
            continue
            
        # Check for Python source files
        if file.endswith('.py'):
            name = file[:-3]
            if name in loaded_names:
                continue
            path = os.path.join(bot_folder, file)
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                if hasattr(module, 'Bot'):
                    bots[name] = module.Bot
                    loaded_names.add(name)
            except Exception as e:
                print(f"Failed to load {file}: {e}")
        
        # Check for compiled extensions (.so on Mac/Linux, .pyd on Windows) unless use_source is True
        elif not use_source and '.cpython-' in file and (file.endswith('.so') or file.endswith('.pyd')):
            # Extract bot name from e.g. "zone_keeper.cpython-311-darwin.so"
            name = file.split('.')[0]
            if name in loaded_names:
                continue
            path = os.path.join(bot_folder, file)
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                if hasattr(module, 'Bot'):
                    bots[name] = module.Bot
                    loaded_names.add(name)
            except Exception as e:
                print(f"Failed to load {file}: {e}")
    
    return bots


def load_maps(map_folder='maps', validate=True):
    """
    Load all map files from the maps folder.
    
    Args:
        map_folder: Path to the maps folder
        validate: If True, only return valid maps and print errors for invalid ones
    
    Returns:
        List of valid map filenames
    """
    if not os.path.exists(map_folder):
        os.makedirs(map_folder)
        with open(os.path.join(map_folder, 'default.txt'), 'w') as f:
            f.write("........\n..###...\n..#..1..\n..#..c..\n..S..D..\n........")
    
    all_maps = []
    for file in os.listdir(map_folder):
        if file.endswith('.txt'):
            all_maps.append(file)
    
    if not validate:
        return all_maps
    
    # Validate maps and filter out invalid ones
    valid_maps = []
    for map_file in all_maps:
        errors = validate_map(map_file, map_folder)
        if errors:
            print(f"[WARNING] Invalid map '{map_file}':")
            for error in errors:
                print(f"  - {error}")
        else:
            valid_maps.append(map_file)
    
    return valid_maps


def build_full_map(filename, map_folder='maps'):
    """
    Build a game map from a map file.
    
    Supports two formats:
        - Quarter map (1 spawn 'S'): Mirrored 4 ways to create full symmetric map
        - Full map (4 spawns 'S'): Used as-is, no mirroring
    
    Raises:
        MapValidationError: If the map file is invalid
    """
    # Validate first
    errors = validate_map(filename, map_folder)
    if errors:
        error_msg = f"Invalid map '{filename}':\n" + "\n".join(f"  - {e}" for e in errors)
        raise MapValidationError(error_msg)
    
    spawn_count = get_spawn_count(filename, map_folder)
    
    with open(os.path.join(map_folder, filename), 'r') as f:
        grid = [list(line.strip()) for line in f if line.strip()]
    
    if spawn_count == 4:
        # Full map mode - use as-is
        return grid
    else:
        # Quarter map mode - mirror to create full map
        q1 = grid
        q2 = [row[::-1] for row in q1]
        q3 = copy.deepcopy(q1[::-1])
        q4 = copy.deepcopy(q2[::-1])
        top_half = []
        for r1, r2 in zip(q1, q2):
            top_half.append(r1 + r2)
        bottom_half = []
        for r3, r4 in zip(q3, q4):
            bottom_half.append(r3 + r4)
        return top_half + bottom_half


def get_map_choices():
    """Get list of available maps for menu selection."""
    maps = load_maps()
    if not maps:
        return [('No Maps Found', 'default.txt')]
    # Sort maps by name for more predictable menu ordering
    maps.sort(key=lambda s: s.lower())
    return [(m, m) for m in maps]


def get_bot_choices(use_source=False):
    """Get list of available bots for menu selection."""
    bots = load_bot_classes(use_source=use_source)
    bot_names = list(bots.keys())
    if not bot_names:
        return [('No Bots', None)]
    return [(name, name) for name in bot_names]
