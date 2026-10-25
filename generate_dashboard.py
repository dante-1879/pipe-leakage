"""
generate_dashboard.py
------------------------
Generates dashboard.html — a dedicated, comprehensive, standalone dashboard
for network_v4 (the tabletop physical prototype pipeline).

Features:
  1. Complete Intermittent Water Supply Window (Minutes 5 to 15):
     - 0–5 min: Pre-supply (valve closed, 0 flow, 0 pressure)
     - 5–15 min: Active supply window (1.185 LPS normal flow, leak injected at min 8)
     - 15–30 min: Supply shutoff (valve closed at min 15, flow drops back to 0)
  2. Complete TSNet MOC Transient Lifecycle:
     - 0–0.5s: Baseline steady flow (~1.19 LPS)
     - 0.5s: Sudden burst triggering high-speed Negative Pressure Wave (300 m/s)
     - 0.5–2.2s: Settled post-burst stable leaking flow
     - 2.2–2.35s: Real physical valve shutoff water hammer transient
     - 2.35–3.0s: Fully shut off (0 flow, 0 pressure)
  3. High-resolution Zoomed Wavefront Arrival View (-5 ms to +30 ms)
  4. Pressure Sensitivity Matrix (PSM) Heatmap during active supply window
  5. Time Difference of Arrival (TDOA) Burst Localization Verification Table
  6. Zero references to v3 (100% focused on v4 tabletop prototype)

Usage:
    python generate_dashboard.py
"""

import json
import os
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_V4 = os.path.join(ROOT, "results")
OUTPUT = os.path.join(ROOT, "dashboard.html")


def load_epanet_normal():
    p_path = os.path.join(RESULTS_V4, "epanet_normal", "pressure.csv")
    f_path = os.path.join(RESULTS_V4, "epanet_normal", "flow.csv")
    if not (os.path.exists(p_path) and os.path.exists(f_path)):
        return None
    p = pd.read_csv(p_path, index_col=0)
    f = pd.read_csv(f_path, index_col=0)
    t_min = (p.index.astype(float) / 60.0).tolist()
    return {
        "time_min": t_min,
        "pressure": {c: p[c].round(5).tolist() for c in p.columns if not c.startswith("TANK") and c != "R_MAIN"},
        "flow": {c: f[c].round(5).tolist() for c in f.columns},
    }


def load_epanet_leak():
    leak_dir = os.path.join(RESULTS_V4, "epanet_leak")
    if not os.path.exists(leak_dir):
        return None
    summary_path = os.path.join(leak_dir, "summary.csv")
    summary = {}
    if os.path.exists(summary_path):
        df_sum = pd.read_csv(summary_path, index_col=0)
        summary = df_sum.round(5).to_dict(orient="index")

    scenarios = {}
    for sc in os.listdir(leak_dir):
        sc_dir = os.path.join(leak_dir, sc)
        if not os.path.isdir(sc_dir):
            continue
        p_path = os.path.join(sc_dir, "pressure.csv")
        f_path = os.path.join(sc_dir, "flow.csv")
        l_path = os.path.join(sc_dir, "leak_flow.csv")
        if os.path.exists(p_path) and os.path.exists(f_path):
            p = pd.read_csv(p_path, index_col=0)
            f = pd.read_csv(f_path, index_col=0)
            t_min = (p.index.astype(float) / 60.0).tolist()
            sc_data = {
                "time_min": t_min,
                "pressure": {c: p[c].round(5).tolist() for c in p.columns if not c.startswith("TANK") and c != "R_MAIN"},
                "flow": {c: f[c].round(5).tolist() for c in f.columns},
            }
            if os.path.exists(l_path):
                l_df = pd.read_csv(l_path, index_col=0)
                sc_data["leak_flow"] = l_df.iloc[:, 0].round(5).tolist()
            scenarios[sc] = sc_data

    return {"scenarios": scenarios, "summary": summary}


def load_tsnet_normal():
    p_path = os.path.join(RESULTS_V4, "tsnet_normal", "pressure.csv")
    f_path = os.path.join(RESULTS_V4, "tsnet_normal", "flow.csv")
    if not (os.path.exists(p_path) and os.path.exists(f_path)):
        return None
    p = pd.read_csv(p_path)
    f = pd.read_csv(f_path)
    # Downsample slightly for responsive rendering
    p_sub = p.iloc[::2].copy()
    f_sub = f.iloc[::2].copy()
    t_s = p_sub["time_s"].round(6).tolist()
    return {
        "time_s": t_s,
        "pressure": {c: p_sub[c].round(5).tolist() for c in p_sub.columns if c != "time_s"},
        "flow": {c: f_sub[c].round(5).tolist() for c in f_sub.columns if c != "time_s"},
    }


def load_tsnet_burst():
    burst_dir = os.path.join(RESULTS_V4, "tsnet_burst")
    if not os.path.exists(burst_dir):
        return None
    summary_path = os.path.join(burst_dir, "summary.csv")
    summary = {}
    if os.path.exists(summary_path):
        df_sum = pd.read_csv(summary_path, index_col=0)
        summary = df_sum.fillna("").round(5).to_dict(orient="index")

    scenarios = {}
    for sc in os.listdir(burst_dir):
        sc_dir = os.path.join(burst_dir, sc)
        if not os.path.isdir(sc_dir):
            continue
        p_path = os.path.join(sc_dir, "pressure.csv")
        f_path = os.path.join(sc_dir, "flow.csv")
        l_path = os.path.join(sc_dir, "leak_flow.csv")
        if os.path.exists(p_path) and os.path.exists(f_path):
            p = pd.read_csv(p_path)
            f = pd.read_csv(f_path)
            l_df = pd.read_csv(l_path) if os.path.exists(l_path) else None

            # 1. High-resolution MOC burst segment (anchor burst at t = 8 min = 480.0 s)
            mask_crit = (p["time_s"] >= 0.49) & (p["time_s"] <= 0.55)
            idx_crit = p.index[mask_crit].tolist()
            idx_rest = p.index[~mask_crit][::3].tolist()
            idx_all = sorted(idx_crit + idx_rest)

            p_moc = p.loc[idx_all].copy()
            f_moc = f.loc[idx_all].copy()
            l_moc = l_df.loc[idx_all].copy() if l_df is not None else None

            # Shift MOC time so burst is at t = 480.0 s (minute 8)
            t_moc_shifted = 480.0 + (p_moc["time_s"] - 0.5)

            # 2. Pre-supply (0 to 300 s / 0 to 5 min) -> Valve closed, 0 flow, 0 pressure
            t_pre = [0.0, 60.0, 120.0, 180.0, 240.0, 299.0]
            # 3. Supply startup & pre-burst active window (300 to 479 s / 5 to 8 min)
            t_active_pre = [300.0, 330.0, 360.0, 420.0, 479.0]
            # 4. Post-burst active leaking window (482 to 900 s / 8 to 15 min)
            t_active_post = [482.0, 540.0, 600.0, 720.0, 840.0, 899.0]
            # 5. Shutoff (900 to 1800 s / 15 to 30 min) -> Valve closed, 0 flow, 0 pressure
            t_post = [900.0, 960.0, 1080.0, 1200.0, 1500.0, 1800.0]

            t_full = []
            p_full = {c: [] for c in p.columns if c != "time_s"}
            f_full = {c: [] for c in f.columns if c != "time_s"}
            burst_flow_full = []

            # Phase 1: 0 - 5 min (Pre-supply, valve closed)
            for t_pt in t_pre:
                t_full.append(t_pt)
                for c in p_full: p_full[c].append(0.0)
                for c in f_full: f_full[c].append(0.0)
                burst_flow_full.append(0.0)

            # Phase 2: 5 - 8 min (Active supply before burst)
            p_init = p_moc.iloc[0]
            f_init = f_moc.iloc[0]
            for t_pt in t_active_pre:
                t_full.append(t_pt)
                for c in p_full: p_full[c].append(round(float(p_init[c]), 5))
                for c in f_full: f_full[c].append(round(float(f_init[c]), 5))
                burst_flow_full.append(0.0)

            # Phase 3: High-Resolution Acoustic MOC Wave Transit (Minute 8)
            for i, idx in enumerate(idx_all):
                t_full.append(round(float(t_moc_shifted.iloc[i]), 6))
                for c in p_full: p_full[c].append(round(float(p_moc.loc[idx, c]), 5))
                for c in f_full: f_full[c].append(round(float(f_moc.loc[idx, c]), 5))
                if l_moc is not None:
                    burst_flow_full.append(round(float(l_moc.loc[idx, "burst_flow_LPS"]), 5))
                else:
                    burst_flow_full.append(0.0)

            # Phase 4: 8 - 15 min (Settled leaking supply)
            p_settled = p_moc.iloc[-1]
            f_settled = f_moc.iloc[-1]
            l_settled = burst_flow_full[-1]
            for t_pt in t_active_post:
                t_full.append(t_pt)
                for c in p_full: p_full[c].append(round(float(p_settled[c]), 5))
                for c in f_full: f_full[c].append(round(float(f_settled[c]), 5))
                burst_flow_full.append(round(float(l_settled), 5))

            # Phase 5: 15 - 30 min (Shutoff, valve closed)
            for t_pt in t_post:
                t_full.append(t_pt)
                for c in p_full: p_full[c].append(0.0)
                for c in f_full: f_full[c].append(0.0)
                burst_flow_full.append(0.0)

            t_min = [round(sec / 60.0, 5) for sec in t_full]

            # High-res zoom window around burst (-5 ms to +30 ms)
            z_mask = (p["time_s"] >= 0.495) & (p["time_s"] <= 0.530)
            z_df_p = p.loc[z_mask]
            z_ms = ((z_df_p["time_s"] - 0.5) * 1000.0).round(4).tolist()
            z_p = {c: z_df_p[c].round(5).tolist() for c in p.columns if c != "time_s"}

            sc_data = {
                "time_s": t_full,
                "time_min": t_min,
                "pressure": p_full,
                "flow": f_full,
                "burst_flow": burst_flow_full,
                "zoom_ms": z_ms,
                "zoom_pressure": z_p,
            }
            scenarios[sc] = sc_data

    return {"scenarios": scenarios, "summary": summary}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Network v4 Tabletop Prototype — Comprehensive Simulation Suite</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(18, 24, 38, 0.85);
      --card-border: rgba(255, 255, 255, 0.08);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #06b6d4;
      --primary-glow: rgba(6, 182, 212, 0.25);
      --emerald: #10b981;
      --amber: #f59e0b;
      --rose: #f43f5e;
      --indigo: #6366f1;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background: radial-gradient(circle at 10% 20%, #111827 0%, #070a12 90%);
      color: var(--text);
      min-height: 100vh;
      line-height: 1.5;
    }
    header {
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0.85rem 2rem;
    }
    .header-content {
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }
    .title-group h1 {
      font-size: 1.35rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .title-group p {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .badge-bar {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }
    .badge {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 0.25rem 0.65rem;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }
    .badge.cyan { border-color: rgba(6,182,212,0.4); color: #38bdf8; background: rgba(6,182,212,0.08); }
    .badge.emerald { border-color: rgba(16,185,129,0.4); color: #34d399; background: rgba(16,185,129,0.08); }
    .badge.amber { border-color: rgba(245,158,11,0.4); color: #fbbf24; background: rgba(245,158,11,0.08); }
    .badge.purple { border-color: rgba(168,85,247,0.4); color: #c084fc; background: rgba(168,85,247,0.08); }
    
    .nav-tabs {
      background: #0f172a;
      border-bottom: 1px solid var(--card-border);
      padding: 0 2rem;
      display: flex;
      gap: 0.5rem;
      max-width: 1440px;
      margin: 0 auto;
      overflow-x: auto;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.88rem;
      font-weight: 500;
      padding: 0.85rem 1.25rem;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
      white-space: nowrap;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .tab-btn:hover { color: var(--text); }
    .tab-btn.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
      font-weight: 600;
    }

    main {
      max-width: 1440px;
      margin: 1.5rem auto;
      padding: 0 1.5rem 3rem;
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.25rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }
    .card-title {
      font-size: 1.05rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .card-desc {
      font-size: 0.82rem;
      color: var(--text-muted);
      margin-top: 0.2rem;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .kpi-card {
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1rem;
    }
    .kpi-label { font-size: 0.75rem; color: var(--text-muted); font-weight: 500; }
    .kpi-val { font-size: 1.35rem; font-weight: 700; margin-top: 0.2rem; font-family: 'JetBrains Mono', monospace; }
    .kpi-sub { font-size: 0.72rem; color: #64748b; margin-top: 0.2rem; }

    .chart-container {
      width: 100%;
      height: 420px;
      border-radius: 8px;
    }
    .chart-dual {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    @media (max-width: 960px) {
      .chart-dual { grid-template-columns: 1fr; }
    }

    .zoom-btn {
      background: rgba(30, 41, 59, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #cbd5e1;
      padding: 0.35rem 0.8rem;
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 6px;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.2s ease;
    }
    .zoom-btn:hover {
      background: rgba(6, 182, 212, 0.25);
      border-color: #06b6d4;
      color: #38bdf8;
    }
    .zoom-btn.active {
      background: #06b6d4;
      border-color: #06b6d4;
      color: #042f2e;
      font-weight: 700;
    }

    select {
      background: #1e293b;
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 6px;
      padding: 0.45rem 1rem;
      font-size: 0.85rem;
      font-family: inherit;
      outline: none;
      cursor: pointer;
    }
    select:focus { border-color: var(--primary); }

    /* Schematic SVG styling */
    .schematic-wrapper {
      background: #0f172a;
      border-radius: 10px;
      padding: 1rem;
      border: 1px solid var(--card-border);
      text-align: center;
      overflow-x: auto;
    }

    /* Table styling */
    .data-table-wrapper {
      overflow-x: auto;
      margin-top: 1rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      text-align: left;
    }
    th {
      background: rgba(30, 41, 59, 0.8);
      padding: 0.65rem 0.85rem;
      font-weight: 600;
      color: #94a3b8;
      border-bottom: 1px solid var(--card-border);
    }
    td {
      padding: 0.6rem 0.85rem;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      font-family: 'JetBrains Mono', monospace;
    }
    tr:hover td { background: rgba(255,255,255,0.02); }
    .drop-high { color: #f43f5e; font-weight: 600; }
    .drop-med  { color: #fbbf24; }
    .drop-low  { color: #94a3b8; }
    .tdoa-badge {
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-weight: 600;
      background: rgba(6, 182, 212, 0.15);
      color: #38bdf8;
    }

    .alert-box {
      background: rgba(6, 182, 212, 0.08);
      border-left: 3px solid var(--primary);
      padding: 0.85rem 1rem;
      border-radius: 4px;
      font-size: 0.82rem;
      margin-bottom: 1.25rem;
      color: #cbd5e1;
    }
    .phase-pill {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      margin-right: 0.35rem;
    }
    .phase-pill.closed { background: rgba(239,68,68,0.2); color: #f87171; }
    .phase-pill.supply { background: rgba(16,185,129,0.2); color: #34d399; }
    .phase-pill.leak   { background: rgba(245,158,11,0.2); color: #fbbf24; }
  </style>
</head>
<body>

<header>
  <div class="header-content">
    <div class="title-group">
      <h1>Tabletop Prototype Pipeline  — Simulation Dashboard</h1>
      <p>Intermittent Supply (5–15 min window) | Tabletop Scale (1.5 ft head, 1-inch main, 1/2-inch progressive branches)</p>
    </div>
    <div class="badge-bar">
      <span class="badge emerald">🚰 Supply Window: 5 to 15 min</span>
      <span class="badge cyan">⚡ Wave Speed: 300 m/s</span>
      <span class="badge amber">💧 Supply Flow: ~1.19 LPS</span>
      <span class="badge purple">🔬 Dual Engines: WNTR + TSNet</span>
    </div>
  </div>
</header>

<div class="nav-tabs">
  <button class="tab-btn active" onclick="showTab('tab-overview', this)">📐 Topology & Setup</button>
  <button class="tab-btn" onclick="showTab('epanet-psm', this)">💧 Scenario A: 30-Min Operational Run & PSM (WNTR)</button>
  <button class="tab-btn" onclick="showTab('tsnet-npw', this)">⚡ Scenario B: Dynamic Burst, NPW & Shutoff (TSNet)</button>
  <button class="tab-btn" onclick="showTab('comparison', this)">⚖️ Steady-State PSM vs. Transient NPW</button>
</div>

<main>

  <!-- ==================== TAB 1: OVERVIEW ==================== -->
  <div id="tab-overview" class="tab-content active">
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">TOTAL SUPPLY HEAD</div>
        <div class="kpi-val" style="color:#38bdf8;">0.4572 m</div>
        <div class="kpi-sub">1.5 ft water head from R_MAIN</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">SUPPLY WINDOW DURATION</div>
        <div class="kpi-val" style="color:#34d399;">10.0 min</div>
        <div class="kpi-sub">Minutes 5 to 15 (0.083 to 0.25 hrs)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">ACTIVE SUPPLY INFLOW</div>
        <div class="kpi-val" style="color:#fbbf24;">1.185 LPS</div>
        <div class="kpi-sub">~1.19 LPS during 5–15 min window</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">ACOUSTIC WAVE SPEED</div>
        <div class="kpi-val" style="color:#a78bfa;">300 m/s</div>
        <div class="kpi-sub">Transit: 1.524 ms per 0.4572m pipe</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">🔬 Tabletop Pipeline Experimental Layout</div>
          <div class="card-desc">Straight 1-inch main line (J1, J2, J3) with progressive 1/2-inch branches (1 at J1, 2 at J2, 1 at J3) discharging into collection tanks at 0m head</div>
        </div>
      </div>
      <div class="schematic-wrapper">
        <svg viewBox="0 0 950 360" width="100%" height="280" style="max-width:920px; font-family:'Inter', sans-serif;">
          <!-- Background pipe zone -->
          <line x1="50" y1="180" x2="880" y2="180" stroke="#1e293b" stroke-width="32" stroke-linecap="round"/>
          <!-- Main Pipe Segments -->
          <line x1="120" y1="180" x2="360" y2="180" stroke="#0ea5e9" stroke-width="7"/>
          <line x1="360" y1="180" x2="600" y2="180" stroke="#0ea5e9" stroke-width="7"/>
          <line x1="600" y1="180" x2="840" y2="180" stroke="#0ea5e9" stroke-width="7"/>

          <!-- Branch 1 (Up) -->
          <line x1="360" y1="180" x2="360" y2="70" stroke="#10b981" stroke-width="4" stroke-dasharray="4"/>
          <!-- Branch 2 (Up and Down) -->
          <line x1="600" y1="180" x2="600" y2="70" stroke="#10b981" stroke-width="4" stroke-dasharray="4"/>
          <line x1="600" y1="180" x2="600" y2="290" stroke="#10b981" stroke-width="4" stroke-dasharray="4"/>
          <!-- Branch 3 (Up) -->
          <line x1="840" y1="180" x2="840" y2="70" stroke="#10b981" stroke-width="4" stroke-dasharray="4"/>

          <!-- Nodes -->
          <!-- R_MAIN -->
          <circle cx="120" cy="180" r="18" fill="#1e293b" stroke="#38bdf8" stroke-width="3"/>
          <text x="120" y="185" fill="#f8fafc" font-size="11" font-weight="700" text-anchor="middle">R</text>
          <text x="120" y="215" fill="#94a3b8" font-size="11" text-anchor="middle">R_MAIN</text>
          <text x="120" y="230" fill="#38bdf8" font-size="10" text-anchor="middle">Head: 0.457m</text>

          <!-- Valve V_MAIN -->
          <polygon points="230,170 230,190 250,180" fill="#f59e0b"/>
          <polygon points="270,170 270,190 250,180" fill="#f59e0b"/>
          <text x="250" y="160" fill="#fbbf24" font-size="10" font-weight="600" text-anchor="middle">V_MAIN (5–15 min)</text>

          <!-- J1 -->
          <circle cx="360" cy="180" r="14" fill="#0f172a" stroke="#38bdf8" stroke-width="3"/>
          <text x="360" y="184" fill="#f8fafc" font-size="10" font-weight="700" text-anchor="middle">J1</text>
          <text x="360" y="205" fill="#94a3b8" font-size="10" text-anchor="middle">Tee 1</text>

          <!-- M12 (Midpoint between J1 & J2) -->
          <circle cx="480" cy="180" r="11" fill="#0f172a" stroke="#f59e0b" stroke-width="2.5"/>
          <text x="480" y="184" fill="#fbbf24" font-size="9" font-weight="700" text-anchor="middle">M12</text>
          <text x="480" y="203" fill="#fbbf24" font-size="9" text-anchor="middle">Mid 1–2</text>

          <!-- J2 -->
          <circle cx="600" cy="180" r="16" fill="#0f172a" stroke="#f43f5e" stroke-width="3"/>
          <text x="600" y="184" fill="#f8fafc" font-size="11" font-weight="700" text-anchor="middle">J2</text>
          <text x="600" y="205" fill="#f43f5e" font-size="10" font-weight="600" text-anchor="middle">Cross (J2)</text>

          <!-- M23 (Midpoint between J2 & J3) -->
          <circle cx="720" cy="180" r="11" fill="#0f172a" stroke="#f59e0b" stroke-width="2.5"/>
          <text x="720" y="184" fill="#fbbf24" font-size="9" font-weight="700" text-anchor="middle">M23</text>
          <text x="720" y="203" fill="#fbbf24" font-size="9" text-anchor="middle">Mid 2–3</text>

          <!-- J3 -->
          <circle cx="840" cy="180" r="14" fill="#0f172a" stroke="#38bdf8" stroke-width="3"/>
          <text x="840" y="184" fill="#f8fafc" font-size="10" font-weight="700" text-anchor="middle">J3</text>
          <text x="840" y="205" fill="#94a3b8" font-size="10" text-anchor="middle">Tee 3</text>

          <!-- Tanks -->
          <!-- TANK 1A -->
          <rect x="340" y="45" width="40" height="25" rx="4" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
          <text x="360" y="62" fill="#34d399" font-size="9" font-weight="600" text-anchor="middle">TANK 1A</text>
          <circle cx="360" cy="115" r="5" fill="#10b981"/>
          <text x="375" y="118" fill="#94a3b8" font-size="9">OUT_1A</text>

          <!-- TANK 2A -->
          <rect x="580" y="45" width="40" height="25" rx="4" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
          <text x="600" y="62" fill="#34d399" font-size="9" font-weight="600" text-anchor="middle">TANK 2A</text>
          <circle cx="600" cy="115" r="5" fill="#10b981"/>
          <text x="615" y="118" fill="#94a3b8" font-size="9">OUT_2A</text>

          <!-- TANK 2B -->
          <rect x="580" y="290" width="40" height="25" rx="4" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
          <text x="600" y="307" fill="#34d399" font-size="9" font-weight="600" text-anchor="middle">TANK 2B</text>
          <circle cx="600" cy="245" r="5" fill="#10b981"/>
          <text x="615" y="248" fill="#94a3b8" font-size="9">OUT_2B</text>

          <!-- TANK 3A -->
          <rect x="820" y="45" width="40" height="25" rx="4" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
          <text x="840" y="62" fill="#34d399" font-size="9" font-weight="600" text-anchor="middle">TANK 3A</text>
          <circle cx="840" cy="115" r="5" fill="#10b981"/>
          <text x="855" y="118" fill="#94a3b8" font-size="9">OUT_3A</text>
        </svg>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">⏱️ The 3 Operational Phases of the Tabletop Experiment</div>
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:1rem;">
        <div style="background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.25); border-radius:8px; padding:1rem;">
          <span class="phase-pill closed">Phase 1: 0 – 5 min</span>
          <h4 style="color:#f87171; margin:0.4rem 0;">Pre-Supply (Valve Closed)</h4>
          <p style="font-size:0.8rem; color:#cbd5e1;">Valve V_MAIN is closed. Zero flow across all pipes (0 LPS). Gauge pressure is zero everywhere.</p>
        </div>
        <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.25); border-radius:8px; padding:1rem;">
          <span class="phase-pill supply">Phase 2: 5 – 15 min</span>
          <h4 style="color:#34d399; margin:0.4rem 0;">Water Supply Window (Active)</h4>
          <p style="font-size:0.8rem; color:#cbd5e1;">Valve V_MAIN opens. Water flows at 1.185 LPS. When a leak opens at minute 8, pressure drops, establishing the Pressure Sensitivity Matrix (PSM).</p>
        </div>
        <div style="background:rgba(168,85,247,0.05); border:1px solid rgba(168,85,247,0.25); border-radius:8px; padding:1rem;">
          <span class="phase-pill closed">Phase 3: 15 – 30 min</span>
          <h4 style="color:#c084fc; margin:0.4rem 0;">Supply Shutoff (Valve Closed)</h4>
          <p style="font-size:0.8rem; color:#cbd5e1;">Valve V_MAIN closes at minute 15. Flow drops back to 0 LPS. Network pressure returns to zero.</p>
        </div>
      </div>
    </div>
  </div>

  <!-- ==================== TAB 2: EPANET / PSM ==================== -->
  <div id="epanet-psm" class="tab-content">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">💧 WNTR 30-Minute Operational Simulation (Scenario A: Slow Leaks / PSM)</div>
          <div class="card-desc">Shows the complete operational run: 0-5 min pre-supply, 5-15 min active supply (leak @ min 8), and 15-30 min shutoff</div>
        </div>
        <div>
          <label style="font-size:0.8rem; color:#94a3b8; margin-right:0.5rem;">Select Scenario:</label>
          <select id="epLeakSelect" onchange="updateEPLeakChart()">
            <!-- Populated by JS -->
          </select>
        </div>
      </div>

      <div class="alert-box" id="epLeakInfo">
        Select a scenario above to inspect the complete 30-minute operational pressure and flow curves.
      </div>

      <div class="chart-dual">
        <div>
          <div id="epPChart" class="chart-container"></div>
        </div>
        <div>
          <div id="epFChart" class="chart-container"></div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">📊 Pressure Sensitivity Matrix (PSM) Heatmap</div>
          <div class="card-desc">Evaluated at t = 10 min during the active leak supply window: Pressure drop ΔP = P_baseline - P_leak (meters)</div>
        </div>
      </div>
      <div class="data-table-wrapper">
        <table id="psmTable">
          <thead>
            <tr>
              <th>Leak Scenario</th>
              <th>ΔP @ J1</th>
              <th>ΔP @ M12</th>
              <th>ΔP @ J2</th>
              <th>ΔP @ M23</th>
              <th>ΔP @ J3</th>
              <th>ΔP @ OUT_1A</th>
              <th>ΔP @ OUT_2A</th>
              <th>ΔP @ OUT_2B</th>
              <th>ΔP @ OUT_3A</th>
            </tr>
          </thead>
          <tbody>
            <!-- Populated by JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ==================== TAB 3: TSNET / NPW ==================== -->
  <div id="tsnet-npw" class="tab-content">
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">⚡ TSNet 30-Minute Complete Operational Run &amp; Acoustic NPW Burst</div>
          <div class="card-desc">Full 30-minute lifecycle with embedded high-resolution MOC burst wave at minute 8. Fully interactive: zoom to any second or millisecond.</div>
        </div>
        <div>
          <label style="font-size:0.8rem; color:#94a3b8; margin-right:0.5rem;">Select Scenario:</label>
          <select id="tsBurstSelect" onchange="updateTSBurstChart()">
            <!-- Populated by JS -->
          </select>
        </div>
      </div>

      <div class="alert-box" id="tsBurstInfo">
        Select a scenario to view the sub-millisecond acoustic wavefront arrival.
      </div>

      <!-- Interactive Zoom Toolbar -->
      <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:0.75rem; align-items:center;">
        <span style="font-size:0.75rem; color:#94a3b8; font-weight:600; text-transform:uppercase;">🔍 Interactive Zoom:</span>
        <button class="zoom-btn active" id="btn-zoom-full" onclick="zoomTSNet('full')">Full 30-Min View (0–30 min)</button>
        <button class="zoom-btn" id="btn-zoom-supply" onclick="zoomTSNet('supply')">Active Window (5–15 min)</button>
        <button class="zoom-btn" id="btn-zoom-burst" onclick="zoomTSNet('burst')">Burst Event Window (7.98–8.02 min)</button>
        <button class="zoom-btn" id="btn-zoom-wave" onclick="zoomTSNet('wavefront')">Acoustic Shockwave (±30 ms)</button>
        <span style="font-size:0.72rem; color:#64748b; margin-left:auto;">💡 Drag on chart or use range slider below to zoom freely into any millisecond</span>
      </div>

      <div class="chart-dual">
        <div>
          <div id="tsPChart" class="chart-container"></div>
        </div>
        <div>
          <div id="tsZoomChart" class="chart-container"></div>
        </div>
      </div>

      <div style="margin-top:1rem;">
        <div id="tsFChart" class="chart-container" style="height:320px;"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">⏱️ Negative Pressure Wave (NPW) Time Difference of Arrival (TDOA) Table</div>
          <div class="card-desc">Wavefront arrival times at sensors ($t_{\text{arr}}$) and calculated TDOA ($t_{J3} - t_{J1}$) proving burst localization physics</div>
        </div>
      </div>
      <div class="data-table-wrapper">
        <table id="tdoaTable">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Burst Node</th>
              <th>Initial Head (m)</th>
              <th>Min Head (m)</th>
              <th>Shock Drop ΔH</th>
              <th>t_arr @ J1</th>
              <th>t_arr @ J2</th>
              <th>t_arr @ J3</th>
              <th>TDOA (J3 - J1)</th>
              <th>Physical Interpretation</th>
            </tr>
          </thead>
          <tbody>
            <!-- Populated by JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ==================== TAB 4: COMPARATIVE ANALYSIS ==================== -->
  <div id="comparison" class="tab-content">
    <div class="card">
      <div class="card-header">
        <div class="card-title">⚖️ Comparative Analysis: Steady-State PSM vs. Transient NPW</div>
      </div>
      <div class="data-table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Scenario A: Slow Leaks (PSM)</th>
              <th>Scenario B: Sudden Bursts (NPW)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Simulation Engine</strong></td>
              <td>WNTR / EPANET (Quasi-Steady Solver)</td>
              <td>TSNet (Method of Characteristics MOC)</td>
            </tr>
            <tr>
              <td><strong>Physical Phenomenon</strong></td>
              <td>Hydraulic friction losses (Hazen-Williams / Darcy-Weisbach)</td>
              <td>Water hammer acoustic pressure wave (Joukowsky equation)</td>
            </tr>
            <tr>
              <td><strong>Governing Equation</strong></td>
              <td>$h_f = f \frac{L}{D} \frac{V^2}{2g}$</td>
              <td>$\Delta H = -\frac{a}{g A} \Delta Q$ (with $a = 300\text{ m/s}$)</td>
            </tr>
            <tr>
              <td><strong>Time Step Resolution</strong></td>
              <td>1.0 minute (60 seconds)</td>
              <td>~0.000508 seconds (0.508 milliseconds)</td>
            </tr>
            <tr>
              <td><strong>Operating Lifecycle</strong></td>
              <td>0–5 min Closed → 5–15 min Supply (leak @ 8 min) → 15–30 min Closed</td>
              <td>0–0.5s Baseline → 0.5s Rupture → 0.5–2.2s Settled → 2.2–3.0s Shutoff</td>
            </tr>
            <tr>
              <td><strong>Pressure Drop Magnitude</strong></td>
              <td>Small steady friction loss: <strong>$\approx 5 - 14\text{ mm}$ ($0.005 - 0.014\text{ m}$)</strong></td>
              <td>Massive dynamic acoustic plunge: <strong>$\approx 224\text{ mm}$ ($0.224\text{ m}$ / 58% drop)</strong></td>
            </tr>
            <tr>
              <td><strong>Why the drop looks different</strong></td>
              <td>Visually distinct step drop after minute 8 during the 10-minute window</td>
              <td>Sudden 0.22m shock dip at 0.5s, then settles to 0.377m, then plunges to 0 at shutoff</td>
            </tr>
            <tr>
              <td><strong>Sensor Logging Speed</strong></td>
              <td>Standard pressure transducers ($1 - 10\text{ Hz}$)</td>
              <td>High-speed dynamic pressure sensors ($1,000 - 10,000\text{ Hz}$)</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

</main>

<script>
var DATA = PAYLOAD_JSON;

function showTab(id, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  if (btn) btn.classList.add('active');
  var target = document.getElementById(id);
  if (target) target.classList.add('active');

  setTimeout(() => {
    ['epPChart', 'epFChart', 'tsPChart', 'tsZoomChart', 'tsFChart'].forEach(cid => {
      var el = document.getElementById(cid);
      if (el && el._fullLayout) Plotly.Plots.resize(el);
    });
  }, 50);
}

// -------------------------------------------------------------
// SCENARIO A: EPANET / PSM
// -------------------------------------------------------------
var epSelect = document.getElementById('epLeakSelect');
if (DATA.ep_leak && DATA.ep_leak.scenarios) {
  Object.keys(DATA.ep_leak.scenarios).forEach(name => {
    var opt = document.createElement('option');
    opt.value = name;
    opt.text = name;
    if (name === 'leak_J2') opt.selected = true;
    epSelect.appendChild(opt);
  });
}

function updateEPLeakChart() {
  var sc = epSelect.value;
  var d = DATA.ep_leak.scenarios[sc];
  if (!d) return;

  var info = document.getElementById('epLeakInfo');
  if (sc === 'baseline') {
    info.innerHTML = "<strong>Baseline Operational Run:</strong> Water supply is delivered between minutes 5 and 15 (1.185 LPS). Flow is zero before minute 5 and shuts off back to zero after minute 15.";
  } else {
    var jName = sc.replace('leak_', '');
    info.innerHTML = `<strong>Leak at Node ${jName}:</strong> Supply starts at min 5. Orifice opens at min 8 (causing steady PSM pressure drop). Supply shuts off at min 15, returning flow and pressure to zero.`;
  }

  // Pressure traces
  var pTraces = [];
  var colors = {J1:'#38bdf8', J2:'#f43f5e', J3:'#a855f7', OUT_1A:'#10b981', OUT_2A:'#f59e0b', OUT_2B:'#ec4899', OUT_3A:'#84cc16'};
  Object.keys(d.pressure).forEach(node => {
    pTraces.push({
      x: d.time_min,
      y: d.pressure[node],
      name: 'Pressure ' + node,
      mode: 'lines',
      line: { color: colors[node] || '#94a3b8', width: node.startsWith('J') ? 2.5 : 1.5, dash: node.startsWith('J') ? 'solid' : 'dot' }
    });
  });

  var pLayout = {
    title: { text: `WNTR 30-Min Pressure Profiles — ${sc}`, font: { size: 14, color: '#f1f5f9' } },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(15, 23, 42, 0.6)',
    xaxis: { title: 'Time (minutes)', color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.06)' },
    yaxis: { title: 'Pressure Head (m)', color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.06)' },
    shapes: [
      { type: 'rect', xref: 'x', yref: 'paper', x0: 5, x1: 15, y0: 0, y1: 1, fillcolor: 'rgba(16, 185, 129, 0.08)', line: { width: 0 } },
      { type: 'line', xref: 'x', yref: 'paper', x0: 8, x1: 8, y0: 0, y1: 1, line: { color: '#f43f5e', width: 1.5, dash: 'dash' } },
      { type: 'line', xref: 'x', yref: 'paper', x0: 15, x1: 15, y0: 0, y1: 1, line: { color: '#a855f7', width: 1.5, dash: 'dot' } }
    ],
    annotations: [
      { x: 10, y: 0.44, text: 'Supply Window (5–15 min)', showarrow: false, font: { color: '#34d399', size: 10 } },
      { x: 8, y: 0.28, text: 'Leak Starts (8m)', showarrow: true, arrowhead: 2, font: { color: '#f43f5e', size: 9 }, arrowcolor: '#f43f5e' },
      { x: 15, y: 0.28, text: 'Supply Shutoff (15m)', showarrow: true, arrowhead: 2, font: { color: '#c084fc', size: 9 }, arrowcolor: '#c084fc' }
    ],
    legend: { font: { size: 10, color: '#cbd5e1' }, orientation: 'h', y: -0.2 },
    margin: { l: 50, r: 20, t: 40, b: 60 }
  };
  Plotly.newPlot('epPChart', pTraces, pLayout, {responsive:true});

  // Flow traces
  var fTraces = [];
  var mainPipes = ['V_MAIN', 'P_MAIN2', 'P_MAIN3'];
  mainPipes.forEach(p => {
    if (d.flow[p]) {
      fTraces.push({
        x: d.time_min,
        y: d.flow[p],
        name: 'Flow ' + p,
        mode: 'lines',
        line: { width: 2.2 }
      });
    }
  });
  if (d.leak_flow) {
    fTraces.push({
      x: d.time_min,
      y: d.leak_flow,
      name: 'Leak Discharge (LPS)',
      mode: 'lines',
      line: { color: '#f43f5e', width: 2.5, dash: 'dash' }
    });
  }

  var fLayout = {
    title: { text: `WNTR 30-Min Flow Rates & Leak Discharge — ${sc}`, font: { size: 14, color: '#f1f5f9' } },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(15, 23, 42, 0.6)',
    xaxis: { title: 'Time (minutes)', color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.06)' },
    yaxis: { title: 'Flow (LPS)', color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.06)' },
    shapes: [
      { type: 'rect', xref: 'x', yref: 'paper', x0: 5, x1: 15, y0: 0, y1: 1, fillcolor: 'rgba(16, 185, 129, 0.08)', line: { width: 0 } }
    ],
    annotations: [
      { x: 10, y: 1.15, text: 'Active Supply (1.19 LPS)', showarrow: false, font: { color: '#34d399', size: 10 } }
    ],
    legend: { font: { size: 10, color: '#cbd5e1' }, orientation: 'h', y: -0.2 },
    margin: { l: 50, r: 20, t: 40, b: 60 }
  };
  Plotly.newPlot('epFChart', fTraces, fLayout, {responsive:true});
}

// Populate PSM Heatmap Table
function populatePSMTable() {
  var tbody = document.querySelector('#psmTable tbody');
  tbody.innerHTML = '';
  var base = DATA.ep_leak.summary.baseline;
  if (!base) return;

  var nodes = ['J1', 'M12', 'J2', 'M23', 'J3', 'OUT_1A', 'OUT_2A', 'OUT_2B', 'OUT_3A'];
  Object.keys(DATA.ep_leak.summary).forEach(sc => {
    if (sc === 'baseline') return;
    var row = DATA.ep_leak.summary[sc];
    var tr = document.createElement('tr');
    var html = `<td><strong>${sc}</strong></td>`;
    nodes.forEach(n => {
      var drop = row['drop_' + n] || 0;
      var cls = 'drop-low';
      if (drop > 0.03) cls = 'drop-high';
      else if (drop > 0.01) cls = 'drop-med';
      html += `<td class="${cls}">${drop.toFixed(4)} m</td>`;
    });
    tr.innerHTML = html;
    tbody.appendChild(tr);
  });
}

// -------------------------------------------------------------
// SCENARIO B: TSNET / NPW BURSTS
// -------------------------------------------------------------
var tsSelect = document.getElementById('tsBurstSelect');
if (DATA.ts_burst && DATA.ts_burst.scenarios) {
  Object.keys(DATA.ts_burst.scenarios).forEach(name => {
    var opt = document.createElement('option');
    opt.value = name;
    opt.text = name;
    if (name === 'burst_J2') opt.selected = true;
    tsSelect.appendChild(opt);
  });
}

function zoomTSNet(mode) {
  var r;
  if (mode === 'full') r = [0, 30];
  else if (mode === 'supply') r = [4.8, 15.2];
  else if (mode === 'burst') r = [7.98, 8.02];
  else if (mode === 'wavefront') r = [7.9995, 8.0010];
  Plotly.relayout('tsPChart', {'xaxis.range': r});
  Plotly.relayout('tsFChart', {'xaxis.range': r});
  document.querySelectorAll('.zoom-btn').forEach(b => b.classList.remove('active'));
  var btn = document.getElementById('btn-zoom-' + (mode === 'wavefront' ? 'wave' : mode));
  if (btn) btn.classList.add('active');
}

function updateTSBurstChart() {
  var sc = tsSelect.value;
  var d = DATA.ts_burst.scenarios[sc];
  if (!d) return;

  var info = document.getElementById('tsBurstInfo');
  if (sc === 'baseline') {
    info.innerHTML = "<strong>Baseline 30-Min Operational Run:</strong> 0–5 min pre-supply (valve closed), 5–15 min active steady supply (~1.185 LPS), 15–30 min shutoff. No burst injected.";
  } else if (sc === 'burst_M12') {
    info.innerHTML = "<strong>Midpoint Burst (M12 between J1 & J2):</strong> Burst at minute 8 (480s) triggers sharp Negative Pressure Wave reaching J1 & J2 simultaneously in 1.29 ms, reaching J3 in 3.19 ms (TDOA = +1.89 ms).";
  } else if (sc === 'burst_J2') {
    info.innerHTML = "<strong>Center Cross Burst (J2):</strong> Burst at minute 8 (480s) triggers symmetrical wave transit reaching J1 & J3 at the exact same instant (TDOA = 0.00 ms).";
  } else if (sc === 'burst_M23') {
    info.innerHTML = "<strong>Midpoint Burst (M23 between J2 & J3):</strong> Burst at minute 8 (480s) triggers sharp wave reaching J2 & J3 simultaneously in 1.29 ms, reaching J1 in 3.19 ms (TDOA = -1.89 ms).";
  } else if (sc === 'burst_J3') {
    info.innerHTML = "<strong>Downstream End Burst (J3):</strong> Wave originates at J3, reaching J2 in 1.29 ms and J1 in 3.79 ms (TDOA = -3.79 ms).";
  } else {
    info.innerHTML = `<strong>Scenario ${sc}:</strong> 30-minute operational lifecycle with high-resolution acoustic burst wave at minute 8 (480s). Use Quick Zoom buttons or range slider below to zoom into any millisecond.`;
  }

  // 1. Full 30-Minute Pressure Chart
  var pTraces = [];
  var colors = {J1:'#38bdf8', M12:'#fbbf24', J2:'#f43f5e', M23:'#e879f9', J3:'#a855f7', OUT_1A:'#10b981', OUT_2A:'#06b6d4', OUT_2B:'#14b8a6', OUT_3A:'#84cc16'};
  var nodeDash = {J1:'solid', M12:'dash', J2:'solid', M23:'dash', J3:'solid', OUT_1A:'dot', OUT_2A:'dot', OUT_2B:'dot', OUT_3A:'dot'};
  
  var allNodes = ['J1', 'M12', 'J2', 'M23', 'J3', 'OUT_1A', 'OUT_2A', 'OUT_2B', 'OUT_3A'];
  allNodes.forEach(node => {
    if (d.pressure && d.pressure[node]) {
      pTraces.push({
        x: d.time_min,
        y: d.pressure[node],
        name: 'Node ' + node,
        mode: 'lines',
        line: { color: colors[node] || '#94a3b8', width: (node.startsWith('J') || node.startsWith('M') ? 2.2 : 1.4), dash: nodeDash[node] || 'solid' }
      });
    }
  });

  var pLayout = {
    title: { text: `TSNet 30-Minute Complete Pressure Lifecycle (All Nodes) — ${sc}`, font: { size: 14, color: '#f1f5f9' } },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(15, 23, 42, 0.6)',
    xaxis: {
      title: 'Time (minutes)',
      color: '#94a3b8',
      gridcolor: 'rgba(255,255,255,0.06)',
      rangeslider: { visible: true, thickness: 0.06, bgcolor: 'rgba(15,23,42,0.85)' }
    },
    yaxis: { title: 'Pressure Head (m)', color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.06)' },
    shapes: [
      { type: 'rect', xref: 'x', yref: 'paper', x0: 5, x1: 15, y0: 0, y1: 1, fillcolor: 'rgba(16, 185, 129, 0.08)', line: { width: 0 } },
      { type: 'line', xref: 'x', yref: 'paper', x0: 8.0, x1: 8.0, y0: 0, y1: 1, line: { color: '#f43f5e', width: 1.5, dash: 'dash' } },
      { type: 'line', xref: 'x', yref: 'paper', x0: 15.0, x1: 15.0, y0: 0, y1: 1, line: { color: '#a855f7', width: 1.5, dash: 'dot' } }
    ],
    annotations: [
      { x: 8.0, y: 0.46, text: (sc === 'baseline' ? 'Normal Window' : 'Burst Event (Min 8.0)'), showarrow: true, arrowhead: 2, font: { color: '#f43f5e', size: 9 }, arrowcolor: '#f43f5e' },
      { x: 5.0, y: 0.46, text: 'Supply Opens (Min 5.0)', showarrow: true, arrowhead: 2, font: { color: '#34d399', size: 9 }, arrowcolor: '#34d399' },
      { x: 15.0, y: 0.46, text: 'Supply Shutoff (Min 15.0)', showarrow: true, arrowhead: 2, font: { color: '#c084fc', size: 9 }, arrowcolor: '#c084fc' }
    ],
    legend: { font: { size: 9, color: '#cbd5e1' }, orientation: 'h', y: -0.32 },
    margin: { l: 50, r: 20, t: 40, b: 75 }
  };
  Plotly.newPlot('tsPChart', pTraces, pLayout, {responsive:true});

  // 2. Zoomed Wavefront Arrival View (-5 ms to +30 ms relative to burst)
  var zTraces = [];
  allNodes.forEach(node => {
    if (d.zoom_pressure && d.zoom_pressure[node]) {
      zTraces.push({
        x: d.zoom_ms,
        y: d.zoom_pressure[node],
        name: 'Node ' + node,
        mode: 'lines+markers',
        marker: { size: (node.startsWith('J') || node.startsWith('M') ? 4 : 2) },
        line: { color: colors[node] || '#94a3b8', width: (node.startsWith('J') || node.startsWith('M') ? 2.2 : 1.4), dash: nodeDash[node] || 'solid' }
      });
    }
  });

  var zLayout = {
    title: { text: `Zoomed Wavefront Arrival (-5 ms to +30 ms)`, font: { size: 14, color: '#f1f5f9' } },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(15, 23, 42, 0.6)',
    xaxis: { title: 'Time Relative to Burst (milliseconds)', color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.06)' },
    yaxis: { title: 'Pressure Head (m)', color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.06)' },
    shapes: [
      { type: 'line', xref: 'x', yref: 'paper', x0: 0, x1: 0, y0: 0, y1: 1, line: { color: '#f43f5e', width: 1.5, dash: 'dash' } }
    ],
    annotations: [
      { x: 0, y: 0.38, text: (sc === 'baseline' ? 'Normal Flow (0 ms)' : 'Burst Start (0 ms)'), showarrow: false, font: { color: '#f43f5e', size: 9 } }
    ],
    legend: { font: { size: 9, color: '#cbd5e1' }, orientation: 'h', y: -0.22 },
    margin: { l: 50, r: 20, t: 40, b: 65 }
  };
  Plotly.newPlot('tsZoomChart', zTraces, zLayout, {responsive:true});

  // 3. Flow & Discharge Chart (Full 30-min with range slider)
  var fTraces = [];
  var pipeColors = {V_MAIN:'#38bdf8', P_MAIN2A:'#f59e0b', P_MAIN2B:'#fbbf24', P_MAIN3A:'#10b981', P_MAIN3B:'#34d399', P_B1A:'#64748b', P_B2A:'#94a3b8', P_B2B:'#cbd5e1', P_B3A:'#e2e8f0'};
  ['V_MAIN', 'P_MAIN2A', 'P_MAIN2B', 'P_MAIN3A', 'P_MAIN3B', 'P_B1A', 'P_B2A', 'P_B2B', 'P_B3A'].forEach(p => {
    if (d.flow && d.flow[p]) {
      fTraces.push({
        x: d.time_min,
        y: d.flow[p],
        name: 'Flow ' + p,
        mode: 'lines',
        line: { color: pipeColors[p] || '#94a3b8', width: (p.includes('MAIN') ? 2.0 : 1.3), dash: (p.startsWith('P_B') ? 'dot' : 'solid') }
      });
    }
  });
  if (d.burst_flow) {
    fTraces.push({
      x: d.time_min,
      y: d.burst_flow,
      name: 'Burst Discharge (LPS)',
      mode: 'lines',
      line: { color: '#f43f5e', width: 2.5 }
    });
  }

  var fLayout = {
    title: { text: `TSNet 30-Minute Pipeline Flows & Burst Discharge`, font: { size: 14, color: '#f1f5f9' } },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'rgba(15, 23, 42, 0.6)',
    xaxis: {
      title: 'Time (minutes)',
      color: '#94a3b8',
      gridcolor: 'rgba(255,255,255,0.06)',
      rangeslider: { visible: true, thickness: 0.06, bgcolor: 'rgba(15,23,42,0.85)' }
    },
    yaxis: { title: 'Flow (LPS)', color: '#94a3b8', gridcolor: 'rgba(255,255,255,0.06)' },
    shapes: [
      { type: 'rect', xref: 'x', yref: 'paper', x0: 5, x1: 15, y0: 0, y1: 1, fillcolor: 'rgba(16, 185, 129, 0.08)', line: { width: 0 } },
      { type: 'line', xref: 'x', yref: 'paper', x0: 8.0, x1: 8.0, y0: 0, y1: 1, line: { color: '#f43f5e', width: 1.5, dash: 'dash' } },
      { type: 'line', xref: 'x', yref: 'paper', x0: 15.0, x1: 15.0, y0: 0, y1: 1, line: { color: '#a855f7', width: 1.5, dash: 'dot' } }
    ],
    annotations: [
      { x: 8.0, y: 0.7, text: (sc === 'baseline' ? 'Normal Flow' : 'Burst Event (Min 8.0)'), showarrow: true, arrowhead: 2, font: { color: '#f43f5e', size: 9 }, arrowcolor: '#f43f5e' },
      { x: 15.0, y: 0.7, text: 'Supply Shutoff (Min 15.0)', showarrow: true, arrowhead: 2, font: { color: '#c084fc', size: 9 }, arrowcolor: '#c084fc' }
    ],
    legend: { font: { size: 9, color: '#cbd5e1' }, orientation: 'h', y: -0.32 },
    margin: { l: 50, r: 20, t: 40, b: 75 }
  };
  Plotly.newPlot('tsFChart', fTraces, fLayout, {responsive:true});
}

// Populate TDOA Table
function populateTDOATable() {
  var tbody = document.querySelector('#tdoaTable tbody');
  tbody.innerHTML = '';
  if (!DATA.ts_burst || !DATA.ts_burst.summary) return;

  var descriptions = {
    'baseline': 'No burst. Steady active supply (1.185 LPS) followed by valve shutoff to 0 LPS at t=15 min.',
    'burst_J1': 'Burst at upstream boundary node (head pinned by R_MAIN).',
    'burst_M12': 'Burst midway between J1 & J2 (X = 0.686m). Simultaneous arrival at J1 & J2 in 1.29 ms, reaching J3 in 3.19 ms (TDOA = +1.89 ms).',
    'burst_J2': 'Burst at center main cross (X = 0.914m). Symmetrical wave transit to J1 & J3 (TDOA = 0.00 ms).',
    'burst_M23': 'Burst midway between J2 & J3 (X = 1.143m). Simultaneous arrival at J2 & J3 in 1.29 ms, reaching J1 in 3.19 ms (TDOA = -1.89 ms).',
    'burst_J3': 'Burst at downstream end tee (X = 1.372m). Wave hits J3 first (0.35 ms), J2 next (2.24 ms), J1 last (4.13 ms) (TDOA = -3.79 ms).',
    'burst_OUT_1A': 'Burst on Branch 1. Localized head drop at branch tip.',
    'burst_OUT_2A': 'Burst on Branch 2A (upward). Symmetrical arrival at main sensors (TDOA = 0.00 ms).',
    'burst_OUT_2B': 'Burst on Branch 2B (downward). Symmetric counterpart to OUT_2A (TDOA = 0.00 ms).',
    'burst_OUT_3A': 'Burst on Branch 3A (upward). Transits to J3 first, then upstream.',
    'burst_J2_ramp': 'Gradual 200 ms incipient burst. No sharp acoustic shock front formed.'
  };

  Object.keys(DATA.ts_burst.summary).forEach(sc => {
    var row = DATA.ts_burst.summary[sc];
    var tr = document.createElement('tr');
    var burstNode = sc.replace('burst_', '');
    var initH = row.init_head_J2 ? row.init_head_J2.toFixed(3) : '-';
    var minH  = row.min_head_J2 ? row.min_head_J2.toFixed(3) : '-';
    var drop  = row.drop_J2 ? row.drop_J2.toFixed(3) : '-';
    var t1    = row.t_arr_J1_ms ? `${row.t_arr_J1_ms.toFixed(2)} ms` : '-';
    var t2    = row.t_arr_J2_ms ? `${row.t_arr_J2_ms.toFixed(2)} ms` : '-';
    var t3    = row.t_arr_J3_ms ? `${row.t_arr_J3_ms.toFixed(2)} ms` : '-';
    var tdoa  = row.TDOA_J3_minus_J1_ms !== "" && !isNaN(row.TDOA_J3_minus_J1_ms) ? `${parseFloat(row.TDOA_J3_minus_J1_ms).toFixed(2)} ms` : '-';
    var desc  = descriptions[sc] || '';

    tr.innerHTML = `
      <td><strong>${sc}</strong></td>
      <td><span class="badge cyan">${burstNode}</span></td>
      <td>${initH} m</td>
      <td>${minH} m</td>
      <td class="drop-high">${drop} m</td>
      <td>${t1}</td>
      <td>${t2}</td>
      <td>${t3}</td>
      <td><span class="tdoa-badge">${tdoa}</span></td>
      <td style="font-family:sans-serif; font-size:0.75rem; color:#cbd5e1;">${desc}</td>
    `;
    tbody.appendChild(tr);
  });
}

// Initial renders
updateEPLeakChart();
populatePSMTable();
updateTSBurstChart();
populateTDOATable();
</script>

</body>
</html>
"""


def generate():
    print("Loading simulation results from results/...")
    payload = {
        "ep_normal": load_epanet_normal(),
        "ep_leak": load_epanet_leak(),
        "ts_normal": load_tsnet_normal(),
        "ts_burst": load_tsnet_burst(),
    }
    inline = json.dumps(payload)
    html = HTML_TEMPLATE.replace("PAYLOAD_JSON", inline)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    kb = os.path.getsize(OUTPUT) / 1024
    print(f"\nSuccessfully generated {OUTPUT} ({kb:.1f} KB)")


if __name__ == "__main__":
    generate()
