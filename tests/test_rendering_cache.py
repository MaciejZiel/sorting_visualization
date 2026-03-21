from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from sorting_visualizer import drawing, renderer


class RenderingCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()

    def tearDown(self) -> None:
        pygame.quit()
        drawing._panel_cache.clear()
        renderer._background_cache.clear()

    def test_draw_panel_reuses_cached_surface(self) -> None:
        surface = pygame.Surface((320, 240), pygame.SRCALPHA)
        rect = pygame.Rect(20, 20, 180, 90)

        drawing.draw_panel(surface, rect, (10, 20, 30), (40, 50, 60), 18, glow_color=(70, 80, 90), glow_strength=0.12)
        cached_after_first_draw = len(drawing._panel_cache)
        drawing.draw_panel(surface, rect, (10, 20, 30), (40, 50, 60), 18, glow_color=(70, 80, 90), glow_strength=0.12)

        self.assertEqual(cached_after_first_draw, 1)
        self.assertEqual(len(drawing._panel_cache), 1)

    def test_scene_background_reuses_base_surface_per_size(self) -> None:
        surface = pygame.Surface((640, 360))

        renderer.draw_scene_background(surface, 0.0)
        renderer.draw_scene_background(surface, 1.0)

        self.assertEqual(len(renderer._background_cache), 1)


if __name__ == "__main__":
    unittest.main()
