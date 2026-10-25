# Pipeline Design & Physical Rationale Guide

This document captures the physical theory, mathematical derivations, design decisions, and engineering trade-offs developed during the modeling of the **tabletop physical prototype water pipeline network**. It serves as a permanent reference for research defense, report drafting, and laboratory instrumentation design.

---

## Table of Contents
1. [Steady-State Hydraulics vs. Acoustic Water Hammer](#1-steady-state-hydraulics-vs-acoustic-water-hammer)
2. [Why the Post-Burst Pressure Drop Appears "Invisible"](#2-why-the-post-burst-pressure-drop-appears-invisible)
3. [Negative Pressure Wave (NPW) Physics in Small Tabletop Pipes](#3-negative-pressure-wave-npw-physics-in-small-tabletop-pipes)
4. [Sensor Clarifications: "Acoustic / Dynamic" vs. "Static" Transducers](#4-sensor-clarifications-acoustic--dynamic-vs-static-transducers)
5. [Sensor Placement: Main Pipeline vs. Sub-Distribution Lines](#5-sensor-placement-main-pipeline-vs-sub-distribution-lines)

---

## 1. Steady-State Hydraulics vs. Acoustic Water Hammer

A frequent point of confusion when comparing **EPANET / WNTR** and **TSNet** is why their charts appear so fundamentally different despite modeling the exact same network:

```
Pressure (m)
  ^
  |  Pre-Burst Steady
  |──────────────────────┐   /\    /\
  |                      |  /  \  /  \   <-- TSNet: Sub-second Acoustic Wave (MOC)
  |                      └──/    \/    \──────────────────────  Post-Burst Steady
  |                                                             (Identical in EPANET & TSNet)
  +───────────────────────────────────────────────────────────> Time
```

### Q: Why does EPANET just end in a flat, constant line?
* **In EPANET / WNTR (Quasi-Steady Solver)**:
  * **Before Minute 8**: Water flows freely from reservoir `R_MAIN` ($0.4572\text{ m}$ head) through open valve `V_MAIN` into the collection tanks at a constant rate ($\approx 1.185\text{ L/s}$). Pressure at `J2` is constant at $0.383\text{ m}$.
  * **At Minute 8**: An orifice (leak) opens. Water starts escaping through the hole.
  * **From Minute 8 to Minute 15**: The leak remains open, the supply valve remains open, and the reservoir head is constant.
  * **Why it stays constant**: EPANET is an algebraic energy-balance solver. Because boundary conditions do not change (valve stays open, reservoir does not empty), the network settles into a new permanent steady-state equilibrium ($0.369\text{ m}$ pressure, $1.27\text{ L/s}$ total inflow). It will stay at this exact line until a valve closes or the supply runs dry.

### Q: Why is there only data for 1 to 3 seconds in TSNet? What happens after that?
* **Acoustic Wave Travel Speed**: Acoustic pressure waves travel at $a = 300\text{ m/s}$ in $1\text{-inch}$ plastic/PVC pipe.
* **Network Dimensions**: The tabletop main pipeline is only $1.37\text{ meters}$ long.
* **Transit Time**:
  $$\tau = \frac{L}{a} = \frac{1.37\text{ m}}{300\text{ m/s}} = 0.00457\text{ s} \ (4.57\text{ milliseconds})$$
* In just **$1.0\text{ second}$**, the acoustic pressure wave has bounced back and forth between the reservoir and the open pipe ends **over 200 times**.
* Within $\approx 0.3\text{–}0.5\text{ seconds}$, fluid viscosity and pipe wall friction have completely absorbed and damped out all acoustic wave reflections.
* **What happens after 1 second?**
  The system becomes **completely stable**. The post-transient state TSNet reaches at $t = 1.0\text{–}2.0\text{ s}$ is **identical** to the steady state EPANET shows from minute 8 to 15. Running TSNet for 30 minutes would merely generate millions of redundant sub-millisecond timesteps displaying the exact same flat line.

---

## 2. Why the Post-Burst Pressure Drop Appears "Invisible"

When inspecting post-burst pressure on a full-scale chart, the line after the burst settles back close to the pre-burst level. 

### Numerical Comparison from Simulation:

| Parameter | Pre-Burst ($t < 0.5\text{ s}$) | During Burst ($t = 0.505\text{ s}$) | After Burst Settled ($t = 1.5\text{ s}$) |
| :--- | :---: | :---: | :---: |
| **`J2` Pressure Head** | **$0.3828\text{ m}$** | **$0.1592\text{ m}$** | **$0.3774\text{ m}$** |
| **Pressure Change ($\Delta H$)** | — | **$-0.2235\text{ m}$ ($-58\%$ drop!)** | **$-0.0054\text{ m}$ ($-5.4\text{ mm}$ drop)** |

### Why the Dynamic Drop is Violent, but the Settled Drop Looks Negligible:

1. **During the Rupture ($t = 0.50\text{–}0.52\text{ s}$)**:
   Water hammer physics governs the system via the **Joukowsky Equation**:
   $$\Delta H_{\text{dynamic}} = -\frac{a}{g \cdot A} \Delta Q$$
   Because $\frac{a}{g A} \approx 60,350$, even a small burst discharge of $\Delta Q \approx 0.007\text{ L/s}$ creates a massive dynamic shockwave drop of **$0.2235\text{ meters}$ (a $58\%$ plunge in head)**. This Negative Pressure Wave (NPW) travels at $300\text{ m/s}$ down the pipe.
2. **After the Shockwave Dissipates ($t > 0.6\text{ s}$)**:
   The pipeline returns to standard hydraulic friction governed by the Darcy-Weisbach / Hazen-Williams equations:
   $$\Delta h_{\text{friction}} = f \frac{L}{D} \frac{v^2}{2g}$$
   Because the tabletop pipe is only $0.457\text{ m}$ long between junctions, the extra friction loss from supplying the small leak is only **$0.0054\text{ meters}$ ($5.4\text{ millimeters}$)**.
3. **The Visual Scaling Effect**:
   On a chart scaled from $0$ to $0.5\text{ m}$ (or $0$ to $30\text{ m}$), a $5.4\text{ mm}$ difference is only a few screen pixels, causing the human eye to perceive the pre- and post-burst lines as identical.

---

## 3. Negative Pressure Wave (NPW) Physics in Small Tabletop Pipes

### Q: Does an NPW exist in a pipe this small and at pressures this low?
**Yes, physically and mathematically.** The 1D acoustic wave equation in a compressible fluid:
$$\frac{\partial^2 P}{\partial t^2} = a^2 \frac{\partial^2 P}{\partial x^2}$$
has no lower bound on pipe diameter or operating pressure. However, transitioning from a full-scale municipal main ($300\text{ mm}$ diameter, $50\text{ m}$ head, kilometers long) to a tabletop rig ($25.4\text{ mm}$ diameter, $0.457\text{ m}$ head, $1.37\text{ m}$ long) alters the physical regime and measurement requirements.

### 1. Why NPW is Actually Stronger in Small Pipes
According to the Joukowsky Equation:
$$\Delta H = -\frac{a}{g \cdot A} \Delta Q = -\frac{a}{g \cdot \frac{\pi D^2}{4}} \Delta Q$$
Notice that the cross-sectional area $A$ is in the **denominator**:
* In a $12\text{-inch}$ ($300\text{ mm}$) municipal main:
  $$\frac{a}{g A} \approx \frac{1200}{9.81 \cdot \frac{\pi (0.3)^2}{4}} \approx 1,730\text{ m / (m}^3\text{/s)}$$
* In your $1\text{-inch}$ ($25.4\text{ mm}$) tabletop pipe:
  $$\frac{a}{g A} \approx \frac{300}{9.81 \cdot \frac{\pi (0.0254)^2}{4}} \approx \mathbf{60,350\text{ m / (m}^3\text{/s)}}$$

Because the fluid column in a small-diameter pipe has very low cross-sectional inertia, **a tiny sudden leak generates a 35× to 40× larger pressure drop per unit discharge** than in a large transmission main.

---

### 2. The 3 Physical Constraints of Tabletop Testing

While the wave physically exists, validating it on a benchtop laboratory rig introduces three critical physical boundaries:

#### A. The Low-Pressure Cavitation & Air-Ingestion Ceiling
* In a municipal main at $50\text{ m}$ head ($5\text{ bar}$), an NPW dropping pressure by $10\text{ m}$ leaves the pipe at $40\text{ m}$ gauge pressure. Water remains fully pressurized, and the wave travels cleanly for kilometers.
* On a tabletop rig with only $0.4572\text{ m}$ head ($0.045\text{ bar} \approx 0.65\text{ psi}$):
  Any burst causing a dynamic drop greater than $0.4572\text{ m}$ creates a local vacuum. Air will be sucked in through the orifice or open discharge ends.
* **Effect of Air Ingestion**: Once air bubbles enter the water column, the mixture wave speed $a$ collapses from $300\text{ m/s}$ down to $30\text{ m/s}$, and the acoustic shockwave immediately dissipates.

#### B. Sub-Millisecond Transit Time (DAQ Sampling Challenge)
* In a $1\text{ km}$ city pipeline, travel time between sensors is $\approx 1.0\text{ second}$. A standard $100\text{ Hz}$ or $500\text{ Hz}$ logger easily detects the arrival edge.
* In your tabletop pipeline ($L = 0.4572\text{ m}$ between `J1` and `J2`):
  $$\tau = \frac{L}{a} = \frac{0.4572\text{ m}}{300\text{ m/s}} = \mathbf{0.001524\text{ s} \ (1.52\text{ milliseconds})}$$
* A standard Arduino microcontroller ADC sampling at $50\text{–}100\text{ Hz}$ ($10\text{–}20\text{ ms}$ interval) is far too slow to see the wave. To capture this wavefront in a physical lab, high-speed DAQs sampling at **$10\text{ kHz}$ to $50\text{ kHz}$** ($10,000\text{–}50,000$ samples/sec) are required.

#### C. Valve Actuation Speed ($t_c$) vs. Round-Trip Reflection Time ($\frac{2L}{a}$)
For a sharp, distinct Negative Pressure Wave step to form, the rupture or valve opening time $t_c$ must be faster than the acoustic round-trip time:
$$t_c < \frac{2L}{a} = \frac{2 \times 0.4572\text{ m}}{300\text{ m/s}} \approx \mathbf{3.0\text{ milliseconds}}$$
* Most physical solenoid valves take **$15\text{–}40\text{ ms}$** to actuate.
* If a physical valve takes $20\text{ ms}$ to open, the wave reflects back and forth 6 times while the valve is still opening. Rather than a sharp cliff, the sensor observes a smoothed ramp (exactly like the `burst_J2_ramp` scenario modeled in `scripts/tsnet_burst_scan.py`).

---

## 4. Sensor Clarifications: "Acoustic / Dynamic" vs. "Static" Transducers

### Q: What is meant by "acoustic dynamic sensors"? Isn't only pressure and flow being logged?
**Yes, exactly: you are only measuring Pressure and Flow.** There is no microphone or special audio sensor.

In fluid dynamics and pipeline literature:
* Sound is simply a mechanical pressure wave traveling through a compressible fluid.
* The term **"Acoustic Pressure Sensor"** or **"Dynamic Pressure Sensor"** simply refers to a **high-frequency pressure transducer** paired with a fast analog-to-digital converter (DAQ).

| Sensor Category | Variable Measured | Logging Frequency | Primary Project Application |
| :--- | :--- | :---: | :--- |
| **Static Pressure Transducer** | Fluid Head ($m$ or $psi$) | Slow ($1\text{–}10\text{ Hz}$) | **Scenario A (EPANET / PSM)**: Standard SCADA transmitters. Measures permanent, settled friction head losses ($\Delta P$). |
| **Dynamic Pressure Transducer** | Fluid Head ($m$ or $psi$) | Fast ($1\text{ kHz}\text{–}10\text{ kHz}$) | **Scenario B (TSNet / NPW)**: Piezoresistive/piezoelectric transducers. Fast enough to record the sub-millisecond wavefront arrival for TDOA. |

---

## 5. Sensor Placement: Main Pipeline vs. Sub-Distribution Lines

### Q: Why not place sensors on the sub-distribution branch lines (`OUT_1A`, `OUT_2A`) instead of the main line (`J1`, `J2`, `J3`)?
Both locations serve distinct, complementary roles:

### 1. Main Pipeline Placement (`J1`, `J2`, `J3`)
* **Optimal for Acoustic Wave TDOA Localization**:
  The main pipe is straight and uniform ($25.4\text{ mm}$). Placing sensors at `J1` (start) and `J3` (end) brackets the network spine without tee reflections, providing clean arrival times:
  $$x = \frac{L - a \cdot (t_{J3} - t_{J1})}{2}$$
* **Symmetry Breaking (`J2`)**: Placing a third sensor at the center cross distinguishes upstream bursts from downstream bursts.

### 2. Sub-Distribution Line Placement (`OUT_1A`, `OUT_2A`, `OUT_3A`)
* **Optimal for Static Head Loss Sensitivity (PSM)**:
  Because the branch pipes are half the diameter ($12.7\text{ mm}$ vs $25.4\text{ mm}$), their resistance is $32\times$ higher ($h_f \propto D^{-5}$).
  When an outlet leaks, the static pressure at `OUT_1A` drops by **$0.204\text{ m}$ (a $90\%$ head collapse)**, whereas the main line sensor at `J1` sees almost no steady-state change because it is held stiff by the reservoir.

### Q: If a leak is on an `OUT` line, can main sensors still approximate it?
**Yes:**
1. **The Inflow Meter (`V_MAIN`)** immediately registers the extra outflow, quantifying leak volume in $\text{L/s}$.
2. **The TDOA signature** on main sensors (`J1`, `J2`, `J3`) identifies which branch tee the wave exited from.
3. **Limitation**: Main sensors cannot distinguish between symmetrical branches connected to the same tee (e.g., upper branch `OUT_2A` vs. lower branch `OUT_2B` at `J2`).
