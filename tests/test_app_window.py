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


if __name__ == "__main__":
    unittest.main()
