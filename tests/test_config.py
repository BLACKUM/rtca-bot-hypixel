import pytest
import shutil
import os
import json
from core.configuration import BotConfig

CONFIG_FILE = "data/config.json"
TEST_CONFIG_FILE = "data/test_config.json"

@pytest.fixture
def config():
    cfg = BotConfig(file_path=TEST_CONFIG_FILE)
    
    if os.path.exists(TEST_CONFIG_FILE):
        os.remove(TEST_CONFIG_FILE)
        
    yield cfg
    
    if os.path.exists(TEST_CONFIG_FILE):
        os.remove(TEST_CONFIG_FILE)

def test_default_values(config):
    assert config.xp_per_run_default == 300000.0
    assert config.target_level == 50
    assert config.debug_mode is True
    assert isinstance(config.owner_ids, list)
    assert len(config.owner_ids) > 0

def test_save_and_load(config):
    config.xp_per_run_default = 500.0
    config.debug_mode = False
    config.owner_ids = [12345]
    
    config.save()
    
    assert os.path.exists(TEST_CONFIG_FILE)
    
    new_config = BotConfig(file_path=TEST_CONFIG_FILE)
    new_config.load()
    
    assert new_config.xp_per_run_default == 500.0
    assert new_config.debug_mode is False
    assert new_config.owner_ids == [12345]

def test_partial_load(config):
    partial_data = {"target_level": 99}
    with open(TEST_CONFIG_FILE, "w") as f:
        json.dump(partial_data, f)
        
    config.load()
    
    assert config.target_level == 99
    assert config.xp_per_run_default == 300000.0
