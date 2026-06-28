# Static storyboard review

- adapter source version: `static-storyboard-source-v0.1`
- resolution: `1920x1080`
- fps: `30`
- scenes: `5`

## Scene `answer_synthesis`

- frames: `570–780`
- seconds: `19.0–26.0`
- object count: `15`

### Objects

- `answer_synthesis.grounded_answer.box` — rect @ (1426.0, 482.0) 286.0×68.0
- `answer_synthesis.grounded_answer.detail` — text @ (1457.0, 562.0) 224.0×36.0
- `answer_synthesis.grounded_answer.label` — text @ (1464.0, 498.0) 210.0×36.0
- `answer_synthesis.llm.box` — rect @ (1020.0, 482.0) 286.0×68.0
- `answer_synthesis.llm.detail` — text @ (1072.0, 562.0) 182.0×36.0
- `answer_synthesis.llm.grounded_answer.arrow` — arrow @ (1306.0, 512.0) 120.0×8.0
- `answer_synthesis.llm.label` — text @ (1142.0, 498.0) 42.0×36.0
- `answer_synthesis.query.box` — rect @ (208.0, 482.0) 286.0×68.0
- `answer_synthesis.query.detail` — text @ (239.0, 562.0) 224.0×36.0
- `answer_synthesis.query.label` — text @ (260.0, 498.0) 182.0×36.0
- `answer_synthesis.query.retrieved_context.arrow` — arrow @ (494.0, 512.0) 120.0×8.0
- `answer_synthesis.retrieved_context.box` — rect @ (614.0, 482.0) 286.0×68.0
- `answer_synthesis.retrieved_context.detail` — text @ (645.0, 562.0) 224.0×36.0
- `answer_synthesis.retrieved_context.label` — text @ (638.0, 498.0) 238.0×36.0
- `answer_synthesis.retrieved_context.llm.arrow` — arrow @ (900.0, 512.0) 120.0×8.0

### Script review

- The retrieved context carries the question into synthesis, and the LLM turns that grounded path into an answer.

## Scene `indexing_path`

- frames: `180–390`
- seconds: `6.0–13.0`
- object count: `15`

### Objects

- `indexing_path.chunks.box` — rect @ (586.0, 482.0) 314.0×68.0
- `indexing_path.chunks.detail` — text @ (610.0, 562.0) 266.0×36.0
- `indexing_path.chunks.embedder.arrow` — arrow @ (900.0, 512.0) 120.0×8.0
- `indexing_path.chunks.label` — text @ (701.0, 498.0) 84.0×36.0
- `indexing_path.documents.box` — rect @ (152.0, 482.0) 314.0×68.0
- `indexing_path.documents.chunks.arrow` — arrow @ (466.0, 512.0) 120.0×8.0
- `indexing_path.documents.detail` — text @ (190.0, 562.0) 238.0×36.0
- `indexing_path.documents.label` — text @ (246.0, 498.0) 126.0×36.0
- `indexing_path.embedder.box` — rect @ (1020.0, 482.0) 314.0×68.0
- `indexing_path.embedder.detail` — text @ (1072.0, 562.0) 210.0×36.0
- `indexing_path.embedder.label` — text @ (1072.0, 498.0) 210.0×36.0
- `indexing_path.embedder.vector_db.arrow` — arrow @ (1334.0, 512.0) 120.0×8.0
- `indexing_path.vector_db.box` — rect @ (1454.0, 482.0) 314.0×68.0
- `indexing_path.vector_db.detail` — text @ (1485.0, 562.0) 252.0×36.0
- `indexing_path.vector_db.label` — text @ (1527.0, 498.0) 168.0×36.0

### Script review

- VIROC stages the indexing path: documents split into chunks, become embeddings, and land in the vector store.

## Scene `payoff`

- frames: `780–1020`
- seconds: `26.0–34.0`
- object count: `11`

### Objects

- `payoff.bare_answer.box` — rect @ (390.0, 482.0) 300.0×68.0
- `payoff.bare_answer.detail` — text @ (456.0, 562.0) 168.0×36.0
- `payoff.bare_answer.label` — text @ (414.0, 498.0) 252.0×36.0
- `payoff.bare_answer.retrieved_context.arrow` — arrow @ (690.0, 512.0) 120.0×8.0
- `payoff.grounded_answer.box` — rect @ (1230.0, 482.0) 300.0×68.0
- `payoff.grounded_answer.detail` — text @ (1268.0, 562.0) 224.0×36.0
- `payoff.grounded_answer.label` — text @ (1275.0, 498.0) 210.0×36.0
- `payoff.retrieved_context.box` — rect @ (810.0, 482.0) 300.0×68.0
- `payoff.retrieved_context.detail` — text @ (848.0, 562.0) 224.0×36.0
- `payoff.retrieved_context.grounded_answer.arrow` — arrow @ (1110.0, 512.0) 120.0×8.0
- `payoff.retrieved_context.label` — text @ (841.0, 498.0) 238.0×36.0

### Script review

- The payoff is evidence: bare prompting falls short, while retrieved context carries the answer to a grounded result.

## Scene `problem_setup`

- frames: `0–180`
- seconds: `0.0–6.0`
- object count: `10`

### Objects

- `problem_setup.documents.box` — rect @ (1223.0, 482.0) 286.0×68.0
- `problem_setup.documents.detail` — text @ (1247.0, 562.0) 238.0×36.0
- `problem_setup.documents.label` — text @ (1303.0, 498.0) 126.0×36.0
- `problem_setup.llm.box` — rect @ (817.0, 482.0) 286.0×68.0
- `problem_setup.llm.detail` — text @ (869.0, 562.0) 182.0×36.0
- `problem_setup.llm.label` — text @ (939.0, 498.0) 42.0×36.0
- `problem_setup.query.box` — rect @ (411.0, 482.0) 286.0×68.0
- `problem_setup.query.detail` — text @ (442.0, 562.0) 224.0×36.0
- `problem_setup.query.label` — text @ (463.0, 498.0) 182.0×36.0
- `problem_setup.query.llm.arrow` — arrow @ (697.0, 512.0) 120.0×8.0

### Script review

- A user question reaches the model, but the answer still needs the document corpus.

## Scene `retrieval_path`

- frames: `390–570`
- seconds: `13.0–19.0`
- object count: `11`

### Objects

- `retrieval_path.query.box` — rect @ (390.0, 482.0) 300.0×68.0
- `retrieval_path.query.detail` — text @ (428.0, 562.0) 224.0×36.0
- `retrieval_path.query.label` — text @ (449.0, 498.0) 182.0×36.0
- `retrieval_path.query.vector_db.arrow` — arrow @ (690.0, 512.0) 120.0×8.0
- `retrieval_path.retrieved_context.box` — rect @ (1230.0, 482.0) 300.0×68.0
- `retrieval_path.retrieved_context.detail` — text @ (1268.0, 562.0) 224.0×36.0
- `retrieval_path.retrieved_context.label` — text @ (1261.0, 498.0) 238.0×36.0
- `retrieval_path.vector_db.box` — rect @ (810.0, 482.0) 300.0×68.0
- `retrieval_path.vector_db.detail` — text @ (834.0, 562.0) 252.0×36.0
- `retrieval_path.vector_db.label` — text @ (876.0, 498.0) 168.0×36.0
- `retrieval_path.vector_db.retrieved_context.arrow` — arrow @ (1110.0, 512.0) 120.0×8.0

### Script review

- At query time, the same question probes the vector store and pulls back the nearest context.

