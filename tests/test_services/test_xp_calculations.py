from services.xp_calculations import get_dungeon_level, get_class_average
from core.config import DUNGEON_XP

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
