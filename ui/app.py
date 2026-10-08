"""控制器（PySide6）：整合引擎回调、自动接续，协调悬浮球与面板。"""
from __future__ import annotations

import math
import winsound

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

import core.config as config
import storage.repo as repo
from core.timer import Mode, TimerEngine
from ui import theme
from ui.ball import FloatingBall
from ui.panel import BallPanel
from ui.settings_dialog import SettingsDialog
from ui.stats_window import StatsWindow


class App(QObject):
    # 跨线程信号：pystray 子线程 emit → 主线程槽（QueuedConnection 自动）
    sig_show = Signal()
    sig_pause_resume = Signal()
    sig_stop = Signal()
    sig_quit = Signal()

    def __init__(self, settings: dict, tray=None):
        super().__init__()
        self.settings = settings
        self.tray = tray

        self.engine = TimerEngine(settings, self._on_segment_end)

        self.transitioning = False
        self.pending_mode = Mode.IDLE
        self._stats = None

        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._begin_next)

        self.ball = FloatingBall(self, settings)
        self.panel = BallPanel(self, settings)

        self.sig_show.connect(self.show_window)
        self.sig_pause_resume.connect(self.toggle_pause)
        self.sig_stop.connect(self.stop_engine)
        self.sig_quit.connect(self.quit_app)

        self._tick = QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(200)

        self._tick_1s = QTimer(self)
        self._tick_1s.timeout.connect(self._update_tray)
        self._tick_1s.start(1000)

    # ---- 工具 ----
    @staticmethod
    def mode_key(mode: Mode) -> str:
        if mode == Mode.FOCUS:
            return "focus"
        if mode == Mode.SHORT_BREAK:
            return "short_break"
        if mode == Mode.LONG_BREAK:
            return "long_break"
        return "idle"

    @staticmethod
    def fmt_hms(sec: int) -> str:
        h, rem = divmod(int(sec), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @staticmethod
    def fmt_mmss(sec: int) -> str:
        m, s = divmod(int(sec), 60)
        return f"{m:02d}:{s:02d}"

    def _duration_minutes(self, mode: Mode) -> int:
        s = self.settings
        if mode == Mode.FOCUS:
            return int(s.get("focus_min", 25))
        if mode == Mode.SHORT_BREAK:
            return int(s.get("short_break_min", 5))
        if mode == Mode.LONG_BREAK:
            return int(s.get("long_break_min", 15))
        return 0

    # ---- 控制 ----
    def start_from_panel(self) -> None:
        task = self.panel.task_combo.currentText().strip()
        self._remember_task(task)
        self.transitioning = False
        self.engine.start(task or "未命名")
        self._refresh()

    def pause(self) -> None:
        self.engine.pause()
        self._refresh()

    def resume(self) -> None:
        self.engine.resume()
        self._refresh()

    def stop(self) -> None:
        self.engine.stop()
        self._refresh()

    def skip(self) -> None:
        self.engine.skip()
        self._refresh()

    def cancel_auto(self) -> None:
        self._auto_timer.stop()
        self.transitioning = False
        self._refresh()

    def _remember_task(self, task: str) -> None:
        if not task:
            return
        history = list(self.settings.get("task_history", []))
        if task not in history:
            history.append(task)
            self.settings["task_history"] = history
            config.save_settings(self.settings)
            self.panel.update_task_history(history)

    # ---- 面板显隐 ----
    def toggle_panel(self) -> None:
        if self.panel.isVisible():
            self.hide_panel()
        else:
            self.show_panel()

    def show_panel(self) -> None:
        scr = QApplication.primaryScreen().availableGeometry()
        px = scr.center().x() - self.panel.w // 2
        py = scr.center().y() - self.panel.h // 2
        self.panel.show_at(px, py)
        self.ball.set_pinned(True)

    def hide_panel(self) -> None:
        self.panel.hide_panel()
        self.ball.set_pinned(False)

    # ---- 子窗口 ----
    def open_stats(self) -> None:
        if self._stats is not None:
            self._stats.close()
        self._stats = StatsWindow()
        self._stats.show()

    def open_settings(self) -> None:
        dlg = SettingsDialog(None, self.settings, on_save=self._apply_settings)
        dlg.exec()

    def _apply_settings(self) -> None:
        self.panel.update_task_history(self.settings.get("task_history", []))
        self._refresh()

    # ---- 托盘接口 ----
    def show_window(self) -> None:
        self.ball.show_full()

    def toggle_pause(self) -> None:
        if not self.engine.running:
            return
        if self.engine.paused:
            self.engine.resume()
        else:
            self.engine.pause()
        self._refresh()

    def stop_engine(self) -> None:
        if self.engine.running:
            self.engine.stop()
            self._refresh()

    def quit_app(self) -> None:
        if self.engine.running:
            r = QMessageBox.question(None, "退出", "正在计时，确定退出？",
                                     QMessageBox.StandardButton.Yes
                                     | QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return
        if self.tray:
            self.tray.stop()
        QApplication.quit()

    # ---- 引擎回调 ----
    def _on_segment_end(self, record, next_mode: Mode) -> None:
        if record is not None:
            repo.add_session(record)
        self._play_sound()
        self._reveal_ball()

        if next_mode == Mode.IDLE:
            self.transitioning = False
            self._refresh()
            return

        self.transitioning = True
        self.pending_mode = next_mode
        self._refresh()
        self.show_panel()
        self._auto_timer.start(3000)

    def _begin_next(self) -> None:
        self.transitioning = False
        self.engine.begin(self.pending_mode)
        self._refresh()

    # ---- 音频 / 前置 ----
    def _play_sound(self) -> None:
        if self.settings.get("sound_on", True):
            try:
                winsound.PlaySound("SystemAsterisk",
                                   winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass

    def _reveal_ball(self) -> None:
        if self.ball._docked and self.ball._hidden:
            self.ball.show_full()
            self.ball._hidden = False

    # ---- 主循环 ----
    def _on_tick(self) -> None:
        self.engine.tick()
        self._refresh()

    def _refresh(self) -> None:
        if self.engine.running:
            seconds = self.engine.remaining
            key = self.mode_key(self.engine.mode)
        elif self.transitioning:
            seconds = self._duration_minutes(self.pending_mode) * 60
            key = self.mode_key(self.pending_mode)
        else:
            seconds = 0
            key = "idle"
        self.ball.set_display(key, seconds)
        self.panel.refresh()

    def _update_tray(self) -> None:
        if not self.tray:
            return
        if self.engine.running:
            key = self.mode_key(self.engine.mode)
            minutes = math.ceil(self.engine.remaining / 60)
            self.tray.update_icon(minutes, theme.MODE_COLORS[key])
            self.tray.update_tooltip(
                f"{theme.MODE_LABEL[key]} {self.fmt_mmss(self.engine.remaining)} - {self.engine.task}")
        else:
            self.tray.reset_icon()
            self.tray.update_tooltip("c-lock 专注时钟")
