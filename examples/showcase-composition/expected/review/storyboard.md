# Static storyboard review

- adapter source version: `static-storyboard-source-v0.1`
- resolution: `1920x1080`
- fps: `30`
- scenes: `3`

## Scene `comparison`

- frames: `360–540`
- seconds: `12.0–18.0`
- object count: `10`

### Objects

- `comparison.compare.0` — arrow @ (916.0, 372.0) 88.0×8.0
- `comparison.compare.1` — arrow @ (916.0, 652.0) 88.0×8.0
- `comparison.html_path.panel` — rect @ (650.0, 292.0) 266.0×168.0
- `comparison.html_path.title` — text @ (720.0, 472.0) 126.0×36.0
- `comparison.html_source.code_card` — code @ (1004.0, 292.0) 266.0×168.0
- `comparison.html_source.title` — text @ (1067.0, 472.0) 140.0×36.0
- `comparison.remotion_path.panel` — rect @ (650.0, 572.0) 266.0×168.0
- `comparison.remotion_path.title` — text @ (692.0, 752.0) 182.0×36.0
- `comparison.remotion_source.code_card` — code @ (1004.0, 572.0) 266.0×168.0
- `comparison.remotion_source.title` — text @ (1032.0, 752.0) 210.0×36.0

### Script review

- Two portable backend paths compared side by side: HTML versus Remotion source.

## Scene `fanout`

- frames: `180–360`
- seconds: `6.0–12.0`
- object count: `11`

### Objects

- `fanout.build_manifest.evidence` — formula @ (1004.0, 712.0) 252.0×168.0
- `fanout.build_manifest.title` — text @ (1060.0, 892.0) 140.0×36.0
- `fanout.concrete_ir.code_card` — code @ (1004.0, 152.0) 252.0×168.0
- `fanout.concrete_ir.title` — text @ (1053.0, 332.0) 154.0×36.0
- `fanout.resolver.build_manifest.link` — arrow @ (916.0, 792.0) 88.0×8.0
- `fanout.resolver.concrete_ir.link` — arrow @ (916.0, 232.0) 88.0×8.0
- `fanout.resolver.panel` — rect @ (664.0, 432.0) 252.0×168.0
- `fanout.resolver.review_surface.link` — arrow @ (916.0, 512.0) 88.0×8.0
- `fanout.resolver.title` — text @ (734.0, 612.0) 112.0×36.0
- `fanout.review_surface.panel` — rect @ (1004.0, 432.0) 252.0×168.0
- `fanout.review_surface.title` — text @ (1032.0, 612.0) 196.0×36.0

### Script review

- One resolver fans out into Concrete IR, a review surface, and a build manifest.

## Scene `primitives`

- frames: `0–180`
- seconds: `0.0–6.0`
- object count: `8`

### Objects

- `primitives.author_note.callout` — rect @ (664.0, 572.0) 252.0×168.0
- `primitives.author_note.title` — text @ (713.0, 752.0) 154.0×36.0
- `primitives.input_panel.panel` — rect @ (664.0, 292.0) 252.0×168.0
- `primitives.input_panel.title` — text @ (692.0, 472.0) 196.0×36.0
- `primitives.ir_card.code_card` — code @ (1004.0, 292.0) 252.0×168.0
- `primitives.ir_card.title` — text @ (1053.0, 472.0) 154.0×36.0
- `primitives.proof_block.evidence` — formula @ (1004.0, 572.0) 252.0×168.0
- `primitives.proof_block.title` — text @ (1039.0, 752.0) 182.0×36.0

### Script review

- Showcase composes panels, code cards, callouts, and evidence blocks in a non-row grid.

