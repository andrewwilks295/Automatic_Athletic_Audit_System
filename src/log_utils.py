import os
import logging
from datetime import datetime


class CatalogBatchLogger:
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"catalog_batch_{timestamp}.log")

        self.logger = logging.getLogger("CatalogBatchLogger")
        self.logger.setLevel(logging.INFO)
        self.handler = logging.FileHandler(log_path, encoding="utf-8")
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(self.handler)

        self.logger.info(f"📝 Catalog Scraping Log Started: {timestamp}")

    def parsed(self, major_name_web, **kwargs):
        self._log("PARSED", major_name_web, **kwargs)

    def imported(self, major_name_web, **kwargs):
        self._log("IMPORTED", major_name_web, **kwargs)

    def skipped(self, major_name_web, reason=None, extra=None):
        self._log("SKIPPED", major_name_web, reason, extra)

    def failed(self, major_name_web, reason=None, extra=None):
        self._log("FAILED", major_name_web, reason, extra)

    def _log(self, status, major_name_web, reason=None, extra=None):
        line = f"{status} {major_name_web}"
        if reason:
            line += f" — {reason}"
        if extra:
            line += f" [{extra}]"
        self.logger.info(line)

    def close(self):
        self.logger.info("✅ Batch scrape complete.")
        self.logger.removeHandler(self.handler)
        self.handler.close()
