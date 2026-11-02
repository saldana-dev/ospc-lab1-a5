# Measurements (tpovedanoieu2024-hue)

## Task 3 (audit.py) — sample file (100,000 orders)

Commands:
- export DATA=~/data/sales_2025_sample.csv
- T='%e s elapsed, %U s user, %S s system, %M KB peak memory'
- /usr/bin/time -f "$T" python3 steps/audit.py
- strace -c -e trace=openat,write,close python3 steps/audit.py

Before (old version: open/close inside loop):
- time: 2.18 s elapsed, 3.28 s user, 0.64 s system, 135704 KB peak memory
- strace: openat 100689 (17 errors), write 100001 (17 errors), close 100677

After (fixed: open once, write all lines through one handle):
- time: 0.66 s elapsed, 2.30 s user, 0.11 s system, 135488 KB peak memory
- strace: openat 689 (17 errors), write 17, close 677
