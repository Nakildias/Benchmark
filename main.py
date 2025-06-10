#!/usr/bin/env python3

import os
import time
import multiprocessing
import datetime
import threading # Added for concurrent single-core benchmark and timer
from colorama import Fore, Style, init

# Initialize colorama for colored output (autoreset=True will add Style.RESET_ALL after each print)
init(autoreset=True)

# --- Benchmark Configuration ---
BENCHMARK_DURATION_SECONDS = 5  # Duration for each benchmark test
WORK_UNIT_ITERATIONS = 500  # Number of iterations within a single "work unit"
                               # Adjust this if work units are too fast/slow on your system

# --- ANSI Color Definitions (used with colorama) ---
COLOR_TITLE = Fore.CYAN + Style.BRIGHT
COLOR_HEADER = Fore.YELLOW + Style.BRIGHT
COLOR_SCORE = Fore.GREEN + Style.BRIGHT
COLOR_INFO = Fore.WHITE
COLOR_FILE = Fore.MAGENTA
COLOR_ERROR = Fore.RED + Style.BRIGHT

# --- CPU Intensive Work Unit ---
def intensive_work_unit():
    """
    A single unit of CPU-intensive work.
    The benchmark counts how many times this function can be executed.
    """
    a = 1.0
    # Perform a series of calculations that are CPU-bound
    for i in range(1, WORK_UNIT_ITERATIONS + 1):
        a += (float(i) ** 0.57) / (float(i) ** 0.33 + 1e-9) # Floating point ops
        a -= (i * 3) // (i % 100 + 1) # Integer ops
        if i % 2 == 0:
            a *= 1.00000000123 # Multiplication
        else:
            a /= 1.00000000045 # Division
    # The actual value of 'a' is not important, only the computation performed.

# --- Benchmark Runner ---
def run_benchmark_for_duration(duration_seconds): # Removed unused core_id and progress_queue
    """
    Runs the intensive_work_unit repeatedly for the specified duration.

    Args:
        duration_seconds (int): The time in seconds to run the benchmark.

    Returns:
        int: The number of operations (calls to intensive_work_unit) completed.
    """
    operations_count = 0
    start_time = time.monotonic()

    while (time.monotonic() - start_time) < duration_seconds:
        intensive_work_unit()
        operations_count += 1
    return operations_count

# --- Worker for Single-Core Thread ---
def sc_benchmark_thread_task(duration, result_holder):
    """
    Task for the single-core benchmark thread.
    Stores the result in result_holder.
    """
    score = run_benchmark_for_duration(duration)
    if result_holder is not None: # Check in case it's used without a holder
        result_holder.append(score)


# --- Worker for Multiprocessing ---
def multi_core_worker_task(_worker_id): # Argument is for pool.map, can be ignored
    """
    Task executed by each worker process in the multi-core benchmark.
    """
    # Each worker runs the benchmark for the full duration.
    return run_benchmark_for_duration(BENCHMARK_DURATION_SECONDS)

# --- Main Application ---
def main():
    """
    Main function to run the CPU benchmark.
    """
    print(COLOR_TITLE + "=" * 50)
    print(COLOR_TITLE + "PYTHON CPU BENCHMARK UTILITY".center(50))
    print(COLOR_TITLE + "=" * 50)
    print(COLOR_INFO + f"Each test will run for {BENCHMARK_DURATION_SECONDS} seconds.\n")

    # Get CPU core count
    try:
        num_cores = os.cpu_count()
        if num_cores is None:
            print(COLOR_ERROR + "Could not determine number of CPU cores. Defaulting to 1 for multi-core test.")
            num_cores = 1
        else:
            print(COLOR_INFO + f"Detected {COLOR_SCORE}{num_cores}{COLOR_INFO} CPU core(s).")
    except Exception as e:
        print(COLOR_ERROR + f"Error getting CPU count: {e}. Defaulting to 1.")
        num_cores = 1

    print("-" * 50)

    # --- Single-Core Benchmark ---
    print(COLOR_HEADER + "\n--- Starting Single-Core Benchmark ---")
    print(COLOR_INFO + f"Running workload on 1 core for {BENCHMARK_DURATION_SECONDS} seconds...")

    sc_result_holder = [] # To store result from the thread
    benchmark_thread = threading.Thread(target=sc_benchmark_thread_task,
                                       args=(BENCHMARK_DURATION_SECONDS, sc_result_holder))

    start_sc_time = time.monotonic()
    benchmark_thread.start() # Start the benchmark work in a separate thread

    # Display countdown timer in the main thread
    for i in range(BENCHMARK_DURATION_SECONDS, 0, -1):
        print(f"{COLOR_INFO}Time remaining: {i:2d}s", end='\r')
        time.sleep(1) # Sleep for 1 second
        if not benchmark_thread.is_alive(): # Benchmark finished early
            break

    benchmark_thread.join() # Wait for the benchmark thread to complete
    end_sc_time = time.monotonic()

    print(" " * 30, end='\r') # Clear the countdown line

    if sc_result_holder:
        single_core_score = sc_result_holder[0]
        print(COLOR_INFO + f"Single-Core test completed in {end_sc_time - start_sc_time:.2f}s.")
        print(COLOR_SCORE + f"Single-Core Score: {single_core_score} points")
    else:
        single_core_score = "Error"
        print(COLOR_ERROR + "Single-Core test failed to produce a result.")

    print("-" * 50)

    # --- Multi-Core Benchmark ---
    multi_core_score = "N/A" # Default value
    if num_cores > 0:
        print(COLOR_HEADER + f"\n--- Starting Multi-Core Benchmark ({num_cores} cores) ---")
        print(COLOR_INFO + f"Running workload on {num_cores} core(s) for {BENCHMARK_DURATION_SECONDS} seconds...")

        start_mc_time = time.monotonic()
        results_per_core = []

        try:
            with multiprocessing.Pool(processes=num_cores) as pool:
                # map_async is non-blocking, allowing the timer to run concurrently
                async_result = pool.map_async(multi_core_worker_task, range(num_cores))

                # Display countdown timer in the main thread
                for i in range(BENCHMARK_DURATION_SECONDS, 0, -1):
                    print(f"{COLOR_INFO}Time remaining: {i:2d}s", end='\r')
                    time.sleep(1) # Sleep for 1 second
                    if async_result.ready(): # All workers finished
                        break

                print(" " * 30, end='\r') # Clear the countdown line

                results_per_core = async_result.get(timeout=BENCHMARK_DURATION_SECONDS + 5) # Get results, with a timeout

            multi_core_score = sum(results_per_core)
            end_mc_time = time.monotonic()
            print(COLOR_INFO + f"Multi-Core test completed in {end_mc_time - start_mc_time:.2f}s.")
            print(COLOR_SCORE + f"Multi-Core Score: {multi_core_score} points")

            # Optional: Print score per core
            print(COLOR_INFO + "Scores per core:")
            for i, core_score_val in enumerate(results_per_core):
                print(COLOR_INFO + f"  Core {i+1}: {core_score_val} points")

        except multiprocessing.TimeoutError:
            print(COLOR_ERROR + "Multi-core benchmark timed out waiting for results.")
            multi_core_score = "Timeout Error"
            end_mc_time = time.monotonic() # Still record end time
            print(COLOR_INFO + f"Multi-Core test ran for approximately {end_mc_time - start_mc_time:.2f}s before timeout.")
        except Exception as e:
            print(COLOR_ERROR + f"An error occurred during multi-core benchmark: {e}")
            multi_core_score = "Error"
            end_mc_time = time.monotonic() # Still record end time
    else:
        print(COLOR_ERROR + "Multi-core benchmark skipped as core count is zero or undetermined.")

    print("-" * 50)

    # --- Save Results ---
    current_datetime_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_filename = f"results-{current_datetime_str}.txt"

    timestamp_for_file = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # For content of the file
    result_string = (f"{timestamp_for_file} | Single-Core Score: {single_core_score} | "
                     f"Multi-Core Score: {multi_core_score} (on {num_cores} cores)\n")

    try:
        with open(results_filename, "a") as f: # Append mode, though for unique filenames 'w' could also work
            f.write(result_string)
        print(COLOR_FILE + f"\nResults appended to {results_filename}")
    except IOError as e:
        print(COLOR_ERROR + f"\nError saving results to {results_filename}: {e}")

    print(COLOR_TITLE + "\n--- Benchmark Finished ---")

if __name__ == "__main__":
    # This is important for multiprocessing to work correctly, especially on Windows.
    multiprocessing.freeze_support()
    main()
