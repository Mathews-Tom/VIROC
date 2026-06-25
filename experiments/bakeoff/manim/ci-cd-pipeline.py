# Hand-written Manim (LLM-assisted) -- topic: ci-cd-pipeline.
from manim import *


class CiCdPipeline(Scene):
    def construct(self) -> None:
        self.camera.background_color = "#0e1116"
        title = Text("A CI/CD Pipeline", font_size=30, color="#e6edf3").to_edge(UP)
        self.play(FadeIn(title))

        def node(text: str, color: str) -> VGroup:
            rect = RoundedRectangle(
                corner_radius=0.12, width=2.4, height=1.0,
                color=color, fill_color=color, fill_opacity=0.18, stroke_width=2,
            )
            label = Text(text, font_size=18, color="#e6edf3")
            if label.width > rect.width - 0.3:
                label.scale_to_fit_width(rect.width - 0.3)
            label.move_to(rect.get_center())
            return VGroup(rect, label)

        commit = node("Commit", "#3b82f6")
        build = node("Build", "#f59e0b")
        test = node("Test", "#f59e0b")
        package = node("Package", "#14b8a6")
        deploy = node("Deploy", "#22c55e")

        row = VGroup(commit, build, test, package, deploy).arrange(RIGHT, buff=0.8)
        if row.width > 12.5:
            row.scale_to_fit_width(12.5)
        row.next_to(title, DOWN, buff=1.2)

        for box in (commit, build, test, package, deploy):
            self.play(FadeIn(box, shift=UP * 0.2), run_time=0.35)

        e1 = Arrow(commit.get_right(), build.get_left(), buff=0.12, stroke_width=3, color="#8b949e")
        e2 = Arrow(build.get_right(), test.get_left(), buff=0.12, stroke_width=3, color="#8b949e")
        e3 = Arrow(test.get_right(), package.get_left(), buff=0.12, stroke_width=3, color="#34d399")
        e4 = Arrow(package.get_right(), deploy.get_left(), buff=0.12, stroke_width=3, color="#4ade80")
        for arrow in (e1, e2, e3, e4):
            self.play(GrowArrow(arrow), run_time=0.3)

        caption = Text(
            "A commit triggers a build; the build is tested, packaged, and deployed.",
            font_size=18, color="#8b949e",
        )
        if caption.width > 12.0:
            caption.scale_to_fit_width(12.0)
        caption.next_to(row, DOWN, buff=1.0)
        self.play(FadeIn(caption))
        self.wait(1.0)
