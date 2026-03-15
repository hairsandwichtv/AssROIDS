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

def main():
    pygame.init()
    try:
        pygame.mixer.init()
        audio_enabled = True
    except pygame.error:
        audio_enabled = False

    # 1. FIXED BORDERS: Use RESIZABLE. 
    # Do not call set_mode repeatedly unless flags change; 
    # this often causes Linux/WSL borders to vanish.
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    
    # 2. ASPECT RATIO LOCK: Create a virtual "Internal Surface"
    # We draw everything here first at 1280x720
    internal_res = (1280, 720)
    internal_surf = pygame.Surface(internal_res)

    clock = pygame.time.Clock()
    dt = 0

    # Load Assets
    menu_bg_original = pygame.image.load("AssROIDS Menu BG.png").convert()
    menu_bg = pygame.transform.scale(menu_bg_original, internal_res)
    
    if audio_enabled:
        pygame.mixer.music.load("Ass Roids Menu Song.mp3")
        pygame.mixer.music.set_volume(0.66)
        pygame.mixer.music.play(-1)
        tick_sound = pygame.mixer.Sound("Button Tick.mp3")
        tick_sound.set_volume(0.85)
    else:
        tick_sound = None

    # Buttons are placed relative to the INTERNAL 1280x720 resolution
    start_btn = Button(int(1280 * 0.10), 570, "Blast Off Button.png", 0.5)
    exit_btn = Button(int(1280 * 0.90), 570, "Exit Button.png", 0.5)
    stars = Starfield(1280, 720, 200)

    state = "MENU"
    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()

    while True:
        # Handle Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # Update the window size variable without recreating the whole screen constantly
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

        # Clear internal surface
        internal_surf.fill("black")

        if state == "MENU":
            internal_surf.blit(menu_bg, (0, 0))
            # Use internal_surf for drawing and mouse logic
            if start_btn.draw(internal_surf, tick_sound, is_internal=True, target_res=internal_res):
                if audio_enabled: pygame.mixer.music.stop()
                updatable.empty()
                drawable.empty()
                asteroids.empty()
                shots.empty()

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
            for obj in updatable:
                obj.update(dt)

            for asteroid in asteroids:
                if asteroid.collides_with(player):
                    state = "MENU"
                    if audio_enabled: pygame.mixer.music.play(-1)
                for shot in shots:
                    if asteroid.collides_with(shot):
                        shot.kill()
                        asteroid.split()

            stars.draw(internal_surf)
            for obj in drawable:
                obj.draw(internal_surf)

        # 3. FINAL SCALE: Calculate 16:9 Letterboxing
        win_w, win_h = screen.get_size()
        aspect_ratio = 1280 / 720
        
        if win_w / win_h > aspect_ratio:
            # Window is too wide (add side bars)
            scale_h = win_h
            scale_w = int(win_h * aspect_ratio)
        else:
            # Window is too tall (add top/bottom bars)
            scale_w = win_w
            scale_h = int(win_w / aspect_ratio)

        scaled_surf = pygame.transform.scale(internal_surf, (scale_w, scale_h))
        
        # Center the scaled surface on the actual screen
        gap_x = (win_w - scale_w) // 2
        gap_y = (win_h - scale_h) // 2
        
        screen.fill((0, 0, 0)) # Fill black bars
        screen.blit(scaled_surf, (gap_x, gap_y))

        pygame.display.flip()
        dt = clock.tick(60) / 1000

if __name__ == "__main__":
    main()

