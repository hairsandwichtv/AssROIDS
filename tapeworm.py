import pygame
import math
import random
from collections import deque
from asset_helper import asset_path
from constants import ASTEROID_MIN_RADIUS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WORMHOLE_VISUAL_R  = ASTEROID_MIN_RADIUS * 3
WORMHOLE_SPAWN_PCT = 0.36

HEAD_RADIUS  = 60
SEG_RADIUS   = 9
HEAD_SIZE    = HEAD_RADIUS * 2
SEG_SIZE     = SEG_RADIUS * 2
SEG_SPACING  = 2
CHAIN_LENGTH = 184

LUNGE_SPEED   = 460.0
RETRACT_SPEED = 200.0
FREE_SPEED    = 180.0
FLASH_DUR     = 0.12

# ---------------------------------------------------------------------------
# Lazy image loading
# ---------------------------------------------------------------------------
_wh_img = _head_img = _seg_img = None
_seg_rot_cache = {}

# Sounds — loaded lazily after pygame.mixer init
_snd_enter   = None
_snd_defeat  = None
_snd_split   = None
_snd_hit     = None
_snd_lunge   = None
_snd_croak   = None
_snd_rainbow = None
_audio_enabled = False

def set_audio_enabled(enabled):
    global _audio_enabled
    _audio_enabled = enabled

def _load_sounds():
    global _snd_enter, _snd_defeat, _snd_split, _snd_hit, _snd_lunge, _snd_croak, _snd_rainbow
    if _snd_enter is not None:
        return
    def _load(name):
        try:
            return pygame.mixer.Sound(asset_path(name))
        except Exception:
            return None
    _snd_enter   = _load("Tapeworm Enter.mp3")
    _snd_defeat  = _load("Tapeworm Defeat.mp3")
    _snd_split   = _load("Tapeworm Split.mp3")
    _snd_hit     = _load("Poop Splat.mp3")
    _snd_lunge   = _load("Tapeworm Lunge.mp3")
    _snd_croak   = _load("Croaking Ambience.mp3")
    _snd_rainbow = _load("Rainbow Hole.mp3")   # angle (quantized to 1°) → rotated surface

def _load_images():
    global _wh_img, _head_img, _seg_img
    if _wh_img is not None:
        return
    _wh_img   = pygame.transform.scale(
        pygame.image.load(asset_path("Worm Hole.png")).convert_alpha(),
        (WORMHOLE_VISUAL_R * 2, WORMHOLE_VISUAL_R * 2))
    _head_img = pygame.transform.scale(
        pygame.image.load(asset_path("Tapeworm Head.png")).convert_alpha(),
        (HEAD_SIZE, HEAD_SIZE))
    _seg_img  = pygame.transform.scale(
        pygame.image.load(asset_path("Tapeworm Prog128.png")).convert_alpha(),
        (SEG_SIZE, SEG_SIZE))
    _load_sounds()

def _get_seg_rotated(angle):
    """Return cached rotated segment surface, quantized to 1° for cache hits."""
    key = int(angle) % 360
    if key not in _seg_rot_cache:
        _seg_rot_cache[key] = pygame.transform.rotate(_seg_img, angle)
    return _seg_rot_cache[key]


# ---------------------------------------------------------------------------
# TapewormSegment — data only, positioned by TapewormHead each frame
# ---------------------------------------------------------------------------
class TapewormSegment:
    def __init__(self, x, y):
        self.position    = pygame.Vector2(x, y)
        self.angle       = 0.0
        self.flash_timer = 0.0
        self.alive       = True

    def kill(self):
        self.alive = False


# ---------------------------------------------------------------------------
# WormHole
# ---------------------------------------------------------------------------
class WormHole(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self, self.containers)
        _load_images()
        self.position       = pygame.Vector2(x, y)
        self.radius         = WORMHOLE_VISUAL_R
        self.state          = "anchoring"
        self._timer         = 0.0
        self._rainbow_phase = 0.0
        self._sparkles      = []
        self._spawned       = False

    def activate_rainbow(self):
        self.state = "rainbow"
        if _audio_enabled and _snd_rainbow:
            _snd_rainbow.play()
    def is_enterable(self): return self.state == "rainbow"

    def player_overlaps(self, player_pos, player_radius):
        return pygame.Vector2(player_pos).distance_to(self.position) <= self.radius + player_radius

    def update(self, dt):
        self._timer += dt
        if self.state != "rainbow":
            return
        self._rainbow_phase += dt * 5
        if random.random() < 0.5:
            angle = random.uniform(0, 360)
            r     = random.uniform(8, WORMHOLE_VISUAL_R)
            speed = random.uniform(25, 70)
            life  = random.uniform(0.3, 0.9)
            rad   = math.radians(angle)
            self._sparkles.append([
                self.position.x + math.cos(rad)*r,
                self.position.y + math.sin(rad)*r,
                math.cos(rad)*speed,
                math.sin(rad)*speed,
                life, life])
        new = []
        for s in self._sparkles:
            s[0] += s[2]*dt; s[1] += s[3]*dt; s[4] -= dt
            if s[4] > 0:
                new.append(s)
        self._sparkles = new

    def draw(self, screen):
        spin    = (self._timer * 25) % 360
        rotated = pygame.transform.rotate(_wh_img, spin)
        rect    = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(rotated, rect.topleft)
        if self.state != "rainbow":
            return
        ph = self._rainbow_phase
        for i in range(4):
            rc = int(abs(math.sin(ph+i*1.5))*255)
            gc = int(abs(math.sin(ph+i*1.5+2))*255)
            bc = int(abs(math.sin(ph+i*1.5+4))*255)
            rr = WORMHOLE_VISUAL_R + 6 + i*7
            gs = pygame.Surface((rr*2+4, rr*2+4), pygame.SRCALPHA)
            pygame.draw.circle(gs, (rc,gc,bc,160), (rr+2,rr+2), rr, 3)
            screen.blit(gs, (int(self.position.x)-rr-2, int(self.position.y)-rr-2))
        for s in self._sparkles:
            frac = s[4]/s[5]
            rc = int(abs(math.sin(ph+s[0]*0.01))*255)
            gc = int(abs(math.sin(ph+s[1]*0.01+2))*255)
            bc = int(abs(math.sin(ph+4))*255)
            pygame.draw.circle(screen, (rc,gc,bc), (int(s[0]),int(s[1])), max(1,int(4*frac)))


# ---------------------------------------------------------------------------
# TapewormHead
# ---------------------------------------------------------------------------
class TapewormHead(pygame.sprite.Sprite):

    def __init__(self, wormhole, segments, spice_level, anchored=True, start_pos=None):
        pygame.sprite.Sprite.__init__(self, self.containers)
        _load_images()
        self.wormhole    = wormhole
        self.segments    = list(segments)
        self.health      = 9 + spice_level // 2
        self.radius      = HEAD_RADIUS
        self.anchored    = anchored and (wormhole is not None)
        self._spice      = spice_level
        self.flash_timer = 0.0

        pivot         = wormhole.position if wormhole else pygame.Vector2(640, 360)
        self.position = pygame.Vector2(start_pos if start_pos else pivot)

        # Initial angle — points away from pivot so hitbox is correct from frame 1
        offset = self.position - pivot
        if offset.length() > 0:
            self.angle = math.degrees(math.atan2(-offset.y, offset.x)) + 90
        else:
            self.angle = 0.0

        # Spawn grow-in effect
        self._spawn_scale    = 0.0
        self._spawn_duration = 1.0
        self._spawning       = True

        # State machine
        self._state          = "resting"
        self._lunge_dir      = pygame.Vector2(0, -1)
        self._vel            = pygame.Vector2(0, 0)
        self._cooldown       = 1.5
        self._extend_timer   = 0.0
        self._pre_lunge_timer = 0.0   # 0.9s telegraph before lunge
        self._hardness       = 1.0
        self._wriggle_t      = random.uniform(0, math.pi * 2)
        self._move_angle     = random.uniform(0, 360)

        # Play spawn sound
        if _audio_enabled and _snd_enter:
            _snd_enter.play()

        # Free mode trail
        max_hist       = (len(self.segments) + 4) * 4 + 20
        self._trail    = deque(
            [(float(self.position.x), float(self.position.y))] * max_hist,
            maxlen=max_hist)
        self._free_vel = pygame.Vector2(1, 0).rotate(random.uniform(0, 360)).normalize() * FREE_SPEED

    # ── Angle helpers ────────────────────────────────────────────────────
    def _face(self, dx, dy):
        if dx*dx + dy*dy > 0:
            self.angle = math.degrees(math.atan2(-dy, dx)) + 90

    def _smooth_face(self, dx, dy, dt, speed=360.0):
        if dx*dx + dy*dy == 0:
            return
        target = math.degrees(math.atan2(-dy, dx)) + 90
        diff   = (target - self.angle + 180) % 360 - 180
        self.angle += min(abs(diff), speed * dt) * (1 if diff >= 0 else -1)

    def _tail_dir(self):
        """Direction from head toward tail, derived from self.angle."""
        rad = math.radians(self.angle - 90)
        return pygame.Vector2(-math.cos(rad), math.sin(rad))

    # ── Chain constraint (FABRIK) ────────────────────────────────────────
    def _apply_chain_constraint(self):
        if not self.wormhole or not self.segments:
            return
        pivot        = self.wormhole.position
        n            = len(self.segments)
        chain_length = n * SEG_SPACING

        for _ in range(3):
            # Backward pass: head pulls segments
            prev = pygame.Vector2(self.position)
            for i in range(n - 1, -1, -1):
                to_seg = self.segments[i].position - prev
                dist   = to_seg.length()
                self.segments[i].position = (
                    prev + to_seg.normalize() * SEG_SPACING if dist > 0
                    else pygame.Vector2(prev.x, prev.y + SEG_SPACING))
                prev = self.segments[i].position

            # Forward pass: pin to post (skipped during lunge/extended)
            if self._state not in ("lunging", "extended"):
                self.segments[0].position = pygame.Vector2(pivot)
                for i in range(1, n):
                    to_seg = self.segments[i].position - self.segments[i-1].position
                    dist   = to_seg.length()
                    self.segments[i].position = (
                        self.segments[i-1].position + to_seg.normalize() * SEG_SPACING if dist > 0
                        else pygame.Vector2(self.segments[i-1].position.x + SEG_SPACING,
                                            self.segments[i-1].position.y))

        # Bounce when head hits chain limit during lunge
        head_dist = self.position.distance_to(pivot)
        if self._state == "lunging" and head_dist >= chain_length:
            from_pivot    = self.position - pivot
            self.position = pivot + from_pivot.normalize() * chain_length
            self._vel     = pygame.Vector2(0, 0)
            self._state   = "extended"
            self._extend_timer = 0.5

        # Retract complete
        if self._state == "retracting" and head_dist < SEG_SPACING * 2:
            self._state    = "resting"
            self._cooldown = random.uniform(1.2, 3.0) / max(1.0, self._hardness)

        # Segment angles — face toward next link
        for i, seg in enumerate(self.segments):
            if not seg.alive:
                continue
            nxt = self.segments[i+1].position if i < n-1 else self.position
            dx  = nxt.x - seg.position.x
            dy  = nxt.y - seg.position.y
            if dx*dx + dy*dy > 0:
                seg.angle = math.degrees(math.atan2(-dy, dx)) + 90

    # ── Free mode snake follow ───────────────────────────────────────────
    def _snake_follow(self):
        self._trail.appendleft((float(self.position.x), float(self.position.y)))
        trail    = list(self._trail)
        n        = len(trail)
        prev_pos = pygame.Vector2(self.position)
        for i, seg in enumerate(self.segments):
            if not seg.alive:
                continue
            target_dist = SEG_SPACING * (i + 1)
            accumulated = 0.0
            placed      = False
            for j in range(n - 1):
                ax, ay = trail[j]
                bx, by = trail[j+1]
                step   = math.hypot(bx-ax, by-ay)
                if accumulated + step >= target_dist:
                    t = (target_dist - accumulated) / step if step > 0 else 0
                    seg.position.x = ax + (bx-ax) * t
                    seg.position.y = ay + (by-ay) * t
                    placed = True
                    break
                accumulated += step
            if not placed:
                seg.position.x = trail[-1][0]
                seg.position.y = trail[-1][1]
            dx = prev_pos.x - seg.position.x
            dy = prev_pos.y - seg.position.y
            if dx*dx + dy*dy > 0:
                seg.angle = math.degrees(math.atan2(-dy, dx)) + 90
            prev_pos = pygame.Vector2(seg.position)

    # ── Anchored movement ────────────────────────────────────────────────
    def _update_anchored(self, dt, player_pos):
        if self._state == "resting":
            to_player = player_pos - self.position
            if self._cooldown > 0:
                self._cooldown -= dt
                self._smooth_face(to_player.x, to_player.y, dt, 120.0 * self._hardness)
            elif not self._spawning:
                if to_player.length() > 0:
                    self._lunge_dir       = to_player.normalize()
                    self._face(self._lunge_dir.x, self._lunge_dir.y)
                    self._pre_lunge_timer = 0.9
                    self._state           = "pre_lunge"
                    if _audio_enabled and _snd_lunge:
                        _snd_lunge.play()

        elif self._state == "pre_lunge":
            # Telegraph — head stays still, timer counts down
            self._pre_lunge_timer -= dt
            self._smooth_face(self._lunge_dir.x, self._lunge_dir.y, dt, 300.0)
            if self._pre_lunge_timer <= 0:
                self._vel   = self._lunge_dir * LUNGE_SPEED * self._hardness
                self._state = "lunging"

        elif self._state == "lunging":
            self.position += self._vel * dt
            self._face(self._vel.x, self._vel.y)

        elif self._state == "extended":
            self._extend_timer -= dt
            if self._extend_timer <= 0:
                from_pivot  = self.position - self.wormhole.position
                self._vel   = -from_pivot.normalize() * RETRACT_SPEED * self._hardness
                self._state = "retracting"

        elif self._state == "retracting":
            self.position += self._vel * dt
            self._smooth_face(self._lunge_dir.x, self._lunge_dir.y, dt, 180.0 * self._hardness)

    # ── Free movement ────────────────────────────────────────────────────
    def _update_free(self, dt):
        self._move_angle += random.uniform(-50, 50) * dt * 4
        rad            = math.radians(self._move_angle)
        self._free_vel = pygame.Vector2(math.cos(rad), math.sin(rad)) * FREE_SPEED
        self.position += self._free_vel * dt
        self._face(self._free_vel.x, self._free_vel.y)
        if self.position.x < HEAD_RADIUS:
            self.position.x  = HEAD_RADIUS
            self._move_angle = random.uniform(-45, 45)
        elif self.position.x > 1280 - HEAD_RADIUS:
            self.position.x  = 1280 - HEAD_RADIUS
            self._move_angle = random.uniform(135, 225)
        if self.position.y < HEAD_RADIUS:
            self.position.y  = HEAD_RADIUS
            self._move_angle = random.uniform(45, 135)
        elif self.position.y > 720 - HEAD_RADIUS:
            self.position.y  = 720 - HEAD_RADIUS
            self._move_angle = random.uniform(225, 315)

    # ── Main update ──────────────────────────────────────────────────────
    def update(self, dt, player_pos=None, hardness=1.0):
        self._hardness   = hardness
        self._wriggle_t += dt * 2.5
        # Grow-in effect
        if self._spawning:
            self._spawn_scale = min(1.0, self._spawn_scale + dt / self._spawn_duration)
            if self._spawn_scale >= 1.0:
                self._spawning = False
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        for seg in self.segments:
            if seg.flash_timer > 0:
                seg.flash_timer = max(0.0, seg.flash_timer - dt)
        if self.anchored and self.wormhole and player_pos:
            self._update_anchored(dt, player_pos)
            self._apply_chain_constraint()
        else:
            self._update_free(dt)
            self._snake_follow()

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self, screen):
        scale = self._spawn_scale if self._spawning else 1.0
        n = len(self.segments)
        pivot = self.wormhole.position if (self.anchored and self.wormhole) else self.position
        for i, seg in enumerate(reversed(self.segments)):
            if not seg.alive:
                continue
            seg_idx  = n - 1 - i
            phase    = self._wriggle_t - seg_idx * 0.15
            rad      = math.radians(seg.angle - 90)
            perp     = pygame.Vector2(-math.sin(rad), math.cos(rad))
            offset   = perp * math.sin(phase) * 5.0
            # Scale position from pivot during spawn
            draw_pos = pivot + (seg.position - pivot) * scale
            seg_size = max(1, int(SEG_SIZE * scale))
            if seg_size != SEG_SIZE:
                surf = pygame.transform.scale(
                    pygame.transform.rotate(_seg_img, seg.angle), (seg_size, seg_size))
            else:
                surf = _get_seg_rotated(seg.angle)
            rect = surf.get_rect(center=(int(draw_pos.x + offset.x * scale),
                                         int(draw_pos.y + offset.y * scale)))
            screen.blit(surf, rect.topleft)
            if seg.flash_timer > 0:
                alpha = int(200 * seg.flash_timer / FLASH_DUR)
                mask  = pygame.mask.from_surface(surf)
                screen.blit(mask.to_surface(setcolor=(255,255,255,alpha),
                                             unsetcolor=(0,0,0,0)), rect.topleft)

        # Head
        head_size = max(1, int(HEAD_SIZE * scale))
        head_pos  = pivot + (self.position - pivot) * scale
        rad_face  = math.radians(self.angle - 90)
        perp      = pygame.Vector2(-math.sin(rad_face), math.cos(rad_face))
        h_offset  = perp * math.sin(self._wriggle_t) * 5.0 * scale
        if head_size != HEAD_SIZE:
            rotated = pygame.transform.scale(
                pygame.transform.rotate(_head_img, self.angle), (head_size, head_size))
        else:
            rotated = pygame.transform.rotate(_head_img, self.angle)
        rect = rotated.get_rect(center=(int(head_pos.x + h_offset.x),
                                         int(head_pos.y + h_offset.y)))
        screen.blit(rotated, rect.topleft)
        if self.flash_timer > 0:
            alpha = int(200 * self.flash_timer / FLASH_DUR)
            mask  = pygame.mask.from_surface(rotated)
            screen.blit(mask.to_surface(setcolor=(255,255,255,alpha),
                                         unsetcolor=(0,0,0,0)), rect.topleft)

    # ── Hitbox ───────────────────────────────────────────────────────────

    def head_triangle(self):
        tail_dir = self._tail_dir()
        side     = pygame.Vector2(-tail_dir.y, tail_dir.x)
        center   = self.position - tail_dir * HEAD_RADIUS * 0.6
        tip      = center + tail_dir * HEAD_RADIUS * 0.6
        left     = center - tail_dir * HEAD_RADIUS * 0.3 + side * (HEAD_RADIUS * 0.5 - 12)
        right    = center - tail_dir * HEAD_RADIUS * 0.3 - side * (HEAD_RADIUS * 0.5 - 12)
        return [tip, left, right]

    def draw_debug(self, screen):
        tail_dir = self._tail_dir()
        side     = pygame.Vector2(-tail_dir.y, tail_dir.x)
        cx, cy   = int(self.position.x), int(self.position.y)
        pygame.draw.line(screen, (0, 100, 255), (cx, cy),
                         (int(cx + tail_dir.x * HEAD_RADIUS), int(cy + tail_dir.y * HEAD_RADIUS)), 3)
        pygame.draw.line(screen, (0, 255, 0), (cx, cy),
                         (int(cx + side.x * HEAD_RADIUS * 0.5), int(cy + side.y * HEAD_RADIUS * 0.5)), 2)
        pygame.draw.polygon(screen, (255, 0, 0),
                            [(int(p.x), int(p.y)) for p in self.head_triangle()], 2)
        for seg in self.segments:
            if seg.alive:
                pygame.draw.circle(screen, (255, 255, 0),
                                   (int(seg.position.x), int(seg.position.y)), SEG_RADIUS, 1)

    # ── Damage ───────────────────────────────────────────────────────────
    def take_damage(self):
        self.health -= 1
        self.flash_timer = FLASH_DUR
        if _audio_enabled and _snd_hit:
            _snd_hit.play()
        if self.health <= 0:
            if _audio_enabled and _snd_defeat:
                _snd_defeat.play()
            for seg in self.segments:
                seg.kill()
            self.segments.clear()
            self.kill()
            return True
        return False

    def damage_segment(self, seg_index, spice_level):
        if _audio_enabled and _snd_split:
            _snd_split.play()
        self.segments[seg_index].kill()
        head_side = self.segments[:seg_index]
        tail_side = self.segments[seg_index+1:]
        saved_wh  = self.wormhole

        self.segments    = head_side
        self.anchored    = False
        self.wormhole    = None
        self._move_angle = random.uniform(0, 360)
        self._face(self._free_vel.x, self._free_vel.y)

        if not tail_side:
            return None

        new_pos  = pygame.Vector2(tail_side[-1].position)
        new_head = TapewormHead(saved_wh, tail_side, spice_level,
                                anchored=(saved_wh is not None), start_pos=new_pos)
        if not saved_wh:
            new_head._move_angle = random.uniform(0, 360)
            new_head._face(new_head._free_vel.x, new_head._free_vel.y)
            trail_pos = [(float(s.position.x), float(s.position.y)) for s in reversed(tail_side)]
            while len(trail_pos) < new_head._trail.maxlen:
                trail_pos.append(trail_pos[-1])
            new_head._trail = deque(trail_pos, maxlen=new_head._trail.maxlen)
        return new_head


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def point_in_triangle(p, t):
    def sign(p1, p2, p3):
        return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)
    p  = pygame.Vector2(p)
    d1 = sign(p, t[0], t[1])
    d2 = sign(p, t[1], t[2])
    d3 = sign(p, t[2], t[0])
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def create_tapeworm(wormhole, spice_level):
    chain_len = CHAIN_LENGTH + spice_level * 8
    n_segs    = chain_len // SEG_SPACING
    x, y      = float(wormhole.position.x), float(wormhole.position.y)
    segments  = [TapewormSegment(x, y) for _ in range(n_segs)]
    return TapewormHead(wormhole, segments, spice_level, anchored=True, start_pos=(x + 1, y))
