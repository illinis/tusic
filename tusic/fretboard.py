"""A scalable diagram driven entirely by the selected instrument definition."""

import tkinter as tk

from .music import Instrument, Position


class Fretboard(tk.Canvas):
    def __init__(self, parent, instrument: Instrument, **kwargs):
        super().__init__(parent, background="white", highlightthickness=1,
                         highlightbackground="#b8b8b8", height=260, **kwargs)
        self.instrument = instrument
        self.position: Position | None = None
        self.answer_label: str | None = None
        self.correct: bool | None = None
        self.bind("<Configure>", lambda _event: self.redraw())
        self.redraw()

    def set_question(self, position: Position, answer_label: str | None = None,
                     correct: bool | None = None) -> None:
        self.position, self.answer_label, self.correct = position, answer_label, correct
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        width, height = max(self.winfo_width(), 300), max(self.winfo_height(), 170)
        instrument = self.instrument
        left, right, top, bottom = 128, width - 30, 42, height - 48
        step = (right - left) / instrument.fret_count
        string_gap = (bottom - top) / max(1, instrument.string_count - 1)
        string_y = lambda number: ((top + bottom) / 2 if instrument.string_count == 1
                                   else top + (number - 1) * string_gap)
        def fret_x(fret):
            if not instrument.fretted:
                # Fretless pitches sit ON the semitone guides, not between them.
                return left + fret * step
            return left - 24 if fret == 0 else left + (fret - 0.5) * step

        self.centres = {Position(number, fret): (fret_x(fret), string_y(number))
                        for number in range(1, instrument.string_count + 1)
                        for fret in range(instrument.fret_count + 1)}
        self.cell_size = (step, string_gap)

        self.create_rectangle(left, top - 12, right, bottom + 12, fill="#faf8f2", outline="")
        for fret in set(instrument.markers) | set(instrument.double_markers):
            x = fret_x(fret)
            self.create_rectangle(left + (fret - 1) * step, top - 12,
                                  left + fret * step, bottom + 12,
                                  fill="#eeeeea", outline="")
            marker_y = ((top + bottom) / 2,)
            if fret in instrument.double_markers:
                marker_y = (top + (bottom - top) * 0.28, top + (bottom - top) * 0.72)
            for y in marker_y:
                self.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#aaa99e", outline="")

        # Real frets are solid; fretless instruments use dotted position guides.
        for fret in range(instrument.fret_count + 1):
            x = left + fret * step
            self.create_line(x, top - 12, x, bottom + 12,
                             fill="#555555" if instrument.fretted else "#aaaaaa",
                             width=4 if fret == 0 else 1,
                             dash=() if instrument.fretted or fret == 0 else (2, 4))
        self.create_text(26, 17, text="STRING", font=("TkDefaultFont", 8), fill="#555555")
        self.create_text(64, 17, text="NOTE", font=("TkDefaultFont", 8), fill="#555555")
        self.create_text(fret_x(0), height - 24, text="Open\n0", font=("TkDefaultFont", 9))
        if not instrument.fretted:
            self.create_text((left + right) / 2, 17, text="SEMITONES ABOVE OPEN · DOTTED GUIDES, NO FRETS",
                             font=("TkDefaultFont", 9), fill="#555555")
        for fret in range(1, instrument.fret_count + 1):
            self.create_text(fret_x(fret), height - 22, text=str(fret),
                             font=("TkDefaultFont", 10, "bold" if fret in instrument.markers else "normal"))
        for number in range(1, instrument.string_count + 1):
            y = string_y(number)
            self.create_line(left - 43, y, right, y, fill="#555555",
                             width=1 + 2 * (number - 1) / max(1, instrument.string_count - 1))
            self.create_text(26, y, text=str(number), font=("TkDefaultFont", 10))
            self.create_text(64, y, text=instrument.tuning[-number][:-1],
                             font=("TkDefaultFont", 10, "bold"), tags="open-string-note")

        if self.position:
            x, y = fret_x(self.position.fret), string_y(self.position.string_number)
            radius = min(17, step * 0.43, string_gap * 0.43)
            radius = max(9, radius)
            fill = "#245cb3" if self.correct is None else "#24653b" if self.correct else "#a52f29"
            self.create_oval(x - radius, y - radius, x + radius, y + radius,
                             fill=fill, outline="white", width=2)
            self.create_text(x, y, text=self.answer_label or "?", fill="white",
                             font=("TkDefaultFont", 10, "bold"))


class SelectionFretboard(Fretboard):
    """Clickable multi-note diagram for mapping a scale onto any instrument."""

    def __init__(self, parent, instrument, first, last, note_labels, on_change):
        self.first, self.last = first, last
        self.selected = set()
        self.expected = None
        self.note_labels, self.on_change = note_labels, on_change
        super().__init__(parent, instrument)
        self.bind("<Button-1>", self.select_at)

    def redraw(self):
        super().redraw()
        radius = max(8, min(16, self.cell_size[0] * 0.40, self.cell_size[1] * 0.40))
        for position, (x, y) in self.centres.items():
            if not self.first <= position.fret <= self.last:
                continue
            selected = position in self.selected
            fill, outline, label = ("#245cb3", "#245cb3", "") if selected else ("white", "#9da5af", "")
            if self.expected is not None:
                expected = position in self.expected
                if expected or selected:
                    fill = "#24653b" if expected and selected else "#a52f29" if selected else "#98620b"
                    outline = fill
                    label = self.note_labels.get(self.instrument.pitch_at(position), "×")
            self.create_oval(x-radius, y-radius, x+radius, y+radius, fill=fill, outline=outline, width=2)
            if label:
                self.create_text(x, y, text=label, fill="white", font=("TkDefaultFont", 9, "bold"))

    def select_at(self, event):
        if self.expected is not None:
            return
        for position, (x, y) in self.centres.items():
            if (self.first <= position.fret <= self.last and
                    abs(event.x-x) <= self.cell_size[0]*0.45 and abs(event.y-y) <= self.cell_size[1]*0.40):
                if position in self.selected:
                    self.selected.remove(position)
                else:
                    self.selected.add(position)
                self.redraw()
                self.on_change(len(self.selected))
                return

    def show_feedback(self, expected):
        self.expected = expected
        self.redraw()
