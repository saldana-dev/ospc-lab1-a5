# Lab 1: The Nightly Report

Write your answers in this file. Keep them short: a few sentences, the commands
you used, and the numbers you measured. Copy the lines of output that matter,
not whole screens.

## Warm-up: Generating the report

- What happened, and why:
- Your fix, and how it reached your teammates:

## Task 1: Generating the report… again

*Fixed by anderk88 (Ander Krause). Measurements on an Acer Aspire A315-44P,
AMD Ryzen 7 5700U, Windows 11 Home.*

- Symptom: `./run_report.sh` printed
  `./run_report.sh: line 10: 53 Killed python3 steps/report.py`, then carried
  on and printed `Nightly report finished`. `revenue_by_region_month.csv` was
  missing. Run alone, `python3 steps/report.py` printed
  `report: loaded 8,400,000 orders (887 MiB)`, then `Killed`, with exit status 137.
- Commands and recordings you used, why you chose them, and what they showed:
  `echo $?` right after the step gave 137 = 128 + 9: the program did not
  stop by itself, it was ended by signal 9 (SIGKILL), which it cannot catch.
  `cat /sys/fs/cgroup/memory.events` showed `oom_kill 2`: the kernel's
  out-of-memory killer ended it because the container reached its 2 GiB limit
  (`memory.max`). `/usr/bin/time -f "$T"` on the first 1, 2 and 4 million
  orders (`head -n`) showed how the peak memory grows with the input:
  506 MB, 849 MB and 1,566 MB, about 358 MB per million orders. The whole file
  would need about 3.1 GB. With `| tee /tmp/report.log` the log was empty:
  stdout into a pipe is block-buffered, and SIGKILL ended Python before it
  flushed the buffer.
- Cause: the script loads the whole file, with every column, into one
  DataFrame (887 MiB). It then adds a datetime column and a revenue column,
  builds 12 monthly copies with boolean filters and joins them back with
  `pd.concat`: a second full copy of the data. The peak is about 3.5 times
  the table size, so on 8.4 million orders it goes over the 2 GiB limit,
  even though the table itself is well below 2 GB.
- Fix: `steps/report.py` reads the file in chunks of 1,000,000 orders
  (`pd.read_csv(..., chunksize=1_000_000)`), keeps only the 4 columns it
  needs (`order_date`, `region`, `quantity`, `unit_price`), adds up the
  revenue per region and month of each chunk, and sums the chunks. It no
  longer builds the monthly copies. Memory now depends on the chunk size,
  not on the size of the file.
- Before and after (your measurements), `/usr/bin/time -f "$T" python3 steps/report.py`:

  | | Before | After |
  |---|---|---|
  | Result | `Killed`, exit 137 | `report: done`, exit 0 |
  | Elapsed | 59.02 s | 20.97 s |
  | User / system | 46.02 s / 14.00 s | 19.53 s / 3.32 s |
  | Peak memory | 2,089,756 KB (at the limit) | 381,848 KB |
  | Log with `tee` | empty | both lines |
  | `tools/check.py` | missing | PASS |

## Task 2: Extracting data

*Fixed by DMARCOS (commit `14ddba1`). Measurements on an Apple MacBook Air M2.*

- Symptom: `bash steps/extracts.sh` printed `extracts: done` and exited with
  status 0, but the six files in `~/data/out/extracts` were all 0 bytes.
  `tools/check.py` reported `0 rows, expected 2,183,057` for Iberia, and the
  same for every region.
- Commands and recordings you used, why you chose them, and what they showed:
  `less steps/extracts.sh` showed that the script does `cd "$OUT/extracts"`
  before it reads the data. We ran its pipeline by hand from that folder,
  without `2>/dev/null`, so that we could see grep's error and the status of
  every command in the pipe:
  ```
  $ cd ~/data/out/extracts
  $ grep ",Iberia," ../data/sales_2025.csv | cut -d, -f1,2,4,6,7 | wc -l
  grep: ../data/sales_2025.csv: No such file or directory
  0
  $ echo ${PIPESTATUS[@]}
  2 0 0
  $ pwd
  /home/analyst/data/out/extracts
  ```
  We did not need a recording: the step lasts 0.01 s, less than the
  recorder's 50 ms sampling period.
- Cause: three faults together. (1) A relative path after `cd`: from
  `~/data/out/extracts`, `../data/sales_2025.csv` names
  `~/data/out/data/sales_2025.csv`, which does not exist. (2) `2>/dev/null`
  hid grep's error message. It hides only grep's standard error: errors from
  `cut` or from the `>` redirection would still appear. (3) The exit status
  of a pipeline is the status of its last command. grep failed with 2, but
  `cut` read an empty input and exited 0. The script never checked, so it
  went on, printed `done` and exited 0.
- Fix: the script no longer changes folder. It reads the file named by
  `DATA` (default `$HOME/data/sales_2025.csv`, an absolute path) and writes to
  `$OUT/extracts/$region.csv`, like the other steps. We removed `2>/dev/null`
  and added `set -euo pipefail`: `-e` stops the script at the first failing
  command, `-u` treats an unset variable as an error, and `pipefail` makes a
  pipeline fail when any of its commands fails, not only the last one. It
  now works from any folder, for example
  `cd /tmp && bash ~/work/ospc-lab1-a5/steps/extracts.sh`.
- Before and after (your measurements), `/usr/bin/time -f "$T" bash steps/extracts.sh`:

  | | Before | After |
  |---|---|---|
  | Elapsed | 0.01 s | 2.94 s |
  | User / system | 0.00 s / 0.00 s | 3.94 s / 0.87 s |
  | Peak memory | 6376 KB | 8392 KB |
  | Output | 6 empty files, exit 0 | 8,400,000 rows in 6 files (about 290 MB), exit 0 |
  | Input file missing (`DATA=/nope.csv`) | `extracts: done`, exit 0 | `grep: /nope.csv: No such file or directory`, exit 2 |
  | `tools/check.py` | FAIL, 0 rows | PASS for all six regions |

  "Before" was fast only because it did no work.

## Task 3: Auditing

- Symptom:
- Commands and recordings you used, why you chose them, and what they showed:
- Cause:
- Fix:
- Before and after (your measurements):

## Task 4: Segmenting the orders

- Symptom:
- Commands and recordings you used, why you chose them, and what they showed:
- Cause:
- Fix:
- Before and after (your measurements):

## Task 5: Computing the statistics

- Symptom:
- Commands and recordings you used, why you chose them, and what they showed:
- Cause:
- Fix:
- Before and after (your measurements):

## The worker experiment

Every member runs `tools/sweep.sh` on their own laptop. Then run
`python3 tools/plot_sweep.py` and commit `results/sweep.png`.

![Elapsed time against the number of workers](results/sweep.png)

- How does the elapsed time change with the number of workers on each laptop?
- Why do the curves of your laptops differ? Use the cores and threads of each
  laptop, listed in `TEAM.md`.
- Which default number of workers did you choose for `stats.sh`, and why?

## Use of generative AI

- **Diego (DMARCOS)** used (Anthropic, Claude Code in the terminal) as a
  supporting tool. Prompts summary: "help me understand the lab step by step, what do I have to do in each step and why", "I have to do the fix for extracts.sh, explain the error/s and how to do the fix", "Why it ives this error". Claude mainly helped me understand everything I was doing along the way. It ran the measurement commands in the container and created the table for the report (which I obviously checked). It tested the fix of `steps/extracts.sh` (the script has a comment).

- **Ander (anderk88)** used Claude (Anthropic) as a supporting tool.
  Prompts summary: "explain step by step what I have to do", "help me fix
  report.py". Claude explained the commands, helped write the fix of
  `steps/report.py` (the script has a comment) and helped write up my
  measurements and the Task 1 section. I ran all the commands, checked the
  results and committed the files myself.
