import math
import pygame

class Obstacle:
    def __init__(self, x, ground_y, speed, width=25, height=40):
        self.x = x
        self.prev_x = x  # where the obstacle was before its last move
        self.width = width
        self.height = height
        self.y = ground_y - height
        self.speed = speed
        self.scored = False

    def move(self):
        self.prev_x = self.x
        self.x -= self.speed

    def off_screen(self):
        return self.x + self.width < 0

    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def swept_rect(self):
        """Rect covering every x position the obstacle occupied this frame
        (from prev_x to x), so a fast obstacle can't skip over the player."""
        left = math.floor(min(self.x, self.prev_x))
        right = math.ceil(max(self.x, self.prev_x) + self.width)
        return pygame.Rect(left, self.y, right - left, self.height)
