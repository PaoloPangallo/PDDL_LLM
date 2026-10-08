# PDDL_LLM — System Design

> **From narrative descriptions to planner-checkable PDDL.** An experimental neuro-symbolic workflow that combines local LLM generation with an independent classical planner.
>
> [Repository overview](../README.md) · [Italian project walkthrough / interview notes](PROJECT_WALKTHROUGH_IT.md)

## 1. The motivation

Classical planning systems can search for a sequence of actions leading from an initial state to a goal, but they need a **formal** task specification. In PDDL, this means writing a domain (types, predicates and actions) and a problem (objects, initial facts and goals). Turning a natural-language description into those two files by hand requires planning expertise.

LLMs can help translate a narrative into structured PDDL, but generated text can contain incorrect predicates, mismatched domain/problem definitions or unsupported constructs. **A plausible-looking response is not proof that a planner can use it.**

This project explores a bridge between both approaches:

1. **Use an LLM for interpretation and formalization.**
2. **Use an external symbolic tool to check whether the resulting task can be translated and, in a separate step, planned.**
3. **Use validation feedback to inform subsequent LLM refinement attempts.**

The value is the **feedback loop between probabilistic generation and symbolic checking**, not a claim that LLM output becomes semantically correct by default.

### Goals and boundaries

| Goals | Outside the proven scope |
| --- | --- |
| Generate a PDDL domain and problem from structured "lore" | Prove that every generated task faithfully represents the narrative |
| Incorporate similar historical examples into the prompt | Provide a vector/embedding-based RAG system |
| Check PDDL with Fast Downward and attempt to find a plan | Guarantee that every valid PDDL task has a solution |
| Orchestrate conditional generate–validate–refine steps | Claim fully verified, interrupt-safe human-in-the-loop behavior |
| Expose the workflow through a Flask UI/API | Production-scale multi-user deployment |

## 2. System context and components

The diagram is intentionally minimal. It distinguishes **control flow** (LangGraph) from **work done by external services and Python modules**.

\`\`\`mermaid
flowchart LR
    USER["User / browser"] --> WEB["Flask UI + API"]
    WEB --> GRAPH["LangGraph workflow<br/>PipelineState"]

    GRAPH --> PROMPT["Prompt builder +<br/>TF-IDF retrieval"]
    PROMPT <--> EXAMPLES[("SQLite<br/>PDDL examples")]

    GRAPH --> LLMAPI["Ollama HTTP adapter"]
    LLMAPI --> OLLAMA["Local LLM"]

    GRAPH --> FD["Fast Downward<br/>translator + planner"]
    GRAPH <--> STATE[("SQLite<br/>session checkpoints")]
    GRAPH --> FILES[("Generated PDDL<br/>and run artifacts")]
    WEB --> FILES
\`\`\`

**Ownership of responsibilities**

| Component | Responsibility | Real implementation |
| --- | --- | --- |
| Flask | Accept lore/feedback, launch workflow, return JSON or server-sent events | \`routes/pipeline_chat.py\`, \`routes/app_factory.py\` |
| **LangGraph** | Model stages as nodes, maintain typed state, route by validation result, attach checkpointing | \`graphs/pddl_pipeline_graph.py\` |
| Prompt + RAG | Retrieve similar stored examples; add PDDL exemplars to a structured prompt | \`db/db.py\`, \`core/safe_paths.py\`, \`core/generator.py\` |
| Ollama adapter | Make local-model requests over HTTP; extract the marked domain/problem sections | \`core/utils.py\`, \`agents/reflection_agent.py\` |
| Fast Downward | Translate the generated PDDL task, then separately try to produce a plan | \`core/validator.py\` |
| SQLite checkpoint | Keep workflow state under a \`thread_id\` | LangGraph \`SqliteSaver\` |
| Local files | Retain raw output and domain/problem/refinement artifacts | File writes in the graph and web route |

**Two different SQLite roles:** generation-history records used for TF-IDF retrieval are stored through SQLAlchemy; LangGraph execution checkpoints use a separate SQLite checkpointer. These are *not* the same logical store.

## 3. The LangGraph decision workflow

\`\`\`mermaid
flowchart TD
    START["Structured lore"] --> B["BuildPrompt<br/>retrieve examples + assemble prompt"]
    B --> G["Generate<br/>call Ollama + extract PDDL"]
    G --> V{"Validate<br/>Fast Downward translation"}
    V -->|"Accepted"| P["GeneratePlan<br/>search for a plan"]
    P --> E["End / return result"]
    V -->|"Rejected, attempts remain"| R["Refine<br/>LLM correction"]
    R --> V
    V -->|"Refinement limit reached"| H["ChatFeedback<br/>prototype feedback branch"]
    H -->|"Positive feedback"| E
    H -->|"Requested correction"| R
\`\`\`

This is a **conditional graph**, not merely a fixed sequence of LLM calls.

- **BuildPrompt:** assembles a prompt from the input lore and similar PDDL examples (when the history database contains suitable records).
- **Generate:** asks Ollama to produce two tagged sections, then saves \`domain.pddl\` and \`problem.pddl\`.
- **Validate:** calls the Fast Downward translator. Translator success is recorded in the field \`valid_syntax\` (a historical field name; it means *translator accepted the input*).
- **Refine:** passes generated files and validation feedback to a second LLM prompt and tries validation again.
- **GeneratePlan:** separately invokes Fast Downward planning; success means a plan file was produced, not that it matches the narrative intent.
- **ChatFeedback:** an explicit branch for user feedback exists, but the implementation's pause/resume semantics have **not** been verified as a robust LangGraph interrupt workflow.

**Failure nuance:** a planning failure currently returns a failed result and reaches \`End\`; it does not automatically re-enter \`Refine\`. A failed refinement operation may also need stronger handling of the attempt limit. Both are implementation limits, not hidden branches in this diagram.

## 4. Why these technology choices?

| Choice | Motivation and trade-off |
| --- | --- |
| **LangGraph** rather than a linear script | The next stage depends on the *result* of validation. A graph provides explicit branches, shared state and a place to model iterative correction. It adds workflow complexity compared with a one-shot call. |
| **Local Ollama LLM** | Keep inference controllable from the local environment and avoid making a remote API a required architectural component. Quality, latency and the installed model are environment-dependent. |
| **TF-IDF retrieval + SQLite** | Simple, inspectable baseline suitable for a small corpus of past examples; no vector infrastructure is needed. Lexical similarity is weaker than semantic embeddings for distant paraphrases. |
| **Fast Downward as an external checker** | Separate probabilistic generation from deterministic PDDL translation and search. Passing translation does *not* establish narrative fidelity or solvability. |
| **SQLite checkpointer** | Recover a thread's graph state without a separate database service. Proper session lifecycle and multi-user behavior still need stronger testing. |
| **Flask + SSE** | Lightweight browser access with node-by-node progress events. SSE is a transport for updates, not an agent framework. |

## 5. Where LangChain actually appears

A precise technical explanation matters more than a long technology list.

**LangGraph — central to the architecture**

- \`StateGraph(PipelineState)\` defines the workflow's shared, typed state.
- \`add_node\`, \`add_edge\` and \`add_conditional_edges\` express the processing logic.
- \`compile(checkpointer=...)\` and \`SqliteSaver\` support state persistence.
- Flask invokes \`graph.invoke(...)\` and streams \`graph.stream(...)\` updates.

**LangChain Core — used in a smaller, supporting role**

- \`HumanMessage\`, \`AIMessage\` and \`BaseMessage\` represent feedback/message content.
- \`@tool\` decorates \`generate_pddl_tool\` in \`core/generator.py\`; **this tool is not wired into the main LangGraph workflow as an autonomous tool-calling agent**.

**Not LangChain-managed in the main workflow**

- The LLM request uses \`requests.post()\` to the Ollama endpoint, **not** a \`ChatOllama\` runnable or LangChain chain.
- Retrieval uses \`TfidfVectorizer\` and \`cosine_similarity\` from scikit-learn, **not** a LangChain vector store/retriever.
- Planning and validation use subprocess calls to Fast Downward, **not** LLM-generated tool calls.

The honest summary is: **a LangGraph-orchestrated neuro-symbolic pipeline with selected LangChain Core abstractions and custom Python integrations**.

## 6. Data and state design

The graph works on a \`PipelineState\` typed dictionary with these important fields:

| Fields | Meaning |
| --- | --- |
| \`lore\`, \`thread_id\` | Structured input and session identifier |
| \`prompt\`, \`tmp_dir\` | Constructed request and run artifact location |
| \`domain\`, \`problem\` | Current generated PDDL |
| \`refined_domain\`, \`refined_problem\` | Candidate corrections |
| \`validation\`, \`error_message\`, \`status\` | Last checker result and control status |
| \`attempt\` | Refinement counter (configured limit: 3) |
| \`messages\` | LangChain Core messages for feedback |
| \`plan\`, \`plan_log\` | Planning result and diagnostic output |

LangGraph state reducers such as \`last\` and \`non_empty_or_last\` control how values are updated. The checkpoint is keyed by \`thread_id\`, whereas \`questmaster.db\` stores example-generation records used in retrieval.

## 7. Example request (illustrative, not a measured result)

Suppose a user describes an agent who must reach a location and collect an object. The intended behavior is:

1. Read the input lore and select a similar stored example, if one exists.
2. Request a PDDL \`domain\` describing general actions and a \`problem\` describing this scenario.
3. Pass both outputs to Fast Downward's translator.
4. If rejected, feed errors to the refinement prompt and repeat, subject to the retry logic.
5. If accepted, try to calculate a plan and return the result and supporting files.

The example is **conceptual**; it does not imply that any particular model-generated task was successfully solved in a verified experiment.

## 8. Operational and evaluation limitations

- **Translation vs planning vs semantics:** acceptance by the Fast Downward translator, existence of a plan and faithfulness to the input lore are three different properties. Current translation checks do not prove lore–PDDL semantic equivalence.
- **Human feedback:** the graph contains a \`ChatFeedback\` node, but its actual pause/resume behavior should be tested and ideally implemented using explicit interrupt/resume primitives.
- **Retry failure modes:** the three-attempt rule is present, but exceptions during refinement may require additional protection against repeated failure.
- **RAG availability:** retrieved examples depend on historical records in the generation database; the repository does not demonstrate a pretrained embedding index.
- **Execution evidence:** syntax, mocked planner and graph/Flask construction smoke tests exist. They do **not** amount to a demonstrated end-to-end benchmark using a real local LLM and installed Fast Downward.
- **Legacy code:** \`pddl_pipeline.py\` is a separate, older simplified graph. The documented Flask path uses \`graphs/pddl_pipeline_graph.py\`; the two implementations should not be combined when describing a single tested pipeline.
- **Deployability:** the project remains an experimental local prototype, not an audited multi-user production service.

## 9. Source map

- [Active LangGraph workflow](../PROGETTOIAPDDL/graphs/pddl_pipeline_graph.py)
- [Flask streaming and feedback API](../PROGETTOIAPDDL/routes/pipeline_chat.py)
- [RAG history retrieval](../PROGETTOIAPDDL/db/db.py) and [RAG record conversion](../PROGETTOIAPDDL/core/safe_paths.py)
- [Prompt and LangChain tool definition](../PROGETTOIAPDDL/core/generator.py)
- [Ollama HTTP helper](../PROGETTOIAPDDL/core/utils.py) and [reflection agent](../PROGETTOIAPDDL/agents/reflection_agent.py)
- [Fast Downward adapter](../PROGETTOIAPDDL/core/validator.py)
- [Lightweight regression tests](../PROGETTOIAPDDL/tests/)

**Design thesis:** Let the language model propose a formal task; let independent symbolic tools evaluate what they can actually establish; use feedback to revise the proposal. The framework orchestrates those responsibilities without replacing them.
