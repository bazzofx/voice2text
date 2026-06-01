import sys
from PyQt6.QtWidgets import QApplication
from ui.app import Voice2TextApp


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Voice2Text")

    v2t = Voice2TextApp(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
