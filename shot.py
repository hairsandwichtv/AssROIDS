import pygame
from circleshape import CircleShape
from constants import LINE_WIDTH, SHOT_RADIUS, SCREEN_WIDTH, SCREEN_HEIGHT

_CULL_MARGIN = 20  # px beyond screen edge before killing shot

class Shot(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, SHOT_RADIUS)

    def draw(self, screen):
        pygame.draw.circle(screen, "white", self.position, self.radius, LINE_WIDTH)

    def update(self, dt):
        self.position += self.velocity * dt
        # Kill shots that have left the screen
        if (self.position.x < -_CULL_MARGIN or self.position.x > SCREEN_WIDTH  + _CULL_MARGIN or
                self.position.y < -_CULL_MARGIN or self.position.y > SCREEN_HEIGHT + _CULL_MARGIN):
            self.kill()
