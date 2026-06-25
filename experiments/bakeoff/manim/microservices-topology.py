# Hand-written Manim (LLM-assisted) -- topic: microservices-topology.
# The gateway fans out to both auth and orders, so the gateway->orders edge has
# to be routed by hand as a curved connector to avoid crossing the auth box.
from manim import *


class MicroservicesTopology(Scene):
    def construct(self) -> None:
        self.camera.background_color = "#0e1116"
        title = Text("A Microservices Topology", font_size=30, color="#e6edf3").to_edge(UP)
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

        gateway = node("API Gateway", "#f59e0b")
        auth = node("Auth Service", "#f59e0b")
        orders = node("Order Service", "#f59e0b")
        payments = node("Payment Service", "#f59e0b")
        db = node("Database", "#22c55e")

        row = VGroup(gateway, auth, orders, payments, db).arrange(RIGHT, buff=0.8)
        if row.width > 12.5:
            row.scale_to_fit_width(12.5)
        row.next_to(title, DOWN, buff=1.2)

        for box in (gateway, auth, orders, payments, db):
            self.play(FadeIn(box, shift=UP * 0.2), run_time=0.35)

        e1 = Arrow(gateway.get_right(), auth.get_left(), buff=0.12, stroke_width=3, color="#8b949e")
        fanout = CurvedArrow(gateway.get_bottom(), orders.get_bottom(), angle=-TAU / 6, stroke_width=3, color="#60a5fa")
        e3 = Arrow(orders.get_right(), payments.get_left(), buff=0.12, stroke_width=3, color="#8b949e")
        e4 = Arrow(payments.get_right(), db.get_left(), buff=0.12, stroke_width=3, color="#4ade80")
        self.play(GrowArrow(e1), run_time=0.3)
        self.play(Create(fanout), run_time=0.3)
        self.play(GrowArrow(e3), run_time=0.3)
        self.play(GrowArrow(e4), run_time=0.3)

        caption = Text(
            "The gateway authenticates requests and routes orders through the "
            "payment service to the database.",
            font_size=18, color="#8b949e",
        )
        if caption.width > 12.0:
            caption.scale_to_fit_width(12.0)
        caption.next_to(row, DOWN, buff=1.0)
        self.play(FadeIn(caption))
        self.wait(1.0)
