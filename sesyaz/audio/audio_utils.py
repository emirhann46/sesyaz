import os
import tempfile

import numpy as np
import soundfile as sf

SILENCE_THRESHOLD = 200.0  # int16 RMS units


def save_temp_wav(audio_data: np.ndarray, sample_rate: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="sesyaz_")
    os.close(fd)
    sf.write(path, audio_data, sample_rate, subtype="PCM_16")
    return path


def delete_temp_file(path: str):
    try:
        os.unlink(path)
    except OSError:
        pass


def compute_rms(audio_data: np.ndarray) -> float:
    return float(np.sqrt(np.mean(audio_data.astype(np.float32) ** 2)))
