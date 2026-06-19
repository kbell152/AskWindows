#
#  mic_input.py
#  AskWindows
#
#  Listens to the microphone and converts speech to text using
#  SpeechRecognition + sounddevice (ARM64 Windows compatible).
#  Mirrors MicInput.swift — same purpose, same reliability trade-off.
#
#  Runs in a background thread; fires callbacks via a thread-safe queue
#  that main.py drains on the tkinter main loop every 100ms.
#

import queue
import threading
import io
import wave
import numpy as np
import sounddevice as sd
import speech_recognition as sr


SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = 'int16'
CHUNK_SECONDS = 5       # capture in 5-second chunks
SILENCE_THRESHOLD = 500 # RMS below this = silence


class MicInput:
    """
    Async microphone listener using sounddevice (ARM64 compatible).
    All callbacks arrive on a queue; the UI loop should call
    drain_callbacks() regularly (e.g. every 100ms).
    """

    def __init__(self):
        self._recognizer = sr.Recognizer()
        self._queue: queue.Queue = queue.Queue()
        self._listen_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self.is_listening = False
        self.error_message: str | None = None

        self._on_transcript = None
        self._on_error = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_listening(self, on_transcript=None, on_error=None):
        if self.is_listening:
            return
        self._on_transcript = on_transcript
        self._on_error = on_error
        self._stop_event.clear()
        self.is_listening = True
        self.error_message = None
        self._listen_thread = threading.Thread(
            target=self._listen_worker, daemon=True)
        self._listen_thread.start()

    def stop_listening(self) -> str:
        if not self.is_listening:
            return ""
        self._stop_event.set()
        self.is_listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=3)
        return ""

    def drain_callbacks(self):
        while not self._queue.empty():
            try:
                kind, payload = self._queue.get_nowait()
                if kind == "transcript" and self._on_transcript:
                    self._on_transcript(payload)
                elif kind == "error" and self._on_error:
                    self._on_error(payload)
            except queue.Empty:
                break

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    def _listen_worker(self):
        while not self._stop_event.is_set():
            try:
                # Record a chunk of audio
                frames = int(SAMPLE_RATE * CHUNK_SECONDS)
                recording = sd.rec(
                    frames,
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype=DTYPE
                )
                sd.wait()

                if self._stop_event.is_set():
                    break

                # Skip silent chunks
                rms = np.sqrt(np.mean(recording.astype(np.float32) ** 2))
                if rms < SILENCE_THRESHOLD:
                    continue

                # Convert numpy array to WAV bytes for SpeechRecognition
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(2)  # int16 = 2 bytes
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(recording.tobytes())
                wav_buffer.seek(0)

                # Recognise in a sub-thread so we keep recording
                threading.Thread(
                    target=self._recognise,
                    args=(wav_buffer,),
                    daemon=True
                ).start()

            except Exception as e:
                if not self._stop_event.is_set():
                    self._queue.put(("error",
                        f"Microphone error — {e}. Check your mic settings."))
                break

    def _recognise(self, wav_buffer: io.BytesIO):
        if self._stop_event.is_set():
            return
        try:
            with sr.AudioFile(wav_buffer) as source:
                audio = self._recognizer.record(source)
            text = self._recognizer.recognize_google(audio)
            if text and not self._stop_event.is_set():
                self._queue.put(("transcript", text))
        except sr.UnknownValueError:
            pass  # silence / unintelligible
        except sr.RequestError as e:
            if not self._stop_event.is_set():
                self._queue.put(("error",
                    f"Couldn't reach speech recognition service — {e}. "
                    "Check your internet connection."))
        except Exception:
            pass
