#!/usr/bin/env python3
"""
Script to run voice bot calls against all scenarios or a single scenario.

This script:
- Starts the Flask app in a background thread
- Makes outbound calls via the /call/start endpoint
- Processes all scenarios sequentially with delays between calls
- Logs call information and provides a summary

Usage:
    python run_calls.py              # Run all 10 scenarios
    python run_calls.py --single     # Run single random scenario (for testing)
"""

import os
import sys
import time
import random
import threading
import argparse
import requests
from datetime import datetime

from scenarios import SCENARIOS
from app import app

# Configuration
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_URL = f"http://{FLASK_HOST}:{FLASK_PORT}"
CALL_START_ENDPOINT = f"{FLASK_URL}/call/start"

# Wait times (in seconds)
FLASK_STARTUP_TIME = 3
CALL_DURATION_WAIT = 180  # 3 minutes between calls
HEALTH_CHECK_TIMEOUT = 10


def start_flask_app():
    """
    Start the Flask app in a background thread.
    
    Returns:
        threading.Thread: The thread running Flask
    """
    print("[SETUP] Starting Flask app in background thread...")
    
    # Create and start Flask thread
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=False,
            use_reloader=False,
            threaded=True
        ),
        daemon=True
    )
    flask_thread.start()
    
    return flask_thread


def wait_for_flask_startup():
    """
    Wait for Flask app to be ready, with health check.
    
    Attempts to ping the /health endpoint until it responds.
    """
    print(f"[SETUP] Waiting for Flask to start (max {HEALTH_CHECK_TIMEOUT}s)...")
    
    health_url = f"{FLASK_URL}/health"
    start_time = time.time()
    
    while time.time() - start_time < HEALTH_CHECK_TIMEOUT:
        try:
            response = requests.get(health_url, timeout=2)
            if response.status_code == 200:
                print("[SETUP] Flask is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(0.5)
    
    print("[SETUP] Flask health check failed - proceeding anyway...")
    return False


def initiate_call(scenario):
    """
    Initiate a call for a given scenario.
    
    Args:
        scenario (dict): The scenario dict with id, name, patient_name
        
    Returns:
        dict: Call response data or None if request failed
    """
    try:
        print(f"\n[CALL] Initiating call for scenario: {scenario['name']}")
        print(f"       Patient: {scenario['patient_name']}")
        
        response = requests.post(
            CALL_START_ENDPOINT,
            json={"scenario_id": scenario["id"]},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"       ✓ Call SID: {data.get('call_sid')}")
            print(f"       Status: {data.get('status')}")
            return data
        else:
            print(f"       ✗ Error: HTTP {response.status_code}")
            print(f"       Response: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"       ✗ Request failed: {e}")
        return None
    except Exception as e:
        print(f"       ✗ Unexpected error: {e}")
        return None


def run_all_scenarios():
    """
    Run calls for all scenarios sequentially.
    
    Returns:
        int: Number of successful calls
    """
    print("\n" + "=" * 80)
    print("RUNNING ALL SCENARIOS")
    print("=" * 80)
    
    successful_calls = 0
    failed_calls = 0
    
    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n[PROGRESS] Scenario {i}/{len(SCENARIOS)}")
        
        # Initiate call
        result = initiate_call(scenario)
        
        if result:
            successful_calls += 1
        else:
            failed_calls += 1
        
        # Wait before next call (except on last iteration)
        if i < len(SCENARIOS):
            print(f"\n[WAIT] Waiting {CALL_DURATION_WAIT}s for call to complete...")
            print("       (Press Ctrl+C to stop)")
            
            try:
                time.sleep(CALL_DURATION_WAIT)
            except KeyboardInterrupt:
                print("\n\n[STOP] Interrupted by user")
                break
    
    return successful_calls, failed_calls


def run_single_scenario():
    """
    Run a call for a single random scenario.
    
    Returns:
        tuple: (successful_calls, failed_calls)
    """
    print("\n" + "=" * 80)
    print("RUNNING SINGLE SCENARIO (TESTING MODE)")
    print("=" * 80)
    
    scenario = random.choice(SCENARIOS)
    
    print(f"\n[TEST] Selected random scenario: {scenario['name']}")
    
    result = initiate_call(scenario)
    
    if result:
        return 1, 0
    else:
        return 0, 1


def print_summary(successful_calls, failed_calls):
    """
    Print a summary of all calls.
    
    Args:
        successful_calls (int): Number of successful calls
        failed_calls (int): Number of failed calls
    """
    total_calls = successful_calls + failed_calls
    
    print("\n" + "=" * 80)
    print("CALL SUMMARY")
    print("=" * 80)
    print(f"Total calls initiated: {total_calls}")
    print(f"Successful: {successful_calls}")
    print(f"Failed: {failed_calls}")
    
    if successful_calls > 0:
        print(f"\nEstimated total runtime: ~{successful_calls * CALL_DURATION_WAIT / 60:.1f} minutes")
    
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


def main():
    """
    Main entry point.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Run voice bot calls against healthcare scenarios"
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Run single random scenario (for testing)"
    )
    args = parser.parse_args()
    
    try:
        # Start Flask app
        flask_thread = start_flask_app()
        
        # Wait for Flask to be ready
        time.sleep(FLASK_STARTUP_TIME)
        wait_for_flask_startup()
        
        # Run calls
        if args.single:
            successful, failed = run_single_scenario()
        else:
            successful, failed = run_all_scenarios()
        
        # Print summary
        print_summary(successful, failed)
        
        print("\n[DONE] All calls completed!")
        print("       Check ./transcripts/ for conversation transcripts")
        print("       Check ./recordings/ for call recordings")
    
    except KeyboardInterrupt:
        print("\n\n[STOP] Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
