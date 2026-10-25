import os
import tsnet
import numpy as np

tsnet_dir = os.path.dirname(tsnet.__file__)
print("TSNet directory:", tsnet_dir)

# 1. discretize.py
discretize_file = os.path.join(tsnet_dir, "network", "discretize.py")
with open(discretize_file, "r", encoding="utf-8") as f:
    disc_code = f.read()

# Replace Ndis assignment with scalar casting
disc_code = disc_code.replace(
    "pipe.number_of_segments = int(Ndis[i])",
    "pipe.number_of_segments = int(np.asarray(Ndis[i]).flatten()[0])"
)

# Replace adjust_wavev dt and pipe.wavev with scalar floats
old_adjust = """    # adjust time step
    dt = np.float64(1/theta)

    # adjust the wave speed of each links
    for _, pipe in tm.pipes():
        pipe.wavev = np.float64(pipe.wavev * phi[int(pipe.id)-1] * theta)

    # set time step as a new attribute to TransientModel
    tm.time_step =dt"""

new_adjust = """    theta_val = float(np.asarray(theta).flatten()[0])
    dt = float(1.0 / theta_val)

    for _, pipe in tm.pipes():
        pipe.wavev = float(np.asarray(pipe.wavev * phi[int(pipe.id)-1] * theta_val).flatten()[0])

    tm.time_step = dt"""

if old_adjust in disc_code:
    disc_code = disc_code.replace(old_adjust, new_adjust)
    print("Patched adjust_wavev in discretize.py")

with open(discretize_file, "w", encoding="utf-8") as f:
    f.write(disc_code)

# 2. model.py
model_file = os.path.join(tsnet_dir, "network", "model.py")
with open(model_file, "r", encoding="utf-8") as f:
    model_code = f.read()

model_code = model_code.replace("pump.status= LinkStatus.Open", "pump.initial_status = LinkStatus.Open")
model_code = model_code.replace("pump.status = LinkStatus.Open", "pump.initial_status = LinkStatus.Open")
model_code = model_code.replace("valve.status = LinkStatus.Open", "valve.initial_status = LinkStatus.Open")

with open(model_file, "w", encoding="utf-8") as f:
    f.write(model_code)
print("Patched model.py")

# 3. solver.py
solver_file = os.path.join(tsnet_dir, "simulation", "solver.py")
with open(solver_file, "r", encoding="utf-8") as f:
    solver_code = f.read()

# In add_leakage, make HP and VP scalar floats
old_leakage_ret = """    if nn == 0:  # pipe start
        VP = np.float64(-C2[:,0]+ C2[:,1]*HP)
    else:        # pipe end
        VP = np.float64(C1[:,0] - C1[:,1]*HP)
    return HP, VP"""

new_leakage_ret = """    if nn == 0:  # pipe start
        VP = np.float64(-C2[:,0]+ C2[:,1]*HP)
    else:        # pipe end
        VP = np.float64(C1[:,0] - C1[:,1]*HP)
    return float(np.asarray(HP).flatten()[0]), float(np.asarray(VP).flatten()[0])"""

if old_leakage_ret in solver_code:
    solver_code = solver_code.replace(old_leakage_ret, new_leakage_ret)
    print("Patched add_leakage in solver.py")

with open(solver_file, "w", encoding="utf-8") as f:
    f.write(solver_code)

print("TSNet all patches applied successfully!")
