#!/usr/bin/env python3
"""Example usage of the activity scheduler optimization"""
import os
from src.activity_scheduler import optimizer


def main():
    """Demonstrate the scheduling optimization"""
    print("=" * 60)
    print("Activity Scheduling Optimization Example")
    print("=" * 60)

    # Get file paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    activities_file = os.path.join(base_dir, "data", "activities.csv")
    user_config_file = os.path.join(base_dir, "data", "user.json")

    # Run optimization
    print(f"\nLoading activities from: {activities_file}")
    print(f"Loading user config from: {user_config_file}")
    print("\nRunning optimization...")

    try:
        results = optimizer.optimize_schedule(activities_file, user_config_file)
    except Exception as e:
        print(f"Error: {e}")
        return

    # Display maximum gain results
    print("\n" + "=" * 60)
    print("1. MAXIMUM GAIN SCHEDULE")
    print("=" * 60)
    display_schedule_result(results.maximum_gain)

    # Display balanced results
    print("\n" + "=" * 60)
    print("2. BALANCED SCHEDULE")
    print("=" * 60)
    display_schedule_result(results.balanced)

    # Comparison
    print("\n" + "=" * 60)
    print("SCHEDULE COMPARISON")
    print("=" * 60)
    print(f"Maximum Gain Value: {results.maximum_gain.total_value:.1f}")
    print(f"Balanced Value: {results.balanced.total_value:.1f}")
    print(f"Maximum Gain Rest Time: {results.maximum_gain.rest_time} minutes")
    print(f"Balanced Rest Time: {results.balanced.rest_time} minutes")


def display_schedule_result(result):
    """Display a single schedule result"""
    print(f"\nTotal Value: {result.total_value:.1f}")
    print(f"Total Active Time: {result.total_duration} minutes")
    print(f"Rest Time: {result.rest_time} minutes")
    print(f"Switching Overhead: {result.details['total_overhead']} minutes")
    print(f"Number of Activities: {result.details['num_activities']}")

    print("\nDetailed Schedule:")
    for i, item in enumerate(result.schedule, 1):
        type_label = "A" if item.activity.type.value == "typeA" else "B"
        duration = item.end_time - item.start_time
        print(f"  {i}. [{type_label}] {item.activity.activity_name}")
        print(f"     Duration: {duration} minutes | Value: {item.activity.value}")
        print(f"     Time slot: {item.start_time} - {item.end_time} minutes")


if __name__ == "__main__":
    main()