import math
import struct
from dataclasses import dataclass


@dataclass
class Vec3:
    x: float
    y: float
    z: float

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def norm(self) -> "Vec3":
        length = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if length == 0:
            return Vec3(0, 0, 1)
        return Vec3(self.x / length, self.y / length, self.z / length)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


class Mesh:
    def __init__(self) -> None:
        self.triangles: list[tuple[Vec3, Vec3, Vec3]] = []

    def add_box(
        self,
        origin: Vec3,
        size: Vec3,
    ) -> None:
        x0, y0, z0 = origin.x, origin.y, origin.z
        x1, y1, z1 = origin.x + size.x, origin.y + size.y, origin.z + size.z
        v = [
            Vec3(x0, y0, z0),
            Vec3(x1, y0, z0),
            Vec3(x1, y1, z0),
            Vec3(x0, y1, z0),
            Vec3(x0, y0, z1),
            Vec3(x1, y0, z1),
            Vec3(x1, y1, z1),
            Vec3(x0, y1, z1),
        ]
        faces = [
            (0, 3, 2, 1),  # bottom (-Z)
            (4, 5, 6, 7),  # top (+Z)
            (0, 1, 4, 5),  # front (-Y)
            (1, 2, 5, 6),  # right (+X)
            (2, 3, 6, 7),  # back (+Y)
            (3, 0, 7, 4),  # left (-X)
        ]
        for a, b, c, d in faces:
            self._add_quad(v[a], v[b], v[c], v[d])

    def _add_quad(self, a: Vec3, b: Vec3, c: Vec3, d: Vec3) -> None:
        self.triangles.append((a, b, c))
        self.triangles.append((a, c, d))

    def write_binary_stl(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(b"PartsDB Organizer".ljust(80, b"\x00"))
            f.write(struct.pack("<I", len(self.triangles)))
            for a, b, c in self.triangles:
                normal = (b - a).cross(c - a).norm()
                f.write(struct.pack("<3f", normal.x, normal.y, normal.z))
                for vertex in (a, b, c):
                    f.write(struct.pack("<3f", vertex.x, vertex.y, vertex.z))
                f.write(struct.pack("<H", 0))
