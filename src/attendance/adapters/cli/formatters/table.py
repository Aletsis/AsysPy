"""Formateador de tablas para terminal sin dependencias externas."""

import re
from typing import Any, Sequence

from .colors import bold, cyan

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def visible_len(text: str) -> int:
    """Calcula la longitud visible de un string ignorando códigos de escape ANSI."""
    return len(_ANSI_ESCAPE.sub("", text))


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    alignments: Sequence[str] | None = None,
    ascii_only: bool = False,
) -> str:
    """Renderiza una lista de filas y cabeceras en formato de tabla de texto alineada.

    Args:
        headers: Lista de títulos de columna.
        rows: Lista de filas (cada una con el mismo número de columnas que headers).
        alignments: Lista de 'left', 'right' o 'center' para cada columna.
        ascii_only: Si es True, usa caracteres ASCII (+, -, |) en lugar de Unicode.
    """
    str_headers = [str(h) for h in headers]
    str_rows: list[list[str]] = [[str(cell) if cell is not None else "" for cell in row] for row in rows]

    num_cols = len(str_headers)
    if num_cols == 0:
        return ""

    if alignments is None:
        align_list = ["left"] * num_cols
    else:
        align_list = list(alignments)
        if len(align_list) < num_cols:
            align_list.extend(["left"] * (num_cols - len(align_list)))

    # Calcular anchos de columna basados en longitud visible
    col_widths = [visible_len(h) for h in str_headers]
    for row in str_rows:
        for idx in range(num_cols):
            cell_val = row[idx] if idx < len(row) else ""
            w = visible_len(cell_val)
            if w > col_widths[idx]:
                col_widths[idx] = w

    # Añadir 2 espacios de padding mínimo
    col_widths = [max(w, 1) for w in col_widths]

    # Caracteres de borde
    if ascii_only:
        tl, tm, tr = "+", "+", "+"
        ml, mm, mr = "+", "+", "+"
        bl, bm, br = "+", "+", "+"
        h_line = "-"
        v_line = "|"
    else:
        tl, tm, tr = "┌", "┬", "┐"
        ml, mm, mr = "├", "┼", "┤"
        bl, bm, br = "└", "┴", "┘"
        h_line = "─"
        v_line = "│"

    top_border = tl + tm.join(h_line * (w + 2) for w in col_widths) + tr
    sep_border = ml + mm.join(h_line * (w + 2) for w in col_widths) + mr
    bottom_border = bl + bm.join(h_line * (w + 2) for w in col_widths) + br

    def format_cell(text: str, width: int, align: str) -> str:
        vis_len = visible_len(text)
        pad = max(0, width - vis_len)
        if align == "right":
            return (" " * pad) + text
        elif align == "center":
            left_pad = pad // 2
            right_pad = pad - left_pad
            return (" " * left_pad) + text + (" " * right_pad)
        else:
            return text + (" " * pad)

    lines: list[str] = [top_border]

    # Fila de cabecera (en negrita y cian)
    header_cells = [
        f" {cyan(bold(format_cell(str_headers[i], col_widths[i], align_list[i])))} "
        for i in range(num_cols)
    ]
    lines.append(v_line + v_line.join(header_cells) + v_line)
    lines.append(sep_border)

    # Filas de datos
    for row in str_rows:
        cells = []
        for i in range(num_cols):
            val = row[i] if i < len(row) else ""
            cells.append(f" {format_cell(val, col_widths[i], align_list[i])} ")
        lines.append(v_line + v_line.join(cells) + v_line)

    lines.append(bottom_border)
    return "\n".join(lines)
