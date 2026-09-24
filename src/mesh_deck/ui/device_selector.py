"""Textual startup screen for selecting a Meshtastic serial device."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Label, OptionList, Static
from textual.widgets.option_list import Option

from mesh_deck.core.events import DeviceConnectionInfo
from mesh_deck.core.scanner import scan_meshtastic_ports
from mesh_deck.i18n import t
from mesh_deck.ui.theme import ThemedApp


class DeviceSelectorScreen(Screen[str | None]):
    """Present detected devices and return the selected serial port."""

    TITLE = "MESH-DECK"
    SUB_TITLE = "Seleziona una periferica Meshtastic"
    BINDINGS = [
        Binding("r", "refresh_devices", "Aggiorna", show=True),
        Binding("t", "retry_failed_device", "Riprova", show=False),
        Binding("q", "cancel", "Annulla", show=True),
        Binding("escape", "cancel", "Annulla", show=False),
    ]
    CSS = """
    Screen { align: center middle; background: $mesh-bg; color: $mesh-text; }
    #device-dialog { width: 76; height: auto; max-height: 28; padding: 1 2; border: round $mesh-primary; background: $mesh-bg-elevated; }
    #device-heading { width: 100%; height: 3; background: $mesh-bg-header; color: $mesh-primary; content-align: center middle; text-align: center; text-style: bold; }
    #device-help { width: 100%; height: 3; margin: 1 0; background: $mesh-bg-panel; color: $mesh-muted; content-align: center middle; text-align: center; }
    #devices { height: auto; max-height: 12; background: $mesh-bg-panel; color: $mesh-text; }
    #device-error { height: auto; margin-top: 1; padding: 0 1; color: $mesh-warning; display: none; }
    #device-empty { height: auto; margin-top: 1; padding: 1; border: round $mesh-border-soft; background: $mesh-bg-panel; color: $mesh-muted; display: none; }
    Footer { background: $mesh-bg-elevated; color: $mesh-muted; }
    OptionList:focus { border: double $mesh-primary; }
    """

    def __init__(
        self,
        devices: list[DeviceConnectionInfo],
        preferred_port: str | None = None,
        active_port: str | None = None,
        failed_port: str | None = None,
        failure_reason: str | None = None,
        lang: str = "it",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.devices = devices
        self.preferred_port = preferred_port
        self.active_port = active_port
        self.failed_port = failed_port
        self.failure_reason = failure_reason
        self.lang = lang
        self.sub_title = t("DEVICE_SELECTOR_SUBTITLE", self.lang)
        self._bindings.key_to_bindings["r"] = [Binding("r", "refresh_devices", t("BINDING_REFRESH", self.lang), show=True)]
        self._bindings.key_to_bindings["t"] = [
            Binding("t", "retry_failed_device", t("BINDING_RETRY", self.lang), show=bool(self.failed_port))
        ]
        self._bindings.key_to_bindings["q"] = [Binding("q", "cancel", t("BINDING_CANCEL", self.lang), show=True)]
        self._bindings.key_to_bindings["escape"] = [Binding("escape", "cancel", t("BINDING_CANCEL", self.lang), show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="device-dialog"):
            yield Label(t("DEVICE_SELECTOR_HEADING", self.lang), id="device-heading")
            yield Static(t("DEVICE_SELECTOR_HELP", self.lang), id="device-help")
            yield OptionList(id="devices")
            yield Static(id="device-error")
            yield Static(id="device-empty")
        yield Footer()

    def on_mount(self) -> None:
        self._update_options()
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_index < len(self.devices):
            self.dismiss(self.devices[event.option_index].port)

    def action_refresh_devices(self) -> None:
        self.devices = scan_meshtastic_ports()
        self._update_options()

    def action_retry_failed_device(self) -> None:
        if self.failed_port:
            self.dismiss(self.failed_port)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _update_options(self) -> None:
        options = self.query_one(OptionList)
        options.set_options(
            [
                Option(self._device_label(device))
                for device in self.devices
            ]
        )
        options.disabled = not self.devices
        error = self.query_one("#device-error", Static)
        empty = self.query_one("#device-empty", Static)
        error.display = bool(self.failed_port)
        if self.failed_port:
            reason = self.failure_reason or t("DEVICE_SELECTOR_FAILURE_UNKNOWN", self.lang)
            error.update(t("DEVICE_SELECTOR_FAILURE", self.lang, port=self.failed_port, reason=reason))
        empty.display = not self.devices
        if not self.devices:
            empty.update(t("DEVICE_SELECTOR_EMPTY_HELP", self.lang))
        if self.devices:
            selected_index = 0
            for port in (self.failed_port, self.active_port, self.preferred_port):
                if not port:
                    continue
                match = next(
                    (index for index, device in enumerate(self.devices) if device.port == port),
                    None,
                )
                if match is not None:
                    selected_index = match
                    break
            options.highlighted = selected_index

    def _device_label(self, device: DeviceConnectionInfo) -> str:
        badges: list[str] = []
        if device.port == self.active_port:
            badges.append(t("DEVICE_SELECTOR_ACTIVE", self.lang))
        if device.port == self.preferred_port:
            badges.append(t("DEVICE_SELECTOR_PREFERRED", self.lang))
        if device.port == self.failed_port:
            badges.append(t("DEVICE_SELECTOR_RETRY", self.lang))
        badge_text = f"  [dim]•[/]  [bold]{' · '.join(badges)}[/]" if badges else ""
        return f"[bold cyan]{device.port}[/]  [white]{device.hw_name}[/]{badge_text}\n[dim]{device.description}[/]"


class DeviceSelectorApp(ThemedApp, App[str | None]):
    """Standalone wrapper for the reusable device selector screen."""

    def __init__(
        self,
        devices: list[DeviceConnectionInfo],
        preferred_port: str | None = None,
        active_port: str | None = None,
        failed_port: str | None = None,
        failure_reason: str | None = None,
        lang: str = "it",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.devices = devices
        self.preferred_port = preferred_port
        self.active_port = active_port
        self.failed_port = failed_port
        self.failure_reason = failure_reason
        self.lang = lang

    def on_mount(self) -> None:
        self.push_screen(
            DeviceSelectorScreen(
                self.devices,
                preferred_port=self.preferred_port,
                active_port=self.active_port,
                failed_port=self.failed_port,
                failure_reason=self.failure_reason,
                lang=self.lang,
            ),
            callback=self.exit,
        )


def select_device(
    devices: list[DeviceConnectionInfo],
    preferred_port: str | None = None,
    active_port: str | None = None,
    failed_port: str | None = None,
    failure_reason: str | None = None,
    lang: str = "it",
) -> str | None:
    """Run the startup selector and return a chosen port, if any."""
    return DeviceSelectorApp(
        devices,
        preferred_port=preferred_port,
        active_port=active_port,
        failed_port=failed_port,
        failure_reason=failure_reason,
        lang=lang,
    ).run()
