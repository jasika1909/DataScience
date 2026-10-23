<div align="center">

# CodeGuard AI

**Intelligent code similarity and plagiarism analysis for classrooms and developers**

Compare source code, see exactly which blocks match, and understand *why* a score is what it is.
Runs entirely on your own computer, with no API keys, cloud services or paid tools.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Tests](https://img.shields.io/badge/tests-111%20passing-2ea44f)
![Offline](https://img.shields.io/badge/runs-100%25%20offline-444)

</div>

> Similarity scores are **indicators for human review, not proof of plagiarism.** Shared templates,
> standard algorithms and very short programs can score high; heavily restructured copies can score low.
> Always read the highlighted code before drawing a conclusion.

---

## Screenshots

| Side-by-side comparison | Same logic, different language |
|---|---|
| ![Side-by-side workspace](docs/screenshots/workspace.png) | ![Python vs Java semantic match](docs/screenshots/semantic.png) |
| Matching blocks are colour-coded in both files, even when methods were reordered. | A Python program ported to Java is detected through the semantic signal. |

| Batch overview | PDF report |
|---|---|
| ![Batch ranking and heatmap](docs/screenshots/batch.png) | ![PDF report with code snippets](docs/screenshots/pdf-detail.png) |
| Highest-similarity pairs, possible groups and a clustered heatmap. | Reasons, charts and side-by-side matched code snippets. |

![PDF summary page](docs/screenshots/pdf-summary.png)

*Screenshots are rendered from the application's own UI components and analysis engine on the bundled
sample files in `samples/`.*

---

## Features

- **Side-by-side comparison** with syntax highlighting, line numbers and colour-coded matching blocks.
- **Seven independent signals**, combined with adjustable weights: exact lines, normalized token
  n-grams, TF-IDF cosine, sequence matching, Greedy String Tiling (finds moved blocks), syntax-tree
  structure and a semantic logic profile.
- **False-positive reduction:** comments, imports, brace-only lines, standard boilerplate (entry points,
  input set-up, plain constructors), instructor template code and lines common to most submissions are
  ignored before scoring. Every report lists what was excluded.
- **Semantic matching:** renamed variables, different loop styles (`for` / `while` / `range`),
  `i++` vs `i += 1` vs `i = i + 1`, reordered functions and even code ported between languages.
- **Five languages:** Python, Java, C, C++ and JavaScript. Python uses the real `ast` module; the others
  use a lightweight statement-level parser.
- **Detailed explanations:** a plain-language "Why this score", unique-code ranges and per-signal charts.
- **Batch mode:** upload a ZIP of submissions (up to 60 files), get ranked pairs, possible groups and a
  similarity heatmap whose files are re-ordered so copying groups stand out.
- **Reports:** CSV and PDF with charts, a heatmap, ranking, reasons and matched code snippets.
- **Classroom features:** teacher and student accounts, assignments, submissions, role-based dashboards,
  and a viewer so teachers can read every submitted file.
- **Security and privacy:** hashed passwords, lock-out, session timeout, server-side access control,
  safe uploads and ZIP handling, and delete options that overwrite data.

## How the score is built

| Signal | What it catches |
|---|---|
| Exact line matching | Copy and paste |
| Normalized token n-grams | Renamed variables, reformatting |
| TF-IDF cosine | Shared rare vocabulary |
| Sequence matching | The same steps in the same order |
| Block tiling (GST) | Moved or reordered blocks |
| Syntax-tree structure | The same program structure |
| Semantic profile | The same logic in another style or language |

The overall score is a weighted mean of the signals that apply (weights are in `config.py` and adjustable in the
app). Risk bands (Low / Moderate / High) use **configurable thresholds**, not universal cut-offs.

## Quick start

Requires **Python 3.12** (3.10+ should also work).

```powershell
# 1. Get the code
git clone https://github.com/<your-username>/CodeGuard_AI.git
cd CodeGuard_AI

# 2. Create and activate a virtual environment (Windows PowerShell)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Run
python -m streamlit run app.py
```

Then open <http://localhost:8501>. On macOS or Linux use `python3 -m venv .venv`, `source .venv/bin/activate`
and the same pip and streamlit commands.

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once.

### First launch and accounts

The first launch asks you to create the **administrator (teacher) account**. After that, teachers and
students can use the **Sign up** tab:

- **Teachers** create assignments and student accounts, read every submitted file for their own
  assignments, and run a batch comparison with one click.
- **Students** choose their teacher when signing up, submit one file per assignment and can use
  *Compare Code* as a private self-check. They never see other students' code.
- Each teacher sees only their own assignments and students.

Open sign-up suits one computer or a trusted classroom network. To switch it off (accounts are then created
by teachers and the administrator only):

```powershell
$env:CODEGUARD_SIGNUP = "off"
python -m streamlit run app.py
```

For single-user use with no login at all: `$env:CODEGUARD_AUTH = "off"`.

### Forgot a password?

- **A student:** their teacher resets it under *Assignments > Students > Reset password*.
- **Anyone, including the administrator:** on the computer that runs CodeGuard, with the virtual environment
  active, run `python reset_password.py`. Your data is kept.

## Using the app

1. **Compare Code:** upload files or a **ZIP of submissions**, paste snippets, or load the sample sets.
   Optionally add instructor **template code** that is ignored as non-evidence.
2. Choose a pair or *All pairs*, then press **Analyze Similarity**.
3. Read the workspace: colour-coded blocks, signal bars, **Why this score**, **Unique code**, and function
   structure matches. Use *Highlight* to focus on one block.
4. Download **CSV** or **PDF** reports. PDFs include matched code snippets.
5. **Assignments** (teachers) lets you collect submissions, view each student's code and analyze them all at
   once. **Dashboard** and **Reports** show your history.

## Project layout

```
CodeGuard_AI/
  app.py                    entry point, header and navigation
  config.py                 limits, weights, thresholds, feature flags
  reset_password.py         recover a forgotten password
  requirements.txt
  src/
    file_handler.py           upload / paste / ZIP validation (never executes code)
    code_normalizer.py        tokenizer and normalizer for 5 languages
    similarity_engine.py      signals, scoring, block detection, reasons
    ast_analyzer.py           Python AST analysis
    structure_analyzer.py     tree analysis for Java, C, C++, JavaScript
    semantic.py               canonical-form rewriting (semantic signal)
    boilerplate.py            standard-boilerplate patterns
    batch.py                  ranking, groups, matrix ordering
    report_generator.py       CSV and PDF reports
    database.py, accounts.py  SQLite storage, roles, assignments, access control
    code_viewer.py, ui_components.py, charts.py
  views/                    app pages (home, login, compare, results, assignments, dashboard, ...)
  assets/                   styles.css, logo.svg
  samples/                  example source files
  docs/screenshots/         images used in this README
  tests/                    unit tests
  data/  reports/           local database and saved reports (git-ignored)
```

## Configuration

Most settings live in `config.py`.

| Setting | Default |
|---|---|
| Max file size / lines | 1 MB / 5,000 lines |
| Max files per analysis | 60 (1,770 pairs) |
| ZIP limits | 30 MB, 300 entries, compression-ratio check |
| Session timeout | 30 minutes |
| Lock-out | 5 failed sign-ins, 5 minutes |
| `CODEGUARD_AUTH` | `on` (set `off` for no login) |
| `CODEGUARD_SIGNUP` | `on` (set `off` to disable self-registration) |

## Testing

```powershell
python -m unittest discover -s tests -t . -v
```

The suite (111 tests) covers file validation, the tokenizer, every signal, false-positive reduction, semantic and
structural analysis, batch features, reports, the database and access control.

## Performance

Normalized documents and results are cached, large batches are quick-screened, and a batch stops after 120 seconds
with a clear message. On the development machine, 60 files of about 70 lines (1,770 pairs) took about 2.4 seconds.
Your times will vary.

## Security and privacy

- Passwords: salted PBKDF2-HMAC-SHA256; lock-out after repeated failures; sessions expire when idle.
- Access control is enforced in the server code, not only in the UI, and is covered by tests.
- Uploads are decoded as text and **never executed**. File names are sanitised; ZIPs are read in memory with
  entry, size and compression-ratio limits.
- Comparison history stores file names, hashes and scores, not source code. Submitted assignment files are
  stored so teachers can review them, and can be deleted. Deleted database content is overwritten and the file
  compacted.
- **Not included:** database encryption at rest and HTTPS. Use disk encryption on shared computers and put the
  app behind an HTTPS reverse proxy before exposing it beyond `127.0.0.1`.
- No telemetry: Streamlit usage statistics are disabled and the app makes no network calls.

## Limitations

- Lexical and rule-based methods cannot see intent and cannot prove two programs are equivalent. The semantic
  signal is rule-based and offline, not a neural network.
- Java, C, C++ and JavaScript use a lightweight parser, not a full compiler grammar.
- If every student solves the same small task in the same shape, structural and semantic scores will be high
  for everyone. Compare pairs against the rest of the batch and read the highlighted code.
- The common-code filter can hide a real copy when most of a class copied the same lines. Prefer an instructor
  template when you have one.
- Students submit one file per assignment.

## Status

The analysis engine, accounts and reports are covered by automated tests. The Streamlit interface was exercised
with a scripted test harness; if something looks off in your browser or Streamlit version, please open an issue
with the error text and your Streamlit version (`python -m streamlit --version`).

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named streamlit` | Activate the virtual environment, then `python -m pip install -r requirements.txt` |
| `streamlit` is not recognised | Use `python -m streamlit run app.py` |
| Port 8501 in use | `python -m streamlit run app.py --server.port 8502` |
| Signed out unexpectedly | Sessions expire after 30 minutes of inactivity |
| "Too many failed attempts" | The account is locked for 5 minutes |
| PDF button asks for reportlab | `python -m pip install reportlab` |
| "History database unavailable" | Make sure the `data/` folder is writable |

## License

Add a `LICENSE` file of your choice (for example MIT) before others reuse the code.
