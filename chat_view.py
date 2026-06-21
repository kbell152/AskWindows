#
#  chat_view.py
#  AskWindows
#
#  The main chat screen. Mirrors ChatView in ContentView.swift.
#  Handles:
#   - Text input and sending
#   - Single-shot mic (tap to listen, tap to stop)
#   - Conversation mode (fully hands-free, mirrors the Swift state machine)
#   - TTS read-aloud per message
#   - Settings sheet
#   - Text zoom (Ctrl +/-)
#

import threading
import time
import requests
import customtkinter as ctk
from tkinter import messagebox
from user_settings import UserSettings, SKILL_OPTIONS, TONE_OPTIONS
from speech import SpeechPlayer
from mic_input import MicInput

ORANGE       = "#FF8C00"
ORANGE_HOVER = "#CC6600"
SERVER_URL   = "https://askmac-server.morning-poetry-8fbb.workers.dev"
SILENCE_SECONDS = 4.0   # matches AskMac's 4-second silence timer


class ChatView(ctk.CTkFrame):

    def __init__(self, master, settings: UserSettings, on_reset, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._settings   = settings
        self._on_reset   = on_reset
        self._speech     = SpeechPlayer()
        self._mic        = MicInput()

        # Conversation mode state (mirrors Swift state machine)
        self._is_conversing      = False
        self._conv_muted         = False
        self._silence_timer: threading.Timer | None = None
        self._last_transcript    = ""
        self._conv_transcript    = ""

        # Single-shot mic state
        self._mic_active = False
        self._mic_transcript = ""

        # Messages: list of {"role": "user"|"assistant", "content": str}
        self._messages: list[dict] = []

        # Text zoom (mirrored from AppStorage)
        self._base_font_size = 13

        self._build()
        self._schedule_drain()

    # ==================================================================
    # UI Construction
    # ==================================================================

    def _build(self):
        # ── Top bar ──────────────────────────────────────────────────
        topbar = ctk.CTkFrame(self, fg_color="transparent")
        topbar.pack(fill="x", padx=16, pady=(12, 0))

        ctk.CTkLabel(
            topbar,
            text="Ask Windows",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            topbar,
            text="⚙",
            width=36, height=30,
            font=ctk.CTkFont(size=16),
            fg_color="transparent",
            hover_color="gray20",
            command=self._open_settings,
        ).pack(side="right")

        # ── Chat history ─────────────────────────────────────────────
        self._chat_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=("gray95", "gray10"),
            corner_radius=10,
        )
        self._chat_frame.pack(fill="both", expand=True, padx=16, pady=10)
        self._chat_frame.columnconfigure(0, weight=1)

        # ── Status label (conversation mode) ────────────────────────
        self._status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self._status_label.pack(pady=(0, 2))

        # ── Bottom bar ───────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 12))

        # Text input
        self._input_var = ctk.StringVar()
        self._entry = ctk.CTkEntry(
            bottom,
            textvariable=self._input_var,
            placeholder_text="Ask a question…",
            font=ctk.CTkFont(size=self._base_font_size),
            height=36,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._entry.bind("<Return>", lambda e: self._send_text())

        # Conversation mode button (waveform)
        self._conv_btn = ctk.CTkButton(
            bottom,
            text="〜",
            width=36, height=36,
            font=ctk.CTkFont(size=18),
            fg_color=ORANGE,
            hover_color=ORANGE_HOVER,
            command=self._toggle_conversation_mode,
        )
        self._conv_btn.pack(side="right", padx=(4, 0))

        # Mic button
        self._mic_btn = ctk.CTkButton(
            bottom,
            text="🎤",
            width=36, height=36,
            font=ctk.CTkFont(size=16),
            fg_color=ORANGE,
            hover_color=ORANGE_HOVER,
            command=self._toggle_mic,
        )
        self._mic_btn.pack(side="right", padx=(4, 0))

        # Send button
        self._send_btn = ctk.CTkButton(
            bottom,
            text="➤",
            width=36, height=36,
            font=ctk.CTkFont(size=14),
            fg_color=ORANGE,
            hover_color=ORANGE_HOVER,
            command=self._send_text,
        )
        self._send_btn.pack(side="right", padx=(4, 0))

        # Bind Ctrl +/- for zoom
        self.winfo_toplevel().bind("<Control-equal>", lambda e: self._zoom(+0.1))
        self.winfo_toplevel().bind("<Control-plus>",  lambda e: self._zoom(+0.1))
        self.winfo_toplevel().bind("<Control-minus>", lambda e: self._zoom(-0.1))
        self.winfo_toplevel().bind("<Control-0>",     lambda e: self._reset_zoom())

        # ── Welcome message ──────────────────────────────────────────
        name = self._settings.name
        greeting = f"Hi{' ' + name if name else ''}! I'm Ask Windows — your friendly Mac-to-Windows helper. What would you like to know?"
        self._add_message("assistant", greeting)

    # ==================================================================
    # Text zoom
    # ==================================================================

    def _zoom(self, delta: float):
        z = self._settings.text_zoom
        z = max(0.8, min(2.0, round(z + delta, 2)))
        self._settings.text_zoom = z
        self._base_font_size = int(13 * z)

    def _reset_zoom(self):
        self._settings.text_zoom = 1.2
        self._base_font_size = int(13 * 1.2)

    # ==================================================================
    # Chat rendering
    # ==================================================================

    def _add_message(self, role: str, content: str, speak=False):
        self._messages.append({"role": role, "content": content})

        row = len(self._messages) - 1
        is_user = role == "user"

        bubble_color = (ORANGE, "#994400") if is_user else ("gray85", "gray20")
        anchor = "e" if is_user else "w"
        padx   = (60, 8) if is_user else (8, 60)

        bubble = ctk.CTkFrame(
            self._chat_frame,
            fg_color=bubble_color,
            corner_radius=12,
        )
        bubble.grid(row=row * 2, column=0, sticky=anchor,
                    padx=padx, pady=(4, 0))

        text_lbl = ctk.CTkLabel(
            bubble,
            text=content,
            font=ctk.CTkFont(size=self._base_font_size),
            wraplength=480,
            justify="left",
            anchor="w",
        )
        text_lbl.pack(padx=12, pady=8)

        # Speaker button for assistant messages
        if not is_user:
            speak_btn = ctk.CTkButton(
                self._chat_frame,
                text="🔊",
                width=28, height=22,
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color="gray30",
                command=lambda c=content: self._toggle_speak(c),
            )
            speak_btn.grid(row=row * 2 + 1, column=0, sticky="w",
                           padx=(8, 0), pady=(0, 4))

        # Auto-scroll to bottom
        self._chat_frame._parent_canvas.after(
            50, lambda: self._chat_frame._parent_canvas.yview_moveto(1.0))

        if speak:
            self._speech.speak(content,
                               on_done=self._on_speech_done_in_conv_mode)

    def _toggle_speak(self, content: str):
        if self._speech.is_speaking:
            self._speech.stop()
        else:
            self._speech.speak(content)

    # ==================================================================
    # Sending questions
    # ==================================================================

    def _send_text(self):
        text = self._input_var.get().strip()
        if not text:
            return
        self._input_var.set("")
        self._dispatch_question(text)

    def _dispatch_question(self, text: str, speak_reply=False):
        self._add_message("user", text)
        self._set_status("Thinking…" if self._is_conversing else "")
        self._entry.configure(state="disabled")
        self._send_btn.configure(state="disabled")

        threading.Thread(
            target=self._fetch_answer,
            args=(text, speak_reply),
            daemon=True
        ).start()

    def _fetch_answer(self, question: str, speak_reply: bool):
        try:
            # The worker expects an Anthropic-style `messages` array, not a
            # single `question` string. Send the recent conversation, trimmed
            # so it BEGINS with a user message (Anthropic requires that —
            # our first stored message is the assistant greeting).
            recent = self._messages[-20:]
            while recent and recent[0]["role"] != "user":
                recent = recent[1:]
            messages = [
                {"role": m["role"], "content": m["content"]}
                for m in recent
            ]

            payload = {
                "inviteCode": self._settings.invite_code,
                "platform":   "windows",
                "messages":   messages,
                "userContext": {
                    "name":        self._settings.name,
                    "skill":       self._settings.skill,
                    "tone":        self._settings.tone,
                    "osVersion":   self._settings.os_version,
                    "inputDevice": self._settings.input_device,
                },
            }
            resp = requests.post(SERVER_URL, json=payload, timeout=30)
            data = resp.json()
            if "reply" in data:
                self.after(0, self._on_answer, data["reply"], speak_reply)
            else:
                err = data.get("error", "Unknown error from server.")
                self.after(0, self._on_answer_error, err)
        except requests.exceptions.ConnectionError:
            self.after(0, self._on_answer_error,
                       "Couldn't reach the server. Check your internet connection.")
        except Exception as e:
            self.after(0, self._on_answer_error, str(e))

    def _on_answer(self, reply: str, speak: bool):
        self._entry.configure(state="normal")
        self._send_btn.configure(state="normal")
        self._add_message("assistant", reply, speak=speak)
        if self._is_conversing and speak:
            self._set_status("Speaking…")
        elif self._is_conversing:
            self._set_status("Listening…")
            self._start_conversation_listen()

    def _on_answer_error(self, message: str):
        self._entry.configure(state="normal")
        self._send_btn.configure(state="normal")
        self._add_message("assistant", f"⚠ {message}")
        if self._is_conversing:
            self._set_status("Listening…")
            self._start_conversation_listen()

    # ==================================================================
    # Single-shot mic
    # ==================================================================

    def _toggle_mic(self):
        if self._is_conversing:
            # In conversation mode, mic button = mute/unmute
            self._toggle_conv_mute()
            return

        if self._mic_active:
            self._stop_single_mic()
        else:
            self._start_single_mic()

    def _start_single_mic(self):
        self._mic_active = True
        self._mic_transcript = ""
        self._mic_btn.configure(text="⏹", fg_color="red", hover_color="#880000")
        self._mic.start_listening(
            on_transcript=self._on_single_mic_transcript,
            on_error=self._on_mic_error,
        )

    def _stop_single_mic(self):
        self._mic.stop_listening()
        self._mic_active = False
        self._mic_btn.configure(text="🎤", fg_color=ORANGE, hover_color=ORANGE_HOVER)
        if self._mic_transcript.strip():
            self._input_var.set(self._mic_transcript)

    def _on_single_mic_transcript(self, text: str):
        self._mic_transcript = text
        self._input_var.set(text)

    def _on_mic_error(self, message: str):
        # If the mic fails mid-conversation, tear conversation mode down
        # cleanly so the buttons and status don't get stuck.
        if self._is_conversing:
            self._stop_conversation_mode()
        self._mic_active = False
        self._mic_btn.configure(text="🎤", fg_color=ORANGE, hover_color=ORANGE_HOVER)
        messagebox.showwarning("Microphone", message)
        
    # ==================================================================
    # Conversation mode  (mirrors Swift state machine exactly)
    # ==================================================================

    def _toggle_conversation_mode(self):
        if self._is_conversing:
            self._stop_conversation_mode()
        else:
            self._start_conversation_mode()

    def _start_conversation_mode(self):
        self._is_conversing = True
        self._conv_muted = False
        self._conv_btn.configure(text="⏹", fg_color="red", hover_color="#880000")
        self._set_status("Listening…")
        self._start_conversation_listen()

    def _stop_conversation_mode(self):
        self._is_conversing = False
        self._cancel_silence_timer()
        self._mic.stop_listening()
        self._speech.stop()
        self._conv_btn.configure(text="〜", fg_color=ORANGE, hover_color=ORANGE_HOVER)
        self._mic_btn.configure(text="🎤", fg_color=ORANGE, hover_color=ORANGE_HOVER)
        self._set_status("")

    def _start_conversation_listen(self):
        if not self._is_conversing or self._conv_muted:
            return
        self._conv_transcript = ""
        self._last_transcript = ""
        self._mic.start_listening(
            on_transcript=self._on_conv_transcript,
            on_error=self._on_mic_error,
        )

    def _on_conv_transcript(self, text: str):
        """
        Called each time a recognition segment arrives in conversation mode.
        Each new segment resets the 4-second silence timer — just like
        AskMac's `conversationTranscriptUpdated` function.
        """
        if not self._is_conversing:
            return
        self._conv_transcript = (
            (self._conv_transcript + " " + text).strip()
        )
        self._reset_silence_timer()

    def _reset_silence_timer(self):
        self._cancel_silence_timer()
        self._silence_timer = threading.Timer(
            SILENCE_SECONDS, self._on_silence_timeout)
        self._silence_timer.daemon = True
        self._silence_timer.start()

    def _cancel_silence_timer(self):
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None

    def _on_silence_timeout(self):
        """
        Fires after SILENCE_SECONDS of no new transcript segments.
        Mirrors the Swift silenceTimer firing → sendInConversationMode.
        """
        self.after(0, self._send_in_conversation_mode)

    def _send_in_conversation_mode(self):
        if not self._is_conversing:
            return
        text = self._conv_transcript.strip()
        self._mic.stop_listening()
        self._conv_transcript = ""
        if not text:
            # Nothing heard — re-arm immediately
            self._set_status("Listening…")
            self._start_conversation_listen()
            return
        self._set_status("Thinking…")
        self._dispatch_question(text, speak_reply=True)

    def _on_speech_done_in_conv_mode(self):
        """
        Called by SpeechPlayer when an utterance finishes naturally.
        Mirrors the Swift poll on isSpeaking — re-arms the mic.
        Runs on the speech thread; use after() to hop back to UI thread.
        """
        if not self._is_conversing:
            return
        time.sleep(0.8)  # 800 ms pause (matches AskMac)
        self.after(0, self._rearm_after_speech)

    def _rearm_after_speech(self):
        if not self._is_conversing:
            return
        self._set_status("Listening…")
        self._start_conversation_listen()

    def _toggle_conv_mute(self):
        self._conv_muted = not self._conv_muted
        if self._conv_muted:
            self._mic.stop_listening()
            self._cancel_silence_timer()
            self._mic_btn.configure(text="🚫🎤", fg_color="gray40",
                                    hover_color="gray30")
            self._set_status("Muted")
        else:
            self._mic_btn.configure(text="🎤", fg_color=ORANGE,
                                    hover_color=ORANGE_HOVER)
            self._set_status("Listening…")
            self._start_conversation_listen()

    # ==================================================================
    # Status label
    # ==================================================================

    def _set_status(self, text: str):
        self._status_label.configure(text=text)

    # ==================================================================
    # Mic callback drain loop
    # ==================================================================

    def _schedule_drain(self):
        self._mic.drain_callbacks()
        self.after(100, self._schedule_drain)

    # ==================================================================
    # Settings sheet
    # ==================================================================

    def _open_settings(self):
        sheet = SettingsSheet(
            self.winfo_toplevel(),
            self._settings,
            on_reset=self._on_reset,
        )
        sheet.grab_set()

    # ==================================================================
    # Helpers
    # ==================================================================

    def cleanup(self):
        """Call before destroying this view."""
        self._stop_conversation_mode()
        self._mic.stop_listening()
        self._speech.stop()


# ======================================================================
# Settings Sheet  (mirrors SettingsSheet in ContentView.swift)
# ======================================================================

class SettingsSheet(ctk.CTkToplevel):

    def __init__(self, master, settings: UserSettings, on_reset, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Settings")
        self.resizable(False, False)
        self.geometry("400x340")
        self._settings = settings
        self._on_reset  = on_reset
        self._build()

    def _build(self):
        pad = {"padx": 20, "pady": 6}

        ctk.CTkLabel(self, text="Settings",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(**pad, pady=(16, 6))

        # Name
        ctk.CTkLabel(self, text="Your name",
                     font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", **pad)
        self._name_var = ctk.StringVar(value=self._settings.name)
        ctk.CTkEntry(self, textvariable=self._name_var,
                     font=ctk.CTkFont(size=13)).pack(fill="x", **pad)

        # Skill
        ctk.CTkLabel(self, text="Skill level",
                     font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", **pad)
        self._skill_var = ctk.StringVar(value=self._settings.skill)
        ctk.CTkSegmentedButton(
            self, values=SKILL_OPTIONS, variable=self._skill_var,
            font=ctk.CTkFont(size=11)
        ).pack(fill="x", **pad)

        # Tone
        ctk.CTkLabel(self, text="Tone",
                     font=ctk.CTkFont(size=12), anchor="w").pack(fill="x", **pad)
        self._tone_var = ctk.StringVar(value=self._settings.tone)
        ctk.CTkOptionMenu(
            self, values=TONE_OPTIONS, variable=self._tone_var,
            font=ctk.CTkFont(size=12)
        ).pack(fill="x", **pad)

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(14, 0))

        ctk.CTkButton(
            btn_row, text="Save", fg_color=ORANGE, hover_color=ORANGE_HOVER,
            command=self._save
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Start over", fg_color="gray40", hover_color="gray30",
            command=self._reset
        ).pack(side="left", expand=True, fill="x")

    def _save(self):
        self._settings.name  = self._name_var.get().strip()
        self._settings.skill = self._skill_var.get()
        self._settings.tone  = self._tone_var.get()
        self.destroy()

    def _reset(self):
        if messagebox.askyesno(
            "Start over",
            "This will clear your invite code and all settings.\nAre you sure?"
        ):
            self._settings.reset()
            self.destroy()
            self._on_reset()
