"""
epanet_normal_run.py
-----------------------
WNTR quasi-steady simulation of network.inp — the tabletop
physical prototype network:
  - Straight 1-inch main with branches at J1 (1 branch), J2 (2 branches),
    J3 (1 branch), each 1/2-inch pipes leading to open-ended tanks at 0 m head.
  - Supply head: 0.4572 m (1.5 ft) from R_MAIN.
  - Flow controlled by valve V_MAIN: starts Open (1.19 LPS steady tabletop supply).
  - All tanks modelled as fixed-head reservoirs at 0 m (free discharge).
  - 30-minute run, 1-minute quasi-steady timestep.

Network topology: V_MAIN (TCV valve) is the inline shutoff link between R_MAIN and J1.
  Uses WNTRSimulator for robust hydraulic balance.

Requires: pip install wntr
"""

import os
import wntr
import pandas as pd
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE) == "scripts" else _HERE

INP_FILE   = os.path.join(_ROOT, "network.inp")
OUTPUT_DIR = os.path.join(_ROOT, "results", "epanet_normal")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# v4 node/link labels
JUNCTION_COLS  = ["J1", "M12", "J2", "M23", "J3", "OUT_1A", "OUT_2A", "OUT_2B", "OUT_3A"]
MAIN_LINK_COLS = ["V_MAIN", "P_MAIN2A", "P_MAIN2B", "P_MAIN3A", "P_MAIN3B"]
BRANCH_COLS    = ["P_B1A", "P_TANK1A", "P_B2A", "P_TANK2A",
                  "P_B2B", "P_TANK2B", "P_B3A", "P_TANK3A"]


def run():
    wn  = wntr.network.WaterNetworkModel(INP_FILE)
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()

    full_idx = list(range(0, 1860, 60))
    pressure = results.node["pressure"].reindex(full_idx, fill_value=0.0)
    head     = results.node["head"].reindex(full_idx, fill_value=0.0)
    flow     = (results.link["flowrate"] * 1000).reindex(full_idx, fill_value=0.0)

    pressure.to_csv(os.path.join(OUTPUT_DIR, "pressure.csv"))
    head.to_csv(os.path.join(OUTPUT_DIR, "head.csv"))
    flow.to_csv(os.path.join(OUTPUT_DIR, "flow.csv"))
    print(f"Saved pressure/head/flow CSVs -> {OUTPUT_DIR}/")
    return pressure, flow, head


def plot(pressure, flow):
    t_min = pressure.index / 60.0

    fig, axs = plt.subplots(2, 1, figsize=(12, 9), sharex=True)

    # --- Flow ---
    main_cols   = [c for c in MAIN_LINK_COLS if c in flow.columns]
    branch_cols = [c for c in BRANCH_COLS if c in flow.columns]
    for c in main_cols:
        axs[0].plot(t_min, flow[c], lw=2.0, label=f"Flow {c}")
    for c in branch_cols:
        axs[0].plot(t_min, flow[c], lw=1.2, ls="--", label=f"Flow {c}")
    axs[0].axvspan(5, 15, color="green", alpha=0.08, label="Supply window (5-15 min)")
    axs[0].set_ylabel("Flow (LPS)")
    axs[0].set_title("v4 WNTR — Flow (Tabletop Prototype, Supply Window: 5–15 min)")
    axs[0].legend(fontsize=7, loc="upper right", ncol=3)
    axs[0].grid(alpha=0.3)

    # --- Pressure ---
    junc_cols = [c for c in JUNCTION_COLS if c in pressure.columns]
    for c in junc_cols:
        lw = 2.0 if c in ("J1", "J2", "J3") else 1.2
        axs[1].plot(t_min, pressure[c], lw=lw, label=f"Pressure {c}")
    axs[1].axvspan(5, 15, color="green", alpha=0.08, label="Supply window (5-15 min)")
    axs[1].set_ylabel("Pressure (m)")
    axs[1].set_xlabel("Time (min)")
    axs[1].set_title("v4 WNTR — Pressure at Junctions (Supply Window: 5–15 min)")
    axs[1].legend(fontsize=7, ncol=3)
    axs[1].grid(alpha=0.3)

    plt.tight_layout()
    outpath = os.path.join(OUTPUT_DIR, "v4_epanet_normal.png")
    plt.savefig(outpath, dpi=150)
    print(f"Saved plot -> {outpath}")
    plt.close(fig)


if __name__ == "__main__":
    pressure, flow, head = run()
    plot(pressure, flow)
