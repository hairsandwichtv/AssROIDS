import pygame
import sys
import os
import json
import subprocess
import math
import random
from starfield import Starfield
from constants import *
from logger import log_state, log_event
from player import Player
from asteroid import Asteroid
from asteroidfield import AsteroidField
from shot import Shot
from button import Button
from boss import Boss
from powerup import PowerUp

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
POWERUP_SPAWN_BASE   = 20.0
BEAM_DAMAGE_INTERVAL = 0.3
BEAM_LENGTH          = 650

# ---------------------------------------------------------------------------
# Asset / writable path helpers
# ---------------------------------------------------------------------------
def asset_path(filename):
    """Correct path to a read-only asset (bundled inside PyInstaller package)."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(".")
    return os.path.join(base, filename)

def writable_path(filename):
    """Correct path for files that must persist (scores, settings).
    Uses %APPDATA%\\AssROIDS when frozen so Windows doesn't block writes."""
    if getattr(sys, "frozen", False):
        base = os.path.join(os.environ.get("APPDATA", os.path.dirname(sys.executable)), "AssROIDS")
        os.makedirs(base, exist_ok=True)
    else:
        base = os.path.abspath(".")
    return os.path.join(base, filename)

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

def go_to_menu(score, high_score, audio_enabled, sus_channel, beam_channel):
    if score > high_score:
        high_score = score
        save_high_score(high_score)
    if audio_enabled:
        pygame.mixer.stop()
        pygame.mixer.music.load(asset_path("Ass Roids Menu Song.mp3"))
        pygame.mixer.music.set_volume(0.66)
        pygame.mixer.music.play(-1)
    return high_score

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
        boss_enter_sound = pygame.mixer.Sound(asset_path("Boss Enter Cluck.mp3"))
        boss_death_sound = pygame.mixer.Sound(asset_path("Boss Death FX.mp3"))
        swoosh_sound     = pygame.mixer.Sound(asset_path("Swoosh.mp3"))
        rubber_pop_sound = pygame.mixer.Sound(asset_path("Rubber Pop.mp3"))
        gulp_sound       = pygame.mixer.Sound(asset_path("Gulp.mp3"))
        milk_beam_sound  = pygame.mixer.Sound(asset_path("Milk Beam SFX long.mp3"))
        dick_sus_sound   = pygame.mixer.Sound(asset_path("Dick Butt Sus SFX.mp3"))
        sus_channel      = pygame.mixer.Channel(6)
        beam_channel     = pygame.mixer.Channel(7)
    else:
        (tick_sound, blast_off_sound, gun_sound, poop_splat_sound,
         butt_smack_sound, boss_enter_sound, boss_death_sound,
         swoosh_sound, rubber_pop_sound, gulp_sound,
         milk_beam_sound, dick_sus_sound) = (None,) * 12

    all_sounds_list = [
        tick_sound, blast_off_sound, gun_sound, poop_splat_sound,
        butt_smack_sound, boss_enter_sound, boss_death_sound,
        swoosh_sound, rubber_pop_sound, gulp_sound,
        milk_beam_sound, dick_sus_sound
    ]

    start_btn    = Button(int(1280 * 0.10), 570, asset_path("Blast Off Button.png"), 0.5)
    exit_btn     = Button(int(1280 * 0.90), 570, asset_path("Exit Button.png"),      0.5)
    readme_btn   = Button(133,              150, asset_path("READ ME Button.png"),   0.5)
    settings_btn = Button(int(1280 * 0.90), 150, asset_path("Settings Button.png"),  0.5)
    stars        = Starfield(1280, 720, 200)

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
    sus_playing           = False

    updatable = pygame.sprite.Group()
    drawable  = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots     = pygame.sprite.Group()
    bosses    = pygame.sprite.Group()
    powerups  = pygame.sprite.Group()

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
                sus_playing           = False
                AsteroidField.speed_multiplier      = 1.0
                AsteroidField.spawn_rate_multiplier = 1.0
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
                    pygame.mixer.music.set_volume(0.45)
                    pygame.mixer.music.play(-1)

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
                        if audio_enabled: gun_sound.play()

            for obj in updatable:
                obj.update(dt)

            if audio_enabled:
                if player.is_firing_beam and not prev_firing_beam:
                    milk_beam_sound.play(loops=-1)
                elif not player.is_firing_beam and prev_firing_beam:
                    milk_beam_sound.stop()
            prev_firing_beam = player.is_firing_beam

            if prev_milk_beam_active and not player.milk_beam_active:
                total_shots_fired = max(total_shots_fired, spice_score)
            prev_milk_beam_active = player.milk_beam_active

            if butts_busted >= 50:
                spice_level = max(0, total_shots_fired - spice_score)
                boss_hp     = 9 + (spice_level // 2)
                new_boss    = Boss(640, -100, boss_hp)
                new_boss.velocity = pygame.Vector2(random.uniform(-150, 150), 200)
                butts_busted = 0
                if audio_enabled:
                    boss_enter_sound.play()
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
                PowerUp(random.choice(["condom", "zinc"]))

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
                        high_score = go_to_menu(score, high_score, audio_enabled, sus_channel, beam_channel)
                        sus_playing = False
                        state = "MENU"
                for shot in list(shots):
                    if boss.collides_with(shot):
                        total_shots_fired -= 1
                        shot.kill()
                        if boss.take_damage():
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

            if player.is_firing_beam:
                beam_damage_timer -= dt
                if beam_damage_timer <= 0:
                    beam_damage_timer = BEAM_DAMAGE_INTERVAL
                    for asteroid in list(asteroids):
                        if beam_hits_circle(player, asteroid):
                            if asteroid.radius > ASTEROID_MIN_RADIUS:
                                butts_busted += 1
                            score += 1
                            spice_score += 1
                            if asteroid.radius <= ASTEROID_MIN_RADIUS:
                                if audio_enabled: poop_splat_sound.play()
                            else:
                                if audio_enabled: butt_smack_sound.play()
                            asteroid.split()
                    for boss in list(bosses):
                        if beam_hits_circle(player, boss):
                            if boss.take_damage():
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
            else:
                beam_damage_timer = 0.0

            for asteroid in list(asteroids):
                if asteroid.collides_with(player) and not player.is_invincible():
                    if player.has_shield:
                        player.consume_shield()
                        if audio_enabled: rubber_pop_sound.play()
                    else:
                        high_score = go_to_menu(score, high_score, audio_enabled, sus_channel, beam_channel)
                        sus_playing = False
                        state = "MENU"
                for shot in list(shots):
                    if asteroid.collides_with(shot):
                        if asteroid.radius > ASTEROID_MIN_RADIUS:
                            butts_busted += 1
                        if asteroid.radius <= ASTEROID_MIN_RADIUS:
                            score += 1
                            spice_score += 1
                            if audio_enabled: poop_splat_sound.play()
                        else:
                            if audio_enabled: butt_smack_sound.play()
                        shot.kill()
                        asteroid.split()

            if shake_timer > 0:
                shake_timer -= dt

            spice_level = max(0, total_shots_fired - spice_score)
            stars.draw(internal_surf)
            if player.is_firing_beam:
                draw_milk_beam(internal_surf, player)
            for obj in drawable:
                obj.draw(internal_surf)
            s_text = font.render(f"SCORE: {score}",             True, "white")
            h_text = font.render(f"SPICE LEVEL: {spice_level}", True, (255, 165, 0))
            m_text = font.render(f"HARDNESS: {AsteroidField.speed_multiplier:.2f}x", True, (255, 100, 100))
            internal_surf.blit(s_text, (20, 20))
            internal_surf.blit(h_text, (990, 80))
            internal_surf.blit(m_text, (20, 680))
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
