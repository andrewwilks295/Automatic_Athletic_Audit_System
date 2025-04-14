import os
import logging
from datetime import datetime


class CatalogBatchLogger:
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_path = os.path.join(log_dir, f"{timestamp}.log")

        self.logger = logging.getLogger(f"CatalogBatchLogger-{timestamp}")
        self.logger.setLevel(logging.INFO)

        handler = logging.FileHandler(self.log_path, mode="w", encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.propagate = False

    def parsed(self, major, detail=None):
        self._log("✅ PARSED", major, detail)

    def imported(self, major, detail=None):
        self._log("✅ IMPORTED", major, detail)

    def skipped(self, major, detail=None):
        self._log("⚠️ SKIPPED", major, detail)

    def failed(self, major, detail=None):
        self._log("❌ FAILED", major, detail)

    def _log(self, prefix, major, detail):
        message = f"{prefix} {major}"
        if detail:
            message += f" — {detail}"
        print(message)
        self.logger.info(message)

    def close(self):
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)
