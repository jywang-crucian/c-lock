"""配置读写与路径解析。

本模块只依赖标准库，供 core / storage / ui 三层共用。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 专注段实际时长低于该秒数不入库（防误点污染统计）
MIN_RECORD_SEC = 60

# 默认配置，缺失字段一律回落至此
DEFAULTS: dict = {
    "focus_min": 25,
    "short_break_min": 5,
    "long_break_min": 15,
    "long_break_every": 4,
    "auto_continue": True,
    "always_on_top": True,
    "sound_on": True,
    "minimize_to_tray": True,
    "task_history": ["高数", "写代码"],
}


def app_root() -> Path:
    """应用根目录。打包后指向 exe 所在目录，源码运行指向项目根。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


DATA_DIR = app_root() / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "c-lock.db"
SETTINGS_PATH = DATA_DIR / "settings.json"


def _coerce(key: str, value) -> object:
    """按默认值类型校验单个字段，类型不符则回落默认。"""
    default = DEFAULTS[key]
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if isinstance(default, int):
        return value if isinstance(value, int) and not isinstance(value, bool) else default
    if isinstance(default, list):
        return value if isinstance(value, list) and all(isinstance(x, str) for x in value) else default
    return default


def load_settings() -> dict:
    """读取配置；缺失字段回落默认，文件损坏则备份重建。"""
    if not SETTINGS_PATH.exists():
        return dict(DEFAULTS)
    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("settings 根节点不是对象")
    except (json.JSONDecodeError, ValueError, OSError):
        _backup_corrupt()
        return dict(DEFAULTS)

    settings = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in raw:
            settings[key] = _coerce(key, raw[key])
    return settings


def save_settings(settings: dict) -> None:
    """写回配置，UTF-8 + 缩进，保证中文可读。"""
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _backup_corrupt() -> None:
    """把损坏的 settings.json 备份为 settings.json.bak。"""
    try:
        SETTINGS_PATH.replace(SETTINGS_PATH.with_suffix(".json.bak"))
    except OSError:
        pass
