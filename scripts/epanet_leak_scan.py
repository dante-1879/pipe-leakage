"""
epanet_leak_scan.py
----------------------
Leak scan for network.inp — runs one WNTR quasi-steady simulation per
junction in the network, each time introducing a leak at that junction
partway through the valve-open window, then holds it open for the rest of
the run. Also includes a baseline (no-leak) run.

Junctions that can leak (true junctions, not fixed-head reservoirs):
  J1, J2, J3, OUT_1A, OUT_2A, OUT_2B, OUT_3A

Leak parameters are scaled to the network's 1/2-inch (12.7 mm) branch pipe
diameter — much smaller holes than the v3 leak scan (which used 25mm-dia
equivalent on a 25.4mm pipe). A 5mm hole on a 12.7mm pipe is already ~39%
of pipe area and produces physically large leaks at 0.4572 m supply head;
adjust LEAK_AREA below if you want smaller/larger scenarios.

Uses WNTRSimulator (not EpanetSimulator) because leak modelling
(Junction.add_leak) is only supported by the pure-Python WNTR engine.

Requires: pip install wntr
"""

import os
import shutil
import pandas as pd
import wntr
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE) == "scripts" else _HERE

INP_FILE    = os.path.join(_ROOT, "network.inp")
OUTPUT_ROOT = os.path.join(_ROOT, "results", "epanet_leak")

LEAK_START_TIME      = 8 * 60    # 8 min — inside the 5-15 min supply window
LEAK_END_TIME        = None       # stays open for rest of run
LEAK_AREA            = 5e-5      # m² ≈ 8 mm-diameter hole (scaled for 12.7mm pipe)
LEAK_DISCHARGE_COEFF = 0.75

JUNCTION_COLS  = ["J1", "M12", "J2", "M23", "J3", "OUT_1A", "OUT_2A", "OUT_2B", "OUT_3A"]
MAIN_PIPE_COLS = ["V_MAIN", "P_MAIN2A", "P_MAIN2B", "P_MAIN3A", "P_MAIN3B"]
BRANCH_COLS    = ["P_B1A", "P_TANK1A", "P_B2A", "P_TANK2A", "P_B2B", "P_TANK2B",
                  "P_B3A", "P_TANK3A"]


def build_network(leak_junction=None):
    wn = wntr.network.WaterNetworkModel(INP_FILE)
    if leak_junction is not None:
        node = wn.get_node(leak_junction)
        node.add_leak(
            wn,
            area=LEAK_AREA,
            discharge_coeff=LEAK_DISCHARGE_COEFF,
            start_time=LEAK_START_TIME,
            end_time=LEAK_END_TIME,
        )
    return wn


def run_scenario(name, leak_junction, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    wn  = build_network(leak_junction)
    sim = wntr.sim.WNTRSimulator(wn)
    results = sim.run_sim()

    full_idx = list(range(0, 1860, 60))
    pressure = results.node["pressure"].reindex(full_idx, fill_value=0.0)
    head     = results.node["head"].reindex(full_idx, fill_value=0.0)
    flow     = (results.link["flowrate"] * 1000).reindex(full_idx, fill_value=0.0)
    demand   = (results.node["demand"] * 1000).reindex(full_idx, fill_value=0.0)

    pressure.to_csv(os.path.join(out_dir, "pressure.csv"))
    head.to_csv(os.path.join(out_dir, "head.csv"))
    flow.to_csv(os.path.join(out_dir, "flow.csv"))
    demand.to_csv(os.path.join(out_dir, "demand.csv"))

    if leak_junction is not None:
        leak_demand = (results.node["leak_demand"][leak_junction] * 1000
                       ).reindex(full_idx, fill_value=0.0)
        leak_demand.to_frame(name="leak_flow_LPS").to_csv(
            os.path.join(out_dir, "leak_flow.csv")
        )
        peak_leak = leak_demand.max()
        print(f"[{name}] leak @ {leak_junction}: peak {peak_leak:.4f} LPS -> {out_dir}/")
    else:
        print(f"[{name}] baseline (no leak) -> {out_dir}/")

    plot_scenario(name, leak_junction, pressure, flow, out_dir)
    return pressure, flow


def plot_scenario(name, leak_junction, pressure, flow, out_dir):
    t_min = pressure.index / 60.0
    fig, axs = plt.subplots(2, 1, figsize=(12, 9), sharex=True)

    # Pressure
    junc_cols = [c for c in JUNCTION_COLS if c in pressure.columns]
    for col in junc_cols:
        lw = 2.2 if col == leak_junction else (1.8 if col in ("J1","J2","J3") else 1.1)
        axs[0].plot(t_min, pressure[col], lw=lw, label=f"Pressure {col}")
    axs[0].axvspan(5, 15, color="green", alpha=0.08, label="Supply window (5-15 min)")
    if leak_junction is not None:
        axs[0].axvline(LEAK_START_TIME / 60.0, color="red", ls="--", lw=1.5,
                       label=f"Leak starts @ {leak_junction} (t=8 min)")
    axs[0].set_ylabel("Pressure (m)")
    axs[0].set_title(f"v4 EPANET/WNTR PSM — Pressure — {name} (Supply Window: 5–15 min)")
    axs[0].legend(fontsize=7, ncol=3)
    axs[0].grid(alpha=0.3)

    # Flow
    main_cols   = [c for c in MAIN_PIPE_COLS if c in flow.columns]
    branch_cols = [c for c in BRANCH_COLS if c in flow.columns]
    for col in main_cols:
        axs[1].plot(t_min, flow[col], lw=1.8, label=f"Flow {col}")
    for col in branch_cols:
        axs[1].plot(t_min, flow[col], lw=1.1, ls="--", label=f"Flow {col}")
    axs[1].axvspan(5, 15, color="green", alpha=0.08, label="Supply window (5-15 min)")
    if leak_junction is not None:
        axs[1].axvline(LEAK_START_TIME / 60.0, color="red", ls="--", lw=1.5)
    axs[1].set_ylabel("Flow (LPS)")
    axs[1].set_xlabel("Time (min)")
    axs[1].set_title(f"v4 EPANET/WNTR PSM — Flow — {name}")
    axs[1].legend(fontsize=7, loc="upper right", ncol=3)
    axs[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{name}.png"), dpi=150)
    plt.close(fig)


def summarize(all_results):
    rows = []
    base_p = all_results["baseline"][0]
    junc_cols = [c for c in JUNCTION_COLS if c in base_p.columns]

    for name, (pressure, flow) in all_results.items():
        row = {"scenario": name}
        for col in junc_cols:
            # Evaluate at t = 10 min (600 s) during active leak supply window
            p_val = pressure.loc[600, col] if 600 in pressure.index else pressure[col].iloc[10]
            p_base = base_p.loc[600, col] if 600 in base_p.index else base_p[col].iloc[10]
            row[f"pressure_{col}"] = p_val
            row[f"drop_{col}"] = p_base - p_val
        rows.append(row)
    df = pd.DataFrame(rows).set_index("scenario")
    df.to_csv(os.path.join(OUTPUT_ROOT, "summary.csv"))
    print(f"\nSaved PSM summary (evaluated at t=10 min active leak window) -> {OUTPUT_ROOT}/summary.csv")
    print(df.to_string())


if __name__ == "__main__":
    if os.path.exists(OUTPUT_ROOT):
        shutil.rmtree(OUTPUT_ROOT)
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    wn_scan   = wntr.network.WaterNetworkModel(INP_FILE)
    junctions = list(wn_scan.junction_name_list)
    print(f"Junctions available for leak scan: {junctions}\n")

    all_results = {}
    all_results["baseline"] = run_scenario(
        "baseline", None, os.path.join(OUTPUT_ROOT, "baseline")
    )

    for j in junctions:
        name = f"leak_{j}"
        all_results[name] = run_scenario(
            name, j, os.path.join(OUTPUT_ROOT, name)
        )

    summarize(all_results)
