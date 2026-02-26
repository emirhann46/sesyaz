import sys

from PySide6.QtWidgets import QApplication

from sesyaz.config.config_manager import ConfigManager
from sesyaz.config.keyring_manager import KeyringManager
from sesyaz.main_window import VoiceBarWindow
from sesyaz.ui.setup_dialog import SetupDialog


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    config = ConfigManager()

    # First run or missing API key → show setup dialog
    if not KeyringManager.has_key() or config.get("first_run", True):
        dialog = SetupDialog()
        if dialog.exec() != SetupDialog.DialogCode.Accepted:
            return 0
        config.set("first_run", False)

    if not KeyringManager.has_key():
        return 1

    app.setQuitOnLastWindowClosed(False)

    window = VoiceBarWindow(config)
    window.show()
    window.start_recording()

    return app.exec()
