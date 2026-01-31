#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

if [ -z "$1" ]; then
    echo "Usage: ./run_scrape_locally.sh <year> [year2] [year3] ..."
    echo "Example: ./run_scrape_locally.sh 2026"
    echo "Example: ./run_scrape_locally.sh 2025 2026"
    exit 1
fi

YEARS="$@"

STATES="AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"

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
echo "States: 51 (all US states + DC)"
echo "=========================================="
echo ""

(cd scraper && uv sync)
mkdir -p election_data

FIRST_YEAR=true
for YEAR in $YEARS; do
    if [ "$FIRST_YEAR" = false ]; then
        echo ""
        echo "Waiting 5 minutes before next year..."
        sleep 300
    fi
    FIRST_YEAR=false

    echo ""
    echo "=== Scraping $YEAR ==="
    STATE_COUNT=0
    for STATE in $STATES; do
        STATE_COUNT=$((STATE_COUNT + 1))
        STATE_NAME="${STATE_NAMES[$STATE]}"
        OUTPUT_FILE="election_data/${STATE_NAME}_${YEAR}.json"

        echo "[$STATE_COUNT/51] $STATE ($STATE_NAME) $YEAR..."

        if (cd scraper && uv run python main.py "$STATE" "$YEAR" --json) > "$OUTPUT_FILE" 2>/dev/null; then
            echo "  -> $OUTPUT_FILE"
        else
            echo "  -> Failed"
            rm -f "$OUTPUT_FILE"
        fi

        [ $STATE_COUNT -lt 51 ] && sleep 10
    done
done

echo ""
echo "Updating manifest..."
YEARS_FOUND=$(ls election_data/*.json 2>/dev/null | grep -oE '_[0-9]{4}\.json' | grep -oE '[0-9]{4}' | sort -u | tr '\n' ',' | sed 's/,$//')
cat > election_data/manifest.json << EOF
{
  "years": [$YEARS_FOUND],
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo ""
echo "=========================================="
echo "Done! Available years: $YEARS_FOUND"
echo "=========================================="
