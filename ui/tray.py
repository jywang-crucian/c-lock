"""pystray 托盘封装。子线程回调通过 Qt 信号回投主线程。"""
from __future__ import annotations

import pystray
from PIL import Image, ImageDraw, ImageFont


class Tray:
    def __init__(self, app, icon_path: str):
        self.app = app
        self._base_image = Image.open(icon_path)
        self._last_minute = None
        self._font = self._load_font(28)
        self._font_small = self._load_font(20)

        self.icon = pystray.Icon(
            "c-lock",
            self._base_image,
            "c-lock 专注时钟",
            menu=self._build_menu(),
        )

    @staticmethod
    def _load_font(size: int):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)
        except Exception:
            return ImageFont.load_default(size=size)

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("显示悬浮球", self._on_show, default=True),
            pystray.MenuItem("暂停 / 继续", self._on_pause_resume),
            pystray.MenuItem("停止", self._on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit),
        )

    def run(self) -> None:
        self.icon.run()

    def stop(self) -> None:
        try:
            self.icon.stop()
        except Exception:
            pass

    # ---- 托盘菜单回调（子线程）→ 通过信号回投主线程 ----
    def _on_show(self, icon, item):
        self.app.sig_show.emit()

    def _on_pause_resume(self, icon, item):
        self.app.sig_pause_resume.emit()

    def _on_stop(self, icon, item):
        self.app.sig_stop.emit()

    def _on_quit(self, icon, item):
        self.app.sig_quit.emit()

    # ---- 主线程更新 ----
    def update_tooltip(self, text: str) -> None:
        try:
            self.icon.title = text
        except Exception:
            pass

    def update_icon(self, minutes: int, color: str) -> None:
        if minutes == self._last_minute:
            return
        self._last_minute = minutes
        text = str(minutes)
        font = self._font if len(text) <= 2 else self._font_small

        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([2, 2, 62, 62], fill=color)
        d.text((32, 33), text, fill="white", font=font, anchor="mm")
        try:
            self.icon.icon = img
        except Exception:
            pass

    def reset_icon(self) -> None:
        self._last_minute = None
        try:
            self.icon.icon = self._base_image
        except Exception:
            pass
