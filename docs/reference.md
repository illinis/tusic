# Tusic technical reference

For a short introduction to every exercise, see the [practice guide](../README.md).
Run the commands below from the project root.

A simple, offline music practice app for Windows and Linux. It uses Python and
Tkinter, with ordinary controls and a drawn fretboard. No account, server, or
network connection is needed to practice.

## Start practicing

**Windows:** double-click `Tusic.exe` in the Windows download. In this project,
the latest executable is in `dist/v0.3.1/Tusic.exe`; `Start Tusic.bat` also launches it.
The executable includes Python, Tkinter, NumPy, and PortAudio audio support.
If an older version is already running, finish your match and close it before
opening the updated app. Both versions use the same settings and score folder.

**Linux:** install Python 3.10 or newer, Tkinter, PortAudio and the Python
dependencies once, then practice offline. Run this from the project folder:

```sh
# Debian / Ubuntu:
sudo apt install python3 python3-tk python3-venv libportaudio2
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt

# Start the app:
sh start-tusic.sh
```

On Fedora, install `python3-tkinter` and `portaudio` alongside Python. Once the
dependencies are installed, no network connection is used. The same source
runs on both operating systems:

```sh
python main.py
# or: python3 main.py
```

Running from source on Windows requires Python 3.10+ with its Tcl/Tk option
enabled and `python -m pip install -r requirements.txt`. The standalone Windows
executable needs no separate installation of Python or audio libraries.

For source installation on a disconnected computer, first download compatible
wheels on a connected computer with the same OS, architecture and Python
version using `python -m pip download -r requirements.txt -d wheelhouse`.
Transfer that folder and install with
`python -m pip install --no-index --find-links wheelhouse -r requirements.txt`.
The operating system's Python/Tk/PortAudio packages must also be available.

1. Open **Exercises → Fretboard notes**.
2. Select an instrument, question count (1–500), and optional fret/semitone range.
3. Select **Start match**. Name the highlighted note using a button or the text
   box. Press Enter to check a typed answer; press Enter again for the next
   question. Buttons can also be activated with Space after keyboard focus.
4. Read the feedback, then continue. The results screen shows your score and
   every answer for review.

Three instruments are included. Tunings below run from the bottom string in
the diagram to the top; string 1 is always at the top.

| Instrument | Open-string tuning | Diagram |
| --- | --- | --- |
| Guitar | E2–A2–D3–G3–B3–E4 | Six strings, open through fret 12 |
| Violin | G3–D4–A4–E5 | Four strings, open through 12 semitones above open |
| Cavaquinho (Brazilian) | D4–G4–B4–D5 | Four strings, open through fret 12 |

The guitar and cavaquinho diagrams have numbered frets and practice reference
markings at 3, 5, 7, 9, and 12; actual inlay patterns vary by instrument.
The violin is fretless: dotted lines are semitone learning guides, and the
highlight sits on the relevant guide. Numbers count semitones above the open
string, not violin hand positions. Equal spacing is schematic, not a physical
finger-placement chart. The cavaquinho option uses Brazilian tuning; it does
not represent all regional cavaquinho tunings.

Tuning references: [Yamaha violin manual](https://europe.yamaha.com/files/download/other_assets/0/313360/02_violin_E_0702.pdf)
and [Cavaqui's cavaquinho tuner](https://cavaqui.app/).

Open-string note names are always shown to the left of each fretboard for reference.
The highlighted position's note is revealed after answering. Equivalent sharps and flats both count as correct:
`C#` and `Db`, for example. Letter case and Unicode ♯/♭ are accepted.

Positions are shuffled without repetition until every position in the chosen
range has appeared. Longer matches start another shuffled round. Scores count
the first valid answer to each question; invalid text does not use a question.

## Theory, scales and ear training

Each exercise has a question-count setting, immediate feedback, a review
screen, and local score saving. Use a fixed key or randomized roots. You can
skip a question to reveal the answer; it counts as incorrect.

| Exercise | What to do |
| --- | --- |
| Intervals | Identify ascending intervals or write the note above a given root. Basic includes thirds, fourths, fifths and octaves; All adds seconds, sixths, sevenths, augmented fourths and diminished fifths. |
| Build scales | Write major, natural minor, major pentatonic or minor pentatonic scales in ascending order. A repeated final tonic is optional. |
| Scale degrees | Identify the degree of a named note or write the note at a requested degree in major/natural minor. |
| Scales on the instrument | Select all scale-note positions within a fret/semitone range on guitar, violin or cavaquinho. Click a position again to deselect. Green feedback means correct; red means an extra note; amber means a missed note. |
| Chords from scales | Write a root–third–fifth triad on the requested scale degree and choose major, minor or diminished. Natural minor uses its unaltered seventh degree. |
| Ear training | Play a synthesized tonic chord, tonic note and target note, then select the target's scale degree. Replay as often as needed. |

Written theory answers require correct spelling: G major contains F#, not Gb.
Use spaces or commas between notes, and `#` or `b` for accidentals; `##`, `bb`
and `x` (double sharp) are supported. This differs from the original fretboard
note quiz, where equivalent pitch names are accepted. Scale mapping accepts
the pitches of the scale and reveals their correctly spelled note names.

## Sing on pitch

1. Choose **Sing on pitch** from Exercises and select the number of questions.
2. Choose a comfortable lowest and highest target note, a microphone, and an
   output device for optional reference tones. Targets are shuffled chromatic
   notes within your range, without repeats until the range is exhausted.
3. Set the pitch tolerance (default ±35 cents; 100 cents equals one semitone)
   and the time to hold the note (default 0.8 seconds).
4. For each displayed note, optionally use **Hear reference**, then click
   **Start listening**. Match the specified octave as well as the note name.
5. Watch the flat/sharp meter. A steady match passes automatically. After ten
   seconds without a sustained match, the question counts as incorrect. You
   may stop listening before grading to adjust your setup, or skip a target.

The microphone opens only after **Start listening**. It closes on stop, reference
playback, grading, leaving the match or closing the app. Reference playback
finishes before listening can start, to reduce the chance of grading a speaker
tone. Use headphones and a quiet room: the detector measures one pitched sound
and cannot distinguish a singer from another nearby pitched source.

Pitch analysis runs locally with a YIN-style estimator, referenced to A4 =
440 Hz. Silence, clipping and unreliable/noisy frames do not count toward the
hold time. Octave errors count as off pitch. The selected range can be C2–C6;
choose a smaller range that you can sing comfortably. Device quality, room
noise and a breathy/irregular voice can affect detection, so the meter is a
practice aid rather than a guarantee of measurement accuracy in every room.

**No microphone recordings are saved or transmitted.** Only the target,
correctness, response time, and a small pitch summary (such as best cents
error and hold duration) go into the match JSON. Short audio buffers are kept
in memory during listening and discarded when capture stops. Reference tones
are synthesized locally; there are no downloaded sound banks or AI models.

If audio is unavailable, choose a working device in match setup; reopen setup
after plugging in a device. On Windows, enable microphone access for desktop
apps if necessary. On Linux, make sure PortAudio and your normal audio service
are installed and working. The non-audio exercises remain usable without an
audio device.

## Settings and local storage

The score directory is created automatically. Defaults:

| System | Scores | Settings |
| --- | --- | --- |
| Windows | `%LOCALAPPDATA%\Tusic\scores` | `%APPDATA%\Tusic\settings.json` |
| Linux | `~/.local/share/tusic/scores` | `~/.config/tusic/settings.json` |

Linux respects `XDG_DATA_HOME` and `XDG_CONFIG_HOME` when they are absolute paths.
Use **Settings → Score folder → Browse → Save settings** to choose another
location. Changing it affects future matches; existing files stay where they
are. Settings also lets you choose sharp or flat labels for answer buttons.
Both spellings remain valid in the fretboard note quiz regardless of the
display preference; written theory exercises enforce correct note spelling.

Each match has one UTF-8 JSON file named with a unique ID. It contains:

- Schema version, exercise ID, and exercise options. Instrument exercises also
  include an instrument/tuning snapshot and their selected range.
- Requested and answered question counts, correct count, and accuracy.
- UTC start/end timestamps, duration, and completion status.
- Each question/position, submitted answer, expected answer, correctness, and
  response time; singing adds pitch-summary measurements but never audio.

The file is updated atomically after each answer, so completed answers survive
an interrupted application. **End match** or closing the window saves a partial
match as `abandoned`. An unexpected shutdown leaves an `in_progress` record
with the last successfully saved answers. There is no resume or historical
analytics screen yet; the records are ready for those future features.

If a save fails, answers stay in memory and the app offers **Retry save and
continue**. Restore access to the folder before continuing or closing. Tests
use separate temporary folders and do not add scores to your practice history.

## Add another instrument

The renderer and quiz engine use instrument definitions instead of hardcoded
guitar rules. Create an `instruments` directory beside `settings.json` and put
one JSON file per instrument there, then restart Tusic. For example:

```json
{
  "id": "viola_standard",
  "name": "Viola (standard tuning)",
  "tuning": ["C3", "G3", "D4", "A4"],
  "fret_count": 12,
  "markers": [],
  "double_markers": [],
  "fretted": false
}
```

`tuning` lists physical strings from bottom to top in the diagram (not
necessarily ascending pitch, which permits reentrant tunings). Each entry
includes an octave. String 1 corresponds to the last entry. `fret_count` is
the last displayed semitone position, from 1 to 36. Set `fretted` to false
for dotted position guides on a fretless instrument. The illustration adjusts
its string count, fret count, and markers to the instrument. For a fretless
instrument these are learning guides, not physical frets.

Give each instrument a unique lowercase `id`. Invalid definitions produce a
warning and are skipped. The bundled guitar lives in
`tusic/instruments/guitar.json`; copying it with a new ID and `fret_count: 24`
is one way to add a longer-neck practice option. JSON extensions also work
with the standalone executable.

In score files, the existing `fret` and `fret_range` fields also store semitone
offsets for fretless instruments; `instrument.fretted` distinguishes them.
The score schema is unchanged, and previous guitar scores remain readable.

## Development and verification

```sh
python -m unittest discover -s tests -v
```

To include GUI integration tests, set `TUSIC_TEST_GUI=1` in a graphical session:

```powershell
# Windows / PowerShell:
$env:TUSIC_TEST_GUI = '1'
python -m unittest discover -s tests -v
```

```sh
# Linux, with a display:
TUSIC_TEST_GUI=1 python3 -m unittest discover -s tests -v

# Or on a headless Linux machine with Xvfb installed:
TUSIC_TEST_GUI=1 xvfb-run -a python3 -m unittest discover -s tests -v
```

Windows core and GUI integration tests were run locally, including synthetic
pitch signals and simulated microphone success/failure/cleanup cases. Real
microphone singing has not been validated with a human singer. A GitHub Actions
workflow is included for Windows/Linux and Python 3.10/3.12; the Linux jobs
have not been run in this workspace.

Use isolated directories during manual development:

```sh
python main.py --config-dir .test-data/config --data-dir .test-data/scores
```

To create your own executable, build on the target operating system:

```sh
python -m venv .venv
# Activate the virtual environment for your shell, then:
python -m pip install -r requirements-build.txt
python tools/build.py
```

The output is `dist/v0.3.1/Tusic.exe` on Windows and `dist/v0.3.1/Tusic` on Linux. PyInstaller
builds for the operating system it runs on; the Windows build is not a Linux
binary. Runtime dependencies are NumPy and sounddevice (using PortAudio), plus
the standard library. PyInstaller is only a build dependency.

Code organization: `music.py` handles notes/instruments, `theory.py` handles
spelled theory rules, `practice.py` and `exercises.py` manage quizzes,
`storage.py` handles local records, `fretboard.py` draws the instrument,
`audio.py` handles synthesis/devices, `pitch.py` detects pitch, and `ui.py` /
`learning_ui.py` contain the screens.

Audio implementation references: [sounddevice API](https://python-sounddevice.readthedocs.io/en/latest/api/streams.html)
and [YIN algorithm](https://labrosa.ee.columbia.edu/doc/yin.html).
