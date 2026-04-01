"""
Data pipeline package for downloading, cleaning, processing, and serving
market data via a local SQLite database.

Modules:
- db: DB initialization and CRUD helpers
- downloader: Fetch from providers (yfinance) and upsert into DB
- cleaning: Time-series alignment, missing handling, anomaly flags
- processing: Derived features across frequencies (daily/weekly/monthly)
- data_service: Facade used by app code to fetch data with manual/auto updates
- scheduler: Optional daily auto-update scheduler (16:15 local time)
"""

from dataclasses import dataclass, field


@dataclass
class PipelineResult:
    """Structured result from each pipeline stage (download / clean / process).

    Attributes:
        ok:    True if the stage completed without error.
        rows:  Number of rows written (0 is valid when no new data).
        error: Human-readable error message when ok is False.
        warnings: Non-fatal issues encountered during the stage.
    """

    ok: bool = True
    rows: int = 0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
