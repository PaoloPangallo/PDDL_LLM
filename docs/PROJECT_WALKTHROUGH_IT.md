# PDDL_LLM — Come presentare il progetto

> Scheda narrativa da usare per portfolio, colloqui e discussione tecnica. È basata sull'implementazione presente nel repository, non su risultati sperimentali ipotizzati.
>
> [System design tecnico e diagrammi](SYSTEM_DESIGN.md) · [Repository](../README.md)

## 1. La motivazione: quale problema volevo risolvere?

Un pianificatore simbolico può cercare una sequenza di azioni per raggiungere un obiettivo, ma ha bisogno che il problema sia descritto con un linguaggio formale, come **PDDL**.

Per un essere umano è più naturale descrivere lo scenario: *«Il personaggio parte da una stanza e deve recuperare un oggetto»*. Per un planner non basta: servono azioni, precondizioni, effetti, oggetti, stato iniziale e obiettivo.

L'idea del progetto nasce da qui:

**Posso utilizzare un LLM per tradurre una descrizione narrativa in PDDL, senza considerare automaticamente affidabile ciò che genera?**

Un LLM è adatto a interpretare il linguaggio naturale, ma può produrre strutture incomplete o incoerenti. Un planner classico, invece, segue regole formali: è utile come verificatore indipendente, pur non potendo garantire da solo che la descrizione corrisponda all'intenzione dell'utente.

## 2. La soluzione in parole semplici

Ho progettato una pipeline che mette in comunicazione due mondi:

- **Componente generativa:** un LLM locale tramite Ollama scrive `domain.pddl` e `problem.pddl` a partire dalla descrizione.
- **Componente simbolica:** Fast Downward controlla se il task PDDL può essere tradotto e tenta, separatamente, di calcolare un piano.

Se il controllo fallisce, il sistema usa il feedback ottenuto per provare a correggere i file con un nuovo passaggio LLM. Gli esempi di task precedenti possono aiutare a costruire il prompt attraverso un recupero TF-IDF da SQLite.

### Schema da ricordare

```text
LORE → ESEMPI SIMILI → PROMPT → LLM → PDDL → VALIDAZIONE
                                          ↑        │
                                          └─ REFINE (se non valido)
                                                   │
                                         se valido: PLANNING
```

**Distinzione fondamentale:** PDDL accettato dal traduttore non significa necessariamente piano trovato; piano trovato non significa necessariamente fedeltà alla descrizione narrativa.

## 3. Perché ho scelto LangGraph

Il flusso non è solo una catena lineare di richieste. Dopo la generazione bisogna **decidere il prossimo passo in base all'esito del controllo**. In certi casi si procede alla pianificazione; in altri si rientra nel raffinamento.

Con LangGraph ho modellato il processo attraverso nodi e transizioni condizionali, conservando in uno stato comune il prompt, i file generati, gli errori, il numero di tentativi e l'eventuale piano. Il progetto usa anche checkpoint SQLite per associare lo stato a una sessione.

**Motivazione architetturale:** separare responsabilità e controllo del flusso, invece di nascondere tutto in una funzione monolitica che effettua diverse chiamate LLM.

### E LangChain?

Nella pipeline principale **LangChain Core** supporta la rappresentazione dei messaggi (`HumanMessage`, `AIMessage`, `BaseMessage`). Il repository definisce anche una funzione `@tool` compatibile con LangChain.

Non sarebbe corretto affermare che qui LangChain gestisce tutto il RAG o l'inferenza: il retrieval usa scikit-learn e SQLAlchemy, mentre Ollama è chiamato con richieste HTTP Python. Il tool dichiarato non è collegato al grafo come agente autonomo di tool calling.

## 4. Presentazione breve — circa 30 secondi

> Ho realizzato un progetto che unisce LLM e pianificazione simbolica. L'obiettivo è trasformare descrizioni narrative in problemi PDDL che possano essere controllati da un planner classico. L'LLM, eseguito localmente con Ollama, genera dominio e problema; Fast Downward verifica la traducibilità del task e prova a trovare un piano. Con LangGraph organizzo i passaggi e il ciclo di correzione quando la generazione non è valida. L'idea fondamentale è usare l'LLM per la flessibilità linguistica, senza affidargli anche la verifica del proprio output.

## 5. Presentazione tecnica — circa 90 secondi

> Il progetto nasce dal problema di dover tradurre descrizioni narrative in un linguaggio formale, PDDL, richiesto dagli algoritmi di pianificazione classica.
>
> Ho costruito una pipeline in cui inizialmente viene elaborato il contesto fornito dall'utente. Se sono disponibili esempi precedenti salvati in SQLite, un retrieval basato su TF-IDF e similarità coseno seleziona quelli più pertinenti e li inserisce nel prompt.
>
> Il prompt viene inviato a un modello locale tramite Ollama, che genera un dominio PDDL e un problema PDDL. A questo punto entra in gioco Fast Downward: il sistema verifica se il task è accettato dal traduttore. Se la validazione fallisce, il feedback viene passato a un passaggio di refinement con LLM; se viene accettato, il sistema tenta la ricerca di un piano.
>
> Per coordinare questi passaggi ho utilizzato LangGraph. Il suo vantaggio è gestire un workflow con diramazioni condizionali, stato condiviso e checkpoint SQLite, anziché una semplice sequenza lineare di chiamate. LangChain Core è utilizzato soprattutto per le strutture dei messaggi, mentre retrieval, prompt e chiamate HTTP sono implementati direttamente in Python.
>
> L'aspetto che considero più interessante è l'integrazione neuro-simbolica: la parte probabilistica propone una rappresentazione formale, mentre un componente simbolico esterno ne controlla proprietà verificabili. Rimane distinta la questione della correttezza semantica rispetto alla descrizione originale, che non è garantita soltanto dal planner.

## 6. Domande tecniche che devi saper difendere

| Domanda | Risposta essenziale |
| --- | --- |
| **Perché non chiedere all'LLM direttamente un piano?** | Perché una sequenza di azioni plausibile non prova il rispetto di precondizioni ed effetti. PDDL e planner consentono un controllo formale sulla task representation. |
| **Perché LangGraph e non una semplice chain?** | Ci sono diramazioni basate su verifiche esterne, tentativi di correzione e uno stato da mantenere tra i nodi. |
| **Qual è il ruolo concreto di LangChain?** | Messaggi tipizzati e dichiarazione di un tool compatibile; non fa il retrieval o le chiamate al modello nel grafo principale. |
| **Che tipo di RAG hai implementato?** | Retrieval lessicale, con TF-IDF e cosine similarity su record SQLite che contengono esempi PDDL. Non un vector database né un retriever basato su embedding. |
| **Come controlli l'output LLM?** | Il traduttore di Fast Downward verifica che il task possa essere tradotto. Successivamente il planner cerca un piano. Non è una validazione completa dell'aderenza al lore. |
| **Come gestisci il refinement?** | Un nodo dedicato riceve feedback di validazione e prova a riscrivere i due file. Il grafo li rivalida e mantiene un contatore dei tentativi. |
| **È un agente autonomo?** | È più preciso definirlo una *pipeline stateful con un ciclo di refinement*. Non presenta nel grafo principale un agente LangChain che scelga dinamicamente tool. |
| **Che cosa miglioreresti?** | Test end-to-end con modelli e planner reali, metriche su task PDDL, verifica semantica, gestione più robusta delle eccezioni e un vero interrupt/resume per il feedback umano. |

## 7. Cosa abbiamo verificato e cosa non dobbiamo rivendicare

**Supportato dal codice e dai test:** struttura del grafo, gestione dei rami, formattazione del prompt, adapter Ollama HTTP, retrieval TF-IDF, adapter Fast Downward, presenza di checkpoint e integrazione Flask. I controlli automatici includono test unitari con planner simulato e uno smoke test di costruzione di LangGraph/Flask.

**Non dimostrato da queste verifiche:** tasso di successo di generazione PDDL, miglioramento dovuto al RAG, correttezza rispetto al lore, effettivo funzionamento robusto del feedback umano con interruzione/ripresa e prestazioni di planner/LLM reali su un benchmark.

Questo non rende meno interessante il progetto: permette di discuterne con rigore e di proporre un piano di valutazione credibile.

## 8. La frase da ricordare

> **Ho usato l'LLM per proporre una formalizzazione, LangGraph per coordinare il processo e Fast Downward per verificare proprietà del task che non volevo affidare alla sola generazione linguistica.**
