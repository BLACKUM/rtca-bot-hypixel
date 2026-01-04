import pytest
from services.link_manager import LinkManager
from services import json_utils

@pytest.mark.asyncio
async def test_load_links_empty(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    lm = LinkManager()
    await lm.initialize()
    assert lm.links == {}

@pytest.mark.asyncio
async def test_load_links_existing(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=True)
    
    data = {"123": "PlayerOne"}
    mock_aiofiles.read.return_value = json_utils.dumps(data)
    
    lm = LinkManager()
    await lm.initialize()
    assert lm.links["123"] == "PlayerOne"

@pytest.mark.asyncio
async def test_link_user(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    lm = LinkManager()
    await lm.initialize()
    
    await lm.link_user(456, "PlayerTwo")
    
    assert lm.links["456"] == "PlayerTwo"
    mock_aiofiles.write.assert_called_once()
    
    args, _ = mock_aiofiles.write.call_args
    written_data = json_utils.loads(args[0])
    assert written_data["456"] == "PlayerTwo"

@pytest.mark.asyncio
async def test_unlink_user(mock_aiofiles, mocker):
    mocker.patch("os.path.exists", return_value=False)
    lm = LinkManager()
    lm.links = {"789": "PlayerThree"}
    
    result = await lm.unlink_user(789)
    assert result is True
    assert "789" not in lm.links
    mock_aiofiles.write.assert_called()

@pytest.mark.asyncio
async def test_unlink_nonexistent(mock_aiofiles, mocker):
    lm = LinkManager()
    result = await lm.unlink_user(999)
    assert result is False
