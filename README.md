# Desktop LLM testing branch

This branch (`desktop-llm-testing`) adds a larger local model and prompts for the authorship-recognition game. `main` remains at the lightweight Pi-oriented baseline (`95eefbe`), including random fallback. No changes from this branch have been merged into main.

## Run the desktop experiment

```powershell
# Download the desktop model once (about 2 GB):
powershell -ExecutionPolicy Bypass -File scripts/setup-desktop.ps1
# Start the desktop model and writing app:
powershell -ExecutionPolicy Bypass -File scripts/run-desktop.ps1
```

The default is `bartowski/Qwen2.5-3B-Instruct-GGUF` / `Qwen2.5-3B-Instruct-Q4_K_M.gguf`, with a 4096-token context and six CPU threads. This is sized for the inspected desktop (about 16 GB RAM, Ryzen 5 150, integrated Radeon graphics). The installed runtime uses the CPU; integrated GPU acceleration has not been configured. More RAM does not guarantee faster inference. Generation may be slower than SmolLM2, so immediate random fallback remains enabled. The desktop request timeout is 45 seconds; rendering does not wait for it.

If the Hugging Face accelerated download stalls, retry setup with `$env:HF_HUB_DISABLE_XET='1'` in PowerShell. A different compatible GGUF model can be selected using `-ModelPath`; tune CPU usage using `-Threads`. Both launchers stop the server they started on exit.

```powershell
# Compare the larger model using the original simple prompt:
powershell -ExecutionPolicy Bypass -File scripts/run-desktop.ps1 -Profile basic
# Run the lightweight model without switching branches:
powershell -ExecutionPolicy Bypass -File scripts/run-local.ps1
```

To return to the preserved lightweight version, close the application and run `git switch main`. To resume this experiment, run `git switch desktop-llm-testing`. Models and environments are ignored local files shared by these branches, not committed assets.

## What the model is instructed to do

The editable instructions live in `src/writing_prompts.py`. The desktop profile asks it to write a competing anonymous line that the participant might mistake for their own: match topic, vocabulary, perspective, capitalization, short phrasing, informal grammar, and roughness. Nine row-specific strategies vary close paraphrases, small alternative details, neighboring thoughts, emotional tone, and plausible recollections. It must not explain the game, speak as an assistant, label its output, or copy the entire human sample. Each result is a standalone passage so late output can recover after random fallback.

Output is filtered to the same letters/digits/spaces alphabet as human input, preventing punctuation alone from identifying AI rows. Model instructions are best-effort; matching style and confusing a participant require hands-on evaluation. The prompt changes do not hide the immediate key-to-row timing cue, so this is a live-writing test rather than proof that identity cannot be inferred. Shuffled recognition rounds are not implemented here.

Desktop validation on 19 October 2026: the downloaded 1,929,903,264-byte Q4_K_M file passed SHA-256 verification against Hugging Face metadata. Three sequential requests on the inspected desktop took 3,328 ms, 1,141 ms, and 1,265 ms end to end. For the synthetic sample `i walked home after the rain and kept thinking about the conversation we never finished`, one result was `i strolled home after the rain and kept wondering about our unfinished talk`. These are individual short-passage timings, not nine-line throughput or proof of human confusion. The desktop launcher also passed headless app startup and model-server shutdown verification. All 18 regression tests passed.

Run all tests with `.venv/Scripts/python.exe -m unittest discover -s tests -v`. The desktop tests cover distinct row strategies, output filtering, basic-profile compatibility, and timeout selection; the original fallback regression tests still apply.

---

# Local AI writing demo (Windows)

The desktop prototype now supports nine locally generated AI lines alongside one human line. The original random generator remains available. The sections below this guide describe the original random-only implementation.

## Setup and launch

Requires Windows x64 and Python 3.10+ (3.12 recommended). From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-local.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-local.ps1
```

If Python is not on PATH, supply its full executable path to setup with `-PythonExe`. Setup creates `.venv`, installs Pygame and the Hugging Face CLI, downloads the official llama.cpp Windows CPU runtime into `.runtime`, and downloads `bartowski/SmolLM2-360M-Instruct-GGUF` / `SmolLM2-360M-Instruct-Q4_K_M.gguf` into `models`. Internet is required for setup; inference then runs locally. Downloaded binaries and weights are not committed. Setup is for Windows x64; the Python client can also use a separately provisioned llama.cpp server on Linux/Pi.

The launcher starts the inference server on loopback, waits for readiness, opens the app, and stops its server when the app closes. It refuses an occupied port; use `-Port 8081` if necessary. `Esc` exits. Hold Backspace for two seconds to clear displayed text, buffers, and saved random-model state. This does not change the pretrained LLM weights.

```powershell
# Compare with the original random mode:
powershell -ExecutionPolicy Bypass -File scripts/run-local.ps1 -Engine random
# Allow more time before random fallback:
powershell -ExecutionPolicy Bypass -File scripts/run-local.ps1 -FallbackMs 1000
# Use another compatible GGUF model:
powershell -ExecutionPolicy Bypass -File scripts/run-local.ps1 -ModelPath models/other.gguf
```

To use an already running local server directly:

```powershell
.venv/Scripts/python.exe src/main.py --window --engine llm --fallback-ms 0
```

`--endpoint` accepts an HTTP loopback chat-completions endpoint only. Client requests bypass environment proxies. No cloud inference, account, or API key is used. The app prints aggregate AI/random character counts, errors, stale results, and last request duration at exit; server diagnostics are in `.runtime/server.err.log`.

## Generation and fallback behavior

One background HTTP worker sends short excerpts of recent human writing and a line's previous passage to the local inference server. It asks for a new standalone sentence rather than an exact suffix. Each of the nine lines has a bounded text buffer; a round-robin scheduler refills low buffers with at most one request outstanding. Pygame rendering never waits for HTTP. Each accepted human key still schedules one character per line. Scheduling follows current key arrivals with a short delay capped at 80 ms, rather than accumulating slow historical timing predictions. Up to eight overdue characters per line can drain per frame; pending queues remain capped at 24 per line. An unavailable model cannot stall rendering. Server failures trigger a global exponential retry backoff from one to 30 seconds, while random fallback continues.

The default `--fallback-ms 0` supplies a character from the existing random method immediately when a scheduled character has no AI text available. A positive value allows one grace period at the start of each buffer-starvation episode; once fallback activates, subsequent characters continue at typing speed until AI text arrives. The grace period is not reapplied for every character. Late model passages begin with a space rather than attaching to the middle of random text. Random fallback does not invalidate these independent sentences, allowing slow inference to recover. Backspace invalidates outstanding AI context and clears buffered AI text; reset invalidates all prior requests. Ordinary appended typing updates the next request's context rather than cancelling every in-flight request.

SmolLM2-360M prioritizes speed. It can copy input, repeat, ignore instructions, or produce weak prose; this is an initial model to compare, not a claim that all nine lines will convincingly mimic humans. Nine lines share inference capacity, so initial buffers fill progressively. Fallback may remain visible during startup or continuous fast typing. Character punctuation can be generated by AI even though the original human input filter admits letters, digits, and spaces only. Neither the pretrained weights nor personal style are trained by these requests. Rhythm and random patterns continue to learn from human keys only.

## Verification

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

The 13 tests cover fast typing with no model response, one-time fallback grace, slow-model recovery, global failure backoff, and real HTTP request/response parsing against a local fixture, endpoint restrictions, fallback deadlines and recovery, stale results after edits/reset, bounded queues, fair scheduling, refill preservation, and server-error backoff. The initial desktop implementation passed all eight original tests, headless Pygame render/edit/reset checks in both modes, and launcher startup/shutdown with the real local model server. A 10-second nine-line run using simulated input displayed 670 AI characters and 5 random fallback characters, with zero request errors and all nine AI lines active. The last request in that run took 375 ms. This is a smoke test, not a sustained throughput benchmark or an HCI validation. Visual inspection also confirmed that this small model sometimes produces assistant-like text or echoes instructions; a stronger model or further prompt tuning may be needed for convincing deception. After the fallback scheduling fix, a six-second headless Pygame run injected 1.2-second HTTP responses and a server 503 failure. All 100 input keys produced the expected 900 line characters: 81 AI and 819 random. Measured input-to-line-update lag was 34 ms at p95 and 80 ms maximum. This validates fallback responsiveness under those injected conditions, not faster LLM inference. The deterministic regression suite also checks 40 keys/second with no model results and no lost characters. Full Pi performance remains unmeasured.

---

# Keystroke Spike

Keystroke Spike is a local, stateful keystroke predictor built with Python and Pygame for a 720 × 720 Raspberry Pi cyberdeck display. It renders one user-controlled line and nine synthetic “ghost” lines. A bounded character-level n-gram model learns both transition probabilities and inter-key timing online; every accepted user keystroke causes each ghost to schedule one predicted character.

The application has no server component, network dependency, or pretrained model. Inference, learning, rendering, and persistence all run in one process.

## System architecture

```text
                       Pygame event loop
                              │
              ┌───────────────┴───────────────┐
              │                               │
       accepted character                timer tick
              │                               │
              ▼                               ▼
      NgramPredictor.learn()          GhostRunner.tick()
              │                               │
      update transition and            flush due entries
         timing buckets                into ghost text
              │                               │
              ▼                               │
    GhostRunner.on_user_keyed()                │
              │                               │
     sample one character and                  │
    delay for each of 9 ghosts                 │
              └───────────────┬───────────────┘
                              ▼
                    render all 10 lines
```

The process runs a 60 FPS event/render loop. Prediction is synchronous and uses small in-memory collections; ghost output is asynchronous within the loop through timestamped queues rather than threads or coroutines.

## Core algorithm

### Character prediction

The predictor is a fixed-order character model with an order of three. For each accepted character `c`, it uses the preceding three-character context `p` to append a sample to a transition bucket:

```text
next[p] = [..., c]
```

Inference samples uniformly from the stored observations for the current prefix. Keeping repeated observations in the bucket implicitly preserves empirical frequency without maintaining explicit counters.

The fallback chain is:

1. Sample from the current three-character prefix.
2. Sample from the pooled observations across all prefixes.
3. Sample a random lowercase ASCII letter.

Only ASCII letters, digits, and spaces are admitted by the input layer. Backspace edits the displayed user text but is not learned as a model token.

### Timing prediction

The model records the elapsed time between accepted user keystrokes in a parallel bucket:

```text
timing[p] = [..., interval_ms]
```

Intervals are clamped to `[40, 2000]` ms. Prediction uses the median for the active prefix, then the global median if that prefix has no samples, then a cold-start default of `320` ms.

Each ghost applies independent multiplicative jitter to the predicted interval:

```text
delay = clamp(base × uniform(0.72, 1.28), 70, 1400)
```

Ghost queues are serialized per line using `busy_until`. If the user types faster than a ghost emits, new output is scheduled after that ghost's last queued character rather than at the current wall-clock time.

### Bounded state

The learner has explicit limits suitable for a small always-on device:

| Parameter | Value | Purpose |
| --- | ---: | --- |
| Prefix length | 3 characters | Local context for prediction |
| Prefix capacity | 2,000 | Caps model cardinality |
| Samples per bucket | 64 | Caps transition and timing history |
| Save interval | 8 accepted keys | Limits unsaved state |
| Internal history | 11 characters maximum | Bounds active context storage |
| Stored text per line | 160 characters | Bounds display state |
| Visible tail per line | 42 characters | Fits the square UI |

Prefixes are tracked in recency order. Exceeding 2,000 prefixes removes the least recently touched prefix from both transition and timing maps.

## Runtime behavior

`src/main.py` owns the application lifecycle:

1. Detect Raspberry Pi hardware through `/proc/device-tree/model`.
2. Initialize SDL/Pygame and create a logical 720 × 720 surface.
3. Load `data/model-v1.json` when present and valid.
4. Select one of ten rows as the live input row for the session.
5. Process keyboard events, advance ghost queues, and redraw at 60 FPS.
6. Save model state during normal shutdown.

`pygame.SCALED` lets SDL scale the logical square surface for the physical display. Raspberry Pi execution defaults to fullscreen; other platforms default to a fixed-size window. `--fullscreen` and `--window` override detection.

Audio is unused, so `SDL_AUDIODRIVER` defaults to `dummy`. Key repeat is disabled to make each learned event correspond to a distinct key-down event.

## Persistence format

Model state is written as UTF-8 JSON to `data/model-v1.json`:

```json
{
  "next": {
    "the": ["r", " ", "r"]
  },
  "timing": {
    "the": [182, 241, 195]
  },
  "recency": ["the"]
}
```

- `next` maps a three-character prefix to observed successor characters.
- `timing` maps the same prefix to observed inter-key intervals in milliseconds.
- `recency` stores prefix eviction order from oldest to newest.

Writes occur every eight learned characters and on normal process exit. Saving writes directly with `Path.write_text`; it is not transactional or atomic. Malformed or structurally invalid JSON is ignored at startup. File-system errors during load, save, reset, or directory creation are intentionally non-fatal.

Holding Backspace for two seconds clears in-memory model state, ghost queues, live text, and the persisted model file.

## Repository layout

```text
keystroke-spike/
├── src/
│   ├── main.py          # Event loop, input state, rendering, app lifecycle
│   ├── predictor.py     # Online n-gram learner and JSON persistence
│   ├── ghosts.py        # Per-ghost queues, scheduling, and text bounds
│   └── charset.py       # Input validation and cold-start alphabet
├── scripts/
│   ├── setup-pi.sh      # Raspberry Pi OS packages and virtual environment
│   └── run-pi.sh        # Display setup, process launch, and error logging
├── pi/
│   ├── install-desktop-launcher.sh
│   ├── keystroke-spike.png
│   └── README-PI.txt
├── data/                # Runtime model storage
└── requirements-pi.txt  # Pygame 2.6.x
```

## Requirements

- Python 3 with `venv`
- Pygame `>=2.6,<3`
- SDL 2 runtime libraries
- A serif system font; Liberation Serif and DejaVu Serif are Pi fallbacks
- Raspberry Pi OS for the automated device setup script

The application code is portable across Linux, macOS, and Windows. The provisioning and desktop-launcher scripts target Raspberry Pi OS/Linux.

## Development setup

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-pi.txt
python src/main.py --window
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-pi.txt
python src\main.py --window
```

CLI options:

```text
python src/main.py [--fullscreen | --window]
```

## Raspberry Pi deployment

Run provisioning as the intended desktop user, not as `root`:

```bash
cd ~/keystroke-spike
chmod +x scripts/*.sh pi/*.sh
./scripts/setup-pi.sh
```

The script:

1. Verifies that `/proc/device-tree/model` identifies a Raspberry Pi.
2. Installs Python, SDL 2, FreeType, and fallback fonts through `apt`.
3. Creates `.venv` in the repository.
4. Installs the pinned Pygame range.

Launch manually:

```bash
./scripts/run-pi.sh
```

Install `.desktop` entries in `~/Desktop` and `~/.local/share/applications`:

```bash
./pi/install-desktop-launcher.sh
```

The runtime wrapper records environment details and stderr/stdout in `launch.log`. It uses `DISPLAY=:0` when neither X11 nor Wayland display variables are available, and displays launch failures through `zenity` when installed.

Use windowed mode on the Pi with:

```bash
./scripts/run-pi.sh --window
```

## Controls

| Input | Behavior |
| --- | --- |
| `A–Z`, `a–z`, `0–9`, space | Append to live text, update the model, schedule ghost output |
| Backspace | Delete one live-text character |
| Hold Backspace for 2 seconds | Reset all transient and persisted learned state |
| Esc | Exit and save model state |
| Ctrl/Alt/Meta-modified input | Ignored |

## Operational notes

- The generated model can reflect user typing patterns. Keep `data/model-v1.json` out of version control if that data is sensitive.
- Abrupt power loss can discard up to seven accepted keystrokes and may interrupt a JSON write.
- The launcher log is append-only and is not automatically rotated.
- The model format is versioned through its filename rather than an internal schema field.
- There is currently no automated test suite or migration path between model versions.
