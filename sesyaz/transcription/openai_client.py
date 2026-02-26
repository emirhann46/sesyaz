import openai
from PySide6.QtCore import QThread, Signal

from sesyaz.audio.audio_utils import delete_temp_file


class TranscriptionWorker(QThread):
    done = Signal(str)
    error = Signal(str)

    def __init__(self, audio_path: str, model: str, api_key: str,
                 language: str = "", parent=None):
        super().__init__(parent)
        self._audio_path = audio_path
        self._model = model
        self._api_key = api_key
        self._language = language

    def run(self):
        try:
            client = openai.OpenAI(api_key=self._api_key)
            kwargs: dict = dict(model=self._model, file=None, response_format="text")
            if self._language:
                kwargs["language"] = self._language
            with open(self._audio_path, "rb") as f:
                kwargs["file"] = f
                response = client.audio.transcriptions.create(**kwargs)
            text = response.strip() if isinstance(response, str) else response.text.strip()
            if not text:
                self.error.emit("No speech detected")
            else:
                self.done.emit(text)
        except openai.AuthenticationError:
            self.error.emit("Invalid API key")
        except openai.APIConnectionError:
            self.error.emit("Connection error")
        except openai.RateLimitError:
            self.error.emit("Rate limit exceeded")
        except Exception as e:
            self.error.emit(f"Error: {e}")
        finally:
            delete_temp_file(self._audio_path)
