from enum import Enum

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMenu, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from sesyaz.audio.audio_utils import (
    SILENCE_THRESHOLD,
    compute_rms,
    save_temp_wav,
)
from sesyaz.audio.recorder import AudioRecorder
from sesyaz.config.config_manager import ConfigManager
from sesyaz.config.keyring_manager import KeyringManager
from sesyaz.output.output_handler import OutputHandler
from sesyaz.transcription.openai_client import TranscriptionWorker
from sesyaz.waveform_widget import WaveformWidget


class State(Enum):
    LISTENING   = "listening"
    PAUSED      = "paused"
    PROCESSING  = "processing"
    RESULT      = "result"
    ERROR       = "error"


MODELS = [
    ("gpt-4o-mini-transcribe", "mini  ⚡"),
    ("gpt-4o-transcribe",      "gpt-4o  ✦"),
]

BAR_H  = 92   # compact bar height
TALL_H = 200  # expanded height for RESULT state


class VoiceBarWindow(QWidget):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config
        self._worker: TranscriptionWorker | None = None
        self._recorder = AudioRecorder(self)
        self._elapsed = 0
        self._model_idx = self._load_model_idx()
        self._drag_pos = None

        self._setup_window()
        self._build_ui()
        self._connect_signals()

        # Recording duration timer
        self._rec_timer = QTimer(self)
        self._rec_timer.setInterval(1000)
        self._rec_timer.timeout.connect(self._tick)

        # Fade-in
        self.setWindowOpacity(0.0)
        self._fade_step = 0
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(16)
        self._fade_timer.timeout.connect(self._fade_in)

    def _load_model_idx(self) -> int:
        current = self._config.get("model", MODELS[0][0])
        for i, (model_id, _) in enumerate(MODELS):
            if model_id == current:
                return i
        return 0

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(530, BAR_H)
        self._reposition()

    def _reposition(self):
        screen = QApplication.primaryScreen().geometry()
        saved_x = self._config.get("window_x")
        saved_y = self._config.get("window_y")
        x = saved_x if saved_x is not None else (screen.width() - self.width()) // 2
        y = saved_y if saved_y is not None else int(screen.height() * 0.82)
        # Clamp so window stays on screen
        x = max(0, min(x, screen.width() - self.width()))
        y = max(0, min(y, screen.height() - self.height()))
        self.move(x, y)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Background — slightly navy-dark, semi-transparent
        p.setBrush(QColor(16, 18, 22, 228))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 22, 22)
        # Subtle 1px border for depth
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 21, 21)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self._config.set("window_x", self.x())
            self._config.set("window_y", self.y())

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2c2c2e; color: #ebebf5; border: 1px solid #48484a;"
            " border-radius: 8px; padding: 4px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 4px; }"
            "QMenu::item:selected { background: #3a3a3c; }"
        )
        settings_action = menu.addAction("⚙  Ayarlar")
        settings_action.triggered.connect(self._open_settings)
        menu.exec(event.globalPos())

    # ── UI layout ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 8, 14, 6)
        self._root.setSpacing(4)

        # ── Top row ───────────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(10)

        self._mic_dot = QLabel("●")
        self._mic_dot.setStyleSheet("color: #ff3b30; font-size: 12px;")
        self._mic_dot.setFixedWidth(14)
        top.addWidget(self._mic_dot)

        self._waveform = WaveformWidget(self)
        top.addWidget(self._waveform, stretch=1)

        self._status = QLabel()
        self._status.setStyleSheet("color: #ebebf5; font-size: 13px;")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.hide()
        top.addWidget(self._status, stretch=1)

        self._btn_pause = QPushButton("⏸")
        self._btn_pause.setFixedSize(32, 32)
        self._btn_pause.setStyleSheet(
            "QPushButton { background: #636366; color: white; border: none;"
            " border-radius: 16px; font-size: 13px; }"
            "QPushButton:hover { background: #7c7c80; }"
        )
        top.addWidget(self._btn_pause)

        self._btn_confirm = QPushButton("✔")
        self._btn_confirm.setFixedSize(32, 32)
        self._btn_confirm.setStyleSheet(
            "QPushButton { background: #30d158; color: white; border: none;"
            " border-radius: 16px; font-size: 15px; font-weight: bold; }"
            "QPushButton:hover { background: #34e45f; }"
            "QPushButton:pressed { background: #27a348; }"
        )
        top.addWidget(self._btn_confirm)

        self._btn_cancel = QPushButton("✕")
        self._btn_cancel.setFixedSize(32, 32)
        self._btn_cancel.setStyleSheet(
            "QPushButton { background: #3a3a3c; color: #ebebf5; border: none;"
            " border-radius: 16px; font-size: 12px; }"
            "QPushButton:hover { background: #505052; }"
        )
        top.addWidget(self._btn_cancel)

        self._root.addLayout(top)

        # ── Result text area (hidden until RESULT state) ───────────────────────
        self._result_edit = QTextEdit()
        self._result_edit.setStyleSheet(
            "QTextEdit { background: #1c1c1e; color: #ebebf5; border: 1px solid #3a3a3c;"
            " border-radius: 10px; font-size: 13px; padding: 8px; }"
        )
        self._result_edit.setFixedHeight(80)
        self._result_edit.hide()
        self._root.addWidget(self._result_edit)

        # ── Bottom row: model selector + timer ────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(0)

        self._btn_model = QPushButton(MODELS[self._model_idx][1])
        self._btn_model.setFixedHeight(18)
        self._btn_model.setStyleSheet(
            "QPushButton { background: transparent; color: #8e8e93;"
            " border: none; font-size: 11px; padding: 0 6px; }"
            "QPushButton:hover { color: #ebebf5; }"
        )
        bottom.addWidget(self._btn_model, alignment=Qt.AlignmentFlag.AlignLeft)

        bottom.addStretch()

        self._lbl_timer = QLabel("0:00")
        self._lbl_timer.setStyleSheet("color: #636366; font-size: 11px;")
        bottom.addWidget(self._lbl_timer, alignment=Qt.AlignmentFlag.AlignRight)

        self._btn_settings = QPushButton("⚙")
        self._btn_settings.setFixedSize(18, 18)
        self._btn_settings.setStyleSheet(
            "QPushButton { background: transparent; color: #636366;"
            " border: none; font-size: 12px; padding: 0; }"
            "QPushButton:hover { color: #ebebf5; }"
        )
        bottom.addWidget(self._btn_settings, alignment=Qt.AlignmentFlag.AlignRight)

        self._root.addLayout(bottom)

    def _connect_signals(self):
        self._btn_model.clicked.connect(self._on_model_cycle)
        self._btn_settings.clicked.connect(self._open_settings)
        self._btn_pause.clicked.connect(self._on_pause_toggle)
        self._btn_confirm.clicked.connect(self._on_confirm)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._recorder.audio_level.connect(self._waveform.push_level)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self._on_cancel)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(self._on_pause_toggle)

    # ── State control ─────────────────────────────────────────────────────────

    def _set_state(self, state: State):
        is_active = state in (State.LISTENING, State.PAUSED)
        is_result = state == State.RESULT

        self._waveform.setVisible(is_active)
        self._mic_dot.setVisible(is_active)
        self._btn_pause.setVisible(is_active)
        self._status.setVisible(state in (State.PROCESSING, State.ERROR))
        self._result_edit.setVisible(is_result)
        self._lbl_timer.setVisible(not is_result)

        # Expand/collapse window height (keep current x/y position)
        new_h = TALL_H if is_result else BAR_H
        if self.height() != new_h:
            cur_x, cur_y = self.x(), self.y()
            self.setFixedSize(530, new_h)
            screen = QApplication.primaryScreen().geometry()
            self.move(cur_x, max(0, min(cur_y, screen.height() - new_h)))

        if state == State.PAUSED:
            self._mic_dot.setStyleSheet("color: #ff9f0a; font-size: 12px;")
        else:
            self._mic_dot.setStyleSheet("color: #ff3b30; font-size: 12px;")

    # ── Fade-in & timer ───────────────────────────────────────────────────────

    def _fade_in(self):
        self._fade_step += 1
        opacity = min(self._fade_step / 12.0, 1.0)
        self.setWindowOpacity(opacity)
        if opacity >= 1.0:
            self._fade_timer.stop()

    def _tick(self):
        if not self._recorder.is_paused():
            self._elapsed += 1
        mins, secs = divmod(self._elapsed, 60)
        self._lbl_timer.setText(f"{mins}:{secs:02d}")

    # ── Model cycling ─────────────────────────────────────────────────────────

    @Slot()
    def _on_model_cycle(self):
        self._model_idx = (self._model_idx + 1) % len(MODELS)
        model_id, label = MODELS[self._model_idx]
        self._btn_model.setText(label)
        self._config.set("model", model_id)

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        from sesyaz.ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._config, self)
        dlg.exec()
        # Reload model index in case it changed
        self._model_idx = self._load_model_idx()
        self._btn_model.setText(MODELS[self._model_idx][1])

    # ── Actions ───────────────────────────────────────────────────────────────

    def start_recording(self):
        self._set_state(State.LISTENING)
        self._fade_timer.start()
        err = self._recorder.start()
        if err:
            self._show_error(err)
        else:
            self._rec_timer.start()

    @Slot()
    def _on_pause_toggle(self):
        if self._recorder.is_paused():
            self._recorder.resume()
            self._btn_pause.setText("⏸")
            self._set_state(State.LISTENING)
        else:
            self._recorder.pause()
            self._btn_pause.setText("▶")
            self._set_state(State.PAUSED)

    @Slot()
    def _on_confirm(self):
        # In RESULT state, ✔ means "copy and close"
        if self._result_edit.isVisible():
            text = self._result_edit.toPlainText().strip()
            if text:
                OutputHandler.copy_to_clipboard(text)
                mode = self._config.get("output_mode", "clipboard")
                self.hide()
                if mode in ("paste", "clipboard+paste"):
                    QTimer.singleShot(150, OutputHandler.xdotool_paste)
                    QTimer.singleShot(300, QApplication.instance().quit)
                else:
                    QTimer.singleShot(50, QApplication.instance().quit)
            else:
                QTimer.singleShot(50, QApplication.instance().quit)
            return

        self._rec_timer.stop()
        audio = self._recorder.stop()

        if audio is None or compute_rms(audio) < SILENCE_THRESHOLD:
            self._show_error("Ses algılanamadı")
            return

        self._set_state(State.PROCESSING)
        self._status.setText("Transkribe ediliyor…")

        path = save_temp_wav(audio, AudioRecorder.SAMPLE_RATE)
        api_key = KeyringManager.get_key()
        model = self._config.get("model", "gpt-4o-mini-transcribe")
        language = self._config.get("language", "")

        self._worker = TranscriptionWorker(path, model, api_key, language, parent=self)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    @Slot()
    def _on_cancel(self):
        self._rec_timer.stop()
        self._recorder.stop()
        QApplication.instance().quit()

    @Slot(str)
    def _on_done(self, text: str):
        stay_open = self._config.get("stay_open", False)
        mode = self._config.get("output_mode", "clipboard")

        if stay_open:
            # Show editable result — user reviews/edits, then clicks ✔
            self._set_state(State.RESULT)
            self._result_edit.setPlainText(text)
            self._result_edit.setFocus()
            self._result_edit.selectAll()
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
            self.activateWindow()
        else:
            # Immediate copy + close
            OutputHandler.copy_to_clipboard(text)
            self.hide()
            if mode in ("paste", "clipboard+paste"):
                QTimer.singleShot(150, OutputHandler.xdotool_paste)
            QTimer.singleShot(300, QApplication.instance().quit)

    @Slot(str)
    def _on_error(self, msg: str):
        self._show_error(msg)

    def _show_error(self, msg: str):
        self._set_state(State.ERROR)
        self._status.setStyleSheet("color: #ff453a; font-size: 13px;")
        self._status.setText(msg)
        QTimer.singleShot(3000, QApplication.instance().quit)
