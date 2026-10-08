"""悬浮球：透明圆球，径向渐变玻璃质感，显示时间，可拖动、贴边回弹、悬停展开。"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QCursor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from ui import theme


class FloatingBall(QWidget):
    def __init__(self, app, settings: dict):
        super().__init__(None)
        self.app = app
        self.settings = settings
        self.size = theme.BALL_SIZE

        self._mode_key = "idle"
        self._seconds = 0
        self._docked = False
        self._docked_side = None
        self._hidden = False
        self._pinned = False
        self._dragging = False
        self._press_pos = QPoint()
        self._win_pos = QPoint()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.size, self.size)

        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.right() - self.size - 40, scr.center().y() - self.size // 2)

        self._slide = QPropertyAnimation(self, b"pos", self)

        self._poll = QTimer(self)
        self._poll.timeout.connect(self._on_poll)
        self._poll.start(150)

        self.show()

    # ---------- 显示 ----------
    def set_display(self, mode_key: str, seconds: int) -> None:
        if (mode_key, seconds) == (self._mode_key, self._seconds):
            return
        self._mode_key = mode_key
        self._seconds = seconds
        self.update()

    def set_pinned(self, pinned: bool) -> None:
        self._pinned = pinned
        if pinned and self._hidden:
            self._show_full()
            self._hidden = False

    def show_full(self) -> None:
        if self._hidden:
            self._show_full()
            self._hidden = False

    @staticmethod
    def _fmt(sec: int) -> str:
        m, s = divmod(max(0, int(sec)), 60)
        return f"{m:02d}:{s:02d}"

    # ---------- 绘制 ----------
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.size
        rect = QRectF(1, 1, s - 2, s - 2)
        base = QColor(theme.MODE_COLORS[self._mode_key])

        # 玻璃主体：径向渐变，左上亮右下暗
        grad = QRadialGradient(rect.center() - QPointF(s * 0.18, s * 0.18), s * 0.72)
        light = base.lighter(150)
        light.setAlpha(235)
        dark = base.darker(120)
        dark.setAlpha(220)
        grad.setColorAt(0.0, light)
        grad.setColorAt(0.55, QColor(base.red(), base.green(), base.blue(), 215))
        grad.setColorAt(1.0, dark)
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(theme.PANEL_BORDER), 2))
        p.drawEllipse(rect)

        # 顶部高光
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 75))
        p.drawEllipse(QRectF(s * 0.24, s * 0.14, s * 0.46, s * 0.26))

        # 时间文字（带阴影）
        p.setFont(theme.FONT_BALL)
        text = self._fmt(self._seconds)
        p.setPen(QColor(0, 0, 0, 170))
        p.drawText(rect.translated(0, 1), Qt.AlignmentFlag.AlignCenter, text)
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        p.end()

    # ---------- 拖动 ----------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._press_pos = e.globalPosition().toPoint()
            self._win_pos = self.pos()

    def mouseMoveEvent(self, e) -> None:
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        delta = e.globalPosition().toPoint() - self._press_pos
        if not self._dragging and (abs(delta.x()) + abs(delta.y())) > 4:
            self._dragging = True
        if self._dragging:
            self._slide.stop()
            self.move(self._win_pos + delta)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self._dragging:
            self._dock_check()
        else:
            self.app.toggle_panel()
        self._dragging = False

    # ---------- 贴边 ----------
    def _dock_check(self) -> None:
        scr = QApplication.primaryScreen().availableGeometry()
        x = self.x()
        if x <= scr.left():
            self._dock("left")
        elif x + self.size >= scr.right():
            self._dock("right")
        else:
            self._docked = False
            self._docked_side = None
            self._hidden = False

    def _dock(self, side: str) -> None:
        self._docked = True
        self._docked_side = side
        self._hidden = True
        self._slide_to(self._dock_target(), elastic=True)

    def _dock_target(self) -> QPoint:
        scr = QApplication.primaryScreen().availableGeometry()
        y = self.y()
        if self._docked_side == "right":
            return QPoint(scr.right() - theme.BALL_PEEK + 1, y)
        return QPoint(scr.left() - self.size + theme.BALL_PEEK - 1, y)

    def _show_full(self) -> None:
        scr = QApplication.primaryScreen().availableGeometry()
        y = self.y()
        tx = scr.right() - self.size + 1 if self._docked_side == "right" else scr.left()
        self._slide_to(QPoint(tx, y), elastic=True)

    def _slide_to(self, target: QPoint, elastic: bool = False) -> None:
        self._slide.stop()
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(target)
        if elastic:
            self._slide.setDuration(340)
            self._slide.setEasingCurve(QEasingCurve.Type.OutBack)
        else:
            self._slide.setDuration(220)
            self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide.start()

    # ---------- 轮询 ----------
    def _on_poll(self) -> None:
        if self._docked and not self._pinned:
            g = self.geometry().adjusted(-24, -24, 24, 24)
            hover = g.contains(QCursor.pos())
            if hover and self._hidden:
                self._show_full()
                self._hidden = False
            elif not hover and not self._hidden:
                self._slide_to(self._dock_target(), elastic=False)
                self._hidden = True

    # ---------- 右键菜单：退出 ----------
    def contextMenuEvent(self, e) -> None:
        menu = QMenu(self)
        menu.addAction("退出 c-lock", self.app.quit_app)
        menu.exec(e.globalPos())
