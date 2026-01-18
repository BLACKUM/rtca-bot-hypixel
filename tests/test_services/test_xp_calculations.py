from services.xp_calculations import get_dungeon_level, get_class_average
from core.game_data import DUNGEON_XP

def test_get_dungeon_level_zero():
    assert get_dungeon_level(0) == 0

def test_get_dungeon_level_exact():
    total_xp_10 = sum(DUNGEON_XP[1:11])
    assert get_dungeon_level(total_xp_10) == 10

def test_get_dungeon_level_partial():
    base_10 = sum(DUNGEON_XP[1:11])
    next_level_cost = DUNGEON_XP[11]
    
    xp = base_10 + (next_level_cost / 2)
    assert 10.49 <= get_dungeon_level(xp) <= 10.51

def test_get_dungeon_level_max():
    total_xp_50 = sum(DUNGEON_XP[1:])

    total_xp_50 = sum(DUNGEON_XP[1:-1])
    assert get_dungeon_level(total_xp_50) == 50

def test_class_average():
    xp_50 = sum(DUNGEON_XP[1:-1])
    xp_25 = sum(DUNGEON_XP[1:26])
    
    classes = {
        "archer": 0,        # 0
        "berserk": xp_50,   # 50
        "healer": xp_25,    # 25
        "mage": xp_50,      # 50
        "tank": 0           # 0
    }
    # Avg: (0+50+25+50+0) / 5 = 25
    assert get_class_average(classes) == 25.0

def test_calculate_dungeon_xp_per_run_basic():
    # Base floor 28000 (F7)
    # No bonuses
    # 1000 * (0.95 + 0 + 75 * 0.022) = 1000 * (0.95 + 1.65) = 1000 * 2.6 = 2600
    from services.xp_calculations import calculate_dungeon_xp_per_run
    
    xp = calculate_dungeon_xp_per_run(1000.0, 0.0, 0.0, 1.0, 1.0)
    assert xp == 2600.0

def test_calculate_dungeon_xp_per_run_full():
    # Test F7 (28000) with  bonuses
    # ring=0.1, heca=0.02, mayor=1.0
    # 28000 * 1.68 = 47040
    from services.xp_calculations import calculate_dungeon_xp_per_run
    
    xp = calculate_dungeon_xp_per_run(28000.0, 0.1, 0.02, 1.0, 1.0)
    assert xp == 47041.0
