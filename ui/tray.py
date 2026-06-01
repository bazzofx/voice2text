from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt

_STATUSES: dict[str, tuple[str, str]] = {
    "loading":      ("#9E9E9E", "Voice2Text — Loading model..."),
    "ready":        ("#4CAF50", "Voice2Text — Ready"),
    "recording":    ("#F44336", "Voice2Text — Recording..."),
    "transcribing": ("#2196F3", "Voice2Text — Transcribing..."),
    "error":        ("#FF5722", "Voice2Text — Error"),
}


def _make_icon(hex_color: str, size: int = 64) -> QIcon:
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(hex_color))
    p.setPen(Qt.PenStyle.NoPen)
    m = size // 8
    p.drawEllipse(m, m, size - 2 * m, size - 2 * m)
    p.end()
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self._status_action = None

        menu = QMenu()
        self._status_action = menu.addAction("Loading model...")
        self._status_action.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Settings").triggered.connect(self._open_settings)
        menu.addSeparator()
        menu.addAction("Quit").triggered.connect(self.controller.quit)
        self.setContextMenu(menu)

        self.set_status("loading")

    def set_status(self, status: str) -> None:
        color, label = _STATUSES.get(status, ("#9E9E9E", "Voice2Text"))
        self.setIcon(_make_icon(color))
        self.setToolTip(label)
        if self._status_action:
            self._status_action.setText(label)

    def notify(self, title: str, message: str) -> None:
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning, 4000)

    def _open_settings(self) -> None:
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.controller)
        dlg.exec()
