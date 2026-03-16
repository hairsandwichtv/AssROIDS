import pygame
from asset_helper import asset_path

class Button:
    def __init__(self, x, y, image_path, scale):
        img = pygame.image.load(image_path).convert_alpha()
        width = int(img.get_width() * scale)
        height = int(img.get_height() * scale)
        self.image = pygame.transform.scale(img, (width, height))
        self.rect = self.image.get_rect(center=(x, y))
        self.clicked = False
        self.hovered = False

    def draw(self, surface, tick_sound, is_internal=False, target_res=None):
        action = False
        # Get raw mouse position from the window
        mouse_pos = pygame.mouse.get_pos()
        
        # REMAP MOUSE: If drawing to an internal surface, adjust mouse coords
        if is_internal and target_res:
            win_w, win_h = pygame.display.get_surface().get_size()
            aspect = target_res[0] / target_res[1]
            
            # Calculate the same scale/offsets used in main.py
            if win_w / win_h > aspect:
                scale = win_h / target_res[1]
                offset_x = (win_w - target_res[0] * scale) / 2
                offset_y = 0
            else:
                scale = win_w / target_res[0]
                offset_x = 0
                offset_y = (win_h - target_res[1] * scale) / 2
                
            # Convert window mouse to internal coordinate space
            adj_x = (mouse_pos[0] - offset_x) / scale
            adj_y = (mouse_pos[1] - offset_y) / scale
            final_mouse_pos = (adj_x, adj_y)
        else:
            final_mouse_pos = mouse_pos

        if self.rect.collidepoint(final_mouse_pos):
            if not self.hovered and tick_sound:
                tick_sound.play()
                self.hovered = True
            
            surface.blit(self.image, (self.rect.x + 2, self.rect.y + 2))
            if pygame.mouse.get_pressed()[0] == 1 and not self.clicked:
                self.clicked = True
                action = True
        else:
            self.hovered = False
            surface.blit(self.image, (self.rect.x, self.rect.y))

        if pygame.mouse.get_pressed()[0] == 0:
            self.clicked = False

        return action

