"""Application entry point and pygame event loop."""
from __future__ import annotations

import numpy as np
import pygame

from camera import Camera
from engine import GameEngine, _step_generation_2d, _step_generation_3d
from renderer import GameRenderer
from ui import Slider

MODE_3D = False

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
INITIAL_CELL_SIZE = 10
GRID_WIDTH = 200
GRID_HEIGHT = 150
GRID_DEPTH_3D = 12
MIN_FPS = 1
MAX_FPS = 120
DEFAULT_FPS = 10
UI_HEIGHT = 50
SLIDER_WIDTH = 250
SLIDER_HEIGHT = 20


def _paint_line(
    engine: GameEngine,
    start: tuple[int, int],
    end: tuple[int, int],
    z: int,
) -> None:
    """Bring every cell on the segment ``start -> end`` to life.

    Uses linear interpolation so that fast drags don't leave gaps between
    frames.  Out-of-bounds cells are silently skipped by ``set_cell_alive``.
    """
    x0, y0 = start
    x1, y1 = end
    steps = max(abs(x1 - x0), abs(y1 - y0))
    if steps == 0:
        engine.set_cell_alive(x0, y0, z)
        return
    for i in range(steps + 1):
        t = i / steps
        gx = int(round(x0 + (x1 - x0) * t))
        gy = int(round(y0 + (y1 - y0) * t))
        engine.set_cell_alive(gx, gy, z)

def _build_engine() -> GameEngine:
    """Create the engine using the module-level MODE_3D flag."""
    depth = GRID_DEPTH_3D if MODE_3D else 1
    engine = GameEngine(GRID_WIDTH, GRID_HEIGHT, depth)
    engine.randomize(0.3)
    return engine

def _warm_up_jit() -> None:
    """Compile both kernels on tiny inputs so the first step never hitches."""
    _step_generation_2d(
        np.zeros((1, 2, 2), dtype=np.int8),
        np.zeros((1, 2, 2), dtype=np.bool_),
    )
    _step_generation_3d(
        np.zeros((2, 2, 2), dtype=np.int8),
        np.zeros((2, 2, 2), dtype=np.bool_),
    )

def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(
        "Conway's Game of Life — 3D" if MODE_3D else "Conway's Game of Life — 2D"
    )
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)

    engine = _build_engine()

    camera = Camera(INITIAL_CELL_SIZE, is_3d=MODE_3D)
    camera.active_layer = (engine.depth // 2) if engine.is_3d else 0

    renderer = GameRenderer(screen)

    fps_slider = Slider(
        0, 0, SLIDER_WIDTH, SLIDER_HEIGHT,
        MIN_FPS, MAX_FPS, DEFAULT_FPS, "Speed (FPS)",
    )

    def reposition_slider() -> None:
        w, h = screen.get_size()
        fps_slider.rect.right = w - 20
        fps_slider.rect.y = h - 35

    reposition_slider()
    _warm_up_jit()

    running = True
    paused = True

    # Paint-brush state (Shift + RMB drag).
    painting = False
    last_paint_grid: tuple[int, int] | None = None

    while running:
        mods = pygame.key.get_mods()
        ctrl_held = bool(mods & pygame.KMOD_CTRL)
        shift_held = bool(mods & pygame.KMOD_SHIFT)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                renderer.screen = screen
                reposition_slider()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    engine.randomize(0.3)
                elif event.key == pygame.K_c:
                    engine.clear()
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_UP, pygame.K_DOWN) and engine.is_3d:
                    if event.key == pygame.K_UP:
                        camera.active_layer = min(engine.depth - 1, camera.active_layer + 1)
                    else:
                        camera.active_layer = max(0, camera.active_layer - 1)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                w, h = screen.get_size()
                if event.pos[1] < h - UI_HEIGHT:
                    if event.button == 1:
                        # Ctrl + LMB -> rotate camera (3D only).
                        if engine.is_3d and ctrl_held:
                            camera.start_rotation(event.pos[0])
                        else:
                            gx, gy = camera.screen_to_grid(*event.pos, z=camera.active_layer)
                            engine.toggle_cell(gx, gy, camera.active_layer)
                    elif event.button == 2:
                        camera.start_drag(*event.pos)
                    elif event.button == 3:
                        # Shift + RMB -> start the paint brush.
                        if shift_held:
                            painting = True
                            gx, gy = camera.screen_to_grid(*event.pos, z=camera.active_layer)
                            engine.set_cell_alive(gx, gy, camera.active_layer)
                            last_paint_grid = (gx, gy)
                    elif event.button == 4:
                        camera.zoom(event.pos[0], event.pos[1], True)
                    elif event.button == 5:
                        camera.zoom(event.pos[0], event.pos[1], False)
                fps_slider.handle_event(event)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    camera.end_rotation()
                elif event.button == 2:
                    camera.end_drag()
                elif event.button == 3:
                    painting = False
                    last_paint_grid = None
                fps_slider.handle_event(event)

            elif event.type == pygame.MOUSEMOTION:
                if camera.rotating:
                    camera.update_rotation(event.pos[0])
                camera.update_drag(*event.pos)

                if painting:
                    gx, gy = camera.screen_to_grid(*event.pos, z=camera.active_layer)
                    if last_paint_grid is not None:
                        _paint_line(engine, last_paint_grid, (gx, gy), camera.active_layer)
                    else:
                        engine.set_cell_alive(gx, gy, camera.active_layer)
                    last_paint_grid = (gx, gy)

                fps_slider.handle_event(event)

        if not paused:
            engine.next_generation()

        renderer.draw_grid(engine, camera, UI_HEIGHT)
        renderer.draw_ui(fps_slider, font)
        renderer.draw_stats(engine, camera, font, paused)

        pygame.display.flip()
        clock.tick(int(fps_slider.value))

    pygame.quit()


if __name__ == "__main__":
    main()
