import math
from array import array

import pygame
from .player import Player
from .obstacle import Obstacle

# Game Engine

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 40, 40)
BROWN = (120, 80, 40)
DARK_GREEN = (30, 100, 30)

# Task 1: speed ceiling so the game stays fair and reactable.
# Must stay well below player width + obstacle width (55 px per frame).
MAX_SPEED = 14

# Task 2: frames to ignore key presses after dying (30 frames = 0.5 s at 60 FPS),
# so a jump key still being mashed doesn't instantly pick a menu option.
GAME_OVER_INPUT_DELAY = 30

# Task 3: difficulty -> (starting speed, frames between obstacle spawns).
# Higher speed and a smaller interval make the game harder.
DIFFICULTIES = {
    "Easy": (5, 90),
    "Medium": (6, 70),
    "Hard": (8, 55),
}

# Task 3: menu keys that start a new game.
DIFFICULTY_KEYS = {
    pygame.K_1: "Easy",
    pygame.K_2: "Medium",
    pygame.K_3: "Hard",
}


def make_sound(frequencies, ms_per_note=100, volume=0.3):
    """Task 4: build a simple beep sound from a list of note frequencies (Hz).

    Each note is a sine wave that fades out, played one after another.
    Returns None if the audio mixer isn't available, so the game still runs.
    """
    mixer_settings = pygame.mixer.get_init()
    if mixer_settings is None:
        return None
    sample_rate, sample_format, channels = mixer_settings
    if sample_format != -16:  # this helper only builds 16-bit signed audio
        return None

    samples = array("h")  # "h" = signed 16-bit integers
    samples_per_note = int(sample_rate * ms_per_note / 1000)
    for freq in frequencies:
        for i in range(samples_per_note):
            fade = 1 - i / samples_per_note  # fade out to avoid clicks
            wave = math.sin(2 * math.pi * freq * i / sample_rate)
            value = int(32767 * volume * fade * wave)
            for _ in range(channels):  # same value in every channel
                samples.append(value)

    return pygame.mixer.Sound(buffer=samples.tobytes())


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ground_y = height - 40

        self.speed_increase_per_frame = 0.003

        self.font = pygame.font.SysFont("Arial", 30)
        self.big_font = pygame.font.SysFont("Arial", 64, bold=True)  # Task 2

        # Task 4: sound effects, created once.
        self.jump_sound = make_sound([400, 650], ms_per_note=60)
        self.score_sound = make_sound([880, 1320], ms_per_note=70)
        self.game_over_sound = make_sound([400, 300, 200], ms_per_note=200)

        # Task 3: the setup that used to live here is now in start_game(),
        # so it can be repeated for every replay. First game is Medium.
        self.start_game("Medium")

    def play_sound(self, sound):
        """Task 4: play a sound if it exists (it is None when there's no audio)."""
        if sound is not None:
            sound.play()

    def start_game(self, difficulty):
        """Task 3: (re)set all game state for a new run at the given difficulty."""
        start_speed, spawn_interval = DIFFICULTIES[difficulty]

        self.difficulty = difficulty
        self.player = Player(80, self.ground_y)

        self.speed = start_speed
        self.spawn_interval = spawn_interval  # frames between obstacle spawns
        self._spawn_timer = 0
        self.obstacles = []

        self.distance = 0
        self.score = 0
        self.game_over = False
        self.game_over_frames = 0  # Task 2: frames since the player died

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        # Task 3: on the game-over screen, keys choose a difficulty or exit.
        if self.game_over:
            if self.game_over_frames >= GAME_OVER_INPUT_DELAY:
                if event.key in DIFFICULTY_KEYS:
                    self.start_game(DIFFICULTY_KEYS[event.key])
                elif event.key == pygame.K_ESCAPE:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            return

        if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
            # Task 4: only play the sound if the jump will actually happen.
            if self.player.on_ground:
                self.play_sound(self.jump_sound)
            self.player.jump()

    def handle_input(self):
        # Reserved for continuously-held-key input; this runner only
        # needs an edge-triggered jump, handled in handle_event.
        pass

    def update(self):
        if self.game_over:
            self.game_over_frames += 1  # Task 2: drives the input delay
            return

        # Task 1: speed still ramps up, but never past MAX_SPEED.
        self.speed = min(self.speed + self.speed_increase_per_frame, MAX_SPEED)
        self.player.update()

        self._spawn_timer += 1
        if self._spawn_timer >= self.spawn_interval:
            self._spawn_timer = 0
            self.obstacles.append(Obstacle(self.width, self.ground_y, self.speed))

        for obstacle in self.obstacles:
            obstacle.move()
            obstacle.speed = self.speed

        # Task 1: check the obstacle's whole path this frame (swept_rect),
        # not just its final position, so no speed can skip the hitbox.
        for obstacle in self.obstacles:
            if obstacle.swept_rect().colliderect(self.player.rect()):
                self.game_over = True
                self.play_sound(self.game_over_sound)  # Task 4
                return

        for obstacle in self.obstacles:
            if not obstacle.scored and obstacle.x + obstacle.width < self.player.x:
                obstacle.scored = True
                self.score += 1
                self.play_sound(self.score_sound)  # Task 4

        self.obstacles = [o for o in self.obstacles if not o.off_screen()]

        self.distance += self.speed

    def render(self, screen):
        pygame.draw.line(screen, BROWN, (0, self.ground_y), (self.width, self.ground_y), 4)

        pygame.draw.rect(screen, WHITE, self.player.rect())
        for obstacle in self.obstacles:
            pygame.draw.rect(screen, DARK_GREEN, obstacle.rect())

        score_text = self.font.render(f"Score: {self.score}", True, BLACK)
        screen.blit(score_text, (10, 10))

        # Task 2: draw the game-over screen on top of the frozen scene.
        if self.game_over:
            self._render_game_over(screen)

    def _render_game_over(self, screen):
        # Dim the frozen scene with a semi-transparent black overlay.
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(150)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))

        title = self.big_font.render("GAME OVER", True, RED)
        screen.blit(title, title.get_rect(center=(self.width // 2, 70)))

        final = self.font.render(f"Final Score: {self.score}", True, WHITE)
        screen.blit(final, final.get_rect(center=(self.width // 2, 135)))

        # Task 3: replay menu, shown only once input is actually accepted.
        if self.game_over_frames >= GAME_OVER_INPUT_DELAY:
            options = [
                "Play again:",
                "1 - Easy    2 - Medium    3 - Hard",
                "Esc - Exit",
            ]
            y = 205
            for line in options:
                text = self.font.render(line, True, WHITE)
                screen.blit(text, text.get_rect(center=(self.width // 2, y)))
                y += 45
