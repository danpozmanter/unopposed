#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if [ -z "$1" ]; then
    echo "Usage: ./run_scraper_locally.sh <year> [year2] [year3] ..."
    echo "       ./run_scraper_locally.sh <state> <year>"
    echo "Example: ./run_scraper_locally.sh 2026"
    echo "Example: ./run_scraper_locally.sh 2025 2026"
    echo "Example: ./run_scraper_locally.sh MA 2026"
    exit 1
fi

ALL_STATES="AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"

if [[ "$1" =~ ^[A-Z]{2}$ ]] && [[ " $ALL_STATES " == *" $1 "* ]]; then
    STATES="$1"
    YEARS="$2"
    SINGLE_STATE=true
else
    STATES="$ALL_STATES"
    YEARS="$@"
    SINGLE_STATE=false
fi

declare -A STATE_NAMES=(
    ["AL"]="alabama" ["AK"]="alaska" ["AZ"]="arizona" ["AR"]="arkansas"
    ["CA"]="california" ["CO"]="colorado" ["CT"]="connecticut" ["DE"]="delaware"
    ["FL"]="florida" ["GA"]="georgia" ["HI"]="hawaii" ["ID"]="idaho"
    ["IL"]="illinois" ["IN"]="indiana" ["IA"]="iowa" ["KS"]="kansas"
    ["KY"]="kentucky" ["LA"]="louisiana" ["ME"]="maine" ["MD"]="maryland"
    ["MA"]="massachusetts" ["MI"]="michigan" ["MN"]="minnesota" ["MS"]="mississippi"
    ["MO"]="missouri" ["MT"]="montana" ["NE"]="nebraska" ["NV"]="nevada"
    ["NH"]="new_hampshire" ["NJ"]="new_jersey" ["NM"]="new_mexico" ["NY"]="new_york"
    ["NC"]="north_carolina" ["ND"]="north_dakota" ["OH"]="ohio" ["OK"]="oklahoma"
    ["OR"]="oregon" ["PA"]="pennsylvania" ["RI"]="rhode_island" ["SC"]="south_carolina"
    ["SD"]="south_dakota" ["TN"]="tennessee" ["TX"]="texas" ["UT"]="utah"
    ["VT"]="vermont" ["VA"]="virginia" ["WA"]="washington" ["WV"]="west_virginia"
    ["WI"]="wisconsin" ["WY"]="wyoming" ["DC"]="district_of_columbia"
)

echo "=========================================="
echo "Local Election Data Scraper"
echo "=========================================="
echo "Years: $YEARS"
if [ "$SINGLE_STATE" = true ]; then
    echo "State: $STATES"
else
    echo "States: 51 (all US states + DC)"
fi
echo "=========================================="
echo ""

(cd scraper && uv sync)
mkdir -p election_data

TOTAL_STATES=$(echo $STATES | wc -w)

FIRST_YEAR=true
for YEAR in $YEARS; do
    if [ "$FIRST_YEAR" = false ] && [ "$SINGLE_STATE" = false ]; then
        echo ""
        echo "Waiting 1 minute before next year..."
        sleep 60
    fi
    FIRST_YEAR=false

    echo ""
    echo "=== Scraping $YEAR ==="
    STATE_COUNT=0
    for STATE in $STATES; do
        STATE_COUNT=$((STATE_COUNT + 1))
        STATE_NAME="${STATE_NAMES[$STATE]}"
        OUTPUT_FILE="election_data/${STATE_NAME}_${YEAR}.json"

        if [ "$SINGLE_STATE" = true ]; then
            echo "$STATE ($STATE_NAME) $YEAR..."
        else
            echo "[$STATE_COUNT/$TOTAL_STATES] $STATE ($STATE_NAME) $YEAR..."
        fi

        TEMP_FILE=$(mktemp)
        if (cd scraper && uv run python main.py "$STATE" "$YEAR" --json) > "$TEMP_FILE" 2>/dev/null; then
            if grep -q '"error"' "$TEMP_FILE" 2>/dev/null; then
                echo "  -> Scrape error, keeping existing data"
                mkdir -p election_data/errors
                mv "$TEMP_FILE" "election_data/errors/${STATE_NAME}_${YEAR}_error.json"
            else
                mv "$TEMP_FILE" "$OUTPUT_FILE"
                echo "  -> $OUTPUT_FILE"
            fi
        else
            echo "  -> Failed, keeping existing data"
            rm -f "$TEMP_FILE"
        fi

        [ $STATE_COUNT -lt $TOTAL_STATES ] && sleep 10
    done
done

echo ""
echo "Generating manifest with nationwide stats..."
(cd scraper && uv run python nationwide_stats.py)

echo ""
echo "=========================================="
echo "Done! Available years: $YEARS_FOUND"
echo "=========================================="
