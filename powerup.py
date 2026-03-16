import pygame
import random
from circleshape import CircleShape
from asset_helper import asset_path

CONDOM_IMG = pygame.image.load(asset_path("Condom Power Up Icon.png"))
ZINC_IMG   = pygame.image.load(asset_path("Zinc Tab Power Up Icon.png"))

POWERUP_SIZE = 44  # diameter of the icon

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
        super().__init__(pos.x, pos.y, POWERUP_SIZE // 2)
        self.kind = kind  # "condom" or "zinc"
        base_img = CONDOM_IMG if kind == "condom" else ZINC_IMG
        self.original_image = pygame.transform.scale(
            base_img, (POWERUP_SIZE, POWERUP_SIZE)
        ).convert_alpha()
        self.angle = 0
        speed = random.uniform(80, 130)
        direction = edge_dir.rotate(random.uniform(-25, 25))
        self.velocity = direction * speed

    def draw(self, screen):
        rotated = pygame.transform.rotate(self.original_image, self.angle)
        rect = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(rotated, rect.topleft)

    def update(self, dt):
        self.position += self.velocity * dt
        self.angle = (self.angle + 110 * dt) % 360
        # Despawn once well off screen
        if (self.position.x < -100 or self.position.x > 1380 or
                self.position.y < -100 or self.position.y > 820):
            self.kill()
