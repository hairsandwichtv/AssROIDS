"""Pixel-perfect hitboxes — collision masks built from each sprite's visible pixels.

A sprite's hitbox is its image rotated exactly as it's drawn, with every pixel
above ALPHA_THRESHOLD counting as solid. Rotated masks are cached per sprite
key and ANGLE_STEP bucket, so after warm-up a collision test is a broad-phase
distance check plus one C-level mask overlap. Things with no sprite (shots,
Mandingo beam shots) use a filled circle mask of their radius.
"""
import pygame

ALPHA_THRESHOLD = 127   # pixels more opaque than this are solid
ANGLE_STEP      = 1     # degrees per cached rotation — matches how sprites are drawn

_sprite_cache = {}      # (key, angle bucket, shrink) → Mask
_circle_cache = {}      # radius → Mask


def sprite_mask(key, image, angle, shrink=0):
    """Mask of image rotated by angle (as pygame.transform.rotate draws it).
    key identifies the image for caching — e.g. ("boss", skin). shrink erodes
    the mask inward by that many pixels."""
    bucket = round(angle / ANGLE_STEP) % (360 // ANGLE_STEP)
    ck = (key, bucket, shrink)
    mask = _sprite_cache.get(ck)
    if mask is None:
        rotated = pygame.transform.rotate(image, bucket * ANGLE_STEP)
        mask = pygame.mask.from_surface(rotated, ALPHA_THRESHOLD)
        for _ in range(shrink):
            mask = _erode(mask)
        _sprite_cache[ck] = mask
    return mask


def circle_mask(radius):
    r = max(1, int(round(radius)))
    mask = _circle_cache.get(r)
    if mask is None:
        surf = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 255, 255, 255), (r, r), r)
        mask = _circle_cache[r] = pygame.mask.from_surface(surf, ALPHA_THRESHOLD)
    return mask


def reach(image):
    """Broad-phase radius — half the diagonal of the unrotated image."""
    w, h = image.get_size()
    return 0.5 * (w * w + h * h) ** 0.5


def _topleft(mask, center):
    # Same placement as surf.get_rect(center=(int(x), int(y))) when drawing
    w, h = mask.get_size()
    return int(center[0]) - w // 2, int(center[1]) - h // 2


def overlaps(mask_a, center_a, mask_b, center_b):
    ax, ay = _topleft(mask_a, center_a)
    bx, by = _topleft(mask_b, center_b)
    return mask_a.overlap(mask_b, (bx - ax, by - ay)) is not None


def mask_of(obj):
    """(mask, center) for anything with a position — its own hitbox if it has one,
    otherwise a circle of its radius."""
    hit_mask = getattr(obj, "hit_mask", None)
    if hit_mask is not None:
        return hit_mask()
    return circle_mask(obj.radius), obj.position


def reach_of(obj):
    hit_reach = getattr(obj, "hit_reach", None)
    return hit_reach() if hit_reach is not None else obj.radius


def collide(a, b):
    """Broad phase on reach, then exact pixel overlap. Both are game objects
    (CircleShape), so they always have hit_reach() / hit_mask()."""
    r = a.hit_reach() + b.hit_reach()
    if a.position.distance_squared_to(b.position) > r * r:
        return False
    return overlaps(*a.hit_mask(), *b.hit_mask())


def draw_outline(screen, mask, center, color=(255, 0, 0)):
    """DEBUG_HITBOXES overlay — the mask's outline where it sits on screen."""
    pts = mask.outline()
    if len(pts) > 2:
        x, y = _topleft(mask, center)
        pygame.draw.lines(screen, color, True, [(px + x, py + y) for px, py in pts], 1)


def _erode(mask):
    """Shrink a mask by one pixel: keep only pixels whose 4 neighbours are solid."""
    out = mask.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        out = out.overlap_mask(mask, (dx, dy))
    return out
