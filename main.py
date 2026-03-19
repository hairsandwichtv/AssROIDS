import pygame
import sys
import json
import subprocess
import math
import random
from starfield import Starfield
from nebula import Nebula
from particles import ParticleManager
from constants import *
from logger import log_event
from asset_helper import asset_path, writable_path
from player import Player
from asteroid import Asteroid
from asteroidfield import AsteroidField
from shot import Shot
from button import Button
from boss import Boss
from powerup import PowerUp
from circleshape import DEBUG_HITBOXES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
POWERUP_SPAWN_BASE   = 20.0
BEAM_DAMAGE_INTERVAL = 0.3
BEAM_LENGTH          = 650

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
    forward   = pygame.Vector2(0, 1).rotate(player.rotation)
    to_target = target.position - player.position
    proj      = to_target.dot(forward)
    if proj < 0 or proj > BEAM_LENGTH:
        return False
    perp_dist = (to_target - forward * proj).length()
    return perp_dist <= target.radius + 5

def draw_milk_beam(surface, player):
    forward = pygame.Vector2(0, 1).rotate(player.rotation)
    start   = pygame.Vector2(player.position) + forward * (player.radius + 4)
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

def draw_settings_menu(surface, settings, font, small_font, waiting_for_key):
    overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))
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

def boss_death_clear(asteroids, score, audio_enabled, poop_splat_sound,
                     boss_death_sound, shake_timer, SHAKE_DURATION):
    """Shared logic for when any boss dies — clear field, boost speed, return updated score and shake_timer."""
    if audio_enabled: boss_death_sound.play()
    shake_timer = SHAKE_DURATION
    AsteroidField.speed_multiplier      *= 1.15
    AsteroidField.spawn_rate_multiplier *= 1.15
    for asteroid in list(asteroids):
        if asteroid.radius <= ASTEROID_MIN_RADIUS:
            score += 1
            asteroid.kill()
        else:
            asteroid.split()
    for asteroid in asteroids:
        asteroid.velocity *= 1.15
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
    except pygame.error:
        audio_enabled = False

    screen        = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    internal_res  = (1280, 720)
    internal_surf = pygame.Surface(internal_res)
    font          = pygame.font.SysFont("Arial", 24, bold=True)
    small_font    = pygame.font.SysFont("Arial", 18, bold=True)
    clock         = pygame.time.Clock()
    dt            = 0

    menu_bg_original = pygame.image.load(asset_path("AssROIDS Menu BG.png")).convert()
    menu_bg          = pygame.transform.scale(menu_bg_original, internal_res)

    sus_channel  = None
    beam_channel = None

    if audio_enabled:
        pygame.mixer.set_num_channels(16)
        pygame.mixer.music.load(asset_path("Ass Roids Menu Song.mp3"))
        pygame.mixer.music.set_volume(0.66)
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
        death_sound      = pygame.mixer.Sound(asset_path("Player Death SFX.mp3"))
        death_sfx_length = death_sound.get_length()  # seconds — used for freeze duration
        sus_channel      = pygame.mixer.Channel(6)
        beam_channel     = pygame.mixer.Channel(7)
    else:
        (tick_sound, blast_off_sound, gun_sound, poop_splat_sound,
         butt_smack_sound, boss_enter_sound, boss_death_sound,
         swoosh_sound, rubber_pop_sound, gulp_sound,
         milk_beam_sound, dick_sus_sound, thruster_sound, death_sound,
         titvag_enter_sound, coinpurse_enter_sound) = (None,) * 16
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
    STATS_DURATION        = 6.0

    updatable = pygame.sprite.Group()
    drawable  = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots     = pygame.sprite.Group()
    bosses    = pygame.sprite.Group()
    powerups  = pygame.sprite.Group()

    # HUD render cache — surfaces only rebuilt when values change
    _hud_score   = _hud_spice = _hud_hard = None
    _hud_score_v = _hud_spice_v = _hud_hard_v = None

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
            hs_label = font.render("HIGHEST SCORE", True, (255, 215, 0))
            hs_value = font.render(str(high_score),  True, "white")
            internal_surf.blit(hs_label, (640 - hs_label.get_width() // 2, 100))
            internal_surf.blit(hs_value, (640 - hs_value.get_width() // 2, 130))

            if start_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                if audio_enabled:
                    blast_off_sound.play()
                    pygame.mixer.music.stop()
                updatable.empty(); drawable.empty()
                asteroids.empty(); shots.empty()
                bosses.empty();    powerups.empty()
                score             = 0
                spice_score       = 0
                butts_busted      = 0
                total_shots_fired = 0
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
                Shot.containers      = (shots,     updatable, drawable)
                Asteroid.containers  = (asteroids, updatable, drawable)
                AsteroidField.containers = (updatable,)
                Player.containers    = (updatable, drawable)
                Boss.containers      = (bosses,    updatable, drawable)
                PowerUp.containers   = (powerups,  updatable, drawable)
                player        = Player(1280 / 2, 720 / 2)
                asteroid_field = AsteroidField()
                state         = "GAME"
                if audio_enabled:
                    pygame.mixer.music.load(asset_path("Space Amb.mp3"))
                    pygame.mixer.music.play(-1)
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
                if player.milk_beam_active:
                    pass
                else:
                    if player.shoot():
                        total_shots_fired += 1
                        stat_shots_fired_raw += 1
                        if audio_enabled: gun_sound.play()

            player.update(dt, speed_multiplier=AsteroidField.speed_multiplier)
            stars.update(dt, hardness=AsteroidField.speed_multiplier)
            for obj in updatable:
                if obj is not player:
                    obj.update(dt)

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
                butts_busted = 0
                if audio_enabled:
                    if new_boss.skin == "dickbutt":
                        boss_enter_sound.play()
                    elif new_boss.skin == "titvag":
                        titvag_enter_sound.play()
                    elif new_boss.skin == "coinpurse":
                        coinpurse_enter_sound.play()
                    if not sus_playing:
                        dick_sus_sound.set_volume(0.60)
                        dick_sus_sound.play(loops=-1)
                        sus_playing = True

            if audio_enabled and sus_playing and len(bosses) == 0:
                dick_sus_sound.stop()
                sus_playing = False

            powerup_spawn_timer -= dt
            if powerup_spawn_timer <= 0:
                powerup_spawn_timer = POWERUP_SPAWN_BASE + random.uniform(-5, 5)
                PowerUp(random.choice(["condom", "zinc", "dp"]))
                powerup_spawn_timer = max(powerup_spawn_timer, 5.0)  # never less than 5s gap

            for powerup in list(powerups):
                if powerup.collides_with(player):
                    if powerup.kind == "condom":
                        if player.has_shield:
                            score += 50
                        else:
                            player.activate_shield()
                        if audio_enabled: swoosh_sound.play()
                    elif powerup.kind == "zinc":
                        player.activate_milk_beam()
                        if audio_enabled: gulp_sound.play()
                    elif powerup.kind == "dp":
                        player.activate_dp()
                        if audio_enabled: gulp_sound.play()
                    powerup.kill()

            for boss in list(bosses):
                dx = player.position.x - boss.position.x
                dy = player.position.y - boss.position.y
                boss.angle = math.degrees(math.atan2(-dy, dx)) + 180
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
                                shake_timer, SHAKE_DURATION)

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
                    for boss in list(bosses):
                        if beam_hits_circle(player, boss):
                            if boss.take_damage():
                                stat_bosses_killed += 1
                                particles.spawn_boss_explosion(boss.position.x, boss.position.y)
                                score, shake_timer = boss_death_clear(
                                    asteroids, score, audio_enabled,
                                    poop_splat_sound, boss_death_sound,
                                    shake_timer, SHAKE_DURATION)
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
                        break

            if shake_timer > 0:
                shake_timer -= dt

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
                shield_txt = small_font.render("SHIELD ACTIVE", True, (100, 200, 255))
                internal_surf.blit(shield_txt, (20, hud_y))
                hud_y += 24
            if player.milk_beam_active:
                secs_left = math.ceil(player.milk_beam_timer)
                beam_txt  = small_font.render(f"MILK BEAM: {secs_left}s", True, (200, 220, 255))
                internal_surf.blit(beam_txt, (20, hud_y))
                hud_y += 24
            if player.dp_active:
                secs_left = math.ceil(player.dp_timer)
                dp_txt = small_font.render(f"DOUBLE SHOT: {secs_left}s", True, (184, 0, 0))
                internal_surf.blit(dp_txt, (20, hud_y))

        # ===================================================================
        # DYING STATE — freeze screen on death SFX, then show stats
        # ===================================================================
        elif state == "DYING":
            death_freeze_timer -= dt
            if death_freeze_timer <= 0:
                stats_timer = STATS_DURATION
                state = "STATS"

        # ===================================================================
        # STATS STATE — Player Shitistics screen
        # ===================================================================
        elif state == "STATS":
            stats_timer += dt  # count up for prompt pulse animation only
            accuracy = 0
            if stat_shots_fired_raw > 0:
                accuracy = int((stat_poops_killed / stat_shots_fired_raw) * 100)

            internal_surf.fill((0, 0, 0))
            stars.draw(internal_surf, hardness=AsteroidField.speed_multiplier)

            # RIP
            rip_font  = pygame.font.SysFont("Arial", 52, bold=True)
            rip_surf  = rip_font.render("RIP", True, (200, 0, 0))
            internal_surf.blit(rip_surf, (640 - rip_surf.get_width() // 2, 80))

            # Title
            title_font = pygame.font.SysFont("Arial", 30, bold=True)
            title_surf = title_font.render("Player Shitistics", True, (255, 215, 0))
            internal_surf.blit(title_surf, (640 - title_surf.get_width() // 2, 150))

            stat_lines = [
                f"Final Score:       {score}",
                f"Shit Shot:         {stat_poops_killed}",
                f"Cheeks Clapped:    {stat_butts_killed}",
                f"Bosses Downed:     {stat_bosses_killed}",
                f"Shots Fired:       {stat_shots_fired_raw}",
            ]
            stat_font = pygame.font.SysFont("Arial", 22)
            for i, line in enumerate(stat_lines):
                surf = stat_font.render(line, True, "white")
                internal_surf.blit(surf, (640 - surf.get_width() // 2, 220 + i * 38))

            # Prompt
            prompt_alpha = int(abs(math.sin(stats_timer * 3)) * 200 + 55)
            prompt_surf  = small_font.render("[ Press any key to continue ]", True, (150, 150, 150))
            prompt_surf.set_alpha(prompt_alpha)
            internal_surf.blit(prompt_surf, (640 - prompt_surf.get_width() // 2, 460))

            # Any key → menu (no time limit)
            keys_pressed = pygame.key.get_pressed()
            any_key = any(keys_pressed)
            if any_key:
                if audio_enabled:
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
