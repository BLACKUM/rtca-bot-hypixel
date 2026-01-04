import json
import os
import time
import aiofiles
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from core.logger import log_info, log_error, log_debug
from services.xp_calculations import get_dungeon_level
from services.api import get_uuid, get_dungeon_xp
from datetime import timedelta
import asyncio
import random
from services.xp_calculations import get_dungeon_level, get_class_average

DAILY_DATA_FILE = "data/daily_data.json"

CONGRATS_GIFS = [
    "https://c.tenor.com/n5-r2F_JeGMAAAAd/tenor.gif",
    "https://c.tenor.com/xAW8c7Z8-3cAAAAd/tenor.gif",
    "https://c.tenor.com/4YDfECEyEtwAAAAd/tenor.gif",
    "https://c.tenor.com/8Zvt_ouixT8AAAAd/tenor.gif",
    "https://c.tenor.com/I5LkHI4yrRcAAAAd/tenor.gif",
    "https://c.tenor.com/JDUuuveDLeQAAAAd/tenor.gif",
    "https://c.tenor.com/Xqc4YXfCySEAAAAd/tenor.gif",
    "https://c.tenor.com/UgvKJP8OIHoAAAAd/tenor.gif",
    "https://c.tenor.com/O57p6KOsleoAAAAd/tenor.gif",
    "https://c.tenor.com/gdBh7nScJMYAAAAd/tenor.gif",
    "https://c.tenor.com/mamnZXgZxqIAAAAd/tenor.gif",
    "https://c.tenor.com/lfbOYamuNSoAAAAd/tenor.gif",
    "https://c.tenor.com/8WpxdEqUcWEAAAAd/tenor.gif",
    "https://c.tenor.com/jI79BCqsw68AAAAd/tenor.gif",
    "https://c.tenor.com/XgzhRq264JcAAAAd/tenor.gif",
    "https://c.tenor.com/VngFH2yD0RAAAAAC/tenor.gif",
    "https://c.tenor.com/JEFazVKAde0AAAAd/tenor.gif",
    "https://c.tenor.com/GEAz2m-SWAsAAAAd/tenor.gif",
    "https://c.tenor.com/LcsbStHRMCMAAAAC/tenor.gif",
    "https://c.tenor.com/Dgmg1Dzjq-oAAAAd/tenor.gif",
    "https://media.tenor.com/UlNu8AJREWwAAAAM/kermit-the-frog-go-the-fuck-outside-punk.gif",
    "https://i.imgflip.com/8axaft.gif",
    "https://media.tenor.com/0lsV1eolzSMAAAAM/shower-soap.gif",
    "https://media.tenor.com/jcG6b0cZgQEAAAAM/homer-bath.gif",
    "https://media.tenor.com/XX7CWmfJ8ZIAAAAM/shower-dogs.gif",
    "https://img1.picmix.com/output/pic/normal/2/8/0/6/11396082_40409.gif",
    "https://media.tenor.com/MMo4B6tp-GMAAAAM/job-application.gif",
    "https://media.tenor.com/Rs-PNa8EBFcAAAAM/job-jumpscare-job-application.gif",
    "https://media.tenor.com/JkMtMAjXHS8AAAAM/job-job-application.gif",
    "https://c.tenor.com/xyMEZ2xCttcAAAAC/tenor.gif",
    "https://media.tenor.com/Kp0_YKtqqXIAAAAe/job-application.png",
    "https://media.tenor.com/Gk2yr271HUsAAAAe/job-application.png",
    "https://media.tenor.com/UsDCL6bOIT4AAAAM/touch-grass-touch.gif",
    "https://i.imgflip.com/6f5788.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUyODIyMXFzamljbm9sc2d1NnVzdDJvYXllN2Jjcm14Y25kYm00cGF5ZSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/bum2UBz4nR9IxZmWde/giphy-downsized.gif",
    "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyODVzb2JyeXpveng0Z2FocHdsczF6enZqbDN6NDBiZmhuaWlndXl1NiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/JyOtBwVBKFoeIQ14Po/200w_d.gif",
    "https://media.discordapp.net/attachments/1122856048374595647/1152961363614908497/JIXMersMo8xcnmXQ.gif?ex=69591b72&is=6957c9f2&hm=40759ab651245f54ba2e5f10640403b43806c1cfe5cbf542ec4be9d2a4607437&=&width=585&height=75",
    "https://media.discordapp.net/attachments/1263938847910269000/1276128862849339393/minus-infinite-social-credit-china.gif?ex=6958f21e&is=6957a09e&hm=34acdfe4c04a23c4d4e4256f908b7523d41670e382018038544bfc3aeb2823ff&=&width=800&height=450",
    "https://media.discordapp.net/attachments/1263938847910269000/1276125652730380349/gypsycrusadervshoke.gif?ex=6958ef20&is=69579da0&hm=545b63f83cb383740758971ca6940b9f9b22d1bd9d832ed09089d9246c15ffc0&=&width=800&height=503",
    "https://media.discordapp.net/attachments/1263938847910269000/1276130366847057950/redditsave.com_y2dkx7x76f481.gif?ex=6958f384&is=6957a204&hm=da6abb1ff3db36d77abaf35e8103173e849eb85297686fb2edcb1f1dec3cb57f&=&width=800&height=800",
    "https://media.discordapp.net/attachments/1236050415020277840/1267879801566269481/caption.gif?ex=69594214&is=6957f094&hm=2581bd92a3109cad09926351f8b69d6bc279a5003b64536ddb50684697b5eb5d&=&width=750&height=934",
    "https://media.discordapp.net/attachments/993269478060195950/1118188097222488104/ED6EFBC5-A68E-48C6-9103-B123B1ECC22D.gif?ex=69592a51&is=6957d8d1&hm=9b2954746a2d198cd8442724df3d8ccb09134436db77a0cdfdbc5b13cf79876e&=&width=254&height=60",
    "https://cdn.discordapp.com/attachments/982414624844554241/1185533720233508894/tM1qwcbNS15DWrFk.gif?ex=6958f3d1&is=6957a251&hm=9708f3e09cc4e9d50d986acaf7086d2177ba9e1c4bc09a6b96214851f9a9c28a",
    "https://media.discordapp.net/attachments/1255211359227084821/1269003922413060176/caption.gif?ex=6958bbc0&is=69576a40&hm=aec2497118642f46043347f8f462cc2f4e9fdd19d60cd0882d414949b84efcd8&=&width=294&height=375",
    "https://media.discordapp.net/attachments/773213826186739775/979470724098039878/puzzlehater.gif.gif?ex=6958c972&is=695777f2&hm=f9d81391304ff5749a3deeea31c77a76627bb1b7c14c872e148fe28afd26344a&=&width=168&height=168",
    "https://media.discordapp.net/attachments/1347938901825814592/1400962571082924132/MedalTVMinecraft20250731185114-1753971386_1.gif?ex=6958e9d1&is=69579851&hm=dcaf2ed25e77aca670c8f26e47e332c73c3d202af44bb5f5140369b7eda85757&=&width=865&height=485",
    "https://media.discordapp.net/attachments/1275995649988628574/1300897696269209681/wdhu.gif?ex=6958bf24&is=69576da4&hm=dc133d83ca5895f9975fee6ce031e2ad7bd4aad3cd84006b75de18ae3093abc7&=&width=658&height=849",
    "https://media.discordapp.net/attachments/1172235640117669921/1402064324805132479/a276ic.gif?ex=6958f768&is=6957a5e8&hm=01f61333a5246f22918ca0791a5ea7950a9470ce5d55f8e55491c423eab243ec&=&width=450&height=236",
    "https://media.discordapp.net/attachments/1397725617239363625/1403384070540365914/meowmeow.gif?ex=69592744&is=6957d5c4&hm=39de6c27bf9cca6fd7e61e2b61e8d232ce4bf1979e960d483204ba27e93b4605&=&width=445&height=445",
    "https://media.discordapp.net/attachments/1379474866725453988/1420884081176084551/togif.gif?ex=6958e0ab&is=69578f2b&hm=11c34bd40104687de43199b1e43539f6f8fa59083525b3736cf39d1f8d66fc70&=&width=1545&height=875",
    "https://media.discordapp.net/attachments/1420147559011192924/1447572753149591592/togif.gif?ex=6959122e&is=6957c0ae&hm=b55333c72e8ef1c3e5b9cc6247a0b414412b0d1e6e49973edb9dd3919d74b401&=&width=1024&height=796"
]

class DailyManager:
    def __init__(self):
        self.data = {
            "users": {},
            "daily_snapshots": {},
            "monthly_snapshots": {},
            "current_xp": {},
            "last_daily_reset": 0,
            "last_monthly_reset": 0,
            "last_updated": 0
        }
    async def initialize(self):
        await self.load_data()

    def get_reset_timestamps(self) -> Tuple[int, int]:
        now = datetime.now(timezone.utc)
        target_daily = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        next_daily_ts = int(target_daily.timestamp())
        
        if now.month == 12:
            target_monthly = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            target_monthly = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        next_monthly_ts = int(target_monthly.timestamp())
        
        return next_daily_ts, next_monthly_ts

    async def force_update_all(self, status_message=None, force=False):
        tracked_users = self.get_tracked_users()
        total_users = len(tracked_users)
        
        now = int(time.time())
        last_updated = self.data.get("last_updated", 0)
        
        if not force and now - last_updated < 86400:
            log_debug(f"Skipping daily update (last updated {now - last_updated}s ago)")
            if status_message:
                 try:
                     await status_message.edit(content=f"✅ Daily stats already up to date (Updated <t:{last_updated}:R>)")
                 except: pass
            return 0, 0, total_users
        
        log_info(f"Starting stats update for {total_users} users (Forced: {force})")
        
        if total_users == 0:
            return 0, 0, 0 # updated, errors, total
            
        updated_count = 0
        errors = 0
        processed_count = 0
        sem = asyncio.Semaphore(5)
        
        async def update_user(user_id, uuid):
            nonlocal updated_count, errors, processed_count
            async with sem:
                try:
                    if not uuid:
                        log_error(f"Skipping update for {user_id}: No UUID")
                        errors += 1
                    else:
                        xp_data = await get_dungeon_xp(uuid)
                        if xp_data:
                            await self.update_user_data(user_id, xp_data)
                            updated_count += 1
                        else:
                            errors += 1
                except Exception as e:
                    log_error(f"Error updating user {user_id}: {e}")
                    errors += 1
                finally:
                    processed_count += 1
                    if status_message and (processed_count <= 5 or processed_count % 5 == 0):
                        try:
                            asyncio.create_task(status_message.edit(
                                content=f"🔄 **Force Update In Progress**\nProcessing: {processed_count}/{total_users}\nUpdated: {updated_count}\nErrors: {errors}"
                            ))
                        except Exception:
                            pass

        tasks = [update_user(uid, uuid) for uid, uuid in tracked_users]
        await asyncio.gather(*tasks)
                
        return updated_count, errors, total_users

    async def load_data(self):
        if not os.path.exists(DAILY_DATA_FILE):
            log_info("No daily data file found, starting fresh.")
            await self._save_data()
            return

        try:
            async with aiofiles.open(DAILY_DATA_FILE, 'r') as f:
                content = await f.read()
                loaded = json.loads(content)
                for key in self.data:
                    if key in loaded:
                        self.data[key] = loaded[key]
            log_info(f"Loaded daily data for {len(self.data.get('users', {}))} users.")
        except Exception as e:
            log_error(f"Failed to load daily data: {e}")

    async def _save_data(self):
        try:
            async with aiofiles.open(DAILY_DATA_FILE, 'w') as f:
                await f.write(json.dumps(self.data, indent=4))
        except Exception as e:
            log_error(f"Failed to save daily data: {e}")

    async def register_user(self, user_id: str, ign: str, uuid: str):
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "ign": ign,
                "uuid": uuid
            }
            await self._save_data()
            log_info(f"Registered user {ign} ({user_id}) for daily tracking.")
        elif self.data["users"][user_id]["ign"] != ign:
             self.data["users"][user_id]["ign"] = ign
             await self._save_data()

    def get_tracked_users(self) -> List[Tuple[str, str]]:
        return [(uid, info["uuid"]) for uid, info in self.data["users"].items()]

    async def update_user_data(self, user_id: str, xp_data: dict):
        user_id = str(user_id)
        now = int(time.time())
        
        self.data["current_xp"][user_id] = {
            "timestamp": now,
            "cata_xp": xp_data["catacombs"],
            "classes": xp_data["classes"]
        }
        
        if user_id not in self.data["daily_snapshots"]:
             self.data["daily_snapshots"][user_id] = self.data["current_xp"][user_id]
        
        if user_id not in self.data["monthly_snapshots"]:
             self.data["monthly_snapshots"][user_id] = self.data["current_xp"][user_id]
             
        self.data["last_updated"] = now
        await self._save_data()

    async def check_resets(self):
        now = datetime.now(timezone.utc)
        
        last_reset_ts = self.data.get("last_daily_reset", 0)
        last_reset_date = datetime.fromtimestamp(last_reset_ts, timezone.utc)
        
        if now.date() > last_reset_date.date():
            log_info("Performing Daily Reset...")
            self.data["daily_snapshots"] = self.data["current_xp"].copy()
            self.data["last_daily_reset"] = int(now.timestamp())
        await self._save_data()
             
        last_month_ts = self.data.get("last_monthly_reset", 0)
        last_month_date = datetime.fromtimestamp(last_month_ts, timezone.utc)
        
        if now.month != last_month_date.month or now.year != last_month_date.year:
            log_info("Performing Monthly Reset...")
            self.data["monthly_snapshots"] = self.data["current_xp"].copy()
            self.data["last_monthly_reset"] = int(now.timestamp())
            await self._save_data()

    def get_last_updated(self) -> int:
        return self.data.get("last_updated", 0)

    def get_daily_stats(self, user_id: str):
        return self._calculate_stats(user_id, "daily_snapshots")

    def get_monthly_stats(self, user_id: str):
        return self._calculate_stats(user_id, "monthly_snapshots")

    def _calculate_stats(self, user_id: str, snapshot_key: str):
        user_id = str(user_id)
        current = self.data["current_xp"].get(user_id)
        start = self.data[snapshot_key].get(user_id)
        
        if not current or not start:
            return None
            
        stats = {
            "cata_gained": current["cata_xp"] - start["cata_xp"],
            "cata_start_xp": start["cata_xp"],
            "cata_current_xp": current["cata_xp"],
            "cata_start_lvl": get_dungeon_level(start["cata_xp"]),
            "cata_current_lvl": get_dungeon_level(current["cata_xp"]),
            "classes": {}
        }
        
        for cls, xp in current["classes"].items():
            start_xp = start["classes"].get(cls, 0)
            stats["classes"][cls] = {
                "gained": xp - start_xp,
                "start_xp": start_xp,
                "current_xp": xp,
                "start_lvl": get_dungeon_level(start_xp),
                "current_lvl": get_dungeon_level(xp)
            }
            
        return stats

    def get_leaderboard(self, type="daily"):
        snapshot_key = "daily_snapshots" if type == "daily" else "monthly_snapshots"
        leaderboard_map = {}
        
        for user_id, info in self.data["users"].items():
            stats = self._calculate_stats(user_id, snapshot_key)
            if stats:
                ign = info["ign"]
                if ign not in leaderboard_map or stats["cata_gained"] > leaderboard_map[ign]["gained"]:
                    leaderboard_map[ign] = {
                        "ign": ign,
                        "gained": stats["cata_gained"],
                        "user_id": user_id
                    }
        
        leaderboard = list(leaderboard_map.values())
        leaderboard.sort(key=lambda x: x["gained"], reverse=True)
        return leaderboard

    # i have no idea why uuid was invalid in the first place, but i've made this function to fix it in the future
    # somebody changed a name... ig that's why
    async def sanitize_data(self):
        log_info("Sanitizing daily data...")
        updates = False
        for user_id, info in self.data["users"].items():
            uuid = info.get("uuid", "")
            ign = info.get("ign", "")
            
            if not uuid or len(uuid) != 32:
                log_info(f"Detected invalid UUID for {ign} ({uuid}). Fetching correct UUID...")
                new_uuid = await get_uuid(ign)
                if new_uuid:
                    self.data["users"][user_id]["uuid"] = new_uuid
                    log_info(f"Fixed UUID for {ign}: {new_uuid}")
                    updates = True
                else:
                    log_error(f"Failed to fix UUID for {ign}")

        if updates:
            await self._save_data()
            log_info("Daily data sanitized and saved.")
        else:
            log_info("Daily data is clean.")

daily_manager = DailyManager()
