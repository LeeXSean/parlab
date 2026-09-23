"""Assignment 1 note measurements; only temporary copies are changed.

Usage: python3 benchmark.py REPO OUTPUT_DIRECTORY
The output directory must exist and contain no 'build' directory.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys

repo, out = map(lambda s: Path(s).resolve(), sys.argv[1:3])
baseline_revision = '11ea69fbb09570aa7cc2946ae3bc99ee04a19d30'
build = out / 'build'
build.mkdir()
shutil.copytree(repo / 'asst1/common', build / 'common')
records = []
log = (out / 'raw.log').open('w')

def run(cmd, cwd, allow_failure=False):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    text = p.stdout + p.stderr
    log.write(f'\n$ {cwd.name}: {" ".join(cmd)}\n{text}')
    log.flush()
    if p.returncode or (not allow_failure and re.search(r'Mismatch|Error:|Error :|@@@ Failed', text)):
        raise RuntimeError(text[-3000:])
    return text

def copy_program(prefix, name):
    src = next((repo / 'asst1').glob(prefix + '*'))
    dest = build / name
    dest.mkdir()
    for f in src.iterdir():
        if f.is_file() and (f.suffix in ('.cpp', '.h', '.ispc') or f.name == 'Makefile'):
            shutil.copy2(f, dest / f.name)
    return dest

def modify(path, old, new):
    s = path.read_text()
    assert old in s, (path, old)
    path.write_text(s.replace(old, new))

def compile_at(path):
    # Serial build: old ISPC Makefiles declare two outputs with one recipe.
    run(['make', '-s'], path)

def measure(path, exe, group, config, args=(), repeats=3):
    runs = []
    for n in range(repeats):
        output = run(['./' + exe, *args], path)
        times = {k: float(v) for k, v in re.findall(r'\[([^\]]+)\]:\s*\[([\d.]+)\] ms', output)}
        workers = [(int(i), float(t)) for i, t in re.findall(r'Thread (\d+): ([\d.]+) ms', output)]
        runs.append({'times_ms': times, 'workers_ms': workers})
    medians = {k: statistics.median(r['times_ms'][k] for r in runs) for k in runs[0]['times_ms']}
    record = {'group': group, **config, 'runs': runs, 'median_ms': medians, 'correct': True}
    records.append(record)
    (out / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
    print(group, config, medians, flush=True)

# P1: preserve timing prints in current code; reconstruct the earlier block
# policy only in a separate copy. The last block owns any leftover rows.
p1 = copy_program('prog1_', 'p1-interleaved')
compile_at(p1)
blocks = copy_program('prog1_', 'p1-blocks')
p = blocks / 'mandelbrotThread.cpp'
s = p.read_text()
start = s.index('    for (unsigned int i = args->threadId;')
end = s.index('    double endTime', start)
s = s[:start] + '''    int count = args->height / args->numThreads;
    int first = args->threadId * count;
    if (args->threadId == args->numThreads - 1) count = args->height - first;
    mandelbrotSerial(args->x0, args->y0, args->x1, args->y1,
                    args->width, args->height, first, count,
                    args->maxIterations, args->output);
''' + s[end:]
p.write_text(s)
compile_at(blocks)
for view in (1, 2):
    for n in (*range(2, 9), 16):
        for policy, path in [('blocks', blocks), ('interleaved', p1)]:
            if n == 16 and policy == 'blocks':
                continue
            measure(path, 'mandelbrot', 'p1', {'view': view, 'threads': n, 'policy': policy},
                    ['--view', str(view), '--threads', str(n)])

# P2: simulated instruction counts, not wall-clock speedups.
for width in (2, 4, 8, 16):
    p2 = copy_program('prog2_', f'p2-w{width}')
    p = p2 / 'CS149intrin.h'
    p.write_text(re.sub(r'#define VECTOR_WIDTH \d+', f'#define VECTOR_WIDTH {width}', p.read_text()))
    compile_at(p2)
    for n in (3, width, width * 2, 10000):
        output = run(['./myexp', '-s', str(n)], p2, allow_failure=True)
        exponent, total = output.split('ARRAY SUM', 1)
        records.append({'group': 'p2', 'width': width, 'n': n,
                        'clamped_pass': '@@@ Failed' not in exponent,
                        'sum_pass': None if n % width else '@@@ Failed' not in total,
                        'instructions': int(re.search(r'Total Vector Instructions: (\d+)', output)[1]),
                        'utilization': float(re.search(r'Vector Utilization:\s*([\d.]+)', output)[1])})
        print('p2', records[-1], flush=True)

# P3: every tested task count divides the fixed height (800).
for tasks in (2, 8, 32, 100, 200, 400, 800):
    p3 = copy_program('prog3_', f'p3-t{tasks}')
    p = p3 / 'mandelbrot.ispc'
    modify(p, 'height / 200', f'height / {tasks}')
    modify(p, 'launch[200]', f'launch[{tasks}]')
    compile_at(p3)
    for view in (1, 2):
        measure(p3, 'mandelbrot_ispc', 'p3', {'view': view, 'tasks': tasks}, ['--tasks', '--view', str(view)])

# P4: same kernels, different input arrays only.
for case in ('random', 'all-2.999', 'one-slow-seven-fast', 'all-1'):
    p4 = copy_program('prog4_', 'p4-' + case)
    if case != 'one-slow-seven-fast':
        p = p4 / 'main.cpp'
        s = p.read_text()
        start = s.index('    for (unsigned int i=0; i<N; i+=8)')
        end = s.index('    // generate a gold', start)
        expr = {'random': '.001f + 2.998f * static_cast<float>(rand()) / RAND_MAX',
                'all-2.999': '2.999f', 'all-1': '1.f'}[case]
        p.write_text(s[:start] + f'    for (unsigned int i=0; i<N; ++i) values[i] = {expr};\n\n' + s[end:])
    compile_at(p4)
    measure(p4, 'sqrt', 'p4', {'input': case})

p5 = copy_program('prog5_', 'p5')
compile_at(p5)
measure(p5, 'saxpy', 'p5', {'tasks': 64})

# P6 phase timings are diagnostic, not a replacement for the previously
# verified three-run whole-program baseline. No convergence changes.
for version in ('serial', 'parallel'):
    p6 = copy_program('prog6_', 'p6-profile-' + version)
    (p6 / 'data.dat').symlink_to(repo / 'asst1/prog6_kmeans/data.dat')
    p = p6 / 'kmeansThread.cpp'
    if version == 'serial':
        p.write_text(subprocess.check_output(['git', 'show', baseline_revision + ':asst1/prog6_kmeans/kmeansThread.cpp'], cwd=repo, text=True))
    modify(p, '  int iter = 0;', '  int iter = 0;\n  double phase[3] = {};')
    modify(p, '    computeAssignments(&args);\n    computeCentroids(&args);\n    computeCost(&args);', '''    double t = CycleTimer::currentSeconds();
    computeAssignments(&args);
    phase[0] += CycleTimer::currentSeconds() - t;
    t = CycleTimer::currentSeconds();
    computeCentroids(&args);
    phase[1] += CycleTimer::currentSeconds() - t;
    t = CycleTimer::currentSeconds();
    computeCost(&args);
    phase[2] += CycleTimer::currentSeconds() - t;''')
    modify(p, '  delete[] currCost;', '  printf("PROFILE %d %.3f %.3f %.3f\\n", iter, phase[0]*1000, phase[1]*1000, phase[2]*1000);\n  delete[] currCost;')
    compile_at(p6)
    output = run(['./kmeans'], p6)
    m = re.search(r'PROFILE (\d+) ([\d.]+) ([\d.]+) ([\d.]+)', output)
    records.append({'group': 'p6-profile', 'version': version, 'iterations': int(m[1]),
                    'assign_ms': float(m[2]), 'centroids_ms': float(m[3]), 'cost_ms': float(m[4])})
    print(records[-1], flush=True)

(out / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
manifest = {}
for p in (repo / 'asst1').rglob('*'):
    if p.is_file() and 'objs' not in p.parts and (p.suffix in ('.cpp', '.h', '.ispc') or p.name == 'Makefile'):
        manifest[str(p.relative_to(repo))] = hashlib.sha256(p.read_bytes()).hexdigest()
(out / 'source-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
