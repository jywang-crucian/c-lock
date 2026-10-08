"""计时状态机（纯逻辑，不 import tkinter）。"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from core.config import MIN_RECORD_SEC


class Mode(Enum):
    IDLE = "idle"
    FOCUS = "focus"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


@dataclass
class SegmentRecord:
    """一段已结束的记录，交给 storage 层入库。"""

    task: str
    kind: str
    started_at: str
    ended_at: str
    duration_sec: int
    completed: int


# core -> ui 的唯一出口
SegmentEndCallback = Callable[[Optional[SegmentRecord], Mode], None]


class TimerEngine:
    """番茄钟状态机。

    计时用 time.monotonic() 目标时刻，禁止计数器累加，避免误差累积。
    轮次判定：round_no 从 1 起，休息结束时 +1；专注自然走完时用
    round_no % long_break_every == 0 判断是否进入长休。
    """

    def __init__(self, settings: dict, on_segment_end: SegmentEndCallback):
        self._settings = settings
        self._on_segment_end = on_segment_end

        self.mode = Mode.IDLE
        self.running = False
        self.paused = False
        self.round_no = 1
        self.task = "未命名"

        # 计时内部量
        self._end_at = 0.0
        self._frozen_remaining = 0.0
        self._seg_start_mono = 0.0
        self._seg_started_at = ""
        self._paused_total = 0.0
        self._paused_at_mono = 0.0

    # ---- 只读属性 ----
    @property
    def remaining(self) -> int:
        """剩余秒数（ceil，供 UI 显示）。"""
        if not self.running:
            return 0
        if self.paused:
            return math.ceil(self._frozen_remaining)
        return max(0, math.ceil(self._end_at - time.monotonic()))

    @property
    def duration_sec(self) -> int:
        """当前段的配置总时长（秒）。"""
        return self._duration_for(self.mode)

    # ---- 控制 ----
    def start(self, task: str) -> None:
        """开始一段专注（默认入口，从 IDLE）。"""
        self.begin(Mode.FOCUS, task)

    def begin(self, mode: Mode, task: str | None = None) -> None:
        """从 IDLE 开始指定模式的一段。自动接续走此入口。"""
        if self.running:
            return
        self.mode = mode
        if mode == Mode.FOCUS and task is not None:
            self.task = task.strip() or "未命名"
        self._start_segment()

    def pause(self) -> None:
        if not self.running or self.paused:
            return
        self.paused = True
        self._frozen_remaining = max(0.0, self._end_at - time.monotonic())
        self._paused_at_mono = time.monotonic()

    def resume(self) -> None:
        if not self.running or not self.paused:
            return
        self.paused = False
        self._paused_total += time.monotonic() - self._paused_at_mono
        self._end_at = time.monotonic() + self._frozen_remaining

    def stop(self) -> None:
        """结算当前段并回 IDLE（专注段时长不足阈值则不写记录）。"""
        if not self.running:
            return
        self._finish_segment("stop")

    def skip(self) -> None:
        """结束当前休息，进下一轮专注。仅休息段有效。"""
        if not self.running:
            return
        if self.mode in (Mode.SHORT_BREAK, Mode.LONG_BREAK):
            self._finish_segment("skip")

    def reset(self) -> None:
        """丢弃当前段，不写记录，回 IDLE。"""
        if not self.running and self.mode == Mode.IDLE:
            return
        self._teardown()
        self.round_no = 1
        self._on_segment_end(None, Mode.IDLE)

    def tick(self) -> None:
        """由 UI 每 200ms 调用一次。"""
        if not self.running or self.paused:
            return
        if time.monotonic() >= self._end_at:
            self._finish_segment("natural")

    # ---- 内部 ----
    def _start_segment(self) -> None:
        self.running = True
        self.paused = False
        self._seg_start_mono = time.monotonic()
        self._seg_started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._paused_total = 0.0
        duration = self._duration_for(self.mode)
        self._end_at = time.monotonic() + duration
        self._frozen_remaining = float(duration)

    def _duration_for(self, mode: Mode) -> int:
        s = self._settings
        if mode == Mode.FOCUS:
            return max(1, int(s.get("focus_min", 25))) * 60
        if mode == Mode.SHORT_BREAK:
            return max(1, int(s.get("short_break_min", 5))) * 60
        if mode == Mode.LONG_BREAK:
            return max(1, int(s.get("long_break_min", 15))) * 60
        return 0

    def _elapsed_sec(self) -> int:
        elapsed = time.monotonic() - self._seg_start_mono - self._paused_total
        return max(0, int(round(elapsed)))

    def _build_record(self, prev_mode: Mode, duration: int, completed: int) -> SegmentRecord | None:
        # 专注段低于阈值不入库；休息段总是入库
        if prev_mode == Mode.FOCUS and duration < MIN_RECORD_SEC:
            return None
        return SegmentRecord(
            task=self.task,
            kind=prev_mode.value,
            started_at=self._seg_started_at,
            ended_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            duration_sec=duration,
            completed=completed,
        )

    def _advance_round(self, prev_mode: Mode, reason: str) -> Mode:
        every = max(1, int(self._settings.get("long_break_every", 4)))
        auto = bool(self._settings.get("auto_continue", True))

        if reason == "stop":
            self.round_no = 1
            return Mode.IDLE

        if reason == "natural" and prev_mode == Mode.FOCUS:
            nxt = Mode.LONG_BREAK if self.round_no % every == 0 else Mode.SHORT_BREAK
        else:
            # 休息自然走完 / skip 休息
            self.round_no += 1
            nxt = Mode.FOCUS

        if not auto:
            return Mode.IDLE
        return nxt

    def _finish_segment(self, reason: str) -> None:
        prev_mode = self.mode
        duration = self._elapsed_sec()
        completed = 1 if reason == "natural" else 0
        record = self._build_record(prev_mode, duration, completed)
        next_mode = self._advance_round(prev_mode, reason)

        self._teardown()

        self._on_segment_end(record, next_mode)

    def _teardown(self) -> None:
        self.running = False
        self.paused = False
        self.mode = Mode.IDLE
        self._end_at = 0.0
        self._frozen_remaining = 0.0
