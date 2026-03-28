import os
import time
import aiofiles
from services import json_utils as json
from core.logger import log_info, log_error

SOLO_DATA_FILE = "data/solo_clears.json"

class SoloManager:
    def __init__(self):
        self.data = {}

    async def initialize(self):
        await self.load_data()

    async def load_data(self):
        if not os.path.exists(SOLO_DATA_FILE):
            log_info("No solo clears data file found, starting fresh.")
            await self._save_data()
            return

        try:
            async with aiofiles.open(SOLO_DATA_FILE, json.get_read_mode()) as f:
                content = await f.read()
                self.data = json.loads(content)
            log_info(f"Loaded solo clears data for {len(self.data)} floors.")
        except Exception as e:
            log_error(f"Failed to load solo clears data: {e}")

    async def _save_data(self):
        try:
            temp_path = SOLO_DATA_FILE + ".tmp"
            async with aiofiles.open(temp_path, json.get_write_mode()) as f:
                await f.write(json.dumps(self.data))
            os.replace(temp_path, SOLO_DATA_FILE)
        except Exception as e:
            log_error(f"Failed to save solo clears data: {e}")

    async def submit_run(self, floor, ign, uuid, time_ms, proof_text, discord_id):
        floor = floor.upper()
        if floor not in self.data:
            self.data[floor] = {}

        existing_run = self.data[floor].get(uuid)
        if existing_run and existing_run.get("time_ms", float('inf')) <= time_ms:
            return False, "You already have a faster or equal time recorded."

        self.data[floor][uuid] = {
            "ign": ign,
            "time_ms": time_ms,
            "date_achieved": int(time.time()),
            "verified": False,
            "proof_text": proof_text,
            "discord_id": str(discord_id)
        }

        await self._save_data()
        return True, "Run submitted successfully and is pending verification."

    async def verify_run(self, floor, uuid, approved: bool):
        floor = floor.upper()
        if floor not in self.data or uuid not in self.data[floor]:
            return False, "Run not found."

        if approved:
            self.data[floor][uuid]["verified"] = True
            await self._save_data()
            return True, "Run approved."
        else:
            del self.data[floor][uuid]
            await self._save_data()
            return True, "Run rejected and removed."

    def get_leaderboard(self, floor, category="verified"):
        floor = floor.upper()
        if floor not in self.data:
            return []

        runs = []
        for uuid, entry in self.data[floor].items():
            is_ver = entry.get("verified", False)
            if category == "all" or (category == "verified" and is_ver) or (category == "unverified" and not is_ver):
                runs.append({
                    "uuid": uuid,
                    **entry
                })

        runs.sort(key=lambda x: x["time_ms"])
        return runs
