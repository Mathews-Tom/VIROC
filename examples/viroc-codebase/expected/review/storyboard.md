# Static storyboard review

- adapter source version: `static-storyboard-source-v0.1`
- resolution: `1920x1080`
- fps: `30`
- scenes: `7`

## Scene `compile_fanout`

- frames: `840–1020`
- seconds: `28.0–34.0`
- object count: `11`

### Objects

- `compile_fanout.concrete_ir.code_card` — code @ (650.0, 432.0) 266.0×168.0
- `compile_fanout.concrete_ir.html_source.link` — arrow @ (916.0, 512.0) 88.0×8.0
- `compile_fanout.concrete_ir.manim_source.link` — arrow @ (916.0, 232.0) 88.0×8.0
- `compile_fanout.concrete_ir.remotion_source.link` — arrow @ (916.0, 792.0) 88.0×8.0
- `compile_fanout.concrete_ir.title` — text @ (706.0, 612.0) 154.0×36.0
- `compile_fanout.html_source.code_card` — code @ (1004.0, 432.0) 266.0×168.0
- `compile_fanout.html_source.title` — text @ (1060.0, 612.0) 154.0×36.0
- `compile_fanout.manim_source.code_card` — code @ (1004.0, 152.0) 266.0×168.0
- `compile_fanout.manim_source.title` — text @ (1053.0, 332.0) 168.0×36.0
- `compile_fanout.remotion_source.code_card` — code @ (1004.0, 712.0) 266.0×168.0
- `compile_fanout.remotion_source.title` — text @ (1032.0, 892.0) 210.0×36.0

### Script review

- One resolved Concrete IR compiles deterministically to Manim, HTML, and Remotion source.

## Scene `concept_input`

- frames: `0–150`
- seconds: `0.0–5.0`
- object count: `8`

### Objects

- `concept_input.author.callout` — rect @ (1004.0, 572.0) 240.0×168.0
- `concept_input.author.title` — text @ (1096.0, 752.0) 56.0×36.0
- `concept_input.doc_set.panel` — rect @ (1004.0, 292.0) 240.0×168.0
- `concept_input.doc_set.title` — text @ (1040.0, 472.0) 168.0×36.0
- `concept_input.repo_context.panel` — rect @ (676.0, 292.0) 240.0×168.0
- `concept_input.repo_context.title` — text @ (712.0, 472.0) 168.0×36.0
- `concept_input.topic.panel` — rect @ (676.0, 572.0) 240.0×168.0
- `concept_input.topic.title` — text @ (719.0, 752.0) 154.0×36.0

### Script review

- Start from a concept: a repo, a document set, and a topic brief, not renderer code.

## Scene `editable_vidir`

- frames: `330–480`
- seconds: `11.0–16.0`
- object count: `6`

### Objects

- `editable_vidir.author.callout` — rect @ (664.0, 572.0) 252.0×168.0
- `editable_vidir.author.title` — text @ (762.0, 752.0) 56.0×36.0
- `editable_vidir.outline.code_card` — code @ (664.0, 292.0) 252.0×168.0
- `editable_vidir.outline.title` — text @ (741.0, 472.0) 98.0×36.0
- `editable_vidir.storyboard.code_card` — code @ (1004.0, 292.0) 252.0×168.0
- `editable_vidir.storyboard.title` — text @ (1032.0, 472.0) 196.0×36.0

### Script review

- The approved outline becomes editable VidIR the user and agents refine.

## Scene `parity_proof`

- frames: `1020–1200`
- seconds: `34.0–40.0`
- object count: `10`

### Objects

- `parity_proof.build_manifest.evidence` — formula @ (1004.0, 572.0) 240.0×168.0
- `parity_proof.build_manifest.title` — text @ (1054.0, 752.0) 140.0×36.0
- `parity_proof.compare.0` — arrow @ (916.0, 372.0) 88.0×8.0
- `parity_proof.compare.1` — arrow @ (916.0, 652.0) 88.0×8.0
- `parity_proof.html_path.panel` — rect @ (676.0, 292.0) 240.0×168.0
- `parity_proof.html_path.title` — text @ (733.0, 472.0) 126.0×36.0
- `parity_proof.remotion_path.panel` — rect @ (676.0, 572.0) 240.0×168.0
- `parity_proof.remotion_path.title` — text @ (705.0, 752.0) 182.0×36.0
- `parity_proof.source_hashes.evidence` — formula @ (1004.0, 292.0) 240.0×168.0
- `parity_proof.source_hashes.title` — text @ (1033.0, 472.0) 182.0×36.0

### Script review

- Backend paths compared side by side; source hashes and build.json close the proof.

## Scene `script_and_scene_plan`

- frames: `150–330`
- seconds: `5.0–11.0`
- object count: `11`

### Objects

- `script_and_scene_plan.outline.code_card` — code @ (1004.0, 712.0) 252.0×168.0
- `script_and_scene_plan.outline.title` — text @ (1081.0, 892.0) 98.0×36.0
- `script_and_scene_plan.planner.outline.link` — arrow @ (916.0, 792.0) 88.0×8.0
- `script_and_scene_plan.planner.panel` — rect @ (664.0, 432.0) 252.0×168.0
- `script_and_scene_plan.planner.scene_plan.link` — arrow @ (916.0, 512.0) 88.0×8.0
- `script_and_scene_plan.planner.script.link` — arrow @ (916.0, 232.0) 88.0×8.0
- `script_and_scene_plan.planner.title` — text @ (692.0, 612.0) 196.0×36.0
- `script_and_scene_plan.scene_plan.code_card` — code @ (1004.0, 432.0) 252.0×168.0
- `script_and_scene_plan.scene_plan.title` — text @ (1060.0, 612.0) 140.0×36.0
- `script_and_scene_plan.script.code_card` — code @ (1004.0, 152.0) 252.0×168.0
- `script_and_scene_plan.script.title` — text @ (1088.0, 332.0) 84.0×36.0

### Script review

- The guided planner derives a script, a scene plan, and an outline before any IR exists.

## Scene `storyboard_review`

- frames: `660–840`
- seconds: `22.0–28.0`
- object count: `8`

### Objects

- `storyboard_review.author.callout` — rect @ (1004.0, 572.0) 252.0×168.0
- `storyboard_review.author.title` — text @ (1102.0, 752.0) 56.0×36.0
- `storyboard_review.review.panel` — rect @ (664.0, 292.0) 252.0×168.0
- `storyboard_review.review.title` — text @ (692.0, 472.0) 196.0×36.0
- `storyboard_review.scene_cards.code_card` — code @ (1004.0, 292.0) 252.0×168.0
- `storyboard_review.scene_cards.title` — text @ (1053.0, 472.0) 154.0×36.0
- `storyboard_review.script_review.code_card` — code @ (664.0, 572.0) 252.0×168.0
- `storyboard_review.script_review.title` — text @ (699.0, 752.0) 182.0×36.0

### Script review

- The review surface shows scene cards and the script as an inspectable artifact before final render.

## Scene `validate_repair`

- frames: `480–660`
- seconds: `16.0–22.0`
- object count: `6`

### Objects

- `validate_repair.checks.panel` — rect @ (1004.0, 292.0) 266.0×168.0
- `validate_repair.checks.title` — text @ (1032.0, 472.0) 210.0×36.0
- `validate_repair.repaired.code_card` — code @ (650.0, 572.0) 266.0×168.0
- `validate_repair.repaired.title` — text @ (685.0, 752.0) 196.0×36.0
- `validate_repair.storyboard.code_card` — code @ (650.0, 292.0) 266.0×168.0
- `validate_repair.storyboard.title` — text @ (685.0, 472.0) 196.0×36.0

### Script review

- viroc check surfaces typed VIR diagnostics so the storyboard is repaired before render.

