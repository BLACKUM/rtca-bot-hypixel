import pytest
from unittest.mock import MagicMock
from modules.admin import SoloRunPickerView, SoloRunPickerSelect


def test_solo_run_picker_single_page():
    bot = MagicMock()
    runs = [{"uuid": f"uuid_{i}", "ign": f"Player{i}", "time_ms": 10000 + i, "verified": True} for i in range(1, 15)]
    
    view = SoloRunPickerView(bot, "F7", runs)
    
    assert view.total_pages == 1
    assert view.page == 1
    assert view.get_content() == "Select a run on **F7**:"
    
    # 1 Select + 1 Back button = 2 components
    assert len(view.children) == 2
    select = view.children[0]
    assert isinstance(select, SoloRunPickerSelect)
    assert len(select.options) == 14
    assert select.options[0].label == "#1 Player1 — 00:10.001"


def test_solo_run_picker_multi_page():
    bot = MagicMock()
    runs = [{"uuid": f"uuid_{i}", "ign": f"Player{i}", "time_ms": 10000 + i, "verified": i % 2 == 0} for i in range(1, 61)]
    
    view = SoloRunPickerView(bot, "M7", runs, page=1)
    
    assert view.total_pages == 3
    assert view.page == 1
    assert view.get_content() == "Select a run on **M7** (Page 1/3):"
    
    # 1 Select + Prev + Next + Back = 4 components
    assert len(view.children) == 4
    select = view.children[0]
    assert isinstance(select, SoloRunPickerSelect)
    assert len(select.options) == 25
    assert select.options[0].label.startswith("#1 ")
    assert select.options[24].label.startswith("#25 ")
    
    prev_btn = view.children[1]
    next_btn = view.children[2]
    assert prev_btn.disabled is True
    assert next_btn.disabled is False
    
    # Switch to page 2
    view.page = 2
    view.update_components()
    assert view.get_content() == "Select a run on **M7** (Page 2/3):"
    select_p2 = view.children[0]
    assert len(select_p2.options) == 25
    assert select_p2.options[0].label.startswith("#26 ")
    assert select_p2.options[24].label.startswith("#50 ")
    assert view.children[1].disabled is False
    assert view.children[2].disabled is False
    
    # Switch to page 3
    view.page = 3
    view.update_components()
    assert view.get_content() == "Select a run on **M7** (Page 3/3):"
    select_p3 = view.children[0]
    assert len(select_p3.options) == 10
    assert select_p3.options[0].label.startswith("#51 ")
    assert select_p3.options[9].label.startswith("#60 ")
    assert view.children[1].disabled is False
    assert view.children[2].disabled is True
