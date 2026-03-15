import pygame
import sys
from starfield import Starfield
from constants import *
from logger import log_state, log_event
from player import Player
from asteroid import Asteroid
from asteroidfield import AsteroidField
from shot import Shot
from button import Button

def draw_boss_sauce(surface, x, y, width, height, current_butts, font):
    # Calculate percentage (2% per smack, max 100%)
    progress_pct = min(int((current_butts / 50) * 100), 100)
    
    # Draw Bar Background (Dark Grey)
    pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height))
    
    # Draw Fill (Neon Green)
    fill_width = int(width * (progress_pct / 100))
    pygame.draw.rect(surface, (0, 255, 100), (x, y, fill_width, height))
    
    # Draw White Border
    pygame.draw.rect(surface, "white", (x, y, width, height), 2)
    
    # Label above the bar
    label = font.render(f"BOSS SAUCE: {progress_pct}%", True, "white")
    surface.blit(label, (x, y - 25))

def draw_bar(surface, x, y, width, height, progress, label, font):
    # Draw Background (Dark Grey)
    pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height))
    # Draw Fill (Neon Green)
    fill_width = int(width * (progress / 100))
    pygame.draw.rect(surface, (0, 255, 100), (x, y, fill_width, height))
    # Draw Outline
    pygame.draw.rect(surface, "white", (x, y, width, height), 2)
    # Draw Label
    text = font.render(f"{label}: {progress}%", True, "white")
    surface.blit(text, (x, y - 25))

def main():
    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont("Arial", 24, bold=True)

    # WSL Audio Fail-safe
    audio_enabled = True
    try:
        pygame.mixer.init()
    except pygame.error:
        print("Warning: No audio device found. Running in silent mode.")
        audio_enabled = False

    pygame.display.set_caption("AssROIDS")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)

    # 16:9 Internal Canvas
    internal_res = (1280, 720)
    internal_surf = pygame.Surface(internal_res)

    clock = pygame.time.Clock()
    dt = 0

    # Assets
    menu_bg_original = pygame.image.load("AssROIDS Menu BG.png").convert()
    menu_bg = pygame.transform.scale(menu_bg_original, internal_res)

    if audio_enabled:
        pygame.mixer.music.load("Ass Roids Menu Song.mp3")
        pygame.mixer.music.set_volume(0.66)
        pygame.mixer.music.play(-1)
        tick_sound = pygame.mixer.Sound("Button Tick.mp3")
    else:
        tick_sound = None

    # Your specific button parameters
    start_btn = Button(int(1280 * 0.10), 570, "Blast Off Button.png", 0.5)
    exit_btn = Button(int(1280 * 0.90), 570, "Exit Button.png", 0.5)
    stars = Starfield(1280, 720, 200)

    state = "MENU"
    
    # Initialize Counters
    score = 0
    butts_busted = 0
    total_shots_fired = 0

    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()

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
            if start_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                if audio_enabled: pygame.mixer.music.stop()
                
                # RESET EVERYTHING FOR NEW GAME
                updatable.empty()
                drawable.empty()
                asteroids.empty()
                shots.empty()
                score = 0
                butts_busted = 0
                total_shots_fired = 0

                Shot.containers = (shots, updatable, drawable)
                Asteroid.containers = (asteroids, updatable, drawable)
                AsteroidField.containers = (updatable)
                Player.containers = (updatable, drawable)

                player = Player(1280 / 2, 720 / 2)
                asteroid_field = AsteroidField()
                state = "GAME"

            if exit_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                pygame.quit()
                sys.exit()

        elif state == "GAME":
            # Track firing for Dick Butt Health
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                if player.shoot():
                    total_shots_fired += 1

            for obj in updatable:
                obj.update(dt)

            for asteroid in asteroids:
                if asteroid.collides_with(player):
                    log_event("player_hit")
                    state = "MENU"
                    if audio_enabled: pygame.mixer.music.play(-1)
                
                for shot in shots:
                    if asteroid.collides_with(shot):
                        # Logic: Every hit is a busted butt
                        butts_busted += 1
                        # Logic: Only smallest radius gives a score point
                        if asteroid.radius <= ASTEROID_MIN_RADIUS:
                            score += 1
                        
                        shot.kill()
                        asteroid.split()
            draw_boss_sauce(internal_surf, 980, 50, 250, 25, butts_busted, font)
            score_text = font.render(f"SCORE: {score}", True, "white")
            
            # Logic: Spice Level = Shots that didn't destroy a poop
            # 1. Logic Calculations
            sauce_progress = min(int((butts_busted / 50) * 100), 100)
            spice_level = total_shots_fired - score
            
            if sauce_progress >= 100:
                pass # Boss trigger goes here later!

            # 2. Draw Background and Game Objects first
            stars.draw(internal_surf)
            for obj in drawable:
                obj.draw(internal_surf)

            # 3. UI TEXT RENDERING (Top Left)
            s_text = font.render(f"SCORE: {score}", True, "white")
            internal_surf.blit(s_text, (20, 20))

            # 4. SPICE LEVEL (Top Right, under the bar)
            spice_color = (255, 165, 0) # Orange
            if spice_level > 30: 
                spice_color = (255, 50, 50) # Red
            
            h_text = font.render(f"SPICE LEVEL: {spice_level}", True, spice_color)
            # Positioned at 990 to align with the bar above it
            internal_surf.blit(h_text, (990, 80))

            # 5. BOSS SAUCE PROGRESS BAR (Top Right)
            draw_boss_sauce(internal_surf, 980, 50, 250, 25, butts_busted, font)

        # Letterboxing / Scaling
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
        screen.blit(scaled_view, (offset_x, offset_y))

        pygame.display.flip()
        dt = clock.tick(60) / 1000

if __name__ == "__main__":
    main()

