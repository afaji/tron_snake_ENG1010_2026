#!/bin/bash

# ==========================================
# CONFIGURATION
# ==========================================
# Use the first argument provided, or default to "Scout"
MY_BOT="${1:-"Scout"}"
RUN_CMD="python runner.py"
MAX_TICKS=10000

# ==========================================
# PARSER FUNCTION
# ==========================================
parse_result() {
    local raw_output="$1"
    
    # Targets ONLY the lines after "RANKINGS:"
    # Looks for your bot exactly in column 3, then prints Column 1 (Rank) and Column 4 (Score)
    echo "$raw_output" | grep -A 10 "RANKINGS:" | awk -v bot="$MY_BOT" '$3 == bot {print $1, $4; exit}'
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================
get_points() {
    local rank=$1
    local is_duel=$2

    if [[ "$is_duel" == "true" ]]; then
        # Duel rule: Win gives 100, 2nd gives 0
        if [[ "$rank" -eq 1 ]]; then echo 100; else echo 0; fi
    else
        # Standard rules (Updated 2nd place to 50 pts)
        case "$rank" in
            1) echo 100 ;;
            2) echo 50 ;;
            3) echo 25 ;;
            *) echo 0 ;;
        esac
    fi
}

run_match() {
    local map_name=$1
    local b1=$2
    local b2=$3
    local b3=$4
    local b4=$5
    local is_duel=$6

    # Run the python script
    local output=$($RUN_CMD -m "${map_name}.txt" -b "$b1" "$b2" "$b3" "$b4" --max-ticks $MAX_TICKS)
    
    # Parse the rank and game score
    local result=$(parse_result "$output")
    local rank=$(echo "$result" | awk '{print $1}')
    local game_score=$(echo "$result" | awk '{print $2}')
    
    # If parsing completely fails, default to rank 4
    if [[ -z "$rank" ]]; then
        rank=4
        game_score="N/A"
    fi

    local points=$(get_points "$rank" "$is_duel")
    
    # Print debug info to stderr
    echo -e "  -> Map: ${map_name}.txt | Bots: $b1, $b2, $b3, $b4" >&2
    echo -e "     [Result] Rank: $rank | Game Score: $game_score | Points Awarded: $points\n" >&2
    
    # Return points to stdout for the math addition
    echo "$points"
}

# ==========================================
# MAIN EXECUTION
# ==========================================

echo "==========================================="
echo "   STARTING BOT EVALUATION FOR: $MY_BOT"
echo "==========================================="

# --- 1. SOLO PLAYER (10 Points Total) ---
echo -e "\n--- Running Solo Player Scenarios ---"
# Added s_choice_3
SOLO_MAPS=("s_path_0" "s_path_1" "s_path_2"  "s_path_3" "s_floodfill_0" "s_floodfill_1" "s_floodfill_2" "s_choice_0" "s_choice_1" "s_choice_2")
SOLO_SCORE=0
SOLO_MAX=1000 # 10 maps * 100 max points

for map in "${SOLO_MAPS[@]}"; do
    pts=$(run_match "$map" "$MY_BOT" "Drunk" "Drunk" "Drunk" "false")
    SOLO_SCORE=$((SOLO_SCORE + pts))
done

# --- 2. DUEL (30 Points Total) ---
echo -e "\n--- Running Duel Scenarios ---"
# Added cube, swapped Drunk for Blaze
DUEL_MAPS=("arena" "maze" "treasure" "gate" "cube" "orbit")
DUEL_BOTS=("Scout" "Rogue" "Stingray" "Viper" "Blaze")
DUEL_SCORE=0
DUEL_MAX=6000 # 6 maps * 5 bots * 2 positions * 100 max points

for map in "${DUEL_MAPS[@]}"; do
    for opp in "${DUEL_BOTS[@]}"; do
        # Position 1
        pts1=$(run_match "$map" "$MY_BOT" "Dummy" "Dummy" "$opp" "true")
        DUEL_SCORE=$((DUEL_SCORE + pts1))
        # Position 4
        pts2=$(run_match "$map" "$opp" "Dummy" "Dummy" "$MY_BOT" "true")
        DUEL_SCORE=$((DUEL_SCORE + pts2))
    done
done

# --- 3. BATTLE ROYALE (15 Points Total) ---
echo -e "\n--- Running Battle Royale Scenarios ---"
BR_SCORE=0
BR_MAX=1500 # 15 matches * 100 max points

# Map | Bot1 | Bot2 | Bot3 | Bot4
while read -r map b1 b2 b3 b4; do
    [ -z "$map" ] && continue 
    pts=$(run_match "$map" "$b1" "$b2" "$b3" "$b4" "false")
    BR_SCORE=$((BR_SCORE + pts))
done << EOF
arena $MY_BOT Scout Stingray Blaze
arena $MY_BOT Rogue Viper Stingray
arena $MY_BOT Rogue Viper Blaze
treasure $MY_BOT Rogue Stingray Stingray
treasure $MY_BOT Viper Viper Rogue
treasure $MY_BOT Rogue Scout Blaze
maze $MY_BOT Rogue Rogue Scout
maze $MY_BOT Viper Rogue Rogue
gate $MY_BOT Stingray Stingray Blaze
gate $MY_BOT Viper Stingray Scout
cube $MY_BOT Stingray Stingray Blaze
cube $MY_BOT Viper Stingray Scout
cube $MY_BOT Viper Blaze Blaze
orbit $MY_BOT Rogue Rogue Viper
orbit $MY_BOT Blaze Viper Scout
EOF

# ==========================================
# FINAL CALCULATIONS
# ==========================================
echo "==========================================="
echo "               FINAL RESULTS                 "
echo "==========================================="

# Updated weights to 10, 25, 15
SOLO_WEIGHTED=$(awk "BEGIN {printf \"%.2f\", ($SOLO_SCORE / $SOLO_MAX) * 10}")
DUEL_WEIGHTED=$(awk "BEGIN {printf \"%.2f\", ($DUEL_SCORE / $DUEL_MAX) * 30}")
BR_WEIGHTED=$(awk "BEGIN {printf \"%.2f\", ($BR_SCORE / $BR_MAX) * 15}")
TOTAL_WEIGHTED=$(awk "BEGIN {printf \"%.2f\", $SOLO_WEIGHTED + $DUEL_WEIGHTED + $BR_WEIGHTED}")

echo "Solo Score:          $SOLO_SCORE / $SOLO_MAX points ($SOLO_WEIGHTED / 10.00 wt)"
echo "Duel Score:          $DUEL_SCORE / $DUEL_MAX points ($DUEL_WEIGHTED / 30.00 wt)"
echo "Battle Royale Score: $BR_SCORE / $BR_MAX points ($BR_WEIGHTED / 15.00 wt)"
echo "-------------------------------------------"
echo "TOTAL AUTOMATED SCORE:   $TOTAL_WEIGHTED / 55.00"
echo "==========================================="
