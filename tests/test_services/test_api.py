import pytest
from services import api
from services import json_utils

@pytest.fixture
def mock_session_get(mocker):
    mock_session = mocker.MagicMock() 
    mock_session.get = mocker.Mock()
    mocker.patch("services.api._SESSION", mock_session)
    return mock_session

@pytest.mark.asyncio
async def test_get_uuid_cached(mocker):
    mocker.patch("services.api.cache_get", return_value="cached_uuid")
    uuid = await api.get_uuid("Player")
    assert uuid == "cached_uuid"

@pytest.mark.asyncio
async def test_get_uuid_fetch(mocker):
    mocker.patch("services.api.cache_get", return_value=None)
    mock_set = mocker.patch("services.api.cache_set")
    
    mock_session = mocker.MagicMock()
    mock_session.get = mocker.Mock()
    mocker.patch("services.api._SESSION", mock_session)
    mocker.patch("services.api.init_session")
    
    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"data": {"player": {"raw_id": "real_uuid"}}}
    
    cm = mocker.AsyncMock()
    cm.__aenter__.return_value = mock_resp
    cm.__aexit__.return_value = None
    mock_session.get.return_value = cm
    
    uuid = await api.get_uuid("Player")
    assert uuid == "real_uuid"
    mock_set.assert_called_with("player", "real_uuid", ttl=pytest.approx(60))

@pytest.mark.asyncio
async def test_get_profile_data(mocker):
    mocker.patch("services.api.cache_get", return_value=None)
    mock_session = mocker.MagicMock()
    mock_session.get = mocker.Mock()
    mocker.patch("services.api._SESSION", mock_session)
    
    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"profiles": []}
    
    cm = mocker.AsyncMock()
    cm.__aenter__.return_value = mock_resp
    cm.__aexit__.return_value = None
    mock_session.get.return_value = cm
    
    data = await api.get_profile_data("a"*32) # 32 chars
    assert data == {"profiles": []}

@pytest.mark.asyncio
async def test_get_bazaar_prices(mocker):
    mocker.patch("services.api.cache_get", return_value=None)
    mock_set = mocker.patch("services.api.cache_set")
    
    mock_session = mocker.MagicMock()
    mock_session.get = mocker.Mock()
    mocker.patch("services.api._SESSION", mock_session)
    
    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "products": {
            "ITEM_ID": {"quick_status": {"sellPrice": 100.0}}
        }
    }
    
    cm = mocker.AsyncMock()
    cm.__aenter__.return_value = mock_resp
    cm.__aexit__.return_value = None
    mock_session.get.return_value = cm
    
    prices = await api.get_bazaar_prices()
    assert prices == {"ITEM_ID": 100.0}
    mock_set.assert_called_once()

@pytest.mark.asyncio
async def test_get_ah_prices(mocker):
    mocker.patch("services.api.cache_get", return_value=None)
    mock_set = mocker.patch("services.api.cache_set")
    
    mock_session = mocker.MagicMock()
    mock_session.get = mocker.Mock()
    mocker.patch("services.api._SESSION", mock_session)
    
    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"ITEM_ID": 200.0}
    
    cm = mocker.AsyncMock()
    cm.__aenter__.return_value = mock_resp
    cm.__aexit__.return_value = None
    mock_session.get.return_value = cm
    
    prices = await api.get_ah_prices()
    assert prices == {"ITEM_ID": 200.0}
    mock_set.assert_called_once()

