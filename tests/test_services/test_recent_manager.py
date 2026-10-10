from services.recent_manager import get_teammates


def test_get_teammates_counts_current_runs_only():
    me = "a" * 32
    mate = "b" * 32
    runs = [
        {"completion_ts": 2000, "dungeon_type": "master_catacombs", "dungeon_tier": 7,
         "participants": [{"player_uuid": me, "display_name": "§aMe: Mage (50)"},
                          {"player_uuid": mate, "display_name": "§bMate: Tank (48)"}]},
        {"completion_ts": 1000, "dungeon_type": "catacombs", "dungeon_tier": 0,
         "participants": [{"player_uuid": mate, "display_name": "§bMate: Healer (45)"}]},
    ]

    teammates = get_teammates(me, runs)

    assert [name for name, _ in teammates] == ["Mate"]
    data = teammates[0][1]
    assert data["count"] == 2
    assert data["last_floor"] == "M7"
    assert data["last_class"] == "Tank"
    assert data["last_class_level"] == 48
    assert data["last_ts"] == 2.0


def test_get_teammates_empty():
    assert get_teammates("a" * 32, None) == []
    assert get_teammates("a" * 32, []) == []
