"""Non-blocking standard-library notification sound service."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Optional


class SoundNotifier:
    """Plays a gentle, non-blocking completion chime using standard library only."""

    def __init__(self, bell_fallback: Optional[Callable[[], None]] = None) -> None:
        self._bell_fallback = bell_fallback

    def set_bell_fallback(self, bell_fallback: Optional[Callable[[], None]]) -> None:
        self._bell_fallback = bell_fallback

    def play_completion_chime(self) -> None:
        """Trigger a soft completion chime without blocking the Tkinter UI thread."""
        thread = threading.Thread(target=self._play_worker, daemon=True)
        thread.start()

    def _play_worker(self) -> None:
        try:
            if sys.platform == "darwin":
                afplay = shutil.which("afplay")
                for candidate in (
                    "/System/Library/Sounds/Glass.aiff",
                    "/System/Library/Sounds/Tink.aiff",
                    "/System/Library/Sounds/Pop.aiff",
                ):
                    if afplay and Path(candidate).exists():
                        subprocess.run(
                            [afplay, candidate],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False,
                        )
                        return
            elif sys.platform.startswith("win"):
                import winsound  # Standard library on Windows

                winsound.Beep(660, 140)
                winsound.Beep(880, 200)
                return
            else:
                for player, sound_path in (
                    ("paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"),
                    ("paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"),
                    ("aplay", "/usr/share/sounds/alsa/Front_Center.wav"),
                ):
                    exe = shutil.which(player)
                    if exe and Path(sound_path).exists():
                        subprocess.run(
                            [exe, sound_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False,
                        )
                        return
        except Exception:
            pass

        if self._bell_fallback is not None:
            try:
                self._bell_fallback()
            except Exception:
                pass
