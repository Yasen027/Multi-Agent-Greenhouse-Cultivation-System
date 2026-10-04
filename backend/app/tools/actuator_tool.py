"""Compatibility wrapper for the safety-gated MQTT actuator dispatcher."""

from .actuator_dispatch import dispatch_commands

__all__ = ['dispatch_commands']
