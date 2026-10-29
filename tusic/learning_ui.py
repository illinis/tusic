"""Screens for theory, scale mapping, ear training and offline singing practice."""

import time
import tkinter as tk
from tkinter import messagebox, ttk

from .exercises import EXERCISES, ExerciseSession
from .fretboard import SelectionFretboard
from .theory import KEYS, SCALES, midi_name, pitch_class


class LearningScreens:
    def ensure_audio(self):
        if getattr(self, "audio_backend", None) is None:
            from .audio import AudioBackend
            self.audio_backend = AudioBackend()
        return self.audio_backend

    def stop_microphone(self):
        timer = getattr(self, "microphone_timer", None)
        if timer is not None:
            self.after_cancel(timer)
            self.microphone_timer = None
        microphone = getattr(self, "microphone", None)
        self.microphone = None
        if microphone is not None:
            try:
                microphone.close()
            except Exception:
                # A disconnected device must not prevent saving results or closing the app.
                pass

    def stop_media(self):
        self.stop_microphone()
        timer = getattr(self, "playback_timer", None)
        if timer is not None:
            self.after_cancel(timer)
            self.playback_timer = None
        if getattr(self, "audio_backend", None) is not None:
            try:
                self.audio_backend.stop()
            except Exception:
                pass

    def show_learning_setup(self, exercise_id):
        self.session = None
        self.notebook.tab(self.settings_tab, state="normal")
        frame = self.new_screen("learning_setup")
        self.learning_id = exercise_id
        ttk.Label(frame, text=EXERCISES[exercise_id][0] + " — match setup", style="Heading.TLabel").grid(row=0, sticky="w", pady=(0, 12))
        ttk.Label(frame, text=EXERCISES[exercise_id][1], wraplength=790).grid(row=1, sticky="w", pady=(0, 12))
        form = ttk.Frame(frame)
        form.grid(row=2, sticky="nw")
        self.learning_vars = {}
        saved = getattr(self, "learning_preferences", {}).get(exercise_id, {})

        def field(name, label, default, choices=None, limits=None):
            row = len(self.learning_vars)
            variable = tk.StringVar(value=str(saved.get(name, default)))
            self.learning_vars[name] = variable
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=5)
            if choices is not None:
                if variable.get() not in choices:
                    variable.set(str(default))
                widget = ttk.Combobox(form, textvariable=variable, values=choices, state="readonly", width=55)
            elif limits:
                widget = ttk.Spinbox(form, from_=limits[0], to=limits[1], increment=limits[2], width=10, textvariable=variable)
            else:
                widget = ttk.Entry(form, textvariable=variable, width=10)
            widget.grid(row=row, column=1, sticky="w")
            return widget

        field("count", "Number of questions", 5 if exercise_id == "scale_mapping" else 10, limits=(1, 500, 1))
        if exercise_id != "singing":
            field("key", "Key / root note", "Random", ("Random", *KEYS))
        if exercise_id not in ("intervals", "singing"):
            scales = tuple(SCALES) if exercise_id in ("scales", "scale_mapping") else ("Major", "Natural minor")
            field("scale", "Scale", "Major", scales)
        if exercise_id in ("intervals", "scale_degrees"):
            field("mode", "Question mode", "Mixed", ("Mixed", "Identify", "Build"))
        if exercise_id == "intervals":
            field("difficulty", "Interval set", "Basic", ("Basic", "All"))
        if exercise_id == "scale_mapping":
            names = [item.name for item in self.instruments]
            field("instrument", "Instrument", next((item.name for item in self.instruments if item.id == "guitar_standard"), names[0]), names)
            field("first", "First fret / semitone", 0, limits=(0, 36, 1))
            field("last", "Last fret / semitone", 5, limits=(0, 36, 1))
        if exercise_id == "singing":
            notes = tuple(midi_name(midi) for midi in range(36, 85))
            field("low_note", "Lowest target note", "C3", notes)
            field("high_note", "Highest target note", "C5", notes)
            field("tolerance", "Tolerance (cents)", 35, limits=(10, 50, 5))
            field("hold_seconds", "Hold in tune (seconds)", 0.8, limits=(0.4, 3, 0.1))
        self.input_devices, self.output_devices = [], []
        audio_error = ""
        if exercise_id in ("ear_training", "singing"):
            try:
                backend = self.ensure_audio()
                self.output_devices = backend.devices("output")
                if exercise_id == "singing":
                    self.input_devices = backend.devices("input")
            except Exception as error:
                audio_error = f"Audio is unavailable: {error}"
            if exercise_id == "singing":
                field("microphone", "Microphone", "System default", ("System default", *(label for _, label in self.input_devices)))
            field("output", "Speakers / headphones", "System default", ("System default", *(label for _, label in self.output_devices)))
            field("volume", "Reference volume (%)", 18, limits=(1, 50, 1))
        if exercise_id == "singing":
            hint = ("Match the displayed note AND octave. Each attempt lasts up to 10 seconds.\n"
                    "Use headphones and sing one steady note in a quiet room. A reference tone is optional.\n"
                    "The microphone starts only when you click Start listening; no microphone audio is saved.")
        elif exercise_id == "ear_training":
            hint = "Listen to a tonic chord, the tonic alone, then a target note. Choose the final note's scale degree."
        elif exercise_id == "scale_mapping":
            hint = "Click all scale notes in the selected region. A question is correct only when the whole selection is correct."
        else:
            hint = "Written answers use exact musical spelling. Enter notes separated by spaces; sharps and flats are not interchangeable here."
        ttk.Label(frame, text=audio_error or hint, wraplength=790, foreground="#a52f29" if audio_error else "").grid(row=3, sticky="w", pady=(16, 14))
        actions = ttk.Frame(frame)
        actions.grid(row=4, sticky="w")
        ttk.Button(actions, text="Start match", command=self.start_learning_match).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Back to exercises", command=self.show_exercises).pack(side="left")

    def start_learning_match(self):
        values = {key: variable.get() for key, variable in self.learning_vars.items()}
        try:
            options = {key: values[key] for key in ("key", "scale", "mode", "difficulty") if key in values}
            instrument = None
            if self.learning_id == "scale_mapping":
                instrument = next(item for item in self.instruments if item.name == values["instrument"])
                options.update(first=int(values["first"]), last=int(values["last"]))
            if self.learning_id == "singing":
                note_numbers = {midi_name(midi): midi for midi in range(36, 85)}
                options.update(low_midi=note_numbers[values["low_note"]], high_midi=note_numbers[values["high_note"]],
                               tolerance=float(values["tolerance"]), hold_seconds=float(values["hold_seconds"]))
                if not self.input_devices:
                    raise ValueError("No microphone found. Connect one and reopen this setup screen to refresh the device list.")
                options["input_device"] = next((index for index, label in self.input_devices if label == values["microphone"]), None)
            if self.learning_id in ("ear_training", "singing"):
                self.ensure_audio()
                if self.learning_id == "ear_training" and not self.output_devices:
                    raise ValueError("No audio output found. Connect speakers or headphones and reopen this setup screen.")
                options["output_device"] = next((index for index, label in self.output_devices if label == values["output"]), None)
                options["volume"] = float(values["volume"]) / 100
                if not 0.01 <= options["volume"] <= 0.5:
                    raise ValueError("Use a reference volume from 1 to 50 percent.")
            session = ExerciseSession(self.learning_id, int(values["count"]), options, instrument)
            path = self.score_store.save(session)
        except Exception as error:
            messagebox.showerror("Cannot start match", str(error), parent=self)
            return
        if not hasattr(self, "learning_preferences"):
            self.learning_preferences = {}
        self.learning_preferences[self.learning_id] = values
        self.session, self.saved_path, self.save_pending = session, path, False
        self.notebook.tab(self.settings_tab, state="disabled")
        self.show_learning_question()

    def show_learning_question(self):
        frame = self.new_screen("quiz")
        frame.rowconfigure(3, weight=1)
        question = self.session.current
        heading = ttk.Frame(frame)
        heading.grid(row=0, sticky="ew")
        ttk.Label(heading, text=self.session.title, style="Heading.TLabel").pack(side="left")
        ttk.Button(heading, text="End match", command=self.end_match).pack(side="right")
        self.progress_label = ttk.Label(frame)
        self.progress_label.grid(row=1, sticky="w", pady=(8, 12))
        self.update_progress()
        ttk.Label(frame, text=question.prompt, style="Heading.TLabel", wraplength=790).grid(row=2, sticky="w", pady=(0, 14))
        content = ttk.Frame(frame)
        content.grid(row=3, sticky="nsew")
        content.columnconfigure(0, weight=1)
        self.response_controls = []
        self.answer_var = tk.StringVar()
        self.heard_audio = False
        if question.kind == "positions":
            content.rowconfigure(0, weight=1)
            labels = {pitch_class(note): note for note in question.context["scale_notes"]}
            self.selection_label = ttk.Label(content, text="0 positions selected")
            self.board = SelectionFretboard(content, self.session.instrument, self.session.options["first"], self.session.options["last"], labels,
                                           lambda count: self.selection_label.configure(text=f"{count} positions selected"))
            self.board.grid(row=0, sticky="nsew")
            self.selection_label.grid(row=1, sticky="w", pady=8)
            ttk.Label(content, text=f"Click the outlined positions from {self.session.options['first']} through {self.session.options['last']}. Click again to deselect.\n"
                                   "After checking: green = correct, red = extra, amber = missed.", wraplength=790).grid(row=2, sticky="w")
            self.check_button = ttk.Button(content, text="Check selection", command=self.submit_learning_answer)
            self.check_button.grid(row=3, sticky="w", pady=10)
            self.response_controls.append(self.check_button)
        elif question.kind == "voice":
            self.build_voice_controls(content)
        else:
            row = 0
            if self.session.exercise_id == "ear_training":
                self.audio_label = ttk.Label(content, text="Play the tones before answering.")
                self.audio_label.grid(row=0, sticky="w", pady=(0, 8))
                ttk.Button(content, text="Play / replay tones", command=self.play_question_audio).grid(row=1, sticky="w", pady=(0, 18))
                row = 2
            if question.kind == "choice":
                choices = ttk.Frame(content)
                choices.grid(row=row, sticky="nw")
                for i, choice in enumerate(question.choices):
                    button = ttk.Button(choices, text=choice, width=21, style="Answer.TButton",
                                        command=lambda value=choice: self.submit_learning_answer(value))
                    button.grid(row=i // 4, column=i % 4, padx=(0, 6), pady=5, sticky="ew")
                    self.response_controls.append(button)
            else:
                ttk.Label(content, text="Write notes in order, separated by spaces. Use # for sharps and b for flats.", wraplength=790).grid(row=row, sticky="w", pady=(0, 8))
                self.answer_entry = ttk.Entry(content, textvariable=self.answer_var, width=55)
                self.answer_entry.grid(row=row + 1, sticky="w")
                self.response_controls.append(self.answer_entry)
                if question.kind == "chord":
                    self.quality_var = tk.StringVar()
                    ttk.Label(content, text="Root – third – fifth, followed by the chord quality:").grid(row=row + 2, sticky="w", pady=(12, 6))
                    quality = ttk.Combobox(content, textvariable=self.quality_var, state="readonly", values=("major", "minor", "diminished"))
                    quality.grid(row=row + 3, sticky="w")
                    self.response_controls.append(quality)
                self.check_button = ttk.Button(content, text="Check answer", command=self.submit_learning_answer)
                self.check_button.grid(row=row + 4, sticky="w", pady=14)
                self.response_controls.append(self.check_button)
                self.answer_entry.focus_set()
        footer = ttk.Frame(frame)
        footer.grid(row=4, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        self.feedback_label = ttk.Label(footer, text="", wraplength=630)
        self.feedback_label.grid(row=0, column=0, sticky="w")
        self.next_button = ttk.Button(footer, text="Next question", command=self.next_question, state="disabled")
        self.next_button.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.skip_button = ttk.Button(footer, text="Show answer / skip", command=self.skip_learning_question)
        self.skip_button.grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.save_label = ttk.Label(frame, text="Answers are saved locally. All exercises work offline.")
        self.save_label.grid(row=5, sticky="w", pady=(10, 0))

    def submit_learning_answer(self, value=None):
        if self.session.answered_current:
            return
        question = self.session.current
        if self.session.exercise_id == "ear_training" and not self.heard_audio:
            self.feedback_label.configure(text="Play the tones first, then choose the final note's degree.", foreground="#a52f29")
            return
        try:
            if question.kind == "positions":
                value = self.board.selected
            elif question.kind == "chord":
                value = (self.answer_var.get(), self.quality_var.get())
            elif question.kind == "notes":
                value = self.answer_var.get() if value is None else value
            elif question.kind == "voice":
                return
            answer = self.session.submit(value)
        except ValueError as error:
            self.feedback_label.configure(text=str(error), foreground="#a52f29")
            return
        self.finish_learning_answer(answer)

    def skip_learning_question(self):
        if not self.session.answered_current:
            self.finish_learning_answer(self.session.record_result(False, "Skipped", {"skipped": True}))

    def finish_learning_answer(self, answer):
        self.stop_media()
        for widget in self.response_controls:
            widget.configure(state="disabled")
        self.skip_button.configure(state="disabled")
        if self.session.current.kind == "positions":
            self.board.show_feedback(self.session.current.expected)
        if self.session.current.kind == "voice":
            self.voice_status.configure(text="Microphone off. " + answer["answer"])
        prefix = "Correct. " if answer["correct"] else "Incorrect. "
        self.feedback_label.configure(text=prefix + self.session.current.explanation,
                                      foreground="#24653b" if answer["correct"] else "#a52f29")
        self.update_progress()
        self.persist_session()
        self.next_button.configure(text=self.next_button_text(), state="normal")
        self.next_button.focus_set()

    def play_question_audio(self):
        is_voice = self.session.exercise_id == "singing"
        if is_voice:
            self.stop_listening()
        try:
            duration = self.ensure_audio().play(self.session.current.audio,
                                               self.session.options.get("output_device"),
                                               self.session.options.get("volume", 0.18))
        except Exception as error:
            messagebox.showerror("Cannot play audio", f"Choose an available output device in match setup.\n\n{error}", parent=self)
            return
        if getattr(self, "playback_timer", None) is not None:
            self.after_cancel(self.playback_timer)
        if is_voice:
            self.listen_button.configure(state="disabled")
            self.voice_status.configure(text="Playing reference. Microphone is off until playback finishes.")
        else:
            self.heard_audio = False
            self.audio_label.configure(text="Playing: tonic chord → tonic → target note…")

        def finished():
            self.playback_timer = None
            self.audio_backend.stop()
            if is_voice:
                self.voice_status.configure(text="Reference finished. Click Start listening when ready.")
                if not self.session.answered_current:
                    self.listen_button.configure(state="normal")
            else:
                self.heard_audio = True
                self.audio_label.configure(text="Which degree was the final note? Replay as often as needed.")

        self.playback_timer = self.after(int((duration + 0.3) * 1000), finished)

    def build_voice_controls(self, content):
        options = self.session.options
        ttk.Label(content, text=f"Hold within ±{options['tolerance']:g} cents for {options['hold_seconds']:g} seconds.\n"
                               "Match the octave shown above. Each attempt lasts up to 10 seconds.", wraplength=790).grid(row=0, sticky="w")
        self.pitch_meter = tk.Canvas(content, width=600, height=90, background="white", highlightthickness=1, highlightbackground="#bbb")
        self.pitch_meter.grid(row=1, sticky="w", pady=14)
        self.draw_pitch_meter(None)
        self.voice_status = ttk.Label(content, text="Microphone off. Click Start listening to begin.", wraplength=790)
        self.voice_status.grid(row=2, sticky="w")
        self.hold_progress = ttk.Progressbar(content, length=600, maximum=options["hold_seconds"])
        self.hold_progress.grid(row=3, sticky="w", pady=10)
        controls = ttk.Frame(content)
        controls.grid(row=4, sticky="w", pady=8)
        self.listen_button = ttk.Button(controls, text="Start listening", command=self.start_listening)
        self.listen_button.pack(side="left", padx=(0, 8))
        stop = ttk.Button(controls, text="Stop listening", command=self.stop_listening)
        stop.pack(side="left", padx=(0, 8))
        self.reference_button = ttk.Button(controls, text="Hear reference", command=self.play_question_audio)
        self.reference_button.pack(side="left")
        self.response_controls.extend((self.listen_button, stop, self.reference_button))
        ttk.Label(content, text="Use headphones so the microphone hears your voice, not a speaker.\n"
                               "Audio is processed in memory and discarded; only the result and pitch summary are saved.", wraplength=790).grid(row=5, sticky="w", pady=10)

    def draw_pitch_meter(self, cents):
        meter = self.pitch_meter
        meter.delete("all")
        tolerance = self.session.options["tolerance"]
        meter.create_rectangle(300 - tolerance * 2.4, 20, 300 + tolerance * 2.4, 60, fill="#dceedd", outline="")
        meter.create_line(60, 40, 540, 40, fill="#555")
        for value in (-100, -50, 0, 50, 100):
            x = 300 + value * 2.4
            meter.create_line(x, 34, x, 46)
            meter.create_text(x, 73, text=f"{value:+d}" if value else "In tune")
        meter.create_text(65, 10, text="Flat")
        meter.create_text(535, 10, text="Sharp")
        if cents is not None:
            x = 300 + max(-100, min(100, cents)) * 2.4
            meter.create_oval(x-7, 33, x+7, 47, fill="#24653b" if abs(cents) <= tolerance else "#a52f29", outline="")

    def start_listening(self):
        if self.session.answered_current or getattr(self, "playback_timer", None) is not None:
            return
        self.stop_microphone()
        try:
            from .pitch import PitchHold
            backend = self.ensure_audio()
            backend.stop()
            self.microphone = backend.microphone(self.session.options.get("input_device"))
            self.pitch_hold = PitchHold(self.session.current.expected, self.session.options["tolerance"], self.session.options["hold_seconds"])
        except Exception as error:
            self.stop_microphone()
            messagebox.showerror("Cannot open microphone", "Select an available input device and allow microphone access in your operating system.\n\n" + str(error), parent=self)
            return
        self.voice_started = self.voice_last_frame = time.monotonic()
        self.listen_button.configure(state="disabled")
        self.voice_status.configure(text="Listening… sing the requested note.")
        self.hold_progress["value"] = 0
        self.microphone_timer = self.after(80, self.poll_voice)

    def stop_listening(self):
        self.stop_microphone()
        if self.view == "quiz" and isinstance(self.session, ExerciseSession) and self.session.exercise_id == "singing":
            self.voice_status.configure(text="Microphone off. Click Start listening when ready.")
            self.hold_progress["value"] = 0
            if not self.session.answered_current and getattr(self, "playback_timer", None) is None:
                self.listen_button.configure(state="normal")

    def poll_voice(self):
        self.microphone_timer = None
        microphone = getattr(self, "microphone", None)
        if microphone is None or self.session.answered_current:
            return
        from .pitch import PitchReading, detect_pitch, heard_note
        now = time.monotonic()
        remaining = max(0, self.session.options["attempt_seconds"] - (now - self.voice_started))
        try:
            if not microphone.active:
                raise RuntimeError("The microphone disconnected or stopped. Reconnect it and retry.")
            block = microphone.read()
            if block is not None:
                samples, rate, seconds, reason = block
                self.voice_last_frame = now
                reading = detect_pitch(samples, rate) if samples is not None else PitchReading(None, 0, 0, reason)
                matched = self.pitch_hold.update(reading, seconds)
                self.draw_pitch_meter(self.pitch_hold.last_cents)
                self.hold_progress["value"] = self.pitch_hold.held
                if reading.hz is None:
                    text = reading.reason
                else:
                    text = f"Hearing {heard_note(reading.hz)} · {reading.hz:.1f} Hz · {self.pitch_hold.last_cents:+.0f} cents"
                self.voice_status.configure(text=f"Listening: {text}   |   {remaining:.0f}s left")
                if matched:
                    self.finish_learning_answer(self.session.record_result(True, "On pitch", self.pitch_hold.summary()))
                    return
            elif now - self.voice_last_frame > 0.25:
                self.pitch_hold.update(PitchReading(None, 0, 0), 0)
                self.hold_progress["value"] = 0
                self.draw_pitch_meter(None)
                self.voice_status.configure(text=f"Listening: waiting for microphone audio…   |   {remaining:.0f}s left")
        except Exception as error:
            self.stop_listening()
            self.voice_status.configure(text=f"Microphone stopped: {error}")
            return
        if remaining <= 0:
            message = "No steady pitch detected" if self.pitch_hold.best_cents is None else "Target not held in tune within 10 seconds"
            self.finish_learning_answer(self.session.record_result(False, message, self.pitch_hold.summary()))
            return
        self.microphone_timer = self.after(80, self.poll_voice)

    def show_learning_results(self):
        frame = self.new_screen("results")
        self.notebook.tab(self.settings_tab, state="normal")
        session = self.session
        ttk.Label(frame, text=f"{session.title} — " + ("complete" if session.status == "completed" else "ended early"), style="Heading.TLabel").grid(row=0, sticky="w", pady=(0, 12))
        ttk.Label(frame, text=f"{session.correct_count} / {len(session.answers)} correct · {session.accuracy:g}%", style="Score.TLabel").grid(row=1, sticky="w")
        ttk.Label(frame, text=f"{len(session.answers)} of {session.question_count} questions answered. Select a row for details.").grid(row=2, sticky="w", pady=10)
        table_frame = ttk.Frame(frame)
        table_frame.grid(row=3, sticky="nsew")
        frame.rowconfigure(3, weight=1)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        table = ttk.Treeview(table_frame, columns=("number", "question", "answer", "expected", "result"), show="headings", height=8)
        for key, title, width in (("number", "#", 35), ("question", "Question", 280), ("answer", "Your answer", 180), ("expected", "Expected", 180), ("result", "Result", 80)):
            table.heading(key, text=title)
            table.column(key, width=width, minwidth=30)
        for index, answer in enumerate(session.answers):
            table.insert("", "end", iid=str(index), values=(index+1, answer["prompt"], answer["answer"], answer["expected_answer"], "Correct" if answer["correct"] else "Incorrect"))
        table.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        table.configure(yscrollcommand=scroll.set)
        details = ttk.Label(frame, text="", wraplength=790)
        details.grid(row=4, sticky="w", pady=10)

        def review(_event):
            if table.selection():
                index = int(table.selection()[0])
                answer = session.answers[index]
                details.configure(text=f"{answer['prompt']}\nYour answer: {answer['answer']}\n{session.questions[index].explanation}")

        table.bind("<<TreeviewSelect>>", review)
        ttk.Label(frame, text=f"Saved: {self.saved_path}", wraplength=790).grid(row=5, sticky="w", pady=10)
        actions = ttk.Frame(frame)
        actions.grid(row=6, sticky="w")
        ttk.Button(actions, text="New match", command=lambda: self.show_learning_setup(session.exercise_id)).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Exercises", command=self.show_exercises).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Open score folder", command=lambda: self.open_folder(self.saved_path.parent)).pack(side="left")
