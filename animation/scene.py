"""
SOPAL Smart Core Warehouse — 2D front-view routing animation.

Hard-coded, self-contained Manim scene. The choreography is computed by a
mirror of the storage.c allocator rules (FIFO free pool + per-type FIFO
queues), so the routing shown is exactly the firmware's algorithm. The free
pool is seeded so that consecutive allocations land in separate column bands
(same policy freedom as storage_init's lane order).

Render:
    manim -qm scene.py RackRouting          # 720p30 draft
    manim -qh scene.py RackRouting          # 1080p60 final
    FAST=1 manim -ql scene.py RackRouting   # quick render for frame review
"""

import os
from collections import deque

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    PI,
    AnimationGroup,
    Arrow,
    Circle,
    Create,
    FadeIn,
    FadeOut,
    Flash,
    Group,
    Indicate,
    Line,
    Paragraph,
    Rectangle,
    ReplacementTransform,
    Rotate,
    RoundedRectangle,
    Scene,
    SurroundingRectangle,
    Text,
    VGroup,
    Write,
    config,
)

# Rack division — from storage.h -------------------------------------------
SHELF_WIDTH = 15      # lanes per shelf (horizontal)
SHELF_COUNT = 26      # shelves (vertical)
LANE_LENGTH = 10      # belt segments per lane (into depth)
ROOM_W = 6.0          # m, front face = 6 x 6 m
ROOM_H = 6.0

LANE_W = ROOM_W / SHELF_WIDTH        # 0.4 m lane pitch
SHELF_H = ROOM_H / SHELF_COUNT       # 0.231 m shelf pitch

# Palette -------------------------------------------------------------------
BG = "#0e1116"
RACK_LINE = "#4a5560"
LANE_FREE = "#1a2027"
STATE_USED = "#f9a825"     # used-but-not-full
STATE_FULL = "#e53935"     # full
STATE_USED_FILL = "#7a5c10"
STATE_FULL_FILL = "#7a1d1d"
ACCENT = "#00e5ff"         # selector / MCU highlights
READY = "#7cb342"          # cured, past the 24 h threshold

TYPE_COLORS = {
    "A": "#00bcd4",
    "B": "#ab47bc",
}

TEXT = "#e8eaed"
SUBTLE = "#9aa0a6"

# Hard-coded choreography ----------------------------------------------------
# Inputs alternate between the two types; type A arrives at a higher rate
# (14 vs 10) and is the only type that overflows into a second lane.
EVENTS = [t for _ in range(10) for t in ("A", "B")] + ["A"] * 4
FETCH = ("A", 13)  # production demand: 13 cores of type A

FAST = os.environ.get("FAST") is not None  # quick render for frame review


def wait(self, t):
    self.wait(0.12 if FAST else t)


class Choreography:
    """Mirror of the storage.c allocator: FIFO free pool + per-type FIFO."""

    def __init__(self):
        n = SHELF_WIDTH * SHELF_COUNT
        # seed: lanes ordered by column band (col % 5), rows interleaved with
        # stride 7 (coprime with 26) — consecutive allocations spread over the
        # rack face instead of piling onto one shelf row
        row_order = [(r * 7) % SHELF_COUNT for r in range(SHELF_COUNT)]
        pool = [i for band in range(5) for row in row_order
                for i in range(n)
                if i // SHELF_WIDTH == row and (i % SHELF_WIDTH) % 5 == band]
        self.free_pool = deque(pool)
        self.queues = {t: deque() for t in TYPE_COLORS}
        self.active = {}
        self.fill = [0] * n

    def pos(self, idx):
        return (idx % SHELF_WIDTH, idx // SHELF_WIDTH)

    def alloc(self, t):
        idx = self.free_pool.popleft()
        self.queues[t].append(idx)
        return idx

    def place_box(self, t):
        lane = self.active.get(t)
        if lane is None or self.fill[lane] >= LANE_LENGTH:
            lane = self.alloc(t)
            self.active[t] = lane
        self.fill[lane] += 1
        return lane, self.fill[lane]

    def state(self, idx):
        if self.fill[idx] == 0:
            return 0
        if self.fill[idx] >= LANE_LENGTH:
            return 2
        return 1

    def fetch(self, t, n):
        """Yield (lane, k): k boxes leave the oldest lane; mirrors free_lane."""
        while n > 0:
            lane = self.queues[t][0]
            take = min(n, self.fill[lane])
            self.fill[lane] -= take
            n -= take
            if self.fill[lane] == 0:
                self.queues[t].popleft()
                self.free_pool.append(lane)
                self.active[t] = None
            yield lane, take


class RackRouting(Scene):
    def construct(self):
        config.background_color = BG
        self.ch = Choreography()
        self.lane_states = {}
        self.lane_prev = {}

        self.title()
        self.build_rack()
        self.show_legend()
        self.phase_arrivals()
        self.phase_cure()
        self.phase_fetch()
        self.outro()

    # -- static layout ------------------------------------------------------

    def title(self):
        self.t_main = Text("Smart Core Warehouse — box routing", font_size=30,
                           color=TEXT).to_edge(UP, buff=0.25)
        self.play(Write(self.t_main), run_time=1.2)
        wait(self, 0.4)

    def cell_center(self, col, row):
        x = self.rack_x0 + LANE_W * (col + 0.5)
        y = self.rack_y0 + SHELF_H * (row + 0.5)
        return x, y

    def build_rack(self):
        w, h = ROOM_W, ROOM_H
        self.rack_x0, self.rack_y0 = -6.5, -3.4
        x0, y0 = self.rack_x0, self.rack_y0

        hlines = VGroup(*[
            Line([x0, y0 + SHELF_H * i, 0], [x0 + w, y0 + SHELF_H * i, 0],
                 stroke_width=1.0, color=RACK_LINE)
            for i in range(SHELF_COUNT + 1)
        ])
        vlines = VGroup(*[
            Line([x0 + LANE_W * i, y0, 0], [x0 + LANE_W * i, y0 + h, 0],
                 stroke_width=1.0, color=RACK_LINE)
            for i in range(SHELF_WIDTH + 1)
        ])
        frame = SurroundingRectangle(
            hlines + vlines, color=RACK_LINE, stroke_width=2.0, buff=0.0)

        free_tint = Rectangle(width=w, height=h, stroke_width=0,
                              fill_color=LANE_FREE, fill_opacity=1.0)
        free_tint.move_to([x0 + w / 2, y0 + h / 2, 0])

        # persistent input rail above the rack
        self.rail_y = y0 + h + 0.06
        rail = Line([x0, self.rail_y, 0], [x0 + w, self.rail_y, 0],
                    color=RACK_LINE, stroke_width=3)

        self.play(Create(free_tint), Create(frame), Create(hlines),
                  Create(vlines), Create(rail), run_time=1.6)
        self.rack_frame = frame
        self.say("15 lanes × 26 shelves × 10 positions — room 6 × 6 × 6 m",
                 run=0.9)
        wait(self, 0.5)

    def show_legend(self):
        sw = 0.32
        items = [
            (LANE_FREE, "free", "#252c34"),
            (STATE_USED, "in use — not full", STATE_USED_FILL),
            (STATE_FULL, "full", STATE_FULL_FILL),
        ]
        legend = VGroup()
        for color, label, fillc in items:
            swatch = RoundedRectangle(
                corner_radius=0.04, width=sw, height=sw,
                stroke_color=color, stroke_width=1.5,
                fill_color=fillc, fill_opacity=1.0)
            txt = Text(label, font_size=20, color=TEXT)
            legend.add(VGroup(swatch, txt).arrange(RIGHT, buff=0.12))
        legend.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        legend.to_edge(RIGHT, buff=0.4).to_edge(UP, buff=0.9)

        note = Text("first in → first out (24 h cure)", font_size=18,
                    color=SUBTLE).next_to(legend, DOWN, buff=0.3)

        self.legend = legend
        self.legend_note = note
        self.play(FadeIn(legend), FadeIn(note), run_time=1.0)
        wait(self, 0.6)

    def mcu_panel(self):
        chip = RoundedRectangle(corner_radius=0.06, width=1.6, height=0.7,
                                stroke_color=ACCENT, stroke_width=1.5)
        chip_txt = Text("STM32F407", font_size=16, color=ACCENT).move_to(chip)
        panel = VGroup(chip, chip_txt).arrange(DOWN, buff=0.08)
        panel.next_to(self.legend, DOWN, buff=0.7)
        panel.align_to(self.legend, LEFT)
        self.play(FadeIn(panel), run_time=0.5)
        self.mcu_panel_m = panel
        self.mcu_label = Text("", font_size=18, color=TEXT)
        self.mcu_label.next_to(panel, DOWN, buff=0.15)
        self.add(self.mcu_label)

    def say(self, txt, run=0.7):
        cap = Text(txt, font_size=22, color=TEXT)
        cap.next_to(self.t_main, DOWN, buff=0.15)
        cap.align_to(self.rack_frame, LEFT)
        if getattr(self, "caption", None) is not None:
            self.play(FadeOut(self.caption), FadeIn(cap), run_time=run)
        else:
            self.play(FadeIn(cap), run_time=run)
        self.caption = cap

    # -- lane state on the rack ---------------------------------------------

    def lane_cell(self, idx):
        col, row = self.ch.pos(idx)
        x, y = self.cell_center(col, row)
        cell = Rectangle(width=LANE_W - 0.035, height=SHELF_H - 0.02,
                         stroke_width=0)
        cell.move_to([x, y, 0])
        return cell

    def set_state(self, idx):
        st = self.ch.state(idx)
        old = self.lane_states.pop(idx, None)
        if old is not None:
            self.remove(*old)
        prev = self.lane_prev.get(idx, 0)
        self.lane_prev[idx] = st

        if st == 0:
            sw = self.legend[0][0]
            if prev != 0:
                self.play(Indicate(sw, color=SUBTLE, scale_factor=1.25),
                          run_time=0.4)
            return
        fillc = STATE_USED_FILL if st == 1 else STATE_FULL_FILL
        stroke = STATE_USED if st == 1 else STATE_FULL
        cell = self.lane_cell(idx).set_stroke(stroke, 2.4)
        cell.set_fill(fillc, 1.0)
        bar = Rectangle(
            width=(LANE_W - 0.09) * (self.ch.fill[idx] / LANE_LENGTH),
            height=0.06, stroke_width=0, fill_color=stroke, fill_opacity=1.0)
        x, y = self.cell_center(*self.ch.pos(idx))
        bar.move_to([x, y - SHELF_H * 0.32, 0])
        count = Text(str(self.ch.fill[idx]), font_size=15, weight="BOLD",
                     color=TEXT)
        count.set_stroke(color=BG, width=1.2)
        count.move_to([x, y + SHELF_H * 0.18, 0])
        self.add(cell, bar, count)
        self.lane_states[idx] = (cell, bar, count)

        if st != prev or prev == 0:
            sw = self.legend[st][0]
            self.play(Indicate(sw, color=stroke, scale_factor=1.25),
                      run_time=0.4)

    # -- inset: lane cross-section with conditional belt segments -----------

    def build_inset(self):
        panel_w, panel_h = 6.4, 2.0
        panel = RoundedRectangle(corner_radius=0.08, width=panel_w,
                                 height=panel_h, stroke_color=RACK_LINE,
                                 stroke_width=1.5)
        panel.to_edge(RIGHT, buff=0.35).to_edge(DOWN, buff=0.45)
        title = Text("lane cross-section — 10 belt segments", font_size=18,
                     color=SUBTLE)
        title.move_to([panel.get_center()[0], panel.get_top()[1] - 0.16, 0])

        seg_w = (panel_w - 0.5) / LANE_LENGTH
        x0 = panel.get_left()[0] + 0.30
        y_seg = panel.get_center()[1] - 0.08

        rollers = VGroup()
        seg_cells = VGroup()
        cells = []
        for i in range(LANE_LENGTH):
            cx = x0 + seg_w * (i + 0.5)
            seg_cells.add(RoundedRectangle(
                corner_radius=0.02, width=seg_w * 0.94, height=0.62,
                stroke_color=RACK_LINE, stroke_width=1.2).move_to([cx, y_seg, 0]))
            r1 = Circle(radius=0.07, color=SUBTLE, stroke_width=1.4)
            r2 = r1.copy()
            r1.move_to([cx - seg_w * 0.22, y_seg - 0.22, 0])
            r2.move_to([cx + seg_w * 0.22, y_seg - 0.22, 0])
            rollers.add(r1, r2)
            cells.append(cx)

        box = RoundedRectangle(
            corner_radius=0.03, width=seg_w * 0.82, height=0.30,
            fill_color=TYPE_COLORS["A"], fill_opacity=0.9, stroke_width=0)
        box.move_to([x0 + seg_w * 0.5, y_seg - 0.02, 0])

        in_lbl = Text("in", font_size=16, color=ACCENT)
        in_lbl.next_to(seg_cells, LEFT, buff=0.08)
        out_lbl = Text("out", font_size=16, color=ACCENT)
        out_lbl.next_to(seg_cells, RIGHT, buff=0.08)

        self.inset = Group(panel, seg_cells, rollers, box, in_lbl, out_lbl)
        self.inset_title = title
        self.inset_box = box
        self.inset_rollers = rollers
        self.inset_seg_w = seg_w
        self.inset_x0 = x0
        self.inset_y = y_seg
        self.inset_cells = cells

    def show_inset(self, box_type):
        if not hasattr(self, "inset"):
            self.build_inset()
            self.inset_box.set_fill(TYPE_COLORS[box_type], 0.9)
            self.play(FadeIn(self.inset), FadeIn(self.inset_title), run_time=0.6)
        else:
            self.inset_box.set_fill(TYPE_COLORS[box_type], 0.9)
            self.play(self.inset_box.animate.move_to(
                [self.inset_x0 + self.inset_seg_w * 0.5, self.inset_y, 0]),
                run_time=0.3)

    def belt_sequence(self, dock_slot, fast):
        """Drive segments one after another until the box docks behind the
        previous one. Segments right of the parked boxes are never powered."""
        if dock_slot > 0 and not fast:
            skip = Text("segments beyond stay unpowered — box ahead",
                        font_size=16, color=SUBTLE)
            skip.next_to(self.inset, DOWN, buff=0.08)
            self.play(FadeIn(skip), run_time=0.4)
            self.wait(0.6)
            self.play(FadeOut(skip), run_time=0.3)

        rides = list(range(LANE_LENGTH - dock_slot))
        target_x = self.inset_x0 + self.inset_seg_w * (
            LANE_LENGTH - dock_slot - 0.5)
        for i, seg in enumerate(rides):
            r1, r2 = self.inset_rollers[seg * 2], self.inset_rollers[seg * 2 + 1]
            if i == len(rides) - 1:
                nx = target_x
            else:
                nx = self.inset_cells[seg + 1]
            run = 0.22 if fast else 0.7
            self.play(
                AnimationGroup(
                    Rotate(r1, angle=-PI, about_point=r1.get_center()),
                    Rotate(r2, angle=-PI, about_point=r2.get_center()),
                    self.inset_box.animate.move_to([nx, self.inset_y, 0]),
                ),
                run_time=run)
        wait(self, 0.3)

    def hide_inset(self):
        if hasattr(self, "inset"):
            self.play(FadeOut(self.inset), FadeOut(self.inset_title),
                      run_time=0.5)

    # -- arrival ------------------------------------------------------------

    def arrival(self, box_type, fast=False, semi=False):
        lane, count = self.ch.place_box(box_type)
        col, row = self.ch.pos(lane)
        x, y = self.cell_center(col, row)

        # the overflow story beat: this type's previous lane filled up, so a
        # fresh lane is opened from the free pool (fires exactly once)
        if count == 1 and len(self.ch.queues[box_type]) > 1:
            self.say(f"lane full — {box_type} boxes now route to a new lane "
                     f"({col}, {row})", run=0.9)
            self.wait(1.2 if not FAST else 0.2)

        if semi or not fast:
            if not hasattr(self, "mcu_panel_m"):
                self.mcu_panel()
            self.play(Indicate(self.mcu_panel_m[0], color=ACCENT), run_time=0.4)
            new_lbl = Text(f"lane ({col}, {row})", font_size=18, color=TEXT)
            new_lbl.next_to(self.mcu_panel_m, DOWN, buff=0.15)
            self.play(ReplacementTransform(self.mcu_label, new_lbl),
                      run_time=0.3)
            self.mcu_label = new_lbl
            self.say(f"box of type {box_type} → lane ({col}, {row})")

        # input rail along the top, selector picks the column
        box = RoundedRectangle(
            corner_radius=0.04, width=LANE_W * 0.8, height=LANE_W * 0.8,
            fill_color=TYPE_COLORS[box_type], fill_opacity=0.9, stroke_width=0)
        box.move_to([self.rack_x0 - 0.05, self.rail_y, 0])
        self.add(box)
        if semi:
            head = Arrow(box.get_center(), [x, self.rail_y, 0], color=ACCENT,
                         stroke_width=3, buff=0,
                         max_tip_length_to_length_ratio=0.12)
            self.play(Create(head), box.animate.move_to([x, self.rail_y, 0]),
                      run_time=0.7)
            self.play(FadeOut(head), box.animate.move_to([x, y, 0]).scale(0.62),
                      run_time=0.6)
            self.remove(box)
        elif not fast:
            head = Arrow(box.get_center(), [x, self.rail_y, 0], color=ACCENT,
                         stroke_width=3, buff=0,
                         max_tip_length_to_length_ratio=0.12)
            self.play(Create(head), box.animate.move_to([x, self.rail_y, 0]),
                      run_time=1.0)
            self.play(FadeOut(head), box.animate.move_to([x, y, 0]).scale(0.62),
                      run_time=0.8)
            self.show_inset(box_type)
            self.belt_sequence(count - 1, fast=False)
            self.play(FadeOut(box), run_time=0.4)
            if count == LANE_LENGTH:
                self.say(f"lane ({col}, {row}) full — next {box_type} box "
                         "gets a new lane")
        else:
            if hasattr(self, "inset"):
                self.inset_box.set_fill(TYPE_COLORS[box_type], 0.9)
                self.inset_box.move_to([
                    self.inset_x0
                    + self.inset_seg_w * (LANE_LENGTH - (count - 1) - 0.5),
                    self.inset_y, 0])
            self.play(box.animate.move_to([x, self.rail_y, 0]), run_time=0.15)
            self.play(box.animate.move_to([x, y, 0]).scale(0.62), run_time=0.2)
            self.remove(box)

        self.set_state(lane)
        return lane

    def phase_arrivals(self):
        for i, t in enumerate(EVENTS):
            self.arrival(t, fast=i > 1, semi=i == 1)
            if i == 1 and getattr(self, "caption", None) is not None:
                self.play(FadeOut(self.caption), run_time=0.4)
                self.caption = None
        wait(self, 0.4)

    # -- cure tracking --------------------------------------------------------

    def phase_cure(self):
        self.say("24 h drying — first boxes in are the first ones ready")
        clock = Text("elapsed: 0 h", font_size=20, color=SUBTLE)
        clock.move_to([5.6, -0.85, 0])
        self.play(FadeIn(clock), run_time=0.5)

        for h in (6, 12, 18, 24):
            new_clock = Text(f"elapsed: {h} h", font_size=20,
                             color=READY if h >= 24 else SUBTLE)
            new_clock.move_to([5.6, -0.85, 0])
            self.play(ReplacementTransform(clock, new_clock), run_time=0.4)
            clock = new_clock
        tick = Text("✓", font_size=26, color=READY)
        tick.next_to(clock, RIGHT, buff=0.15)
        self.play(FadeIn(tick), run_time=0.3)
        wait(self, 0.6)

    # -- fetch ----------------------------------------------------------------

    def phase_fetch(self):
        t, n = FETCH
        self.say(f"production demand: fetch {n} cores of type {t} — FIFO",
                 run=0.9)

        out_y = self.rack_y0 - 0.35
        out_line = Line([self.rack_x0, out_y, 0],
                        [self.rack_x0 + ROOM_W, out_y, 0],
                        color=ACCENT, stroke_width=5)
        out_lbl = Text("output", font_size=16, color=SUBTLE)
        out_lbl.next_to(out_line, UP, buff=0.08)
        out_lbl.align_to(out_line, RIGHT)
        self.play(Create(out_line), FadeIn(out_lbl), run_time=0.6)

        if not hasattr(self, "inset"):
            self.build_inset()
            self.play(FadeIn(self.inset), FadeIn(self.inset_title),
                      run_time=0.5)
        self.inset_box.set_fill(TYPE_COLORS[t], 0.9)
        self.inset_box.set_opacity(0)  # a convoy of copies replaces it here

        convoy = None
        for lane, take in self.ch.fetch(t, n):
            col, row = self.ch.pos(lane)
            x, y = self.cell_center(col, row)
            self.say(f"oldest lane ({col}, {row}) → {take} of "
                     f"{take + self.ch.fill[lane]} box(es)")
            if hasattr(self, "mcu_panel_m"):
                new_lbl = Text(f"lane ({col}, {row})", font_size=18, color=TEXT)
                new_lbl.next_to(self.mcu_panel_m, DOWN, buff=0.15)
                self.play(ReplacementTransform(self.mcu_label, new_lbl),
                          run_time=0.3)
                self.mcu_label = new_lbl

            # cross-section convoy: the lane's parked boxes, front at the
            # out end; each exit frees a slot and the rest advance one segment
            n0 = take + self.ch.fill[lane]
            self.ch.fill[lane] = n0
            if convoy:
                self.remove(*convoy)
            convoy = [
                RoundedRectangle(
                    corner_radius=0.03, width=self.inset_seg_w * 0.82,
                    height=0.30, fill_color=TYPE_COLORS[t], fill_opacity=0.9,
                    stroke_width=0)
                for _ in range(n0)
            ]
            for k, b in enumerate(convoy):
                b.move_to([self.inset_cells[LANE_LENGTH - n0 + k],
                           self.inset_y, 0])
            self.add(*convoy)

            run = 0.2 if FAST else 0.35
            for _ in range(take):
                exiting = convoy.pop()
                box = RoundedRectangle(
                    corner_radius=0.04, width=LANE_W * 0.5,
                    height=LANE_W * 0.5,
                    fill_color=TYPE_COLORS[t], fill_opacity=0.9, stroke_width=0)
                box.move_to([x, y - SHELF_H * 0.6, 0])
                self.add(box)
                self.play(
                    exiting.animate.move_to(
                        [self.inset_x0 + self.inset_seg_w * LANE_LENGTH + 0.1,
                         self.inset_y, 0]),
                    box.animate.move_to([x, out_y, 0]).scale(1.1),
                    run_time=run)
                self.play(
                    box.animate.shift(
                        RIGHT * (config.frame_width / 2 + 0.8 - x)),
                    exiting.animate.shift(RIGHT * 0.6),
                    *[b.animate.shift(RIGHT * self.inset_seg_w)
                      for b in convoy],
                    run_time=run)
                self.remove(box, exiting)
                self.ch.fill[lane] -= 1
                self.set_state(lane)

        self.play(FadeOut(out_line), FadeOut(out_lbl), run_time=0.5)

    # -- outro ----------------------------------------------------------------

    def outro(self):
        self.hide_inset()
        recap = VGroup(*[
            Text(s, font_size=17, color=TEXT) for s in [
                "• free lanes stay at the front of the pool (FIFO reuse)",
                "• each type keeps its own FIFO of lanes",
                "• belt segments only run until a box docks",
                "• the 24 h threshold decides readiness",
            ]
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        recap.move_to([3.9, -2.0, 0])
        self.play(FadeOut(self.caption), Write(recap), run_time=1.2)
        wait(self, 2.0)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)
