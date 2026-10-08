"""控制面板：圆角毛玻璃面板，居中显示，弹性按钮（开始为大圆）。"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

from core.timer import Mode
from ui import theme
from ui.fx import ElasticButton, blurred_qpixmap, find_bg_image


class BallPanel(QWidget):
    def __init__(self, app, settings: dict):
        super().__init__(None)
        self.app = app
        self.settings = settings
        self.w = theme.PANEL_W
        self.h = theme.PANEL_H
        self.r = theme.RADIUS
        self._btn_cache: dict = {}
        self._commands: dict = {}

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.w, self.h)

        # 背景：图片模糊 + 压暗
        bg_path = find_bg_image()
        self._bg = None
        if bg_path is not None:
            try:
                self._bg = blurred_qpixmap(bg_path, self.w, self.h, blur=18, darken=0.55)
            except Exception:
                self._bg = None

        self._build_ui()

    # ---------- 背景 ----------
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.w, self.h), self.r, self.r)
        p.setClipPath(path)
        if self._bg is not None:
            p.drawPixmap(0, 0, self._bg)
        else:
            p.fillPath(path, QColor(theme.PANEL_BG))
        p.setClipping(False)
        p.setPen(QPen(QColor(theme.PANEL_BORDER), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()

    # ---------- 内容 ----------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 10, 16, 18)
        outer.setSpacing(8)

        # 倒计时大字
        self.timer_label = QLabel("00:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setFont(theme.FONT_TIMER)
        self.timer_label.setStyleSheet(f"color: {theme.TEXT_MAIN};")
        outer.addWidget(self.timer_label)

        # 模式徽标 + 轮次
        badge_row = QHBoxLayout()
        badge_row.addStretch(1)
        self.badge_label = QLabel("空闲")
        self.badge_label.setFont(theme.FONT_BOLD)
        self.badge_label.setStyleSheet(f"color: {theme.ACCENT};")
        badge_row.addWidget(self.badge_label)
        badge_row.addSpacing(12)
        self.round_label = QLabel("")
        self.round_label.setFont(theme.FONT_SMALL)
        self.round_label.setStyleSheet(f"color: {theme.TEXT_SUB};")
        badge_row.addWidget(self.round_label)
        badge_row.addStretch(1)
        outer.addLayout(badge_row)

        # 过渡提示
        self.hint_label = QLabel("")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setFont(theme.FONT_SMALL)
        self.hint_label.setStyleSheet(f"color: {theme.ACCENT};")
        outer.addWidget(self.hint_label)

        # 任务输入
        task_row = QHBoxLayout()
        task_lbl = QLabel("任务")
        task_lbl.setFont(theme.FONT_UI)
        task_lbl.setStyleSheet(f"color: {theme.TEXT_SUB};")
        task_row.addWidget(task_lbl)
        self.task_combo = QComboBox()
        self.task_combo.setEditable(True)
        self.task_combo.setFont(theme.FONT_UI)
        self.task_combo.setMinimumHeight(28)
        self.task_combo.addItems(self.settings.get("task_history", []))
        self.task_combo.setCurrentText("")
        self.task_combo.lineEdit().setPlaceholderText("选择或输入任务")
        task_row.addWidget(self.task_combo, 1)
        outer.addLayout(task_row)

        # 开始按钮：大圆
        start_row = QHBoxLayout()
        start_row.addStretch(1)
        self.start_btn = ElasticButton("开始")
        self.start_btn.setObjectName("StartButton")
        self.start_btn.setFixedSize(80, 80)
        self.start_btn.setFont(theme.FONT_BOLD)
        self.start_btn.clicked.connect(lambda: self._dispatch(self.start_btn))
        start_row.addWidget(self.start_btn)
        start_row.addStretch(1)
        outer.addLayout(start_row)

        # 副按钮：圆角矩形
        sub_row = QHBoxLayout()
        sub_row.addStretch(1)
        self.btn2 = ElasticButton("统计")
        self.btn2.setFixedSize(72, 30)
        self.btn2.setFont(theme.FONT_UI)
        self.btn2.clicked.connect(lambda: self._dispatch(self.btn2))
        sub_row.addWidget(self.btn2)
        sub_row.addSpacing(12)
        self.btn3 = ElasticButton("设置")
        self.btn3.setFixedSize(72, 30)
        self.btn3.setFont(theme.FONT_UI)
        self.btn3.clicked.connect(lambda: self._dispatch(self.btn3))
        sub_row.addWidget(self.btn3)
        sub_row.addStretch(1)
        outer.addLayout(sub_row)

    # ---------- 显隐 ----------
    def show_at(self, x: int, y: int) -> None:
        self.move(x, y)
        self.show()
        self.raise_()
        self.refresh()

    def hide_panel(self) -> None:
        self.hide()

    # ---------- 刷新 ----------
    def _set_btn(self, btn: ElasticButton, text: str, command, enabled: bool) -> None:
        sig = (text, enabled, command)
        if self._btn_cache.get(btn) == sig:
            return
        self._btn_cache[btn] = sig
        self._commands[btn] = command
        btn.setText(text)
        btn.setEnabled(enabled)

    def _dispatch(self, btn: ElasticButton) -> None:
        cmd = self._commands.get(btn)
        if cmd is not None:
            cmd()

    def refresh(self) -> None:
        if not self.isVisible():
            return
        app = self.app
        eng = app.engine
        every = app.settings.get("long_break_every", 4)

        if app.transitioning:
            timer_text = "00:00"
        elif eng.running:
            timer_text = app.fmt_mmss(eng.remaining)
        else:
            timer_text = "00:00"
        self.timer_label.setText(timer_text)

        if app.transitioning:
            name = theme.MODE_LABEL[app.mode_key(app.pending_mode)]
            self.badge_label.setText(name)
            self.round_label.setText(f"#{eng.round_no} / {every}")
            self.hint_label.setText(f"3 秒后进入{name}…")
        elif eng.running:
            name = theme.MODE_LABEL[app.mode_key(eng.mode)]
            self.badge_label.setText(name)
            self.round_label.setText(f"#{eng.round_no} / {every}")
            self.hint_label.setText("")
        else:
            self.badge_label.setText("空闲")
            self.round_label.setText("")
            self.hint_label.setText("")

        if app.transitioning:
            self._set_btn(self.start_btn, "取消自动", app.cancel_auto, True)
            self._set_btn(self.btn2, "统计", app.open_stats, False)
            self._set_btn(self.btn3, "设置", app.open_settings, False)
        elif not eng.running:
            self._set_btn(self.start_btn, "开始", app.start_from_panel, True)
            self._set_btn(self.btn2, "统计", app.open_stats, True)
            self._set_btn(self.btn3, "设置", app.open_settings, True)
        else:
            self._set_btn(self.start_btn,
                          "继续" if eng.paused else "暂停",
                          app.resume if eng.paused else app.pause, True)
            self._set_btn(self.btn2, "停止", app.stop, True)
            is_break = eng.mode in (Mode.SHORT_BREAK, Mode.LONG_BREAK)
            self._set_btn(self.btn3, "跳过", app.skip, is_break)

    def update_task_history(self, history) -> None:
        self.task_combo.clear()
        self.task_combo.addItems(history)
