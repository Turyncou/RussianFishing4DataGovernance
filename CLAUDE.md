# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Russian Fishing 4 activity scheduling and recommendation tool. The program optimally allocates daily fishing activity time to maximize gains based on different activity types and constraints.

**Problem**: Recommend optimal activity combinations for a day that maximize total gains. Two activity types:
- **Activity A**: Requires full concentration, can only do one at a time
- **Activity B**: Can do multiple simultaneously, upper limit configurable by user

Activity switching takes 15-20 minutes overhead.

## Data Format

- `activities.csv`: Stores activity plans with columns: activity name, type (A/B), duration, total value
- `user.json`: Stores user configuration:
  - `max_concurrent_b`: Maximum number of concurrent activity B
  - `total_available_hours`: Total available activity hours for the day

## Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run example
python example_usage.py

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_scheduler.py -v

# Run tests with coverage
python -m pytest tests/ --cov=src/activity_scheduler -v

# Check coverage report
python -m pytest tests/ --cov=src/activity_scheduler --cov-report=html
```

## Project Structure

```
D:\Ivy\GQ\lyf\RussianFishing4DataGovernance\
├── data/
│   ├── activities.csv          # Activity definitions
│   └── user.json              # User configuration
├── src/activity_scheduler/
│   ├── __init__.py
│   ├── types.py                # Data classes (Activity, UserConfig, ScheduleResult, etc.)
│   ├── exceptions.py           # Custom exceptions (NoValidScheduleError)
│   ├── data_loader.py          # Load data from CSV/JSON
│   └── optimizer.py            # Optimization algorithms
├── tests/
│   ├── __init__.py
│   ├── test_types.py           # Tests for type definitions
│   ├── test_io.py              # Tests for data loading
│   └── test_scheduler.py       # Tests for optimization logic
├── pyproject.toml              # Project configuration
├── requirements.txt            # Python dependencies (pytest, pytest-cov)
├── example_usage.py            # Example script showing usage
├── design.md                   # Original design requirements
└── CLAUDE.md                   # This file (Claude Code guidance)
```

## Architecture

### Core Modules:

1. **types.py** - Dataclasses defining the data structures:
   - `ActivityType` - Enum for TYPE_A (single concurrent) and TYPE_B (multiple concurrent)
   - `Activity` - Activity definition (name, type, duration in minutes, value/gain)
   - `UserConfig` - User configuration (max_concurrent_b, total_available_hours
   - `ScheduleItem` - Single item in the resulting schedule
   - `ScheduleResult` - Result for one optimization run (schedule, total value, duration, rest time
   - `OptimizationResults` - Container for both optimization results (max gain + balanced)

2. **data_loader.py** - Reads and validates input data from:
   - `activities.csv` with columns: activity_name, type (A/B), duration, value
   - `user.json` with `max_concurrent_b and `total_available_hours`

3. **exceptions.py** - Custom exception `NoValidScheduleError` for when no valid schedule exists

4. **optimizer.py** - Two optimization strategies:
   - `optimize_schedule()` - Main entry point, loads data and runs both optimizations
   - `_optimize_for_max_gain()` - Greedy algorithm that prioritizes activities by value per hour, fills all available time with minimal rest
   - `_optimize_for_balanced()` - Balanced approach that leaves significant rest time, limits type A to 60% of available time

### Algorithm:

- **Activity A** (type A): Cannot overlap, one at a time (requires full concentration)
- **Activity B** (type B): Can be concurrent, up to user-specified maximum
- **Switching overhead**: 15-20 minutes added when switching between different activity types
- **Sorting**: Activities sorted by value per hour (efficiency) in descending order for greedy selection
- **Two results**: Both maximum gain (fills all available time) and balanced (includes rest)

The current implementation uses a greedy approach based on value-per-minute density, which works well for the problem constraints.
