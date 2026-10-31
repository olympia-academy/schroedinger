"""Open the corrected default experiment paused, with limited CPU use.

Only process scheduling and display settings change; the physical setup,
grid, time step and saved frames are the same as the corrected 2D default.
"""
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(root / ".mpl-cache")
os.environ["MPLBACKEND"] = "TkAgg"
for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

if os.name == "nt":
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetPriorityClass.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.SetPriorityClass.restype = wintypes.BOOL
    handle = kernel.GetCurrentProcess()
    if not kernel.SetPriorityClass(handle, 0x4000):  # BELOW_NORMAL_PRIORITY_CLASS
        raise ctypes.WinError(ctypes.get_last_error())
    kernel.GetProcessAffinityMask.argtypes = (wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t))
    kernel.GetProcessAffinityMask.restype = wintypes.BOOL
    kernel.SetProcessAffinityMask.argtypes = (wintypes.HANDLE, ctypes.c_size_t)
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    available, system = ctypes.c_size_t(), ctypes.c_size_t()
    if kernel.GetProcessAffinityMask(handle, ctypes.byref(available), ctypes.byref(system)):
        one_cpu = 1 << (available.value.bit_length() - 1)
        if not kernel.SetProcessAffinityMask(handle, one_cpu):
            raise ctypes.WinError(ctypes.get_last_error())

print(f"Corrected 2D: low priority, one CPU, paused on opening. PID {os.getpid()}", flush=True)
import matplotlib
matplotlib.use("TkAgg", force=True)
import matplotlib.pyplot as plt
plt.ioff()
plt.rcParams["figure.dpi"] = 85
from schroedinger import Config2D, get_wave_packet, get_potential, get_barrier_mask, simulate
from schroedinger.visualization import animate

config = Config2D()
config.initial_values.wave_type = "plane_wave"
config.simulation_params.store_density = True
config.simulation_params.progress = False
potential, mask = get_potential(config), get_barrier_mask(config)
result = simulate(get_wave_packet(config), potential, config, mask)
animation = animate(result, config, potential, mask, interval=80, show=False)
animation._fig.canvas.draw()
animation._schroedinger_controls[0]._observers.process("clicked", None)
animation._fig.canvas.manager.set_window_title("Akademie Olympia - rettet 2D - lav belastning")
print("Ready. Press Play in the figure when you want the animation to start.", flush=True)
plt.show(block=True)
