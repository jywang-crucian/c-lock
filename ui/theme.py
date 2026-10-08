"""配色、字体、尺寸与 QSS 主题（PySide6）。"""
from __future__ import annotations

from PySide6.QtGui import QFont

# ---- 模式配色：(球面/强调色) ----
MODE_COLORS: dict[str, str] = {
    "focus": "#6E8C3A",        # 黄绿（进行中）
    "short_break": "#2E5E46",  # 深绿（放松）
    "long_break": "#1F4D5E",   # 深青（长休息）
    "idle": "#24332B",         # 深灰绿（中性）
}

MODE_LABEL: dict[str, str] = {
    "focus": "专注",
    "short_break": "短休",
    "long_break": "长休",
    "idle": "空闲",
}

# ---- 面板 / 通用 ----
PANEL_BG = "#0C1F1A"        # 深绿近黑
PANEL_CARD = "#16281D"      # 次级卡片
PANEL_BORDER = "#2A4636"    # 描边
ACCENT = "#8FA84A"          # 黄绿强调（按钮/进度）
ACCENT_HOVER = "#A3B45C"
ACCENT_PRESS = "#7C9640"
ACCENT_DARK = "#6E8C3A"
TEXT_MAIN = "#E6EBDD"       # 浅绿白
TEXT_SUB = "#8CA08A"        # 灰绿
BTN_BG = "#16281D"
BTN_FG = "#E6EBDD"
BTN_ACTIVE = "#223B2C"
ON_ACCENT_FG = "#14210F"    # 黄绿底上的深色文字

STATS_BG = "#0C1F1A"
STATS_FG = "#E6EBDD"
BAR_COLOR = "#8FA84A"
AXIS_COLOR = "#3A5544"

# ---- 尺寸（逻辑像素，Qt 自动 HiDPI 缩放）----
BALL_SIZE = 92
PANEL_W = 320
PANEL_H = 350
RADIUS = 20             # 面板圆角半径
BALL_PEEK = 16          # 贴边时露出的宽度

# ---- 字体（point size，Qt 按 DPI 自动缩放，保证高分屏清晰）----


def qfont(family: str, size: int, bold: bool = False) -> QFont:
    f = QFont(family)
    f.setPointSize(size)
    if bold:
        f.setBold(True)
    return f


FONT_UI = qfont("Microsoft YaHei", 9)
FONT_SMALL = qfont("Microsoft YaHei", 8)
FONT_BOLD = qfont("Microsoft YaHei", 10, True)
FONT_BIG = qfont("Microsoft YaHei", 12, True)
FONT_TIMER = qfont("Consolas", 24, True)
FONT_BALL = qfont("Consolas", 16, True)

# ---- 全局 QSS ----
GLOBAL_QSS = f"""
* {{ font-family: "Microsoft YaHei"; }}

QPushButton {{
    background-color: {BTN_BG};
    color: {BTN_FG};
    border: 1px solid {PANEL_BORDER};
    border-radius: 8px;
    padding: 6px 14px;
}}
QPushButton:hover {{ background-color: {BTN_ACTIVE}; }}
QPushButton:pressed {{ background-color: #1A3123; }}
QPushButton:disabled {{ color: #5A6B5E; background-color: #122019; border-color: #1E2E25; }}

QPushButton#StartButton {{
    background-color: {ACCENT};
    color: {ON_ACCENT_FG};
    border: none;
    border-radius: 40px;
    font-weight: bold;
}}
QPushButton#StartButton:hover {{ background-color: {ACCENT_HOVER}; }}
QPushButton#StartButton:pressed {{ background-color: {ACCENT_PRESS}; }}

QPushButton#CloseButton {{
    background-color: transparent;
    color: {TEXT_SUB};
    border: none;
    border-radius: 12px;
    font-size: 14pt;
    padding: 0px;
}}
QPushButton#CloseButton:hover {{ background-color: {BTN_ACTIVE}; color: {TEXT_MAIN}; }}

QComboBox, QSpinBox, QLineEdit, QPlainTextEdit {{
    background-color: {PANEL_CARD};
    color: {TEXT_MAIN};
    border: 1px solid {PANEL_BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {PANEL_CARD};
    color: {TEXT_MAIN};
    selection-background-color: {ACCENT};
    border: 1px solid {PANEL_BORDER};
}}
QSpinBox::up-button, QSpinBox::down-button {{ border: none; background: transparent; width: 16px; }}

QCheckBox, QRadioButton {{
    color: {TEXT_MAIN};
    background: transparent;
    spacing: 6px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {AXIS_COLOR};
    border-radius: 3px;
    background: {PANEL_BG};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {ACCENT}; border-color: {ACCENT};
}}
QRadioButton::indicator {{ border-radius: 7px; }}

QDialog, QWidget#AppWindow {{ background-color: {STATS_BG}; }}

QMenu {{
    background-color: {PANEL_CARD};
    color: {TEXT_MAIN};
    border: 1px solid {PANEL_BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{ background-color: {ACCENT}; color: {ON_ACCENT_FG}; }}
"""
