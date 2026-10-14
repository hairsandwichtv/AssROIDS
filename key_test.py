"""
Quick standalone keyboard diagnostic — checks whether Alt+Space reaches the game.
Run with: uv run key_test.py   (close the window or press Esc to quit)
"""
import pygame
import sys
from win_keymenu import block_alt_menu, _hooked

pygame.init()
screen = pygame.display.set_mode((500, 200))
pygame.display.set_caption("Key Test")
block_alt_menu()

print(f"pygame version: {pygame.version.ver}")
print(f"SDL version: {pygame.version.SDL}")
print(f"Alt-menu hook installed: {bool(_hooked)}")
print("\nHold LEFT ALT, then tap SPACE a few times. Esc to quit.\n")

clock = pygame.time.Clock()
last_state = None
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
        if event.type == pygame.WINDOWFOCUSLOST:
            print("  !! window LOST focus")
        if event.type == pygame.WINDOWFOCUSGAINED:
            print("  window gained focus")
        if event.type in (pygame.KEYDOWN, pygame.KEYUP):
            kind = "DOWN" if event.type == pygame.KEYDOWN else "up  "
            print(f"  key {kind}  {pygame.key.name(event.key)!r:14} mods={event.mod:#06x}")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                sys.exit()
    keys  = pygame.key.get_pressed()
    state = (keys[pygame.K_LALT], keys[pygame.K_SPACE])
    if state != last_state:
        print(f"  held -> left alt: {state[0]}   space: {state[1]}")
        last_state = state
    clock.tick(60)
