# Tabletop Water Pipeline Simulation & Leak Detection Suite

A dual-engine hydraulic modeling and transient burst simulation suite for the **tabletop physical prototype water pipeline network**. 

Combines **EPANET / WNTR** (quasi-steady state pressure-driven analysis) and **TSNet** (Method of Characteristics acoustic transient solver) to model intermittent water supply, detect sustained leaks, and localize sudden pipe bursts via Negative Pressure Waves (NPW).

---

## 1. Network Topology Specifications

* **Topology Model**: [`network.inp`](file:///d:/Working/Pipeline/water-26-08-21/network.inp)
* **Supply Head**: $1.5\text{ ft}$ ($0.4572\text{ m}$) gravity supply head from reservoir `R_MAIN`.
* **Main Pipeline**: Straight $1\text{-inch}$ ($25.4\text{ mm}$) diameter pipeline connecting junctions `J1`, `M12`, `J2`, `M23`, `J3`.
* **Progressive Branches**: $1/2\text{-inch}$ ($12.7\text{ mm}$) pipes leading to open collection tanks at $0\text{ m}$ head (free discharge):
  * **Branch 1** (at `J1`): 1 pipe leading up to `OUT_1A` $\to$ `TANK_1A`.
  * **Branch 2** (at `J2`): 2 pipes (cross) leading up to `OUT_2A` $\to$ `TANK_2A` and down to `OUT_2B` $\to$ `TANK_2B`.
  * **Branch 3** (at `J3`): 1 pipe leading up to `OUT_3A` $\to$ `TANK_3A`.
* **Intermittent Supply Window**:
  * 0–5 min: Pre-supply (valve `V_MAIN` closed, $0\text{ flow}$, $0\text{ pressure}$).
  * 5–15 min: Active supply window ($\approx 1.185\text{ L/s}$ normal flow).
  * 15–30 min: Supply shutoff (valve `V_MAIN` closed, flow returns to $0$).

---

## 2. Prerequisites & Installation

### Supported Python Versions
* **Recommended**: Python `3.10`, `3.11`, or `3.12`.
* **Python 3.14+**: Fully supported when the compatibility patch (`scripts/patch_tsnet.py`) is applied.

### Setup Instructions

1. **Clone or navigate to the repository directory**:
   ```bash
   cd water-26-08-21
   ```

2. **Create and activate a virtual environment**:
   * **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   * **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply TSNet Compatibility Patch (One-time setup)**:
   *TSNet 0.3.1 requires scalar casting patches to support modern NumPy versions:*
   ```bash
   python scripts/patch_tsnet.py
   ```

---

## 3. Repository Directory Structure

```
water-26-08-21/
├── network.inp               # EPANET input file for tabletop prototype network
├── rerun_all.py              # Master orchestrator script (runs all simulations & compiles dashboard)
├── generate_dashboard.py     # Compiles results/ into standalone interactive HTML dashboard
├── dashboard.html            # Standalone visualizer (PSM heatmaps, MOC transients, TDOA tables)
├── requirements.txt          # Python package dependencies
├── .gitignore                # Git ignore rules for bytecode, dumps, and virtual environments
├── README.md                 # Project documentation and engineering guide
│
├── results/                  # Structured simulation outputs
│   ├── epanet_normal/        # 30-minute quasi-steady baseline data (pressure.csv, flow.csv)
│   ├── epanet_leak/          # Pressure Sensitivity Matrix (PSM) leak scan per junction
│   ├── tsnet_normal/         # MOC transient baseline run (sub-millisecond resolution)
│   └── tsnet_burst/          # High-speed acoustic burst scan & wavefront arrival data
│
└── scripts/                  # Executable simulation modules
    ├── patch_tsnet.py        # One-time compatibility patch for tsnet library
    ├── epanet_normal_run.py  # Runs WNTR 30-min baseline supply simulation
    ├── epanet_leak_scan.py   # Runs WNTR leak scan across all network junctions
    ├── tsnet_normal_run.py   # Runs TSNet baseline MOC transient simulation
    └── tsnet_burst_scan.py   # Runs TSNet acoustic burst scan & computes TDOA
```

---

## 4. How to Run Simulations & Generate Dashboard

### Option A: Run Everything Automatically (Recommended)
Execute all simulation suites and regenerate `dashboard.html` in one command:
```bash
python rerun_all.py
```

### Option B: Run Specific Simulation Suites
* **Run only WNTR / EPANET quasi-steady simulations**:
  ```bash
  python rerun_all.py --epanet-only
  ```
* **Run only TSNet transient MOC burst simulations**:
  ```bash
  python rerun_all.py --tsnet-only
  ```
* **Recompile `dashboard.html` from existing `results/`**:
  ```bash
  python rerun_all.py --dashboard-only
  # or directly:
  python generate_dashboard.py
  ```

### Option C: Run Individual Scripts Manually
```bash
# 1. Steady-state runs
python scripts/epanet_normal_run.py
python scripts/epanet_leak_scan.py

# 2. Transient MOC runs
python scripts/tsnet_normal_run.py
python scripts/tsnet_burst_scan.py

# 3. Dashboard compilation
python generate_dashboard.py
```

---

## 5. Hydraulic Modeling Concepts & Physics

### A. Quasi-Steady Analysis (WNTR / EPANET)
* Solves the nonlinear algebraic energy and mass conservation equations at discrete intervals ($1.0\text{ minute}$).
* **Leak Modeling**: Modeled as pressure-driven orifice discharge ($Q = C_d A \sqrt{2gP}$).
* **Application**: Evaluates the **Pressure Sensitivity Matrix (PSM)**:
  $$\Delta P_i = P_{i,\text{baseline}} - P_{i,\text{leak}}$$
  Terminal branch ends (`OUT_1A`, `OUT_2A`, `OUT_3A`) exhibit the highest steady-state pressure drops ($\Delta P > 0.15\text{ m}$), making them ideal for static leak detection.

### B. Method of Characteristics Acoustic Transients (TSNet)
* Solves the 1D hyperbolic partial differential equations of transient pipe flow at sub-millisecond timesteps ($\Delta t \approx 0.0005\text{ s}$):
  $$\frac{\partial H}{\partial x} + \frac{1}{g}\frac{\partial v}{\partial t} + \frac{f v |v|}{2gD} = 0$$
  $$\frac{\partial H}{\partial t} + \frac{a^2}{g}\frac{\partial v}{\partial x} = 0$$
  where $a = 300\text{ m/s}$ (plastic/PVC tabletop scale wave speed).
* **Negative Pressure Wave (NPW)**: An abrupt rupture generates an acoustic decompression wave traveling away from the burst in both directions.
* **Burst Localization via Time Difference of Arrival (TDOA)**:
  Measuring wavefront arrival times at two boundary sensors (`J1` and `J3`) pinpoints the burst location ($x$) along the pipeline length ($L$):
  $$x = \frac{L - a \cdot (t_{J3} - t_{J1})}{2}$$

---

## 6. Sensor Placement Guidelines

* **Flow Monitoring (`V_MAIN`)**: Place directly downstream of the inlet control valve. Measures total inflow; any increase over baseline equals the exact leak discharge ($Q_{\text{leak}}$).
* **Main Boundary Pressure Transducers (`J1` & `J3`)**: Placed at the upstream entry and downstream dead-end of the straight main pipeline. Provides clean, unreflected acoustic wavefront timestamps for TDOA localization.
* **Branch Manifold Transducers (`OUT_1A` or `OUT_2A`)**: Placed on sub-distribution lines to capture localized static pressure drops ($80\%\text{–}90\%$ head collapse) that are attenuated on the main line.

---

## 7. Extended Engineering Documentation & Guides

Comprehensive technical references are organized in the [`docs/`](file:///d:/Working/Pipeline/water-26-08-21/docs) folder:

* **[Design & Physical Rationale Guide](file:///d:/Working/Pipeline/water-26-08-21/docs/design_and_physics_rationale.md)**:
  * In-depth physics Q&A explaining why steady-state EPANET lines stay constant while TSNet transient runs are short.
  * Mathematical derivation of the Joukowsky equation and why NPW is 40× stronger in small 1-inch pipes ($\frac{a}{gA} \approx 60,350$) than 12-inch city mains.
  * Analysis of laboratory boundaries on tabletop rigs: cavitation ceilings, $1.52\text{ ms}$ travel times, DAQ sampling ($10\text{–}50\text{ kHz}$), and valve actuation speeds.
  * Clarification of "acoustic/dynamic" vs. "static" pressure sensor terminology.
* **[ML Pipeline & Reporting Blueprint](file:///d:/Working/Pipeline/water-26-08-21/docs/ml_pipeline_and_reporting_framework.md)**:
  * End-to-end blueprint for reporting data logging, cleaning, EDA, feature extraction, and ML model training.
  * Recommended architectures: Autoencoders for anomaly detection, XGBoost / 1D-CNN / Graph Neural Networks (GNN) for branch localization, and Gradient Boosted Regressors for leak sizing.
  * Strategies for bridging the sim-to-real gap (noise injection, digital twin calibration, domain transfer).

