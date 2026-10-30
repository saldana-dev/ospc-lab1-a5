#!/bin/bash
# Extract the orders of each region to a separate file.

DATA=${DATA:-~/data/sales_2025.csv}
OUT=${OUT:-~/data/out}

mkdir -p "$OUT/extracts"
cd "$OUT/extracts"

for region in Benelux DACH France Iberia Italy Nordics; do
    grep ",$region," "$DATA" | cut -d, -f1,2,4,6,7 > "$region.csv"
done

echo "extracts: done"
