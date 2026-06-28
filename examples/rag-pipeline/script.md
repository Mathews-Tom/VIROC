# Script — How Retrieval-Augmented Generation Works

- audience: Engineers new to retrieval-augmented generation
- objective: Show why grounding a model in retrieved context beats bare prompting

## The grounding gap

- scene_id: `problem_setup`
- duration: `6s`
- goal: Set up the problem: a bare model answer still needs the document corpus.

### Narration

A user question reaches the model, but the answer still needs the document corpus.

## Index the corpus

- scene_id: `indexing_path`
- duration: `7s`
- goal: Stage the offline indexing path from documents to a vector store.

### Narration

VIROC stages the indexing path: documents split into chunks, become embeddings, and land in the vector store.

## Retrieve at query time

- scene_id: `retrieval_path`
- duration: `6s`
- goal: Probe the vector store with the question and pull back the nearest context.

### Narration

At query time, the same question probes the vector store and pulls back the nearest context.

## Synthesize a grounded answer

- scene_id: `answer_synthesis`
- duration: `7s`
- goal: Carry the question and retrieved context into the model for synthesis.

### Narration

The retrieved context carries the question into synthesis, and the LLM turns that grounded path into an answer.

## Bare versus grounded

- scene_id: `payoff`
- duration: `8s`
- goal: Contrast the bare-prompt answer with the grounded result.

### Narration

The payoff is evidence: bare prompting falls short, while retrieved context carries the answer to a grounded result.

