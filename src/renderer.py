"""Pygame rendering for the simulation and status overlay."""
from __future__ import annotations

import pygame

from camera import Camera, LAYER_SPREAD
from engine import GameEngine
from ui import Slider, BLACK, WHITE, UI_BG

DARK_GRAY = (32, 32, 32)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 100, 0)
RED = (255, 100, 100)
DARK_RED = (120, 30, 30)
UI_HEIGHT = 50
LAYER_FOG = 0.55

class GameRenderer:
    """Draws the lattice (2D or pseudo-3D) and the UI overlay."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen

    @staticmethod
    def _tinted(color: tuple[int, int, int], z: int, depth: int) -> tuple[int, int, int]:
        """Darken ``color`` for deep layers to give a sense of depth."""
        if depth <= 1:
            return color
        factor = 1.0 - LAYER_FOG * (z / max(1, depth - 1))
        return (
            max(0, int(color[0] * factor)),
            max(0, int(color[1] * factor)),
            max(0, int(color[2] * factor)),
        )

    def _draw_layer(
        self,
        engine: GameEngine,
        camera: Camera,
        z: int,
        ui_height: int,
        draw_grid_lines: bool,
    ) -> None:
        screen_w, screen_h = self.screen.get_size()
        cell_size = camera.cell_size
        dx, dy = camera.layer_offset(z)

        start_x = max(0, int(-(camera.offset_x + dx) / cell_size))
        start_y = max(0, int(-(camera.offset_y + dy) / cell_size))
        end_x = min(engine.width, start_x + int(screen_w / cell_size) + 2)
        end_y = min(engine.height, start_y + int(screen_h / cell_size) + 2)

        # Cache per-layer colours to avoid recomputing inside the hot loop.
        red = self._tinted(RED, z, engine.depth)
        red_edge = self._tinted(DARK_RED, z, engine.depth)
        green = self._tinted(GREEN, z, engine.depth)
        green_edge = self._tinted(DARK_GREEN, z, engine.depth)
        grid_line = self._tinted(DARK_GRAY, z, engine.depth)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                sx = x * cell_size + camera.offset_x + dx
                sy = y * cell_size + camera.offset_y + dy
                if not (0 <= sy < screen_h - ui_height):
                    continue

                x1, y1 = int(sx), int(sy)
                x2, y2 = int(sx + cell_size), int(sy + cell_size)
                cell_rect = pygame.Rect(x1, y1, x2 - x1, y2 - y1)

                if engine.red_mask[z, y, x]:
                    pygame.draw.rect(self.screen, red, cell_rect)
                    if cell_size > 10:
                        pygame.draw.rect(self.screen, red_edge, cell_rect, 1)
                elif engine.grid[z, y, x]:
                    pygame.draw.rect(self.screen, green, cell_rect)
                    if cell_size > 10:
                        pygame.draw.rect(self.screen, green_edge, cell_rect, 1)
                elif draw_grid_lines and cell_size > 3:
                    pygame.draw.rect(self.screen, grid_line, cell_rect, 1)

    def draw_grid(self, engine: GameEngine, camera: Camera, ui_height: int) -> None:
        self.screen.fill(BLACK)
        # Back-to-front so nearer layers occlude farther ones.
        for z in range(engine.depth - 1, -1, -1):
            draw_lines = (engine.depth == 1) or (z == camera.active_layer)
            self._draw_layer(engine, camera, z, ui_height, draw_lines)

    def draw_ui(self, fps_slider: Slider, font: pygame.font.Font) -> None:
        screen_w, screen_h = self.screen.get_size()
        ui_surface = pygame.Surface((screen_w, UI_HEIGHT), pygame.SRCALPHA)
        ui_surface.fill((*UI_BG, 200))
        self.screen.blit(ui_surface, (0, screen_h - UI_HEIGHT))
        fps_slider.draw(self.screen, font)

    def draw_stats(
        self,
        engine: GameEngine,
        camera: Camera,
        font: pygame.font.Font,
        paused: bool,
    ) -> None:
        state = "PAUSED" if paused else "RUNNING"
        mode = "3D" if engine.is_3d else "2D"
        text = (
            f"Generation: {engine.generation} | Population: {engine.population} | "
            f"Mode: {mode} | {state}"
        )
        if engine.is_3d:
            text += f" | Layer: {camera.active_layer}"
        surface = font.render(text, True, WHITE)
        self.screen.blit(surface, (10, 10))
