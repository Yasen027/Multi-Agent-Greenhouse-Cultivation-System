"""Backward-compatible import path for the crop identification agent."""

from ..crop_identification_agent import CROP_HINTS, build_prompt, evaluate, identify_crop

__all__ = ['CROP_HINTS', 'build_prompt', 'evaluate', 'identify_crop']
