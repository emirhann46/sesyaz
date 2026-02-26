from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGroupBox,
)
from PySide6.QtCore import Qt

from sesyaz.config.config_manager import ConfigManager
from sesyaz.config.keyring_manager import KeyringManager

_KEY_PLACEHOLDER = "●" * 32  # sentinel: mevcut key değiştirilmedi


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Sesyaz — Ayarlar")
        self.setMinimumWidth(420)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # ── API Anahtarı ──────────────────────────────────────────────────────
        key_group = QGroupBox("API Anahtarı")
        key_layout = QHBoxLayout(key_group)
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if KeyringManager.has_key():
            self._key_input.setText(_KEY_PLACEHOLDER)
            self._key_input.setPlaceholderText("Değiştirmek için üzerine yazın")
        else:
            self._key_input.setPlaceholderText("sk-…  (API anahtarınızı girin)")
        key_layout.addWidget(self._key_input)
        root.addWidget(key_group)

        # ── Transkripsiyon ────────────────────────────────────────────────────
        tx_group = QGroupBox("Transkripsiyon")
        tx_form = QFormLayout(tx_group)

        self._model_combo = QComboBox()
        self._model_combo.addItem("gpt-4o-mini-transcribe  (hızlı, ekonomik)", "gpt-4o-mini-transcribe")
        self._model_combo.addItem("gpt-4o-transcribe  (en iyi kalite)", "gpt-4o-transcribe")
        current_model = config.get("model", "gpt-4o-mini-transcribe")
        self._model_combo.setCurrentIndex(
            0 if current_model == "gpt-4o-mini-transcribe" else 1
        )
        tx_form.addRow("Model:", self._model_combo)

        self._lang_input = QLineEdit()
        self._lang_input.setPlaceholderText("otomatik algıla  (veya: tr, en, de, fr…)")
        self._lang_input.setText(config.get("language", ""))
        tx_form.addRow("Dil:", self._lang_input)

        root.addWidget(tx_group)

        # ── Çıktı ─────────────────────────────────────────────────────────────
        out_group = QGroupBox("Çıktı")
        out_form = QFormLayout(out_group)

        self._output_combo = QComboBox()
        self._output_combo.addItem("Sadece panoya kopyala", "clipboard")
        self._output_combo.addItem("Otomatik yapıştır (xdotool)", "paste")
        self._output_combo.addItem("Pano + otomatik yapıştır", "clipboard+paste")
        mode_idx = {"clipboard": 0, "paste": 1, "clipboard+paste": 2}.get(
            config.get("output_mode", "clipboard"), 0
        )
        self._output_combo.setCurrentIndex(mode_idx)
        out_form.addRow("Transkripsiyon sonrası:", self._output_combo)

        self._stay_open = QCheckBox("Açık kal — kopyalamadan önce metni düzenle")
        self._stay_open.setChecked(bool(config.get("stay_open", False)))
        out_form.addRow("", self._stay_open)

        root.addWidget(out_group)

        # ── Butonlar ──────────────────────────────────────────────────────────
        self._error_lbl = QLabel()
        self._error_lbl.setStyleSheet("color: #ff453a;")
        self._error_lbl.hide()
        root.addWidget(self._error_lbl)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Kaydet")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("İptal")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _save(self):
        new_key = self._key_input.text().strip()
        if new_key and new_key != _KEY_PLACEHOLDER:
            if not new_key.startswith("sk-") or len(new_key) < 20:
                self._error_lbl.setText("Geçersiz API anahtarı — sk- ile başlamalı")
                self._error_lbl.show()
                return
            KeyringManager.set_key(new_key)

        self._config.set("model",       self._model_combo.currentData())
        self._config.set("language",    self._lang_input.text().strip())
        self._config.set("output_mode", self._output_combo.currentData())
        self._config.set("stay_open",   self._stay_open.isChecked())
        self.accept()
