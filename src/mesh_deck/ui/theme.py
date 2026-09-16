"""Cyberpunk / Matrix high-contrast theme and visual badge formatters for Mesh-Deck.

Inspired by Hermes TUI, Claude CLI, and Aider aesthetics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from rich.theme import Theme

# Cyberpunk / Matrix Color Palette
THEME_COLORS: Final[dict[str, str]] = {
    "neon_green": "#00ff66",  # Matrix glowing green (strong signals, online, success)
    "neon_cyan": "#00f3ff",   # Cyberpunk electric cyan (primary accents, titles, local node)
    "neon_magenta": "#ff007f",# High-contrast hot fuchsia (routers, DMs, alerts)
    "neon_yellow": "#ffb800", # Amber/Gold (warnings, medium battery, repeaters)
    "neon_red": "#ff3366",    # Alert red (critical battery, weak SNR, errors)
    "neon_purple": "#9d4edd", # Deep electric violet (special roles, keys)
    "dim_gray": "#64748b",    # Slate gray for secondary text and units
    "border": "#00f3ff",      # Panel border accent
    "border_dim": "#334155",  # Table separator border
    "bg_dark": "#0a0e17",     # Deep void dark background
    "text_bright": "#f8fafc", # Bright white foreground
    # Semantic aliases
    "primary": "#00f3ff",
    "secondary": "#00ff66",
    "accent": "#ff007f",
    "warning": "#ffb800",
    "alert": "#ff3366",
    "muted": "#64748b",
    "magenta": "#ff007f",
}

CYBERPUNK_THEME: Final[Theme] = Theme({
    "mesh.cyan": "bold #00f3ff",
    "mesh.green": "bold #00ff66",
    "mesh.magenta": "bold #ff007f",
    "mesh.yellow": "bold #ffb800",
    "mesh.red": "bold #ff3366",
    "mesh.purple": "bold #9d4edd",
    "mesh.dim": "#64748b",
    "mesh.border": "#00f3ff",
    "mesh.border_dim": "#334155",
    "mesh.title": "bold #00f3ff",
    "mesh.local": "bold #00ff66",
    "mesh.header": "bold #00f3ff",
    "mesh.badge": "bold black on #00f3ff",
    "mesh.warning": "bold #ffb800",
    "mesh.error": "bold #ff3366",
    "mesh.success": "bold #00ff66",
    "mesh.text": "#f8fafc",
})


def format_snr(snr: float | None) -> str:
    """Format Signal-to-Noise Ratio (SNR) in dB with color coding.

    - >= 5 dB: Bright Green (strong signal)
    - 0..5 dB: Bright Cyan (good signal)
    - -10..0 dB: Yellow / Amber (marginal signal)
    - < -10 dB: Red (weak / critical signal)
    - None: Dim placeholder
    """
    if snr is None:
        return "[dim]-- dB[/dim]"

    if snr >= 5.0:
        return f"[bold #00ff66]+{snr:.1f} dB[/bold #00ff66]"
    elif snr >= 0.0:
        return f"[bold #00f3ff]+{snr:.1f} dB[/bold #00f3ff]"
    elif snr >= -10.0:
        return f"[bold #ffb800]{snr:.1f} dB[/bold #ffb800]"
    else:
        return f"[bold #ff3366]{snr:.1f} dB[/bold #ff3366]"


def format_battery(level: int | None, voltage: float | None) -> str:
    """Format battery percentage and voltage with state indicator.

    - > 70%: Green
    - 30-70%: Yellow
    - < 30%: Red
    - Powered/Charging (> 100% or high voltage without battery): ⚡ icon
    """
    if level is None and voltage is None:
        return "[dim]--[/dim]"

    # External USB power indicator
    if level is not None and level > 100:
        volt_str = f" ({voltage:.2f}V)" if voltage is not None else ""
        return f"[bold #00ff66]⚡ USB{volt_str}[/bold #00ff66]"

    if level is not None:
        volt_str = f" ({voltage:.2f}V)" if voltage is not None else ""
        if level > 70:
            return f"[bold #00ff66]{level}%{volt_str}[/bold #00ff66]"
        elif level >= 30:
            return f"[bold #ffb800]{level}%{volt_str}[/bold #ffb800]"
        else:
            return f"[bold #ff3366]{level}%{volt_str}[/bold #ff3366]"

    # Only voltage available
    if voltage is not None:
        if voltage >= 4.20:
            return f"[bold #00ff66]⚡ {voltage:.2f}V[/bold #00ff66]"
        elif voltage >= 3.85:
            return f"[bold #00ff66]{voltage:.2f}V[/bold #00ff66]"
        elif voltage >= 3.65:
            return f"[bold #ffb800]{voltage:.2f}V[/bold #ffb800]"
        else:
            return f"[bold #ff3366]{voltage:.2f}V[/bold #ff3366]"

    return "[dim]--[/dim]"


def format_role(role: str) -> str:
    """Format Meshtastic device role with pill badge markup."""
    role_clean = role.upper().strip() if role else "CLIENT"

    badge_map = {
        "ROUTER": "[bold black on #ff007f] ROUTER [/bold black on #ff007f]",
        "ROUTER_CLIENT": "[bold black on #d946ef] ROUTER_CLI [/bold black on #d946ef]",
        "REPEATER": "[bold black on #ffb800] REPEATER [/bold black on #ffb800]",
        "CLIENT": "[bold black on #00ff66] CLIENT [/bold black on #00ff66]",
        "CLIENT_MUTE": "[bold black on #94a3b8] CLI_MUTE [/bold black on #94a3b8]",
        "TRACKER": "[bold black on #00f3ff] TRACKER [/bold black on #00f3ff]",
        "SENSOR": "[bold black on #38bdf8] SENSOR [/bold black on #38bdf8]",
        "TAK": "[bold black on #f97316] TAK [/bold black on #f97316]",
        "TAK_TRACKER": "[bold black on #f97316] TAK_TRACK [/bold black on #f97316]",
        "LOST_AND_FOUND": "[bold black on #ec4899] LOST&FOUND [/bold black on #ec4899]",
    }

    return badge_map.get(
        role_clean,
        f"[bold white on #475569] {role_clean} [/bold white on #475569]",
    )


def format_time_ago(dt: datetime | None) -> str:
    """Format datetime relative to now as 'Xs fa', 'Xm fa', 'Xh fa', 'Xd fa'."""
    if dt is None:
        return "[dim]mai[/dim]"

    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = (now - dt).total_seconds()

    if diff < 0:
        diff = 0

    if diff < 60:
        return f"[bold #00ff66]{int(diff)}s fa[/bold #00ff66]"
    elif diff < 3600:
        return f"[bold #00f3ff]{int(diff // 60)}m fa[/bold #00f3ff]"
    elif diff < 86400:
        return f"[#ffb800]{int(diff // 3600)}h fa[/#ffb800]"
    else:
        return f"[dim]{int(diff // 86400)}d fa[/dim]"


def format_hops(hops: int | None) -> str:
    """Format hops count as 'Diretto (0)' or 'N hops'."""
    if hops is None:
        return "[dim]--[/dim]"

    if hops == 0:
        return "[bold #00ff66]Diretto (0)[/bold #00ff66]"
    elif hops == 1:
        return "[bold #00f3ff]1 hop[/bold #00f3ff]"
    else:
        return f"[#ffb800]{hops} hops[/#ffb800]"


def format_distance(dist_km: float | None) -> str:
    """Format distance in meters or kilometers."""
    if dist_km is None:
        return "[dim]--[/dim]"

    if dist_km < 1.0:
        return f"{int(dist_km * 1000)} m"
    elif dist_km < 10.0:
        return f"{dist_km:.2f} km"
    else:
        return f"{dist_km:.1f} km"
