"""
tsnet_burst_scan.py
----------------------
TSNet (Method of Characteristics) simulation suite for network.inp:
Simulates sudden bursts (Negative Pressure Waves / NPW) traveling down
the tabletop 1-inch main pipeline at high speed (wave speed = 300 m/s).

Scenarios:
  - baseline: steady-state tabletop flow (~1.19 LPS), no burst
  - burst_J1: sudden burst at upstream main junction J1
  - burst_J2: sudden burst at midpoint main junction J2
  - burst_J3: sudden burst at downstream main junction J3
  - burst_OUT_1A, burst_OUT_2A, burst_OUT_2B, burst_OUT_3A: branch terminal bursts
  - burst_J2_ramp: gradual incipient burst at J2 (0.2s ramp)

For each scenario, exports:
  - pressure.csv (sub-millisecond resolution pressure head at all junctions)
  - flow.csv (flows in main and branch pipes)
  - leak_flow.csv (burst emitter discharge)
  - high-resolution 3-panel transient plot showing wavefront arrival and reflections
  - summary.csv comparing peak pressure drops and wave arrival times (TDOA)

Requires: pip install tsnet
"""

import os
import shutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tsnet
from wntr.network.base import LinkStatus

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE) == "scripts" else _HERE

INP_FILE    = os.path.join(_ROOT, "network.inp")
OUTPUT_ROOT = os.path.join(_ROOT, "results", "tsnet_burst")
WAVESPEED   = 300.0   # m/s (tabletop 1-inch plastic/PVC scale, 300+ m/s)

SIM_DURATION     = 1.5     # seconds (0.5s baseline + 1.0s post-burst transient & settled leak)
BURST_START_TIME = 0.5     # seconds (0.5s pristine baseline before burst)
BURST_COEFF      = 1.0e-5  # m^3/s / (m H2O)^0.5 (~0.007 LPS burst, clean physical drop)


def build_and_run(burst_node=None, ramp_time=0.002):
    tm = tsnet.network.TransientModel(INP_FILE)
    # Start during active water supply window
    tm.get_link("V_MAIN").initial_status = LinkStatus.Open
    tm.set_wavespeed(WAVESPEED)
    tm.set_time(SIM_DURATION)
    tm = tsnet.simulation.Initializer(tm, 0.0, "DD")

    if burst_node is not None:
        tm.add_burst(burst_node, BURST_START_TIME, ramp_time, BURST_COEFF)

    # Clean burst transient without unphysical artificial valve slamming
    tm = tsnet.simulation.MOCSimulator(tm, "v4_tsnet_burst")
    return tm


def export_results(tm, out_dir, burst_node=None):
    os.makedirs(out_dir, exist_ok=True)
    t = np.array(tm.simulation_timestamps)

    # Pressure
    pressure_data = {"time_s": t}
    for name in tm.junction_name_list:
        node = tm.get_node(name)
        pressure_data[name] = np.array(node.head) - (node.elevation or 0.0)
    pressure_df = pd.DataFrame(pressure_data)
    pressure_df.to_csv(os.path.join(out_dir, "pressure.csv"), index=False)

    # Flow
    flow_data = {"time_s": t}
    for name in tm.pipe_name_list:
        pipe = tm.get_link(name)
        q_start = np.array(pipe.start_node_flowrate)
        q_end   = np.array(pipe.end_node_flowrate)
        flow_data[name] = ((q_start + q_end) / 2.0) * 1000  # LPS

    p_m2 = "P_MAIN2A" if "P_MAIN2A" in flow_data else "P_MAIN2"
    if p_m2 in flow_data and "P_B1A" in flow_data:
        flow_data["V_MAIN"] = flow_data[p_m2] + flow_data["P_B1A"]

    flow_df = pd.DataFrame(flow_data)
    flow_df.to_csv(os.path.join(out_dir, "flow.csv"), index=False)

    # Burst flow
    leak_df = None
    if burst_node is not None:
        node = tm.get_node(burst_node)
        leak_lps = np.array(node.emitter_discharge) * 1000  # LPS
        leak_df = pd.DataFrame({"time_s": t, "burst_flow_LPS": leak_lps})
        leak_df.to_csv(os.path.join(out_dir, "leak_flow.csv"), index=False)
        print(f"  Burst @ {burst_node}: peak discharge = {leak_lps.max():.4f} LPS -> {out_dir}/")
    else:
        print(f"  Baseline (no burst) -> {out_dir}/")

    return pressure_df, flow_df, leak_df


def plot_scenario(name, burst_node, pressure_df, flow_df, leak_df, out_dir, ramp_time=0.002):
    t = pressure_df["time_s"]
    fig, axs = plt.subplots(3, 1, figsize=(11, 11))

    # --- 1. Full Simulation Pressure ---
    main_juncs = ["J1", "M12", "J2", "M23", "J3"]
    for j in main_juncs:
        lw = 2.2 if j == burst_node else 1.5
        axs[0].plot(t, pressure_df[j], lw=lw, label=f"Pressure {j}")
    branch_juncs = ["OUT_1A", "OUT_2A", "OUT_2B", "OUT_3A"]
    for j in branch_juncs:
        lw = 2.0 if j == burst_node else 1.0
        axs[0].plot(t, pressure_df[j], lw=lw, ls="--", alpha=0.7, label=f"Pressure {j}")

    if burst_node is not None:
        axs[0].axvline(BURST_START_TIME, color="red", ls=":", lw=1.5,
                       label=f"Burst Start (t={BURST_START_TIME}s, {ramp_time*1000:.1f}ms ramp)")
    axs[0].set_ylabel("Pressure Head (m)")
    axs[0].set_title(f"TSNet NPW Complete Lifecycle — {name} (Baseline -> Burst -> Settled)")
    axs[0].legend(fontsize=7, ncol=5, loc="upper right")
    axs[0].grid(alpha=0.3)

    # --- 2. Zoomed-In Wavefront Arrival Window ---
    zoom_start = BURST_START_TIME - 0.005
    zoom_end   = BURST_START_TIME + 0.030
    idx_zoom   = (t >= zoom_start) & (t <= zoom_end)
    t_ms_rel   = (t[idx_zoom] - BURST_START_TIME) * 1000.0

    for j in main_juncs:
        lw = 2.2 if j == burst_node else 1.5
        axs[1].plot(t_ms_rel, pressure_df.loc[idx_zoom, j], lw=lw, label=f"Sensor {j}")
    if burst_node in branch_juncs:
        axs[1].plot(t_ms_rel, pressure_df.loc[idx_zoom, burst_node],
                    lw=2.0, ls="--", label=f"Burst Site {burst_node}")

    if burst_node is not None:
        axs[1].axvline(0.0, color="red", ls=":", lw=1.5, label="Burst Injected (t = 0 ms)")
    axs[1].set_ylabel("Pressure Head (m)")
    axs[1].set_xlabel("Time Relative to Burst (milliseconds)")
    axs[1].set_title("Zoomed Negative Pressure Wavefront Arrival (-5 ms to +30 ms)")
    axs[1].legend(fontsize=8, loc="upper right")
    axs[1].grid(alpha=0.3)

    # --- 3. Flow and Burst Discharge ---
    p2 = "P_MAIN2A" if "P_MAIN2A" in flow_df.columns else "P_MAIN2"
    p3 = "P_MAIN3A" if "P_MAIN3A" in flow_df.columns else "P_MAIN3"
    if p2 in flow_df.columns:
        axs[2].plot(t, flow_df[p2], lw=1.8, label=f"Flow {p2}")
    if p3 in flow_df.columns:
        axs[2].plot(t, flow_df[p3], lw=1.8, label=f"Flow {p3}")
    if leak_df is not None:
        axs[2].plot(t, leak_df["burst_flow_LPS"], lw=2.0, color="darkred",
                    label=f"Burst Discharge @ {burst_node} (LPS)")
    if burst_node is not None:
        axs[2].axvline(BURST_START_TIME, color="red", ls=":", lw=1.5)
    axs[2].set_ylabel("Flow (LPS)")
    axs[2].set_xlabel("Time (s)")
    axs[2].set_title(f"Pipeline Flow & Burst Discharge Rate")
    axs[2].legend(fontsize=8, loc="upper right")
    axs[2].grid(alpha=0.3)

    plt.tight_layout()
    outpath = os.path.join(out_dir, f"{name}.png")
    plt.savefig(outpath, dpi=150)
    plt.close(fig)
    print(f"  Saved plot -> {outpath}")


def summarize(all_pressure, all_burst_times):
    rows = []
    first_p = list(all_pressure.values())[0]
    junc_cols = [c for c in ["J1", "J2", "J3", "OUT_1A", "OUT_2A", "OUT_2B", "OUT_3A"]
                 if c in first_p.columns]

    for name, p_df in all_pressure.items():
        row = {"scenario": name}
        for j in junc_cols:
            row[f"init_head_{j}"] = p_df[j].iloc[0]
            row[f"min_head_{j}"]  = p_df[j].min()
            row[f"drop_{j}"]      = p_df[j].iloc[0] - p_df[j].min()
        if name in all_burst_times:
            for j, t_arr in all_burst_times[name].items():
                row[f"t_arr_{j}_ms"] = (t_arr - BURST_START_TIME) * 1000 if t_arr is not None else None
            t1 = all_burst_times[name].get("J1")
            t3 = all_burst_times[name].get("J3")
            if t1 is not None and t3 is not None:
                row["TDOA_J3_minus_J1_ms"] = (t3 - t1) * 1000
        rows.append(row)

    summary_df = pd.DataFrame(rows).set_index("scenario")
    summary_df.to_csv(os.path.join(OUTPUT_ROOT, "summary.csv"))
    print(f"\nSaved summary -> {OUTPUT_ROOT}/summary.csv")
    print(summary_df.to_string())


if __name__ == "__main__":
    if os.path.exists(OUTPUT_ROOT):
        shutil.rmtree(OUTPUT_ROOT)
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    scenarios = [
        ("baseline",       None,      0.002),
        ("burst_J1",       "J1",      0.002),
        ("burst_M12",      "M12",     0.002),
        ("burst_J2",       "J2",      0.002),
        ("burst_M23",      "M23",     0.002),
        ("burst_J3",       "J3",      0.002),
        ("burst_OUT_1A",   "OUT_1A",  0.002),
        ("burst_OUT_2A",   "OUT_2A",  0.002),
        ("burst_OUT_2B",   "OUT_2B",  0.002),
        ("burst_OUT_3A",   "OUT_3A",  0.002),
        ("burst_J2_ramp",  "J2",      0.200),
    ]

    all_pressure    = {}
    all_burst_times = {}

    for name, burst_node, ramp_time in scenarios:
        print(f"\n--- Running scenario: {name} (node={burst_node}, ramp={ramp_time*1000:.1f}ms) ---")
        out_dir = os.path.join(OUTPUT_ROOT, name)
        tm = build_and_run(burst_node=burst_node, ramp_time=ramp_time)
        pressure_df, flow_df, leak_df = export_results(tm, out_dir, burst_node=burst_node)
        plot_scenario(name, burst_node, pressure_df, flow_df, leak_df, out_dir, ramp_time=ramp_time)
        all_pressure[name] = pressure_df

        # Detect wavefront arrival times
        if burst_node is not None:
            t = pressure_df["time_s"].values
            arr_times = {}
            for j in ["J1", "M12", "J2", "M23", "J3"]:
                head = pressure_df[j].values
                idx_pre = np.where(t < BURST_START_TIME)[0][-1]
                h_base = head[idx_pre]
                # Wave arrival defined as head drop exceeding 0.015 m
                idx_drop = np.where((t >= BURST_START_TIME) & (h_base - head >= 0.015))[0]
                if len(idx_drop) > 0:
                    arr_times[j] = t[idx_drop[0]]
                else:
                    arr_times[j] = None
            all_burst_times[name] = arr_times

    summarize(all_pressure, all_burst_times)
