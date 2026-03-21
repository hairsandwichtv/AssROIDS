import pygame

# Set to True to draw collision circles on all objects for debugging
DEBUG_HITBOXES = True

# Base class for game objects
class CircleShape(pygame.sprite.Sprite):
    def __init__(self, x, y, radius):
        if hasattr(self, "containers"):
            super().__init__(self.containers)
        else:
            super().__init__()

        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.radius = radius

    def draw(self, screen):
        pass

    def collides_with(self, other):
        distance = self.position.distance_to(other.position)
        return distance <= (self.radius + other.radius)

    def draw_debug(self, screen):
        """Draw collision circle overlay — only active when DEBUG_HITBOXES is True."""
        if DEBUG_HITBOXES:
            pygame.draw.circle(screen, (255, 0, 0),
                               (int(self.position.x), int(self.position.y)),
                               self.radius, 1)

    def update(self, dt):
        pass
