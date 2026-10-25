"""
tsnet_normal_run.py
----------------------
TSNet (Method of Characteristics) simulation of network.inp — the tabletop
physical prototype network under steady, valve-open operation.

Demonstrates that TSNet initializes smoothly and runs the Method of Characteristics
directly from network.inp now that V_MAIN starts Open (establishing the required
nonzero initial steady-state flow of ~1.19 LPS across the network).

Setup:
  - Tabletop prototype network (1-inch main, 1/2-inch branches, 1.5 ft = 0.4572 m head)
  - V_MAIN Open at t=0 (no pump required)
  - Wave speed = 300 m/s (realistic for 1-inch plastic/PVC tabletop piping)
  - Duration = 2.0 s (at fine MOC timestep dt ≈ 0.00051 s, ~3,937 steps)

Requires: pip install tsnet
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tsnet

from wntr.network.base import LinkStatus

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE) == "scripts" else _HERE

INP_FILE   = os.path.join(_ROOT, "network.inp")
OUTPUT_DIR = os.path.join(_ROOT, "results", "tsnet_normal")
WAVESPEED  = 300.0   # m/s (plastic/PVC tabletop scale, 300+ m/s)
SIM_DURATION = 3.0   # seconds
SHUTOFF_TIME = 2.0   # seconds (valve shutoff to complete full operational cycle)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_and_run():
    print(f"Loading {INP_FILE} into TSNet...")
    tm = tsnet.network.TransientModel(INP_FILE)
    # Start during active supply window
    tm.get_link("V_MAIN").initial_status = LinkStatus.Open
    tm.set_wavespeed(WAVESPEED)
    tm.set_time(SIM_DURATION)

    print(f"MOC time step: {tm.time_step:.6f} s "
          f"({len(tm.simulation_timestamps)} steps over {SIM_DURATION:.1f} s)")

    # Initializer computes steady state via WNTR (valve is Open -> flow ~1.19 LPS)
    tm = tsnet.simulation.Initializer(tm, 0.0, "DD")
    print("TSNet Initializer completed successfully (nonzero initial flow established).")

    # Pure Normal Baseline: Run steady flow without artificial valve slam
    # This demonstrates the stable baseline supply condition in MOC
    tm = tsnet.simulation.MOCSimulator(tm, "v4_tsnet_normal")
    print("MOC simulation completed.")
    return tm


def export_results(tm):
    t = np.array(tm.simulation_timestamps)

    # Pressure at junctions
    pressure_data = {"time_s": t}
    for name in tm.junction_name_list:
        node = tm.get_node(name)
        pressure_data[name] = np.array(node.head) - (node.elevation or 0.0)
    pressure_df = pd.DataFrame(pressure_data)
    pressure_df.to_csv(os.path.join(OUTPUT_DIR, "pressure.csv"), index=False)

    # Flow in pipes (LPS)
    flow_data = {"time_s": t}
    for name in tm.pipe_name_list:
        pipe = tm.get_link(name)
        q_start = np.array(pipe.start_node_flowrate)
        q_end   = np.array(pipe.end_node_flowrate)
        flow_data[name] = ((q_start + q_end) / 2.0) * 1000  # LPS

    # Mass balance at J1 gives flow through V_MAIN
    p_m2 = "P_MAIN2A" if "P_MAIN2A" in flow_data else "P_MAIN2"
    if p_m2 in flow_data and "P_B1A" in flow_data:
        flow_data["V_MAIN"] = flow_data[p_m2] + flow_data["P_B1A"]

    flow_df = pd.DataFrame(flow_data)
    flow_df.to_csv(os.path.join(OUTPUT_DIR, "flow.csv"), index=False)

    print(f"Saved: {OUTPUT_DIR}/pressure.csv  (shape {pressure_df.shape})")
    print(f"Saved: {OUTPUT_DIR}/flow.csv       (shape {flow_df.shape})")
    return pressure_df, flow_df


def plot_results(pressure_df, flow_df):
    fig, axs = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    # Pressure
    all_juncs = ["J1", "M12", "J2", "M23", "J3", "OUT_1A", "OUT_2A", "OUT_2B", "OUT_3A"]
    junc_cols = [c for c in all_juncs if c in pressure_df.columns]
    for col in junc_cols:
        lw = 2.0 if col in ("J1", "J2", "J3", "M12", "M23") else 1.2
        ls = "-" if col in ("J1", "J2", "J3") else ("-." if "M" in col else "--")
        axs[0].plot(pressure_df["time_s"], pressure_df[col], lw=lw, ls=ls, label=f"Pressure {col}")
    axs[0].set_ylabel("Pressure Head (m)")
    axs[0].set_title("TSNet (MOC) — Normal Baseline Pressure (network_v4 Tabletop, a = 300 m/s)")
    axs[0].legend(fontsize=8, ncol=5, loc="upper right")
    axs[0].grid(alpha=0.3)

    # Flow
    flow_cols = [c for c in ["V_MAIN", "P_MAIN2A", "P_MAIN2B", "P_MAIN3A", "P_MAIN3B", "P_B1A", "P_B2A", "P_B2B", "P_B3A"]
                 if c in flow_df.columns]
    for col in flow_cols:
        lw = 2.0 if "MAIN" in col else 1.2
        ls = "-" if "MAIN" in col else "--"
        axs[1].plot(flow_df["time_s"], flow_df[col], lw=lw, ls=ls, label=f"Flow {col}")
    axs[1].set_ylabel("Flow (LPS)")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_title("TSNet (MOC) — Normal Baseline Flow (~1.19 LPS Total Tabletop Supply)")
    axs[1].legend(fontsize=8, ncol=4, loc="upper right")
    axs[1].grid(alpha=0.3)

    plt.tight_layout()
    outpath = os.path.join(OUTPUT_DIR, "v4_tsnet_normal.png")
    plt.savefig(outpath, dpi=150)
    plt.close(fig)
    print(f"Saved plot -> {outpath}")


if __name__ == "__main__":
    tm = build_and_run()
    pressure_df, flow_df = export_results(tm)
    plot_results(pressure_df, flow_df)
