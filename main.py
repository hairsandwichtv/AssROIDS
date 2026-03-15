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
    
    # WSL Audio Fail-safe
    audio_enabled = True
    try:
        pygame.mixer.init()
    except pygame.error:
        print("Warning: No audio device found. Running in silent mode.")
        audio_enabled = False

    # FIX: Set caption BEFORE set_mode to help WSLg decorations
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

    # Use internal resolution (1280x720) for positioning
    start_btn = Button(int(1280 * 0.10), 570, "Blast Off Button.png", 0.5)
    exit_btn = Button(int(1280 * 0.90), 570, "Exit Button.png", 0.5)
    stars = Starfield(1280, 720, 200)

    state = "MENU"
    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # Update physical window size variable
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

        # 1. Update/Draw to Internal Surface (Always 1280x720)
        internal_surf.fill("black")

        if state == "MENU":
            internal_surf.blit(menu_bg, (0, 0))
            # We pass is_internal=True to remap mouse coords in button.py
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

        # 2. Scale Internal Surface to Window (Letterboxing)
        win_w, win_h = screen.get_size()
        target_ratio = 1280 / 720
        
        if win_w / win_h > target_ratio:
            scale_h = win_h
            scale_w = int(win_h * target_ratio)
        else:
            scale_w = win_w
            scale_h = int(win_w / target_ratio)

        scaled_view = pygame.transform.scale(internal_surf, (scale_w, scale_h))
        
        # Center the view
        offset_x = (win_w - scale_w) // 2
        offset_y = (win_h - scale_h) // 2
        
        screen.fill("black")
        screen.blit(scaled_view, (offset_x, offset_y))

        pygame.display.flip()
        dt = clock.tick(60) / 1000

if __name__ == "__main__":
    main()

