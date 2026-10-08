"""入口：QApplication，高 DPI 由 Qt 自动处理。"""
from __future__ import annotations

import sys
import threading

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import core.config as config
import storage.repo as repo
from ui import theme
from ui.app import App
from ui.tray import Tray


def main() -> None:
    # 需在 QApplication 创建前设置，保证高分屏清晰
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("c-lock")
    # 悬浮球/面板都是 Tool 窗口（不算主窗口），关闭设置/统计等对话框时
    # 不应触发“最后一个窗口关闭即退出”，程序只由“退出”动作显式结束。
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(theme.GLOBAL_QSS)

    settings = config.load_settings()
    repo.init_db()

    controller = App(settings)

    icon_path = str(config.app_root() / "assets" / "icon.png")
    tray = Tray(controller, icon_path)
    controller.tray = tray
    threading.Thread(target=tray.run, daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
