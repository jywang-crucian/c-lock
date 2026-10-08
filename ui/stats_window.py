"""统计面板（PySide6）：今日 / 本周，QPainter 抗锯齿柱状图。"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QRadioButton, QVBoxLayout,
                               QWidget)

import storage.repo as repo
from ui import theme

_WEEK_DAYS = ["一", "二", "三", "四", "五", "六", "日"]


class ChartWidget(QWidget):
    """柱状图绘制。"""

    def __init__(self):
        super().__init__()
        self._data: list[tuple[str, int]] = []
        self.setMinimumHeight(180)

    def set_data(self, data: list[tuple[str, int]]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        data = self._data
        max_val = max((v for _, v in data), default=0)

        if not data or max_val <= 0:
            p.setPen(QColor(theme.AXIS_COLOR))
            p.setFont(theme.FONT_UI)
            p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "暂无记录")
            p.end()
            return

        margin_top, margin_bottom, margin_side = 26, 32, 12
        usable_h = h - margin_top - margin_bottom
        n = len(data)
        slot = (w - 2 * margin_side) / n
        bar_w = slot * 0.58

        for i, (label, value) in enumerate(data):
            bar_h = usable_h * value / max_val if value > 0 else 0
            bar_h = max(2, bar_h) if value > 0 else 0
            cx = margin_side + i * slot + slot / 2
            x0, x1 = cx - bar_w / 2, cx + bar_w / 2
            y1 = margin_top + usable_h
            y0 = y1 - bar_h

            if value > 0:
                grad = QLinearGradient(0, y0, 0, y1)
                grad.setColorAt(0.0, QColor(theme.ACCENT_HOVER))
                grad.setColorAt(1.0, QColor(theme.ACCENT_DARK))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(grad)
                p.drawRoundedRect(QRectF(x0, y0, bar_w, bar_h), 4, 4)
                p.setPen(QColor(theme.STATS_FG))
                p.setFont(theme.FONT_SMALL)
                p.drawText(QRectF(cx - slot / 2, y0 - 18, slot, 14),
                           Qt.AlignmentFlag.AlignCenter, self._fmt_duration(value))
            p.setPen(QColor(theme.STATS_FG))
            p.setFont(theme.FONT_SMALL)
            p.drawText(QRectF(cx - slot / 2, y1 + 8, slot, 16),
                       Qt.AlignmentFlag.AlignCenter, label)
        p.end()

    @staticmethod
    def _fmt_duration(sec: int) -> str:
        m = sec // 60
        if m < 60:
            return f"{m}m"
        h, rm = divmod(m, 60)
        return f"{h}h {rm}m" if rm else f"{h}h"


class StatsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppWindow")
        self.setWindowTitle("统计")
        self.setFixedSize(560, 460)
        self.setStyleSheet(theme.GLOBAL_QSS)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self.total_label = QLabel("")
        self.total_label.setFont(theme.FONT_BIG)
        layout.addWidget(self.total_label)

        mode_row = QHBoxLayout()
        self.today_radio = QRadioButton("今日")
        self.week_radio = QRadioButton("本周")
        self.today_radio.setFont(theme.FONT_UI)
        self.week_radio.setFont(theme.FONT_UI)
        mode_row.addWidget(self.today_radio)
        mode_row.addWidget(self.week_radio)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        self.chart = ChartWidget()
        layout.addWidget(self.chart, 1)

        self.summary_label = QLabel("")
        self.summary_label.setFont(theme.FONT_UI)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.summary_label)

        self.today_radio.setChecked(True)
        self.today_radio.toggled.connect(self._refresh)
        self.week_radio.toggled.connect(self._refresh)

    def _refresh(self) -> None:
        if self.today_radio.isChecked():
            self._show_today()
        else:
            self._show_week()

    def _show_today(self) -> None:
        total = repo.today_total()
        tasks = repo.today_by_task()
        self.total_label.setText(f"今日专注 {self._fmt_hours(total)} 小时")
        self.chart.set_data([(t, s) for t, s in tasks])
        lines = ["今日各任务累计："]
        if not tasks:
            lines.append("暂无记录")
        for task, sec in tasks:
            lines.append(f"  {task}    {self._fmt_hours(sec)} 小时")
        self.summary_label.setText("\n".join(lines))

    def _show_week(self) -> None:
        total = repo.week_total()
        days = repo.week_by_day()
        tasks = repo.week_by_task()
        self.total_label.setText(f"本周专注 {self._fmt_hours(total)} 小时")
        self.chart.set_data([(label, days[i]) for i, label in enumerate(_WEEK_DAYS)])
        lines = ["本周各任务累计："]
        if not tasks:
            lines.append("暂无记录")
        for task, sec in tasks:
            lines.append(f"  {task}    {self._fmt_hours(sec)} 小时")
        self.summary_label.setText("\n".join(lines))

    @staticmethod
    def _fmt_hours(sec: int) -> str:
        return f"{sec / 3600:.1f}"
