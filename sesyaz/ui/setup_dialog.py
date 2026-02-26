from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QPushButton,
)
from PySide6.QtCore import Qt

from sesyaz.config.keyring_manager import KeyringManager


class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sesyaz — İlk Kurulum")
        self.setMinimumWidth(380)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("<b>Enter your OpenAI API key</b>"))
        layout.addWidget(QLabel(
            "The key is stored securely in the system keyring (KWallet).\n"
            "It is never saved to disk in plaintext."
        ))

        self._input = QLineEdit()
        self._input.setEchoMode(QLineEdit.EchoMode.Password)
        self._input.setPlaceholderText("sk-...")
        layout.addWidget(self._input)

        self._error = QLabel()
        self._error.setStyleSheet("color: #ff453a;")
        self._error.hide()
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        key = self._input.text().strip()
        if not key.startswith("sk-") or len(key) < 20:
            self._error.setText("Invalid key format — must start with sk-")
            self._error.show()
            return
        KeyringManager.set_key(key)
        self.accept()
