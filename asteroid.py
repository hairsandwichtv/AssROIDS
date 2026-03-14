import pygame
import random
from circleshape import CircleShape
from constants import LINE_WIDTH, ASTEROID_MIN_RADIUS
from logger import log_event

BUTT_IMG = pygame.image.load("butt.png")
POOP_IMG = pygame.image.load("poop.png")

class Asteroid(CircleShape):
    def __init__(self, x, y, radius):
        super().__init__(x, y, radius)

        base_img = POOP_IMG if radius <= ASTEROID_MIN_RADIUS else BUTT_IMG
        size = int(radius * 2)
        self.image = pygame.transform.scale(base_img, (size, size))

    def draw(self, screen):
        render_pos = (self.position.x - self.radius, self.position.y - self.radius)
        screen.blit(self.image, render_pos)

    def update(self, dt):
        self.position += (self.velocity * dt)

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
