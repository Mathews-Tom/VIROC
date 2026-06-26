# Script review

## answer_synthesis

- The retrieved context carries the question into synthesis, and the LLM turns that grounded path into an answer.

## indexing_path

- VIROC stages the indexing path: documents split into chunks, become embeddings, and land in the vector store.

## payoff

- The payoff is evidence: bare prompting falls short, while retrieved context carries the answer to a grounded result.

## problem_setup

- A user question reaches the model, but the answer still needs the document corpus.

## retrieval_path

- At query time, the same question probes the vector store and pulls back the nearest context.

