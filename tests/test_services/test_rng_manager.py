import pytest
from services.rng_manager import RngManager
from services import json_utils

@pytest.mark.asyncio
async def test_rng_update_drop(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    rm = RngManager()
    
    await rm.update_drop("123", "Floor 7 (Necron)", "Handle", 1)
    stats = rm.get_floor_stats("123", "Floor 7 (Necron)")
    assert stats["Handle"] == 1
    
    await rm.update_drop("123", "Floor 7 (Necron)", "Handle", -1)
    stats = rm.get_floor_stats("123", "Floor 7 (Necron)")
    assert stats["Handle"] == 0
    
    await rm.update_drop("123", "Floor 7 (Necron)", "Handle", -1)
    stats = rm.get_floor_stats("123", "Floor 7 (Necron)")
    assert stats["Handle"] == 0

@pytest.mark.asyncio
async def test_rng_set_drop(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    rm = RngManager()
    
    await rm.set_drop_count("123", "Floor 7 (Necron)", "Scroll", 5)
    stats = rm.get_floor_stats("123", "Floor 7 (Necron)")
    assert stats["Scroll"] == 5

@pytest.mark.asyncio
async def test_rng_default_target(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    rm = RngManager()
    
    await rm.set_default_target("user1", "user2")
    target = rm.get_default_target("user1")
    assert target == "user2"

@pytest.mark.asyncio
async def test_rng_load(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=True)
    
    data = {
        "123": {
            "Floor 7 (Necron)": {"Handle": 2},
            "_settings": {"default_target": "456"}
        }
    }
    mock_aiofiles.read.return_value = json_utils.dumps(data)
    
    rm = RngManager()
    await rm.initialize()
    
    assert rm.get_floor_stats("123", "Floor 7 (Necron)")["Handle"] == 2
    assert rm.get_default_target("123") == "456"
