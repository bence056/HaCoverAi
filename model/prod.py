import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def sleep_until_next_hour():
    now = datetime.now()

    next_hour = (now.replace(minute=0, second=0, microsecond=0)
                 + timedelta(hours=1))

    delta = (next_hour - now).total_seconds()

    time.sleep(delta)


class CoverIntelligence:
    options: Any
    HA_URL: str
    HA_TOKEN: str

    def __init__(self):
        print("Initializing CoverIntelligence...")
        file_path = Path("/data/options.json")
        if file_path.exists():
            with open("/data/options.json", "r") as f:
                self.options = json.load(f)
            self.HA_URL = self.options["ha_url"]
            self.HA_TOKEN = self.options["ha_token"]
            self.headers = {
                "Authorization": f"Bearer {self.HA_TOKEN}",
                "Content-Type": "application/json"
            }
