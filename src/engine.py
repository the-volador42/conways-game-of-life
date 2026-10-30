"""Simulation rules and state management for Conway's Game of Life."""
from __future__ import annotations

import numpy as np
from numba import njit

AI_FOV_SIZE_2D = 64
AI_FOV_SIZE_3D = 16

@njit(cache=True)
def _step_generation_2d(grid, red_mask):
    """Advance one 2D Conway generation on a torus.

    ``grid`` is expected to be 3D with ``depth == 1`` — layer 0 is the only
    plane that gets simulated.  Cells flagged in ``red_mask`` are immortal.
    """
    depth, height, width = grid.shape
    new_grid = np.zeros_like(grid)
    for y in range(height):
        for x in range(width):
            if red_mask[0, y, x]:
                new_grid[0, y, x] = 1
                continue

            neighbors = 0
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dx == 0 and dy == 0:
                        continue
                    nx = (x + dx) % width
                    ny = (y + dy) % height
                    neighbors += grid[0, ny, nx]

            alive = grid[0, y, x] == 1
            if alive:
                if neighbors == 2 or neighbors == 3:
                    new_grid[0, y, x] = 1
            else:
                if neighbors == 3:
                    new_grid[0, y, x] = 1
    return new_grid

@njit(cache=True)
def _step_generation_3d(grid, red_mask):
    """Advance one 3D Life generation on a torus (rule B5/S45).

    Each cell has up to 26 neighbours in the wrapped cubic lattice.
    """
    depth, height, width = grid.shape
    new_grid = np.zeros_like(grid)
    for z in range(depth):
        for y in range(height):
            for x in range(width):
                if red_mask[z, y, x]:
                    new_grid[z, y, x] = 1
                    continue

                neighbors = 0
                for dz in range(-1, 2):
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            if dx == 0 and dy == 0 and dz == 0:
                                continue
                            nx = (x + dx) % width
                            ny = (y + dy) % height
                            nz = (z + dz) % depth
                            neighbors += grid[nz, ny, nx]

                alive = grid[z, y, x] == 1
                if alive:
                    if 4 <= neighbors <= 5:
                        new_grid[z, y, x] = 1
                else:
                    if neighbors == 5:
                        new_grid[z, y, x] = 1
    return new_grid

def _step_generation(grid: np.ndarray, red_mask: np.ndarray) -> np.ndarray:
    """Advance one generation using the rule for the grid's dimensionality."""
    if grid.shape[0] > 1:
        return _step_generation_3d(grid, red_mask)
    return _step_generation_2d(grid, red_mask)


class GameEngine:
    """Owns the cellular lattice and advances generations.

    The grid is always shaped ``(depth, height, width)``.  In 2D mode
    ``depth == 1`` and the classic Conway rule is applied to the single plane.
    In 3D mode the full cubic lattice is simulated with rule B5/S45.

    A single immortal red cell acts as the reference point that the AI
    observes; it is placed at the centre of the lattice in both modes.
    """

    def __init__(self, width: int, height: int, depth: int = 1) -> None:
        self.width = int(width)
        self.height = int(height)
        self.depth = int(depth)

        self.grid = np.zeros((self.depth, self.height, self.width), dtype=np.int8)
        self.red_mask = np.zeros((self.depth, self.height, self.width), dtype=np.bool_)

        red_x = self.width // 2
        red_y = self.height // 2
        red_z = self.depth // 2
        self.red_cells: set[tuple[int, int, int]] = {(red_x, red_y, red_z)}

        self.generation = 0
        self.population = 0
        self._apply_red_cells()
        self.update_population()

    # ---- properties ------------------------------------------------------ #

    @property
    def is_3d(self) -> bool:
        """``True`` when the lattice spans more than one layer."""
        return self.depth > 1

    # ---- state manipulation --------------------------------------------- #

    def _apply_red_cells(self) -> None:
        for x, y, z in self.red_cells:
            if 0 <= x < self.width and 0 <= y < self.height and 0 <= z < self.depth:
                self.grid[z, y, x] = 1
                self.red_mask[z, y, x] = True

    def randomize(self, density: float = 0.3) -> None:
        shape = (self.depth, self.height, self.width)
        self.grid = (np.random.random(shape) < density).astype(np.int8)
        self._apply_red_cells()
        self.update_population()

    def clear(self) -> None:
        self.grid.fill(0)
        self._apply_red_cells()
        self.generation = 0
        self.update_population()

    def toggle_cell(self, x: int, y: int, z: int = 0) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height and 0 <= z < self.depth):
            return
        if self.red_mask[z, y, x]:
            return
        self.grid[z, y, x] = 1 - self.grid[z, y, x]
        self.update_population()

    def set_cell_alive(self, x: int, y: int, z: int = 0) -> None:
        """Idempotently bring a cell to life (used by the paint brush)."""
        if not (0 <= x < self.width and 0 <= y < self.height and 0 <= z < self.depth):
            return
        if self.red_mask[z, y, x]:
            return
        if self.grid[z, y, x] == 1:
            return
        self.grid[z, y, x] = 1
        self.population += 1

    def update_population(self) -> None:
        self.population = int(self.grid.sum())

    def next_generation(self) -> None:
        self.grid = _step_generation(self.grid, self.red_mask)
        self.generation += 1
        self.update_population()

    # ---- AI interface ---------------------------------------------------- #

    def get_matrix_for_ai(self) -> list[tuple[int, int, int, int]]:
        """Return observations around the red control cell.

        A cubic window is centred on the red cell and wrapped toroidally
        around the lattice.  The result is a flat list of
        ``(x, y, z, alive)`` tuples — in 2D mode ``z`` is always 0.
        """
        if not self.red_cells:
            return []

        center_x, center_y, center_z = next(iter(self.red_cells))

        if self.is_3d:
            half = AI_FOV_SIZE_3D // 2
            matrix: list[tuple[int, int, int, int]] = []
            for dz in range(-half, half):
                for dy in range(-half, half):
                    for dx in range(-half, half):
                        x = (center_x + dx) % self.width
                        y = (center_y + dy) % self.height
                        z = (center_z + dz) % self.depth
                        matrix.append((x, y, z, int(self.grid[z, y, x])))
            return matrix

        half = AI_FOV_SIZE_2D // 2
        matrix = []
        for dy in range(-half, half):
            for dx in range(-half, half):
                x = (center_x + dx) % self.width
                y = (center_y + dy) % self.height
                matrix.append((x, y, 0, int(self.grid[0, y, x])))
        return matrix
