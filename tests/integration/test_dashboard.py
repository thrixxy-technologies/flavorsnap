from __future__ import annotations

import pytest

from src.ui.keyboard_manager import KeyboardManager
from src.ui.main_interface import MainInterface


@pytest.mark.integration
def test_main_interface_toggle_history_and_help() -> None:
    ui = MainInterface(classify_fn=lambda event=None: None, save_image_fn=lambda: None)

    assert ui.history_panel.visible is False
    ui.toggle_history()
    assert ui.history_panel.visible is True
    ui.toggle_history()
    assert ui.history_panel.visible is False

    assert ui.help_panel.visible is False
    ui.toggle_help()
    assert ui.help_panel.visible is True


@pytest.mark.integration
def test_keyboard_manager_invokes_callback_and_resets_bridge_value() -> None:
    called: list[str] = []

    def target_callback(combo: str) -> None:
        called.append(combo)

    km = KeyboardManager(target_callback=target_callback)
    km.keyboard_event.value = "ctrl+h"

    assert called == ["ctrl+h"]
    assert km.keyboard_event.value == ""

