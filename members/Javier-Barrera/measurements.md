\# Measurements – Javier-Barrera



\## Laptop

| | |

|---|---|

| Machine | ASUS Vivobook S, Windows 11 ARM |

| CPUs in the container (`nproc`) | 8 |

| Memory seen in the container (`free -h`) | 7.5 Gi (the whole Docker VM, not the limit) |

| Container memory limit | 2 GB, no swap (cgroup `memory.max`) |



\## Dataset

| File | Orders | Size |

|---|---|---|

| `sales\_2025.csv` | 8,400,000 | 498 MB |

| `sales\_2025\_sample.csv` | 100,000 | 5.8 MB |



\## Baseline: `tools/check.py` before any fix

| Output | Result |

|---|---|

| `revenue\_by\_region\_month.csv` | missing |

| `extracts/\*.csv` | 0 rows each (expected 839,987 to 2,183,057 per region) |

| `audit\_2025.csv` | 100,000 lines (sample run), expected 8,400,000 |

| `segments.csv` | missing |

| `stats.csv` | missing |



\---



\## 5.1 Warm-up: Generating the Report

\- `ls -l run\_report.sh`: `-rwxrwxrwx root root`

\- `./run\_report.sh` ran on my laptop, no "Permission denied".



\*\*Q1. Which permission is missing, and for whom?\*\*

Execute (`x`), for owner, group and others. Git stored the file as `100644` (not executable). \*To confirm with a Mac teammate's `ls -l`.\*



\*\*Q2. Why does `bash run\_report.sh` work?\*\*

Then `bash` is the program being run; it only needs to \*read\* the file, not execute it.



\*\*Q3. Did the same happen on every laptop?\*\*

No. My repo is in a Windows folder: Windows has no Linux permissions, so Docker shows every file as `rwxrwxrwx`. On a Mac the file keeps its real mode (`-rw-r--r--`), so `./run\_report.sh` fails with "Permission denied". \*To confirm with a Mac teammate.\*



\*\*Fix (done by me, commit `d1476ae`)\*\*

`chmod +x run\_report.sh` (container) + `git update-index --chmod=+x run\_report.sh` (Windows git does not see file modes). Commit showed `mode change 100644 => 100755`.



\---



\## 5.2 Task 1: Generating the Report… Again



\### Full pipeline, timed

`/usr/bin/time -f "$T" ./run\_report.sh`

\- 324.10 s elapsed, 406.22 s user, 181.16 s system, 2,089,892 KB peak memory

\- user + system (587 s) > elapsed → several CPUs in parallel (stats workers)

\- `report.py` was killed, but the script continued and printed "finished"

\- stats used 16 workers on a container with 8 CPUs



\### Outputs vs README

| Output | Result |

|---|---|

| `revenue\_by\_region\_month.csv` | \*\*missing\*\*: `report.py` killed before writing it |

| `extracts/\*.csv` | 6 files, all \*\*0 bytes\*\* (Task 2) |

| `audit\_2025.csv` | OK, 180 MB, 8.4M lines |

| `segments.csv` | OK |

| `stats.csv` | OK |



\### `report.py` alone

\- 16.24 s elapsed, 12.64 s user, 3.40 s system, 2,090,008 KB peak memory

\- Printed "Killed"; exit status \*\*137\*\*

\- `memory.events`: `max 83832`, `oom 6`, `oom\_kill 6`



\### Memory growth

| Orders | Table size | Peak memory | Result |

|---|---|---|---|

| 1,000,000 | 106 MiB | 503,492 KB (\~492 MiB) | OK, 7.25 s |

| 2,000,000 | 211 MiB | 856,560 KB (\~836 MiB) | OK, 10.28 s |

| 4,000,000 | 423 MiB | 1,567,288 KB (\~1.5 GiB) | OK, 17.97 s |

| 8,400,000 | 887 MiB | \~2 GB at the limit | \*\*Killed\*\* |



Memory grows \~350 MB per million orders + \~150 MB fixed (Python itself).



\### With `tee`

`python3 steps/report.py | tee /tmp/report.log`: nothing on screen, log empty, no "Killed" message.



\### Answers

\*\*Q1.\*\* 137 = 128 + 9 → signal 9 (SIGKILL). Sent by the kernel's out-of-memory killer when the container hit 2 GB. Confirmed by `oom\_kill` in `memory.events`.



\*\*Q2.\*\* 887 MiB is only the raw data. Python wraps each value in an object with extra information, so the program needs \~3.5–5× more memory than the table size.



\*\*Q3.\*\* See the table. The whole file would need about \*\*3 GB\*\* (150 MB + 8.4 × 350 MB), more than the 2 GB limit.



\*\*Q4.\*\* Output into a pipe is buffered, not written line by line. SIGKILL ended Python before it flushed the buffer, so the line was lost. The shell reports the status of `tee` (the last command, OK), which hides the failure.



\---



\## 5.3 Task 2: Extracting Data



\### Run

\- `bash steps/extracts.sh` → "extracts: done"

\- `echo $?` → 0 (success)

\- `ls -l \~/data/out/extracts` → 6 files (Benelux, DACH, France, Iberia, Italy, Nordics), all 0 bytes



\### The script (`less steps/extracts.sh`)

\- `cd` into `\~/data/out/extracts`, then for each region:

&#x20; `grep ",REGION," ../data/sales\_2025.csv 2>/dev/null | cut ... > REGION.csv`

\- The path is relative to the folder it moved into

\- grep's errors are thrown away (`2>/dev/null`)

\- Always prints "extracts: done"; does not use the `DATA` variable



\### Pipeline by hand (from `\~/data/out/extracts`)

| Command | Result |

|---|---|

| `grep ",Iberia," ../data/sales\_2025.csv \\| cut ... \\| wc -l` | `No such file or directory`, 0 lines |

| `echo ${PIPESTATUS\[@]}` | `2 0 0` (grep failed, cut and wc OK) |

| `pwd` | `/home/analyst/data/out/extracts` |



\### Answers

\*\*Q1.\*\* grep reads a file that does not exist. From `\~/data/out/extracts`, `../data/sales\_2025.csv` = `/home/analyst/data/out/data/sales\_2025.csv`. The real file is `/home/analyst/data/sales\_2025.csv`.



\*\*Q2.\*\* A pipeline's status is that of its last command (`cut`, OK), so grep's failure is lost. The script ends with `echo "extracts: done"`, which always succeeds → exit 0.



\*\*Q3.\*\* `2>/dev/null` hides only grep's error messages (e.g. "No such file or directory"). Errors from `cut`, `mkdir`, `cd` or the `>` redirection would still appear.



\*\*Q4.\*\*

| Option | Meaning |

|---|---|

| `-e` | exit immediately if a command fails |

| `-u` | treat unset variables as an error |

| `pipefail` | a pipeline fails if \*any\* command in it fails |



Add `set -euo pipefail` after `#!/bin/bash`: grep's failure (status 2) makes the pipeline fail, and `-e` stops the script with a non-zero status before it prints "done". Also remove `2>/dev/null` so the error is visible.



\---



\## 5.4 Task 3: Auditing

\*(to do)\*

