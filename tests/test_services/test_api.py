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
async def test_get_profile_data_priority(mocker):
    mocker.patch("services.api.cache_get", return_value=None)
    mocker.patch("services.api.cache_set")
    mocker.patch("services.api.init_session")
    
    mock_soopy = mocker.patch("services.api.fetch_soopy_profile", return_value=None)
    mock_adjectils = mocker.patch("services.api.fetch_adjectils_profile", return_value=None)
    
    from core.config import config
    config.primary_api = "soopy"
    await api.get_profile_data("a"*32)
    
    assert mock_soopy.called
    assert mock_adjectils.called
    
    mock_soopy.reset_mock()
    mock_adjectils.reset_mock()
    
    config.primary_api = "skycrypt"
    await api.get_profile_data("a"*32)
    
    assert mock_adjectils.called
    assert mock_soopy.called

@pytest.mark.asyncio
async def test_get_profile_data_success_stop(mocker):
    mocker.patch("services.api.cache_get", return_value=None)
    mocker.patch("services.api.cache_set")
    mocker.patch("services.api.init_session")
    
    mock_soopy = mocker.patch("services.api.fetch_soopy_profile", return_value={"_source": "soopy"})
    mock_adjectils = mocker.patch("services.api.fetch_adjectils_profile", return_value={"_source": "skycrypt"})
    
    from core.config import config
    config.primary_api = "soopy"
    result = await api.get_profile_data("a"*32)
    assert result["_source"] == "soopy"
    assert not mock_adjectils.called
    
    mock_soopy.reset_mock()
    mock_adjectils.reset_mock()
    
    config.primary_api = "skycrypt"
    result = await api.get_profile_data("a"*32)
    assert result["_source"] == "skycrypt"
    assert not mock_soopy.called
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

    player_data = {
        "stats": {
            "achievements": {
                "skyblock": {
                    "dungeon_secrets": 74445
                }
            }
        }
    }
    
    result = api._parse_soopy_dungeon_stats(member_data, player_data)
    
    assert result["catacombs"] == 1000.5
    assert result["secrets"] == 74445
    assert result["blood_mob_kills"] == 50
    assert result["magical_power"] == 450
    assert result["accessory_bag_storage"]["highest_magical_power"] == 450
    assert result["classes"]["Archer"] == 100.0
    assert result["classes"]["Berserk"] == 200.0
    assert result["floors"]["F1"]["runs"] == 10
    assert result["floors"]["F1"]["fastest_s"] == 100


@pytest.mark.asyncio
async def test_get_dungeon_stats_soopy_with_extra_api(mocker):
    mock_profile = {
        "profiles": [
            {
                "selected": True,
                "members": {
                    "uuid": {
                        "dungeons": {"catacombs_xp": 10},
                        "accessory_reforge": {"highest_magical_power": 123},
                        "kills": {"watcher_summon_undead": 5}
                    }
                }
            }
        ]
    }
    mock_player = {
        "stats": {
            "achievements": {
                "skyblock": {
                    "dungeon_secrets": 74445
                }
            }
        }
    }
    mocker.patch("services.api.get_profile_data", return_value=mock_profile)
    mocker.patch("services.api.get_soopy_player_data", return_value=mock_player)
    
    stats = await api.get_dungeon_stats("uuid")
    
    assert stats["magical_power"] == 123
    assert stats["accessory_bag_storage"]["highest_magical_power"] == 123
    assert stats["secrets"] == 74445


