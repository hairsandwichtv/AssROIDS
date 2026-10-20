import pygame
import hitmask

# Set to True to draw hitbox outlines on all objects for debugging
DEBUG_HITBOXES = False

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

    # ── Hitbox ───────────────────────────────────────────────────────────
    # Sprites override hit_mask()/hit_reach() (see SpriteHitbox); everything
    # else is a filled circle of self.radius.
    def hit_mask(self):
        return hitmask.circle_mask(self.radius), self.position

    def hit_reach(self):
        return self.radius

    def collides_with(self, other):
        return hitmask.collide(self, other)

    def draw_debug(self, screen):
        """Hitbox outline overlay — only active when DEBUG_HITBOXES is True."""
        if DEBUG_HITBOXES:
            hitmask.draw_outline(screen, *self.hit_mask())

    def update(self, dt):
        pass


class SpriteHitbox:
    """Mixin: the hitbox is the sprite's own visible pixels, rotated as drawn.
    Subclasses set hit_key and implement _hit_image() / _hit_angle()."""
    hit_key    = "sprite"
    hit_shrink = 0          # px eroded off the mask (player ship only)

    def _hit_image(self):
        return self.original_image

    def _hit_angle(self):
        return self.angle   # pygame.transform.rotate(image, angle) in draw()

    def hit_mask(self):
        return (hitmask.sprite_mask(self.hit_key, self._hit_image(), self._hit_angle(), self.hit_shrink),
                self.position)

    def hit_reach(self):
        r = self.__dict__.get("_hit_reach")   # image size never changes — work it out once
        if r is None:
            r = self._hit_reach = hitmask.reach(self._hit_image())
        return r
