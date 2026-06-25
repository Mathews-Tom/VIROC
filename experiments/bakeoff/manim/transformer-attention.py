# Hand-written Manim (LLM-assisted) -- topic: transformer-attention.
from manim import *


class TransformerAttention(Scene):
    def construct(self) -> None:
        self.camera.background_color = "#0e1116"
        title = Text("Self-Attention in Transformers", font_size=30, color="#e6edf3").to_edge(UP)
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

        tokens = node("Input Tokens", "#3b82f6")
        embeddings = node("Embeddings", "#14b8a6")
        qkv = node("QKV Projections", "#a855f7")
        scores = node("Attention Scores", "#14b8a6")
        context = node("Context Vectors", "#22c55e")

        row = VGroup(tokens, embeddings, qkv, scores, context).arrange(RIGHT, buff=0.8)
        if row.width > 12.5:
            row.scale_to_fit_width(12.5)
        row.next_to(title, DOWN, buff=1.2)

        for box in (tokens, embeddings, qkv, scores, context):
            self.play(FadeIn(box, shift=UP * 0.2), run_time=0.35)

        e1 = Arrow(tokens.get_right(), embeddings.get_left(), buff=0.12, stroke_width=3, color="#34d399")
        e2 = Arrow(embeddings.get_right(), qkv.get_left(), buff=0.12, stroke_width=3, color="#60a5fa")
        e3 = Arrow(qkv.get_right(), scores.get_left(), buff=0.12, stroke_width=3, color="#f472b6")
        e4 = Arrow(scores.get_right(), context.get_left(), buff=0.12, stroke_width=3, color="#fbbf24")
        for arrow in (e1, e2, e3, e4):
            self.play(GrowArrow(arrow), run_time=0.3)

        caption = Text(
            "Tokens are embedded, projected into queries, keys, and values, "
            "scored by similarity, and combined into context vectors.",
            font_size=18, color="#8b949e",
        )
        if caption.width > 12.0:
            caption.scale_to_fit_width(12.0)
        caption.next_to(row, DOWN, buff=1.0)
        self.play(FadeIn(caption))
        self.wait(1.0)
