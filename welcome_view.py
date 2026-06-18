#
#  welcome_view.py
#  AskWindows
#
#  First-run setup screen. Mirrors WelcomeView.swift.
#  Collects invite code, name, skill, tone, input device, and Windows version.
#  Saves to UserSettings and calls on_complete() when done.
#

import customtkinter as ctk
from user_settings import UserSettings, SKILL_OPTIONS, TONE_OPTIONS, INPUT_OPTIONS, INPUT_LABELS
from system_info import SystemInfo


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
            font=ctk.CTkFont(size=11), text_color="red"
        )
        # not gridded yet — shown on error

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
        ctk.CTkButton(
            inner,
            text="Continue",
            command=self._save_and_continue,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ORANGE,
            hover_color="#CC6600",
            height=38,
            width=380,
        ).grid(row=row, column=0, sticky="w", pady=(10, 0)); row += 1

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
            self._code_error.grid(column=0, sticky="w", pady=(0, 8))
            return
        self._code_error.grid_remove()

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
