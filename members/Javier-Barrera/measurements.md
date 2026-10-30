# Measurements – Javier-Barrera

## Laptop
| | |
|---|---|
| Machine | ASUS Vivobook S 15 (S5507QA), Windows 11 ARM |
| Processor | Snapdragon X Plus X1P42100, 8 cores, 8 threads |
| CPUs in the container (`nproc`) | 8 |
| Memory seen in the container (`free -h`) | 7.5 Gi (the whole Docker VM, not the limit) |
| Container memory limit | 2 GB, no swap (cgroup `memory.max`) |

## Dataset
| File | Orders | Size |
|---|---|---|
| `sales_2025.csv` | 8,400,000 | 498 MB |
| `sales_2025_sample.csv` | 100,000 | 5.8 MB |

## Baseline: `tools/check.py` before any fix
| Output | Result |
|---|---|
| `revenue_by_region_month.csv` | missing |
| `extracts/*.csv` | 0 rows each (expected 839,987 to 2,183,057 per region) |
| `audit_2025.csv` | 100,000 lines (sample run), expected 8,400,000 |
| `segments.csv` | missing |
| `stats.csv` | missing |

---

## 5.1 Warm-up: Generating the Report
- `ls -l run_report.sh`: `-rwxrwxrwx root root`
- `./run_report.sh` ran on my laptop, no "Permission denied".

**Q1. Which permission is missing, and for whom?**
Execute (`x`), for owner, group and others. Git stored the file as `100644` (not executable). *To confirm with a Mac teammate's `ls -l`.*

**Q2. Why does `bash run_report.sh` work?**
Then `bash` is the program being run; it only needs to *read* the file, not execute it.

**Q3. Did the same happen on every laptop?**
No. My repo is in a Windows folder: Windows has no Linux permissions, so Docker shows every file as `rwxrwxrwx`. On a Mac the file keeps its real mode (`-rw-r--r--`), so `./run_report.sh` fails with "Permission denied". *To confirm with a Mac teammate.*

**Fix (done by me, commit `d1476ae`)**
`chmod +x run_report.sh` (container) + `git update-index --chmod=+x run_report.sh` (Windows git does not see file modes). Commit showed `mode change 100644 => 100755`.

---

## 5.2 Task 1: Generating the Report… Again

### Full pipeline, timed
`/usr/bin/time -f "$T" ./run_report.sh`
- 324.10 s elapsed, 406.22 s user, 181.16 s system, 2,089,892 KB peak memory
- user + system (587 s) > elapsed → several CPUs in parallel (stats workers)
- `report.py` was killed, but the script continued and printed "finished"
- stats used 16 workers on a container with 8 CPUs

### Outputs vs README
| Output | Result |
|---|---|
| `revenue_by_region_month.csv` | **missing**: `report.py` killed before writing it |
| `extracts/*.csv` | 6 files, all **0 bytes** (Task 2) |
| `audit_2025.csv` | OK, 180 MB, 8.4M lines |
| `segments.csv` | OK |
| `stats.csv` | OK |

### `report.py` alone
- 16.24 s elapsed, 12.64 s user, 3.40 s system, 2,090,008 KB peak memory
- Printed "Killed"; exit status **137**
- `memory.events`: `max 83832`, `oom 6`, `oom_kill 6`

### Memory growth
| Orders | Table size | Peak memory | Result |
|---|---|---|---|
| 1,000,000 | 106 MiB | 503,492 KB (~492 MiB) | OK, 7.25 s |
| 2,000,000 | 211 MiB | 856,560 KB (~836 MiB) | OK, 10.28 s |
| 4,000,000 | 423 MiB | 1,567,288 KB (~1.5 GiB) | OK, 17.97 s |
| 8,400,000 | 887 MiB | ~2 GB at the limit | **Killed** |

Memory grows ~350 MB per million orders + ~150 MB fixed (Python itself).

### With `tee`
`python3 steps/report.py | tee /tmp/report.log`: nothing on screen, log empty, no "Killed" message.

### Answers
**Q1.** 137 = 128 + 9 → signal 9 (SIGKILL). Sent by the kernel's out-of-memory killer when the container hit 2 GB. Confirmed by `oom_kill` in `memory.events`.

**Q2.** 887 MiB is only the raw data. Python wraps each value in an object with extra information, so the program needs ~3.5–5× more memory than the table size.

**Q3.** See the table. The whole file would need about **3 GB** (150 MB + 8.4 × 350 MB), more than the 2 GB limit.

**Q4.** Output into a pipe is buffered, not written line by line. SIGKILL ended Python before it flushed the buffer, so the line was lost. The shell reports the status of `tee` (the last command, OK), which hides the failure.

---

## 5.3 Task 2: Extracting Data

### Run
- `bash steps/extracts.sh` → "extracts: done"
- `echo $?` → 0 (success)
- `ls -l ~/data/out/extracts` → 6 files (Benelux, DACH, France, Iberia, Italy, Nordics), all 0 bytes

### The script (`less steps/extracts.sh`)
- `cd` into `~/data/out/extracts`, then for each region:
  `grep ",REGION," ../data/sales_2025.csv 2>/dev/null | cut ... > REGION.csv`
- The path is relative to the folder it moved into
- grep's errors are thrown away (`2>/dev/null`)
- Always prints "extracts: done"; does not use the `DATA` variable

### Pipeline by hand (from `~/data/out/extracts`)
| Command | Result |
|---|---|
| `grep ",Iberia," ../data/sales_2025.csv \| cut ... \| wc -l` | `No such file or directory`, 0 lines |
| `echo ${PIPESTATUS[@]}` | `2 0 0` (grep failed, cut and wc OK) |
| `pwd` | `/home/analyst/data/out/extracts` |

### Answers
**Q1.** grep reads a file that does not exist. From `~/data/out/extracts`, `../data/sales_2025.csv` = `/home/analyst/data/out/data/sales_2025.csv`. The real file is `/home/analyst/data/sales_2025.csv`.

**Q2.** A pipeline's status is that of its last command (`cut`, OK), so grep's failure is lost. The script ends with `echo "extracts: done"`, which always succeeds → exit 0.

**Q3.** `2>/dev/null` hides only grep's error messages (e.g. "No such file or directory"). Errors from `cut`, `mkdir`, `cd` or the `>` redirection would still appear.

**Q4.**
| Option | Meaning |
|---|---|
| `-e` | exit immediately if a command fails |
| `-u` | treat unset variables as an error |
| `pipefail` | a pipeline fails if *any* command in it fails |

Add `set -euo pipefail` after `#!/bin/bash`: grep's failure (status 2) makes the pipeline fail, and `-e` stops the script with a non-zero status before it prints "done". Also remove `2>/dev/null` so the error is visible.

---

## 5.4 Task 3: Auditing

**Prediction:** around 10 to 20 seconds.

### Timing
| Run | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| Sample (100,000 orders) | 2.43 s | 1.57 s | 1.10 s | 128,020 KB |
| Full file (8.4M orders) | 88.46 s | 42.92 s | 45.15 s | 633,440 KB |

### System calls on the sample (`strace -c -e trace=openat,write,close`)
| System call | Calls |
|---|---|
| `openat` | 100,686 |
| `write` | 100,001 |
| `close` | 100,673 |
| **Total** | **301,360** |

`ls -l ~/data/out/audit_2025.csv`: 1,952,269 bytes

### Answers
**Q1. How many openat, write and close calls for 100,000 orders? Why so many?**
About 100,000 of each (table above). `audit.py` opens the file, writes one line and closes it again for every single order: 100,000 opens, 100,000 writes and 100,000 closes. Each system call is a trip to the kernel, so it makes the program slow and pushes up the system time.

**Q2. Where did the time go on the whole file? What share went to the kernel? Compare with `report.py`.**
| Script | User | System | System share |
|---|---|---|---|
| `audit.py` (full file) | 42.92 s | 45.15 s | ≈ 51% |
| `report.py` (full file) | 12.64 s | 3.40 s | ≈ 21% |

About half of `audit.py`'s CPU time went to the kernel, because it makes three system calls per order (open, write, close): about 25 million calls for 8.4 million orders. In `report.py` only about 21% went to the kernel, because it reads the file once and does most of its work in Python.

**Q3. Is it true that opening and closing the file for every order saves each line on disk?**
No. Closing a file doesn't send the data to the disk; it only hands it to the kernel, which keeps it in memory and writes it to disk later. Lecture 9 (slide 13): closing alone does not guarantee that writes have reached persistent storage. So opening and closing does not make the data safer, only slower.

**Q4. With a 128 KiB buffer and a single open file, about how many write calls?**
About 15. The file is 1,952,269 bytes and the buffer holds 128 KiB = 131,072 bytes. Python only calls `write` when its buffer is full: 1,952,269 ÷ 131,072 ≈ 15 write calls, instead of the 100,001 that `audit.py` makes now.

---

## 6.4 Worker Experiment (sweep)

`bash tools/sweep.sh Javier-Barrera` → `members/Javier-Barrera/sweep.csv`
Stats step timed with 1, 2, 4, 8 and 16 workers, three runs each.

| Workers | Run 1 | Run 2 | Run 3 | Avg. elapsed | System time (range) |
|---|---|---|---|---|---|
| 1 | 73.56 s | 66.36 s | 63.87 s | ~67.9 s | 3.8–4.5 s |
| 2 | 29.31 s | 29.30 s | 29.08 s | ~29.2 s | 3.4–3.9 s |
| **4** | 16.65 s | 16.37 s | 16.56 s | **~16.5 s (fastest)** | 4.0–4.3 s |
| 8 | 39.39 s | 59.43 s | 74.41 s | ~57.7 s | 91–327 s |
| 16 | 24.41 s | 42.70 s | 59.57 s | ~42.2 s | 25–186 s |

**My laptop:** Snapdragon X Plus X1P42100, **8 cores, 8 threads** (one thread per core). Container `nproc`: 8.

**Observation:** more workers help up to 4. With 8 and 16 workers the step gets much slower and the system time explodes, even though the laptop has 8 cores. (The cause is Task 5.)

**Line for REPORT.md:**
Javier-Barrera: ASUS Vivobook S 15 (Snapdragon X Plus X1P42100), 8 cores, 8 threads. Fastest with 4 workers (~16.5 s); 8 and 16 workers were much slower (~58 s and ~42 s), with very high system time.
