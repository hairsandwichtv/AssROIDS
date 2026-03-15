import pygame
import sys
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
from boss import Boss # Ensure this file exists!

HIGHSCORE_FILE = "highscore.txt"

def load_high_score():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

def save_high_score(score):
    with open(HIGHSCORE_FILE, "w") as f:
        f.write(str(score))

def draw_boss_sauce(surface, x, y, width, height, current_butts, font):
    progress_pct = min(int((current_butts / 50) * 100), 100)
    pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height))
    fill_width = int(width * (progress_pct / 100))
    pygame.draw.rect(surface, (0, 255, 100), (x, y, fill_width, height))
    pygame.draw.rect(surface, "white", (x, y, width, height), 2)
    label = font.render(f"BOSS SAUCE: {progress_pct}%", True, "white")
    surface.blit(label, (x, y - 25))

def main():
    pygame.init()
    pygame.display.set_caption("AssROIDS")
    
    try:
        pygame.mixer.init()
        audio_enabled = True
    except pygame.error:
        audio_enabled = False

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    internal_res = (1280, 720)
    internal_surf = pygame.Surface(internal_res)
    font = pygame.font.SysFont("Arial", 24, bold=True)
    clock = pygame.time.Clock()
    dt = 0

    # Assets
    menu_bg_original = pygame.image.load("AssROIDS Menu BG.png").convert()
    menu_bg = pygame.transform.scale(menu_bg_original, internal_res)
    
    if audio_enabled:
        pygame.mixer.music.load("Ass Roids Menu Song.mp3")
        pygame.mixer.music.set_volume(0.66)
        pygame.mixer.music.play(-1)
        tick_sound       = pygame.mixer.Sound("Button Tick.mp3")
        gun_sound        = pygame.mixer.Sound("Main Gun Sound.mp3")
        poop_splat_sound = pygame.mixer.Sound("Poop Splat.mp3")
        butt_smack_sound = pygame.mixer.Sound("Butt Smack.mp3")
        boss_enter_sound = pygame.mixer.Sound("Boss Enter Cluck.mp3")
        boss_death_sound = pygame.mixer.Sound("Boss Death FX.mp3")
    else:
        tick_sound = gun_sound = poop_splat_sound = None
        butt_smack_sound = boss_enter_sound = boss_death_sound = None

    start_btn = Button(int(1280 * 0.10), 570, "Blast Off Button.png", 0.5)
    exit_btn = Button(int(1280 * 0.90), 570, "Exit Button.png", 0.5)
    stars = Starfield(1280, 720, 200)

    state = "MENU"
    score = 0
    butts_busted = 0
    total_shots_fired = 0
    high_score = load_high_score()

    # Screen shake state
    SHAKE_DURATION = 0.45
    SHAKE_INTENSITY = 10
    shake_timer = 0.0

    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()
    bosses = pygame.sprite.Group()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

        internal_surf.fill("black")

        if state == "MENU":
            internal_surf.blit(menu_bg, (0, 0))

            # High score display
            hs_label = font.render("HIGHEST SCORE", True, (255, 215, 0))
            hs_value = font.render(str(high_score), True, "white")
            internal_surf.blit(hs_label, (636 - hs_label.get_width() // 2, 100))
            internal_surf.blit(hs_value, (636 - hs_value.get_width() // 2, 130))
            if start_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                if audio_enabled: pygame.mixer.music.stop()
                updatable.empty()
                drawable.empty()
                asteroids.empty()
                shots.empty()
                bosses.empty()
                score = 0
                butts_busted = 0
                total_shots_fired = 0
                shake_timer = 0.0

                Shot.containers = (shots, updatable, drawable)
                Asteroid.containers = (asteroids, updatable, drawable)
                AsteroidField.containers = (updatable)
                Player.containers = (updatable, drawable)
                Boss.containers = (bosses, updatable, drawable)

                player = Player(1280 / 2, 720 / 2)
                asteroid_field = AsteroidField()
                state = "GAME"

                # Start ambient game music at 50% volume
                if audio_enabled:
                    pygame.mixer.music.load("Space Amb.mp3")
                    pygame.mixer.music.set_volume(0.50)
                    pygame.mixer.music.play(-1)

            if exit_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                pygame.quit()
                sys.exit()

        elif state == "GAME":
            # 1. Handle Input (Only count shot if fired)
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                if player.shoot():
                    total_shots_fired += 1
                    if audio_enabled: gun_sound.play()

            # 2. Update all objects
            for obj in updatable:
                obj.update(dt)

            # 3. Boss Spawning Logic
            if butts_busted >= 50:
                spice_level = total_shots_fired - score
                boss_hp = max(1, spice_level // 2)
                new_boss = Boss(640, -100, boss_hp) # Spawn off-screen top
                new_boss.velocity = pygame.Vector2(random.uniform(-150, 150), 200)
                butts_busted = 0 # Reset bar immediately
                if audio_enabled: boss_enter_sound.play()

            # 4. Boss AI (Face the player)
            for boss in bosses:
                dx = player.position.x - boss.position.x
                dy = player.position.y - boss.position.y

                # Negate dy to convert from pygame coords (y-down) to math coords (y-up)
                angle_deg = math.degrees(math.atan2(-dy, dx))

                # IMAGE_OFFSET corrects for the natural facing direction of the sprite:
                #   0   = sprite faces RIGHT
                #   90  = sprite faces UP
                #   180 = sprite faces LEFT
                #   270 = sprite faces DOWN
                IMAGE_OFFSET = 180
                boss.angle = angle_deg + IMAGE_OFFSET
                
                # Check Boss vs Player collision
                if boss.collides_with(player):
                    if score > high_score:
                        high_score = score
                        save_high_score(high_score)
                    state = "MENU"
                    if audio_enabled:
                        pygame.mixer.music.load("Ass Roids Menu Song.mp3")
                        pygame.mixer.music.set_volume(0.66)
                        pygame.mixer.music.play(-1)

                for shot in shots:
                    if boss.collides_with(shot):
                        # Offset the shot so it doesn't count as a "miss" toward spice level
                        total_shots_fired -= 1
                        shot.kill()
                        if boss.take_damage():
                            # Boss died — play death sound and trigger screen shake
                            if audio_enabled: boss_death_sound.play()
                            shake_timer = SHAKE_DURATION

                            # Clear all asteroids on screen
                            for asteroid in list(asteroids):
                                if asteroid.radius <= ASTEROID_MIN_RADIUS:
                                    # Poop: award a point and destroy
                                    score += 1
                                    asteroid.kill()
                                else:
                                    # Butt: split as normal (spawns smaller children)
                                    asteroid.split()

                            # Speed up ALL remaining asteroids (including split children) by 2%
                            for asteroid in asteroids:
                                asteroid.velocity *= 1.02

            # 5. Asteroid Collisions
            for asteroid in asteroids:
                if asteroid.collides_with(player):
                    if score > high_score:
                        high_score = score
                        save_high_score(high_score)
                    state = "MENU"
                    if audio_enabled:
                        pygame.mixer.music.load("Ass Roids Menu Song.mp3")
                        pygame.mixer.music.set_volume(0.66)
                        pygame.mixer.music.play(-1)
                
                for shot in shots:
                    if asteroid.collides_with(shot):
                        butts_busted += 1
                        if asteroid.radius <= ASTEROID_MIN_RADIUS:
                            score += 1
                            if audio_enabled: poop_splat_sound.play()
                        else:
                            if audio_enabled: butt_smack_sound.play()
                        shot.kill()
                        asteroid.split()

            # Tick down shake timer
            if shake_timer > 0:
                shake_timer -= dt

            # 6. UI Rendering
            spice_level = total_shots_fired - score
            stars.draw(internal_surf)
            for obj in drawable:
                obj.draw(internal_surf)

            s_text = font.render(f"SCORE: {score}", True, "white")
            h_text = font.render(f"SPICE LEVEL: {spice_level}", True, (255, 165, 0))
            internal_surf.blit(s_text, (20, 20))
            internal_surf.blit(h_text, (990, 80))
            draw_boss_sauce(internal_surf, 980, 50, 250, 25, butts_busted, font)

        # Final Scaling / Letterboxing
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
        # Apply screen shake offset if active
        shake_x = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY) if shake_timer > 0 else 0
        shake_y = random.randint(-SHAKE_INTENSITY, SHAKE_INTENSITY) if shake_timer > 0 else 0
        screen.blit(scaled_view, (offset_x + shake_x, offset_y + shake_y))
        pygame.display.flip()
        dt = clock.tick(60) / 1000

if __name__ == "__main__":
    main()
