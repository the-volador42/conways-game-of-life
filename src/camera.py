"""Camera controls and grid-to-screen coordinate conversion."""
from __future__ import annotations

import math

LAYER_SPREAD = 0.5
ROTATION_SPEED = 0.01

class Camera:
    """Pans, zooms, rotates and projects grid coordinates onto screen space."""

    def __init__(self, initial_cell_size: float, is_3d: bool = False) -> None:
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.cell_size = float(initial_cell_size)
        self.min_cell_size = 2.0
        self.max_cell_size = 50.0

        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_offset_start_x = 0.0
        self.drag_offset_start_y = 0.0

        # Pseudo-3D view angle.  -pi/4 reproduces the original fixed look.
        self.rotation = -math.pi / 4
        self.rotating = False
        self.rotate_start_x = 0
        self.rotate_start_rotation = 0.0

        # Layer currently being edited (3D mode only).
        self.active_layer = 0
        self.is_3d = is_3d

    # ---- projection helpers --------------------------------------------- #

    def layer_offset(self, z: int) -> tuple[float, float]:
        """Return the screen-space offset applied to layer ``z``.

        The magnitude matches the original fixed offset so switching between
        the old and new camera feels identical; only the direction depends
        on :attr:`rotation`.
        """
        if not self.is_3d:
            return 0.0, 0.0
        spread = self.cell_size * LAYER_SPREAD * math.sqrt(2.0)
        return (
            z * spread * math.cos(self.rotation),
            z * spread * math.sin(self.rotation),
        )

    def screen_to_grid(
        self, screen_x: float, screen_y: float, z: int = 0
    ) -> tuple[int, int]:
        """Convert a screen pixel to grid coordinates on layer ``z``."""
        dx, dy = self.layer_offset(z)
        return (
            int((screen_x - self.offset_x - dx) // self.cell_size),
            int((screen_y - self.offset_y - dy) // self.cell_size),
        )

    # ---- panning -------------------------------------------------------- #

    def start_drag(self, mouse_x: int, mouse_y: int) -> None:
        self.dragging = True
        self.drag_start_x = mouse_x
        self.drag_start_y = mouse_y
        self.drag_offset_start_x = self.offset_x
        self.drag_offset_start_y = self.offset_y

    def update_drag(self, mouse_x: int, mouse_y: int) -> None:
        if not self.dragging:
            return
        self.offset_x = self.drag_offset_start_x + (mouse_x - self.drag_start_x)
        self.offset_y = self.drag_offset_start_y + (mouse_y - self.drag_start_y)

    def end_drag(self) -> None:
        self.dragging = False

    # ---- rotation (3D only) --------------------------------------------- #

    def start_rotation(self, mouse_x: int) -> None:
        self.rotating = True
        self.rotate_start_x = mouse_x
        self.rotate_start_rotation = self.rotation

    def update_rotation(self, mouse_x: int) -> None:
        if not self.rotating:
            return
        delta = mouse_x - self.rotate_start_x
        self.rotation = self.rotate_start_rotation + delta * ROTATION_SPEED

    def end_rotation(self) -> None:
        self.rotating = False

    # ---- zooming -------------------------------------------------------- #

    def zoom(self, mouse_x: int, mouse_y: int, zoom_in: bool) -> None:
        if zoom_in:
            new_cell_size = min(self.cell_size * 1.2, self.max_cell_size)
        else:
            new_cell_size = max(self.cell_size / 1.2, self.min_cell_size)
        ratio = new_cell_size / self.cell_size
        self.offset_x = mouse_x - ratio * (mouse_x - self.offset_x)
        self.offset_y = mouse_y - ratio * (mouse_y - self.offset_y)
        self.cell_size = new_cell_size
