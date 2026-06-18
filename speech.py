#
#  speech.py
#  AskWindows
#
#  Reads Ask Windows' answers aloud using Windows SAPI via pyttsx3.
#  Mirrors Speech.swift — same purpose, same markdown stripping,
#  same slightly-slower rate for clarity.
#
#  Runs TTS in a background thread so the UI never blocks.
#

import re
import threading
import pyttsx3


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so it isn't read aloud literally."""
    t = text
    t = t.replace("**", "")
    t = t.replace("*", "")
    t = re.sub(r"(?m)^\s*[-•]\s+", "", t)
    t = re.sub(r"(?m)^---+\s*$", "", t)
    t = t.replace("`", "")
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _pick_best_voice(engine) -> str | None:
    """
    Return the id of the best available English voice.
    Prefers voices whose name contains 'Zira', 'David', or 'Mark'
    (the higher-quality Microsoft voices); falls back to any English voice.
    """
    voices = engine.getProperty("voices")
    preferred_names = ["zira", "david", "mark", "aria", "guy", "jenny", "neural"]

    english_voices = [v for v in voices if "en" in v.languages[0].lower()
                      if v.languages] if voices else []
    if not english_voices:
        english_voices = [v for v in voices
                          if "english" in v.name.lower() or "_en" in v.id.lower()]

    for pref in preferred_names:
        for v in english_voices:
            if pref in v.name.lower():
                return v.id

    if english_voices:
        return english_voices[0].id

    return None  # use system default


class SpeechPlayer:
    """
    Thread-safe TTS player. on_done callback fires on the speaking thread
    when an utterance finishes naturally — used by conversation mode to
    know when to re-arm the microphone.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self.is_speaking = False
        self._on_done_callback = None

        # Build engine once to discover voices; each speak() gets a fresh
        # engine instance to avoid pyttsx3's reinit quirks on Windows.
        try:
            probe = pyttsx3.init()
            self._best_voice_id = _pick_best_voice(probe)
            probe.stop()
            del probe
        except Exception:
            self._best_voice_id = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def speak(self, text: str, on_done=None):
        """
        Read text aloud in a background thread.
        Stops any current speech first.
        on_done() is called when speech finishes naturally (not when stopped).
        """
        self.stop()
        self._on_done_callback = on_done
        clean = _strip_markdown(text)
        if not clean:
            return
        self._stop_event.clear()
        self.is_speaking = True
        self._thread = threading.Thread(target=self._speak_worker,
                                        args=(clean,), daemon=True)
        self._thread.start()

    def stop(self):
        """Stop speech immediately."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2)
        self.is_speaking = False
        self._on_done_callback = None

    @property
    def current_voice_description(self) -> str:
        if self._best_voice_id:
            return self._best_voice_id.split("\\")[-1]
        return "System default"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _speak_worker(self, text: str):
        try:
            engine = pyttsx3.init()
            if self._best_voice_id:
                engine.setProperty("voice", self._best_voice_id)
            rate = engine.getProperty("rate")
            engine.setProperty("rate", int(rate * 0.95))  # slightly slower

            # Feed text in sentences so we can honour stop requests
            # between sentences without cutting mid-word.
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                if self._stop_event.is_set():
                    break
                engine.say(sentence)
                engine.runAndWait()

            engine.stop()
        except Exception:
            pass
        finally:
            self.is_speaking = False
            if not self._stop_event.is_set() and self._on_done_callback:
                self._on_done_callback()
