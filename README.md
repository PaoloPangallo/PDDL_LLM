# LLM + PDDL Automated Planning

**Generating, validating and refining PDDL planning problems with Large Language Models**

This project explores the intersection between **Large Language Models and classical automated planning**. It turns structured narrative or "lore" input into PDDL domain/problem files, validates them with a symbolic planner and uses an LLM-based reflection step when corrections are required.

## What it does

The core pipeline is implemented with **LangGraph** and follows a generate–validate–refine workflow:

```text
Structured lore
      ↓
Retrieve similar examples (RAG)
      ↓
Build planning prompt
      ↓
Generate PDDL with a local LLM
      ↓
Validate with Fast Downward
      ↓
   valid?
   /   \
 yes   no
  ↓     ↓
 end   LLM reflection / refinement
```

The aim is not to trust generated planning code blindly. Symbolic validation is used as an external check, while failed generations can be sent through a refinement loop.

## Main components

- **RAG-assisted prompt construction** using examples stored in a local database
- **Local LLM inference** through Ollama
- **LangGraph orchestration**
- **PDDL domain and problem generation**
- **Fast Downward syntax validation and planning**
- **Reflection agent** for automatic correction
- **Flask application** for interacting with the system

## Repository structure

```text
PDDL_LLM/
└── PROGETTOIAPDDL/
    ├── agents/
    │   └── reflection_agent.py
    ├── core/
    │   ├── generator.py
    │   ├── utils.py
    │   └── validator.py
    ├── db/
    ├── lore/
    ├── pddl_examples/
    ├── planner/
    ├── prompts/
    ├── routes/
    ├── app.py
    └── pddl_pipeline.py
```

## Pipeline

The main workflow in `pddl_pipeline.py` contains four stages:

1. **BuildPrompt** — retrieves a similar example and builds the generation prompt.
2. **GeneratePDDL** — asks the configured local LLM for a domain and problem.
3. **Validate** — checks the generated PDDL using Fast Downward.
4. **Refine** — when validation fails, a reflection agent receives the generated files and validation feedback and proposes a corrected version.

## Tech stack

- Python
- LangGraph
- LangChain
- Ollama
- Fast Downward
- Flask
- SQLite / local retrieval
- scikit-learn

## Setup

```bash
cd PROGETTOIAPDDL
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Make sure Ollama is available locally and configure the desired model in the project settings.

Run the pipeline directly with:

```bash
python pddl_pipeline.py
```

or start the Flask application with:

```bash
python app.py
```

## Why it is interesting

LLMs are good at translating high-level descriptions into structured artifacts, but generated PDDL can contain syntactic or semantic errors. This project combines **neural generation with symbolic validation**, making the planner part of the verification loop rather than treating model output as correct by default.

## Author

**Paolo Pangallo**  
M.Sc. candidate in Computer Engineering — Artificial Intelligence  
University of Calabria

## Reliability fixes and reproducibility

The project keeps the original LangGraph workflow, Flask interface, sample lore,
PDDL examples, and historic generated artifacts. The review branch adds safer
session and lore paths, restores structured RAG examples to prompts, and corrects
the Fast Downward invocation; it does **not** replace the project with a demo.

### Planning dependencies

Fast Downward is present as a pinned Git submodule at
`PROGETTOIAPDDL/downward`. Initialise it after cloning (and build the planner
according to its upstream instructions):

```bash
git submodule update --init PROGETTOIAPDDL/downward
cd PROGETTOIAPDDL/downward
./build.py
cd ../..
```

Alternatively install/build Fast Downward elsewhere and set
`FAST_DOWNWARD_PATH` to the absolute path of its `fast-downward.py` driver.
The optional VAL plan checker can be supplied via `VAL_BIN`.

### Local configuration

Use the values in `.env.example` as a reference. These are **environment
variables**, not automatically loaded from a `.env` file.

```bash
export OLLAMA_URL=http://127.0.0.1:11434/api/generate
export OLLAMA_MODEL=deepseek-coder-v2:16b
export FAST_DOWNWARD_PATH="$(pwd)/PROGETTOIAPDDL/downward/fast-downward.py"
```

Install dependencies from `PROGETTOIAPDDL/requirements.txt` and run the Flask
entry point from `PROGETTOIAPDDL/`. The old `pddl_pipeline.py` is retained as
an experimental alternative to the checkpointer-backed graph.

Run dependency-free checks from the repository root:

```bash
python -m unittest discover -s PROGETTOIAPDDL/tests -v
python -m compileall -q PROGETTOIAPDDL
bash -n PROGETTOIAPDDL/planner/run-planner.sh
```

**Validation scope:** Fast Downward translation checks whether the PDDL task
can be translated, not whether the generated storyline faithfully represents
the lore. Finding a plan is a distinct operation. Reproduction of LLM output
requires the same local model, tool versions, prompts and planner build; neither
real Ollama generation nor full end-to-end PDDL planning is exercised by the
lightweight tests.
