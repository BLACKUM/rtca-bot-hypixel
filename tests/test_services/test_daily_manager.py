import pytest
from services.daily_manager import DailyManager

@pytest.mark.asyncio
async def test_daily_register(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    dm = DailyManager()
    
    valid_uuid = "a" * 32
    await dm.register_user("123", "IGN1", valid_uuid)
    
    users = dm.get_tracked_users()
    assert len(users) == 1
    assert users[0] == ("123", valid_uuid)
