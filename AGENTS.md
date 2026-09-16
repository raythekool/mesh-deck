# Mesh-Deck Agent Guide

## Workflow

- Use `uv` for all project commands. Run the relevant focused test first, then
  run `uv run python -m unittest discover -s tests` before finishing changes.
- Test modules use the standard library `unittest`; add coverage beside the
  owning layer in `tests/test_core.py`, `tests/test_commands.py`, or
  `tests/test_ui.py`.
- Keep changes scoped. Do not require a physical Meshtastic radio for tests;
  use mocks or fixtures for serial and PubSub behavior.

## Architecture

- Keep hardware and state logic in `src/mesh_deck/core/`, command parsing in
  `src/mesh_deck/commands/`, and presentation in `src/mesh_deck/ui/`.
- `NodeStore` and `RadioClient` can receive updates from background PubSub
  threads. Preserve locking and defensive handling of incomplete radio data.
- The primary console is Textual. Route background-originated UI updates
  through `TextualConsole` and `app.call_from_thread()`; do not mutate Textual
  widgets directly from radio callbacks.
- Execute potentially blocking command work outside Textual's UI event loop.

## UI And Settings

- Keep Rich renderables for tables, panels, and message formatting; use Textual
  widgets and screens for interaction. `/view` must push an internal screen,
  not start a nested `App`.
- User settings live in `~/.config/mesh-deck/settings.json`. Preserve bounded
  command history and support `it` and `en` via `mesh_deck.i18n.t()`.
- Add user-visible UI strings to `i18n.py` when touching Textual surfaces.

## References

- Read [README.md](README.md) for commands and quick start,
  [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for user-facing behavior, and
  [REQUIREMENTS.md](REQUIREMENTS.md) for the supported feature scope.