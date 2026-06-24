# VIROC - Video Intermediate Representation & Open Compiler

Typed storyboards. Validated before they render.

VIROC is an open-source toolchain that turns a typed, validatable storyboard (VidIR) into technical-explainer videos. It type-checks and validates the storyboard — layout, timing, references — before rendering, then compiles it deterministically into an animation backend's source code. Technical videos become reviewable in a PR, testable in CI, and reproducible by build. Built for the cases where being correct matters more than being cinematic: architecture, ML concepts, algorithms.
