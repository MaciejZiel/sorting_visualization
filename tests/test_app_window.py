from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from sorting_visualizer import config
from sorting_visualizer.app import SortingVisualizerApp


class AppWindowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = SortingVisualizerApp()

    def tearDown(self) -> None:
        pygame.quit()

    def test_window_size_is_clamped_to_minimum(self) -> None:
        self.assertEqual(
            self.app._clamp_window_size((320, 240)),
            (config.MIN_WINDOW_WIDTH, config.MIN_WINDOW_HEIGHT),
        )

    def test_video_resize_event_uses_size_attribute(self) -> None:
        # VIDEORESIZE carries size/w/h but no x/y attributes.
        event = pygame.event.Event(pygame.VIDEORESIZE, size=(1240, 840), w=1240, h=840)

        self.app._resize_window(self.app._resize_size_from_event(event))

        self.assertEqual(self.app.screen.get_size(), (1240, 840))

    def test_window_resized_event_uses_xy_attributes(self) -> None:
        event = pygame.event.Event(pygame.WINDOWRESIZED, x=1200, y=830)

        self.assertEqual(self.app._resize_size_from_event(event), (1200, 830))


if __name__ == "__main__":
    unittest.main()
