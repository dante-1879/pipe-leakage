"""
rerun_all.py
------------
Runs the tabletop prototype water pipeline simulation suite :
  - EPANET / WNTR quasi-steady baseline & PSM leak scan
  - TSNet MOC transient normal & acoustic NPW burst scan
  - Compiles the standalone dashboard.html

Usage:
    python rerun_all.py                 # Runs all v4 simulations + compiles dashboard
    python rerun_all.py --epanet-only   # Runs only WNTR quasi-steady scripts
    python rerun_all.py --tsnet-only    # Runs only TSNet MOC transient scripts
    python rerun_all.py --dashboard-only # Compiles dashboard.html from results/
"""

import subprocess
import sys
import time
import argparse

V4_EPANET_SCRIPTS = [
    "scripts/epanet_normal_run.py",
    "scripts/epanet_leak_scan.py",
]

V4_TSNET_SCRIPTS = [
    "scripts/tsnet_normal_run.py",
    "scripts/tsnet_burst_scan.py",
]

V4_DASHBOARD_SCRIPT = "generate_dashboard.py"


def run_script(script):
    t0 = time.time()
    print(f"\n==========================================", flush=True)
    print(f"--> Running {script}...", flush=True)
    res = subprocess.run([sys.executable, script], capture_output=True, text=True)
    dt = time.time() - t0
    print(f"Finished {script} in {dt:.1f}s (Exit code: {res.returncode})", flush=True)
    if res.stdout:
        print(f"STDOUT:\n{res.stdout.strip()}", flush=True)
    if res.stderr:
        print(f"STDERR:\n{res.stderr.strip()}", flush=True)
    if res.returncode != 0:
        print(f"ERROR: {script} failed with exit code {res.returncode}", flush=True)
        sys.exit(res.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the tabletop v4 pipeline simulation suite.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--epanet-only", action="store_true", help="Run only v4 WNTR/EPANET scripts")
    group.add_argument("--tsnet-only", action="store_true", help="Run only v4 TSNet scripts")
    group.add_argument("--dashboard-only", action="store_true", help="Compile only dashboard.html")
    args = parser.parse_args()

    scripts = []
    if args.epanet_only:
        scripts = V4_EPANET_SCRIPTS + [V4_DASHBOARD_SCRIPT]
    elif args.tsnet_only:
        scripts = V4_TSNET_SCRIPTS + [V4_DASHBOARD_SCRIPT]
    elif args.dashboard_only:
        scripts = [V4_DASHBOARD_SCRIPT]
    else:
        scripts = V4_EPANET_SCRIPTS + V4_TSNET_SCRIPTS + [V4_DASHBOARD_SCRIPT]

    for s in scripts:
        run_script(s)

    print("\n==========================================", flush=True)
    print("ALL REQUESTED RUNS COMPLETE! Dashboard ready at dashboard.html", flush=True)

