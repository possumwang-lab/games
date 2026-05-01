import pygame
import asyncio
import sys

pygame.init()

WIDTH, HEIGHT = 640, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Minimal Web Game")

clock = pygame.time.Clock()

# Simple player
x, y = 300, 220
speed = 200  # pixels per second

async def main():
    global x, y

    while True:
        dt = clock.tick(60) / 1000  # delta time (seconds)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            x -= speed * dt
        if keys[pygame.K_RIGHT]:
            x += speed * dt
        if keys[pygame.K_UP]:
            y -= speed * dt
        if keys[pygame.K_DOWN]:
            y += speed * dt

        # Draw
        screen.fill((30, 30, 30))
        pygame.draw.rect(screen, (0, 200, 255), (x, y, 40, 40))

        pygame.display.flip()

        # 🔑 CRITICAL for web
        await asyncio.sleep(0)

# 🔑 REQUIRED ENTRY POINT FOR PYGBAG
asyncio.run(main())