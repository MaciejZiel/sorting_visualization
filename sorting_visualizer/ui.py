from __future__ import annotations

from dataclasses import dataclass

import pygame

from sorting_visualizer import config
from sorting_visualizer.drawing import clamp, draw_glow, draw_panel, lighten, mix_color, with_alpha


@dataclass(slots=True)
class AppLayout:
    sidebar: pygame.Rect
    canvas_card: pygame.Rect
    canvas_header: pygame.Rect
    bar_area: pygame.Rect
    title_card: pygame.Rect
    algorithm_card: pygame.Rect
    controls_card: pygame.Rect
    info_card: pygame.Rect


@dataclass(slots=True)
class UISnapshot:
    algorithm_key: str
    algorithm_label: str
    algorithm_description: str
    status_label: str
    status_detail: str
    comparisons: int
    swaps: int
    writes: int
    elapsed: float
    sorted_count: int
    array_size: int
    speed_label: str
    speed_value: int
    ui_scale_label: str
    is_running: bool
    can_start: bool
    can_pause: bool
    can_step: bool
    can_scale_down: bool
    can_scale_up: bool
    can_size_down: bool
    can_size_up: bool
    can_speed_down: bool
    can_speed_up: bool


@dataclass(slots=True)
class ButtonSpec:
    control_id: str
    group: str
    action: str
    label: str
    rect: pygame.Rect
    style: str = "neutral"
    hotkey: str = ""
    toggled: bool = False
    disabled: bool = False
    show_hotkey: bool = True


@dataclass(slots=True)
class AdjusterSpec:
    label: str
    value: str
    row_rect: pygame.Rect
    down_button: ButtonSpec
    up_button: ButtonSpec


@dataclass(slots=True)
class ControlLayout:
    inner: pygame.Rect
    start_rect: pygame.Rect
    pause_rect: pygame.Rect
    step_rect: pygame.Rect
    shuffle_rect: pygame.Rect
    reset_rect: pygame.Rect
    divider_y: int
    adjust_rows: list[pygame.Rect]


class UIManager:
    def __init__(self, scale: float = 1.0) -> None:
        self.scale = scale
        self.controls: list[ButtonSpec] = []
        self.adjusters: list[AdjusterSpec] = []
        self.control_layout: ControlLayout | None = None
        self.hover_progress: dict[str, float] = {}
        self.set_scale(scale)

    def set_scale(self, scale: float) -> None:
        self.scale = scale
        self.hero_font = pygame.font.SysFont(config.FONT_NAME, self.s(30), bold=True)
        self.title_font = pygame.font.SysFont(config.FONT_NAME, self.s(24), bold=True)
        self.section_font = pygame.font.SysFont(config.FONT_NAME, self.s(15), bold=True)
        self.body_font = pygame.font.SysFont(config.FONT_NAME, self.s(16))
        self.small_font = pygame.font.SysFont(config.FONT_NAME, self.s(14))
        self.micro_font = pygame.font.SysFont(config.FONT_NAME, self.s(12), bold=True)
        self.value_font = pygame.font.SysFont(config.MONO_FONT_NAME, self.s(24), bold=True)

    def s(self, value: int | float) -> int:
        return max(1, int(round(value * self.scale)))

    def compute_layout(self, screen_size: tuple[int, int]) -> AppLayout:
        width, height = screen_size
        margin = self.s(config.OUTER_MARGIN)
        gap = self.s(config.PANEL_GAP)

        sidebar_width = int(clamp(width * 0.245, self.s(config.SIDEBAR_MIN_WIDTH), self.s(config.SIDEBAR_MAX_WIDTH)))
        min_canvas_width = self.s(560)
        max_sidebar = width - margin * 2 - gap - min_canvas_width
        sidebar_width = int(clamp(sidebar_width, self.s(300), max_sidebar if max_sidebar > self.s(300) else sidebar_width))

        sidebar = pygame.Rect(margin, margin, sidebar_width, height - margin * 2)
        canvas_card = pygame.Rect(sidebar.right + gap, margin, width - sidebar.right - gap - margin, height - margin * 2)

        title_height = self.s(82)
        algorithm_height = self.s(184)
        controls_height = self.s(294)
        minimum_info_height = self.s(154)
        available_height = sidebar.height - gap * 3

        required_height = title_height + algorithm_height + controls_height + minimum_info_height
        if required_height > available_height:
            overflow = required_height - available_height
            segments = [
                ("controls", self.s(258)),
                ("algorithm", self.s(160)),
                ("title", self.s(70)),
            ]
            for segment, minimum in segments:
                if overflow <= 0:
                    break
                current = {
                    "controls": controls_height,
                    "algorithm": algorithm_height,
                    "title": title_height,
                }[segment]
                reduction = min(current - minimum, overflow)
                if reduction <= 0:
                    continue
                if segment == "controls":
                    controls_height -= reduction
                elif segment == "algorithm":
                    algorithm_height -= reduction
                else:
                    title_height -= reduction
                overflow -= reduction

        title_card = pygame.Rect(sidebar.x, sidebar.y, sidebar.width, title_height)
        algorithm_card = pygame.Rect(sidebar.x, title_card.bottom + gap, sidebar.width, algorithm_height)
        controls_card = pygame.Rect(sidebar.x, algorithm_card.bottom + gap, sidebar.width, controls_height)
        info_card = pygame.Rect(sidebar.x, controls_card.bottom + gap, sidebar.width, max(0, sidebar.bottom - (controls_card.bottom + gap)))

        canvas_header = pygame.Rect(
            canvas_card.x + self.s(22),
            canvas_card.y + self.s(16),
            canvas_card.width - self.s(44),
            self.s(70),
        )
        bar_top = canvas_header.bottom + self.s(2)
        bar_area = pygame.Rect(
            canvas_card.x + self.s(18),
            bar_top,
            canvas_card.width - self.s(36),
            max(self.s(120), canvas_card.bottom - self.s(18) - bar_top),
        )

        return AppLayout(
            sidebar=sidebar,
            canvas_card=canvas_card,
            canvas_header=canvas_header,
            bar_area=bar_area,
            title_card=title_card,
            algorithm_card=algorithm_card,
            controls_card=controls_card,
            info_card=info_card,
        )

    def prepare(self, layout: AppLayout, snapshot: UISnapshot, algorithms: list) -> None:
        self.control_layout = self._compute_control_layout(layout.controls_card)
        self.adjusters = self._build_adjusters(snapshot)

        controls: list[ButtonSpec] = []
        controls.extend(self._algorithm_buttons(layout.algorithm_card, snapshot.algorithm_key, algorithms))
        controls.extend(self._action_buttons(snapshot))
        for adjuster in self.adjusters:
            controls.append(adjuster.down_button)
            controls.append(adjuster.up_button)

        self.controls = controls
        for control in controls:
            self.hover_progress.setdefault(control.control_id, 0.0)

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        for control in self.controls:
            hovered = control.rect.collidepoint(mouse_pos) and not control.disabled
            target = 1.0 if hovered else 0.0
            current = self.hover_progress.get(control.control_id, 0.0)
            self.hover_progress[control.control_id] = current + (target - current) * min(1.0, dt * 14.0)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        for control in reversed(self.controls):
            if not control.disabled and control.rect.collidepoint(event.pos):
                return control.action
        return None

    def draw(self, surface: pygame.Surface, layout: AppLayout, snapshot: UISnapshot, algorithms: list) -> None:
        self._draw_title_card(surface, layout.title_card)
        self._draw_algorithm_card(surface, layout.algorithm_card, snapshot)
        self._draw_controls_card(surface, layout.controls_card, snapshot)
        self._draw_info_card(surface, layout.info_card, snapshot)

        for control in self.controls:
            self._draw_button(surface, control)

    def _compute_control_layout(self, card: pygame.Rect) -> ControlLayout:
        inset = self.s(16)
        inner = card.inflate(-inset, -inset)
        gap = self.s(8)
        top = card.y + self.s(56)
        button_height = self.s(40)

        start_width = int((inner.width - gap) * 0.58)
        pause_width = inner.width - start_width - gap
        half_width = (inner.width - gap) // 2

        start_rect = pygame.Rect(inner.x, top, start_width, button_height)
        pause_rect = pygame.Rect(start_rect.right + gap, top, pause_width, button_height)
        step_rect = pygame.Rect(inner.x, start_rect.bottom + gap, half_width, button_height)
        shuffle_rect = pygame.Rect(step_rect.right + gap, step_rect.y, inner.width - half_width - gap, button_height)
        reset_rect = pygame.Rect(inner.x, step_rect.bottom + gap, inner.width, button_height)

        divider_y = reset_rect.bottom + self.s(18)
        adjust_top = divider_y + self.s(10)
        adjust_height = self.s(26)
        adjust_gap = self.s(14)
        available_space = inner.bottom - adjust_top
        minimum_needed = adjust_height * 3 + adjust_gap * 2
        if minimum_needed > available_space:
            adjust_gap = max(self.s(8), (available_space - adjust_height * 3) // 2)
            minimum_needed = adjust_height * 3 + adjust_gap * 2
        if minimum_needed > available_space:
            adjust_height = max(self.s(22), (available_space - adjust_gap * 2) // 3)

        adjust_rows = [
            pygame.Rect(inner.x, adjust_top + index * (adjust_height + adjust_gap), inner.width, adjust_height)
            for index in range(3)
        ]

        return ControlLayout(
            inner=inner,
            start_rect=start_rect,
            pause_rect=pause_rect,
            step_rect=step_rect,
            shuffle_rect=shuffle_rect,
            reset_rect=reset_rect,
            divider_y=divider_y,
            adjust_rows=adjust_rows,
        )

    def _algorithm_buttons(self, card: pygame.Rect, selected_key: str, algorithms: list) -> list[ButtonSpec]:
        inset = self.s(16)
        inner = card.inflate(-inset, -inset)
        gap = self.s(8)
        top = card.y + self.s(58)
        height = self.s(36)
        width = (inner.width - gap) // 2

        positions = [
            pygame.Rect(inner.x, top, width, height),
            pygame.Rect(inner.x + width + gap, top, width, height),
            pygame.Rect(inner.x, top + height + gap, width, height),
            pygame.Rect(inner.x + width + gap, top + height + gap, width, height),
            pygame.Rect(inner.x, top + (height + gap) * 2, inner.width, height),
        ]

        specs: list[ButtonSpec] = []
        for index, algorithm in enumerate(algorithms):
            specs.append(
                ButtonSpec(
                    control_id=f"algorithm:{algorithm.key}",
                    group="algorithm",
                    action=f"algorithm:{algorithm.key}",
                    label=algorithm.label,
                    rect=positions[index],
                    style="algorithm",
                    toggled=algorithm.key == selected_key,
                    show_hotkey=False,
                )
            )
        return specs

    def _action_buttons(self, snapshot: UISnapshot) -> list[ButtonSpec]:
        if self.control_layout is None:
            return []

        return [
            ButtonSpec("start", "control", "start", "Start", self.control_layout.start_rect, style="primary", hotkey="Enter", disabled=not snapshot.can_start),
            ButtonSpec(
                "pause",
                "control",
                "pause_toggle",
                "Pause" if snapshot.is_running else "Resume",
                self.control_layout.pause_rect,
                style="secondary",
                hotkey="Space",
                disabled=not snapshot.can_pause,
            ),
            ButtonSpec("step", "control", "step", "Step", self.control_layout.step_rect, style="secondary", hotkey="N", disabled=not snapshot.can_step),
            ButtonSpec("shuffle", "control", "shuffle", "Shuffle", self.control_layout.shuffle_rect, style="neutral", hotkey="H"),
            ButtonSpec("reset", "control", "reset", "Reset Array", self.control_layout.reset_rect, style="ghost", hotkey="R"),
        ]

    def _build_adjusters(self, snapshot: UISnapshot) -> list[AdjusterSpec]:
        if self.control_layout is None:
            return []

        button_size = self.s(26)
        button_gap = self.s(6)

        rows = [
            ("Array size", f"{snapshot.array_size} bars", "size_down", "size_up", snapshot.can_size_down, snapshot.can_size_up, "[", "]"),
            (
                "Playback speed",
                f"{snapshot.speed_label} · {snapshot.speed_value}/s",
                "speed_down",
                "speed_up",
                snapshot.can_speed_down,
                snapshot.can_speed_up,
                "-",
                "=",
            ),
            ("Interface scale", snapshot.ui_scale_label, "ui_down", "ui_up", snapshot.can_scale_down, snapshot.can_scale_up, ",", "."),
        ]

        adjusters: list[AdjusterSpec] = []
        for index, (label, value, down_action, up_action, can_down, can_up, down_key, up_key) in enumerate(rows):
            row_rect = self.control_layout.adjust_rows[index]
            up_rect = pygame.Rect(row_rect.right - button_size, row_rect.y, button_size, row_rect.height)
            down_rect = pygame.Rect(up_rect.x - button_gap - button_size, row_rect.y, button_size, row_rect.height)
            adjusters.append(
                AdjusterSpec(
                    label=label,
                    value=value,
                    row_rect=row_rect,
                    down_button=ButtonSpec(
                        control_id=down_action,
                        group="adjuster",
                        action=down_action,
                        label="−",
                        rect=down_rect,
                        style="adjust",
                        hotkey=down_key,
                        disabled=not can_down,
                        show_hotkey=False,
                    ),
                    up_button=ButtonSpec(
                        control_id=up_action,
                        group="adjuster",
                        action=up_action,
                        label="+",
                        rect=up_rect,
                        style="adjust",
                        hotkey=up_key,
                        disabled=not can_up,
                        show_hotkey=False,
                    ),
                )
            )

        return adjusters

    def _draw_title_card(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        left = rect.x + self.s(18)
        draw_panel(
            surface,
            rect,
            config.PANEL_FILL,
            config.CANVAS_BORDER,
            self.s(config.PANEL_RADIUS),
            glow_color=config.ACCENT,
            glow_strength=0.12,
            shadow_alpha=58,
            border_alpha=140,
            gloss_alpha=16,
        )
        surface.blit(self.micro_font.render("INTERACTIVE SORTING VISUALIZER", True, config.TEXT_SECONDARY), (left, rect.y + self.s(14)))
        surface.blit(self.hero_font.render("Neon Sorting Studio", True, config.TEXT_PRIMARY), (left, rect.y + self.s(28)))
        surface.blit(
            self.small_font.render("Smooth sorting visuals with responsive controls.", True, config.TEXT_SECONDARY),
            (left, rect.y + self.s(58)),
        )

    def _draw_algorithm_card(self, surface: pygame.Surface, rect: pygame.Rect, snapshot: UISnapshot) -> None:
        left = rect.x + self.s(18)
        draw_panel(
            surface,
            rect,
            mix_color(config.PANEL_FILL, config.PANEL_INNER, 0.22),
            config.PANEL_BORDER,
            self.s(config.PANEL_RADIUS),
            shadow_alpha=38,
            border_alpha=88,
            gloss_alpha=8,
        )
        surface.blit(self.section_font.render("Algorithms", True, config.TEXT_PRIMARY), (left, rect.y + self.s(16)))
        surface.blit(self.small_font.render("Choose the active algorithm.", True, config.TEXT_SECONDARY), (left, rect.y + self.s(38)))

        if rect.height >= self.s(208):
            description_y = rect.bottom - self.s(34)
            pygame.draw.line(surface, with_alpha(config.GRID_LINE, 140), (left, description_y - self.s(10)), (rect.right - self.s(18), description_y - self.s(10)), 1)
            surface.blit(self.small_font.render(snapshot.algorithm_description, True, config.TEXT_MUTED), (left, description_y))

    def _draw_controls_card(self, surface: pygame.Surface, rect: pygame.Rect, snapshot: UISnapshot) -> None:
        left = rect.x + self.s(18)
        draw_panel(
            surface,
            rect,
            mix_color(config.PANEL_FILL, config.PANEL_INNER, 0.2),
            config.PANEL_BORDER,
            self.s(config.PANEL_RADIUS),
            shadow_alpha=36,
            border_alpha=84,
            gloss_alpha=8,
        )
        surface.blit(self.section_font.render("Controls", True, config.TEXT_PRIMARY), (left, rect.y + self.s(16)))
        surface.blit(self.small_font.render("Playback first, then tuning controls below.", True, config.TEXT_SECONDARY), (left, rect.y + self.s(38)))

        if self.control_layout is None:
            return

        pygame.draw.line(
            surface,
            with_alpha(config.GRID_LINE, 140),
            (left, self.control_layout.divider_y),
            (rect.right - self.s(18), self.control_layout.divider_y),
            1,
        )

        caption_y = self.control_layout.divider_y + self.s(2)
        surface.blit(self.micro_font.render("TUNE THE VISUALIZER", True, config.TEXT_SECONDARY), (left, caption_y))

        for index, adjuster in enumerate(self.adjusters):
            self._draw_adjuster_row(surface, adjuster, is_last=index == len(self.adjusters) - 1)

    def _draw_adjuster_row(self, surface: pygame.Surface, adjuster: AdjusterSpec, *, is_last: bool) -> None:
        row = adjuster.row_rect
        label_surface = self.small_font.render(adjuster.label, True, config.TEXT_SECONDARY)
        value_surface = self.body_font.render(adjuster.value, True, config.TEXT_PRIMARY)

        surface.blit(label_surface, label_surface.get_rect(midleft=(row.x, row.centery)))
        surface.blit(value_surface, value_surface.get_rect(midright=(adjuster.down_button.rect.x - self.s(12), row.centery)))

        if not is_last:
            pygame.draw.line(
                surface,
                with_alpha(config.GRID_LINE, 116),
                (row.x, row.bottom + self.s(7)),
                (row.right, row.bottom + self.s(7)),
                1,
            )

    def _draw_info_card(self, surface: pygame.Surface, rect: pygame.Rect, snapshot: UISnapshot) -> None:
        left = rect.x + self.s(18)
        draw_panel(
            surface,
            rect,
            mix_color(config.PANEL_FILL, config.PANEL_INNER, 0.18),
            config.PANEL_BORDER,
            self.s(config.PANEL_RADIUS),
            shadow_alpha=34,
            border_alpha=78,
            gloss_alpha=8,
        )
        surface.blit(self.section_font.render("Performance", True, config.TEXT_PRIMARY), (left, rect.y + self.s(16)))

        if rect.height < self.s(146):
            compact = [
                f"Comparisons {snapshot.comparisons:,}   Swaps {snapshot.swaps:,}",
                f"Runtime {snapshot.elapsed:05.2f}s   Writes {snapshot.writes:,}",
                f"Progress {snapshot.sorted_count}/{snapshot.array_size}   Speed {snapshot.speed_label}",
            ]
            for index, text in enumerate(compact):
                surface.blit(self.small_font.render(text, True, config.TEXT_SECONDARY if index == 0 else config.TEXT_MUTED), (left, rect.y + self.s(44) + index * self.s(18)))
            return

        inner = rect.inflate(-self.s(16), -self.s(16))
        top = rect.y + self.s(46)
        gap = self.s(8)
        stat_width = (inner.width - gap * 2) // 3
        stat_height = self.s(70)

        major_stats = [
            ("Comparisons", f"{snapshot.comparisons:,}", config.ACCENT),
            ("Swaps", f"{snapshot.swaps:,}", config.BAR_UPDATE),
            ("Runtime", f"{snapshot.elapsed:05.2f}s", config.SUCCESS),
        ]

        for index, (label, value, accent) in enumerate(major_stats):
            rect_stat = pygame.Rect(inner.x + index * (stat_width + gap), top, stat_width, stat_height)
            self._draw_major_stat(surface, rect_stat, label, value, accent)

        details_top = top + stat_height + self.s(16)
        detail_rows = [
            ("Writes", f"{snapshot.writes:,}"),
            ("Progress", f"{snapshot.sorted_count}/{snapshot.array_size}"),
            ("Array size", f"{snapshot.array_size} bars"),
            ("Speed", f"{snapshot.speed_label} · {snapshot.speed_value}/s"),
        ]

        for index, (label, value) in enumerate(detail_rows):
            column = index % 2
            row = index // 2
            row_rect = pygame.Rect(
                inner.x + column * ((inner.width + gap) // 2),
                details_top + row * self.s(24),
                (inner.width - gap) // 2,
                self.s(20),
            )
            self._draw_detail_row(surface, row_rect, label, value)

        divider_y = details_top + self.s(58)
        pygame.draw.line(surface, with_alpha(config.GRID_LINE, 138), (inner.x, divider_y), (inner.right, divider_y), 1)
        surface.blit(self.micro_font.render("COLOR MEANING", True, config.TEXT_SECONDARY), (inner.x, divider_y + self.s(12)))

        legend_items = [
            ("Default", config.BAR_DEFAULT),
            ("Comparing", config.BAR_COMPARE),
            ("Swap / write", config.BAR_UPDATE),
            ("Sorted", config.BAR_SORTED),
        ]
        legend_top = divider_y + self.s(32)
        legend_gap_x = self.s(12)
        legend_width = (inner.width - legend_gap_x) // 2

        for index, (label, color) in enumerate(legend_items):
            column = index % 2
            row = index // 2
            item_rect = pygame.Rect(
                inner.x + column * (legend_width + legend_gap_x),
                legend_top + row * self.s(28),
                legend_width,
                self.s(20),
            )
            self._draw_legend_item(surface, item_rect, label, color)

    def _draw_major_stat(self, surface: pygame.Surface, rect: pygame.Rect, label: str, value: str, accent: tuple[int, int, int]) -> None:
        draw_panel(
            surface,
            rect,
            mix_color(config.PANEL_INNER, accent, 0.09),
            mix_color(config.PANEL_BORDER, accent, 0.18),
            self.s(18),
            shadow_alpha=18,
            border_alpha=86,
            gloss_alpha=10,
        )
        accent_rect = pygame.Rect(rect.x + self.s(10), rect.y + self.s(10), self.s(28), self.s(4))
        pygame.draw.rect(surface, accent, accent_rect, border_radius=self.s(4))
        surface.blit(self.micro_font.render(label.upper(), True, config.TEXT_SECONDARY), (rect.x + self.s(10), rect.y + self.s(22)))
        surface.blit(self.value_font.render(value, True, config.TEXT_PRIMARY), (rect.x + self.s(10), rect.y + self.s(36)))

    def _draw_detail_row(self, surface: pygame.Surface, rect: pygame.Rect, label: str, value: str) -> None:
        surface.blit(self.small_font.render(label, True, config.TEXT_MUTED), (rect.x, rect.y))
        value_surface = self.small_font.render(value, True, config.TEXT_PRIMARY)
        surface.blit(value_surface, value_surface.get_rect(topright=(rect.right, rect.y)))

    def _draw_legend_item(self, surface: pygame.Surface, rect: pygame.Rect, label: str, color: tuple[int, int, int]) -> None:
        swatch = pygame.Rect(rect.x, rect.y + self.s(7), self.s(26), self.s(6))
        draw_glow(surface, swatch, color, self.s(6), 0.22, layers=2)
        pygame.draw.rect(surface, color, swatch, border_radius=self.s(4))
        surface.blit(self.small_font.render(label, True, config.TEXT_SECONDARY), (swatch.right + self.s(10), rect.y))

    def _draw_button(self, surface: pygame.Surface, control: ButtonSpec) -> None:
        hover = self.hover_progress.get(control.control_id, 0.0)
        radius = self.s(14 if control.style == "adjust" else config.BUTTON_RADIUS)
        rect = control.rect

        if control.disabled:
            fill = mix_color(config.PANEL_INNER, config.PANEL_FILL, 0.2)
            border = mix_color(config.PANEL_BORDER, config.PANEL_FILL, 0.55)
            text = mix_color(config.TEXT_MUTED, config.PANEL_FILL, 0.15)
            glow_strength = 0.0
            shadow_alpha = 0
        else:
            fill, border, text, glow_strength, shadow_alpha = self._button_style(control, hover)

        if shadow_alpha > 0:
            shadow = pygame.Surface((rect.width + self.s(18), rect.height + self.s(18)), pygame.SRCALPHA)
            pygame.draw.rect(
                shadow,
                (0, 0, 0, shadow_alpha),
                pygame.Rect(self.s(9), self.s(11), rect.width, rect.height),
                border_radius=radius + self.s(4),
            )
            surface.blit(shadow, (rect.x - self.s(9), rect.y - self.s(9)))

        if glow_strength > 0:
            glow_color = config.ACCENT if control.style != "algorithm" else (config.BAR_COMPARE if control.toggled else config.ACCENT)
            draw_glow(surface, rect, glow_color, radius, glow_strength, layers=3)

        pygame.draw.rect(surface, fill, rect, border_radius=radius)
        pygame.draw.rect(surface, with_alpha(border, 210), rect, width=1, border_radius=radius)

        highlight = pygame.Rect(rect.x + 1, rect.y + 1, rect.width - 2, max(self.s(10), int(rect.height * 0.38)))
        pygame.draw.rect(surface, with_alpha(lighten(fill, 0.12), 34), highlight, border_radius=radius)

        if control.style == "algorithm" and control.toggled:
            accent_bar = pygame.Rect(rect.x + self.s(8), rect.y + self.s(7), self.s(4), rect.height - self.s(14))
            pygame.draw.rect(surface, config.ACCENT, accent_bar, border_radius=self.s(3))
            label_pos = (rect.x + self.s(18), rect.centery)
            label_rect = self.body_font.render(control.label, True, text).get_rect(midleft=label_pos)
            surface.blit(self.body_font.render(control.label, True, text), label_rect)
            return

        if control.style == "adjust":
            glyph_font = self.title_font
            glyph = glyph_font.render(control.label, True, text)
            surface.blit(glyph, glyph.get_rect(center=(rect.centerx, rect.centery - self.s(1))))
            return

        label_surface = self.body_font.render(control.label, True, text)
        if control.show_hotkey and control.hotkey:
            surface.blit(label_surface, label_surface.get_rect(midleft=(rect.x + self.s(14), rect.centery)))
            hotkey_surface = self.micro_font.render(control.hotkey, True, mix_color(config.TEXT_MUTED, text, 0.35))
            surface.blit(hotkey_surface, hotkey_surface.get_rect(midright=(rect.right - self.s(12), rect.centery)))
        else:
            surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _button_style(self, control: ButtonSpec, hover: float) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], float, int]:
        if control.style == "primary":
            fill = mix_color(config.ACCENT_SOFT, config.ACCENT, 0.28 + hover * 0.16)
            border = lighten(config.ACCENT, 0.18)
            text = config.TEXT_PRIMARY
            return fill, border, text, 0.16 + hover * 0.22, 44

        if control.style == "secondary":
            fill = mix_color(config.PANEL_INNER, config.ACCENT_SOFT, 0.24 + hover * 0.1)
            border = mix_color(config.PANEL_BORDER, config.ACCENT, 0.2 + hover * 0.14)
            text = config.TEXT_PRIMARY
            return fill, border, text, hover * 0.14, 30

        if control.style == "ghost":
            fill = mix_color(config.PANEL_FILL, config.PANEL_INNER, 0.28 + hover * 0.08)
            border = mix_color(config.PANEL_BORDER, config.TEXT_SECONDARY, 0.1 + hover * 0.08)
            text = config.TEXT_SECONDARY
            return fill, border, text, hover * 0.08, 18

        if control.style == "adjust":
            fill = mix_color(config.PANEL_INNER, lighten(config.PANEL_INNER, 0.08), hover * 0.24)
            border = mix_color(config.PANEL_BORDER, config.TEXT_SECONDARY, 0.16 + hover * 0.08)
            text = config.TEXT_PRIMARY
            return fill, border, text, hover * 0.08, 16

        if control.style == "algorithm":
            if control.toggled:
                fill = mix_color(config.ACCENT_SOFT, config.PANEL_INNER, 0.22)
                border = mix_color(config.ACCENT, lighten(config.ACCENT, 0.2), 0.25 + hover * 0.1)
                text = config.TEXT_PRIMARY
                return fill, border, text, 0.14 + hover * 0.18, 30
            fill = mix_color(config.PANEL_INNER, lighten(config.PANEL_INNER, 0.08), hover * 0.14)
            border = mix_color(config.PANEL_BORDER, config.TEXT_SECONDARY, 0.06 + hover * 0.06)
            text = config.TEXT_SECONDARY
            return fill, border, text, hover * 0.07, 14

        fill = mix_color(config.PANEL_INNER, lighten(config.PANEL_INNER, 0.08), hover * 0.14)
        border = mix_color(config.PANEL_BORDER, config.TEXT_SECONDARY, 0.08 + hover * 0.08)
        text = config.TEXT_PRIMARY
        return fill, border, text, hover * 0.08, 18
