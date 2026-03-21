from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from sorting_visualizer import config
from sorting_visualizer.drawing import clamp
from sorting_visualizer.renderer import BarVisualizer, draw_scene_background
from sorting_visualizer.sorting import ALGORITHMS, SortEvent, SortGenerator
from sorting_visualizer.ui import UIManager, UISnapshot


@dataclass(slots=True)
class SortMetrics:
    comparisons: int = 0
    swaps: int = 0
    writes: int = 0
    elapsed: float = 0.0


class SortingVisualizerApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)
        display_size = self._get_display_size()
        self.ui_scale_index = self._detect_ui_scale_index(display_size)
        window_size = self._initial_window_size(display_size)
        self.screen = pygame.display.set_mode(self._clamp_window_size(window_size), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.ui = UIManager(self.current_ui_scale)
        self.visualizer = BarVisualizer(self.current_ui_scale)
        self.metrics = SortMetrics()

        self.algorithm_index = 0
        self.array_size = config.DEFAULT_ARRAY_SIZE
        self.speed_index = config.DEFAULT_SPEED_INDEX
        self.original_values: list[int] = []
        self.generator: SortGenerator | None = None
        self.auto_running = False
        self.completed = False
        self.step_accumulator = 0.0
        self.scene_time = 0.0

        self.shuffle_values(animate=True)

    @property
    def current_algorithm(self):
        return ALGORITHMS[self.algorithm_index]

    @property
    def current_speed(self) -> int:
        return config.SPEED_PRESETS[self.speed_index][0]

    @property
    def current_speed_label(self) -> str:
        return config.SPEED_PRESETS[self.speed_index][1]

    @property
    def current_ui_scale(self) -> float:
        return config.UI_SCALE_PRESETS[self.ui_scale_index]

    @property
    def current_ui_scale_label(self) -> str:
        return f"{int(round(self.current_ui_scale * 100))}%"

    def run(self) -> None:
        running = True

        while running:
            dt = self.clock.tick(config.FPS) / 1000.0
            self.scene_time += dt
            layout = self.ui.compute_layout(self.screen.get_size())
            self.visualizer.set_canvas(layout.bar_area)

            pre_snapshot = self._build_snapshot()
            self.ui.prepare(layout, pre_snapshot, ALGORITHMS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_key(event)
                elif event.type in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED):
                    self._resize_window((event.x, event.y))
                else:
                    action = self.ui.handle_event(event)
                    if action:
                        self._handle_action(action)

            layout = self.ui.compute_layout(self.screen.get_size())
            self.visualizer.set_canvas(layout.bar_area)
            self._advance_sort(dt)
            self.visualizer.update(dt)

            snapshot = self._build_snapshot()
            self.ui.prepare(layout, snapshot, ALGORITHMS)
            self.ui.update(dt, pygame.mouse.get_pos())

            self._draw(layout, snapshot)

        pygame.quit()

    def _draw(self, layout, snapshot: UISnapshot) -> None:
        draw_scene_background(self.screen, self.scene_time)
        self.visualizer.draw(
            self.screen,
            layout.canvas_card,
            layout.canvas_header,
            snapshot.algorithm_label,
            snapshot.status_label,
            snapshot.status_detail,
        )
        self.ui.draw(self.screen, layout, snapshot, ALGORITHMS)
        pygame.display.flip()

    def _handle_key(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key == pygame.K_RETURN:
            self.start_sorting()
        elif event.key == pygame.K_SPACE:
            if self.auto_running:
                self.auto_running = False
            elif self.generator is not None and not self.completed:
                self.auto_running = True
            else:
                self.start_sorting()
        elif event.key == pygame.K_n:
            self.step_once()
        elif event.key == pygame.K_r:
            self.reset_array()
        elif event.key == pygame.K_h:
            self.shuffle_values()
        elif event.key == pygame.K_LEFT:
            self.cycle_algorithm(-1)
        elif event.key == pygame.K_RIGHT:
            self.cycle_algorithm(1)
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.change_speed(-1)
        elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.change_speed(1)
        elif event.key == pygame.K_COMMA:
            self.change_ui_scale(-1)
        elif event.key == pygame.K_PERIOD:
            self.change_ui_scale(1)
        elif event.key == pygame.K_LEFTBRACKET:
            self.change_size(-1)
        elif event.key == pygame.K_RIGHTBRACKET:
            self.change_size(1)
        elif pygame.K_1 <= event.key <= pygame.K_5:
            self.select_algorithm(event.key - pygame.K_1)
        return True

    def _handle_action(self, action: str) -> None:
        if action.startswith("algorithm:"):
            key = action.split(":", 1)[1]
            for index, algorithm in enumerate(ALGORITHMS):
                if algorithm.key == key:
                    self.select_algorithm(index)
                    return

        handlers = {
            "start": self.start_sorting,
            "pause_toggle": self.toggle_pause,
            "step": self.step_once,
            "shuffle": self.shuffle_values,
            "reset": self.reset_array,
            "size_down": lambda: self.change_size(-1),
            "size_up": lambda: self.change_size(1),
            "speed_down": lambda: self.change_speed(-1),
            "speed_up": lambda: self.change_speed(1),
            "ui_down": lambda: self.change_ui_scale(-1),
            "ui_up": lambda: self.change_ui_scale(1),
        }
        handler = handlers.get(action)
        if handler:
            handler()

    def _build_snapshot(self) -> UISnapshot:
        if self.completed:
            status_label = "Finished"
            status_detail = "Sequence complete with the final sorted wave locked in."
        elif self.generator is not None and self.auto_running:
            status_label = "Sorting"
            status_detail = "Live playback is running with real-time compares, swaps, and writes."
        elif self.generator is not None:
            status_label = "Paused"
            status_detail = "Playback is paused. Resume the run or advance one generator event at a time."
        else:
            status_label = "Ready"
            status_detail = "Shuffle the data, pick an algorithm, and start the visualization."

        return UISnapshot(
            algorithm_key=self.current_algorithm.key,
            algorithm_label=self.current_algorithm.label,
            algorithm_description=self.current_algorithm.description,
            status_label=status_label,
            status_detail=status_detail,
            comparisons=self.metrics.comparisons,
            swaps=self.metrics.swaps,
            writes=self.metrics.writes,
            elapsed=self.metrics.elapsed,
            sorted_count=self.visualizer.sorted_count,
            array_size=self.array_size,
            speed_label=self.current_speed_label,
            speed_value=self.current_speed,
            ui_scale_label=self.current_ui_scale_label,
            is_running=self.auto_running,
            can_start=self.generator is None,
            can_pause=self.generator is not None and not self.completed,
            can_step=not self.completed,
            can_scale_down=self.ui_scale_index > 0,
            can_scale_up=self.ui_scale_index < len(config.UI_SCALE_PRESETS) - 1,
            can_size_down=self.array_size > config.ARRAY_MIN_SIZE,
            can_size_up=self.array_size < config.ARRAY_MAX_SIZE,
            can_speed_down=self.speed_index > 0,
            can_speed_up=self.speed_index < len(config.SPEED_PRESETS) - 1,
        )

    def _generate_values(self, size: int) -> list[int]:
        values = list(range(1, size + 1))
        random.shuffle(values)
        return values

    def shuffle_values(self, *, animate: bool = True) -> None:
        self.original_values = self._generate_values(self.array_size)
        self.reset_array(animate=animate)

    def reset_array(self, *, animate: bool = False) -> None:
        self._stop_sort()
        self.metrics = SortMetrics()
        self.visualizer.set_data(self.original_values, animate=animate)

    def start_sorting(self) -> None:
        if self.completed:
            self.reset_array()
        if self.generator is None:
            self._begin_sort()
        self.auto_running = True

    def toggle_pause(self) -> None:
        if self.generator is None or self.completed:
            return
        self.auto_running = not self.auto_running

    def step_once(self) -> None:
        if self.completed:
            return
        if self.generator is None:
            self._begin_sort()
        self.auto_running = False
        self._advance_events(1)

    def change_speed(self, direction: int) -> None:
        new_index = int(clamp(self.speed_index + direction, 0, len(config.SPEED_PRESETS) - 1))
        self.speed_index = new_index

    def change_size(self, direction: int) -> None:
        new_size = int(clamp(self.array_size + direction * config.ARRAY_SIZE_STEP, config.ARRAY_MIN_SIZE, config.ARRAY_MAX_SIZE))
        if new_size == self.array_size:
            return
        self.array_size = new_size
        self.shuffle_values()

    def change_ui_scale(self, direction: int) -> None:
        new_index = int(clamp(self.ui_scale_index + direction, 0, len(config.UI_SCALE_PRESETS) - 1))
        if new_index == self.ui_scale_index:
            return
        self.ui_scale_index = new_index
        self.ui.set_scale(self.current_ui_scale)
        self.visualizer.set_scale(self.current_ui_scale)

    def select_algorithm(self, index: int) -> None:
        bounded = int(clamp(index, 0, len(ALGORITHMS) - 1))
        if bounded == self.algorithm_index:
            return
        self.algorithm_index = bounded
        self.reset_array()

    def cycle_algorithm(self, direction: int) -> None:
        self.algorithm_index = (self.algorithm_index + direction) % len(ALGORITHMS)
        self.reset_array()

    def _begin_sort(self) -> None:
        self.metrics = SortMetrics()
        self.step_accumulator = 0.0
        self.completed = False
        self.visualizer.prepare_for_sort()
        current_values = self.visualizer.snapshot_values()
        self.generator = self.current_algorithm.generator_factory(current_values)

    def _advance_sort(self, dt: float) -> None:
        if not self.auto_running or self.generator is None:
            return

        self.metrics.elapsed += dt
        self.step_accumulator += dt * self.current_speed
        steps = min(config.MAX_EVENTS_PER_FRAME, int(self.step_accumulator))
        if steps <= 0:
            return

        self.step_accumulator -= steps
        self._advance_events(steps)

    def _advance_events(self, count: int) -> None:
        for _ in range(count):
            if self.generator is None:
                return
            try:
                event = next(self.generator)
            except StopIteration:
                self._finish_sort()
                return
            self._apply_event(event)

    def _apply_event(self, event: SortEvent) -> None:
        if event.kind == "compare":
            self.metrics.comparisons += 1
        elif event.kind == "swap":
            self.metrics.swaps += 1
        elif event.kind == "overwrite":
            self.metrics.writes += 1
        self.visualizer.apply_event(event)

    def _finish_sort(self) -> None:
        self.generator = None
        self.auto_running = False
        self.completed = True
        self.step_accumulator = 0.0
        self.visualizer.start_completion_animation()

    def _stop_sort(self) -> None:
        self.generator = None
        self.auto_running = False
        self.step_accumulator = 0.0
        self.completed = False

    def _get_display_size(self) -> tuple[int, int]:
        sizes = pygame.display.get_desktop_sizes()
        if sizes:
            return max(sizes, key=lambda size: size[0] * size[1])

        display_info = pygame.display.Info()
        if display_info.current_w and display_info.current_h:
            return display_info.current_w, display_info.current_h

        return config.WINDOW_WIDTH, config.WINDOW_HEIGHT

    def _detect_ui_scale_index(self, display_size: tuple[int, int]) -> int:
        width, height = display_size

        if width >= 3200 or height >= 1900:
            target_scale = 1.45
        elif width >= 2800 or height >= 1700:
            target_scale = 1.3
        elif width >= 2400 or height >= 1440:
            target_scale = 1.15
        else:
            target_scale = 1.0

        closest_index = 0
        closest_distance = float("inf")
        for index, scale in enumerate(config.UI_SCALE_PRESETS):
            distance = abs(scale - target_scale)
            if distance < closest_distance:
                closest_index = index
                closest_distance = distance
        return closest_index

    def _initial_window_size(self, display_size: tuple[int, int]) -> tuple[int, int]:
        width, height = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        display_width, display_height = display_size

        if display_width >= 2800 or display_height >= 1700:
            width = min(display_width - 140, 1880)
            height = min(display_height - 140, 1180)
        else:
            width = min(width, max(960, display_width - 80))
            height = min(height, max(720, display_height - 80))

        return self._clamp_window_size((width, height))

    def _clamp_window_size(self, size: tuple[int, int]) -> tuple[int, int]:
        width, height = size
        return max(config.MIN_WINDOW_WIDTH, int(width)), max(config.MIN_WINDOW_HEIGHT, int(height))

    def _resize_window(self, size: tuple[int, int]) -> None:
        clamped_size = self._clamp_window_size(size)
        if clamped_size != self.screen.get_size():
            self.screen = pygame.display.set_mode(clamped_size, pygame.RESIZABLE)
