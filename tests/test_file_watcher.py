"""Tests for file watching functionality"""
import pytest
import os
import tempfile
import time
from activity_scheduler import ActivityScheduler, ActivityType
from activity_scheduler.api import WATCHDOG_AVAILABLE

# Skip all tests if watchdog not available
pytestmark = pytest.mark.skipif(
    not WATCHDOG_AVAILABLE,
    reason="watchdog library not installed"
)


class TestFileWatching:
    """Tests for file watching functionality"""

    def test_start_watching_requires_watchdog(self):
        """Test that start_watching raises ImportError if watchdog not available"""
        # This test only runs if watchdog is not available
        if WATCHDOG_AVAILABLE:
            pytest.skip("watchdog is available")

        scheduler = ActivityScheduler()
        scheduler.add_activity("Test", ActivityType.TYPE_A, 60, 50)
        scheduler.update_user_config(2, 8.0)

        def callback(_): pass

        with pytest.raises(ImportError):
            scheduler.start_watching(callback)

    def test_start_watching_no_files_raises(self):
        """Test starting watching without any files raises error"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip()

        scheduler = ActivityScheduler()
        scheduler.add_activity("Test", ActivityType.TYPE_A, 60, 50)
        scheduler.update_user_config(2, 8.0)

        def callback(_): pass

        with pytest.raises(ValueError):
            scheduler.start_watching(callback)

    def test_start_stop_watching(self):
        """Test starting and stopping watching works"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("activity_name,type,duration,value\n")
            f.write("Test,typeA,60,50\n")
            activities_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"max_concurrent_b": 2, "total_available_hours": 8}\n')
            config_file = f.name

        try:
            scheduler = ActivityScheduler(activities_file, config_file)
            called = False
            results = None

            def callback(res):
                nonlocal called, results
                called = True
                results = res

            scheduler.start_watching(callback, debounce_ms=100)
            assert scheduler.is_watching()

            scheduler.stop_watching()
            assert not scheduler.is_watching()

        finally:
            os.unlink(activities_file)
            os.unlink(config_file)

    def test_callback_invoked_on_file_change(self):
        """Test callback is invoked when watched file changes"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("activity_name,type,duration,value\n")
            f.write("Original,typeA,60,50\n")
            activities_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"max_concurrent_b": 2, "total_available_hours": 8}\n')
            config_file = f.name

        try:
            scheduler = ActivityScheduler(activities_file, config_file)
            called = False
            results = None

            def callback(res):
                nonlocal called, results
                called = True
                results = res

            scheduler.start_watching(callback, debounce_ms=100)
            assert scheduler.is_watching()

            # Modify the file
            time.sleep(0.2)  # Ensure watching started
            with open(activities_file, 'w', encoding='utf-8') as f:
                f.write("activity_name,type,duration,value\n")
                f.write("Modified,typeA,60,50\n")
                f.write("New,typeB,30,20\n")

            # Wait for debounce and callback
            time.sleep(0.5)

            assert called
            assert results is not None
            assert len(results.maximum_gain.schedule) >= 1

            scheduler.stop_watching()
            assert not scheduler.is_watching()

        finally:
            os.unlink(activities_file)
            os.unlink(config_file)

    def test_watch_single_file_activities_only(self):
        """Test watching only activities file"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("activity_name,type,duration,value\n")
            f.write("Test,typeA,60,50\n")
            activities_file = f.name

        try:
            scheduler = ActivityScheduler()
            scheduler.load_activities_from_file(activities_file)
            scheduler.update_user_config(2, 8.0)

            called = False

            def callback(_):
                nonlocal called
                called = True

            scheduler.start_watching(callback, activities_file=activities_file, debounce_ms=100)
            assert scheduler.is_watching()

            # Modify
            time.sleep(0.2)
            with open(activities_file, 'w', encoding='utf-8') as f:
                f.write("activity_name,type,duration,value\n")
                f.write("Changed,typeA,60,50\n")

            time.sleep(0.5)
            assert called

            scheduler.stop_watching()

        finally:
            os.unlink(activities_file)

    def test_watch_single_file_config_only(self):
        """Test watching only config file"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip()

        scheduler = ActivityScheduler()
        scheduler.add_activity("Test", ActivityType.TYPE_A, 60, 50)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"max_concurrent_b": 2, "total_available_hours": 8}\n')
            config_file = f.name

        try:
            scheduler.load_config_from_file(config_file)

            called = False

            def callback(_):
                nonlocal called
                called = True

            scheduler.start_watching(callback, user_config_file=config_file, debounce_ms=100)
            assert scheduler.is_watching()

            # Modify
            time.sleep(0.2)
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write('{"max_concurrent_b": 3, "total_available_hours": 10}\n')

            time.sleep(0.5)
            assert called

            scheduler.stop_watching()

        finally:
            os.unlink(config_file)

    def test_is_watching_returns_correct_state(self):
        """Test is_watching returns correct boolean state"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("activity_name,type,duration,value\nTest,typeA,60,50\n")
            activities_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"max_concurrent_b": 2, "total_available_hours": 8}\n')
            config_file = f.name

        try:
            scheduler = ActivityScheduler(activities_file, config_file)
            assert not scheduler.is_watching()

            def callback(_): pass

            scheduler.start_watching(callback)
            assert scheduler.is_watching()

            scheduler.stop_watching()
            assert not scheduler.is_watching()

        finally:
            os.unlink(activities_file)
            os.unlink(config_file)

    def test_start_watching_stops_previous(self):
        """Test starting watching again stops previous observer"""
        if not WATCHDOG_AVAILABLE:
            pytest.skip()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("activity_name,type,duration,value\nTest,typeA,60,50\n")
            activities_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"max_concurrent_b": 2, "total_available_hours": 8}\n')
            config_file = f.name

        try:
            scheduler = ActivityScheduler(activities_file, config_file)

            def callback(_): pass

            scheduler.start_watching(callback)
            assert scheduler.is_watching()
            observer1 = scheduler._observer

            # Start again
            scheduler.start_watching(callback)
            assert scheduler.is_watching()
            # observer1 should have been stopped
            assert observer1 is not scheduler._observer
            assert not observer1.is_alive()

            scheduler.stop_watching()
            assert not scheduler.is_watching()

        finally:
            os.unlink(activities_file)
            os.unlink(config_file)
