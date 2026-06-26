# Captions

- `0–180` A user question reaches the model, but the answer still needs the document corpus.
- `180–390` VIROC stages the indexing path: documents split into chunks, become embeddings, and land in the vector store.
- `390–570` At query time, the same question probes the vector store and pulls back the nearest context.
- `570–780` The retrieved context carries the question into synthesis, and the LLM turns that grounded path into an answer.
- `780–1020` The payoff is evidence: bare prompting falls short, while retrieved context carries the answer to a grounded result.
