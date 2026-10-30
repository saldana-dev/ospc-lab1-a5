\# Measurements - Javier-Barrera



\## Laptop

\- ASUS Vivobook S, Windows 11 ARM

\- CPUs in the container (nproc): 8  -> how many CPUs Docker lets the container use

\- Memory seen in the container (free -h): 7.5 Gi total -> docker's whole virtual machine

\- Container memory limit: 2 GB, no swap -> real ceiling for everything inside the container



\## Dataset -> about the file

\- sales\_2025.csv: 8,400,000 orders, 498 MB

\- sales\_2025\_sample.csv: 100,000 orders, 5.8 MB



**##5.1 Warm-up**



**#run report and roots**



\- ls -l run\_report.sh: -rwxrwxrwx root root

\- ./run\_report.sh ran on my laptop (no "Permission denied")

\- Why: the repo is in a Windows folder. Windows has no Linux permissions,

&#x20; so Docker shows every file as rwxrwxrwx (executable for everyone).

&#x20; On a Mac the file keeps its real mode (-rw-r--r--, no x),

&#x20; so ./run\_report.sh fails with "Permission denied".

&#x20;

**#Q1, permissions missing, and from whom**

\-To confirm: compare with a teammate on a Mac.



**#Q2, why does bash run\_report.sh work?**



\-it Works because bash is the program being run, it only needs to read the file, no need to execute it.



**#Q3, did the same happen on every laptop? If not compare ls and -l and explain**



\-mine run because im on Windows and Windows has no Linux permissions



**#Fix what we just did and make it executable**



Fix: chmod +x run\_report.sh (container) + git update-index --chmod=+x run\_report.sh (Windows)

\- git commit showed: mode change 100644 => 100755 (not executable -> executable)

\- Pushed in commit d1476ae. Teammates get it with git pull.













**## 5.2 Task 1: report.py on the full file**

\- Table size printed by the script: 8,400,000 orders (887 MiB)

\- 16.24s elapsed, 12.64 s user, 3.40s system

\- Peak memory: 2,090,008 KB (about 2 GB, the container limit)

\- Result: killed by signal 9 (SIGKILL, out of memory) <- kernel killed it and script had no chance to print an error



**-5.2 task 1:  run\_report.sh, timed**

\-report.py killed again, but the script printed "finished"



**##Outputs of code vs lab README**



\-revenue\_by\_region\_month.csv: MISSING -> report.py was killed before writing it

\-extracts.csv: 6 files exist and are shown, such as France, Spain or Benelux but have no bites and are empty so script runs nothing

\-audit\_2025.csv: OK

\-segments.csv:OK

\-stats.csv: OK



\-oom\_kill 6 is the line that answers the main question. The kernel oom has killed 6 processes in this container because it reaches the memory limit. It stopped report.py



other lines: -> max 83832: n of times container reached its limit

&#x09;     -> oom 6: how many times it failed and kernel had to kill something

&#x09;     -> low/high 0: other thresholds not used here



\#the 1-million-order test:



\-with 1 million data de program worked and didnt get killed

\-it took about 7 seconds (7.25s)

\-the program says its data is 106Mib but actually used 429 MiB (almost 5 times more than the data itself)



\#repeat with head -n 2000001 -> with 2 million orders it also worked

&#x09;-> 211MiB (x2 the 1M run)

&#x09;-> 10.26 seconds used



\#repeat with head -n 4000001 -> it also worked, but only just

&#x09;-> 423MiB

&#x09;-> only just, because it used 1.5GiB, close to the 2GB limit in Docker



\#the pattern



From 1M to 2M orders, memory went up by about 350 MB.

From 2M to 4M orders, it went up by about 710 MB, which is again about 350 MB per million orders.



So memory grows in a straight line: about 350 MB per million orders, plus a fixed \~150 MB for Python itself.



\#How much memory would the whole file need? -> about 3 GB (≈150 MB + 8.4 × 350 MB).



**5.3 task 2: Extracting data**



\-> run the data first and compare it with the README outputs table



&#x09;		-> bash extracts : done

&#x09;		-> echo $?: 0, success

&#x09;		-> 6 files,(Benelux, France, Dach, Iberia etc...) but all 0 bytes (empty)

&#x09;		-> README expects a file to contain orders of that region -> step did not do its job as its 			empty



\-> less steps/extracts.sh script



&#x09;Script (less steps/extracts.sh) - what it does:

&#x09; cd into \~/data/out/extracts, then for each region:

&#x20;	-grep ",REGION," ../data/sales\_2025.csv 2>/dev/null | cut ... > REGION.csv

&#x09;-Path ../data/sales\_2025.csv is relative to the folder it cd'd into					 	-Errors from grep are thrown away (2>/dev/null)

&#x09;-Always prints "extracts: done" at the end

&#x09;-Does not use the DATA variable



\-> run the pipeline



Q4, set -euo pipefail:



&#x09;-e: exit immediately if a command fails (non-zero status)

&#x09;-u: treat unset variables as an error

&#x09;-pipefail: a pipeline fails if ANY command in it fails, not only the last one

&#x09;

How to make extracts.sh stop with an error:

&#x09;  add "set -euo pipefail" at the top of extracts.sh (after #!/bin/bash).

&#x09;  Then grep's failure (status 2) makes the whole pipeline fail (pipefail),

&#x09;  and -e stops the script at once with a non-zero status, before it prints















\## Baseline: tools/check.py before any fix

\- revenue\_by\_region\_month.csv: missing

\- extracts/\*.csv: 0 rows each (expected 839,987 to 2,183,057 per region)

\- audit\_2025.csv: 100,000 lines (from a sample run), expected 8,400,000

\- segments.csv: missing

\- stats.csv: missing



(the "before picture: every output fails. This Will be compared with the "after" once each fault is fixed



