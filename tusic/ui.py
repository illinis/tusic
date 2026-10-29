"""Plain Tk/ttk screens. Music rules and disk storage live in separate modules."""

from pathlib import Path
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .fretboard import Fretboard
from .exercises import EXERCISES, ExerciseSession
from .learning_ui import LearningScreens
from .music import load_instruments, note_name, note_names
from .practice import PracticeSession
from .storage import (ScoreStore, Settings, SettingsStore, default_scores_directory,
                      ensure_writable_directory)


class TusicApp(LearningScreens, tk.Tk):
    def __init__(self, config_directory: Path | None = None, data_directory: Path | None = None):
        super().__init__()
        self.title("Tusic — Music practice")
        self.geometry("1020x720")
        self.minsize(860, 620)
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.settings_store = SettingsStore(config_directory.resolve() if config_directory else None)
        self.settings, settings_warning = self.settings_store.load()
        if data_directory:
            self.settings = Settings(data_directory.expanduser().resolve(), self.settings.spelling)
        self.score_store = ScoreStore(self.settings.scores_directory)
        self.instruments, warnings = load_instruments(self.settings_store.directory / "instruments")
        if settings_warning:
            warnings.insert(0, settings_warning)
        try:
            ensure_writable_directory(self.settings.scores_directory)
        except OSError as error:
            warnings.append(f"The score folder is unavailable: {error}\nChoose another folder in Settings.")
        self.session: PracticeSession | None = None
        self.saved_path: Path | None = None
        self.save_pending = False
        self.view = "exercises"
        default_index = next((i for i, instrument in enumerate(self.instruments)
                              if instrument.id == "guitar_standard"), 0)
        default_last = self.instruments[default_index].fret_count if self.instruments else 12
        self.match_preferences = {"instrument_index": default_index, "count": "20",
                                  "first": "0", "last": str(default_last)}

        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("TkDefaultFont", 19, "bold"))
        style.configure("Heading.TLabel", font=("TkDefaultFont", 13, "bold"))
        style.configure("Score.TLabel", font=("TkDefaultFont", 24, "bold"))
        style.configure("Answer.TButton", padding=(8, 8))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        title = ttk.Frame(self, padding=(18, 12, 18, 8))
        title.grid(row=0, column=0, sticky="ew")
        ttk.Label(title, text="Tusic", style="Title.TLabel").pack(side="left")
        ttk.Label(title, text="Music practice", padding=(14, 0)).pack(side="left")
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.exercise_tab = ttk.Frame(self.notebook, padding=18)
        self.settings_tab = ttk.Frame(self.notebook, padding=18)
        self.notebook.add(self.exercise_tab, text="  Exercises  ")
        self.notebook.add(self.settings_tab, text="  Settings  ")
        self.exercise_tab.columnconfigure(0, weight=1)
        self.exercise_tab.rowconfigure(0, weight=1)
        self.build_settings()
        self.show_exercises()
        self.bind("<Return>", self.on_enter)
        self.bind("<KP_Enter>", self.on_enter)
        if warnings:
            self.after(100, lambda: messagebox.showwarning("Startup information", "\n\n".join(warnings), parent=self))

    def new_screen(self, view: str) -> ttk.Frame:
        self.stop_media()
        self.view = view
        for child in self.exercise_tab.winfo_children():
            child.destroy()
        frame = ttk.Frame(self.exercise_tab)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        return frame

    def show_exercises(self) -> None:
        self.session = None
        self.notebook.tab(self.settings_tab, state="normal")
        frame = self.new_screen("exercises")
        ttk.Label(frame, text="Exercises", style="Heading.TLabel").grid(row=0, sticky="w", pady=(0, 18))
        catalogue = ttk.Frame(frame)
        catalogue.grid(row=1, sticky="ew")
        catalogue.columnconfigure(1, weight=1)
        entries = [("fretboard_notes", "Fretboard notes", "Identify a highlighted note on guitar, violin or cavaquinho.")]
        entries.extend((key, name, description) for key, (name, description) in EXERCISES.items())
        for row, (identifier, name, description) in enumerate(entries):
            command = self.show_setup if identifier == "fretboard_notes" else lambda key=identifier: self.show_learning_setup(key)
            state = "disabled" if identifier in ("fretboard_notes", "scale_mapping") and not self.instruments else "normal"
            ttk.Button(catalogue, text=name, command=command, width=28, state=state).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=9)
            ttk.Label(catalogue, text=description, wraplength=530).grid(row=row, column=1, sticky="w", pady=9)
        if not self.instruments:
            ttk.Label(frame, text="No valid instruments were found. Check the instrument definitions.").grid(row=2, sticky="w", pady=16)
        ttk.Label(frame, text="All exercises work offline. Scores stay on this computer; change the folder in Settings.",
                  wraplength=700).grid(row=3, sticky="w", pady=24)

    def show_setup(self) -> None:
        self.session = None
        self.notebook.tab(self.settings_tab, state="normal")
        frame = self.new_screen("setup")
        ttk.Label(frame, text="Fretboard notes — match setup", style="Heading.TLabel").grid(row=0, sticky="w", pady=(0, 20))
        form = ttk.Frame(frame)
        form.grid(row=1, sticky="nw")
        ttk.Label(form, text="Instrument").grid(row=0, column=0, sticky="w", padx=(0, 20), pady=8)
        self.instrument_choice = ttk.Combobox(form, state="readonly", width=40,
                                               values=[item.name for item in self.instruments])
        self.instrument_choice.grid(row=0, column=1, sticky="w")
        self.instrument_choice.current(self.match_preferences["instrument_index"])
        self.instrument_choice.bind("<<ComboboxSelected>>", self.instrument_changed)
        self.count_var = tk.StringVar(value=self.match_preferences["count"])
        self.first_var = tk.StringVar(value=self.match_preferences["first"])
        self.last_var = tk.StringVar(value=self.match_preferences["last"])
        ttk.Label(form, text="Number of questions").grid(row=1, column=0, sticky="w", pady=8)
        self.count_input = ttk.Spinbox(form, from_=1, to=500, textvariable=self.count_var, width=8)
        self.count_input.grid(row=1, column=1, sticky="w")
        self.range_label = ttk.Label(form)
        self.range_label.grid(row=2, column=0, sticky="w", pady=8)
        range_frame = ttk.Frame(form)
        range_frame.grid(row=2, column=1, sticky="w")
        selected = self.instruments[self.instrument_choice.current()]
        self.first_input = ttk.Spinbox(range_frame, from_=0, to=selected.fret_count, textvariable=self.first_var, width=5)
        self.first_input.pack(side="left")
        ttk.Label(range_frame, text=" through ").pack(side="left")
        self.last_input = ttk.Spinbox(range_frame, from_=0, to=selected.fret_count, textvariable=self.last_var, width=5)
        self.last_input.pack(side="left")
        ttk.Label(form, text="0 means an open string. Both endpoints are included.").grid(row=3, column=1, sticky="w", pady=(0, 12))
        self.setup_info = ttk.Label(frame, wraplength=760)
        self.setup_info.grid(row=2, sticky="w", pady=(14, 5))
        self.update_setup_info()
        ttk.Label(frame, text="Positions are shuffled. Each position appears once before any repeats.\n"
                             "Sharps and equivalent flats both count as correct.",
                  wraplength=760).grid(row=3, sticky="w", pady=(5, 24))
        actions = ttk.Frame(frame)
        actions.grid(row=4, sticky="w")
        ttk.Button(actions, text="Start match", command=self.start_match).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Back to exercises", command=self.show_exercises).pack(side="left")
        self.count_input.focus_set()

    def update_setup_info(self) -> None:
        instrument = self.instruments[self.instrument_choice.current()]
        self.range_label.configure(text=instrument.range_label)
        if instrument.fretted:
            diagram_info = f"The diagram shows string 1 at the top and frets 0–{instrument.fret_count}."
        else:
            diagram_info = (f"The diagram shows string 1 at the top and 0–{instrument.fret_count} semitones above each open string.\n"
                            "Dotted lines are learning guides; this instrument has no frets.\n"
                            "The schematic spacing is not a physical finger-placement chart or a hand-position number.")
        self.setup_info.configure(text=f"{instrument.string_count} strings · Tuning (bottom to top): "
                                      f"{' – '.join(instrument.tuning)}\n"
                                      f"{diagram_info}")

    def instrument_changed(self, _event=None) -> None:
        instrument = self.instruments[self.instrument_choice.current()]
        self.first_input.configure(to=instrument.fret_count)
        self.last_input.configure(to=instrument.fret_count)
        self.first_var.set("0")
        self.last_var.set(str(instrument.fret_count))
        self.update_setup_info()

    def start_match(self) -> None:
        try:
            count, first, last = int(self.count_var.get()), int(self.first_var.get()), int(self.last_var.get())
            instrument_index = self.instrument_choice.current()
            session = PracticeSession(self.instruments[instrument_index], count, first, last)
        except ValueError as error:
            messagebox.showerror("Check match settings", f"Use whole numbers for the question count and selected range.\n\n{error}", parent=self)
            return
        try:
            self.saved_path = self.score_store.save(session)
        except OSError as error:
            messagebox.showerror("Cannot save scores", f"Choose a writable score folder in Settings.\n\n{error}", parent=self)
            return
        self.match_preferences = {"instrument_index": instrument_index, "count": str(count),
                                  "first": str(first), "last": str(last)}
        self.session = session
        self.save_pending = False
        self.notebook.tab(self.settings_tab, state="disabled")
        self.build_quiz()
        self.show_question()

    def build_quiz(self) -> None:
        frame = self.new_screen("quiz")
        frame.rowconfigure(3, weight=1)
        heading = ttk.Frame(frame)
        heading.grid(row=0, sticky="ew")
        ttk.Label(heading, text="Fretboard notes", style="Heading.TLabel").pack(side="left")
        ttk.Button(heading, text="End match", command=self.end_match).pack(side="right")
        self.progress_label = ttk.Label(frame)
        self.progress_label.grid(row=1, sticky="w", pady=(8, 8))
        self.question_label = ttk.Label(frame)
        self.question_label.grid(row=2, sticky="w", pady=(0, 8))
        self.board = Fretboard(frame, self.session.instrument)
        self.board.grid(row=3, sticky="nsew")
        guidance = "String 1 is at the top. Identify the highlighted note. Select a button or type its name."
        if not self.session.instrument.fretted:
            guidance += "\nNumbers count semitones above open, not hand positions. Spacing is schematic."
        ttk.Label(frame, text=guidance, wraplength=790).grid(row=4, sticky="w", pady=(8, 6))
        keypad = ttk.Frame(frame)
        keypad.grid(row=5, sticky="ew")
        self.answer_buttons = []
        for pitch in range(12):
            name = note_name(pitch, self.settings.spelling)
            button = ttk.Button(keypad, text=name, style="Answer.TButton", command=lambda value=name: self.submit_answer(value))
            button.grid(row=pitch // 6, column=pitch % 6, sticky="ew", padx=3, pady=3)
            keypad.columnconfigure(pitch % 6, weight=1)
            self.answer_buttons.append(button)
        entry_row = ttk.Frame(frame)
        entry_row.grid(row=6, sticky="w", pady=(8, 0))
        ttk.Label(entry_row, text="Your answer:").pack(side="left", padx=(0, 8))
        self.answer_var = tk.StringVar()
        self.answer_entry = ttk.Entry(entry_row, width=10, textvariable=self.answer_var)
        self.answer_entry.pack(side="left", padx=(0, 8))
        self.submit_button = ttk.Button(entry_row, text="Check answer", command=lambda: self.submit_answer(self.answer_var.get()))
        self.submit_button.pack(side="left")
        ttk.Label(entry_row, text="  e.g. C, F# or Bb").pack(side="left")
        footer = ttk.Frame(frame)
        footer.grid(row=7, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        self.feedback_label = ttk.Label(footer, text="", wraplength=620)
        self.feedback_label.grid(row=0, column=0, sticky="w")
        self.next_button = ttk.Button(footer, text="Next question", command=self.next_question, state="disabled")
        self.next_button.grid(row=0, column=1, sticky="e")
        self.save_label = ttk.Label(frame, text="Scores are saved automatically after each answer.")
        self.save_label.grid(row=8, sticky="w", pady=(8, 0))

    def update_progress(self) -> None:
        session = self.session
        context = session.title if isinstance(session, ExerciseSession) else session.instrument.name
        self.progress_label.configure(text=f"Question {session.index + 1} of {session.question_count}   |   "
                                           f"Correct: {session.correct_count} / {len(session.answers)}   |   {context}")

    def show_question(self) -> None:
        if isinstance(self.session, ExerciseSession):
            self.show_learning_question()
            return
        self.update_progress()
        position = self.session.current
        location = self.session.instrument.position_label(position.fret)
        self.question_label.configure(text=f"What note is this?   String {position.string_number}, {location}")
        self.board.set_question(position)
        self.answer_var.set("")
        for button in [*self.answer_buttons, self.submit_button, self.answer_entry]:
            button.configure(state="normal")
        self.feedback_label.configure(text="", foreground="")
        self.next_button.configure(state="disabled", text="Next question")
        self.answer_entry.focus_set()

    def submit_answer(self, text: str) -> None:
        if isinstance(self.session, ExerciseSession):
            self.submit_learning_answer(text)
            return
        if self.view != "quiz" or self.session.answered_current:
            return
        try:
            answer = self.session.submit(text)
        except ValueError as error:
            self.feedback_label.configure(text=str(error), foreground="#a52f29")
            self.answer_entry.focus_set()
            return
        for button in [*self.answer_buttons, self.submit_button, self.answer_entry]:
            button.configure(state="disabled")
        expected = answer["expected_pitch_class"]
        if answer["correct"]:
            feedback, color = f"Correct — {note_names(expected)}.", "#24653b"
        else:
            feedback, color = f"Incorrect — you answered {text.strip()}. The note is {note_names(expected)}.", "#a52f29"
        self.feedback_label.configure(text=feedback, foreground=color)
        self.board.set_question(self.session.current, note_name(expected, self.settings.spelling), answer["correct"])
        self.update_progress()
        self.persist_session()
        self.next_button.configure(state="normal", text=self.next_button_text())
        self.next_button.focus_set()

    def next_button_text(self) -> str:
        if self.save_pending:
            return "Retry save and continue"
        return "View results" if self.session.status == "completed" else "Next question"

    def persist_session(self) -> bool:
        try:
            self.saved_path = self.score_store.save(self.session)
            self.save_pending = False
            if self.view == "quiz":
                self.save_label.configure(text="Progress saved on this computer.", foreground="")
            return True
        except OSError as error:
            self.save_pending = True
            if self.view == "quiz":
                self.save_label.configure(text="Could not save. Your answers are still in memory; retry before continuing.", foreground="#a52f29")
            messagebox.showerror("Could not save progress", f"Your answers are still in this window.\n"
                                 f"Restore access to the score folder, then retry.\n\n{error}", parent=self)
            return False

    def next_question(self) -> None:
        if self.view != "quiz" or not self.session.answered_current:
            return
        if self.save_pending and not self.persist_session():
            return
        if self.session.advance():
            self.show_question()
        else:
            self.show_results()

    def end_match(self) -> None:
        if self.session.status == "in_progress":
            if not messagebox.askyesno("End this match?", "End the match now? Your answered questions will be saved as a partial match.", parent=self):
                return
        self.stop_media()
        if self.save_pending and not self.persist_session():
            return
        self.session.finish()
        if self.persist_session():
            self.show_results()

    def show_results(self) -> None:
        if isinstance(self.session, ExerciseSession):
            self.show_learning_results()
            return
        frame = self.new_screen("results")
        self.notebook.tab(self.settings_tab, state="normal")
        session = self.session
        ttk.Label(frame, text="Match complete" if session.status == "completed" else "Match ended early",
                  style="Heading.TLabel").grid(row=0, sticky="w", pady=(0, 14))
        ttk.Label(frame, text=f"{session.correct_count} / {len(session.answers)} correct  ·  {session.accuracy:g}%",
                  style="Score.TLabel").grid(row=1, sticky="w")
        ttk.Label(frame, text=f"{session.instrument.name}  ·  {len(session.answers)} of {session.question_count} questions answered",
                  wraplength=790).grid(row=2, sticky="w", pady=(8, 16))
        table_frame = ttk.Frame(frame)
        table_frame.grid(row=3, sticky="nsew")
        frame.rowconfigure(3, weight=1)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        columns = ("question", "position", "answer", "expected", "result")
        table = ttk.Treeview(table_frame, columns=columns, show="headings", height=9, selectmode="browse")
        for key, heading, width in zip(columns, ("#", "Position", "Your answer", "Correct note", "Result"), (45, 280, 105, 130, 90)):
            table.heading(key, text=heading)
            table.column(key, width=width, minwidth=40, anchor="w")
        for answer in session.answers:
            table.insert("", "end", values=(answer["question_number"],
                                            f"String {answer['string_number']}, {session.instrument.position_label(answer['fret'])}",
                                            answer["answer"], note_names(answer["expected_pitch_class"]),
                                            "Correct" if answer["correct"] else "Incorrect"))
        table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        table.configure(yscrollcommand=scrollbar.set)
        ttk.Label(frame, text=f"Saved: {self.saved_path}", wraplength=790).grid(row=4, sticky="w", pady=(14, 10))
        actions = ttk.Frame(frame)
        actions.grid(row=5, sticky="w")
        ttk.Button(actions, text="New match", command=self.show_setup).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Exercises", command=self.show_exercises).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Open score folder", command=lambda: self.open_folder(self.saved_path.parent)).pack(side="left")

    def build_settings(self) -> None:
        frame = self.settings_tab
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="Settings", style="Heading.TLabel").grid(row=0, sticky="w", pady=(0, 20))
        ttk.Label(frame, text="Score folder").grid(row=1, sticky="w")
        folder_row = ttk.Frame(frame)
        folder_row.grid(row=2, sticky="ew", pady=(6, 8))
        folder_row.columnconfigure(0, weight=1)
        self.folder_var = tk.StringVar(value=str(self.settings.scores_directory))
        ttk.Entry(folder_row, textvariable=self.folder_var).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(folder_row, text="Browse…", command=self.browse_folder).grid(row=0, column=1)
        ttk.Label(frame, text="One JSON file per match, including individual answers and timings.\n"
                             "Changing this folder affects future matches. Existing scores stay in their original folder.",
                  wraplength=770).grid(row=3, sticky="w", pady=(0, 12))
        ttk.Button(frame, text="Use default folder", command=lambda: self.folder_var.set(str(default_scores_directory()))).grid(row=4, sticky="w")
        ttk.Label(frame, text="Note names on answer buttons").grid(row=5, sticky="w", pady=(24, 8))
        self.spelling_var = tk.StringVar(value=self.settings.spelling)
        options = ttk.Frame(frame)
        options.grid(row=6, sticky="w")
        ttk.Radiobutton(options, text="Sharps (C#, D#…)", value="sharps", variable=self.spelling_var).pack(side="left", padx=(0, 18))
        ttk.Radiobutton(options, text="Flats (Db, Eb…)", value="flats", variable=self.spelling_var).pack(side="left")
        ttk.Label(frame, text="Both spellings are always accepted when you type an answer.").grid(row=7, sticky="w", pady=(8, 20))
        actions = ttk.Frame(frame)
        actions.grid(row=8, sticky="w")
        ttk.Button(actions, text="Save settings", command=self.save_settings).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Open saved score folder", command=lambda: self.open_folder(self.settings.scores_directory)).pack(side="left")
        self.settings_feedback = ttk.Label(frame, text="", wraplength=770)
        self.settings_feedback.grid(row=9, sticky="w", pady=(12, 0))
        ttk.Label(frame, text=f"Settings file: {self.settings_store.path}", wraplength=770).grid(row=10, sticky="w", pady=(20, 0))

    def browse_folder(self) -> None:
        current = Path(self.folder_var.get()).expanduser()
        selected = filedialog.askdirectory(title="Choose where to save scores", parent=self,
                                            initialdir=str(current if current.is_dir() else Path.home()))
        if selected:
            self.folder_var.set(selected)

    def save_settings(self) -> None:
        raw = self.folder_var.get().strip()
        if not raw:
            messagebox.showerror("Choose a folder", "Enter a score folder or use Browse.", parent=self)
            return
        try:
            path = Path(raw).expanduser()
            if not path.is_absolute():
                raise ValueError("Choose an absolute path, or use Browse.")
            settings = Settings(path.resolve(), self.spelling_var.get())
            self.settings_store.save(settings)
        except (OSError, ValueError) as error:
            messagebox.showerror("Could not save settings", str(error), parent=self)
            return
        self.settings = settings
        self.score_store = ScoreStore(settings.scores_directory)
        self.folder_var.set(str(settings.scores_directory))
        self.settings_feedback.configure(text="Settings saved. New matches will use this score folder.")

    @staticmethod
    def open_folder(path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as error:
            messagebox.showerror("Cannot open folder", f"Open this folder manually:\n{path}\n\n{error}")

    def on_enter(self, event) -> str | None:
        if self.notebook.select() != str(self.exercise_tab):
            return None
        # Buttons retain their standard keyboard activation; the entry uses Enter to submit.
        if self.view == "quiz":
            if self.session.answered_current:
                self.next_question()
            elif isinstance(self.session, ExerciseSession):
                if self.session.current.kind in ("notes", "chord", "positions"):
                    self.submit_learning_answer()
            else:
                self.submit_answer(self.answer_var.get())
            return "break"
        if self.view == "setup" and event.widget in (self.count_input, self.first_input, self.last_input):
            self.start_match()
            return "break"
        return None

    def close_app(self) -> None:
        if self.view == "quiz" and self.session:
            if self.session.status == "in_progress":
                if not messagebox.askyesno("Close Tusic?", "End this match and close Tusic? Your answered questions will be saved.", parent=self):
                    return
            self.stop_media()
            if self.save_pending and not self.persist_session():
                return
            self.session.finish()
            if not self.persist_session():
                return
        self.stop_media()
        self.destroy()
