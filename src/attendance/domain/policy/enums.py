"""Enums para políticas laborales y de compensación."""

from enum import Enum


class RoundingMethod(str, Enum):
    NONE = "none"
    NEAREST = "nearest"
    ROUND_UP = "round_up"
    ROUND_DOWN = "round_down"
