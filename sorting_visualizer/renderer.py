from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from sorting_visualizer import config
from sorting_visualizer.drawing import darken, draw_glow, draw_panel, exp_lerp, lighten, mix_color, with_alpha
from sorting_visualizer.sorting import SortEvent


@dataclass(slots=True)
class BarSprite:
    identifier: int
    value: int
    current_x: float
    target_x: float
    current_width: float
    target_width: float
    current_height: float
    target_height: float
    transient_state: str = ""
    transient_timer: float = 0.0
    sorted_locked: bool = False
    pulse: float = 0.0
    age: float = 0.0
    arrival_delay: float = 0.0


def draw_scene_background(surface: pygame.Surface, phase: float) -> None:
    width, height = surface.get_size()

    for y in range(height):
        blend = y / max(height - 1, 1)
        color = mix_color(config.BACKGROUND_TOP, config.BACKGROUND_BOTTOM, blend)
        pygame.draw.line(surface, color, (0, y), (width, y))

    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    auroras = [
        (config.AURORA_ONE, (width * 0.18 + math.sin(phase * 0.30) * 24, height * 0.20), (420, 280), 26),
        (config.AURORA_TWO, (width * 0.84 + math.cos(phase * 0.22) * 28, height * 0.18), (360, 260), 24),
        (config.AURORA_THREE, (width * 0.68 + math.sin(phase * 0.18) * 36, height * 0.84), (540, 320), 22),
    ]
    for color, center, size, alpha in auroras:
        rect = pygame.Rect(0, 0, size[0], size[1])
        rect.center = (int(center[0]), int(center[1]))
        pygame.draw.ellipse(overlay, with_alpha(color, alpha), rect)
        pygame.draw.ellipse(overlay, with_alpha(color, alpha * 0.45), rect.inflate(160, 120))

    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(vignette, (0, 0, 0, 32), vignette.get_rect(), width=120, border_radius=0)
    surface.blit(overlay, (0, 0))
    surface.blit(vignette, (0, 0))


class BarVisualizer:
    def __init__(self, scale: float = 1.0) -> None:
        self.scale = scale
        self.bars: list[BarSprite] = []
        self.canvas = pygame.Rect(0, 0, 0, 0)
        self.value_ceiling = 1
        self._next_identifier = 1
        self.finish_active = False
        self.finish_timer = 0.0
        self.finish_cursor = -1
        self.set_scale(scale)

    def set_scale(self, scale: float) -> None:
        self.scale = scale
        self.kicker_font = pygame.font.SysFont(config.FONT_NAME, self.s(12), bold=True)
        self.heading_font = pygame.font.SysFont(config.FONT_NAME, self.s(28), bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, self.s(16))
        self.small_font = pygame.font.SysFont(config.FONT_NAME, self.s(14))
        self._recalculate_targets()

    def s(self, value: int | float) -> int:
        return max(1, int(round(value * self.scale)))

    @property
    def is_completion_active(self) -> bool:
        return self.finish_active

    @property
    def sorted_count(self) -> int:
        return sum(1 for bar in self.bars if bar.sorted_locked)

    def set_canvas(self, rect: pygame.Rect) -> None:
        if rect.size != self.canvas.size or rect.topleft != self.canvas.topleft:
            self.canvas = rect.copy()
            self._recalculate_targets()

    def set_data(self, values: list[int], *, animate: bool = True) -> None:
        self.value_ceiling = max(values, default=1)
        self.bars = []
        self.finish_active = False
        self.finish_timer = 0.0
        self.finish_cursor = -1

        for index, value in enumerate(values):
            target_x, target_width = self._target_slot(index, len(values))
            target_height = self._height_for_value(value)
            current_height = 0.0 if animate else target_height
            bar = BarSprite(
                identifier=self._next_identifier,
                value=value,
                current_x=target_x,
                target_x=target_x,
                current_width=target_width,
                target_width=target_width,
                current_height=current_height,
                target_height=target_height,
                arrival_delay=index * 0.006 if animate else 0.0,
            )
            self._next_identifier += 1
            self.bars.append(bar)

    def snapshot_values(self) -> list[int]:
        return [bar.value for bar in self.bars]

    def prepare_for_sort(self) -> None:
        self.finish_active = False
        self.finish_timer = 0.0
        self.finish_cursor = -1
        for bar in self.bars:
            bar.transient_state = ""
            bar.transient_timer = 0.0
            bar.sorted_locked = False
            bar.pulse = 0.0

    def start_completion_animation(self) -> None:
        self.finish_active = True
        self.finish_timer = 0.0
        self.finish_cursor = -1
        for bar in self.bars:
            bar.transient_state = ""
            bar.transient_timer = 0.0
            bar.pulse = max(bar.pulse, 0.2)

    def apply_event(self, event: SortEvent) -> None:
        if event.kind == "compare":
            for index in event.indices:
                if 0 <= index < len(self.bars):
                    bar = self.bars[index]
                    bar.transient_state = "compare"
                    bar.transient_timer = config.BAR_COMPARE_DURATION
                    bar.pulse = max(bar.pulse, 0.95)

        elif event.kind == "swap" and len(event.indices) == 2:
            first, second = event.indices
            if first == second or not (0 <= first < len(self.bars) and 0 <= second < len(self.bars)):
                return
            self.bars[first], self.bars[second] = self.bars[second], self.bars[first]
            for bar in (self.bars[first], self.bars[second]):
                bar.transient_state = "update"
                bar.transient_timer = config.BAR_SWAP_DURATION
                bar.pulse = max(bar.pulse, 1.18)
            self._recalculate_targets()

        elif event.kind == "overwrite" and event.indices and event.values:
            index = event.indices[0]
            value = event.values[0]
            if 0 <= index < len(self.bars):
                bar = self.bars[index]
                bar.value = value
                bar.target_height = self._height_for_value(value)
                bar.transient_state = "update"
                bar.transient_timer = config.BAR_WRITE_DURATION
                bar.pulse = max(bar.pulse, 1.08)

        elif event.kind == "mark_sorted":
            for index in event.indices:
                if 0 <= index < len(self.bars):
                    bar = self.bars[index]
                    bar.sorted_locked = True
                    bar.pulse = max(bar.pulse, 0.95)

    def update(self, dt: float) -> None:
        for bar in self.bars:
            bar.age += dt

            target_height = bar.target_height if bar.age >= bar.arrival_delay else 0.0
            bar.current_x = exp_lerp(bar.current_x, bar.target_x, config.POSITION_SPRING, dt)
            bar.current_width = exp_lerp(bar.current_width, bar.target_width, config.WIDTH_SPRING, dt)
            bar.current_height = exp_lerp(bar.current_height, target_height, config.HEIGHT_SPRING, dt)

            if bar.transient_timer > 0:
                bar.transient_timer = max(0.0, bar.transient_timer - dt)
                if bar.transient_timer == 0 and not bar.sorted_locked:
                    bar.transient_state = ""

            bar.pulse = max(0.0, bar.pulse - dt * config.FINISH_PULSE_DECAY)

        if self.finish_active and self.bars:
            self.finish_timer += dt
            target_cursor = min(len(self.bars) - 1, int(self.finish_timer / config.FINISH_STAGGER))
            while self.finish_cursor < target_cursor:
                self.finish_cursor += 1
                bar = self.bars[self.finish_cursor]
                bar.sorted_locked = True
                bar.pulse = max(bar.pulse, 1.28)
            if self.finish_cursor >= len(self.bars) - 1 and self.finish_timer > len(self.bars) * config.FINISH_STAGGER + 0.72:
                self.finish_active = False

    def draw(
        self,
        surface: pygame.Surface,
        card_rect: pygame.Rect,
        header_rect: pygame.Rect,
        algorithm_label: str,
        status_label: str,
        status_detail: str,
    ) -> None:
        draw_panel(
            surface,
            card_rect,
            config.PANEL_FILL,
            config.CANVAS_BORDER,
            self.s(config.PANEL_RADIUS),
            glow_color=config.ACCENT,
            glow_strength=0.11,
            shadow_alpha=62,
            border_alpha=132,
            gloss_alpha=12,
        )
        self._draw_header(surface, header_rect, algorithm_label, status_label, status_detail)
        self._draw_canvas(surface, self.canvas)

    def _draw_header(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        algorithm_label: str,
        status_label: str,
        status_detail: str,
    ) -> None:
        left = rect.x
        top = rect.y
        surface.blit(self.kicker_font.render("ACTIVE ALGORITHM", True, config.TEXT_SECONDARY), (left, top + self.s(2)))
        surface.blit(self.heading_font.render(algorithm_label, True, config.TEXT_PRIMARY), (left, top + self.s(16)))
        surface.blit(self.body_font.render(status_detail, True, config.TEXT_SECONDARY), (left, top + self.s(48)))

        pill_rect = pygame.Rect(rect.right - self.s(134), top + self.s(14), self.s(134), self.s(32))
        self._draw_status_pill(surface, pill_rect, status_label)
        pygame.draw.line(
            surface,
            with_alpha(config.GRID_LINE, 148),
            (rect.x, rect.bottom + self.s(1)),
            (rect.right, rect.bottom + self.s(1)),
            1,
        )

    def _draw_status_pill(self, surface: pygame.Surface, rect: pygame.Rect, status_label: str) -> None:
        if status_label == "Sorting":
            accent = config.ACCENT
        elif status_label == "Finished":
            accent = config.SUCCESS
        elif status_label == "Paused":
            accent = config.WARNING
        else:
            accent = config.PANEL_BORDER

        draw_panel(
            surface,
            rect,
            mix_color(config.PANEL_INNER, accent, 0.13),
            mix_color(config.PANEL_BORDER, accent, 0.35),
            self.s(16),
            glow_color=accent,
            glow_strength=0.1,
            shadow_alpha=18,
            border_alpha=100,
            gloss_alpha=12,
        )
        dot = (rect.x + self.s(16), rect.centery)
        pulse = 0.55 + abs(math.sin(pygame.time.get_ticks() / 340.0)) * 0.45 if status_label == "Sorting" else 0.9
        pygame.draw.circle(surface, lighten(accent, 0.12), dot, self.s(4))
        draw_glow(surface, pygame.Rect(dot[0] - self.s(3), dot[1] - self.s(3), self.s(6), self.s(6)), accent, self.s(6), 0.18 * pulse, layers=2)
        label = self.small_font.render(status_label.upper(), True, lighten(accent, 0.32) if accent != config.PANEL_BORDER else config.TEXT_SECONDARY)
        surface.blit(label, label.get_rect(midleft=(rect.x + self.s(28), rect.centery)))

    def _draw_canvas(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if rect.width <= 0 or rect.height <= 0:
            return

        inner = pygame.Surface(rect.size, pygame.SRCALPHA)
        inner_rect = inner.get_rect()
        radius = self.s(24)
        pygame.draw.rect(inner, with_alpha(config.PANEL_INNER, 242), inner_rect, border_radius=radius)
        pygame.draw.rect(inner, with_alpha(config.CANVAS_BORDER, 126), inner_rect, width=1, border_radius=radius)
        gloss = pygame.Rect(0, 0, rect.width, max(self.s(24), rect.height // 8))
        pygame.draw.rect(inner, with_alpha(lighten(config.PANEL_INNER, 0.1), 14), gloss, border_radius=radius)
        surface.blit(inner, rect.topleft)

        self._draw_grid(surface, rect)

        previous_clip = surface.get_clip()
        clip_inset = self.s(8)
        surface.set_clip(rect.inflate(-clip_inset, -clip_inset))
        ordered = sorted(self.bars, key=self._draw_priority)
        for bar in ordered:
            self._draw_bar(surface, rect, bar)
        surface.set_clip(previous_clip)

    def _draw_grid(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        for index in range(1, 5):
            y = rect.bottom - self.s(14) - int((rect.height - self.s(28)) * index / 5)
            alpha = 118 if index < 4 else 148
            pygame.draw.line(surface, with_alpha(config.GRID_LINE, alpha), (rect.x + self.s(12), y), (rect.right - self.s(12), y), 1)

    def _draw_bar(self, surface: pygame.Surface, canvas: pygame.Rect, bar: BarSprite) -> None:
        height = max(self.s(8), int(bar.current_height))
        width = max(self.s(4), int(bar.current_width))
        baseline = canvas.bottom - self.s(14)
        rect = pygame.Rect(int(bar.current_x), baseline - height, width, height)
        radius = min(self.s(12), max(self.s(6), width // 3))
        color, edge, glow_strength = self._bar_style(bar)

        if glow_strength > 0.06:
            draw_glow(surface, rect, color, radius, glow_strength, layers=3)

        shadow = pygame.Rect(rect.x, rect.y + self.s(7), rect.width, rect.height)
        pygame.draw.rect(surface, with_alpha(darken(color, 0.88), 104), shadow, border_radius=radius)
        pygame.draw.rect(surface, color, rect, border_radius=radius)
        pygame.draw.rect(surface, with_alpha(edge, 210), rect, width=1, border_radius=radius)

        highlight_height = max(self.s(10), int(rect.height * 0.44))
        highlight = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(highlight, with_alpha(lighten(color, 0.26), 132), pygame.Rect(0, 0, rect.width, highlight_height), border_radius=radius)
        pygame.draw.rect(highlight, with_alpha(lighten(color, 0.42), 92), pygame.Rect(self.s(1), self.s(1), max(self.s(2), rect.width - self.s(2)), max(self.s(2), rect.height // 10)), border_radius=radius)
        surface.blit(highlight, rect.topleft)

        cap_height = self.s(3)
        if bar.transient_state == "compare":
            pygame.draw.rect(surface, with_alpha(lighten(config.BAR_COMPARE, 0.22), 240), pygame.Rect(rect.x, rect.y, rect.width, cap_height), border_radius=self.s(3))
        elif bar.transient_state == "update":
            pygame.draw.rect(surface, with_alpha(lighten(config.BAR_UPDATE, 0.18), 240), pygame.Rect(rect.x, rect.y, rect.width, cap_height), border_radius=self.s(3))
        elif bar.sorted_locked:
            pygame.draw.rect(surface, with_alpha(lighten(config.BAR_SORTED, 0.12), 228), pygame.Rect(rect.x, rect.y, rect.width, cap_height), border_radius=self.s(3))

    def _draw_priority(self, bar: BarSprite) -> tuple[int, float]:
        return (1 if (bar.transient_state or bar.sorted_locked) else 0, bar.current_height)

    def _bar_style(self, bar: BarSprite) -> tuple[tuple[int, int, int], tuple[int, int, int], float]:
        if bar.sorted_locked:
            color = mix_color(config.BAR_SORTED, lighten(config.BAR_SORTED, 0.08), min(1.0, 0.18 + bar.pulse * 0.45))
            edge = lighten(config.BAR_SORTED, 0.34)
            return color, edge, 0.16 + bar.pulse * 0.48
        if bar.transient_state == "compare":
            color = mix_color(config.BAR_COMPARE, lighten(config.BAR_COMPARE, 0.14), min(1.0, 0.22 + bar.pulse * 0.36))
            edge = lighten(config.BAR_COMPARE, 0.42)
            return color, edge, 0.18 + bar.pulse * 0.52
        if bar.transient_state == "update":
            color = mix_color(config.BAR_UPDATE, lighten(config.BAR_UPDATE, 0.18), min(1.0, 0.18 + bar.pulse * 0.34))
            edge = lighten(config.BAR_UPDATE, 0.38)
            return color, edge, 0.16 + bar.pulse * 0.5
        color = mix_color(config.BAR_DEFAULT, lighten(config.BAR_DEFAULT, 0.1), min(0.34, bar.pulse * 0.24))
        edge = lighten(config.BAR_DEFAULT, 0.18)
        return color, edge, 0.03 + bar.pulse * 0.16

    def _recalculate_targets(self) -> None:
        count = len(self.bars)
        for index, bar in enumerate(self.bars):
            target_x, target_width = self._target_slot(index, count)
            bar.target_x = target_x
            bar.target_width = target_width
            bar.target_height = self._height_for_value(bar.value)

    def _target_slot(self, index: int, count: int) -> tuple[float, float]:
        if count <= 0 or self.canvas.width <= 0:
            return 0.0, 0.0

        padding = self.s(12)
        usable_width = max(60.0, self.canvas.width - padding * 2)
        gap = max(2.0, min(8.0, 240.0 / max(count, 1)))
        width = (usable_width - gap * (count - 1)) / max(count, 1)

        if width < 3:
            gap = 1.0
            width = max(2.0, (usable_width - gap * (count - 1)) / max(count, 1))

        x = self.canvas.x + padding + index * (width + gap)
        return x, width

    def _height_for_value(self, value: int) -> float:
        usable_height = max(40.0, self.canvas.height - float(self.s(24)))
        minimum = float(self.s(10))
        normalized = value / max(self.value_ceiling, 1)
        return minimum + (usable_height - minimum) * normalized
