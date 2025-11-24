#!/bin/bash
#
# Example setup script for STDF watchdog ingestion
# This script demonstrates how to setup and test the watchdog ingestion system
#

set -e  # Exit on error

echo "STDF Watchdog Ingestion - Example Setup"
echo "========================================"
echo ""

# Configuration
BASE_PATH="${1:-/tmp/stdf-ingestion-demo}"  # Use /tmp for demo, override with $1
CLICKHOUSE_HOST="${2:-localhost}"
CLICKHOUSE_PORT="${3:-9000}"

echo "Configuration:"
echo "  Base Path:       $BASE_PATH"
echo "  ClickHouse Host: $CLICKHOUSE_HOST"
echo "  ClickHouse Port: $CLICKHOUSE_PORT"
echo ""

# Step 1: Create directory structure
echo "Step 1: Creating directory structure..."
python3 setup_ingestion_dirs.py \
    --base-path "$BASE_PATH" \
    --facilities OSBE25 OSBE26 \
    --lots KEWGBCLD1U LOT002 \
    --products BE_HRG3301Y.06 PRODUCT_B \
    --programs Prod_TPP202_03 TEST_V2

echo ""
echo "Step 2: Directory structure created:"
tree -L 5 "$BASE_PATH" 2>/dev/null || find "$BASE_PATH" -type d | head -20

echo ""
echo "Step 3: Example file placement"
echo "To test the system, copy STDF files to incoming directory:"
echo ""
echo "  cp your_file.stdf \\"
echo "     $BASE_PATH/incoming/OSBE25/KEWGBCLD1U/BE_HRG3301Y.06/Prod_TPP202_03/"
echo ""

# Check if we have example STDF files
if [ -d "STDF_Files" ]; then
    EXAMPLE_FILE=$(find STDF_Files -name "*.stdf" -type f | head -1)
    if [ -n "$EXAMPLE_FILE" ]; then
        echo "Found example STDF file: $EXAMPLE_FILE"
        echo "Copying to incoming directory..."

        DEST_DIR="$BASE_PATH/incoming/OSBE25/KEWGBCLD1U/BE_HRG3301Y.06/Prod_TPP202_03"
        cp "$EXAMPLE_FILE" "$DEST_DIR/"

        echo "✓ Example file copied to: $DEST_DIR/$(basename $EXAMPLE_FILE)"
        echo ""
    fi
fi

echo "Step 4: Start watchdog service"
echo "Run the following command to start monitoring:"
echo ""
echo "  python3 watchdog_ingestion.py \\"
echo "      --base-path $BASE_PATH \\"
echo "      --clickhouse-host $CLICKHOUSE_HOST \\"
echo "      --clickhouse-port $CLICKHOUSE_PORT \\"
echo "      --log-level INFO"
echo ""

echo "Step 5: Monitor processing"
echo "Watch logs in real-time:"
echo "  tail -f stdf_ingestion.log"
echo ""

echo "Step 6: Check status"
echo "Count files in each directory:"
echo "  find $BASE_PATH/incoming -name '*.stdf' | wc -l    # Waiting to process"
echo "  find $BASE_PATH/processing -name '*.stdf' | wc -l  # Currently processing"
echo "  find $BASE_PATH/processed -name '*.stdf' | wc -l   # Successfully processed"
echo "  find $BASE_PATH/failed -name '*.stdf' | wc -l      # Failed processing"
echo ""

echo "========================================"
echo "Setup complete!"
echo ""
echo "Quick start command:"
echo "  python3 watchdog_ingestion.py --base-path $BASE_PATH"
echo ""
