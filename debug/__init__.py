"""
Debug tools for Chisel development.
These will be removed before the 1.0 release.

Usage:
    from debug import inspector, fraccion_render, benchmark
    inspector.dump_page(doc, page_num)
    fraccion_render.visualize_fractions(page)
    benchmark.time_render(page, zoom=2.0)
"""

import logging
import time
from pathlib import Path

DEBUG = True
LOG_DIR = Path(__file__).parent

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "chisel_debug.log"),
        logging.StreamHandler(),
    ],
)

log = logging.getLogger("chisel.debug")


def timer(func):
    """Decorator to time function execution."""
    def wrapper(*args, **kwargs):
        if not DEBUG:
            return func(*args, **kwargs)
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        log.debug("%s took %.4f ms", func.__name__, elapsed * 1000)
        return result
    return wrapper


def dump_state(obj, label=""):
    """Dump the state of any object for debugging."""
    if not DEBUG:
        return
    log.debug("=== %s ===", label or obj.__class__.__name__)
    for attr in dir(obj):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(obj, attr)
            if not callable(val):
                log.debug("  %s = %s", attr, repr(val)[:120])
        except Exception:
            log.debug("  %s = <error>", attr)
