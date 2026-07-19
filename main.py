import sys

from PyQt6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

from focus_tracker.config import cfg
from focus_tracker.i18n import set_language


def main():
    set_language(cfg.language.value)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    setTheme(Theme.DARK if cfg.theme.value == "Dark" else Theme.LIGHT)

    from focus_tracker.main_window import MainWindow

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
