"""Reusable UI widgets and palette constants."""
from __future__ import annotations

import pygame

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SLIDER_BG = (50, 50, 50)
SLIDER_ACTIVE = (100, 100, 200)
UI_BG = (20, 20, 20)

class Slider:
    """Horizontal slider used to control the simulation FPS."""

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        min_value: float,
        max_value: float,
        initial_value: float,
        label: str,
    ) -> None:
        self.rect = pygame.Rect(x, y, width, height)
        self.min_value = min_value
        self.max_value = max_value
        self.value = float(initial_value)
        self.label = label
        self.dragging = False
        self.handle_radius = 8

    def _handle_x(self) -> float:
        rel = (self.value - self.min_value) / (self.max_value - self.min_value)
        return self.rect.x + rel * self.rect.width

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hx = self._handle_x()
            handle_rect = pygame.Rect(
                hx - self.handle_radius,
                self.rect.y - self.handle_radius,
                self.handle_radius * 2,
                self.rect.height + self.handle_radius * 2,
            )
            if handle_rect.collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            rel_x = max(0, min(event.pos[0] - self.rect.x, self.rect.width))
            self.value = self.min_value + (rel_x / self.rect.width) * (
                self.max_value - self.min_value
            )

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(screen, SLIDER_BG, self.rect, border_radius=5)
        filled = (self.value - self.min_value) / (
            self.max_value - self.min_value
        ) * self.rect.width
        if filled > 0:
            filled_rect = pygame.Rect(self.rect.x, self.rect.y, int(filled), self.rect.height)
            pygame.draw.rect(screen, SLIDER_ACTIVE, filled_rect, border_radius=5)
        hx = int(self._handle_x())
        hy = self.rect.y + self.rect.height // 2
        pygame.draw.circle(screen, WHITE, (hx, hy), self.handle_radius)
        pygame.draw.circle(screen, BLACK, (hx, hy), self.handle_radius - 2)
        label = font.render(f"{self.label}: {self.value:.1f}", True, WHITE)
        screen.blit(label, (self.rect.x, self.rect.y - 25))
