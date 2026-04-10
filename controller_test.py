"""
Quick standalone controller diagnostic.
Run with: uv run controller_test.py
"""
import pygame
import sys

pygame.init()
pygame.joystick.init()

print(f"pygame version: {pygame.version.ver}")
print(f"SDL version: {pygame.version.SDL}")
print(f"Joysticks detected: {pygame.joystick.get_count()}")

if pygame.joystick.get_count() == 0:
    print("\nNo controllers found.")
    print("Try:")
    print("  1. Unplug and replug the controller")
    print("  2. Check it works in another app")
    print("  3. Run: python controller_test.py  (without uv)")
else:
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        print(f"\nController {i}: {j.get_name()}")
        print(f"  Axes:    {j.get_numaxes()}")
        print(f"  Buttons: {j.get_numbuttons()}")
        print(f"  Hats:    {j.get_numhats()}")
        print("\nPress buttons/move sticks for 5 seconds...")
        clock = pygame.time.Clock()
        screen = pygame.display.set_mode((400, 200))
        pygame.display.set_caption("Controller Test")
        import time
        start = time.time()
        while time.time() - start < 5:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                if event.type == pygame.JOYBUTTONDOWN:
                    print(f"  Button {event.button} pressed")
                if event.type == pygame.JOYAXISMOTION:
                    if abs(event.value) > 0.2:
                        print(f"  Axis {event.axis} = {event.value:.2f}")
                if event.type == pygame.JOYHATMOTION:
                    print(f"  Hat {event.hat} = {event.value}")
            clock.tick(30)

pygame.quit()
print("\nDone.")
