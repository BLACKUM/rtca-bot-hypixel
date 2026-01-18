import pytest
from services.simulation_logic import simulate_to_level_all50
from services.xp_calculations import get_total_xp_for_level
from core.game_data import DUNGEON_XP
from unittest.mock import patch, MagicMock
from core.config import config

@patch("services.simulation_logic.config")
def test_simulate_already_maxed(mock_config):
    mock_config.target_level = 50
    target_xp_50 = get_total_xp_for_level(50)
    max_xp = target_xp_50 + 1000
    classes = {
        "archer": max_xp, 
        "berserk": max_xp, 
        "healer": max_xp, 
        "mage": max_xp, 
        "tank": max_xp
    }
    
    runs_total, results = simulate_to_level_all50(classes, 10000.0, {"global": 1.0})
    assert runs_total == 0
    assert results["archer"]["runs_done"] == 0

def test_simulate_one_run_needed():

    target_xp = 50
    classes = {"mage": 0}
    
    runs_total, results = simulate_to_level_all50(classes, 1000000.0, {"global": 1.0}, target_level=1)
    
    assert runs_total == 1
    assert results["mage"]["runs_done"] == 1

def test_simulate_stops_at_max_runs():
    classes = {"mage": 0}
    max_runs = 100
    
    runs_total, results = simulate_to_level_all50(classes, 1.0, {"global": 1.0}, max_runs=max_runs)
    
    assert runs_total == max_runs
