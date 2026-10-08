"""设置对话框（PySide6）：改配置即时生效并落盘。"""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QDialog, QGridLayout, QHBoxLayout,
                               QLabel, QPlainTextEdit, QPushButton, QSpinBox,
                               QVBoxLayout)

import core.config as config
from ui import theme


class SettingsDialog(QDialog):
    def __init__(self, parent, settings: dict, on_save=None):
        super().__init__(parent)
        self.settings = settings
        self.on_save = on_save

        self.setWindowTitle("设置")
        self.setModal(True)
        self.setFixedSize(300, 430)
        self.setStyleSheet(theme.GLOBAL_QSS)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self.int_vars: dict[str, QSpinBox] = {}
        rows = [
            ("专注时长（分钟）", "focus_min", 1, 180),
            ("短休时长（分钟）", "short_break_min", 1, 60),
            ("长休时长（分钟）", "long_break_min", 1, 120),
            ("长休间隔（轮）", "long_break_every", 2, 12),
        ]
        for i, (label, key, lo, hi) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setFont(theme.FONT_UI)
            spin = QSpinBox()
            spin.setRange(lo, hi)
            spin.setValue(int(self.settings.get(key, lo)))
            spin.setFont(theme.FONT_UI)
            self.int_vars[key] = spin
            grid.addWidget(lbl, i, 0)
            grid.addWidget(spin, i, 1)
        layout.addLayout(grid)

        self.bool_vars: dict[str, QCheckBox] = {}
        bool_rows = [
            ("段结束自动接续", "auto_continue"),
            ("窗口置顶", "always_on_top"),
            ("提示音", "sound_on"),
            ("关闭时收进托盘", "minimize_to_tray"),
        ]
        for label, key in bool_rows:
            cb = QCheckBox(label)
            cb.setChecked(bool(self.settings.get(key, True)))
            cb.setFont(theme.FONT_UI)
            self.bool_vars[key] = cb
            layout.addWidget(cb)

        task_lbl = QLabel("任务历史（每行一个）")
        task_lbl.setFont(theme.FONT_UI)
        layout.addWidget(task_lbl)
        self.history_text = QPlainTextEdit()
        self.history_text.setPlainText("\n".join(self.settings.get("task_history", [])))
        self.history_text.setFont(theme.FONT_UI)
        layout.addWidget(self.history_text, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save = QPushButton("保存")
        save.setFont(theme.FONT_UI)
        save.clicked.connect(self._save)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _save(self) -> None:
        for key, spin in self.int_vars.items():
            self.settings[key] = spin.value()
        for key, cb in self.bool_vars.items():
            self.settings[key] = cb.isChecked()

        lines = self.history_text.toPlainText().splitlines()
        seen, history = set(), []
        for ln in lines:
            t = ln.strip()
            if t and t not in seen:
                seen.add(t)
                history.append(t)
        self.settings["task_history"] = history

        config.save_settings(self.settings)
        if self.on_save:
            self.on_save()
        self.accept()
