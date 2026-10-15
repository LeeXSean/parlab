"""Usage: python3 plot_a2.py a2-results.json a2-pools.svg"""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

records = json.loads(Path(sys.argv[1]).read_text())["records"]
cases = ["super_super_light", "math_operations_in_tight_for_loop",
         "spin_between_run_calls", "mandelbrot_chunked"]
labels = ["Super-super light", "Math loop", "Spin between calls", "Mandelbrot"]
implementations = ["Parallel + Always Spawn", "Parallel + Thread Pool + Spin",
                   "Parallel + Thread Pool + Sleep"]
data = {r["test"]: r["min_ms"]["gcc9"] for r in records if r["part"] == "part_a"}

with plt.rc_context({"font.size": 10, "svg.fonttype": "none"}):
    fig, ax = plt.subplots(figsize=(8.1, 3.9), layout="constrained")
    for offset, implementation, label, color in zip(
            [-0.25, 0, 0.25], implementations,
            ["Always spawn", "Spinning pool", "Sleeping pool"],
            ["#9da8af", "#627f91", "#344d5a"]):
        speedups = [data[case]["Serial"] / data[case][implementation] for case in cases]
        ax.bar(np.arange(len(cases)) + offset, speedups, width=0.23,
               label=label, color=color)
    ax.axhline(1, color="#777777", linewidth=0.8, linestyle="--")
    ax.set_xticks(np.arange(len(cases)), labels)
    ax.set_ylabel("Speedup over serial (same GCC 9.3 build)")
    ax.set_title("Part A · eight workers", loc="left", fontsize=12)
    ax.set_ylim(0, 8)
    ax.legend(frameon=False, ncols=3, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.yaxis.grid(color="#e4e4e4", linewidth=0.6)
    fig.savefig(sys.argv[2])
