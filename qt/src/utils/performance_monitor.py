"""Performance monitor - tracks memory, CPU usage for debugging"""
import os
import sys
import time
import psutil
import logging
from threading import Thread
from typing import Optional

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Simple performance monitor that logs memory and CPU usage periodically"""

    _instance: Optional['PerformanceMonitor'] = None

    def __init__(self, interval_seconds: float = 5.0):
        self._interval = interval_seconds
        self._running = False
        self._thread: Optional[Thread] = None
        self._process = psutil.Process(os.getpid())
        self._start_time = time.time()

        PerformanceMonitor._instance = self

    @classmethod
    def instance(cls) -> Optional['PerformanceMonitor']:
        return cls._instance

    def _get_memory_usage(self) -> float:
        """Return memory usage in MB"""
        return self._process.memory_info().rss / (1024 * 1024)

    def _get_cpu_usage(self) -> float:
        """Return CPU usage percentage (0-100)"""
        return self._process.cpu_percent(interval=None)

    def _get_thread_count(self) -> int:
        """Return number of threads"""
        return self._process.num_threads()

    def _get_open_files(self) -> int:
        """Return number of open file descriptors"""
        try:
            return len(self._process.open_files())
        except Exception:
            return 0

    def _monitor_loop(self):
        """Background monitoring loop"""
        logger.info("=== Performance monitor started ===")
        self._log_stats()

        while self._running:
            time.sleep(self._interval)
            if self._running:
                self._log_stats()

        logger.info("=== Performance monitor stopped ===")

    def _log_stats(self):
        """Log current performance statistics"""
        mem_mb = self._get_memory_usage()
        cpu_pct = self._get_cpu_usage()
        threads = self._get_thread_count()
        open_files = self._get_open_files()
        uptime = time.time() - self._start_time

        logger.info(
            f"[Performance] Memory: {mem_mb:.1f} MB | "
            f"CPU: {cpu_pct:.1f}% | "
            f"Threads: {threads} | "
            f"Open files: {open_files} | "
            f"Uptime: {uptime:.0f}s"
        )

    def start(self):
        """Start the performance monitor in background thread"""
        if self._running:
            return

        self._running = True
        self._thread = Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the performance monitor"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def log_current(self):
        """Log current stats immediately"""
        self._log_stats()
