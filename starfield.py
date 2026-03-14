import pygame
import random
from constants import SCREEN_WIDTH, SCREEN_HEIGHT

class Starfield:
    def __init__(self, num_stars=150):
        # Create a transparent surface the size of the screen
        self.surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.surface.fill("black")
        
        for _ in range(num_stars):
            # Pick a random spot
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            
            # Random size (1 to 3 pixels) and brightness
            size = random.randint(1, 2)
            color_val = random.randint(150, 255) # Varied white/grey
            color = (color_val, color_val, color_val)
            
            pygame.draw.circle(self.surface, color, (x, y), size)

    def draw(self, screen):
        # "Stamp" the star surface onto the main screen
        screen.blit(self.surface, (0, 0))

