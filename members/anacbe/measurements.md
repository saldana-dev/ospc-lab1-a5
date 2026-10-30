

# Measurements: anacbe

Laptop: Apple MacBook Air M1 2020, 8 GB, macOS Sequoia 15.6.1
nproc in container: 8



## Task 1: Task 1: Generating the Report (report.py memory by size)

```
T='%e s elapsed, %U s user, %S s system, %M KB peak memory'
/usr/bin/time -f "$T" ./run_report.sh
```
163.12 s elapsed, 238.20 s user, 30.24 s system, 2087452 KB peak memory

```
python3 steps/report.py
echo $?
cat /sys/fs/cgroup/memory.events
```
report: loaded 8,400,000 orders (887 MiB), then Killed. Exit status 137. memory.events: oom_kill 3.


```
head -n 1000001 ~/data/sales_2025.csv > /tmp/orders_1m.csv
DATA=/tmp/orders_1m.csv OUT=/tmp /usr/bin/time -f "$T" python3 steps/report.py
```
(same with 2000001 and 4000001)

| Orders | Table size (MiB) | Peak memory (KB) | Elapsed (s) |
|---|---|---|---|
| 1M | 106 | 511,444 | 2.26 |
| 2M | 211 | 854,800 | 4.19 |
| 4M | 423 | 1,566,540 | 8.53 |
| 8.4M | 887 | killed (limit 2 GiB) | – |

Peak grows about 350,000 KB per million orders, so the full file would need about 3,100,000 KB (≈ 3 GiB).

```
python3 steps/report.py | tee /tmp/report.log
cat /tmp/report.log
```
The log is empty: "report: loaded ..." is missing.

## Task 2: Extracting Data

```
bash steps/extracts.sh
echo $?
ls -l ~/data/out/extracts
```
"extracts: done", exit status 0, but all six REGION.csv files are 0 bytes.

```
cd ~/data/out/extracts
grep ",Iberia," ../data/sales_2025.csv | cut -d, -f1,2,4,6,7 | wc -l
echo ${PIPESTATUS[@]}
pwd
```
grep: ../data/sales_2025.csv: No such file or directory
wc -l: 0
PIPESTATUS: 2 0 0 (grep failed, cut and wc succeeded)
pwd: /home/analyst/data/out/extracts
