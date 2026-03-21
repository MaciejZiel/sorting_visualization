from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from sorting_visualizer.app import SortingVisualizerApp


class HelpOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = SortingVisualizerApp()

    def tearDown(self) -> None:
        pygame.quit()

    def test_f1_toggles_help_overlay(self) -> None:
        self.app._handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=0))
        self.assertTrue(self.app.show_help)

        self.app._handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=0))
        self.assertFalse(self.app.show_help)

    def test_escape_closes_help_without_quitting(self) -> None:
        self.app.show_help = True

        should_continue = self.app._handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))

        self.assertTrue(should_continue)
        self.assertFalse(self.app.show_help)


if __name__ == "__main__":
    unittest.main()
