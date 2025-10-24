"""Slash Commands Module for Neoai Workflow Service.

This module handles processing messages that begin with a slash (/) character, mapping them to predefined commands
configured in YAML files.
"""

from neoai_workflow_service.slash_commands.processor import SlashCommandsProcessor

__all__ = ["SlashCommandsProcessor"]
