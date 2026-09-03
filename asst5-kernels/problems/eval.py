import gc
import base64
import dataclasses
import multiprocessing
import re
import time
import os
import sys
import math
from pathlib import Path
from typing import Any, Optional

import torch.cuda

from utils import set_seed, clear_l2_cache
try:
    from task import TestSpec
except ImportError:
    TestSpec = dict

from reference import check_implementation, generate_input


class PopcornOutput:
    def __init__(self, fd: int):
        self.file = os.fdopen(fd, 'w')
        os.set_inheritable(fd, False)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
    
    def print(self, *args, **kwargs):
        print(*args, **kwargs, file=self.file, flush=True)
    
    def log(self, key, value):
        self.print(f"{key}: {value}")


@dataclasses.dataclass
class TestCase:
    args: dict
    spec: str


def _combine(a: int, b: int) -> int:
    # combine two integers into one:
    # we need this to generate a secret seed based on the test-level seed and
    # the global secret seed.
    # the test-level seeds are public knowledge, and typically relatively small numbers,
    # so we need to make sure they don't provide any useful info for the full seed.
    # This Cantor construction ensures that if the secret seed is a large number,
    # then so is the overall seed.
    return int(a + (a+b)*(a+b+1)//2)


def get_test_cases(file_name: str, seed: Optional[int]) -> list[TestCase]:
    try:
        content = Path(file_name).read_text()
    except Exception as E:
        print(f"Could not open test file`{file_name}`: {E}", file=sys.stderr)
        exit(113)

    tests = []
    lines = content.splitlines()
    match = r"\s*([a-zA-Z_][a-zA-Z0-9_]*):\s*([a-zA-Z_][a-zA-Z0-9_]*|[+-]?[0-9]+)\s*"
    for line in lines:
        parts = line.split(";")
        case = {}
        for part in parts:
            matched = re.match(match, part)
            if not re.fullmatch(match, part):
                print(f"invalid test case: '{line}': '{part}'", file=sys.stderr)
                exit(113)
            key = matched[1]
            val = matched[2]
            try:
                val = int(val)
            except ValueError:
                pass

            case[key] = val
        tests.append(TestCase(spec=line, args=case))

    if seed is not None:
        for test in tests:
            if "seed" in test.args:
                test.args["seed"] = _combine(test.args["seed"], seed)

    return tests


@dataclasses.dataclass
class Stats:
    runs: int
    mean: float
    std: float
    err: float
    best: float
    worst: float


def calculate_stats(durations: list[int]):
    """
    Calculate statistical data from a list of durations.

    @param durations: A list of durations in nanoseconds.
    @return: A Stats object containing the number of runs, mean, standard deviation, error, best, and worst durations.
    """
    runs = len(durations)
    total = sum(durations)
    best = min(durations)
    worst = max(durations)

    avg = total / runs
    variance = sum(map(lambda x: (x - avg)**2, durations))
    std = math.sqrt(variance / (runs - 1))
    err = std / math.sqrt(runs)

    return Stats(runs=runs, mean=avg, std=std, err=err, best=float(best),
                 worst=float(worst))


def _clone_data(data):
    """
    Recursively goes through data and clones all tensors.
    """
    if isinstance(data, tuple):
        return tuple(_clone_data(x) for x in data)
    elif isinstance(data, list):
        return [_clone_data(x) for x in data]
    elif isinstance(data, dict):
        return {k: _clone_data(v) for k, v in data.items()}
    elif isinstance(data, torch.Tensor):
        return data.clone()
    else:
        return data


def _run_single_test(test: TestCase):
    """
    Runs a single test case. Do not call directly
    """
    from submission import custom_kernel
    data = generate_input(**test.args)
    torch.cuda.synchronize()
    submission_output = custom_kernel(_clone_data(data))
    torch.cuda.synchronize()
    return check_implementation(data, submission_output)

def run_single_test(pool: multiprocessing.Pool, test: TestCase):
    """
    Runs a single test in another process with timeout.
    """
    try:
        result = pool.apply_async(_run_single_test, (test,))
        return result.get(timeout=30)  # 30 second timeout
    except multiprocessing.TimeoutError:
        # Process hung, terminate it
        pool.terminate()
        pool.join()
        return False, "Test timed out after 30 seconds"
    except Exception as e:
        return False, f"Test failed with exception: {str(e)}"


def run_testing(logger: PopcornOutput, pool: multiprocessing.Pool, tests: list[TestCase]):
    """
    Executes the actual test case code and checks for correctness.

    @param logger: A PopcornOutput object used for logging test results.
    @param tests: A list of TestCase objects representing the test cases to be executed.
    @return: An integer representing the exit status: 0 if all tests pass, otherwise 112.
    """
    passed = True
    logger.log("test-count", len(tests))
    for idx, test in enumerate(tests):
        logger.log(f"test.{idx}.spec", test.spec)
        good, message = run_single_test(pool, test)
        if not good:
            logger.log(f"test.{idx}.status", "fail")
            logger.log(f"test.{idx}.error", message)
            passed = False
        else:
            logger.log(f"test.{idx}.status", "pass")
            if message:
                logger.log(f"test.{idx}.message", message)

    clean_up_ninja_files()
    if passed:
        logger.log("check", "pass")
        return 0
    else:
        logger.log("check", "fail")
        return 112


def _run_single_benchmark(test: TestCase, recheck: bool, max_repeats: int, max_time_ns: float) -> Stats | Any:
    """
    Runs one benchmark. Do not call directly.
    """
    from submission import custom_kernel

    durations = []
    # generate input data once
    data = generate_input(**test.args)
    check_copy = _clone_data(data)
    #  first, one obligatory correctness check
    output = custom_kernel(data)
    good, message = check_implementation(check_copy, output)
    if not good:
        return message

    # now, do multiple timing runs without further correctness testing
    # there is an upper bound of 100 runs, and a lower bound of 3 runs;
    # otherwise, we repeat until we either measure at least 10 full seconds,
    # or the relative error of the mean is below 1%.

    bm_start_time = time.perf_counter_ns()
    for i in range(max_repeats):
        if recheck:
            # Force Python Garbage Collection
            gc.collect()
            # Force PyTorch to release cached memory back to OS/allocator
            torch.cuda.empty_cache()

            # ensure we use a different seed for every benchmark
            if "seed" in test.args:
                test.args["seed"] += 13

            data = generate_input(**test.args)
            check_copy = _clone_data(data)
        torch.cuda.synchronize()
        start_event = torch.cuda.Event(enable_timing=True)
        end_event = torch.cuda.Event(enable_timing=True)
        clear_l2_cache()

        start_event.record()
        output = custom_kernel(data)
        end_event.record()
        torch.cuda.synchronize()
        # duration = start_event.elapsed_time(end_event) * 1e6  # Convert ms to ns
        duration = start_event.elapsed_time(end_event)

        if recheck:
            good, message = check_implementation(check_copy, output)
            if not good:
                return message

        del output
        durations.append(duration)

        if i > 1:
            total_bm_duration = time.perf_counter_ns() - bm_start_time
            stats = calculate_stats(durations)
            # stop if either
            # a) relative error dips below 0.1%
            # b) we exceed the total time limit for benchmarking the kernel
            # c) we exceed 2 minutes of total wallclock time.
            if stats.err / stats.mean < 0.001 or stats.mean * stats.runs > max_time_ns or total_bm_duration > 120e9:
                break

    return calculate_stats(durations)


def run_single_benchmark(pool: multiprocessing.Pool, test: TestCase, recheck: bool, max_repeats: int,
                         max_time_ns: float):
    """
    For a particular test case, check correctness (if applicable) and grab runtime results.

    @param pool: Process on which the benchmark will be launched.
    @param test: TestCase object.
    @param recheck: Flag for whether to explicitly check functional correctness.
    @param max_repeats: Number of trials to repeat.
    @param max_time_ns: Timeout time in nanoseconds.
    @return: A Stats object for this particular benchmark case or an error if the test fails.
    """
    return pool.apply(_run_single_benchmark, (test, recheck, max_repeats, max_time_ns))


def run_benchmarking(logger: PopcornOutput, pool: multiprocessing.Pool, tests: list[TestCase]):
    """
    Executes benchmarking code for a CUDA Kernel and logs runtimes.

    @param logger: A PopcornOutput object used for logging benchmark results.
    @param pool: Process on which the benchmarks will be launched.
    @param tests: A list of TestCase objects representing the test cases to be benchmarked.
    @return: An integer representing the exit status: 0 if all benchmarks pass, otherwise 112.
    """
    def fmt(x):
        if isinstance(x, float):
            return f"{x:,.3f}"      # comma + 3 decimals
        return f"{x:,}"             # integers get commas only

    # warm up
    run_single_benchmark(pool, tests[0], False, 100, 10e7)

    passed = True
    logger.log("benchmark-count", len(tests))
    for idx, test in enumerate(tests):
        logger.log(f"benchmark.{idx}.spec", test.spec)
        result = run_single_benchmark(pool, test, False, 100, 10e9)

        if isinstance(result, Stats):
            lines = []
            for field in dataclasses.fields(Stats):
                val = getattr(result, field.name)
                if field.name == "runs":
                    lines.append(f"{field.name}={fmt(val)}")
                else:
                    lines.append(f"{field.name}={fmt(val)} ms")
            logger.log(f"benchmark.{idx}", ", ".join(lines))

        # if isinstance(result, Stats):
        #     for field in dataclasses.fields(Stats):
        #         logger.log(f"benchmark.{idx}.{field.name}", getattr(result, field.name))
        else:
            passed = False
            logger.log(f"benchmark.{idx}.status", "fail")
            logger.log(f"benchmark.{idx}.error", result)

    clean_up_ninja_files()
    if passed:
        logger.log("check", "pass")
        return 0
    else:
        logger.log("check", "fail")
        return 112

def parse_ncu_report(file_path):
    import ncu_report
    my_context = ncu_report.load_report(file_path)
    
    # Define metrics with their nicknames and types
    metrics = {
        'gpu__time_duration.sum': {
            'nickname': 'Duration',
            'type': 'Counter',
            'unit': 'ns'
        },
        'sm__throughput.avg.pct_of_peak_sustained_elapsed': {
            'nickname': 'Compute_Throughput',
            'type': 'Throughput',
            'unit': '%'
        },
        'sm__instruction_throughput.avg.pct_of_peak_sustained_active': {
            'nickname': 'SM_Busy',
            'type': 'Throughput',
            'unit': '%'
        },
        'l1tex__throughput.avg.pct_of_peak_sustained_elapsed': {
            'nickname': 'L1_Cache_Throughput',
            'type': 'Throughput',
            'unit': '%'
        },
        'lts__throughput.avg.pct_of_peak_sustained_elapsed': {
            'nickname': 'L2_Cache_Throughput',
            'type': 'Throughput',
            'unit': '%'
        },
        'gpu__dram_throughput.avg.pct_of_peak_sustained_elapsed': {
            'nickname': 'DRAM_Throughput',
            'type': 'Throughput',
            'unit': '%'
        },
        'l1tex__t_sector_hit_rate.pct': {
            'nickname': 'L1_Cache_Hit_Rate',
            'type': 'Ratio',
            'unit': '%'
        },
        'lts__t_sector_hit_rate.pct': {
            'nickname': 'L2_Cache_Hit_Rate',
            'type': 'Ratio',
            'unit': '%'
        },
        'dram__bytes_read.sum': {
            'nickname': 'DRAM_Read',
            'type': 'Counter',
            'unit': 'bytes'
        },
        'dram__bytes_write.sum': {
            'nickname': 'DRAM_Write',
            'type': 'Counter',
            'unit': 'bytes'
        },
        'l1tex__m_xbar2l1tex_read_bytes.sum': {
            'nickname': 'L2_to_L1_Traffic',
            'type': 'Counter',
            'unit': 'bytes'
        },
        'l1tex__m_l1tex2xbar_write_bytes.sum': {
            'nickname': 'L1_to_L2_Traffic',
            'type': 'Counter',
            'unit': 'bytes'
        },
        'sm__sass_l1tex_m_xbar2l1tex_read_bytes_mem_global_op_ldgsts_cache_bypass.sum': {
            'nickname': 'L2_to_SHMEM_Traffic',
            'type': 'Counter',
            'unit': 'bytes'
        }
    }
    
    def format_value(value, metric_info):
        """Format value based on metric type and unit"""
        if value is None:
            return "N/A"
        
        metric_type = metric_info['type']
        unit = metric_info['unit']
        
        if metric_type == 'Counter':
            if unit == 'ns':
                # Format time duration
                if value >= 1_000_000:  # >= 1ms
                    return f"{value / 1_000_000:.2f} ms"
                elif value >= 1_000:  # >= 1us
                    return f"{value / 1_000:.2f} us"
                else:
                    return f"{value:.2f} ns"
            elif unit == 'bytes':
                # Format bytes
                if value >= 1_073_741_824:  # >= 1GB
                    return f"{value / 1_073_741_824:.2f} GB"
                elif value >= 1_048_576:  # >= 1MB
                    return f"{value / 1_048_576:.2f} MB"
                elif value >= 1_024:  # >= 1KB
                    return f"{value / 1_024:.2f} KB"
                else:
                    return f"{value:.2f} B"
        elif metric_type in ['Throughput', 'Ratio']:
            if unit == '%':
                return f"{value:.2f}%"
        
        # Default formatting
        return f"{value:.2f}"
    
    # Get the first range (usually there's only one)
    my_range = my_context.range_by_idx(0)
    
    # Find the longest nickname for alignment
    max_nickname_len = max(len(info['nickname']) for info in metrics.values())
    
    # Process each kernel
    report = "NCU Report:"
    for j in range(my_range.num_actions()):
        my_action = my_range.action_by_idx(j)
        kernel_name = my_action.name()
        
        # Extract metrics and build string
        metric_strings = []
        for metric_name, metric_info in metrics.items():
            metric_obj = my_action.metric_by_name(metric_name)
            value = metric_obj.as_double() if metric_obj is not None else None
            formatted_value = format_value(value, metric_info)
            
            # Left-align nickname, right-align value
            nickname = metric_info['nickname'].ljust(max_nickname_len)
            metric_strings.append(f"  {nickname} : {formatted_value}")
        
        # Concatenate as string
        result = "\n".join(metric_strings)
        report += f"\n\nKernel {j}: {kernel_name}\n"
        report += result
    
    return report

def run_profiling(logger: PopcornOutput, tests: list[TestCase]):
    """
    Profile a single test case with Nsight Compute (ncu).
    Produces a .ncu-rep and returns a text summary (CSV or text) extracted via ncu --import.
    """
    test = tests[-1]
    # logger.log("benchmark-count", len(tests))

    import json, subprocess, tempfile, shlex

    # Allow overrides via env
    NCU = os.getenv("NCU_PATH", "ncu")
    NCU_SET = os.getenv("NCU_SET", "full")  # or "full" if you want everything

    # Build a tiny one-shot Python that runs the kernel once
    # (keeps your current generate_input/custom_kernel semantics)
    
    one_shot = (
        "import torch; "
        "from reference import generate_input; "
        "from submission import custom_kernel; "
    )
    payload = {
        "args": test.args
    }
    one_shot += (
        f"args={json.dumps(payload['args'])}; "
        "data=generate_input(**args); "
        "torch.cuda.synchronize(); "
        "custom_kernel(data); "
        "torch.cuda.synchronize(); "
    )

    profile_data_folder = "profile_data"
    if not os.path.exists(profile_data_folder):
        os.makedirs(profile_data_folder)

    export_prefix = os.path.join(profile_data_folder, "profile")

    # 1) Run the kernel under ncu to collect the report
    cmd = [
        NCU,
        "--target-processes", "all",
        "--set", NCU_SET,
        "--force-overwrite",
        "--export", export_prefix,
        sys.executable, "-c", one_shot
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print("=== NCU FAILED ===", file=sys.stderr)
        print("STDOUT:", e.stdout, file=sys.stderr)
        print("STDERR:", e.stderr, file=sys.stderr)
        print("Return code:", e.returncode, file=sys.stderr)
        clean_up_ninja_files()
        raise

    # 2) Extract a readable report from the .ncu-rep
    rep_path = export_prefix + ".ncu-rep"
    report_text = parse_ncu_report(rep_path)
    # print(f"report_text: {report_text}")

    logger.log(f"benchmark.{0}.spec", tests[0].spec)
    logger.log(f"benchmark.{0}.report", report_text)
    logger.log("check", "pass")
    clean_up_ninja_files()
    return 0

def clean_up_ninja_files():
    files_to_remove=(
        ".ninja_log",
        ".ninja_deps",
        "build.ninja",
        "kernel_cuda.so",
        "cuda.cu",
        "cuda.cuda.o",
        "main.cpp",
        "main.o",
    )
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)


def main():
    if len(sys.argv) < 3:
        return 2

    mode = sys.argv[1]
    seed = os.getenv("POPCORN_SEED")
    os.unsetenv("POPCORN_SEED")
    seed = int(seed) if seed else None
    set_seed(seed or 42)
    tests = get_test_cases(sys.argv[2], seed)

    try:
        from submission import custom_kernel
    except Exception as e:
        print(f"Compilation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    with PopcornOutput(1) as logger:
        import multiprocessing
        mp_context = multiprocessing.get_context('spawn')
        with mp_context.Pool(1) as pool:
            if mode == "test":
                return run_testing(logger, pool, tests)
            if mode == "benchmark":
                return run_benchmarking(logger, pool, tests)
            elif mode == "profile":
                run_profiling(logger, tests)
            else:
                return 2


if __name__ == "__main__":
    sys.exit(main())
