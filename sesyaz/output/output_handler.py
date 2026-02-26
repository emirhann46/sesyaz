import subprocess

from PySide6.QtWidgets import QApplication


class OutputHandler:
    @staticmethod
    def copy_to_clipboard(text: str):
        QApplication.clipboard().setText(text)

    @staticmethod
    def xdotool_paste():
        try:
            subprocess.Popen(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass  # xdotool not installed, skip paste

    @staticmethod
    def handle(text: str, mode: str):
        if mode in ("clipboard", "clipboard+paste"):
            OutputHandler.copy_to_clipboard(text)
        if mode in ("paste", "clipboard+paste"):
            OutputHandler.xdotool_paste()
