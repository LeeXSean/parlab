"""Plot the 2–8-thread contiguous-block results for P1, step 2."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

here = Path(__file__).resolve().parent
rows = json.loads((here / 'results.json').read_text())
plt.rcParams.update({'font.size': 11, 'svg.fonttype': 'none'})
fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True, sharey=True, layout='constrained')
for view, ax in enumerate(axes, start=1):
    data = sorted((r for r in rows if r['group'] == 'p1' and r['view'] == view
                   and r['policy'] == 'blocks' and 2 <= r['threads'] <= 8),
                  key=lambda r: r['threads'])
    assert [r['threads'] for r in data] == list(range(2, 9))
    ax.plot([r['threads'] for r in data],
            [r['median_ms']['mandelbrot serial'] / r['median_ms']['mandelbrot thread'] for r in data],
            marker='o', markersize=4, color='#275e7a', label='Contiguous blocks')
    ax.plot([2, 8], [2, 8], '--', color='#999999', linewidth=1, label='Ideal linear reference')
    ax.set_title(f'View {view}', loc='left', fontsize=12)
    ax.set_ylabel('Speedup over serial')
    ax.grid(axis='y', color='#dddddd', linewidth=.6)
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_ylim(0, 8.5)
axes[0].legend(frameon=False, loc='upper left', fontsize=10)
axes[1].set_xlabel('Threads')
axes[1].set_xticks([2, 3, 4, 5, 6, 7, 8])
fig.savefig(here.parent / 'p1-scaling.svg', metadata={'Date': None})
