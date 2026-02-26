import threading

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal


class AudioRecorder(QObject):
    audio_level = Signal(float)  # 0.0-1.0 RMS, emitted each audio block

    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = "int16"
    BLOCKSIZE = 1024

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._paused = False

    def start(self) -> str | None:
        """Start recording. Returns error string or None on success."""
        self._frames.clear()
        try:
            self._stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                blocksize=self.BLOCKSIZE,
                callback=self._callback,
            )
            self._stream.start()
            return None
        except sd.PortAudioError as e:
            return f"Microphone not found: {e}"

    def pause(self):
        self._paused = True
        self.audio_level.emit(0.0)

    def resume(self):
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        # AUDIO THREAD — only Signal.emit() is safe here
        if self._paused:
            return
        with self._lock:
            self._frames.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
        self.audio_level.emit(min(rms * 10.0, 1.0))

    def stop(self) -> np.ndarray | None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._frames:
                return None
            return np.concatenate(self._frames, axis=0)

    def is_recording(self) -> bool:
        return self._stream is not None and self._stream.active
