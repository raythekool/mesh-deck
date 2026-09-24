"""Safe, transactional UI for the editable identity of the connected radio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from mesh_deck.i18n import t

if TYPE_CHECKING:
    from mesh_deck.core.radio_client import RadioClient


class IdentityConfirmScreen(ModalScreen[bool]):
    """Require an explicit review before an identity write reaches the radio."""

    CSS = """
    IdentityConfirmScreen { align: center middle; background: #000000aa; }
    #identity-confirm-dialog { width: 72; height: auto; padding: 1 2; border: round $mesh-warning; background: $mesh-bg-elevated; }
    #identity-confirm-title { color: $mesh-warning; text-style: bold; }
    #identity-confirm-diff { margin-top: 1; color: $mesh-text; }
    #identity-confirm-actions { height: auto; margin-top: 2; align-horizontal: right; }
    #identity-confirm-actions Button { margin-left: 1; }
    """

    def __init__(
        self,
        current: dict[str, str],
        draft: dict[str, str],
        lang: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.current = current
        self.draft = draft
        self.lang = lang

    def compose(self) -> ComposeResult:
        with Vertical(id="identity-confirm-dialog"):
            yield Label(t("DEVICE_SETTINGS_CONFIRM_TITLE", self.lang), id="identity-confirm-title")
            yield Static(
                t(
                    "DEVICE_SETTINGS_CONFIRM_DIFF",
                    self.lang,
                    old_long=self.current["long_name"] or "—",
                    new_long=self.draft["long_name"],
                    old_short=self.current["short_name"] or "—",
                    new_short=self.draft["short_name"],
                ),
                id="identity-confirm-diff",
            )
            with Horizontal(id="identity-confirm-actions"):
                yield Button(t("DEVICE_SETTINGS_CANCEL", self.lang), id="cancel")
                yield Button(t("DEVICE_SETTINGS_APPLY", self.lang), id="apply", variant="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "apply")


class DeviceSettingsScreen(Screen[None]):
    """Edit identity in a local draft, review its diff, then apply explicitly."""

    BINDINGS = [
        Binding("q", "close", "Close", show=True),
        Binding("escape", "close", "Back", show=True),
        Binding("r", "reload_identity", "Reload", show=True),
    ]

    CSS = """
    Screen { background: $mesh-bg; color: $mesh-text; }
    #device-settings-body { height: 1fr; margin: 1; }
    #device-settings-groups { width: 24; padding: 1; border: round $mesh-border-soft; background: $mesh-bg-elevated; }
    #device-settings-groups-title { color: $mesh-primary; text-style: bold; }
    .device-settings-group { margin-top: 1; color: $mesh-text; }
    .device-settings-group-disabled { margin-top: 1; color: $mesh-muted; }
    #device-settings-editor { width: 1fr; margin-left: 1; padding: 1; border: round $mesh-primary; background: $mesh-bg-panel; }
    #device-settings-title { color: $mesh-primary; text-style: bold; }
    .device-settings-label { margin-top: 1; color: $mesh-text; }
    .device-settings-input { background: $mesh-bg-elevated; color: $mesh-text; }
    #device-settings-status { height: auto; margin-top: 1; color: $mesh-muted; }
    #device-settings-diff { height: auto; margin-top: 1; padding: 1; border: round $mesh-border-soft; color: $mesh-text; }
    #device-settings-actions { height: auto; margin-top: 2; align-horizontal: right; }
    #device-settings-actions Button { margin-left: 1; }
    Footer { background: $mesh-bg-elevated; color: $mesh-muted; }
    """

    def __init__(self, client: RadioClient, lang: str = "it", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.client = client
        self.lang = lang
        self._snapshot: dict[str, str] = {}
        self._busy = False
        self.title = t("DEVICE_SETTINGS_TITLE", lang)
        self.sub_title = t("DEVICE_SETTINGS_SUBTITLE", lang)
        self._bindings.key_to_bindings["q"] = [Binding("q", "close", t("BINDING_CLOSE", lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "close", t("BINDING_BACK", lang), show=True)]
        self._bindings.key_to_bindings["r"] = [Binding("r", "reload_identity", t("BINDING_REFRESH", lang), show=True)]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="device-settings-body"):
            with Vertical(id="device-settings-groups"):
                yield Static(t("DEVICE_SETTINGS_GROUPS_TITLE", self.lang), id="device-settings-groups-title")
                yield Static(t("DEVICE_SETTINGS_GROUP_IDENTITY", self.lang), classes="device-settings-group")
                yield Static(t("DEVICE_SETTINGS_GROUP_RADIO_LOCKED", self.lang), classes="device-settings-group-disabled")
                yield Static(t("DEVICE_SETTINGS_GROUP_POSITION_LOCKED", self.lang), classes="device-settings-group-disabled")
                yield Static(t("DEVICE_SETTINGS_GROUP_CHANNELS_LOCKED", self.lang), classes="device-settings-group-disabled")
            with Vertical(id="device-settings-editor"):
                yield Static(t("DEVICE_SETTINGS_IDENTITY_TITLE", self.lang), id="device-settings-title")
                yield Label(t("DEVICE_SETTINGS_LONG_NAME", self.lang), classes="device-settings-label")
                yield Input(id="device-settings-long-name", classes="device-settings-input")
                yield Label(t("DEVICE_SETTINGS_SHORT_NAME", self.lang), classes="device-settings-label")
                yield Input(id="device-settings-short-name", classes="device-settings-input")
                yield Static(id="device-settings-status")
                yield Static(id="device-settings-diff")
                with Horizontal(id="device-settings-actions"):
                    yield Button(t("DEVICE_SETTINGS_REVERT", self.lang), id="revert")
                    yield Button(t("DEVICE_SETTINGS_REVIEW", self.lang), id="review", variant="warning")
        yield Footer()

    def on_mount(self) -> None:
        self.reload_identity()

    @work(thread=True, exclusive=True)
    def reload_identity(self) -> None:
        try:
            snapshot = self.client.get_device_identity()
        except Exception as exc:
            self.app.call_from_thread(self._show_error, exc)
            return
        self.app.call_from_thread(self._load_snapshot, snapshot)

    def _load_snapshot(self, snapshot: dict[str, str]) -> None:
        self._snapshot = snapshot
        self.query_one("#device-settings-long-name", Input).value = snapshot["long_name"]
        self.query_one("#device-settings-short-name", Input).value = snapshot["short_name"]
        self.query_one("#device-settings-status", Static).update(
            t("DEVICE_SETTINGS_SNAPSHOT", self.lang, node=snapshot["id"])
        )
        self._render_diff()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in ("device-settings-long-name", "device-settings-short-name"):
            self._render_diff()

    def _draft(self) -> dict[str, str]:
        return {
            "long_name": self.query_one("#device-settings-long-name", Input).value.strip(),
            "short_name": self.query_one("#device-settings-short-name", Input).value.strip(),
        }

    def _validate_draft(self) -> str | None:
        draft = self._draft()
        if not draft["long_name"]:
            return t("DEVICE_SETTINGS_VALIDATION_LONG_REQUIRED", self.lang)
        if len(draft["long_name"]) > 39:
            return t("DEVICE_SETTINGS_VALIDATION_LONG_LENGTH", self.lang)
        if not draft["short_name"]:
            return t("DEVICE_SETTINGS_VALIDATION_SHORT_REQUIRED", self.lang)
        if len(draft["short_name"]) > 4:
            return t("DEVICE_SETTINGS_VALIDATION_SHORT_LENGTH", self.lang)
        return None

    def _render_diff(self) -> None:
        if not self._snapshot:
            return
        draft = self._draft()
        validation_error = self._validate_draft()
        if validation_error:
            self.query_one("#device-settings-diff", Static).update(
                f"[{self.app.get_css_variables()['mesh-alert']}]{validation_error}[/]"
            )
            return
        if draft == {key: self._snapshot.get(key, "") for key in draft}:
            self.query_one("#device-settings-diff", Static).update(t("DEVICE_SETTINGS_NO_CHANGES", self.lang))
            return
        self.query_one("#device-settings-diff", Static).update(
            t(
                "DEVICE_SETTINGS_DIFF",
                self.lang,
                old_long=self._snapshot.get("long_name") or "—",
                new_long=draft["long_name"],
                old_short=self._snapshot.get("short_name") or "—",
                new_short=draft["short_name"],
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "revert":
            self._load_snapshot(self._snapshot)
            return
        if event.button.id == "review":
            validation_error = self._validate_draft()
            if validation_error:
                self.query_one("#device-settings-status", Static).update(validation_error)
                return
            draft = self._draft()
            if draft == {key: self._snapshot.get(key, "") for key in draft}:
                self.query_one("#device-settings-status", Static).update(t("DEVICE_SETTINGS_NO_CHANGES", self.lang))
                return
            self.app.push_screen(
                IdentityConfirmScreen(self._snapshot, draft, self.lang),
                callback=self._on_identity_confirmed,
            )

    def _on_identity_confirmed(self, apply: bool | None) -> None:
        if not apply:
            return
        self._apply_identity(self._draft())

    @work(thread=True, exclusive=True)
    def _apply_identity(self, draft: dict[str, str]) -> None:
        try:
            updated = self.client.update_device_identity(**draft)
        except Exception as exc:
            self.app.call_from_thread(self._show_error, exc)
            return
        self.app.call_from_thread(self._show_applied, updated)

    def _show_applied(self, snapshot: dict[str, str]) -> None:
        self._load_snapshot(snapshot)
        self.query_one("#device-settings-status", Static).update(
            t("DEVICE_SETTINGS_APPLIED", self.lang)
        )

    def _show_error(self, exc: Exception) -> None:
        self.query_one("#device-settings-status", Static).update(
            t("DEVICE_SETTINGS_ERROR", self.lang, error=exc)
        )

    def action_reload_identity(self) -> None:
        self.reload_identity()

    def action_close(self) -> None:
        self.dismiss()
