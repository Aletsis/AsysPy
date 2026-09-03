"""Pruebas unitarias para los formateadores de la CLI (colores y tablas)."""

import os
from unittest.mock import patch

from attendance.adapters.cli.formatters.colors import (
    Colors,
    _supports_color,
    blue,
    bold,
    cyan,
    dim,
    green,
    red,
    yellow,
)
from attendance.adapters.cli.formatters.table import render_table, visible_len


def test_visible_len_strips_ansi() -> None:
    raw_text = "Hola Mundo"
    ansi_text = f"\033[31m{raw_text}\033[0m"
    assert visible_len(raw_text) == 10
    assert visible_len(ansi_text) == 10


def test_colors_when_no_color_env_set() -> None:
    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        assert _supports_color() is False
        assert red("texto") == "texto"
        assert green("texto") == "texto"
        assert bold("texto") == "texto"


def test_colors_when_supported() -> None:
    with patch.dict(os.environ, {}, clear=True), patch("sys.stdout.isatty", return_value=True):
        assert _supports_color() is True
        assert red("error") == f"{Colors.RED}error{Colors.RESET}"
        assert green("ok") == f"{Colors.GREEN}ok{Colors.RESET}"
        assert bold("titulo") == f"{Colors.BOLD}titulo{Colors.RESET}"
        assert yellow("alerta") == f"{Colors.YELLOW}alerta{Colors.RESET}"
        assert blue("info") == f"{Colors.BLUE}info{Colors.RESET}"
        assert cyan("header") == f"{Colors.CYAN}header{Colors.RESET}"
        assert dim("opaco") == f"{Colors.DIM}opaco{Colors.RESET}"


def test_render_table_unicode() -> None:
    headers = ["Nombre", "Edad", "Ciudad"]
    rows = [
        ["Alice", 30, "Madrid"],
        ["Bob", 25, "Barcelona"],
    ]
    table = render_table(headers, rows, alignments=["left", "right", "left"])
    assert "Alice" in table
    assert "Madrid" in table
    assert "┌" in table
    assert "└" in table
    assert "│" in table


def test_render_table_ascii() -> None:
    headers = ["ID", "Status"]
    rows = [["1", "OK"], ["2", "FAIL"]]
    table = render_table(headers, rows, ascii_only=True)
    assert "+" in table
    assert "|" in table
    assert "OK" in table
    assert "FAIL" in table


def test_render_table_empty() -> None:
    assert render_table([], []) == ""
