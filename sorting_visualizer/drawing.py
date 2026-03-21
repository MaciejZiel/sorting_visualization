from __future__ import annotations

import math
from collections import OrderedDict

import pygame


_PANEL_MARGIN = 26
_PANEL_CACHE_LIMIT = 192
_panel_cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()


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


def _draw_glow_onto(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    radius: int,
    strength: float,
    layers: int,
) -> None:
    for layer in range(layers, 0, -1):
        inflate = layer * 12
        alpha = (18 + layer * 8) * strength
        pygame.draw.rect(
            surface,
            with_alpha(color, alpha),
            rect.inflate(inflate, inflate),
            border_radius=radius + layer * 6,
        )


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

    padding = _PANEL_MARGIN
    glow = pygame.Surface((rect.width + padding * 2, rect.height + padding * 2), pygame.SRCALPHA)
    inner = pygame.Rect(padding, padding, rect.width, rect.height)
    _draw_glow_onto(glow, inner, color, radius, strength, layers)
    surface.blit(glow, (rect.x - padding, rect.y - padding))


def _panel_cache_key(
    size: tuple[int, int],
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
    radius: int,
    glow_color: tuple[int, int, int] | None,
    glow_strength: float,
    shadow_alpha: int,
    fill_alpha: int,
    border_alpha: int,
    gloss_alpha: int,
    gloss_height_ratio: float,
) -> tuple:
    return (
        size,
        fill,
        border,
        radius,
        glow_color,
        round(glow_strength, 2),
        shadow_alpha,
        fill_alpha,
        border_alpha,
        gloss_alpha,
        round(gloss_height_ratio, 2),
    )


def _build_panel_surface(
    size: tuple[int, int],
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
    radius: int,
    *,
    glow_color: tuple[int, int, int] | None,
    glow_strength: float,
    shadow_alpha: int,
    fill_alpha: int,
    border_alpha: int,
    gloss_alpha: int,
    gloss_height_ratio: float,
) -> pygame.Surface:
    surface = pygame.Surface((size[0] + _PANEL_MARGIN * 2, size[1] + _PANEL_MARGIN * 2), pygame.SRCALPHA)
    rect = pygame.Rect(_PANEL_MARGIN, _PANEL_MARGIN, size[0], size[1])

    if shadow_alpha > 0:
        shadow_rect = pygame.Rect(rect.x, rect.y + 8, rect.width, rect.height)
        pygame.draw.rect(surface, (0, 0, 0, shadow_alpha), shadow_rect, border_radius=radius + 6)

    if glow_color is not None and glow_strength > 0:
        _draw_glow_onto(surface, rect, glow_color, radius, glow_strength, layers=4)

    panel = pygame.Surface(size, pygame.SRCALPHA)
    panel_rect = panel.get_rect()
    pygame.draw.rect(panel, with_alpha(fill, fill_alpha), panel_rect, border_radius=radius)
    if gloss_alpha > 0:
        gloss_rect = pygame.Rect(1, 1, size[0] - 2, max(24, int(size[1] * gloss_height_ratio)))
        pygame.draw.rect(panel, with_alpha(lighten(fill, 0.14), gloss_alpha), gloss_rect, border_radius=radius)
    if border_alpha > 0:
        pygame.draw.rect(panel, with_alpha(border, border_alpha), panel_rect, width=1, border_radius=radius)
    surface.blit(panel, rect.topleft)
    return surface


def _get_panel_surface(
    size: tuple[int, int],
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
    radius: int,
    *,
    glow_color: tuple[int, int, int] | None,
    glow_strength: float,
    shadow_alpha: int,
    fill_alpha: int,
    border_alpha: int,
    gloss_alpha: int,
    gloss_height_ratio: float,
) -> pygame.Surface:
    key = _panel_cache_key(
        size,
        fill,
        border,
        radius,
        glow_color,
        glow_strength,
        shadow_alpha,
        fill_alpha,
        border_alpha,
        gloss_alpha,
        gloss_height_ratio,
    )
    cached = _panel_cache.get(key)
    if cached is not None:
        _panel_cache.move_to_end(key)
        return cached

    panel_surface = _build_panel_surface(
        size,
        fill,
        border,
        radius,
        glow_color=glow_color,
        glow_strength=glow_strength,
        shadow_alpha=shadow_alpha,
        fill_alpha=fill_alpha,
        border_alpha=border_alpha,
        gloss_alpha=gloss_alpha,
        gloss_height_ratio=gloss_height_ratio,
    )
    _panel_cache[key] = panel_surface
    if len(_panel_cache) > _PANEL_CACHE_LIMIT:
        _panel_cache.popitem(last=False)
    return panel_surface


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
    panel_surface = _get_panel_surface(
        rect.size,
        fill,
        border,
        radius,
        glow_color=glow_color,
        glow_strength=glow_strength,
        shadow_alpha=shadow_alpha,
        fill_alpha=fill_alpha,
        border_alpha=border_alpha,
        gloss_alpha=gloss_alpha,
        gloss_height_ratio=gloss_height_ratio,
    )
    surface.blit(panel_surface, (rect.x - _PANEL_MARGIN, rect.y - _PANEL_MARGIN))
