# Hand-written Manim (LLM-assisted) — bake-off approach 1, topic: rag-pipeline.
# Every box, position, color, and arrow is authored and tuned by hand. There is
# no schema and no validation: a typo in a label or a misplaced arrow is only
# visible after a full render.
from manim import *


class RagPipeline(Scene):
    def construct(self) -> None:
        self.camera.background_color = "#0e1116"
        title = Text(
            "How Retrieval-Augmented Generation Works", font_size=30, color="#e6edf3"
        ).to_edge(UP)
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

        documents = node("Documents", "#3b82f6")
        chunks = node("Chunks", "#14b8a6")
        embedder = node("Embedding Model", "#a855f7")
        vector_db = node("Vector DB", "#22c55e")
        llm = node("LLM", "#a855f7")

        row = VGroup(documents, chunks, embedder, vector_db, llm).arrange(RIGHT, buff=0.8)
        if row.width > 12.5:
            row.scale_to_fit_width(12.5)
        row.next_to(title, DOWN, buff=1.2)

        for box in (documents, chunks, embedder, vector_db, llm):
            self.play(FadeIn(box, shift=UP * 0.2), run_time=0.35)

        a1 = Arrow(documents.get_right(), chunks.get_left(), buff=0.12, stroke_width=3, color="#60a5fa")
        a2 = Arrow(chunks.get_right(), embedder.get_left(), buff=0.12, stroke_width=3, color="#34d399")
        a3 = Arrow(embedder.get_right(), vector_db.get_left(), buff=0.12, stroke_width=3, color="#4ade80")
        a4 = Arrow(vector_db.get_right(), llm.get_left(), buff=0.12, stroke_width=3, color="#8b949e")
        for arrow in (a1, a2, a3, a4):
            self.play(GrowArrow(arrow), run_time=0.3)

        caption = Text(
            "Documents are chunked, embedded, stored in a vector database, "
            "and retrieved to ground the LLM.",
            font_size=18, color="#8b949e",
        )
        if caption.width > 12.0:
            caption.scale_to_fit_width(12.0)
        caption.next_to(row, DOWN, buff=1.0)
        self.play(FadeIn(caption))
        self.wait(1.0)
