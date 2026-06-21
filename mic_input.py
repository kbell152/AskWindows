#
#  mic_input.py
#  AskWindows
#
#  Listens to the microphone and converts speech to text using
#  SpeechRecognition + Google Web Speech API (same reliability trade-off
#  as AskMac's requiresOnDeviceRecognition = false).
#
#  Also supports Vosk for fully offline recognition — set USE_OFFLINE = True
#  below if you want to experiment, but leave False for production parity
#  with AskMac.
#
#  Runs in a background thread; fires callbacks on the calling thread via
#  a thread-safe queue that main.py drains on the tkinter main loop.
#

import queue
import threading
import speech_recognition as sr


USE_OFFLINE = False  # True = Vosk (must pip install vosk + download model)


class MicInput:
    """
    Async microphone listener. All callbacks arrive on a queue; the UI
    loop should call drain_callbacks() regularly (e.g. every 100 ms).
    """

    def __init__(self):
        self._recognizer = sr.Recognizer()
        # Tune for typical quiet home/office environments.
        # Shorter pause_threshold = 4-second-silence handled by conversation
        # mode itself; we keep recognition segments shorter.
        self._recognizer.pause_threshold = 0.8
        self._recognizer.energy_threshold = 300
        self._recognizer.dynamic_energy_threshold = True

        self._queue: queue.Queue = queue.Queue()
        self._listen_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self.is_listening = False
        self.error_message: str | None = None

        # Callbacks the owner registers:
        # on_transcript(text)  — partial or final text update
        # on_error(message)    — something went wrong
        self._on_transcript = None
        self._on_error = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_listening(self, on_transcript=None, on_error=None):
        """
        Start continuous microphone capture.
        on_transcript(text) is called with each recognised segment.
        on_error(message) is called on failure.
        """
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
        """
        Stop listening. Returns whatever transcript was accumulated.
        """
        if not self.is_listening:
            return ""
        self._stop_event.set()
        self.is_listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=3)
        return ""

    def drain_callbacks(self):
        """
        Call this regularly from the UI main loop (e.g. root.after(100, ...)).
        Fires any queued on_transcript / on_error callbacks on the UI thread.
        """
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
        """
        Continuously reads audio chunks and recognises each one.
        Uses Google Web Speech (free, no key, mirrors AskMac's cloud STT).
        """
        # Opening the mic can fail outright on a PC with no audio input
        # device (a VM with no mic passed through, or a desktop with nothing
        # plugged in). Handle it gracefully instead of crashing this thread.
        try:
            mic = sr.Microphone()
        except Exception:
            if not self._stop_event.is_set():
                self._queue.put(("error",
                    "I couldn't find a microphone on this PC. "
                    "You can still type your questions."))
            self.is_listening = False
            return

        try:
            with mic as source:
                try:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                except Exception:
                    pass

                while not self._stop_event.is_set():
                    try:
                        audio = self._recognizer.listen(
                            source, timeout=1, phrase_time_limit=30)
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        if not self._stop_event.is_set():
                            self._queue.put(("error",
                                f"Microphone error — {e}. Check your mic settings."))
                        break

                    if self._stop_event.is_set():
                        break

                    threading.Thread(
                        target=self._recognise, args=(audio,), daemon=True).start()
        except Exception:
            # The stream itself failed to open (device vanished / PortAudio error).
            if not self._stop_event.is_set():
                self._queue.put(("error",
                    "The microphone stopped working. "
                    "You can still type your questions."))
        finally:
            self.is_listening = False

    def _recognise(self, audio: sr.AudioData):
        if self._stop_event.is_set():
            return
        try:
            if USE_OFFLINE:
                text = self._recognizer.recognize_vosk(audio)
            else:
                text = self._recognizer.recognize_google(audio)

            if text and not self._stop_event.is_set():
                self._queue.put(("transcript", text))

        except sr.UnknownValueError:
            pass  # silence / unintelligible — not an error
        except sr.RequestError as e:
            if not self._stop_event.is_set():
                self._queue.put(("error",
                    f"Couldn't reach speech recognition service — {e}. "
                    "Check your internet connection."))
        except Exception:
            pass
