# Static storyboard review

- adapter source version: `static-storyboard-source-v0.1`
- resolution: `1920x1080`
- fps: `30`
- scenes: `9`

## Scene `closing`

- frames: `1320–1440`
- seconds: `44.0–48.0`
- object count: `1`

### Objects

- `closing.closing_claim.statement` — text @ (283.0, 488.0) 1354.0×104.0

### Script review

- Reviewable, testable, reproducible — VidIR is the source of truth.

## Scene `compile_fanout`

- frames: `960–1140`
- seconds: `32.0–38.0`
- object count: `17`

### Objects

- `compile_fanout.concrete_ir.body.0` — text @ (608.0, 500.0) 210.0×32.0
- `compile_fanout.concrete_ir.body.1` — text @ (608.0, 532.0) 280.0×32.0
- `compile_fanout.concrete_ir.code_card` — code @ (580.0, 432.0) 336.0×168.0
- `compile_fanout.concrete_ir.detail` — text @ (636.0, 612.0) 224.0×36.0
- `compile_fanout.concrete_ir.html_source.link` — arrow @ (916.0, 512.0) 88.0×8.0
- `compile_fanout.concrete_ir.manim_source.link` — arrow @ (916.0, 232.0) 88.0×8.0
- `compile_fanout.concrete_ir.remotion_source.link` — arrow @ (916.0, 792.0) 88.0×8.0
- `compile_fanout.concrete_ir.title` — text @ (671.0, 454.0) 154.0×36.0
- `compile_fanout.html_source.code_card` — code @ (1004.0, 432.0) 336.0×168.0
- `compile_fanout.html_source.detail` — text @ (1102.0, 612.0) 140.0×36.0
- `compile_fanout.html_source.title` — text @ (1095.0, 454.0) 154.0×36.0
- `compile_fanout.manim_source.code_card` — code @ (1004.0, 152.0) 336.0×168.0
- `compile_fanout.manim_source.detail` — text @ (1116.0, 332.0) 112.0×36.0
- `compile_fanout.manim_source.title` — text @ (1088.0, 174.0) 168.0×36.0
- `compile_fanout.remotion_source.code_card` — code @ (1004.0, 712.0) 336.0×168.0
- `compile_fanout.remotion_source.detail` — text @ (1067.0, 892.0) 210.0×36.0
- `compile_fanout.remotion_source.title` — text @ (1067.0, 734.0) 210.0×36.0

### Script review

- One resolved Concrete IR compiles deterministically to Manim, HTML, and Remotion source.

## Scene `concept_input`

- frames: `120–270`
- seconds: `4.0–9.0`
- object count: `12`

### Objects

- `concept_input.author.callout` — rect @ (1004.0, 572.0) 336.0×168.0
- `concept_input.author.detail` — text @ (1067.0, 752.0) 210.0×36.0
- `concept_input.author.title` — text @ (1144.0, 594.0) 56.0×36.0
- `concept_input.doc_set.detail` — text @ (1053.0, 472.0) 238.0×36.0
- `concept_input.doc_set.panel` — rect @ (1004.0, 292.0) 336.0×168.0
- `concept_input.doc_set.title` — text @ (1088.0, 314.0) 168.0×36.0
- `concept_input.repo_context.detail` — text @ (657.0, 472.0) 182.0×36.0
- `concept_input.repo_context.panel` — rect @ (580.0, 292.0) 336.0×168.0
- `concept_input.repo_context.title` — text @ (664.0, 314.0) 168.0×36.0
- `concept_input.topic.detail` — text @ (608.0, 752.0) 280.0×36.0
- `concept_input.topic.panel` — rect @ (580.0, 572.0) 336.0×168.0
- `concept_input.topic.title` — text @ (671.0, 594.0) 154.0×36.0

### Script review

- Start from a concept: a repo, a document set, and a topic brief, not renderer code.

## Scene `editable_vidir`

- frames: `450–600`
- seconds: `15.0–20.0`
- object count: `11`

### Objects

- `editable_vidir.author.callout` — rect @ (538.0, 572.0) 378.0×168.0
- `editable_vidir.author.detail` — text @ (622.0, 752.0) 210.0×36.0
- `editable_vidir.author.title` — text @ (699.0, 594.0) 56.0×36.0
- `editable_vidir.outline.code_card` — code @ (538.0, 292.0) 378.0×168.0
- `editable_vidir.outline.detail` — text @ (601.0, 472.0) 252.0×36.0
- `editable_vidir.outline.title` — text @ (678.0, 314.0) 98.0×36.0
- `editable_vidir.storyboard.body.0` — text @ (1032.0, 360.0) 252.0×32.0
- `editable_vidir.storyboard.body.1` — text @ (1032.0, 392.0) 322.0×32.0
- `editable_vidir.storyboard.code_card` — code @ (1004.0, 292.0) 378.0×168.0
- `editable_vidir.storyboard.detail` — text @ (1095.0, 472.0) 196.0×36.0
- `editable_vidir.storyboard.title` — text @ (1095.0, 314.0) 196.0×36.0

### Script review

- The approved outline becomes editable VidIR the user and agents refine.

## Scene `parity_proof`

- frames: `1140–1320`
- seconds: `38.0–44.0`
- object count: `19`

### Objects

- `parity_proof.build_manifest.body.0` — text @ (1032.0, 640.0) 224.0×32.0
- `parity_proof.build_manifest.body.1` — text @ (1032.0, 672.0) 280.0×32.0
- `parity_proof.build_manifest.detail` — text @ (1067.0, 752.0) 210.0×36.0
- `parity_proof.build_manifest.evidence` — formula @ (1004.0, 572.0) 336.0×168.0
- `parity_proof.build_manifest.title` — text @ (1102.0, 594.0) 140.0×36.0
- `parity_proof.compare.0` — arrow @ (916.0, 372.0) 88.0×8.0
- `parity_proof.compare.1` — arrow @ (916.0, 652.0) 88.0×8.0
- `parity_proof.html_path.detail` — text @ (650.0, 472.0) 196.0×36.0
- `parity_proof.html_path.panel` — rect @ (580.0, 292.0) 336.0×168.0
- `parity_proof.html_path.title` — text @ (685.0, 314.0) 126.0×36.0
- `parity_proof.remotion_path.detail` — text @ (664.0, 752.0) 168.0×36.0
- `parity_proof.remotion_path.panel` — rect @ (580.0, 572.0) 336.0×168.0
- `parity_proof.remotion_path.title` — text @ (657.0, 594.0) 182.0×36.0
- `parity_proof.source_hashes.body.0` — text @ (1032.0, 360.0) 210.0×32.0
- `parity_proof.source_hashes.body.1` — text @ (1032.0, 392.0) 210.0×32.0
- `parity_proof.source_hashes.body.2` — text @ (1032.0, 424.0) 210.0×32.0
- `parity_proof.source_hashes.detail` — text @ (1095.0, 472.0) 154.0×36.0
- `parity_proof.source_hashes.evidence` — formula @ (1004.0, 292.0) 336.0×168.0
- `parity_proof.source_hashes.title` — text @ (1081.0, 314.0) 182.0×36.0

### Script review

- Backend paths compared side by side; source hashes and build.json close the proof.

## Scene `script_and_scene_plan`

- frames: `270–450`
- seconds: `9.0–15.0`
- object count: `15`

### Objects

- `script_and_scene_plan.outline.code_card` — code @ (1004.0, 712.0) 308.0×168.0
- `script_and_scene_plan.outline.detail` — text @ (1032.0, 892.0) 252.0×36.0
- `script_and_scene_plan.outline.title` — text @ (1109.0, 734.0) 98.0×36.0
- `script_and_scene_plan.planner.detail` — text @ (671.0, 612.0) 182.0×36.0
- `script_and_scene_plan.planner.outline.link` — arrow @ (916.0, 792.0) 88.0×8.0
- `script_and_scene_plan.planner.panel` — rect @ (608.0, 432.0) 308.0×168.0
- `script_and_scene_plan.planner.scene_plan.link` — arrow @ (916.0, 512.0) 88.0×8.0
- `script_and_scene_plan.planner.script.link` — arrow @ (916.0, 232.0) 88.0×8.0
- `script_and_scene_plan.planner.title` — text @ (664.0, 454.0) 196.0×36.0
- `script_and_scene_plan.scene_plan.code_card` — code @ (1004.0, 432.0) 308.0×168.0
- `script_and_scene_plan.scene_plan.detail` — text @ (1067.0, 612.0) 182.0×36.0
- `script_and_scene_plan.scene_plan.title` — text @ (1088.0, 454.0) 140.0×36.0
- `script_and_scene_plan.script.code_card` — code @ (1004.0, 152.0) 308.0×168.0
- `script_and_scene_plan.script.detail` — text @ (1074.0, 332.0) 168.0×36.0
- `script_and_scene_plan.script.title` — text @ (1116.0, 174.0) 84.0×36.0

### Script review

- The guided planner derives a script, a scene plan, and an outline before any IR exists.

## Scene `storyboard_review`

- frames: `780–960`
- seconds: `26.0–32.0`
- object count: `12`

### Objects

- `storyboard_review.author.callout` — rect @ (1004.0, 572.0) 308.0×168.0
- `storyboard_review.author.detail` — text @ (1053.0, 752.0) 210.0×36.0
- `storyboard_review.author.title` — text @ (1130.0, 594.0) 56.0×36.0
- `storyboard_review.review.detail` — text @ (671.0, 472.0) 182.0×36.0
- `storyboard_review.review.panel` — rect @ (608.0, 292.0) 308.0×168.0
- `storyboard_review.review.title` — text @ (664.0, 314.0) 196.0×36.0
- `storyboard_review.scene_cards.code_card` — code @ (1004.0, 292.0) 308.0×168.0
- `storyboard_review.scene_cards.detail` — text @ (1095.0, 472.0) 126.0×36.0
- `storyboard_review.scene_cards.title` — text @ (1081.0, 314.0) 154.0×36.0
- `storyboard_review.script_review.code_card` — code @ (608.0, 572.0) 308.0×168.0
- `storyboard_review.script_review.detail` — text @ (636.0, 752.0) 252.0×36.0
- `storyboard_review.script_review.title` — text @ (671.0, 594.0) 182.0×36.0

### Script review

- The review surface shows scene cards and the script as an inspectable artifact before final render.

## Scene `title_card`

- frames: `0–120`
- seconds: `0.0–4.0`
- object count: `2`

### Objects

- `title_card.brand_claim.statement` — text @ (283.0, 582.0) 1354.0×104.0
- `title_card.brand_title.heading` — text @ (283.0, 394.0) 1354.0×132.0

### Script review

- From a topic to a verified, portable video.

## Scene `validate_repair`

- frames: `600–780`
- seconds: `20.0–26.0`
- object count: `14`

### Objects

- `validate_repair.checks.body.0` — text @ (1095.0, 360.0) 196.0×32.0
- `validate_repair.checks.body.1` — text @ (1067.0, 392.0) 252.0×32.0
- `validate_repair.checks.body.2` — text @ (1039.0, 424.0) 308.0×32.0
- `validate_repair.checks.detail` — text @ (1109.0, 472.0) 168.0×36.0
- `validate_repair.checks.panel` — rect @ (1004.0, 292.0) 378.0×168.0
- `validate_repair.checks.title` — text @ (1088.0, 314.0) 210.0×36.0
- `validate_repair.repaired.code_card` — code @ (538.0, 572.0) 378.0×168.0
- `validate_repair.repaired.detail` — text @ (615.0, 752.0) 224.0×36.0
- `validate_repair.repaired.title` — text @ (629.0, 594.0) 196.0×36.0
- `validate_repair.storyboard.body.0` — text @ (566.0, 360.0) 252.0×32.0
- `validate_repair.storyboard.body.1` — text @ (566.0, 392.0) 322.0×32.0
- `validate_repair.storyboard.code_card` — code @ (538.0, 292.0) 378.0×168.0
- `validate_repair.storyboard.detail` — text @ (629.0, 472.0) 196.0×36.0
- `validate_repair.storyboard.title` — text @ (629.0, 314.0) 196.0×36.0

### Script review

- viroc check surfaces typed VIR diagnostics so the storyboard is repaired before render.

