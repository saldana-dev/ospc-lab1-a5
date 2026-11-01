# Lab 1: The Nightly Report

Write your answers in this file. Keep them short: a few sentences, the commands
you used, and the numbers you measured. Copy the lines of output that matter,
not whole screens.

## Warm-up: Generating the report

- What happened, and why:
- Your fix, and how it reached your teammates:

## Task 1: Generating the report… again

- Symptom:
- Commands and recordings you used, why you chose them, and what they showed:
- Cause:
- Fix:
- Before and after (your measurements):

## Task 2: Extracting data

*Fixed by DMARCOS (commit `14ddba1`). Measurements on Apple MacBook Air M2.*

- Symptom: `bash steps/extracts.sh` printed `extracts: done` and exited with
  status 0 (program claims there was no problem) but the six files in `~/data/out/extracts` were all 0 bytes.
  `tools/check.py` reported `0 rows, expected 2,183,057` for Iberia and also the same for every region.
- Commands and recordings:`less steps/extracts.sh` showed that the script does `cd "$OUT/extracts"`
  before it reads the data. I ran the pipeline by hand from that folder but
  without `2>/dev/null`, to see the grep's error and the status of
  every command in the pipe:
  ```
  $ cd ~/data/out/extracts
  $ grep ",Iberia," ../data/sales_2025.csv | cut -d, -f1,2,4,6,7 | wc -l
  grep: ../data/sales_2025.csv: No such file or directory
  0
  $ echo ${PIPESTATUS[@]}
  2 0 0 #grep fails but the other steps in the pipeline don't so pipeline exit status is 0
  $ pwd
  /home/analyst/data/out/extracts
  ```
- Cause: three issues. (1) Relative path. We are in folder~/data/out/extracts. We write the path ../data/sales_2025.csv which point to ~/data/out/data/sales_2025.csv which doesn’t exist. The real file is ~/data/sales_2025.csv .
(2) `2>/dev/null`
  hides grep's error message. grep can’t find the file so it writes grep: ../data/sales_2025.csv: No such file or directory to stream 2. Then stream 2 points to /dev/null, so the message vanishes (in the "black hole"). Finally, grep writes nothing to stream 1 so cut receives empty input and writes an empty Iberia.csv without any problem.
  (3) The exit status. In pipeline the exit status is the status of its last command. grep failed but `cut` didn't have any problem (it read an empty input and exited 0).
- Fix: Change so that script reads the file named from absolute path. (`$HOME/data/sales_2025.csv`, absolute path) and then writes to
  `$OUT/extracts/$region.csv`. We removed `2>/dev/null`
  and added `set -euo pipefail`. `-e` stops the script when the first command fails, `-u` treats an unset variable as an error, and `pipefail` makes a
  pipeline fail when any of its commands fails (not only the last one).
- Before and after measurements:

  | | Before | After |
  |---|---|---|
  | Elapsed | 0.01 s | 2.94 s |
  | User / system | 0.00 s / 0.00 s | 3.94 s / 0.87 s |
  | Peak memory | 6376 KB | 8392 KB |
  | Output | 6 empty files, exit 0 | 8,400,000 rows in 6 files (about 290 MB), exit 0 |
  | Input file missing (`DATA=/nope.csv`) | `extracts: done`, exit 0 | `grep: /nope.csv: No such file or directory`, exit 2 |
  | `tools/check.py` | FAIL, 0 rows | PASS for all six regions |

  Before was fast because it did not work.

## Task 3: Auditing

- Symptom:
- Commands and recordings you used, why you chose them, and what they showed:
- Cause:
- Fix:
- Before and after (your measurements):

## Task 4: Segmenting the orders

**Fixed by a.saldana**

- Symptom: The segments step took 1.081 seconds on 100,000 orders, which would mean ~90 seconds on the full 8.4 million orders.
- Commands and recordings you used, why you chose them, and what they showed: 
  - `DATA=~/data/sales_2025_sample.csv python3 -m cProfile -s tottime steps/segments.py` - profiler showed `_strptime` was called 100,000 times (0.266 seconds), indicating row-by-row date parsing.

- Cause: The `segment(order)` function used `datetime.strptime(order.order_date, "%Y-%m-%d")` for every single order inside a loop. Row-by-row date parsing is very slow compared to vectorized pandas operations.
- Fix: Replaced with vectorized pandas operations: used `pd.to_datetime()` for the entire column, then computed quarter, value, and size using pandas vectorized operations instead of iterating through rows.
- Before and after (your measurements):
  - Before: Elapsed 1.081 s, User 1.073 s, System 0.000 s
  - After: Elapsed 0.27 s, User 0.85 s, System 0.03 s, Peak memory 148028 KB
  - Improvement: 4x faster (75% reduction in elapsed time)

## Task 5: Computing the statistics
**Fixed by anacbe**
- Symptom: There were two problems. (1) The script always used 16 workers, but more workers stopped helping: in my sweep, 4 workers took 11.9 s and 8 or 16 workers both took about 10.9 s, while user CPU time rose from 45 s to 77 s. (2) After Ctrl-C the script stopped, but its workers kept running at 99% CPU.
- Commands and recordings you used, why you chose them, and what they showed:`bash tools/sweep.sh anacbe` to time 1, 2, 4, 8 and 16 workers (averages of 3 runs: 34.3 s, 19.5 s, 11.9 s, 10.9 s, 10.9 s). `less steps/stats.sh` to read the script. Then I started it, pressed Ctrl-C and listed the processes:

  ```
  $ WORKERS=2 bash steps/stats.sh
  stats: input ready
  ^C
  $ ps -ef
  UID      PID  PPID  C  CMD
  analyst    1     0  0  /bin/bash -l
  analyst 2070     1 99  python3 steps/stats_worker.py 0 2
  analyst 2071     1 99  python3 steps/stats_worker.py 1 2
  ```

  The workers were still running, and their parent (PPID) was 1: the script had died and they had become orphans.
- Cause:(1) `WORKERS=${WORKERS:-16}` is a fixed number that ignores how many CPUs the laptop has. The container has 8 CPUs, so 16 workers just take turns on the same cores, and on the M1 only 4 cores are fast, so the curve flattens after 4. (2) The workers are started in the background with `&`. In a script, bash starts background processes with SIGINT ignored, so Ctrl-C killed the script but not the workers, and the script had no `trap` to stop them.
- Fix:(1) `WORKERS=${WORKERS:-$(nproc)}`, so the default matches the CPUs of each laptop and can still be overridden with `WORKERS=`. (2) Before starting the workers: `trap 'kill $(jobs -p) 2>/dev/null; exit 130' INT TERM`. On Ctrl-C or `kill`, the script sends SIGTERM (which the workers do not ignore) to all its background jobs and exits with 130 (128 + 2). Limitation: `kill -9` (SIGKILL) cannot be caught, so the trap does not run and the workers would still be orphaned. 
- Before and after (your measurements):| | Before | After |
  |---|---|---|
  | Workers (default) | 16 | 8 (`nproc`) |
  | Elapsed | 10.9 s | [fill in] s |
  | User / system | 77.5 s / 4.2 s | [fill in] s / [fill in] s |
  | Peak memory | – | [fill in] KB |
  | Ctrl-C | workers keep running with PPID 1 | no workers left, exit 130 |
  | `tools/check.py` | PASS stats.csv | PASS stats.csv |

  Before values are the averages of my sweep with 16 workers. The elapsed time barely changes, but the same result now needs fewer processes.

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
- **Asís (a.saldana)** used Claude (Anthropic, via nebulaONE chat interface) as a supporting tool. Prompts summary: "Help me understand where to run commands (Mac vs Docker terminal)", "How to fix git merge conflicts", "Explain the performance issue in segments.py", "How to use cProfile to profile the code". Claude helped me:
	- Understand the Docker/Mac terminal separation and where to run git vs Python commands
	- Identify the performance bottleneck in segments.py (datetime.strptime called 100,000 times)
	- Create the vectorized pandas solution using pd.to_datetime() 
	- Navigate git conflicts when teammates pushed change
- **Ana (anacbe)** used Claude (Anthropic, claude.ai chat) as a supporting tool. Prompts summary: "help me set up the SSH key and git", "which terminal do I use, the Mac or the container", "explain this output", "what do I write in measurements.md", "help me find and fix the problems in stats.sh", "help me format REPORT.md". Claude helped me:
  - Set up git and the SSH key, and understand the difference between the laptop terminal and the container
  - Analyse my sweep results and find the two problems in stats.sh
  - Propose the two fixes (`$(nproc)` and the `trap`), which I tested in the container before committing
