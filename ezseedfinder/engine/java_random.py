"""Java Random compatible with Minecraft world generation."""

from __future__ import annotations


class JavaRandom:
    def __init__(self, seed: int | None = None) -> None:
        self.seed = 0
        if seed is not None:
            self.set_seed(seed)

    def set_seed(self, seed: int) -> None:
        self.seed = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def _next(self, bits: int) -> int:
        self.seed = (self.seed * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
        return int(self.seed >> (48 - bits))

    def next_int(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be positive")
        if (n & -n) == n:
            return int(((n * self._next(31)) >> 31))
        while True:
            bits = self._next(31)
            val = bits % n
            if bits - val + (n - 1) >= 0:
                return val

    def next_float(self) -> float:
        return self._next(24) / float(1 << 24)

    def next_double(self) -> float:
        hi = self._next(26)
        lo = self._next(27)
        return ((hi << 27) + lo) / float(1 << 53)

    def next_long(self) -> int:
        hi = self._next(32)
        lo = self._next(32) & 0xFFFFFFFF
        val = (hi << 32) + lo
        if val >= 1 << 63:
            val -= 1 << 64
        return val

    def skip(self, count: int) -> None:
        for _ in range(count):
            self._next(32)


def chunk_generate_rnd(world_seed: int, chunk_x: int, chunk_z: int) -> JavaRandom:
    rng = JavaRandom(world_seed)
    a = rng.next_long()
    b = rng.next_long()
    mixed = (a * chunk_x) ^ (b * chunk_z) ^ (world_seed & ((1 << 64) - 1))
    out = JavaRandom()
    out.set_seed(mixed & ((1 << 64) - 1))
    return out


def block_pos_hash(x: int, y: int, z: int) -> int:
    v = ((y + z * 31) * 31 + x) & 0xFFFFFFFF
    if v >= 0x80000000:
        v -= 0x100000000
    return v


def structure_processor_seed(world_seed: int, x: int, y: int, z: int) -> int:
    return (world_seed + block_pos_hash(x, y, z)) & ((1 << 64) - 1)


def chest_loot_seed(world_seed: int, x: int, y: int, z: int) -> int:
    return (world_seed + block_pos_hash(x, y, z)) & ((1 << 64) - 1)
