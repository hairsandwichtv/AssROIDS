import math
import pygame
from circleshape import CircleShape, SpriteHitbox
from shot import Shot
from asset_helper import asset_path
from constants import (PLAYER_RADIUS, PLAYER_TURN_SPEED, PLAYER_SPEED,
                       PLAYER_SHOT_SPEED, PLAYER_SHOT_COOLDOWN_SECONDS)

SHIP_IMG   = pygame.image.load(asset_path("ship.png"))
SHIELD_IMG = pygame.image.load(asset_path("ship_w_shield.png"))

MILK_BEAM_DURATION   = 15.0
INVINCIBLE_DURATION  = 1.5
THRUSTER_DURATION    = 1.0
THRUSTER_RECHARGE    = 60.0
DP_DURATION          = 15.0  # seconds double-shot lasts
# Hard mode — inertia. Inputs thrust instead of moving the ship directly.
INERTIA_ACCEL       = 400.0  # px/s² along the nose (x2 while boosting) — top speed in ~0.5s
INERTIA_BRAKE       = 400.0  # px/s² the brake sheds — same as thrust
INERTIA_COAST_HALF  = 3.0    # coasting with no input loses half its speed every this many seconds

# Endowments — picked at The Inflation Station, kept for the whole run
ENDOWMENT_MAX_LEVEL = 10
RUNS_SPEED_STEP     = 0.10   # The Runs: +10% move speed per level
HAIR_TRIGGER_STEP   = 0.90   # Hair Trigger: shot cooldown x0.9 per level (~+11% fire rate)
HAIR_TRIGGER_MIN_CD = 0.10   # never faster than 10 shots/s
BASE_MAX_SHIELDS    = 2      # Layer Up: +1 condom slot per level
AUTO_FIRE_DELAY     = 0.25   # hold fire this long before continuous fire kicks in; taps = 1 shot each
BRAKE_AURA_COLOR    = (255, 45, 35)   # soft blurred halo behind the ship while braking
BRAKE_AURA_PAD      = 12              # how far the aura spreads past the ship (px)
BRAKE_AURA_PULSE    = 14.0            # pulse speed (rad/s)

_brake_auras = {}   # id(ship image) → pre-blurred aura, rotated per frame


class Player(SpriteHitbox, CircleShape):
    hit_shrink = 2   # ship mask eroded 2px — grazes on the outline don't count

    shoot_key = pygame.K_SPACE  # rebindable from settings menu
    brake_key = pygame.K_LALT   # rebindable from settings menu

    def __init__(self, x, y, hard_mode=False):
        super().__init__(x, y, PLAYER_RADIUS)
        self.hard_mode = hard_mode   # inertia on: thrust/coast/brake instead of direct movement
        self._thrust   = 0.0         # hard mode: this frame's signed thrust input (in dt units)
        self.rotation = 0
        self.timer    = 0
        size = int(self.radius * 2)
        self.original_image = pygame.transform.scale(SHIP_IMG,   (size, size)).convert_alpha()
        self.shield_image   = pygame.transform.scale(SHIELD_IMG, (size, size)).convert_alpha()

        # --- Power-up states ---
        self.shield_count     = 0   # 0=none, 1=condom, 2=double wrapped, 3+ with Layer Up
        self.invincible_timer = 0.0

        self.milk_beam_active = False
        self.milk_beam_timer  = 0.0
        self.is_firing_beam   = False

        # --- Thruster state ---
        self.thruster_charge  = 1.0
        self.thruster_active  = False
        self.thruster_timer   = 0.0
        self.thruster_locked  = False

        # --- DP state ---
        self.dp_active = False
        self.dp_timer  = 0.0
        self.is_moving = False

        # --- Brake (input only for now; future mechanics read is_braking) ---
        self.is_braking = False

        # --- Endowments (levels) ---
        self.runs_level         = 0
        self.hair_trigger_level = 0
        self.layer_up_level     = 0

    # ------------------------------------------------------------------
    # Power-up helpers
    # ------------------------------------------------------------------
    @property
    def has_shield(self):
        return self.shield_count > 0

    @property
    def max_shields(self):
        return BASE_MAX_SHIELDS + self.layer_up_level

    @property
    def shot_cooldown(self):
        return max(HAIR_TRIGGER_MIN_CD,
                   PLAYER_SHOT_COOLDOWN_SECONDS * HAIR_TRIGGER_STEP ** self.hair_trigger_level)

    @property
    def hair_trigger_scale(self):
        """Hair Trigger's time multiplier — shot cooldown and Milk Beam ticks both use it."""
        return self.shot_cooldown / PLAYER_SHOT_COOLDOWN_SECONDS

    @property
    def move_speed(self):
        return PLAYER_SPEED * (1.0 + RUNS_SPEED_STEP * self.runs_level)

    def activate_shield(self):
        if self.shield_count < self.max_shields:
            self.shield_count += 1

    def consume_shield(self):
        """Decrement shield count; always start invincibility window after a hit."""
        self.shield_count     = max(0, self.shield_count - 1)
        self.invincible_timer = INVINCIBLE_DURATION

    def is_invincible(self):
        # Only the post-hit grace window counts as invincible.
        # has_shield is NOT included here — shielded players still receive
        # collision events so consume_shield() can be called to absorb the hit.
        return self.invincible_timer > 0

    def activate_milk_beam(self):
        self.milk_beam_active = True
        self.milk_beam_timer  = MILK_BEAM_DURATION

    def activate_dp(self):
        """DP can — instant thruster refill + double shot for DP_DURATION seconds."""
        self.dp_active        = True
        self.dp_timer         = DP_DURATION
        self.thruster_charge  = 1.0
        self.thruster_locked  = False

    # ------------------------------------------------------------------
    # Sprite interface
    # ------------------------------------------------------------------
    @property
    def hit_key(self):
        return ("player", self.has_shield)

    def _hit_image(self):
        return self.shield_image if self.has_shield else self.original_image

    def _hit_angle(self):
        return -self.rotation   # draw() rotates by -rotation

    def draw(self, screen):
        # Flash every 80ms during post-hit invincibility window
        if self.invincible_timer > 0:
            if (pygame.time.get_ticks() // 80) % 2 == 0:
                return  # skip drawing this frame = flash effect
        img = self.shield_image if self.has_shield else self.original_image
        rotated  = pygame.transform.rotate(img, -self.rotation)
        new_rect = rotated.get_rect(center=(self.position.x, self.position.y))
        if self.is_braking:
            self._draw_brake_aura(screen, img)
        screen.blit(rotated, new_rect.topleft)

    def _draw_brake_aura(self, screen, img):
        """Soft red glow hugging the ship's silhouette, gently pulsing."""
        aura = _brake_auras.get(id(img))
        if aura is None:
            aura = _brake_auras[id(img)] = self._build_brake_aura(img)
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 1000 * BRAKE_AURA_PULSE)
        glow  = pygame.transform.rotate(aura, -self.rotation)
        glow.set_alpha(int(170 + 85 * pulse))
        screen.blit(glow, glow.get_rect(center=(self.position.x, self.position.y)))

    @staticmethod
    def _build_brake_aura(img):
        """Red silhouette, blurred by repeated down/up-scaling into a halo."""
        pad = BRAKE_AURA_PAD
        w, h = img.get_width() + pad * 2, img.get_height() + pad * 2
        sil = pygame.mask.from_surface(img).to_surface(
            setcolor=(*BRAKE_AURA_COLOR, 255), unsetcolor=(0, 0, 0, 0))
        aura = pygame.Surface((w, h), pygame.SRCALPHA)
        # Slightly swollen silhouette so the glow reaches out past the hull
        sw = pad // 3   # swell scales with the spread so the blur never clips at the edge
        d  = round(sw * 0.8)
        for ox, oy in ((-sw, 0), (sw, 0), (0, -sw), (0, sw), (-d, -d), (d, d), (-d, d), (d, -d), (0, 0)):
            aura.blit(sil, (pad + ox, pad + oy))
        for factor in (6, 4):
            small = pygame.transform.smoothscale(aura, (max(1, w // factor), max(1, h // factor)))
            aura  = pygame.transform.smoothscale(small, (w, h))
        return aura

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def move(self, dt, boost=False):
        if self.is_braking:
            return  # brake cancels all forward/backward movement; rotation still works
        if self.hard_mode:
            self._thrust += dt   # turned into acceleration by _apply_inertia
            return
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        speed   = self.move_speed * (2.0 if boost else 1.0)
        self.position += forward * speed * dt

    def shoot(self):
        if self.timer > 0:
            return False
        self.timer   = self.shot_cooldown
        forward      = pygame.Vector2(0, 1).rotate(self.rotation)
        velocity     = forward * PLAYER_SHOT_SPEED

        if self.dp_active:
            # Two shots offset left and right, tip of triangle sits between them
            right  = pygame.Vector2(0, 1).rotate(self.rotation + 90) * (self.radius * 0.45)
            shot_l = Shot(self.position.x - right.x, self.position.y - right.y)
            shot_r = Shot(self.position.x + right.x, self.position.y + right.y)
            shot_l.velocity = velocity
            shot_r.velocity = velocity
        else:
            new_shot = Shot(self.position.x, self.position.y)
            new_shot.velocity = velocity
        return True

    def update(self, dt, speed_multiplier=1.0,
               ctrl_angle=None, ctrl_magnitude=0.0, ctrl_throttle=0.0,
               ctrl_x_held=False, ctrl_dpad_fwd=False, ctrl_dpad_back=False,
               ctrl_dpad_left=False, ctrl_dpad_right=False,
               ctrl_l3=False, ctrl_boost=False, ctrl_shoot=False, ctrl_brake=False,
               ctrl_speed=0.0, ctrl_config=0):

        # --- Timers ---
        if self.timer          > 0: self.timer          -= dt
        if self.invincible_timer > 0: self.invincible_timer -= dt

        if self.milk_beam_active:
            self.milk_beam_timer -= dt
            if self.milk_beam_timer <= 0:
                self.milk_beam_active = False
                self.milk_beam_timer  = 0.0

        if self.dp_active:
            self.dp_timer -= dt
            if self.dp_timer <= 0:
                self.dp_active = False
                self.dp_timer  = 0.0

        # --- Input state ---
        keys = pygame.key.get_pressed()
        self.is_firing_beam = self.milk_beam_active and (keys[Player.shoot_key] or ctrl_shoot)
        self.is_braking     = keys[Player.brake_key] or ctrl_brake

        # Boost — keyboard Shift or L3 (L3 excluded on config 3, where it's
        # the steering stick; R3 handled in main)
        # Braking blocks boost so thruster charge isn't burned while stopped.
        boost_held = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
                      or ctrl_boost
                      or (ctrl_l3 and ctrl_config != 3)) and not self.is_braking

        # --- Thruster ---
        if self.thruster_active:
            if not self.dp_active:
                self.thruster_charge = max(0.0, self.thruster_charge - dt / THRUSTER_DURATION)
            self.thruster_timer += dt
            if not boost_held or self.thruster_charge <= 0.0:
                self.thruster_active = False
                self.thruster_timer  = 0.0
                if self.thruster_charge <= 0.0:
                    self.thruster_locked = True
        else:
            if self.thruster_charge < 1.0:
                self.thruster_charge = min(1.0, self.thruster_charge + dt * speed_multiplier / THRUSTER_RECHARGE)
            if self.thruster_charge >= 1.0:
                self.thruster_locked = False
            if boost_held and self.thruster_charge > 0.0 and not self.thruster_locked:
                self.thruster_active = True
                self.thruster_timer  = 0.0

        boosting = self.thruster_active

        # --- Movement ---
        self.is_moving = False
        self._thrust   = 0.0

        # Keyboard + D-pad rotation and thrust
        if keys[pygame.K_a] or ctrl_dpad_left:  self.rotate(-dt)
        if keys[pygame.K_d] or ctrl_dpad_right: self.rotate(dt)
        if keys[pygame.K_w] or ctrl_dpad_fwd:
            self.move(dt, boost=boosting)
            self.is_moving = True
        if keys[pygame.K_s] or ctrl_dpad_back:
            self.move(-dt, boost=boosting)
            self.is_moving = True

        # Stick rotation (all configs)
        if ctrl_angle is not None:
            diff = (ctrl_angle - self.rotation + 180) % 360 - 180
            self.rotation += min(abs(diff), 720.0 * dt) * (1 if diff >= 0 else -1)

        # --- Controller config movement ---
        reverse = ctrl_x_held or ctrl_throttle > 0.05

        if ctrl_config == 0:
            # Push Accelerate: outer ring = thrust, LT or X = reverse
            if reverse:
                self.move(-(ctrl_throttle if ctrl_throttle > 0.05 else 1.0) * dt, boost=boosting)
                self.is_moving = True
            elif (ctrl_magnitude > 0 or boosting) and not self.is_moving:
                self.move(dt, boost=boosting)
                self.is_moving = True

        elif ctrl_config == 2:
            # Trigger Accelerate: LT = forward, X = reverse, L3/LB = boost
            if (ctrl_throttle > 0.05 or boosting) and not self.is_moving:
                direction = -1 if ctrl_x_held else 1
                self.move(direction * dt, boost=boosting)
                self.is_moving = True

        elif ctrl_config in (3, 4):
            # Twin Stick / Twin Stick (Reverse): speed stick up = forward, down = reverse,
            # analog speed; ship only moves along its nose (no strafing)
            if not self.is_moving and (ctrl_speed != 0 or boosting):
                self.move((ctrl_speed if ctrl_speed != 0 else 1.0) * dt, boost=boosting)
                self.is_moving = True

        if self.is_braking:
            self.is_moving = False   # no exhaust trail while held still

        if self.hard_mode:
            self._apply_inertia(dt, boosting)

        # --- Screen clamping ---
        clamped_x = max(self.radius, min(self.position.x, 1280 - self.radius))
        clamped_y = max(self.radius, min(self.position.y, 720  - self.radius))
        if clamped_x != self.position.x: self.velocity.x = 0   # slide along walls, don't stick
        if clamped_y != self.position.y: self.velocity.y = 0
        self.position.x, self.position.y = clamped_x, clamped_y

    def _apply_inertia(self, dt, boosting):
        """Hard mode: thrust accelerates, brake decelerates, otherwise coast with light drag."""
        if dt <= 0:
            return
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        thrust  = max(-1.0, min(1.0, self._thrust / dt))   # analog sticks give partial thrust
        cap     = self.move_speed * (2.0 if boosting else 1.0)
        speed   = self.velocity.length()
        if self.is_braking:
            if speed > 0:
                self.velocity *= max(0.0, speed - INERTIA_BRAKE * dt) / speed
        elif thrust:
            self.velocity += forward * thrust * INERTIA_ACCEL * (2.0 if boosting else 1.0) * dt
        else:
            self.velocity *= 0.5 ** (dt / INERTIA_COAST_HALF)
        # Over the cap (thrusting, or boost just ended) — ease back down at brake rate
        speed = self.velocity.length()
        if speed > cap:
            self.velocity *= max(cap, speed - INERTIA_BRAKE * dt) / speed
        self.position += self.velocity * dt
