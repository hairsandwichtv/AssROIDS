import pygame
import random
from circleshape import CircleShape
from constants import LINE_WIDTH, ASTEROID_MIN_RADIUS
from logger import log_event
from asset_helper import asset_path

BUTT_IMG = pygame.image.load(asset_path("butt.png"))
POOP_IMG = pygame.image.load(asset_path("poop.png"))

class Asteroid(CircleShape):
    def __init__(self, x, y, radius):
        super().__init__(x, y, radius)

        base_img = POOP_IMG if radius <= ASTEROID_MIN_RADIUS else BUTT_IMG
        size = int(radius * 2)
        self.original_image = pygame.transform.scale(base_img, (size, size))
        self.image = self.original_image
        self.angle = random.uniform(0, 360)
        self.rotation_speed = 0

    def draw(self, screen):
        rotated_image = pygame.transform.rotate(self.original_image, self.angle)
        new_rect = rotated_image.get_rect(center=(self.position.x, self.position.y))
        screen.blit(rotated_image, new_rect.topleft)

    def update(self, dt):
        self.position += (self.velocity * dt)
        if self.radius <= ASTEROID_MIN_RADIUS:
            speed = self.velocity.length()
            self.angle += speed * dt * 2
            self.angle %= 360

    def split(self):
        self.kill()
        if self.radius <= ASTEROID_MIN_RADIUS:
            return
        log_event("asteroid_split")

        random_angle = random.uniform(20, 50)
        new_velocity1 = self.velocity.rotate(random_angle)
        new_velocity2 = self.velocity.rotate(-random_angle)
        new_radius = self.radius - ASTEROID_MIN_RADIUS

        asteroid1 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid2 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid1.velocity = new_velocity1 * 1.2
        asteroid2.velocity = new_velocity2 * 1.2
