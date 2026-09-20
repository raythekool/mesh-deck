"""Cyberpunk / Matrix high-contrast theme and visual badge formatters for Mesh-Deck.

Inspired by Hermes TUI, Claude CLI, and Aider aesthetics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from rich.theme import Theme

from mesh_deck.i18n import t

# High-Contrast Cyberpunk / Matrix Color Palette (No low-contrast dark pink)
THEME_COLORS: Final[dict[str, str]] = {
    "neon_green": "#00ff66",  # Matrix glowing green (strong signals, online, success)
    "neon_cyan": "#00f3ff",   # Cyberpunk electric cyan (primary accents, titles, local node)
    "neon_magenta": "#c084fc",# Bright luminous violet / lavender (high-contrast DMs, alerts)
    "neon_amber": "#ffb800",  # High-contrast golden amber (accent, warnings, repeaters)
    "neon_yellow": "#ffb800", # Amber/Gold (warnings, medium battery, repeaters)
    "neon_red": "#ff3366",    # Alert red (critical battery, weak SNR, errors)
    "neon_purple": "#7c3aed", # Deep rich purple (routers, special roles)
    "dim_gray": "#94a3b8",    # Slate gray for secondary text and units
    "border": "#00f3ff",      # Panel border accent
    "border_dim": "#334155",  # Table separator border
    "bg_dark": "#0a0e17",     # Deep void dark background
    "text_bright": "#f8fafc", # Bright white foreground
    # Semantic aliases
    "primary": "#00f3ff",     # Electric cyan
    "secondary": "#00ff66",   # Neon green
    "accent": "#ffb800",      # Bright golden amber (high readability!)
    "warning": "#ffb800",     # Amber
    "alert": "#ff3366",       # Bright coral/red
    "muted": "#94a3b8",       # Readable light slate
    "magenta": "#c084fc",     # Bright luminous violet
}

THEMES: Final[dict[str, dict[str, str]]] = {
    "cyberpunk": THEME_COLORS,
    "high_contrast": {
        **THEME_COLORS,
        "primary": "#38bdf8",
        "secondary": "#4ade80",
        "accent": "#facc15",
        "muted": "#cbd5e1",
        "border": "#38bdf8",
    },
    "amber": {
        **THEME_COLORS,
        "primary": "#ffb000",
        "secondary": "#ffd700",
        "accent": "#ffcc00",
        "warning": "#f59e0b",
        "alert": "#ef4444",
        "muted": "#d97706",
        "border": "#ffb000",
    },
    "matrix": {
        **THEME_COLORS,
        "primary": "#22c55e",
        "secondary": "#4ade80",
        "accent": "#86efac",
        "warning": "#eab308",
        "alert": "#f87171",
        "muted": "#16a34a",
        "border": "#22c55e",
    },
}

CYBERPUNK_THEME: Final[Theme] = Theme({
    "mesh.cyan": "bold #00f3ff",
    "mesh.green": "bold #00ff66",
    "mesh.magenta": "bold #c084fc",
    "mesh.yellow": "bold #ffb800",
    "mesh.red": "bold #ff3366",
    "mesh.purple": "bold #7c3aed",
    "mesh.dim": "#94a3b8",
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


import math


def format_snr(snr: float | None) -> str:
    """Format Signal-to-Noise Ratio (SNR) in dB with color coding.

    - >= 5 dB: Bright Green (strong signal)
    - 0..5 dB: Bright Cyan (good signal)
    - -10..0 dB: Yellow / Amber (marginal signal)
    - < -10 dB: Red (weak / critical signal)
    - None or NaN: Dim placeholder
    """
    if snr is None:
        return "[dim]-- dB[/dim]"

    try:
        val = float(snr)
    except (ValueError, TypeError):
        return "[dim]-- dB[/dim]"

    if math.isnan(val):
        return "[dim]-- dB[/dim]"

    if math.isinf(val):
        if val > 0:
            return "[bold #00ff66]+inf dB[/bold #00ff66]"
        else:
            return "[bold #ff3366]-inf dB[/bold #ff3366]"

    if val >= 5.0:
        return f"[bold #00ff66]+{val:.1f} dB[/bold #00ff66]"
    elif val >= 0.0:
        return f"[bold #00f3ff]+{val:.1f} dB[/bold #00f3ff]"
    elif val >= -10.0:
        return f"[bold #ffb800]{val:.1f} dB[/bold #ffb800]"
    else:
        return f"[bold #ff3366]{val:.1f} dB[/bold #ff3366]"


def format_battery(level: int | None, voltage: float | None) -> str:
    """Format battery percentage and voltage with state indicator.

    - > 70%: Green
    - 30-70%: Yellow
    - < 30%: Red
    - Powered/Charging (> 100% or high voltage without battery): ⚡ icon
    """
    if level is None and voltage is None:
        return "[dim]--[/dim]"

    # Clean and validate voltage
    valid_voltage: float | None = None
    if voltage is not None:
        try:
            v = float(voltage)
            if not math.isnan(v) and not math.isinf(v) and v >= 0:
                valid_voltage = v
        except (ValueError, TypeError):
            valid_voltage = None

    # External USB power indicator
    if level is not None and level > 100:
        volt_str = f" ({valid_voltage:.2f}V)" if valid_voltage is not None else ""
        return f"[bold #00ff66]⚡ USB{volt_str}[/bold #00ff66]"

    if level is not None:
        try:
            lvl = int(level)
        except (ValueError, TypeError):
            lvl = 0

        volt_str = f" ({valid_voltage:.2f}V)" if valid_voltage is not None else ""
        if lvl > 70:
            return f"[bold #00ff66]{lvl}%{volt_str}[/bold #00ff66]"
        elif lvl >= 30:
            return f"[bold #ffb800]{lvl}%{volt_str}[/bold #ffb800]"
        else:
            return f"[bold #ff3366]{lvl}%{volt_str}[/bold #ff3366]"

    # Only voltage available
    if valid_voltage is not None:
        if valid_voltage >= 4.20:
            return f"[bold #00ff66]⚡ {valid_voltage:.2f}V[/bold #00ff66]"
        elif valid_voltage >= 3.85:
            return f"[bold #00ff66]{valid_voltage:.2f}V[/bold #00ff66]"
        elif valid_voltage >= 3.65:
            return f"[bold #ffb800]{valid_voltage:.2f}V[/bold #ffb800]"
        else:
            return f"[bold #ff3366]{valid_voltage:.2f}V[/bold #ff3366]"

    return "[dim]--[/dim]"


def format_role(role: str | None) -> str:
    """Format Meshtastic device role with pill badge markup."""
    if role is None:
        role_clean = "CLIENT"
    else:
        role_clean = str(role).upper().strip()
    if not role_clean:
        role_clean = "CLIENT"

    badge_map = {
        "ROUTER": "[bold white on #7c3aed] ROUTER [/bold white on #7c3aed]",
        "ROUTER_CLIENT": "[bold white on #6366f1] ROUTER_CLI [/bold white on #6366f1]",
        "REPEATER": "[bold black on #ffb800] REPEATER [/bold black on #ffb800]",
        "CLIENT": "[bold black on #00ff66] CLIENT [/bold black on #00ff66]",
        "CLIENT_MUTE": "[bold white on #64748b] CLIENT_MUTE [/bold white on #64748b]",
        "TRACKER": "[bold black on #00f3ff] TRACKER [/bold black on #00f3ff]",
        "SENSOR": "[bold black on #38bdf8] SENSOR [/bold black on #38bdf8]",
        "TAK": "[bold black on #f97316] TAK [/bold black on #f97316]",
        "TAK_TRACKER": "[bold black on #f97316] TAK_TRACK [/bold black on #f97316]",
        "LOST_AND_FOUND": "[bold white on #0284c7] LOST&FOUND [/bold white on #0284c7]",
    }

    return badge_map.get(
        role_clean,
        f"[bold white on #475569] {role_clean} [/bold white on #475569]",
    )


def format_time_ago(dt: datetime | None, lang: str = "it") -> str:
    """Format datetime relative to now as 'Xs fa', 'Xm fa', 'Xh fa', 'Xd fa' (or English equivalents)."""
    if dt is None:
        return f"[dim]{t('TIME_AGO_NEVER', lang)}[/dim]"

    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = (now - dt).total_seconds()

    if diff < 0:
        diff = 0

    if diff < 60:
        return f"[bold #00ff66]{int(diff)}{t('TIME_AGO_SUFFIX_SEC', lang)}[/bold #00ff66]"
    elif diff < 3600:
        return f"[bold #00f3ff]{int(diff // 60)}{t('TIME_AGO_SUFFIX_MIN', lang)}[/bold #00f3ff]"
    elif diff < 86400:
        return f"[#ffb800]{int(diff // 3600)}{t('TIME_AGO_SUFFIX_HOUR', lang)}[/#ffb800]"
    else:
        return f"[dim]{int(diff // 86400)}{t('TIME_AGO_SUFFIX_DAY', lang)}[/dim]"


def format_hops(hops: int | None, lang: str = "it") -> str:
    """Format hops count as 'Diretto (0)'/'Direct (0)' or 'N hops'."""
    if hops is None:
        return "[dim]--[/dim]"

    if hops == 0:
        return f"[bold #00ff66]{t('HOPS_DIRECT', lang)} (0)[/bold #00ff66]"
    elif hops == 1:
        return "[bold #00f3ff]1 hop[/bold #00f3ff]"
    else:
        return f"[#ffb800]{hops} hops[/#ffb800]"


def format_distance(dist_km: float | None) -> str:
    """Format distance in meters or kilometers."""
    if dist_km is None:
        return "[dim]--[/dim]"

    try:
        val = float(dist_km)
    except (ValueError, TypeError):
        return "[dim]--[/dim]"

    if math.isnan(val) or math.isinf(val) or val < 0:
        return "[dim]--[/dim]"

    if val < 1.0:
        return f"{int(val * 1000)} m"
    elif val < 10.0:
        return f"{val:.2f} km"
    else:
        return f"{val:.1f} km"
