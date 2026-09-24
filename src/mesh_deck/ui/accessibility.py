"""Palette accessibility helpers used by the theme quality gate."""

from __future__ import annotations

from collections.abc import Mapping


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG relative luminance contrast ratio for two #RRGGBB colours."""
    foreground_luminance = _relative_luminance(foreground)
    background_luminance = _relative_luminance(background)
    lighter, darker = sorted((foreground_luminance, background_luminance), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def palette_contrast_failures(palette: Mapping[str, str]) -> list[str]:
    """Return semantic palette violations for the terminal UI text surfaces.

    Primary state colours are used for readable labels and statuses, so they
    require 4.5:1 on both standard dark surfaces. Muted text is intentionally
    secondary but must still meet 3:1.
    """
    failures: list[str] = []
    for background_key in ("bg", "bg_panel"):
        background = palette[background_key]
        for role in ("text", "primary", "secondary", "warning", "alert"):
            ratio = contrast_ratio(palette[role], background)
            if ratio < 4.5:
                failures.append(f"{role} on {background_key}: {ratio:.2f}:1")
        muted_ratio = contrast_ratio(palette["muted"], background)
        if muted_ratio < 3.0:
            failures.append(f"muted on {background_key}: {muted_ratio:.2f}:1")
    return failures


def _relative_luminance(colour: str) -> float:
    if len(colour) != 7 or not colour.startswith("#"):
        raise ValueError(f"Expected a #RRGGBB colour, got {colour!r}.")
    channels = [int(colour[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
