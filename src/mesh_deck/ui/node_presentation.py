"""Shared node display values for Rich tables, Textual lists, and explorer rows."""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text

from mesh_deck.models import NodeData
from mesh_deck.ui.theme import (
    format_battery,
    format_distance,
    format_hops,
    format_role,
    format_snr,
    format_time_ago,
)


def plain_markup(markup: str) -> str:
    """Convert a Rich-markup value to plain text for Textual DataTable cells."""
    return Text.from_markup(markup).plain


@dataclass(frozen=True)
class NodePresentation:
    """One node's canonical formatted values across every UI surface."""

    node_id: str
    name: str
    long_name: str
    aka: str
    hardware: str
    role: str
    role_markup: str
    snr_markup: str
    snr_text: str
    hops_markup: str
    hops_text: str
    battery_markup: str
    battery_text: str
    distance_markup: str
    distance_text: str
    last_heard_markup: str
    last_heard_text: str


def present_node(
    node: NodeData,
    *,
    lang: str,
    distance_km: float | None = None,
) -> NodePresentation:
    """Build consistent identity, metric, and time values for one node.

    ``distance_km`` is optional because the explorer can compute a fresh value
    relative to its own local-node snapshot, while other surfaces use the
    cached distance maintained by ``NodeStore``.
    """
    effective_distance = node.distance_km if distance_km is None else distance_km
    snr_markup = format_snr(node.snr)
    hops_markup = format_hops(node.hops_away, lang)
    battery_markup = format_battery(node.battery_level, node.voltage)
    distance_markup = format_distance(effective_distance)
    last_heard_markup = format_time_ago(node.last_heard, lang)

    return NodePresentation(
        node_id=node.id,
        name=node.display_name,
        long_name=node.long_name or node.display_name or node.id,
        aka=node.aka,
        hardware=node.hardware or "UNSET",
        role=node.role,
        role_markup=format_role(node.role),
        snr_markup=snr_markup,
        snr_text=plain_markup(snr_markup),
        hops_markup=hops_markup,
        hops_text=plain_markup(hops_markup),
        battery_markup=battery_markup,
        battery_text=plain_markup(battery_markup),
        distance_markup=distance_markup,
        distance_text=plain_markup(distance_markup),
        last_heard_markup=last_heard_markup,
        last_heard_text=plain_markup(last_heard_markup),
    )
