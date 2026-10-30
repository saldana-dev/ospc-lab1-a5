# Measurements - DMARCOS

Laptop: Apple MacBook Air M2 2022, macOS 26.4.1. Container: 8 CPUs (`nproc`),
memory limit 2 GiB (`memory.max` = 2147483648).

All commands were run in the container, from the repository folder, with
`T='%e s elapsed, %U s user, %S s system, %M KB peak memory'`.

## 5.1 Warm-up

`ls -l run_report.sh` → `-rwxr-xr-x` (the teammate's `chmod +x` fix was
already pulled, so `./run_report.sh` ran).

## 5.2 Task 1: Generating the report

Whole pipeline, `/usr/bin/time -f "$T" ./run_report.sh`:

- `./run_report.sh: line 10: 47 Killed python3 steps/report.py`
- 84.52 s elapsed, 111.29 s user, 20.76 s system, 2086728 KB peak memory
- The script still exited 0. `revenue_by_region_month.csv` is missing and the six
  files in `extracts/` are empty (0 bytes).

`python3 steps/report.py` alone: exit status **137**. `memory.events` before → after:

| Counter | Before | After |
|---|---|---|
| max | 0 | 4540 |
| oom | 0 | 2 |
| oom_kill | 0 | 2 |

| Orders | Table size | Elapsed | User | System | Peak memory |
|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | 1.89 s | 2.06 s | 0.20 s | 511768 KB |
| 2,000,000 | 211 MiB | 3.04 s | 3.35 s | 0.30 s | 858260 KB |
| 4,000,000 | 423 MiB | 5.95 s | 5.89 s | 0.66 s | 1565880 KB |
| 8,400,000 | ~890 MiB (extrapolated) | killed | | | ~3.1 GB (extrapolated) > 2 GiB limit |

Peak memory grows by about 350 MB per million orders, so the whole file would
need about 3.1 GB.

`python3 steps/report.py | tee /tmp/report.log`: `PIPESTATUS 137 0`, and the
log is empty. The `report: loaded ...` line stayed in Python's stdout buffer
(it is a pipe, not a terminal) and was lost when the process was killed.

## 5.3 Task 2: Extracting data

`/usr/bin/time -f "$T" bash steps/extracts.sh`: `extracts: done`, exit status 0,
0.01 s elapsed, 0.00 s user, 0.00 s system, 6376 KB peak memory. All six files
are 0 bytes.

Pipeline by hand, from `~/data/out/extracts`, without `2>/dev/null`:

```
grep: ../data/sales_2025.csv: No such file or directory
0
PIPESTATUS 2 0 0
/home/analyst/data/out/extracts
```

## 5.4 Task 3: Auditing

| Input | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| Sample (100,000 orders) | 1.14 s | 1.27 s | 0.26 s | 127500 KB |
| Whole file (8.4 million) | 54.21 s | 38.56 s | 16.25 s | 634252 KB |

On the whole file, system time is 16.25 / (38.56 + 16.25) ≈ 30% of the CPU time.

`strace -c -e trace=openat,write,close` on the sample:

| Syscall | Calls | Errors |
|---|---|---|
| openat | 100686 | 13 |
| write | 100001 | |
| close | 100673 | |
| total | 301360 | 13 |

`audit_2025.csv` for the sample: 1952269 bytes. With one open file and a
128 KiB buffer, that is about 1952269 / 131072 ≈ 15 `write` calls.

## Worker sweep (stats step)

Saved in `sweep.csv`. Elapsed time in seconds:

| Workers | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| 1 | 34.28 | 195.27* | 32.93 |
| 2 | 17.39 | 17.01 | 17.09 |
| 4 | 9.16 | 11.72 | 9.26 |
| 8 | 6.98 | 10.21 | 6.92 |
| 16 | 9.63 | 10.48 | 8.06 |

\* The user time of that run was 34.85 s, the same as the other 1-worker runs.
The extra elapsed time was spent waiting rather than computing (the laptop
was probably busy or asleep), so it is an outlier.

Up to 8 workers (the container's 8 CPUs) the elapsed time drops. With 16 it
goes up again, and user time grows from about 35 s to 58–74 s, because 16
processes compete for 8 cores.
