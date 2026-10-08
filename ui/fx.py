"""视觉效果工具（PySide6）：图片模糊背景、弹性按钮。"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from PySide6.QtCore import QEasingCurve, QVariantAnimation, Qt
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import QPushButton

from core.config import app_root


def find_bg_image():
    """在 resource 目录里找第一张可用背景图。"""
    res = app_root() / "resource"
    if res.exists():
        for p in sorted(list(res.glob("*.jpg")) + list(res.glob("*.jpeg")) + list(res.glob("*.png"))):
            return str(p)
    return None


def blurred_qpixmap(path, w: int, h: int, blur: int = 18, darken: float = 0.55,
                    corner: int = 0) -> QPixmap:
    """居中裁剪图片到 w×h，高斯模糊 + 压暗 + 可选圆角，返回 QPixmap。"""
    img = Image.open(path).convert("RGB")
    tw, th = img.size
    target = w / h
    src = tw / th
    if src > target:
        nw = int(th * target)
        box = ((tw - nw) // 2, 0, (tw - nw) // 2 + nw, th)
    else:
        nh = int(tw / target)
        box = (0, (th - nh) // 2, tw, (th - nh) // 2 + nh)
    img = img.crop(box).resize((w, h), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(blur))
    img = ImageEnhance.Brightness(img).enhance(darken)
    img = img.convert("RGBA")
    if corner > 0:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=corner, fill=255)
        img.putalpha(mask)
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, w, h, w * 4, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


class ElasticButton(QPushButton):
    """带按压缩小、松开回弹动画的按钮（不改动 clicked 信号）。

    PySide6 6.12 已移除 QGraphicsScaleEffect，改用 QVariantAnimation 同步
    缩放 fixedSize 与字号，实现整体弹性缩放。
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._base_size = None
        self._base_font = None
        self._scale = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._on_scale)

    def _capture_base(self) -> None:
        if self._base_size is None:
            self._base_size = self.size()
            self._base_font = QFont(self.font())

    def _on_scale(self, s: float) -> None:
        self._scale = s
        if self._base_size is None:
            return
        w = max(8, int(round(self._base_size.width() * s)))
        h = max(8, int(round(self._base_size.height() * s)))
        self.setFixedSize(w, h)
        f = QFont(self._base_font)
        f.setPointSizeF(self._base_font.pointSizeF() * s)
        self.setFont(f)

    def _animate_to(self, end: float, duration: int, curve) -> None:
        self._capture_base()
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(end)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(curve)
        self._anim.start()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._animate_to(0.88, 90, QEasingCurve.Type.OutQuad)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._animate_to(1.0, 280, QEasingCurve.Type.OutBack)
        super().mouseReleaseEvent(e)
