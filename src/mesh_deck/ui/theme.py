"""Theme palettes and visual badge formatters for Mesh-Deck.

A single *active* palette (``THEME_COLORS``) drives every Rich renderable and,
through :func:`css_variables`, every Textual stylesheet. ``THEME_COLORS`` is
mutated in place by :func:`set_theme` so modules that did
``from ... import THEME_COLORS`` keep seeing the current theme.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Final

from mesh_deck.i18n import t

DEFAULT_THEME: Final[str] = "cyberpunk"

# Every theme defines the same semantic keys; nothing is inherited between
# themes so a palette can never end up half-applied.
THEMES: Final[dict[str, dict[str, str]]] = {
    # Neon cyan/green on deep void: the original Mesh-Deck identity.
    "cyberpunk": {
        "bg": "#081018",
        "bg_panel": "#0b1720",
        "bg_elevated": "#10212b",
        "bg_header": "#063b46",
        "primary": "#00f3ff",
        "secondary": "#00ff66",
        "accent": "#ffb800",
        "warning": "#ffb800",
        "alert": "#ff3366",
        "magenta": "#c084fc",
        "purple": "#7c3aed",
        "border": "#00f3ff",
        "border_soft": "#1f8794",
        "border_dim": "#334155",
        "text": "#e8f1f5",
        "muted": "#94a3b8",
    },
    # Tokyo-Night inspired: low-glare indigo with soft blues and violets.
    "midnight": {
        "bg": "#1a1b26",
        "bg_panel": "#1f2335",
        "bg_elevated": "#24283b",
        "bg_header": "#2f3549",
        "primary": "#7aa2f7",
        "secondary": "#9ece6a",
        "accent": "#e0af68",
        "warning": "#e0af68",
        "alert": "#f7768e",
        "magenta": "#bb9af7",
        "purple": "#9d7cd8",
        "border": "#7aa2f7",
        "border_soft": "#414868",
        "border_dim": "#3b4261",
        "text": "#c0caf5",
        "muted": "#7f8bb5",
    },
    # Nord: cool arctic palette, easiest on the eyes for long sessions.
    "nord": {
        "bg": "#2e3440",
        "bg_panel": "#3b4252",
        "bg_elevated": "#434c5e",
        "bg_header": "#4c566a",
        "primary": "#88c0d0",
        "secondary": "#a3be8c",
        "accent": "#ebcb8b",
        "warning": "#ebcb8b",
        "alert": "#bf616a",
        "magenta": "#b48ead",
        "purple": "#b48ead",
        "border": "#88c0d0",
        "border_soft": "#5e81ac",
        "border_dim": "#4c566a",
        "text": "#eceff4",
        "muted": "#9aa5b8",
    },
    # Ember: warm amber/coral on charcoal, a modern take on phosphor terminals.
    "ember": {
        "bg": "#14100e",
        "bg_panel": "#1d1714",
        "bg_elevated": "#2a211c",
        "bg_header": "#3a2c24",
        "primary": "#ffb454",
        "secondary": "#b8cc52",
        "accent": "#ff9940",
        "warning": "#ffd580",
        "alert": "#f07178",
        "magenta": "#ff7fa8",
        "purple": "#c792ea",
        "border": "#ff9940",
        "border_soft": "#7a5c44",
        "border_dim": "#4a3b32",
        "text": "#f5e6d8",
        "muted": "#a08c7d",
    },
}

# The live palette. Mutated in place by set_theme(); never rebound.
THEME_COLORS: dict[str, str] = dict(THEMES[DEFAULT_THEME])


def theme_names() -> list[str]:
    """Return the selectable theme identifiers, default first."""
    return [DEFAULT_THEME] + [name for name in THEMES if name != DEFAULT_THEME]


def set_theme(name: str | None) -> str:
    """Activate a palette by name, falling back to the default when unknown.

    Returns:
        The name of the theme that is now active.
    """
    resolved = name if name in THEMES else DEFAULT_THEME
    THEME_COLORS.clear()
    THEME_COLORS.update(THEMES[resolved])
    return resolved


def css_variables() -> dict[str, str]:
    """Expose the active palette to Textual stylesheets as ``$mesh-*``."""
    return {f"mesh-{key.replace('_', '-')}": value for key, value in THEME_COLORS.items()}


class ThemedApp:
    """Mixin adding the ``$mesh-*`` CSS variables to a Textual ``App``."""

    def get_css_variables(self) -> dict[str, str]:
        return {**super().get_css_variables(), **css_variables()}


def format_snr(snr: float | None) -> str:
    """Format Signal-to-Noise Ratio (SNR) in dB with color coding.

    - >= 5 dB: secondary (strong signal)
    - 0..5 dB: primary (good signal)
    - -10..0 dB: warning (marginal signal)
    - < -10 dB: alert (weak / critical signal)
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
            return f"[bold {THEME_COLORS['secondary']}]+inf dB[/bold {THEME_COLORS['secondary']}]"
        return f"[bold {THEME_COLORS['alert']}]-inf dB[/bold {THEME_COLORS['alert']}]"

    if val >= 5.0:
        color = THEME_COLORS["secondary"]
        sign = "+"
    elif val >= 0.0:
        color = THEME_COLORS["primary"]
        sign = "+"
    elif val >= -10.0:
        color = THEME_COLORS["warning"]
        sign = ""
    else:
        color = THEME_COLORS["alert"]
        sign = ""
    return f"[bold {color}]{sign}{val:.1f} dB[/bold {color}]"


def format_battery(level: int | None, voltage: float | None) -> str:
    """Format battery percentage and voltage with state indicator.

    - > 70%: secondary
    - 30-70%: warning
    - < 30%: alert
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

    volt_str = f" ({valid_voltage:.2f}V)" if valid_voltage is not None else ""
    good = THEME_COLORS["secondary"]

    # External USB power indicator
    if level is not None and level > 100:
        return f"[bold {good}]⚡ USB{volt_str}[/bold {good}]"

    if level is not None:
        try:
            lvl = int(level)
        except (ValueError, TypeError):
            lvl = 0

        if lvl > 70:
            color = good
        elif lvl >= 30:
            color = THEME_COLORS["warning"]
        else:
            color = THEME_COLORS["alert"]
        return f"[bold {color}]{lvl}%{volt_str}[/bold {color}]"

    # Only voltage available
    if valid_voltage is not None:
        if valid_voltage >= 4.20:
            return f"[bold {good}]⚡ {valid_voltage:.2f}V[/bold {good}]"
        if valid_voltage >= 3.85:
            color = good
        elif valid_voltage >= 3.65:
            color = THEME_COLORS["warning"]
        else:
            color = THEME_COLORS["alert"]
        return f"[bold {color}]{valid_voltage:.2f}V[/bold {color}]"

    return "[dim]--[/dim]"


def format_role(role: str | None) -> str:
    """Format Meshtastic device role with pill badge markup."""
    if role is None:
        role_clean = "CLIENT"
    else:
        role_clean = str(role).upper().strip()
    if not role_clean:
        role_clean = "CLIENT"

    def badge(label: str, background: str, foreground: str = "black") -> str:
        return f"[bold {foreground} on {background}] {label} [/bold {foreground} on {background}]"

    badge_map = {
        "ROUTER": badge("ROUTER", THEME_COLORS["purple"], "white"),
        "ROUTER_CLIENT": badge("ROUTER_CLI", THEME_COLORS["magenta"], "white"),
        "REPEATER": badge("REPEATER", THEME_COLORS["accent"]),
        "CLIENT": badge("CLIENT", THEME_COLORS["secondary"]),
        "CLIENT_MUTE": badge("CLIENT_MUTE", THEME_COLORS["muted"], "white"),
        "TRACKER": badge("TRACKER", THEME_COLORS["primary"]),
        "SENSOR": badge("SENSOR", THEME_COLORS["primary"]),
        "TAK": badge("TAK", THEME_COLORS["accent"]),
        "TAK_TRACKER": badge("TAK_TRACK", THEME_COLORS["accent"]),
        "LOST_AND_FOUND": badge("LOST&FOUND", THEME_COLORS["magenta"], "white"),
    }

    return badge_map.get(role_clean, badge(role_clean, THEME_COLORS["border_dim"], "white"))


def format_time_ago(dt: datetime | None, lang: str = "it") -> str:
    """Format datetime relative to now as 'Xs fa', 'Xm fa', 'Xh fa', 'Xd fa' (or English equivalents)."""
    if dt is None:
        return f"[dim]{t('TIME_AGO_NEVER', lang)}[/dim]"

    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = (now - dt).total_seconds()

    if diff < 0:
        diff = 0

    if diff < 60:
        color = THEME_COLORS["secondary"]
        return f"[bold {color}]{int(diff)}{t('TIME_AGO_SUFFIX_SEC', lang)}[/bold {color}]"
    if diff < 3600:
        color = THEME_COLORS["primary"]
        return f"[bold {color}]{int(diff // 60)}{t('TIME_AGO_SUFFIX_MIN', lang)}[/bold {color}]"
    if diff < 86400:
        color = THEME_COLORS["accent"]
        return f"[{color}]{int(diff // 3600)}{t('TIME_AGO_SUFFIX_HOUR', lang)}[/{color}]"
    return f"[dim]{int(diff // 86400)}{t('TIME_AGO_SUFFIX_DAY', lang)}[/dim]"


def format_hops(hops: int | None, lang: str = "it") -> str:
    """Format hops count as 'Diretto (0)'/'Direct (0)' or 'N hops'."""
    if hops is None:
        return "[dim]--[/dim]"

    if hops == 0:
        color = THEME_COLORS["secondary"]
        return f"[bold {color}]{t('HOPS_DIRECT', lang)} (0)[/bold {color}]"
    if hops == 1:
        color = THEME_COLORS["primary"]
        return f"[bold {color}]1 hop[/bold {color}]"
    color = THEME_COLORS["accent"]
    return f"[{color}]{hops} hops[/{color}]"


def format_bearing(bearing_deg: float | None) -> str:
    """Format a forward azimuth as degrees plus a 16-point compass abbreviation."""
    if bearing_deg is None:
        return "[dim]--[/dim]"

    try:
        val = float(bearing_deg)
    except (ValueError, TypeError):
        return "[dim]--[/dim]"

    if math.isnan(val) or math.isinf(val):
        return "[dim]--[/dim]"

    val %= 360.0
    points = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
    point = points[int((val + 11.25) % 360.0 // 22.5)]
    return f"{val:.0f}° {point}"


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
    if val < 10.0:
        return f"{val:.2f} km"
    return f"{val:.1f} km"
