from __future__ import annotations

import math

import pygame


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def exp_lerp(current: float, target: float, speed: float, dt: float) -> float:
    if dt <= 0:
        return current
    factor = 1.0 - math.exp(-speed * dt)
    return current + (target - current) * factor


def mix_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    amount = clamp(t, 0.0, 1.0)
    return tuple(int(a[index] + (b[index] - a[index]) * amount) for index in range(3))


def lighten(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return mix_color(color, (255, 255, 255), amount)


def darken(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return mix_color(color, (0, 0, 0), amount)


def with_alpha(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], int(clamp(alpha, 0, 255))


def draw_glow(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    radius: int,
    strength: float = 1.0,
    layers: int = 4,
) -> None:
    if strength <= 0:
        return

    padding = 26
    glow = pygame.Surface((rect.width + padding * 2, rect.height + padding * 2), pygame.SRCALPHA)
    inner = pygame.Rect(padding, padding, rect.width, rect.height)

    for layer in range(layers, 0, -1):
        inflate = layer * 12
        alpha = (18 + layer * 8) * strength
        pygame.draw.rect(
            glow,
            with_alpha(color, alpha),
            inner.inflate(inflate, inflate),
            border_radius=radius + layer * 6,
        )

    surface.blit(glow, (rect.x - padding, rect.y - padding))


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
    radius: int,
    *,
    glow_color: tuple[int, int, int] | None = None,
    glow_strength: float = 0.0,
    shadow_alpha: int = 92,
    fill_alpha: int = 248,
    border_alpha: int = 220,
    gloss_alpha: int = 36,
    gloss_height_ratio: float = 0.34,
) -> None:
    shadow_padding = 18
    shadow = pygame.Surface((rect.width + shadow_padding * 2, rect.height + shadow_padding * 2), pygame.SRCALPHA)
    shadow_rect = pygame.Rect(shadow_padding, shadow_padding + 8, rect.width, rect.height)
    pygame.draw.rect(shadow, (0, 0, 0, shadow_alpha), shadow_rect, border_radius=radius + 6)
    surface.blit(shadow, (rect.x - shadow_padding, rect.y - shadow_padding))

    if glow_color is not None and glow_strength > 0:
        draw_glow(surface, rect, glow_color, radius, glow_strength)

    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel_rect = panel.get_rect()
    pygame.draw.rect(panel, with_alpha(fill, fill_alpha), panel_rect, border_radius=radius)
    if gloss_alpha > 0:
        gloss_rect = pygame.Rect(1, 1, rect.width - 2, max(24, int(rect.height * gloss_height_ratio)))
        pygame.draw.rect(panel, with_alpha(lighten(fill, 0.14), gloss_alpha), gloss_rect, border_radius=radius)
    if border_alpha > 0:
        pygame.draw.rect(panel, with_alpha(border, border_alpha), panel_rect, width=1, border_radius=radius)
    surface.blit(panel, rect.topleft)
