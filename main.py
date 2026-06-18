#
#  main.py
#  AskWindows
#
#  App entry point. Mirrors AskMacApp.swift.
#  Creates the window, loads settings, and switches between
#  WelcomeView and ChatView based on settings.is_set_up.
#

import customtkinter as ctk
from user_settings import UserSettings
from welcome_view import WelcomeView
from chat_view import ChatView


APP_TITLE   = "Ask Windows"
WIN_WIDTH   = 640
WIN_HEIGHT  = 700
MIN_WIDTH   = 520
MIN_HEIGHT  = 560


class AskWindowsApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self._settings = UserSettings()

        self.title(APP_TITLE)
        self.geometry(f"{WIN_WIDTH}x{WIN_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)

        # Use system default appearance (respects Windows dark/light mode).
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._current_view = None
        self._show_appropriate_view()

    def _show_appropriate_view(self):
        if self._current_view:
            # Give ChatView a chance to clean up threads before destroying.
            if hasattr(self._current_view, "cleanup"):
                self._current_view.cleanup()
            self._current_view.destroy()
            self._current_view = None

        if self._settings.is_set_up:
            self._current_view = ChatView(
                self,
                settings=self._settings,
                on_reset=self._on_reset,
            )
        else:
            self._current_view = WelcomeView(
                self,
                settings=self._settings,
                on_complete=self._on_setup_complete,
            )

        self._current_view.pack(fill="both", expand=True)

    def _on_setup_complete(self):
        """Called by WelcomeView when the user taps Continue."""
        self._show_appropriate_view()

    def _on_reset(self):
        """Called by SettingsSheet when the user taps 'Start over'."""
        self._show_appropriate_view()


def main():
    app = AskWindowsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
