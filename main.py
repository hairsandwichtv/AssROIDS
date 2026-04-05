import pygame
import sys
import os
import json
import subprocess
import math
import random

from starfield import Starfield
from nebula import Nebula
from particles import ParticleManager
from constants import *
from asset_helper import asset_path, writable_path
from player import Player
from asteroid import Asteroid
from asteroidfield import AsteroidField
from shot import Shot
from button import Button
from boss import Boss
from enemy_ship import MandingoShip, MandingoShot, VulvaShip, GoldenSuppository
from tapeworm import WormHole, TapewormHead, TapewormSegment, create_tapeworm, WORMHOLE_VISUAL_R, WORMHOLE_SPAWN_PCT, SEG_RADIUS, point_in_triangle, set_audio_enabled
import tapeworm as _tapeworm_module
from powerup import PowerUp
from circleshape import DEBUG_HITBOXES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
POWERUP_SPAWN_BASE   = 20.0
BEAM_DAMAGE_INTERVAL = 0.3
BEAM_LENGTH          = 650
_GALAXY_END_SIZE     = int(math.hypot(1280, 720) * 2)  # pre-computed diagonal

class _FakeCircle:
    """Lightweight stand-in for beam_hits_circle checks against non-sprite objects."""
    __slots__ = ('position', 'radius')
    def __init__(self, pos, r):
        self.position = pos
        self.radius   = r

HIGHSCORE_FILE = writable_path("highscore.txt")
SETTINGS_FILE  = writable_path("settings.json")

# ---------------------------------------------------------------------------
# High score
# ---------------------------------------------------------------------------
def load_high_score():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

def save_high_score(score):
    with open(HIGHSCORE_FILE, "w") as f:
        f.write(str(score))

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "master_volume":  1.0,
    "mute_menu_song": False,
    "shoot_key":      pygame.K_SPACE,
}

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                data.setdefault(k, v)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def apply_settings(settings, audio_enabled, all_sounds, in_game=False):
    if not audio_enabled:
        return
    vol = settings["master_volume"]
    for snd in all_sounds:
        if snd:
            snd.set_volume(vol)
    if in_game:
        pygame.mixer.music.set_volume(0.45 * vol)
    else:
        if settings["mute_menu_song"]:
            pygame.mixer.music.set_volume(0)
        else:
            pygame.mixer.music.set_volume(0.66 * vol)
    Player.shoot_key = settings["shoot_key"]

# ---------------------------------------------------------------------------
# README opener
# ---------------------------------------------------------------------------
def open_readme():
    """Open README_GAME.md in the system default app."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(".")
    path = os.path.join(base, "README_GAME.md")
    try:
        os.startfile(path)                          # native Windows
    except AttributeError:
        try:                                        # WSL fallback
            win_path = subprocess.check_output(["wslpath", "-w", path]).decode().strip()
            powershell = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
            subprocess.Popen([powershell, "-Command", f'Invoke-Item "{win_path}"'])
        except Exception:
            pass
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Draw helpers
# ---------------------------------------------------------------------------
def draw_boss_sauce(surface, x, y, width, height, current_butts, font):
    progress_pct = min(int((current_butts / 50) * 100), 100)
    pygame.draw.rect(surface, (50, 50, 50),  (x, y, width, height))
    fill_width = int(width * (progress_pct / 100))
    pygame.draw.rect(surface, (0, 255, 100), (x, y, fill_width, height))
    pygame.draw.rect(surface, "white",       (x, y, width, height), 2)
    label = font.render(f"BOSS SAUCE: {progress_pct}%", True, "white")
    surface.blit(label, (x, y - 25))

def beam_hits_circle(player, target):
    forward = pygame.Vector2(0, 1).rotate(player.rotation)
    right   = pygame.Vector2(0, 1).rotate(player.rotation + 90) * (player.radius * 0.45)
    origins = ([pygame.Vector2(player.position) - right,
                pygame.Vector2(player.position) + right]
               if player.dp_active
               else [pygame.Vector2(player.position)])
    to_target = target.position - player.position
    proj      = to_target.dot(forward)
    if proj < 0 or proj > BEAM_LENGTH:
        return False
    for origin in origins:
        to_t      = target.position - origin
        perp_dist = (to_t - forward * proj).length()
        if perp_dist <= target.radius + 5:
            return True
    return False

def draw_milk_beam(surface, player):
    forward = pygame.Vector2(0, 1).rotate(player.rotation)
    right   = pygame.Vector2(0, 1).rotate(player.rotation + 90) * (player.radius * 0.45)
    origins = ([pygame.Vector2(player.position) - right,
                pygame.Vector2(player.position) + right]
               if player.dp_active
               else [pygame.Vector2(player.position)])
    for origin in origins:
        start = origin + forward * (player.radius + 4)
        for _ in range(30):
            t      = random.uniform(0, BEAM_LENGTH)
            jitter = pygame.Vector2(random.randint(-6, 6), random.randint(-6, 6))
            pos    = start + forward * t + jitter
            fade   = max(0.15, 1.0 - t / BEAM_LENGTH)
            size   = max(1, int(random.randint(2, 5) * fade))
            white  = int(210 + 45 * fade)
            color  = (white, white, 255)
            if 0 <= pos.x <= 1280 and 0 <= pos.y <= 720:
                pygame.draw.circle(surface, color, (int(pos.x), int(pos.y)), size)

_SETTINGS_OVERLAY = None

def draw_settings_menu(surface, settings, font, small_font, waiting_for_key):
    global _SETTINGS_OVERLAY
    if _SETTINGS_OVERLAY is None:
        _SETTINGS_OVERLAY = pygame.Surface((1280, 720), pygame.SRCALPHA)
        _SETTINGS_OVERLAY.fill((0, 0, 0, 180))
    surface.blit(_SETTINGS_OVERLAY, (0, 0))
    panel_rect = pygame.Rect(340, 140, 600, 420)
    pygame.draw.rect(surface, (30, 30, 40),    panel_rect, border_radius=12)
    pygame.draw.rect(surface, (255, 255, 255), panel_rect, 2, border_radius=12)
    title = font.render("SETTINGS", True, (255, 215, 0))
    surface.blit(title, (640 - title.get_width() // 2, 160))
    # Volume slider
    vol_label = small_font.render("MASTER VOLUME", True, "white")
    surface.blit(vol_label, (380, 230))
    slider_bg     = pygame.Rect(380, 260, 520, 16)
    slider_fill   = pygame.Rect(380, 260, int(520 * settings["master_volume"]), 16)
    slider_knob_x = 380 + int(520 * settings["master_volume"])
    pygame.draw.rect(surface, (80, 80, 80),  slider_bg,   border_radius=8)
    pygame.draw.rect(surface, (0, 200, 100), slider_fill, border_radius=8)
    pygame.draw.circle(surface, "white", (slider_knob_x, 268), 10)
    pct_txt = small_font.render(f"{int(settings['master_volume'] * 100)}%", True, "white")
    surface.blit(pct_txt, (910, 255))
    # Mute checkbox
    mute_label = small_font.render("MUTE MENU SONG", True, "white")
    surface.blit(mute_label, (380, 320))
    box_rect = pygame.Rect(820, 318, 22, 22)
    pygame.draw.rect(surface, "white", box_rect, border_radius=3)
    if settings["mute_menu_song"]:
        pygame.draw.rect(surface, (0, 200, 100), box_rect.inflate(-6, -6), border_radius=2)
    # Keybind
    bind_label = small_font.render("SHOOT KEY", True, "white")
    surface.blit(bind_label, (380, 390))
    key_name   = pygame.key.name(settings["shoot_key"]).upper()
    bind_text  = "[ PRESS ANY KEY ]" if waiting_for_key else f"[ {key_name} ]"
    bind_color = (255, 215, 0) if waiting_for_key else (100, 200, 255)
    bind_surf  = small_font.render(bind_text, True, bind_color)
    bind_rect  = bind_surf.get_rect(topleft=(680, 390))
    surface.blit(bind_surf, bind_rect.topleft)
    # ESC hint
    esc_txt = small_font.render("ESC  —  Close Settings", True, (150, 150, 150))
    surface.blit(esc_txt, (640 - esc_txt.get_width() // 2, 510))
    return slider_bg, box_rect, bind_rect

_THRUSTERS_LABEL = None  # cached once after fonts are created

def draw_thruster_bar(surface, x, y, width, height, charge, active, locked, font, tick):
    """Draw thruster bar with label inside, red->blue color shift, flash red when empty."""
    global _THRUSTERS_LABEL
    if locked:
        flash_on  = (tick // 18) % 2 == 0
        bar_color = (220, 0, 0) if flash_on else (100, 0, 0)
    elif active:
        bar_color = (0, 220, 255)
    else:
        r = int(255 * (1.0 - charge))
        b = int(220 * charge)
        bar_color = (r, 0, b)

    pygame.draw.rect(surface, (20, 30, 50), (x, y, width, height), border_radius=4)
    fill_w = max(0, int(width * charge))
    if fill_w > 0:
        pygame.draw.rect(surface, bar_color, (x, y, fill_w, height), border_radius=4)
    highlight = (min(bar_color[0]+80,255), min(bar_color[1]+80,255), min(bar_color[2]+80,255))
    pygame.draw.rect(surface, highlight, (x, y, width, height // 4), border_radius=4)
    pygame.draw.rect(surface, (60, 120, 200), (x, y, width, height), 2, border_radius=4)
    if _THRUSTERS_LABEL is None:
        _THRUSTERS_LABEL = font.render("THRUSTERS", True, "white")
    surface.blit(_THRUSTERS_LABEL,
                 (x + width // 2 - _THRUSTERS_LABEL.get_width() // 2,
                  y + height // 2 - _THRUSTERS_LABEL.get_height() // 2))

def player_death(score, high_score, audio_enabled, death_sound, death_sfx_length):
    """Trigger player death — play SFX, save score, stop other audio.
    Returns (high_score, death_freeze_timer) — caller sets state to DYING."""
    if score > high_score:
        high_score = score
        save_high_score(high_score)
    if audio_enabled:
        pygame.mixer.stop()
        pygame.mixer.music.stop()
        death_sound.play()
    return high_score, death_sfx_length

def maybe_spawn_suppository(asteroid, suppositories, hardness):
    """1% chance to spawn a Golden Suppository when a small butt is destroyed."""
    if (asteroid.is_butt and
            asteroid.visual_radius <= ASTEROID_MIN_RADIUS * 2 and
            random.random() < 0.01):
        speed    = 400.0 * hardness
        velocity = pygame.Vector2(speed, 0).rotate(random.uniform(0, 360))
        GoldenSuppository(asteroid.position.x, asteroid.position.y, velocity)


def boss_death_clear(asteroids, score, audio_enabled, poop_splat_sound,
                     boss_death_sound, shake_timer, SHAKE_DURATION,
                     wormholes=None, spice_level=0, boss_pos=None):
    """Shared logic for when any boss dies — clear field, boost speed, return updated score and shake_timer."""
    if audio_enabled: boss_death_sound.play()
    shake_timer = SHAKE_DURATION
    AsteroidField.speed_multiplier      *= 1.15
    AsteroidField.spawn_rate_multiplier *= 1.15
    wormhole_spawned = wormholes is not None and len(wormholes) > 0
    for asteroid in list(asteroids):
        if asteroid.radius <= ASTEROID_MIN_RADIUS:
            score += 1
            asteroid.kill()
        else:
            asteroid.split()
    for asteroid in asteroids:
        asteroid.velocity *= 1.15
    # 50% chance to spawn wormhole on boss death if none on screen
    if not wormhole_spawned and wormholes is not None and random.random() < 0.50:
        wx = boss_pos.x if boss_pos else 640
        wy = boss_pos.y if boss_pos else 360
        # Clamp to screen
        wx = max(80, min(1200, wx))
        wy = max(80, min(640, wy))
        WormHole(wx, wy)
    return score, shake_timer

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.display.set_caption("AssROIDS")

    try:
        pygame.mixer.init()
        audio_enabled = True
        set_audio_enabled(True)
    except pygame.error:
        audio_enabled = False

    screen        = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    internal_res  = (1280, 720)
    internal_surf = pygame.Surface(internal_res)
    font          = pygame.font.SysFont("Arial", 24, bold=True)
    small_font    = pygame.font.SysFont("Arial", 18, bold=True)
    stats_rip_font   = pygame.font.SysFont("Arial", 52, bold=True)
    stats_title_font = pygame.font.SysFont("Arial", 30, bold=True)
    stats_line_font  = pygame.font.SysFont("Arial", 22)
    clock         = pygame.time.Clock()
    dt            = 0

    menu_bg_original = pygame.image.load(asset_path("AssROIDS Menu BG.png")).convert()
    menu_bg          = pygame.transform.scale(menu_bg_original, internal_res)
    shield_icon      = pygame.transform.rotate(
        pygame.transform.scale(
            pygame.image.load(asset_path("shield.png")).convert_alpha(), (20, 20)), 180)


    if audio_enabled:
        croak_channel   = None
        lullaby_channel = None
        lullaby_sound   = None
        rainbow_tune    = None
        credits_tune    = None
        am_jam_sounds     = []
        space_amb_sound   = None
        space_amb_channel = None
        am_jam_paused   = False   # True while tapeworm is alive
        am_jam_waiting  = False   # True while waiting for rainbow tune to finish
        croak_playing   = False
        lullaby_playing = False
        try:
            pygame.mixer.set_num_channels(16)
            croak_channel     = pygame.mixer.Channel(15)
            lullaby_channel   = pygame.mixer.Channel(14)
            space_amb_channel = pygame.mixer.Channel(12)
            am_jam_sounds = [asset_path(f"Am Jam {_i}.mp3") for _i in range(1, 10)
                             if os.path.exists(asset_path(f"Am Jam {_i}.mp3"))]

            # --- Splash screen while long sounds load ---
            splash_font = pygame.font.SysFont("Arial", 36, bold=True)
            splash_small = pygame.font.SysFont("Arial", 20)
            splash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            splash_surf.fill((0, 0, 0))
            title = splash_font.render("AssROIDS", True, (255, 255, 255))
            loading = splash_small.render("Loading...", True, (180, 180, 180))
            splash_surf.blit(title,   title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60)))
            splash_surf.blit(loading, loading.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 10)))

            disclaimer_lines = [
                "AssROIDS is a passion project developed by HairSandwichTV as they learned to Code,",
                "Algorithms and Data Structures, Systems Architecture, and Networking.",
                "It is designed as a free-to-play parody project for entertainment purposes only.",
                "It is not intended to be viewed as homo-erotica, or as an insult to any unnamed communities.",
                "Please enjoy at your own discretion.  Glurp!",
            ]
            disc_font = pygame.font.SysFont("Arial", 14)
            for i, line in enumerate(disclaimer_lines):
                surf = disc_font.render(line, True, (120, 120, 120))
                splash_surf.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 40 + i * 20)))

            screen.blit(splash_surf, (0, 0))
            pygame.display.flip()

            # Pre-load tapeworm images and pre-populate all 360 segment rotations
            # so there's no hitch when the first tapeworm spawns mid-game
            _tapeworm_module._load_images()
            for _deg in range(360):
                _tapeworm_module._get_seg_rotated(_deg)

            # Now load the long sounds — splash is visible during this delay
            lullaby_sound   = pygame.mixer.Sound(asset_path("Razor Lullaby.mp3"))
            lullaby_sound.set_volume(0.6)
            space_amb_sound = pygame.mixer.Sound(asset_path("Space Amb.mp3"))
            space_amb_sound.set_volume(0.5)
            rainbow_tune    = pygame.mixer.Sound(asset_path("Rainbow Hole Tune.mp3"))
            rainbow_tune.set_volume(0.8)
            credits_tune    = pygame.mixer.Sound(asset_path("Credits Tune.mp3"))
            credits_tune.set_volume(0.2)
        except Exception:
            pass
        pygame.mixer.music.load(asset_path("Ass Roids Menu Song.mp3"))
        _pre_settings = load_settings()
        _vol = _pre_settings.get("master_volume", 1.0)
        if not _pre_settings.get("mute_menu_song", False):
            pygame.mixer.music.set_volume(0.66 * _vol)
            pygame.mixer.music.play(-1)
        tick_sound       = pygame.mixer.Sound(asset_path("Button Tick.mp3"))
        blast_off_sound  = pygame.mixer.Sound(asset_path("Blast Off SFX.mp3"))
        gun_sound        = pygame.mixer.Sound(asset_path("Main Gun Sound.mp3"))
        poop_splat_sound = pygame.mixer.Sound(asset_path("Poop Splat.mp3"))
        butt_smack_sound = pygame.mixer.Sound(asset_path("Butt Smack.mp3"))
        boss_enter_sound      = pygame.mixer.Sound(asset_path("Boss Enter Cluck.mp3"))
        titvag_enter_sound    = pygame.mixer.Sound(asset_path("Tit Vag Boss SFX.mp3"))
        coinpurse_enter_sound = pygame.mixer.Sound(asset_path("Coin Purse Boss SFX.mp3"))
        boss_death_sound = pygame.mixer.Sound(asset_path("Boss Death FX.mp3"))
        swoosh_sound     = pygame.mixer.Sound(asset_path("Swoosh.mp3"))
        rubber_pop_sound = pygame.mixer.Sound(asset_path("Rubber Pop.mp3"))
        gulp_sound       = pygame.mixer.Sound(asset_path("Gulp.mp3"))
        milk_beam_sound  = pygame.mixer.Sound(asset_path("Milk Beam SFX long.mp3"))
        dick_sus_sound   = pygame.mixer.Sound(asset_path("Dick Butt Sus SFX.mp3"))
        thruster_sound   = pygame.mixer.Sound(asset_path("Thrusters SFX.mp3"))
        death_sound           = pygame.mixer.Sound(asset_path("Player Death SFX.mp3"))
        death_sfx_length      = death_sound.get_length()
        mandingo_enter_sound  = pygame.mixer.Sound(asset_path("Mandingo Enter SFX.mp3"))
        mandingo_engine_sound = pygame.mixer.Sound(asset_path("Mandingo Engine SFX.mp3"))
        mandingo_charge_sound = pygame.mixer.Sound(asset_path("Mandingo Beam Charge SFX.mp3"))
        explosion_sfx         = pygame.mixer.Sound(asset_path("Explosion - SFX.mp3"))
        vulva_enter_sound     = pygame.mixer.Sound(asset_path("Vulva Enter SFX.mp3"))
        vulva_engine_sound    = pygame.mixer.Sound(asset_path("Vulva Engine SFX.mp3"))
    else:
        (tick_sound, blast_off_sound, gun_sound, poop_splat_sound,
         butt_smack_sound, boss_enter_sound, boss_death_sound,
         swoosh_sound, rubber_pop_sound, gulp_sound,
         milk_beam_sound, dick_sus_sound, thruster_sound, death_sound,
         titvag_enter_sound, coinpurse_enter_sound,
         mandingo_enter_sound, mandingo_engine_sound, mandingo_charge_sound, explosion_sfx,
         vulva_enter_sound, vulva_engine_sound) = (None,) * 22
        death_sfx_length = 0.0

    all_sounds_list = [
        tick_sound, blast_off_sound, gun_sound, poop_splat_sound,
        butt_smack_sound, boss_enter_sound, boss_death_sound,
        swoosh_sound, rubber_pop_sound, gulp_sound,
        milk_beam_sound, dick_sus_sound, thruster_sound, death_sound
    ]

    start_btn    = Button(int(1280 * 0.10), 570, asset_path("Blast Off Button.png"), 0.5)
    exit_btn     = Button(int(1280 * 0.90), 570, asset_path("Exit Button.png"),      0.5)
    readme_btn   = Button(133,              150, asset_path("READ ME Button.png"),   0.4)
    settings_btn = Button(int(1280 * 0.90), 150, asset_path("Settings Button.png"),  0.5)
    stars        = Starfield(1280, 720, 200)
    nebula       = Nebula(1280, 720)
    particles    = ParticleManager()

    settings        = load_settings()
    apply_settings(settings, audio_enabled, all_sounds_list, in_game=False)
    settings_open   = False
    waiting_for_key = False

    state             = "MENU"
    score             = 0
    spice_score       = 0
    butts_busted      = 0
    first_shot_fired  = False
    total_shots_fired = 0
    high_score        = load_high_score()

    SHAKE_DURATION  = 0.45
    SHAKE_INTENSITY = 10
    shake_timer     = 0.0

    powerup_spawn_timer   = POWERUP_SPAWN_BASE
    beam_damage_timer     = 0.0
    prev_firing_beam      = False
    prev_milk_beam_active = False
    prev_thruster_active  = False
    sus_playing           = False
    death_freeze_timer    = 0.0
    stat_poops_killed     = 0
    stat_butts_killed     = 0
    stat_bosses_killed    = 0
    stat_shots_fired_raw  = 0
    stats_timer           = 0.0
    _stats_keys_on_open   = set()

    updatable = pygame.sprite.Group()
    drawable  = pygame.sprite.Group()
    standard_updatable = pygame.sprite.Group()  # shots, asteroids, powerups, field only
    asteroids      = pygame.sprite.Group()
    shots          = pygame.sprite.Group()
    bosses         = pygame.sprite.Group()
    powerups       = pygame.sprite.Group()
    mandingos      = pygame.sprite.Group()
    mandingo_shots = pygame.sprite.Group()
    vulvas               = pygame.sprite.Group()
    suppositories        = pygame.sprite.Group()
    wormholes            = pygame.sprite.Group()
    tapeworm_heads       = pygame.sprite.Group()
    galaxy_timer         = 0.0
    GALAXY_DURATION      = 3.5
    WARP_FLASH_DURATION  = 1.0
    warp_flash_timer     = 0.0
    warp_flash_wormhole  = None   # WormHole sprite reference during flash
    vulva_engine_ch      = None
    vulva_engine_playing = False

    # Anti-turtle timer — spawns enemy ship if no boss in 2 minutes (reduced by hardness)
    ANTI_TURTLE_BASE   = 75.0  # seconds before anti-turtle ship spawns
    anti_turtle_timer  = ANTI_TURTLE_BASE
    mandingo_engine_ch = None   # channel for looping engine sound
    mandingo_engine_playing = False

    # HUD render cache — surfaces only rebuilt when values change
    _hud_score   = _hud_spice = _hud_hard = None
    _hud_score_v = _hud_spice_v = _hud_hard_v = None
    _hs_label    = font.render("HIGHEST SCORE", True, (255, 215, 0))
    _hs_value    = None
    _hs_value_v  = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            if settings_open and waiting_for_key and event.type == pygame.KEYDOWN:
                if event.key != pygame.K_ESCAPE:
                    settings["shoot_key"] = event.key
                    Player.shoot_key = event.key
                    save_settings(settings)
                waiting_for_key = False

            if settings_open and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                settings_open = False
                save_settings(settings)

            if settings_open and not waiting_for_key and event.type == pygame.MOUSEBUTTONDOWN:
                win_w, win_h = screen.get_size()
                aspect = 1280 / 720
                if win_w / win_h > aspect:
                    sc = win_h / 720; ox = (win_w - 1280 * sc) / 2; oy = 0
                else:
                    sc = win_w / 1280; ox = 0; oy = (win_h - 720 * sc) / 2
                mx = (pygame.mouse.get_pos()[0] - ox) / sc
                my = (pygame.mouse.get_pos()[1] - oy) / sc
                slider_area = pygame.Rect(380, 250, 520, 36)
                mute_box    = pygame.Rect(820, 318, 22, 22)
                bind_area   = pygame.Rect(680, 383, 250, 34)
                if slider_area.collidepoint(mx, my):
                    settings["master_volume"] = max(0.0, min(1.0, (mx - 380) / 520))
                    apply_settings(settings, audio_enabled, all_sounds_list, in_game=(state == "GAME"))
                    save_settings(settings)
                elif mute_box.collidepoint(mx, my):
                    settings["mute_menu_song"] = not settings["mute_menu_song"]
                    apply_settings(settings, audio_enabled, all_sounds_list, in_game=(state == "GAME"))
                    save_settings(settings)
                elif bind_area.collidepoint(mx, my):
                    waiting_for_key = True

        internal_surf.fill("black")

        # ===================================================================
        # MENU STATE
        # ===================================================================
        if state == "MENU":
            internal_surf.blit(menu_bg, (0, 0))
            if high_score != _hs_value_v:
                _hs_value   = font.render(str(high_score), True, "white")
                _hs_value_v = high_score
            internal_surf.blit(_hs_label, (640 - _hs_label.get_width() // 2, 100))
            internal_surf.blit(_hs_value, (640 - _hs_value.get_width() // 2, 130))

            if start_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                if audio_enabled:
                    blast_off_sound.play()
                    pygame.mixer.music.stop()
                updatable.empty(); drawable.empty(); standard_updatable.empty()
                asteroids.empty(); shots.empty()
                bosses.empty();    powerups.empty()
                score             = 0
                spice_score       = 0
                butts_busted      = 0
                total_shots_fired = 0
                first_shot_fired  = False
                shake_timer       = 0.0
                powerup_spawn_timer   = POWERUP_SPAWN_BASE
                beam_damage_timer     = 0.0
                prev_firing_beam      = False
                prev_milk_beam_active = False
                prev_thruster_active  = False
                sus_playing           = False
                death_freeze_timer    = 0.0
                stat_poops_killed     = 0
                stat_butts_killed     = 0
                stat_bosses_killed    = 0
                stat_shots_fired_raw  = 0
                stats_timer           = 0.0
                AsteroidField.speed_multiplier      = 1.0
                AsteroidField.spawn_rate_multiplier = 1.0
                particles.clear()
                mandingos.empty()
                mandingo_shots.empty()
                vulvas.empty()
                suppositories.empty()
                wormholes.empty()
                tapeworm_heads.empty()
                anti_turtle_timer       = ANTI_TURTLE_BASE
                mandingo_engine_playing = False
                vulva_engine_playing    = False
                if audio_enabled and mandingo_engine_ch:
                    mandingo_engine_ch.stop()
                if audio_enabled and mandingo_charge_sound:
                    mandingo_charge_sound.stop()
                if audio_enabled and vulva_engine_ch:
                    vulva_engine_ch.stop()
                Shot.containers           = (shots,          updatable, drawable, standard_updatable)
                Asteroid.containers       = (asteroids,      updatable, drawable, standard_updatable)
                AsteroidField.containers  = (updatable, standard_updatable)
                Player.containers         = (updatable,      drawable)
                Boss.containers           = (bosses,         updatable, drawable)
                PowerUp.containers        = (powerups,       updatable, drawable, standard_updatable)
                MandingoShip.containers   = (mandingos,      updatable, drawable)
                MandingoShot.containers   = (mandingo_shots, updatable, drawable, standard_updatable)
                VulvaShip.containers      = (vulvas,         updatable, drawable)
                GoldenSuppository.containers = (suppositories, updatable, drawable)
                WormHole.containers          = (wormholes,      updatable, drawable)
                TapewormHead.containers      = (tapeworm_heads, updatable, drawable)
                player        = Player(1280 / 2, 720 / 2)
                asteroid_field = AsteroidField()
                asteroid_field.butt_delay = 15.0  # suppressed until first shot or 15s elapses
                state         = "GAME"
                first_shot_fired = False
                am_jam_paused  = False
                am_jam_waiting = False
                if audio_enabled and am_jam_sounds:
                    _am = random.choice(am_jam_sounds); pygame.mixer.music.load(_am); pygame.mixer.music.set_volume(0.3); pygame.mixer.music.play()
                # Spawn 99 stationary poops, clear of player spawn
                player_spawn = pygame.Vector2(1280 / 2, 720 / 2)
                for _ in range(99):
                    while True:
                        pos = pygame.Vector2(
                            random.randint(60, 1220),
                            random.randint(60, 660)
                        )
                        if pos.distance_to(player_spawn) >= 120:
                            break
                    poop = Asteroid(pos.x, pos.y, ASTEROID_MIN_RADIUS)
                    poop.velocity  = pygame.Vector2(0, 0)
                    poop.spin_rate = random.uniform(-120, 120)  # random rotation
                if audio_enabled:
                    if space_amb_channel and space_amb_sound:
                        space_amb_channel.play(space_amb_sound, loops=-1)
                    apply_settings(settings, audio_enabled, all_sounds_list, in_game=True)

            if readme_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                open_readme()

            if settings_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                settings_open = not settings_open
                waiting_for_key = False

            if exit_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                pygame.quit()
                sys.exit()

            if settings_open:
                draw_settings_menu(internal_surf, settings, font, small_font, waiting_for_key)

        # ===================================================================
        # GAME STATE
        # ===================================================================
        elif state == "GAME":

            keys = pygame.key.get_pressed()
            if keys[Player.shoot_key]:
                if not player.milk_beam_active:
                    if player.shoot():
                        total_shots_fired += 1
                        stat_shots_fired_raw += 1
                        if audio_enabled: gun_sound.play()
                        if not first_shot_fired:
                            first_shot_fired = True
                            asteroid_field.butt_delay = 3.0

            player.update(dt, speed_multiplier=AsteroidField.speed_multiplier)
            stars.update(dt, hardness=AsteroidField.speed_multiplier)
            # Update standard objects (shots, asteroids, powerups, field)
            for obj in standard_updatable:
                obj.update(dt)

            # Bosses need player position for special attacks
            for boss in bosses:
                boss.update(dt, player.position)

            for supp in suppositories:
                supp.update(dt, AsteroidField.speed_multiplier)

            for wh in wormholes:
                wh.update(dt)

            for tw in tapeworm_heads:
                tw.update(dt, player.position, AsteroidField.speed_multiplier)

            # Croaking ambience — loop while any tapeworm alive, stop when none
            if audio_enabled and _tapeworm_module._snd_croak and croak_channel:
                if len(tapeworm_heads) > 0:
                    if not croak_playing:
                        croak_channel.play(_tapeworm_module._snd_croak, loops=-1)
                        croak_playing = True
                elif croak_playing:
                    croak_channel.stop()
                    croak_playing = False

            # Razor Lullaby — loop while any wormhole on screen
            if audio_enabled and lullaby_sound and lullaby_channel:
                if len(wormholes) > 0:
                    if not lullaby_playing:
                        lullaby_channel.play(lullaby_sound, loops=-1)
                        lullaby_playing = True
                elif lullaby_playing:
                    lullaby_channel.stop()
                    lullaby_playing = False

            # Single wormhole pass — spawn, rainbow check, player entry
            any_tw_alive = any(tw.alive() for tw in tapeworm_heads) if wormholes else False
            for wh in list(wormholes):
                if wh.state == "anchoring":
                    if not getattr(wh, '_spawned', False):
                        wh._spawned = True
                        create_tapeworm(wh, max(0, total_shots_fired - spice_score))
                        if audio_enabled:
                            pygame.mixer.music.stop()
                        am_jam_paused = True
                    elif not any_tw_alive:
                        wh.activate_rainbow()
                elif wh.is_enterable() and wh.player_overlaps(player.position, player.radius):
                    state = "WARP_FLASH"
                    warp_flash_timer    = WARP_FLASH_DURATION
                    warp_flash_wormhole = wh
                    if audio_enabled and rainbow_tune:
                        rainbow_tune.play()
                        am_jam_waiting = True
                    break

            # Am Jam management — cycle tracks, handle pause/resume
            if audio_enabled and am_jam_sounds:
                if am_jam_waiting:
                    if rainbow_tune and not rainbow_tune.get_num_channels():
                        am_jam_waiting = False
                        am_jam_paused  = False
                        _am = random.choice(am_jam_sounds)
                        pygame.mixer.music.load(_am)
                        pygame.mixer.music.set_volume(0.3)
                        pygame.mixer.music.play()
                elif not am_jam_paused:
                    if not pygame.mixer.music.get_busy():
                        _am = random.choice(am_jam_sounds)
                        pygame.mixer.music.load(_am)
                        pygame.mixer.music.set_volume(0.3)
                        pygame.mixer.music.play()

            # Mandingo needs player position and shot group — updated separately
            for m in list(mandingos):
                prev_state = m._fire_state
                m.update(dt, player.position, AsteroidField.speed_multiplier,
                         mandingo_shots)
                if audio_enabled and mandingo_charge_sound:
                    if m._fire_state == "charging" and prev_state != "charging":
                        mandingo_charge_sound.stop()
                        mandingo_charge_sound.play()

            # Vulva needs player position — updated separately
            for v in list(vulvas):
                v.update(dt, player.position, AsteroidField.speed_multiplier,
                         asteroids, bosses)

            # Vulva engine sound — play while any vulva is alive
            if vulvas:
                if not vulva_engine_playing:
                    if audio_enabled and vulva_engine_sound:
                        vulva_engine_ch = pygame.mixer.find_channel()
                        if vulva_engine_ch:
                            vulva_engine_ch.play(vulva_engine_sound, loops=-1)
                    vulva_engine_playing = True
            else:
                if vulva_engine_playing:
                    if audio_enabled and vulva_engine_ch:
                        vulva_engine_ch.stop()
                    vulva_engine_playing = False

            # Anti-turtle timer — randomly spawn Mandingo OR Vulva
            anti_turtle_timer -= dt * AsteroidField.speed_multiplier
            if anti_turtle_timer <= 0 and len(mandingos) == 0 and len(vulvas) == 0:
                anti_turtle_timer = ANTI_TURTLE_BASE
                spice_level       = max(0, total_shots_fired - spice_score)
                edge = random.randint(0, 3)
                if edge == 0:   ex, ey = random.randint(100, 1180), -120
                elif edge == 1: ex, ey = random.randint(100, 1180), 840
                elif edge == 2: ex, ey = -120, random.randint(100, 620)
                else:           ex, ey = 1400, random.randint(100, 620)
                if random.random() < 0.34:  # 34% Mandingo, 66% Vulva
                    # Spawn Mandingo
                    m_hp = 15 + spice_level
                    MandingoShip(ex, ey, m_hp)
                    if audio_enabled:
                        mandingo_enter_sound.play()
                        mandingo_engine_ch = pygame.mixer.find_channel()
                        if mandingo_engine_ch:
                            mandingo_engine_ch.play(mandingo_engine_sound, loops=-1)
                        mandingo_engine_playing = True
                else:
                    # Spawn Vulva
                    v_hp = 1 + int(AsteroidField.speed_multiplier)
                    VulvaShip(ex, ey, v_hp)
                    if audio_enabled and vulva_enter_sound:
                        vulva_enter_sound.play()

            # Stop mandingo engine sound when no mandingos alive
            if mandingo_engine_playing and len(mandingos) == 0:
                if audio_enabled and mandingo_engine_ch:
                    mandingo_engine_ch.stop()
                mandingo_engine_playing = False
            # Reset anti-turtle timer when a boss spawns
            if audio_enabled:
                if player.is_firing_beam and not prev_firing_beam:
                    milk_beam_sound.play(loops=-1)
                elif not player.is_firing_beam and prev_firing_beam:
                    milk_beam_sound.stop()
                if player.thruster_active and not prev_thruster_active:
                    thruster_sound.play(loops=-1)
                elif not player.thruster_active and prev_thruster_active:
                    thruster_sound.stop()
            prev_firing_beam     = player.is_firing_beam
            prev_thruster_active = player.thruster_active

            if prev_milk_beam_active and not player.milk_beam_active:
                total_shots_fired = max(total_shots_fired, spice_score)
            prev_milk_beam_active = player.milk_beam_active

            if butts_busted >= 50:
                spice_level = max(0, total_shots_fired - spice_score)
                boss_hp     = 9 + (spice_level // 2)
                # Pick a random off-screen spawn point on any edge
                edge_choice = random.randint(0, 3)
                if edge_choice == 0:   # top
                    bx, by = random.randint(100, 1180), -100
                elif edge_choice == 1: # bottom
                    bx, by = random.randint(100, 1180), 820
                elif edge_choice == 2: # left
                    bx, by = -100, random.randint(100, 620)
                else:                  # right
                    bx, by = 1380, random.randint(100, 620)

                # Aim toward screen center with a small random spread
                target = pygame.Vector2(640, 360)
                direction = (target - pygame.Vector2(bx, by)).normalize()
                direction = direction.rotate(random.uniform(-25, 25))
                speed = random.uniform(150, 220)
                new_boss = Boss(bx, by, boss_hp)
                new_boss.velocity = direction * speed
                butts_busted      = 0
                anti_turtle_timer = ANTI_TURTLE_BASE  # boss spawned — reset turtle timer
                if audio_enabled:
                    if new_boss.skin == "dickbutt":
                        boss_enter_sound.play()
                    elif new_boss.skin == "titvag":
                        titvag_enter_sound.play()
                    elif new_boss.skin == "coinpurse":
                        coinpurse_enter_sound.play()
                    if not sus_playing:
                        dick_sus_sound.set_volume(0.40)
                        dick_sus_sound.play(loops=-1)
                        sus_playing = True

            if audio_enabled and sus_playing and len(bosses) == 0:
                dick_sus_sound.stop()
                sus_playing = False

            powerup_spawn_timer -= dt
            if powerup_spawn_timer <= 0:
                powerup_spawn_timer = max(POWERUP_SPAWN_BASE + random.uniform(-5, 5), 5.0)
                PowerUp(random.choice(["condom", "zinc", "dp"]))

            for powerup in list(powerups):
                if powerup.collides_with(player):
                    if powerup.kind == "condom":
                        if player.shield_count >= 2:
                            # Already double wrapped — award 50 points
                            score += 50
                            particles.spawn_score_pop(
                                powerup.position.x, powerup.position.y,
                                text="+50", color=(100, 200, 255))
                        else:
                            player.activate_shield()
                            if player.shield_count == 2:
                                particles.spawn_double_wrapped()
                        if audio_enabled: swoosh_sound.play()
                    elif powerup.kind == "zinc":
                        player.activate_milk_beam()
                        if audio_enabled: gulp_sound.play()
                    elif powerup.kind == "dp":
                        player.activate_dp()
                        if audio_enabled: gulp_sound.play()
                    powerup.kill()

            for boss in list(bosses):
                # Only auto-rotate toward player when not running a special attack
                if boss.special_state in ("idle", "cooldown"):
                    dx = player.position.x - boss.position.x
                    dy = player.position.y - boss.position.y
                    base_angle = math.degrees(math.atan2(-dy, dx)) + 180
                    boss.angle = base_angle + (90 if boss.skin == "coinpurse" else 0)
                if boss.collides_with(player) and not player.is_invincible():
                    if player.has_shield:
                        player.consume_shield()
                        if audio_enabled: rubber_pop_sound.play()
                    else:
                        high_score, death_freeze_timer = player_death(
                            score, high_score, audio_enabled, death_sound,
                            death_sfx_length)
                        sus_playing = False
                        state = "DYING"
                        break
                for shot in list(shots):
                    if boss.collides_with(shot):
                        total_shots_fired -= 1
                        shot.kill()
                        if boss.take_damage():
                            stat_bosses_killed += 1
                            particles.spawn_boss_explosion(boss.position.x, boss.position.y)
                            score, shake_timer = boss_death_clear(
                                asteroids, score, audio_enabled,
                                poop_splat_sound, boss_death_sound,
                                shake_timer, SHAKE_DURATION,
                                wormholes=wormholes, spice_level=spice_level,
                                boss_pos=boss.position)

                # Dick Butt laser hits player
                if boss.laser_hits(player) and not player.is_invincible():
                    if player.has_shield:
                        player.consume_shield()
                        if audio_enabled: rubber_pop_sound.play()
                    else:
                        high_score, death_freeze_timer = player_death(
                            score, high_score, audio_enabled, death_sound, death_sfx_length)
                        sus_playing = False
                        state = "DYING"

                # TitVag suction pull
                pull = boss.get_suction_force()
                if pull > 0:
                    to_boss = boss.position - player.position
                    if to_boss.length() > 1:
                        player.position += to_boss.normalize() * pull * dt

            if player.is_firing_beam:
                beam_damage_timer -= dt
                if beam_damage_timer <= 0:
                    beam_damage_timer = BEAM_DAMAGE_INTERVAL
                    for asteroid in list(asteroids):
                        if beam_hits_circle(player, asteroid):
                            is_poop = asteroid.radius <= ASTEROID_MIN_RADIUS
                            multiplier = max(1, int(AsteroidField.speed_multiplier))
                            if not is_poop:
                                butts_busted += 1
                                stat_butts_killed += 1
                            points = 1 * multiplier
                            score += points
                            spice_score += 1
                            if is_poop:
                                stat_poops_killed += 1
                                if audio_enabled: poop_splat_sound.play()
                                pop_text  = f"+{points}" if multiplier == 1 else f"+{points} x{multiplier}"
                                pop_color = (255, 255, 100) if multiplier == 1 else (255, 180, 0)
                                particles.spawn_score_pop(asteroid.position.x,
                                                          asteroid.position.y - 10,
                                                          text=pop_text, color=pop_color)
                            else:
                                if audio_enabled: butt_smack_sound.play()
                            particles.spawn_explosion(asteroid.position.x,
                                                      asteroid.position.y,
                                                      is_butt=not is_poop)
                            particles.check_meteor_shower(score)
                            particles.check_personal_best(score, high_score)
                            asteroid.split()
                            maybe_spawn_suppository(asteroid, suppositories, AsteroidField.speed_multiplier)
                    for boss in list(bosses):
                        if beam_hits_circle(player, boss):
                            if boss.take_damage():
                                stat_bosses_killed += 1
                                particles.spawn_boss_explosion(boss.position.x, boss.position.y)
                                score, shake_timer = boss_death_clear(
                                    asteroids, score, audio_enabled,
                                    poop_splat_sound, boss_death_sound,
                                    shake_timer, SHAKE_DURATION,
                                wormholes=wormholes, spice_level=spice_level,
                                boss_pos=boss.position)
                    for mandingo in list(mandingos):
                        if beam_hits_circle(player, mandingo):
                            total_shots_fired -= 1  # don't add to spice
                            if mandingo.take_damage():
                                bonus = mandingo.poops_destroyed + 50
                                score       += bonus
                                particles.spawn_score_pop(
                                    mandingo.position.x, mandingo.position.y - 20,
                                    text=f"+{bonus}", color=(255, 200, 0))
                                particles.spawn_metal_explosion(
                                    mandingo.position.x, mandingo.position.y)
                                if audio_enabled:
                                    explosion_sfx.play()
                                    if mandingo_charge_sound: mandingo_charge_sound.stop()
                                particles.check_personal_best(score, high_score)
                                particles.check_meteor_shower(score)
            else:
                beam_damage_timer = 0.0

            for asteroid in list(asteroids):
                if asteroid.collides_with(player) and not player.is_invincible():
                    if player.has_shield:
                        player.consume_shield()
                        if audio_enabled: rubber_pop_sound.play()
                    else:
                        high_score, death_freeze_timer = player_death(
                            score, high_score, audio_enabled, death_sound,
                            death_sfx_length)
                        sus_playing = False
                        state = "DYING"
                        break  # player is dead, stop processing asteroids
                for shot in list(shots):
                    if asteroid.collides_with(shot):
                        is_poop = asteroid.radius <= ASTEROID_MIN_RADIUS
                        multiplier = max(1, int(AsteroidField.speed_multiplier))
                        if not is_poop:
                            butts_busted += 1
                            stat_butts_killed += 1
                        if is_poop:
                            points = 1 * multiplier
                            score += points
                            spice_score += 1
                            stat_poops_killed += 1
                            if audio_enabled: poop_splat_sound.play()
                            pop_text  = f"+{points}" if multiplier == 1 else f"+{points} x{multiplier}"
                            pop_color = (255, 255, 100) if multiplier == 1 else (255, 180, 0)
                            particles.spawn_score_pop(asteroid.position.x,
                                                      asteroid.position.y - 10,
                                                      text=pop_text, color=pop_color)
                        else:
                            if audio_enabled: butt_smack_sound.play()
                        particles.spawn_explosion(asteroid.position.x,
                                                  asteroid.position.y,
                                                  is_butt=not is_poop)
                        particles.check_meteor_shower(score)
                        particles.check_personal_best(score, high_score)
                        shot.kill()
                        asteroid.split()
                        maybe_spawn_suppository(asteroid, suppositories, AsteroidField.speed_multiplier)
                        break

            # ---------------------------------------------------------------
            # MANDINGO COLLISIONS
            # ---------------------------------------------------------------
            for mandingo in list(mandingos):

                # Mandingo shot hits player — once per shot
                for mshot in list(mandingo_shots):
                    if id(player) not in mshot.hit_ids and mshot.collides_with(player) and not player.is_invincible():
                        mshot.hit_ids.add(id(player))
                        if player.has_shield:
                            player.consume_shield()
                            if audio_enabled: rubber_pop_sound.play()
                        else:
                            high_score, death_freeze_timer = player_death(
                                score, high_score, audio_enabled,
                                death_sound, death_sfx_length)
                            sus_playing = False
                            state = "DYING"
                            break

                # Mandingo shot hits asteroids — shot plows through everything
                for mshot in list(mandingo_shots):
                    if not mshot.alive():
                        continue
                    for asteroid in list(asteroids):
                        if id(asteroid) not in mshot.hit_ids and mshot.collides_with(asteroid):
                            mshot.hit_ids.add(id(asteroid))
                            if asteroid.radius <= 20:
                                mandingo.poops_destroyed += 1
                                if audio_enabled: poop_splat_sound.play()
                            else:
                                butts_busted += 1
                                if audio_enabled: butt_smack_sound.play()
                            particles.spawn_explosion(
                                asteroid.position.x, asteroid.position.y,
                                is_butt=(asteroid.radius > 20))
                            asteroid.split()
                            maybe_spawn_suppository(asteroid, suppositories, AsteroidField.speed_multiplier)
                    # Also damages boss — once per shot, 3 HP
                    for boss in list(bosses):
                        if id(boss) not in mshot.hit_ids and mshot.collides_with(boss):
                            mshot.hit_ids.add(id(boss))
                            for _ in range(3):
                                if boss.take_damage():
                                    stat_bosses_killed += 1
                                    particles.spawn_boss_explosion(boss.position.x, boss.position.y)
                                    score, shake_timer = boss_death_clear(
                                        asteroids, score, audio_enabled,
                                        poop_splat_sound, boss_death_sound,
                                        shake_timer, SHAKE_DURATION,
                                wormholes=wormholes, spice_level=spice_level,
                                boss_pos=boss.position)
                                    break

                # Mandingo body collides with asteroids
                for asteroid in list(asteroids):
                    broad = mandingo.radius + asteroid.visual_radius
                    if mandingo.position.distance_squared_to(asteroid.position) <= broad * broad:
                        if asteroid.radius <= 20:  # poop
                            mandingo.poops_destroyed += 1
                            if audio_enabled: poop_splat_sound.play()
                        else:
                            butts_busted += 1
                            if audio_enabled: butt_smack_sound.play()
                        particles.spawn_explosion(
                            asteroid.position.x, asteroid.position.y,
                            is_butt=(asteroid.radius > 20))
                        asteroid.split()
                        maybe_spawn_suppository(asteroid, suppositories, AsteroidField.speed_multiplier)

                # Player shots hit Mandingo
                for shot in list(shots):
                    if mandingo.collides_with(shot):
                        total_shots_fired -= 1  # don't add to spice level
                        shot.kill()
                        if mandingo.take_damage():
                            # Mandingo died — reward player
                            bonus = mandingo.poops_destroyed + 50
                            score       += bonus
                            particles.spawn_score_pop(
                                mandingo.position.x,
                                mandingo.position.y - 20,
                                text=f"+{bonus}",
                                color=(255, 200, 0))
                            particles.spawn_metal_explosion(
                                mandingo.position.x, mandingo.position.y)
                            if audio_enabled:
                                explosion_sfx.play()
                                if mandingo_charge_sound: mandingo_charge_sound.stop()
                            particles.check_meteor_shower(score)
                        break

                # Mandingo collides with player
                if mandingo.collides_with(player) and not player.is_invincible():
                    if player.has_shield:
                        player.consume_shield()
                        if audio_enabled: rubber_pop_sound.play()
                    else:
                        high_score, death_freeze_timer = player_death(
                            score, high_score, audio_enabled,
                            death_sound, death_sfx_length)
                        sus_playing = False
                        state = "DYING"

            if shake_timer > 0:
                shake_timer -= dt

            # ── Vulva Ship collisions ────────────────────────────────────────
            for vulva in list(vulvas):
                if not vulva.alive():
                    continue

                # Vulva hits player
                if vulva.collides_with(player) and not player.is_invincible():
                    if player.has_shield:
                        player.consume_shield()
                        if audio_enabled: rubber_pop_sound.play()
                    else:
                        high_score, death_freeze_timer = player_death(
                            score, high_score, audio_enabled,
                            death_sound, death_sfx_length)
                        sus_playing = False
                        state = "DYING"

                # Vulva hits asteroids — destroys everything it touches
                for asteroid in list(asteroids):
                    if getattr(asteroid, 'grace_timer', 0) > 0:
                        continue
                    if vulva.collides_with(asteroid):
                        if asteroid.radius <= 20:
                            vulva.poops_destroyed += 1
                            if audio_enabled: poop_splat_sound.play()
                        else:
                            butts_busted += 1
                            if audio_enabled: butt_smack_sound.play()
                        particles.spawn_explosion(
                            asteroid.position.x, asteroid.position.y,
                            is_butt=(asteroid.radius > 20))
                        asteroid.split()
                        maybe_spawn_suppository(asteroid, suppositories, AsteroidField.speed_multiplier)

                # Vulva hits bosses — 3 HP once per frame per boss
                for boss in list(bosses):
                    if id(boss) not in vulva.boss_hit_ids and vulva.collides_with(boss):
                        vulva.boss_hit_ids.add(id(boss))
                        for _ in range(3):
                            if boss.take_damage():
                                stat_bosses_killed += 1
                                particles.spawn_boss_explosion(boss.position.x, boss.position.y)
                                score, shake_timer = boss_death_clear(
                                    asteroids, score, audio_enabled,
                                    poop_splat_sound, boss_death_sound,
                                    shake_timer, SHAKE_DURATION,
                                wormholes=wormholes, spice_level=spice_level,
                                boss_pos=boss.position)
                                break

                # Player shots hit Vulva
                for shot in list(shots):
                    if vulva.collides_with(shot):
                        total_shots_fired -= 1  # don't add to spice level
                        shot.kill()
                        if vulva.take_damage():
                            bonus = vulva.poops_destroyed + 25
                            score += bonus
                            particles.spawn_score_pop(
                                vulva.position.x, vulva.position.y - 20,
                                text=f"+{bonus}", color=(255, 200, 0))
                            particles.spawn_metal_explosion(
                                vulva.position.x, vulva.position.y)
                            if audio_enabled: explosion_sfx.play()
                            particles.check_personal_best(score, high_score)
                            particles.check_meteor_shower(score)
                        break

                # Beam hits Vulva
                if player.is_firing_beam:
                    if beam_hits_circle(player, vulva):
                        total_shots_fired -= 1
                        if vulva.take_damage():
                            bonus = vulva.poops_destroyed + 25
                            score += bonus
                            particles.spawn_score_pop(
                                vulva.position.x, vulva.position.y - 20,
                                text=f"+{bonus}", color=(255, 200, 0))
                            particles.spawn_metal_explosion(
                                vulva.position.x, vulva.position.y)
                            if audio_enabled: explosion_sfx.play()
                            particles.check_personal_best(score, high_score)
                            particles.check_meteor_shower(score)

            # ── Golden Suppository collisions ─────────────────────────────────────
            for supp in list(suppositories):
                if not supp.alive():
                    continue
                # Player body hits suppository
                if supp.collides_with(player) and not player.is_invincible():
                    if player.has_shield:
                        player.consume_shield()
                        if audio_enabled: rubber_pop_sound.play()
                    else:
                        high_score, death_freeze_timer = player_death(
                            score, high_score, audio_enabled,
                            death_sound, death_sfx_length)
                        sus_playing = False
                        state = "DYING"
                # Player shots hit suppository
                for shot in list(shots):
                    if supp.collides_with(shot):
                        shot.kill()
                        total_shots_fired -= 1
                        if supp.take_damage():
                            score += 100
                            particles.spawn_score_pop(
                                supp.position.x, supp.position.y - 20,
                                text="+100", color=(255, 220, 0))
                            particles.spawn_metal_explosion(
                                supp.position.x, supp.position.y)
                            particles.check_personal_best(score, high_score)
                            particles.check_meteor_shower(score)
                        break
                # Beam hits suppository
                if player.is_firing_beam and beam_hits_circle(player, supp):
                    if supp.take_damage():
                        score += 100
                        particles.spawn_score_pop(
                            supp.position.x, supp.position.y - 20,
                            text="+100", color=(255, 220, 0))
                        particles.spawn_metal_explosion(
                            supp.position.x, supp.position.y)
                        particles.check_personal_best(score, high_score)
                        particles.check_meteor_shower(score)

            # ── Tapeworm collisions ─────────────────────────────────────────
            for tw in list(tapeworm_heads):
                if not tw.alive():
                    continue
                # Player collides with head
                if (point_in_triangle(player.position, tw.head_triangle())
                        and not player.is_invincible()):
                    if player.has_shield:
                        player.consume_shield()
                        if audio_enabled: rubber_pop_sound.play()
                    else:
                        high_score, death_freeze_timer = player_death(
                            score, high_score, audio_enabled, death_sound, death_sfx_length)
                        sus_playing = False
                        state = "DYING"
                # Player collides with segments
                for i, seg in enumerate(list(tw.segments)):
                    if not seg.alive:
                        continue
                    if (player.position.distance_squared_to(seg.position) <= (player.radius + SEG_RADIUS) ** 2
                            and not player.is_invincible()):
                        if player.has_shield:
                            player.consume_shield()
                            if audio_enabled: rubber_pop_sound.play()
                        else:
                            high_score, death_freeze_timer = player_death(
                                score, high_score, audio_enabled, death_sound, death_sfx_length)
                            sus_playing = False
                            state = "DYING"
                # Player shots hit head
                for shot in list(shots):
                    if point_in_triangle(shot.position, tw.head_triangle()):
                        shot.kill()
                        total_shots_fired -= 1
                        if tw.take_damage():
                            particles.spawn_boss_explosion(tw.position.x, tw.position.y)
                        break
                # Player shots hit segments
                for shot in list(shots):
                    if not shot.alive():
                        continue
                    hit = False
                    for i, seg in enumerate(list(tw.segments)):
                        if not seg.alive:
                            continue
                        if shot.position.distance_squared_to(seg.position) <= (shot.radius + SEG_RADIUS) ** 2:
                            shot.kill()
                            total_shots_fired -= 1
                            particles.spawn_explosion(seg.position.x, seg.position.y, is_butt=False, count=6)
                            new_head = tw.damage_segment(i, spice_level)
                            hit = True
                            break
                    if hit:
                        break
                # Beam hits head
                if player.is_firing_beam and point_in_triangle(player.position, tw.head_triangle()):
                    if tw.take_damage():
                        particles.spawn_boss_explosion(tw.position.x, tw.position.y)
                # Beam hits segments
                if player.is_firing_beam:
                    for i, seg in enumerate(list(tw.segments)):
                        if not seg.alive:
                            continue
                        fc = _FakeCircle(seg.position, SEG_RADIUS)
                        if beam_hits_circle(player, fc):
                            particles.spawn_explosion(seg.position.x, seg.position.y, is_butt=False, count=6)
                            new_head = tw.damage_segment(i, spice_level)
                            break

            spice_level = max(0, total_shots_fired - spice_score)

            # Update particles (exhaust spawns here too)
            particles.update(dt, player=player)

            # Draw layers: stars → nebula → meteors → milk beam → sprites → exhaust/explosions/pops
            stars.draw(internal_surf, hardness=AsteroidField.speed_multiplier)
            nebula.draw(internal_surf, spice_level)
            particles.draw_background(internal_surf)
            if player.is_firing_beam:
                draw_milk_beam(internal_surf, player)
            for obj in drawable:
                obj.draw(internal_surf)
                if DEBUG_HITBOXES and hasattr(obj, 'draw_debug'):
                    if hasattr(obj, 'triangle'):
                        verts = obj.triangle()
                        pygame.draw.polygon(internal_surf, (255, 0, 0), [(v.x, v.y) for v in verts], 1)
                    else:
                        obj.draw_debug(internal_surf)
            particles.draw_foreground(internal_surf)
            if score != _hud_score_v:
                _hud_score   = font.render(f"SCORE: {score}", True, "white")
                _hud_score_v = score
            if spice_level != _hud_spice_v:
                _hud_spice   = font.render(f"SPICE LEVEL: {spice_level}", True, (255, 165, 0))
                _hud_spice_v = spice_level
            _hard_v = round(AsteroidField.speed_multiplier, 2)
            if _hard_v != _hud_hard_v:
                _hud_hard   = font.render(f"HARDNESS: {_hard_v:.2f}x", True, (255, 100, 100))
                _hud_hard_v = _hard_v
            internal_surf.blit(_hud_score, (20, 650))
            internal_surf.blit(_hud_spice, (990, 80))
            internal_surf.blit(_hud_hard,  (20, 680))
            draw_thruster_bar(internal_surf, 20, 20, 250, 22,
                              player.thruster_charge, player.thruster_active,
                              player.thruster_locked, small_font,
                              pygame.time.get_ticks())
            draw_boss_sauce(internal_surf, 980, 50, 250, 25, butts_busted, font)
            hud_y = 50
            if player.has_shield:
                label = "DOUBLE WRAPPED" if player.shield_count == 2 else "SHIELD ACTIVE"
                color = (100, 255, 150) if player.shield_count == 2 else (100, 200, 255)
                shield_txt = small_font.render(label, True, color)
                internal_surf.blit(shield_txt, (20, hud_y))
                # Draw shield icons
                for i in range(player.shield_count):
                    internal_surf.blit(shield_icon, (20 + shield_txt.get_width() + 6 + i * 24, hud_y))
                hud_y += 24
            if player.is_firing_beam:
                secs_left = math.ceil(player.milk_beam_timer)
                beam_txt  = small_font.render(f"MILK BEAM: {secs_left}s", True, (200, 220, 255))
                internal_surf.blit(beam_txt, (20, hud_y))
                hud_y += 24
            if player.dp_active:
                secs_left = math.ceil(player.dp_timer)
                dp_txt = small_font.render(f"DOUBLE SHOT: {secs_left}s", True, (184, 0, 0))
                internal_surf.blit(dp_txt, (20, hud_y))

        # ===================================================================
        # WARP FLASH — 1 second vortex before galaxy transition
        # ===================================================================
        elif state == "WARP_FLASH":
            warp_flash_timer -= dt
            progress = 1.0 - max(0.0, warp_flash_timer / WARP_FLASH_DURATION)
            wh = warp_flash_wormhole

            # Player can still move during flash
            player.update(dt, speed_multiplier=AsteroidField.speed_multiplier)

            # Cancel if player leaves wormhole
            if wh and wh.alive():
                if not wh.player_overlaps(player.position, player.radius):
                    state = "GAME"
                    warp_flash_wormhole = None
                    warp_flash_timer    = 0.0
                    # Wormhole stays alive in rainbow state — player can re-enter
                else:
                    # Draw game scene
                    internal_surf.fill((0, 0, 0))
                    stars.draw(internal_surf, hardness=AsteroidField.speed_multiplier)
                    nebula.draw(internal_surf, spice_level)
                    for obj in drawable:
                        obj.draw(internal_surf)

                    # Vortex effect — rotating electric rings
                    if wh:
                        cx = int(wh.position.x)
                        cy = int(wh.position.y)
                        t  = pygame.time.get_ticks() / 1000.0

                        # Expanding rings with rotation
                        for ring in range(5):
                            ring_frac = (ring / 5 + progress * 0.4) % 1.0
                            r         = int(ring_frac * WORMHOLE_VISUAL_R * 3.5)
                            alpha     = int(200 * (1.0 - ring_frac) * progress)
                            if r > 0 and alpha > 0:
                                rc = int(abs(math.sin(t*4 + ring*1.2))*180 + 75)
                                gc = int(abs(math.sin(t*3 + ring*0.8))*100)
                                bc = 255
                                gs = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
                                thick = max(1, int(4 * (1.0 - ring_frac)))
                                pygame.draw.circle(gs, (rc, gc, bc, alpha),
                                                   (r+1, r+1), r, thick)
                                internal_surf.blit(gs, (cx-r-1, cy-r-1))

                        # Electric arc spokes
                        spoke_count = 8
                        spoke_len   = int(WORMHOLE_VISUAL_R * 2.5 * progress)
                        alpha       = int(180 * progress)
                        arc_surf    = pygame.Surface(internal_surf.get_size(), pygame.SRCALPHA)
                        for s in range(spoke_count):
                            spoke_angle = (s / spoke_count) * 360 + t * 180
                            rad         = math.radians(spoke_angle)
                            jitter      = random.uniform(0.7, 1.0)
                            ex = int(cx + math.cos(rad) * spoke_len * jitter)
                            ey = int(cy + math.sin(rad) * spoke_len * jitter)
                            pygame.draw.line(arc_surf, (150, 100, 255, alpha),
                                             (cx, cy), (ex, ey), 2)
                        internal_surf.blit(arc_surf, (0, 0))

                        # Bright white core flash at center
                        core_r = int(WORMHOLE_VISUAL_R * 0.6 * progress)
                        if core_r > 0:
                            core_surf = pygame.Surface((core_r*2, core_r*2), pygame.SRCALPHA)
                            pygame.draw.circle(core_surf, (255, 255, 255, int(200*progress)),
                                               (core_r, core_r), core_r)
                            internal_surf.blit(core_surf, (cx-core_r, cy-core_r))

            if warp_flash_timer <= 0 and wh and wh.alive():
                # Commit — consume wormhole and start transition
                wh.state = "consumed"
                wh.kill()
                if lullaby_channel: lullaby_channel.stop()
                lullaby_playing = False
                warp_flash_wormhole = None
                state        = "GALAXY_TRANSITION"
                galaxy_timer = GALAXY_DURATION
                player.invincible_timer = GALAXY_DURATION + 1.0

        # ===================================================================
        # GALAXY TRANSITION — warp effect before new galaxy
        # ===================================================================
        elif state == "GALAXY_TRANSITION":
            galaxy_timer -= dt

            # Draw warp effect — streaking stars rushing toward center
            internal_surf.fill((0, 0, 0))
            t = pygame.time.get_ticks() / 1000.0
            progress = max(0.0, 1.0 - galaxy_timer / GALAXY_DURATION)

            # Nebula shifts through galaxy colors during transition
            galaxy_spice = int(progress * 120)   # drive nebula through full color range
            nebula.draw(internal_surf, galaxy_spice)

            for _ in range(120):
                angle  = random.uniform(0, 360)
                speed  = 200 + progress * 800
                dist   = random.uniform(20, 400 * (1.0 + progress))
                px     = 640 + math.cos(math.radians(angle)) * dist
                py     = 360 + math.sin(math.radians(angle)) * dist
                length = max(4, int(speed * dt * 8))
                ex     = 640 + math.cos(math.radians(angle)) * (dist + length)
                ey     = 360 + math.sin(math.radians(angle)) * (dist + length)
                fade   = max(0, min(255, int(100 + 155 * progress)))
                pygame.draw.line(internal_surf, (fade, fade, 255),
                                 (int(px), int(py)), (int(ex), int(ey)), 1)
            # Rainbow center flash
            ph = t * 8
            for i in range(3):
                r_c = int(abs(math.sin(ph + i * 2)) * 255)
                g_c = int(abs(math.sin(ph + i * 2 + 2)) * 255)
                b_c = int(abs(math.sin(ph + i * 2 + 4)) * 255)
                gs = pygame.Surface((200, 200), pygame.SRCALPHA)
                pygame.draw.circle(gs, (r_c, g_c, b_c, 80), (100, 100), 80 + i * 20)
                internal_surf.blit(gs, (540, 260))

            # Draw ship centered, rotated 180°, scaled 4x, fading out toward end
            fade_alpha   = int(255 * (galaxy_timer / GALAXY_DURATION))
            source_img   = player.shield_image if player.has_shield else player.original_image
            ship_size    = int(source_img.get_width() * 4)
            ship_img     = pygame.transform.scale(
                pygame.transform.rotate(source_img, 180),
                (ship_size, ship_size))
            ship_img.set_alpha(fade_alpha)
            ship_rect    = ship_img.get_rect(center=(640, 360))

            # Expanding rounded square — starts at ship icon size, grows to cover screen
            start_size = ship_size
            end_size   = _GALAXY_END_SIZE
            sq_size    = int(start_size + (end_size - start_size) * progress)
            sq_alpha   = int(255 * min(1.0, progress * 1.5))
            border_r   = int(sq_size * 0.12)
            sq_surf    = pygame.Surface((sq_size, sq_size), pygame.SRCALPHA)
            sq_color   = (34, 85, 34, sq_alpha)   # dark green matching icon background
            pygame.draw.rect(sq_surf, sq_color,
                             (0, 0, sq_size, sq_size), border_radius=border_r)
            sq_rect    = sq_surf.get_rect(center=(640, 360))
            internal_surf.blit(sq_surf, sq_rect.topleft)

            # Ship drawn on top of expanding square
            internal_surf.blit(ship_img, ship_rect)
            if galaxy_timer <= 0:
                # Reset to new galaxy — keep hardness, reset spice/boss sauce/field
                spice_score       = total_shots_fired   # zeroes out spice_level
                butts_busted      = 0
                # Clear ALL old objects — kill() removes from every group
                for a in list(asteroids):       a.kill()
                for s in list(shots):           s.kill()
                for b in list(bosses):          b.kill()
                for p in list(powerups):        p.kill()
                for s in list(suppositories):   s.kill()
                for w in list(wormholes):       w.kill()
                for t in list(tapeworm_heads):  t.kill()
                for m in list(mandingos):       m.kill()
                for ms in list(mandingo_shots): ms.kill()
                for v in list(vulvas):          v.kill()
                if croak_channel:     croak_channel.stop()
                if lullaby_channel:   lullaby_channel.stop()
                if space_amb_channel: space_amb_channel.stop()
                croak_playing   = False
                lullaby_playing = False
                sus_playing     = False
                mandingo_engine_playing = False
                vulva_engine_playing    = False
                particles.clear()   # use proper clear method
                # Fresh nebula for the new galaxy
                nebula = Nebula(1280, 720)
                first_shot_fired  = False
                asteroid_field.butt_delay = 15.0
                # Respawn opening poop field — 99 × hardness (more chaotic each galaxy)
                player_spawn = pygame.Vector2(1280 / 2, 720 / 2)
                poop_count   = int(99 * AsteroidField.speed_multiplier)
                for _ in range(poop_count):
                    while True:
                        pos = pygame.Vector2(random.randint(60, 1220),
                                             random.randint(60, 660))
                        if pos.distance_to(player_spawn) >= 120:
                            break
                    poop = Asteroid(pos.x, pos.y, ASTEROID_MIN_RADIUS)
                    poop.velocity  = pygame.Vector2(0, 0)
                    poop.spin_rate = random.uniform(-120, 120)
                player.position = pygame.Vector2(640, 360)
                player.invincible_timer = 2.0
                am_jam_paused  = False
                am_jam_waiting = False
                if audio_enabled and am_jam_sounds:
                    _am = random.choice(am_jam_sounds)
                    pygame.mixer.music.load(_am)
                    pygame.mixer.music.set_volume(0.3)
                    pygame.mixer.music.play()
                if audio_enabled and space_amb_channel and space_amb_sound:
                    space_amb_channel.play(space_amb_sound, loops=-1)
                state = "GAME"

        # ===================================================================
        # DYING STATE — freeze screen on death SFX, then show stats
        # ===================================================================
        elif state == "DYING":
            if croak_channel: croak_channel.stop()
            croak_playing = False
            if lullaby_channel: lullaby_channel.stop()
            lullaby_playing = False
            if space_amb_channel: space_amb_channel.stop()
            death_freeze_timer -= dt
            if death_freeze_timer <= 0:
                stats_timer = 0.0
                _stats_keys_on_open = set(i for i, k in enumerate(pygame.key.get_pressed()) if k)
                state = "STATS"

        # ===================================================================
        # STATS STATE — Player Shitistics screen
        # ===================================================================
        elif state == "STATS":
            stats_timer += dt
            # Play credits tune once after 1 second delay
            if audio_enabled and credits_tune and 1.0 <= stats_timer < 1.0 + dt:
                credits_tune.play()

            internal_surf.fill((0, 0, 0))
            stars.draw(internal_surf, hardness=AsteroidField.speed_multiplier)

            # RIP

            rip_surf  = stats_rip_font.render("RIP", True, (200, 0, 0))
            internal_surf.blit(rip_surf, (640 - rip_surf.get_width() // 2, 80))

            # Title

            title_surf = stats_title_font.render("Player Shitistics", True, (255, 215, 0))
            internal_surf.blit(title_surf, (640 - title_surf.get_width() // 2, 150))

            stat_lines = [
                f"Final Score:       {score}",
                f"Shit Shot:         {stat_poops_killed}",
                f"Cheeks Clapped:    {stat_butts_killed}",
                f"Bosses Downed:     {stat_bosses_killed}",
                f"Shots Fired:       {stat_shots_fired_raw}",
            ]

            for i, line in enumerate(stat_lines):
                surf = stats_line_font.render(line, True, "white")
                internal_surf.blit(surf, (640 - surf.get_width() // 2, 220 + i * 38))

            # Prompt
            prompt_alpha = int(abs(math.sin(stats_timer * 3)) * 200 + 55)
            prompt_surf  = small_font.render("[ Press any key to continue ]", True, (150, 150, 150))
            prompt_surf.set_alpha(prompt_alpha)
            internal_surf.blit(prompt_surf, (640 - prompt_surf.get_width() // 2, 460))

            # Any key → menu (no time limit)
            keys_pressed = pygame.key.get_pressed()
            # Close only when a key pressed NOW was NOT held when stats screen opened
            new_key = any(k and i not in _stats_keys_on_open
                         for i, k in enumerate(keys_pressed))
            if new_key:
                if audio_enabled:
                    if credits_tune:
                        credits_tune.stop()
                    if space_amb_channel:
                        space_amb_channel.stop()
                    pygame.mixer.music.load(asset_path("Ass Roids Menu Song.mp3"))
                    pygame.mixer.music.play(-1)
                    apply_settings(settings, audio_enabled, all_sounds_list, in_game=False)
                state = "MENU"

        # ===================================================================
        # Final Scaling / Letterboxing
        # ===================================================================
        win_w, win_h = screen.get_size()
        target_ratio = 1280 / 720
        if win_w / win_h > target_ratio:
            scale_h = win_h
            scale_w = int(win_h * target_ratio)
        else:
            scale_w = win_w
            scale_h = int(win_w / target_ratio)
        scaled_view = pygame.transform.scale(internal_surf, (scale_w, scale_h))
        offset_x = (win_w - scale_w) // 2
        offset_y = (win_h - scale_h) // 2
        screen.fill("black")
        shake_x = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY) if shake_timer > 0 else 0
        shake_y = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY) if shake_timer > 0 else 0
        screen.blit(scaled_view, (offset_x + shake_x, offset_y + shake_y))
        pygame.display.flip()
        dt = clock.tick(60) / 1000


if __name__ == "__main__":
    main()
