#
#  welcome_view.py
#  AskWindows
#
#  First-run setup screen. Mirrors WelcomeView.swift.
#  Collects invite code, name, skill, tone, input device, and Windows version.
#  Saves to UserSettings and calls on_complete() when done.
#

import threading
import requests
import customtkinter as ctk
from user_settings import UserSettings, SKILL_OPTIONS, TONE_OPTIONS, INPUT_OPTIONS, INPUT_LABELS
from system_info import SystemInfo
from chat_view import SERVER_URL


ORANGE = "#FF8C00"


class WelcomeView(ctk.CTkFrame):

    def __init__(self, master, settings: UserSettings, on_complete, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._settings = settings
        self._on_complete = on_complete
        self._build()

    def _build(self):
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        inner = ctk.CTkFrame(scroll, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=10)
        inner.columnconfigure(0, weight=1)

        row = 0

        # ── Header ──────────────────────────────────────────────────────
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.grid(row=row, column=0, sticky="w", pady=(0, 18)); row += 1

        ctk.CTkLabel(
            header,
            text="Welcome to Ask Windows",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            inner,
            text="A few quick questions so I can help you the way that suits you best.",
            font=ctk.CTkFont(size=13),
            text_color="gray60",
            wraplength=480,
            justify="left",
        ).grid(row=row, column=0, sticky="w", pady=(0, 20)); row += 1

        # ── Invite code ─────────────────────────────────────────────────
        self._section_label(inner, row, "Your invite code *"); row += 1
        self._invite_var = ctk.StringVar(value=self._settings.invite_code)
        ctk.CTkEntry(
            inner,
            textvariable=self._invite_var,
            placeholder_text="e.g. larry-2026-win",
            font=ctk.CTkFont(size=13),
            width=380,
        ).grid(row=row, column=0, sticky="w", pady=(0, 4)); row += 1

        self._code_error = ctk.CTkLabel(
            inner, text="Please enter the invite code you were given.",
            font=ctk.CTkFont(size=11), text_color="red",
            wraplength=380, justify="left",
        )
        # Reserve the row directly under the invite entry so the message
        # appears where the user is looking. Gridded on demand in _show_code_error.
        self._code_error_row = row; row += 1

        # ── Name ────────────────────────────────────────────────────────
        self._section_label(inner, row, "What should I call you?"); row += 1
        self._name_var = ctk.StringVar(value=self._settings.name)
        ctk.CTkEntry(
            inner,
            textvariable=self._name_var,
            placeholder_text="Your first name",
            font=ctk.CTkFont(size=13),
            width=380,
        ).grid(row=row, column=0, sticky="w", pady=(0, 14)); row += 1

        # ── Skill level ─────────────────────────────────────────────────
        self._section_label(inner, row, "How comfortable are you with computers?"); row += 1
        self._skill_var = ctk.StringVar(value=self._settings.skill or SKILL_OPTIONS[0])
        seg = ctk.CTkSegmentedButton(
            inner,
            values=SKILL_OPTIONS,
            variable=self._skill_var,
            font=ctk.CTkFont(size=12),
        )
        seg.grid(row=row, column=0, sticky="w", pady=(0, 14)); row += 1

        # ── Tone ────────────────────────────────────────────────────────
        self._section_label(inner, row, "How would you like me to talk to you?"); row += 1
        self._tone_var = ctk.StringVar(
            value=self._settings.tone or TONE_OPTIONS[0])
        for opt in TONE_OPTIONS:
            ctk.CTkRadioButton(
                inner,
                text=opt,
                variable=self._tone_var,
                value=opt,
                font=ctk.CTkFont(size=13),
            ).grid(row=row, column=0, sticky="w"); row += 1
        self._spacer(inner, row); row += 1

        # ── Input device ────────────────────────────────────────────────
        self._section_label(inner, row, "How do you click and scroll?"); row += 1
        self._input_var = ctk.StringVar(
            value=self._settings.input_device or "unknown")
        for opt in INPUT_OPTIONS:
            ctk.CTkRadioButton(
                inner,
                text=INPUT_LABELS[opt],
                variable=self._input_var,
                value=opt,
                font=ctk.CTkFont(size=13),
            ).grid(row=row, column=0, sticky="w"); row += 1
        self._spacer(inner, row); row += 1

        # ── Windows version ─────────────────────────────────────────────
        self._section_label(inner, row, "Your Windows version"); row += 1
        detected = SystemInfo.friendly_label()
        ctk.CTkLabel(
            inner,
            text=f"We detected: {detected}",
            font=ctk.CTkFont(size=13),
        ).grid(row=row, column=0, sticky="w"); row += 1

        self._use_detected_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            inner,
            text="That's correct — use this",
            variable=self._use_detected_var,
            command=self._toggle_os_override,
            font=ctk.CTkFont(size=13),
        ).grid(row=row, column=0, sticky="w"); row += 1

        os_choices = ["Windows 11", "Windows 10", "Windows 8.1",
                      "Windows 8", "Windows 7", "I'm not sure"]
        self._manual_os_var = ctk.StringVar(value="Windows 11")
        self._os_menu = ctk.CTkOptionMenu(
            inner,
            values=os_choices,
            variable=self._manual_os_var,
            font=ctk.CTkFont(size=13),
            state="disabled",
        )
        self._os_menu.grid(row=row, column=0, sticky="w", pady=(4, 14)); row += 1

        # ── Continue button ─────────────────────────────────────────────
        self._continue_btn = ctk.CTkButton(
            inner,
            text="Continue",
            command=self._save_and_continue,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ORANGE,
            hover_color="#CC6600",
            height=38,
            width=380,
        )
        self._continue_btn.grid(row=row, column=0, sticky="w", pady=(10, 0)); row += 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _section_label(self, parent, row, text):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(12, 2))

    def _spacer(self, parent, row):
        ctk.CTkLabel(parent, text="", height=4).grid(row=row, column=0)

    def _toggle_os_override(self):
        if self._use_detected_var.get():
            self._os_menu.configure(state="disabled")
        else:
            self._os_menu.configure(state="normal")

    def _save_and_continue(self):
        code = self._invite_var.get().strip()
        if not code:
            self._show_code_error("Please enter the invite code you were given.")
            return
        self._code_error.grid_remove()

        # Validate the invite code with the server up front, so the user is
        # told immediately if it's wrong — rather than only after they've
        # gone through setup and asked their first question. The check runs
        # on a background thread so the UI stays responsive.
        self._set_checking(True)
        threading.Thread(
            target=self._check_code, args=(code,), daemon=True
        ).start()

    def _check_code(self, code):
        """Ask the server whether the invite code is valid (runs off-thread)."""
        try:
            resp = requests.post(
                SERVER_URL,
                json={
                    "inviteCode":  code,
                    "platform":    "windows",
                    "messages":    [],
                    "userContext": {},
                },
                # (connect, read) timeouts: fail fast if the server can't be
                # reached, but still allow a moment for it to respond.
                timeout=(3.05, 5),
            )
            # The server checks the invite code before anything else and
            # returns 401 when it's invalid. Any other status means the code
            # itself passed, so we let the user continue.
            if resp.status_code == 401:
                self.after(0, self._on_code_invalid)
            else:
                self.after(0, self._on_code_valid, code)
        except requests.exceptions.RequestException:
            self.after(0, self._on_code_network_error)

    def _on_code_valid(self, code):
        self._set_checking(False)
        self._commit(code)

    def _on_code_invalid(self):
        self._set_checking(False)
        self._show_code_error(
            "That invite code isn't valid. Please check it and try again.")

    def _on_code_network_error(self):
        self._set_checking(False)
        self._show_code_error(
            "Couldn't check your invite code. Please check your internet "
            "connection and try again.")

    def _commit(self, code):
        s = self._settings
        s.invite_code  = code
        s.name         = self._name_var.get().strip()
        s.skill        = self._skill_var.get()
        s.tone         = self._tone_var.get()
        s.input_device = self._input_var.get()

        if self._use_detected_var.get():
            s.os_version = SystemInfo.detected_os_value()
        else:
            s.os_version = self._manual_os_var.get()

        self._on_complete()

    def _set_checking(self, checking: bool):
        """Toggle the Continue button between its normal and 'checking' state."""
        if checking:
            self._continue_btn.configure(state="disabled", text="Checking…")
        else:
            self._continue_btn.configure(state="normal", text="Continue")

    def _show_code_error(self, text: str):
        self._code_error.configure(text=text)
        self._code_error.grid(row=self._code_error_row, column=0,
                              sticky="w", pady=(0, 8))
