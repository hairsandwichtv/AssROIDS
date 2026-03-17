import pygame
import math
import random
from circleshape import CircleShape
from asset_helper import asset_path

CONDOM_IMG = pygame.image.load(asset_path("Condom Power Up Icon.png"))
ZINC_IMG   = pygame.image.load(asset_path("Zinc Tab Power Up Icon.png"))

POWERUP_SIZE = 44  # diameter of the icon

# Zinc pill ellipse — horizontal capsule (wide, not tall)
ZINC_ELLIPSE_A = 0.75   # semi-axis along width — lengthened to match pill
ZINC_ELLIPSE_B = 0.38   # semi-axis along height

# Condom square half-size as fraction of icon radius
CONDOM_SQUARE_SCALE = 0.82


class PowerUp(CircleShape):
    _edges = [
        (pygame.Vector2(1, 0),  lambda: pygame.Vector2(-60,  random.uniform(50, 670))),
        (pygame.Vector2(-1, 0), lambda: pygame.Vector2(1340, random.uniform(50, 670))),
        (pygame.Vector2(0, 1),  lambda: pygame.Vector2(random.uniform(50, 1230), -60)),
        (pygame.Vector2(0, -1), lambda: pygame.Vector2(random.uniform(50, 1230), 780)),
    ]

    def __init__(self, kind):
        edge_dir, pos_fn = random.choice(PowerUp._edges)
        pos = pos_fn()
        r = POWERUP_SIZE // 2
        super().__init__(pos.x, pos.y, r)
        self.kind = kind
        base_img = CONDOM_IMG if kind == "condom" else ZINC_IMG
        self.original_image = pygame.transform.scale(
            base_img, (POWERUP_SIZE, POWERUP_SIZE)
        ).convert_alpha()
        self.angle = 0
        speed = random.uniform(80, 130)
        direction = edge_dir.rotate(random.uniform(-25, 25))
        self.velocity = direction * speed

    def _condom_corners(self):
        """Return the 4 corners of the condom square rotated with the sprite."""
        half = self.radius * CONDOM_SQUARE_SCALE
        angle_rad = math.radians(-self.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        local = [(-half, -half), (half, -half), (half, half), (-half, half)]
        corners = []
        for lx, ly in local:
            wx = cos_a * lx - sin_a * ly + self.position.x
            wy = sin_a * lx + cos_a * ly + self.position.y
            corners.append(pygame.Vector2(wx, wy))
        return corners

    def collides_with(self, other):
        if self.kind == "condom":
            # Rotated square vs circle — check circle against each edge normal
            corners = self._condom_corners()
            cx, cy, r = other.position.x, other.position.y, other.radius
            # Test circle center against each axis of the rotated square
            for i in range(4):
                a = corners[i]
                b = corners[(i + 1) % 4]
                edge = b - a
                normal = pygame.Vector2(-edge.y, edge.x).normalize()
                # Project circle center onto normal
                proj = normal.dot(pygame.Vector2(cx, cy) - a)
                if proj < -r:
                    return False
                # Project all corners onto normal, find square extent
                projs = [normal.dot(c - a) for c in corners]
                if proj - r > max(projs):
                    return False
            return True
        else:
            # Rotated ellipse collision for zinc pill
            r_half = POWERUP_SIZE // 2
            a = r_half * ZINC_ELLIPSE_A
            b = r_half * ZINC_ELLIPSE_B
            r = other.radius
            dx = other.position.x - self.position.x
            dy = other.position.y - self.position.y
            angle_rad = math.radians(-self.angle)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            lx =  cos_a * dx + sin_a * dy
            ly = -sin_a * dx + cos_a * dy
            return (lx / (a + r)) ** 2 + (ly / (b + r)) ** 2 <= 1.0

    def draw_debug(self, screen):
        from circleshape import DEBUG_HITBOXES
        if not DEBUG_HITBOXES:
            return
        if self.kind == "condom":
            corners = self._condom_corners()
            pygame.draw.polygon(screen, (0, 255, 0),
                                [(int(v.x), int(v.y)) for v in corners], 1)
        else:
            r_half = POWERUP_SIZE // 2
            a = r_half * ZINC_ELLIPSE_A
            b = r_half * ZINC_ELLIPSE_B
            angle_rad = math.radians(-self.angle)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            points = []
            for i in range(36):
                t = math.radians(i * 10)
                ex = a * math.cos(t)
                ey = b * math.sin(t)
                wx = cos_a * ex - sin_a * ey + self.position.x
                wy = sin_a * ex + cos_a * ey + self.position.y
                points.append((int(wx), int(wy)))
            pygame.draw.polygon(screen, (0, 255, 0), points, 1)

    def draw(self, screen):
        rotated = pygame.transform.rotate(self.original_image, self.angle)
        rect = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(rotated, rect.topleft)

    def update(self, dt):
        self.position += self.velocity * dt
        self.angle = (self.angle + 110 * dt) % 360
        if (self.position.x < -100 or self.position.x > 1380 or
                self.position.y < -100 or self.position.y > 820):
            self.kill()
