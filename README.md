# Tusic

A simple music practice app for Windows and Linux. All exercises work offline;
scores stay on your computer. Includes guitar, violin, and Brazilian cavaquinho.

## Run the app

**Windows:** open the downloaded `Tusic.exe`. If you have the local build,
double-click `Start Tusic.bat` or `dist/v0.3.1/Tusic.exe`. The executable includes
its dependencies; it is not stored in Git.

**From source:** use Python 3.10+ with Tkinter and install the dependencies once.
For Debian/Ubuntu:

```sh
sudo apt install python3 python3-tk python3-venv libportaudio2
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, install Python with Tcl/Tk enabled, then run
`python -m pip install -r requirements.txt` and `python main.py`.
After setup, no internet connection is needed.

## Practice

Open **Exercises**, choose a topic and question count, adjust its options, then
click **Start match**. Check the feedback after each answer and continue with
**Next question**. Review your answers when the match ends.

| Exercise | What it develops | How to practice |
| --- | --- | --- |
| **Fretboard notes** | Remember where notes are on an instrument. | Choose an instrument and fret/semitone range. Name the highlighted note using a button or the text box. Start with a small range and expand it. |
| **Intervals** | Recognize distances between notes. | Choose Identify, Build, or Mixed. Name the ascending interval or type the note above the given root. Begin with the Basic interval set. |
| **Build scales** | Learn scale notes and spelling. | Choose a key and major, natural minor, or pentatonic scale. Type its notes in ascending order, separated by spaces. Repeating the final tonic is optional. |
| **Scale degrees** | Connect notes to their role in a key. | Choose major or natural minor. Identify a note's degree (1–7), or type the note at a requested degree. |
| **Scales on the instrument** | Connect scale knowledge to fingerboard positions. | Choose a key, scale, instrument, and range. Click every scale-note position, then **Check selection**. Click again to deselect. |
| **Chords from scales** | Build harmony from scale degrees. | Type the requested triad in root–third–fifth order and choose major, minor, or diminished. |
| **Ear training** | Recognize scale degrees by sound. | Play the tonic chord, tonic note, and target note. Choose the final note's degree. Replay whenever needed. |
| **Sing on pitch** | Match and sustain a target pitch. | Choose a comfortable note range and microphone. Optionally **Hear reference**, then **Start listening**. Sing the displayed note and octave while watching the flat/sharp meter. |

Written theory answers require correct spelling: G major uses `F#`, not `Gb`.
Use `#` for sharps and `b` for flats. The fretboard note quiz accepts equivalent
spellings. Every fretboard shows its open-string notes on the left for reference.
Violin lines are semitone learning guides, not physical frets.

For singing, use headphones and a quiet room. The default goal is to stay within
±35 cents for 0.8 seconds (100 cents is one semitone), within a ten-second attempt.
You can adjust the tolerance and hold duration. The microphone opens only when
you start listening; no microphone recordings are saved or transmitted.

## Scores and settings

Answers save automatically as local JSON files. Use **Settings → Score folder**
to choose another location. Defaults are `%LOCALAPPDATA%\Tusic\scores` on Windows
and `~/.local/share/tusic/scores` on Linux.

**Show answer / skip** reveals an answer and counts it as incorrect. **End match**
saves a partial session. If saving fails, restore folder access and use
**Retry save and continue**.

See the [technical reference](docs/reference.md) for custom instruments, offline
installation, troubleshooting, tests, and executable builds. Automated Windows
tests pass; human singing and Linux execution still need validation.
