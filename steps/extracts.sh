#!/bin/bash
# One file per region for the regional managers, with the columns
# order_id, order_date, product_category, quantity, unit_price.

# Stop at the first failing command, unset variable, or failing stage of a pipe
set -euo pipefail

DATA=${DATA:-$HOME/data/sales_2025.csv}
OUT=${OUT:-$HOME/data/out}
mkdir -p "$OUT/extracts"
for region in Iberia DACH France Italy Benelux Nordics; do
    grep ",$region," "$DATA" | cut -d, -f1,2,4,6,7 > "$OUT/extracts/$region.csv"
done
echo "extracts: done"
