# Activity Scheduling Optimization

A Python project for optimizing daily activity scheduling using TDD.

## Features

- **Activity Types**:
  - Type A: Single-concurrent activities requiring full concentration
  - Type B: Multi-concurrent activities with configurable limits
- **Optimization Modes**:
  - Maximum Gain: Optimizes for highest total value
  - Balanced: Balances value with rest time
- **Switching Overhead**: Accounts for 15-20 minute overhead when switching between activities
- **Data Sources**: CSV for activities, JSON for user preferences

## Project Structure

```
activity-scheduler/
├── data/                     # Input data files
│   ├── activities.csv       # Activity definitions
│   └── user.json            # User configuration
├── src/activity_scheduler/   # Source code
│   ├── __init__.py
│   ├── types.py             # Type definitions
│   ├── exceptions.py        # Custom exceptions
│   ├── data_loader.py       # Data loading functions
│   └── optimizer.py         # Optimization algorithms
├── tests/                    # Test files
│   ├── __init__.py
│   ├── test_types.py        # Type tests
│   ├── test_io.py          # Data loading tests
│   └── test_scheduler.py   # Optimization tests
├── pyproject.toml          # Poetry dependencies
└── design.md               # Design documentation
```

## Setup

### Prerequisites

- Python 3.10+
- Poetry (for dependency management)

### Installation

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_scheduler.py -v

# Run with coverage
python -m pytest tests/ -v --tb=short
```

## Usage

### Basic Usage

```python
from src.activity_scheduler import optimizer

results = optimizer.optimize_schedule("data/activities.csv", "data/user.json")

print("Maximum Gain Schedule:")
print(f"Total Value: {results.maximum_gain.total_value:.1f}")
print(f"Duration: {results.maximum_gain.total_duration} minutes")
print(f"Rest Time: {results.maximum_gain.rest_time} minutes")
print(f"Overhead: {results.maximum_gain.details['total_overhead']} minutes")

print("\nBalanced Schedule:")
print(f"Total Value: {results.balanced.total_value:.1f}")
print(f"Duration: {results.balanced.total_duration} minutes")
print(f"Rest Time: {results.balanced.rest_time} minutes")
print(f"Overhead: {results.balanced.details['total_overhead']} minutes")
```

### Data Files

#### activities.csv

```csv
activity_name,type,duration,value
Reading,typeA,60,50
Programming,typeA,120,100
Gaming,typeA,90,80
Walking,typeB,60,30
Meditation,typeB,30,20
Yoga,typeB,45,40
Reading_News,typeB,15,10
Cooking,typeB,45,35
```

#### user.json

```json
{
  "max_concurrent_b": 2,
  "total_available_hours": 8
}
```

## Optimization Details

### Maximum Gain Strategy

1. Sorts activities by value per minute descending
2. Prioritizes Type A activities (single-concurrent, high value)
3. Fills remaining time with Type B activities (multi-concurrent)
4. Uses minimum overhead (15 minutes) to maximize active time

### Balanced Strategy

1. Limits Type A activities to 60% of available time
2. Selects a mix of high-value Type B activities
3. Uses moderate overhead (18 minutes)
4. Ensures significant rest time

## Activity Types

### Type A Characteristics

- Can only be done one at a time
- Require full concentration
- Examples: Reading, Programming, Gaming

### Type B Characteristics

- Can be done in parallel (up to `max_concurrent_b` limit)
- Require less concentration
- Examples: Walking, Meditation, Cooking

## Constraints

- Switching between activities takes 15-20 minutes overhead
- Total scheduled time must fit within available hours
- Type A activities cannot overlap
- Type B activities respect maximum concurrency limit