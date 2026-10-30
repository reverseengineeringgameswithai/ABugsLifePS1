"""Canonical host-path resolution for ABL tools.

Resolves host-specific locations from environment variables, with portable
defaults (no hardcoded /home/<user>). Override by exporting the env var. (GAP-0003)
"""
import os

# Repo root = parent of this tools/ directory (portable; no hardcoded user path)
ABL_DIR = os.environ.get(
    "ABL_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
# The custom DuckStation fork checkout
DUCKSTATION_DIR = os.environ.get("DUCKSTATION_DIR", os.path.expanduser("~/duckstation"))
# DuckStation save-state directory
ABL_SAVESTATES = os.environ.get(
    "ABL_SAVESTATES", os.path.expanduser("~/.local/share/duckstation/savestates")
)
# The external-debugger Python client shipped with the fork
DEBUGGER_CLIENT = os.path.join(DUCKSTATION_DIR, "scripts", "debugger-client")
