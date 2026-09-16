"""Textual startup screen for selecting a Meshtastic serial device."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, OptionList, Static
from textual.widgets.option_list import Option

from mesh_deck.core.events import DeviceConnectionInfo
from mesh_deck.core.scanner import scan_meshtastic_ports


class DeviceSelectorScreen(Screen[str | None]):
    """Present detected devices and return the selected serial port."""

    TITLE = "MESH-DECK"
    SUB_TITLE = "Seleziona una periferica Meshtastic"
    BINDINGS = [
        Binding("r", "refresh_devices", "Aggiorna", show=True),
        Binding("q", "cancel", "Annulla", show=True),
        Binding("escape", "cancel", "Annulla", show=False),
    ]
    CSS = """
    Screen { align: center middle; background: #081018; color: #e8f1f5; }
    #device-dialog { width: 76; height: auto; max-height: 22; padding: 1 2; border: round #00f3ff; background: #10212b; }
    #device-heading { width: 100%; height: 3; background: #063b46; color: #00f3ff; content-align: center middle; text-align: center; text-style: bold; }
    #device-help { width: 100%; height: 3; margin: 1 0; background: #0b1720; color: #9aa9b4; content-align: center middle; text-align: center; }
    #devices { height: auto; max-height: 12; background: #0b1720; color: #e8f1f5; }
    Footer { background: #10212b; color: #9aa9b4; }
    """

    def __init__(
        self,
        devices: list[DeviceConnectionInfo],
        preferred_port: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.devices = devices
        self.preferred_port = preferred_port

    def compose(self) -> ComposeResult:
        with Vertical(id="device-dialog"):
            yield Label("Periferiche Meshtastic rilevate", id="device-heading")
            yield Static("Usa freccia Su/Giu e Invio per selezionare", id="device-help")
            yield OptionList(id="devices")
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

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _update_options(self) -> None:
        options = self.query_one(OptionList)
        options.set_options([
            Option(f"[bold cyan]{device.port}[/]  [white]{device.hw_name}[/]\n[dim]{device.description}[/]")
            for device in self.devices
        ])
        options.disabled = not self.devices
        if self.devices:
            selected_index = next(
                (index for index, device in enumerate(self.devices) if device.port == self.preferred_port),
                0,
            )
            options.highlighted = selected_index


class DeviceSelectorApp(App[str | None]):
    """Standalone wrapper for the reusable device selector screen."""

    def __init__(
        self,
        devices: list[DeviceConnectionInfo],
        preferred_port: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.devices = devices
        self.preferred_port = preferred_port

    def on_mount(self) -> None:
        self.push_screen(
            DeviceSelectorScreen(self.devices, preferred_port=self.preferred_port),
            callback=self.exit,
        )


def select_device(
    devices: list[DeviceConnectionInfo],
    preferred_port: str | None = None,
) -> str | None:
    """Run the startup selector and return a chosen port, if any."""
    return DeviceSelectorApp(devices, preferred_port=preferred_port).run()
