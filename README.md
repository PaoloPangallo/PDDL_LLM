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
