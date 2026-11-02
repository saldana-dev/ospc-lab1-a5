# Measurements - anderk88

Laptop: Acer Aspire A315-44P, Windows 11 Home. AMD Ryzen 7 5700U: 8 cores,
16 threads. Container: 16 CPUs (`nproc`), memory limit 2 GiB
(`memory.max` = 2147483648), no swap.

All commands were run in the container, from the repository folder, with
`T='%e s elapsed, %U s user, %S s system, %M KB peak memory'`.

## 5.1 Warm-up

`./run_report.sh` ran on my laptop without `chmod +x`: the repository is in a
Windows folder, and Docker shows its files as executable.

## 5.2 Task 1: report.py

Whole pipeline, `./run_report.sh` (Tuesday): ran from 11:02:21 to 11:12:30.
`./run_report.sh: line 10: 53 Killed python3 steps/report.py`, but the script
went on and printed `Nightly report finished`.
`revenue_by_region_month.csv` was missing.

`python3 steps/report.py` alone: `Killed`, exit status 137.
`cat /sys/fs/cgroup/memory.events`: `max 1682`, `oom 2`, `oom_kill 2`.

### Before the fix

`head -n N+1 ~/data/sales_2025.csv > /tmp/orders_Nm.csv`, then
`DATA=/tmp/orders_Nm.csv OUT=/tmp /usr/bin/time -f "$T" python3 steps/report.py`

| Orders | Table size | Elapsed | User | System | Peak memory | Result |
|---|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | | | | 505,896 KB | done |
| 2,000,000 | 211 MiB | 20.28 s | 15.93 s | 5.20 s | 849,296 KB | done |
| 4,000,000 | 423 MiB | 28.69 s | 23.21 s | 6.48 s | 1,565,740 KB | done |
| 8,400,000 | 887 MiB | 59.02 s | 46.02 s | 14.00 s | 2,089,756 KB | killed by signal 9, exit 137 |

Peak memory grows by about 358 MB per million orders: the whole file would
need about 1,565,740 + 4.4 × 358,000 ≈ 3.1 GB, more than the 2 GiB limit.

`python3 steps/report.py | tee /tmp/report.log`: the log was empty.

### After the fix (read in chunks of 1 million orders)

`/usr/bin/time -f "$T" python3 steps/report.py`

| | Before | After |
|---|---|---|
| Result | killed, exit 137 | `report: done`, exit 0 |
| Elapsed | 59.02 s | 20.97 s |
| User / system | 46.02 s / 14.00 s | 19.53 s / 3.32 s |
| Peak memory | 2,089,756 KB | 381,848 KB |
| `tee` log | empty | both lines present |
| `tools/check.py` | revenue_by_region_month.csv missing | PASS |

## Worker sweep (stats step)

`bash tools/sweep.sh anderk88`, saved in `sweep.csv`.

| Workers | Run 1 | Run 2 | Run 3 | Average elapsed | User time |
|---|---|---|---|---|---|
| 1 | 229.45 s | 256.60 s | 167.52 s | 217.9 s | 135-179 s |
| 2 | 158.40 s | 122.09 s | 131.47 s | 137.3 s | 161-210 s |
| 4 | 100.61 s | 71.98 s | 72.81 s | 81.8 s | 199-278 s |
| 8 | 69.62 s | 65.50 s | 62.84 s | 66.0 s | 356-377 s |
| 16 | 71.78 s | 74.32 s | 74.34 s | 73.5 s | 749-839 s |

Fastest with 8 workers (66.0 s), the number of physical cores. With 16
workers, one per thread, it is slower (73.5 s) and the user time doubles
(about 800 s instead of about 370 s): two threads of the same core share
its execution units, so the extra workers add CPU time without making the
step faster.

Claude helped me with the formating and doing the sweep