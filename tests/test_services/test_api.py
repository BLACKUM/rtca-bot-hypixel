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
    mock_resp.json.return_value = {"id": "real_uuid", "name": "Player"}
    
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
    mock_resp.json.return_value = {"success": True, "profiles": []}
    
    cm = mocker.AsyncMock()
    cm.__aenter__.return_value = mock_resp
    cm.__aexit__.return_value = None
    mock_session.get.return_value = cm
    
    data = await api.get_profile_data("a"*32) # 32 chars
    assert data == {"success": True, "profiles": [], "_source": "hypixel"}

@pytest.mark.asyncio
async def test_get_profile_data_skips_hypixel_on_cooldown(mocker):
    mocker.patch("services.api.cache_get", return_value=None)
    mocker.patch("services.api.init_session")
    mocker.patch.object(api._api_cooldown, "is_cooling_down", return_value=True)
    mock_hypixel = mocker.patch("services.api.fetch_hypixel_profile")

    assert await api.get_profile_data("a"*32) is None
    assert not mock_hypixel.called

@pytest.mark.asyncio
async def test_fetch_hypixel_profile(mocker):
    mock_session = mocker.MagicMock()
    mock_session.get = mocker.Mock()
    mocker.patch("services.api._SESSION", mock_session)
    mocker.patch("services.api.HYPIXEL_API_KEY", "test_key")
    
    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"success": True, "profiles": []}
    
    cm = mocker.AsyncMock()
    cm.__aenter__.return_value = mock_resp
    cm.__aexit__.return_value = None
    mock_session.get.return_value = cm
    
    data = await api.fetch_hypixel_profile("a"*32)
    assert data == {"success": True, "profiles": [], "_source": "hypixel"}
    
    mock_session.get.assert_called_once()
    call_kwargs = mock_session.get.call_args.kwargs
    assert call_kwargs["headers"] == {"API-Key": "test_key"}

@pytest.mark.asyncio
async def test_get_player_discord(mocker):
    mock_session = mocker.MagicMock()
    mocker.patch("services.api._SESSION", mock_session)
    mocker.patch("services.api.HYPIXEL_API_KEY", "test_key")

    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"success": True, "player": {"socialMedia": {"links": {"DISCORD": "someone"}}}}

    cm = mocker.AsyncMock()
    cm.__aenter__.return_value = mock_resp
    cm.__aexit__.return_value = None
    mock_session.get.return_value = cm

    assert await api.get_player_discord("a"*32) == "someone"
    assert mock_session.get.call_args.kwargs["headers"] == {"API-Key": "test_key"}

    mock_resp.json.return_value = {"success": True, "player": None}
    assert await api.get_player_discord("a"*32) is None

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
    
    prices = await api._fetch_bazaar_prices()
    assert prices == {"ITEM_ID": 100.0}

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
    
    prices = await api._fetch_ah_prices()
    assert prices == {"ITEM_ID": 200.0}

@pytest.mark.asyncio
async def test_get_dungeon_stats_ignores_total(mocker):
    mock_profile = {
        "profiles": [
            {
                "selected": True,
                "members": {
                    "uuid": {
                        "dungeons": {
                            "experience": 1000,
                            "secrets": 10,
                            "dungeon_types": {
                                "catacombs": {
                                    "tier_completions": {
                                        "1": 10,
                                        "total": 50
                                    }
                                },
                                "master_catacombs": {
                                    "tier_completions": {
                                        "1": 5,
                                        "total": 20
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ]
    }
    mocker.patch("services.api.get_profile_data", return_value=mock_profile)
    stats = await api.get_dungeon_stats("uuid")
    
    assert "F1" in stats["floors"]
    assert "M1" in stats["floors"]
    assert "FTotal" not in stats["floors"]
    assert "MTotal" not in stats["floors"]
    assert "Ftotal" not in stats["floors"]
    assert "Mtotal" not in stats["floors"]
    
    total_runs = sum(f["runs"] for f in stats["floors"].values())
    assert total_runs == 15

def test_api_cooldown_escalation(mocker):
    api._api_cooldown._cooldowns = {}
    api._api_cooldown._consecutive_failures = {}

    mock_time = mocker.patch("services.api.time.time", return_value=100.0)

    api._api_cooldown.record_failure("test_api", 429, retry_after=1)
    assert api._api_cooldown._cooldowns["test_api"] == 105.0
    assert api._api_cooldown.is_cooling_down("test_api") is True

    mock_time.return_value = 106.0
    assert api._api_cooldown.is_cooling_down("test_api") is False

    api._api_cooldown.record_failure("test_api", 429, retry_after=1)
    assert api._api_cooldown._cooldowns["test_api"] == 166.0
    assert api._api_cooldown.is_cooling_down("test_api") is True

    api._api_cooldown.record_success("test_api")
    assert "test_api" not in api._api_cooldown._consecutive_failures

    mock_time.return_value = 200.0
    api._api_cooldown.record_failure("test_api", 500)
    assert api._api_cooldown._cooldowns["test_api"] == 230.0

