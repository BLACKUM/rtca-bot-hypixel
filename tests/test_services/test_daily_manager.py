import pytest
import time
from services.daily_manager import DailyManager
from services import json_utils

@pytest.mark.asyncio
async def test_daily_register(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    dm = DailyManager()
    
    valid_uuid = "a" * 32
    await dm.register_user("123", "IGN1", valid_uuid)
    
    users = dm.get_tracked_users()
    assert len(users) == 1
    assert users[0] == ("123", valid_uuid)

@pytest.mark.asyncio
async def test_daily_update_calculation(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    dm = DailyManager()
    
    dm.data["users"]["123"] = {"ign": "TestUser", "uuid": "u1"}
    dm.data["daily_snapshots"]["123"] = {
        "timestamp": 1000,
        "cata_xp": 1000,
        "classes": {"mage": 500}
    }
    
    new_data = {
        "catacombs": 2000,
        "classes": {"mage": 600}
    }
    await dm.update_user_data("123", new_data, save=False)
    
    stats = dm.get_daily_stats("123")
    assert stats["cata_gained"] == 1000
    assert stats["classes"]["mage"]["gained"] == 100

@pytest.mark.asyncio
async def test_daily_leaderboard(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    dm = DailyManager()
    
    dm.data["users"]["1"] = {"ign": "User1", "uuid": "u1"}
    dm.data["daily_snapshots"]["1"] = {"cata_xp": 1000, "classes": {}}
    dm.data["current_xp"]["1"] = {"cata_xp": 2000, "classes": {}}
    
    dm.data["users"]["2"] = {"ign": "User2", "uuid": "u2"}
    dm.data["daily_snapshots"]["2"] = {"cata_xp": 1000, "classes": {}}
    dm.data["current_xp"]["2"] = {"cata_xp": 1500, "classes": {}}
    
    lb = dm.get_leaderboard("daily")
    
    assert len(lb) == 2
    assert lb[0]["ign"] == "User1"
    assert lb[0]["gained"] == 1000
    assert lb[1]["ign"] == "User2"
    assert lb[1]["gained"] == 500
