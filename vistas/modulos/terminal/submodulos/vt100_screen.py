# -*- coding: utf-8 -*-
"""
Emulador ligero de pantalla VT100/ANSI para programas TUI interactivos
(nano, vim, htop, less, mc, raspi-config) dentro de QTextEdit.
"""

import re


class VT100ScreenBuffer:
    """Mantiene una matriz de caracteres rows x cols y el estado de pantalla alternativa."""

    _CSI_RE = re.compile(r"\x1b\[([0-9;:<=>?]*)([ -/]*)([@-~])")
    _OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

    def __init__(self, rows: int = 26, cols: int = 96):
        self.rows = max(10, rows)
        self.cols = max(40, cols)
        self.in_alt_screen = False
        self.saved_normal_text = ""
        self.row = 0
        self.col = 0
        self.grid = [[" "] * self.cols for _ in range(self.rows)]

    def resize(self, rows: int, cols: int):
        rows = max(10, rows)
        cols = max(40, cols)
        if rows == self.rows and cols == self.cols:
            return
        new_grid = [[" "] * cols for _ in range(rows)]
        for r in range(min(self.rows, rows)):
            for c in range(min(self.cols, cols)):
                new_grid[r][c] = self.grid[r][c]
        self.rows, self.cols = rows, cols
        self.grid = new_grid
        self.row = min(self.row, self.rows - 1)
        self.col = min(self.col, self.cols - 1)

    def clear_all(self):
        self.grid = [[" "] * self.cols for _ in range(self.rows)]
        self.row = 0
        self.col = 0

    def enter_alt_screen(self):
        if not self.in_alt_screen:
            self.in_alt_screen = True
            self.clear_all()

    def exit_alt_screen(self):
        self.in_alt_screen = False

    def _put_char(self, ch: str):
        if self.col >= self.cols:
            self.col = 0
            self._newline()
        if 0 <= self.row < self.rows and 0 <= self.col < self.cols:
            self.grid[self.row][self.col] = ch
        self.col += 1

    def _newline(self):
        if self.row < self.rows - 1:
            self.row += 1
        else:
            self.grid.pop(0)
            self.grid.append([" "] * self.cols)

    def _handle_csi(self, params_str: str, final: str):
        # Modos privados DEC (?1049h / ?1049l / ?47h / ?47l)
        if params_str.startswith("?"):
            codes = params_str[1:].split(";")
            if final == "h" and any(c in ("1049", "47", "1047") for c in codes):
                self.enter_alt_screen()
            elif final == "l" and any(c in ("1049", "47", "1047") for c in codes):
                self.exit_alt_screen()
            return

        parts = [int(p) if p.isdigit() else 0 for p in params_str.split(";")] if params_str else []
        n1 = parts[0] if len(parts) >= 1 and parts[0] > 0 else 1
        n2 = parts[1] if len(parts) >= 2 and parts[1] > 0 else 1

        if final in ("H", "f"):
            self.row = max(0, min(self.rows - 1, n1 - 1))
            self.col = max(0, min(self.cols - 1, n2 - 1))
        elif final == "A":
            self.row = max(0, self.row - n1)
        elif final == "B":
            self.row = min(self.rows - 1, self.row + n1)
        elif final == "C":
            self.col = min(self.cols - 1, self.col + n1)
        elif final == "D":
            self.col = max(0, self.col - n1)
        elif final == "G":
            self.col = max(0, min(self.cols - 1, n1 - 1))
        elif final == "d":
            self.row = max(0, min(self.rows - 1, n1 - 1))
        elif final == "J":
            mode = parts[0] if parts else 0
            if mode in (2, 3):
                self.clear_all()
            elif mode == 0:
                for c in range(self.col, self.cols):
                    self.grid[self.row][c] = " "
                for r in range(self.row + 1, self.rows):
                    self.grid[r] = [" "] * self.cols
        elif final == "K":
            mode = parts[0] if parts else 0
            if mode == 0:
                for c in range(self.col, self.cols):
                    self.grid[self.row][c] = " "
            elif mode == 1:
                for c in range(0, min(self.cols, self.col + 1)):
                    self.grid[self.row][c] = " "
            elif mode == 2:
                self.grid[self.row] = [" "] * self.cols

    def feed(self, text: str):
        """Procesa un chunk ANSI crudo actualizando la matriz virtual."""
        text = self._OSC_RE.sub("", text)
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\x1b":
                if i + 1 < n and text[i + 1] == "[":
                    m = self._CSI_RE.match(text, i)
                    if m:
                        self._handle_csi(m.group(1), m.group(3))
                        i = m.end()
                        continue
                # Otra secuencia ESC de 2 caracteres (ej. ESC =, ESC >, ESC ( B)
                if i + 1 < n and text[i + 1] in ("(", ")", "#", "*"):
                    i += 3
                    continue
                i += 2
                continue
            elif ch == "\r":
                self.col = 0
            elif ch == "\n":
                self._newline()
            elif ch == "\b":
                self.col = max(0, self.col - 1)
            elif ch == "\t":
                next_tab = min(self.cols - 1, ((self.col // 8) + 1) * 8)
                self.col = next_tab
            elif ch >= " ":
                self._put_char(ch)
            i += 1

    def render(self) -> str:
        return "\n".join("".join(r).rstrip() for r in self.grid)

    def cursor_char_offset(self) -> int:
        lines = ["".join(r).rstrip() for r in self.grid]
        row = min(max(0, self.row), max(0, len(lines) - 1))
        offset = sum(len(lines[r]) + 1 for r in range(row))
        col_limit = len(lines[row]) if lines else 0
        return offset + min(max(0, self.col), col_limit)
