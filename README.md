# LLM + PDDL Automated Planning

**Generating, validating and refining PDDL planning problems with Large Language Models**

This project explores the intersection between **Large Language Models and classical automated planning**. It turns structured narrative or "lore" input into PDDL domain/problem files, validates them with a symbolic planner and uses an LLM-based reflection step when corrections are required.

## Why this project?

**A classical planner needs formal PDDL, but people naturally describe tasks in prose.**
An LLM can propose the PDDL translation, yet plausible-looking output is not necessarily
valid or usable. This project explores a *neuro-symbolic feedback loop*: let the LLM
generate, let Fast Downward check translation and search for a plan, and use validation
feedback to inform refinement.

## What it does

The Flask application uses a **LangGraph stateful workflow** with these stages:

```text
Lore + similar stored examples → Prompt → Local LLM → Domain + Problem PDDL
                                                       ↓
                                          Fast Downward translation
                                             ↙               ↘
                                          accepted          rejected
                                             ↓                 ↓
                                       plan search      LLM refinement
                                             ↓                 ↺
                                            result
```

The graph also includes a **prototype human-feedback branch** after the refinement
limit. Translator acceptance, plan existence and faithfulness to the original lore
are different questions; the system does not claim to solve all three.

**Architecture and explanations**
- [System design, component boundaries and LangGraph flow](docs/SYSTEM_DESIGN.md)
- [Motivazione e guida in italiano per raccontare il progetto](docs/PROJECT_WALKTHROUGH_IT.md)

LangGraph handles graph transitions and state; **LangChain Core** supplies message
types and a declared tool, while RAG and Ollama HTTP inference are implemented in
custom Python code.

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

The Flask application runs the checkpoint-aware graph in
[`graphs/pddl_pipeline_graph.py`](PROGETTOIAPDDL/graphs/pddl_pipeline_graph.py):
`BuildPrompt`, `Generate`, `Validate`, `Refine`, `ChatFeedback`,
`GeneratePlan`, and `End`. It uses conditional edges to decide when to refine
and when to proceed to planning.

[`pddl_pipeline.py`](PROGETTOIAPDDL/pddl_pipeline.py) is a **separate historical,
simplified experiment** retained for reference; it is not the active Flask graph.

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

To run the historical simplified pipeline directly (experimental path):

```bash
python pddl_pipeline.py
```

To use the checkpoint-aware graph with the Flask UI, start the application:

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
PDDL examples and historic generated artifacts. Recent reliability changes added
safer session paths, restored structured RAG examples and corrected the planner
adapter without replacing the original project.

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
