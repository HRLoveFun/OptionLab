"""APScheduler must stay an optional, lazily imported dependency.

Both checks run in a **fresh interpreter** via ``subprocess`` so the result
cannot be polluted by whatever the current pytest session already imported.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_BLOCK_APSCHEDULER = """
import sys


class _Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "apscheduler" or fullname.startswith("apscheduler."):
            raise ModuleNotFoundError(f"No module named {fullname!r}")
        return None


sys.meta_path.insert(0, _Blocker())
"""


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def test_importing_scheduler_module_does_not_import_apscheduler():
    """Module import alone must not require the package (see constraints §6)."""
    result = _run(
        "import sys\n"
        "import data_pipeline.scheduler\n"
        "assert 'apscheduler' not in sys.modules, 'apscheduler imported at module scope'\n"
    )

    assert result.returncode == 0, result.stderr


def test_missing_apscheduler_raises_actionable_error():
    """`UpdateScheduler()` must explain how to fix it, not blow up opaquely."""
    result = _run(
        _BLOCK_APSCHEDULER
        + (
            "from data_pipeline.scheduler import UpdateScheduler\n"
            "try:\n"
            "    UpdateScheduler()\n"
            "except ModuleNotFoundError as exc:\n"
            "    assert 'APScheduler' in str(exc), str(exc)\n"
            "    assert 'AUTO_UPDATE_TICKERS' in str(exc), str(exc)\n"
            "else:\n"
            "    raise AssertionError('expected ModuleNotFoundError')\n"
        )
    )

    assert result.returncode == 0, result.stderr
