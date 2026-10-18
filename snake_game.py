"""لعبة الثعبان (Snake) باستخدام pygame.

كُل التفاح لتكبر واحصل على نقاط، وتجنب الاصطدام بالجدران أو بجسمك.
الأسهم (أو W/A/S/D) للحركة، P للإيقاف المؤقت، R لإعادة اللعب، Esc للخروج.
"""

import os
import random
import sys

import pygame

CELL = 24
COLS, ROWS = 25, 25
HUD_H = 50
WIDTH, HEIGHT = COLS * CELL, ROWS * CELL + HUD_H
FPS = 60

START_STEP_MS = 140
MIN_STEP_MS = 60

BG_DARK = (30, 120, 50)
BG_LIGHT = (38, 135, 58)
HUD_BG = (20, 30, 25)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SNAKE_HEAD = (40, 70, 200)
SNAKE_BODY = (70, 110, 235)
APPLE = (220, 30, 40)
LEAF = (40, 160, 40)

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
KEY_DIRS = {
    pygame.K_UP: UP, pygame.K_w: UP,
    pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
    pygame.K_LEFT: LEFT, pygame.K_a: LEFT,
    pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT,
}

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snake_highscore.txt")


def cell_rect(pos):
    x, y = pos
    return pygame.Rect(x * CELL, HUD_H + y * CELL, CELL, CELL)


class Snake:
    def __init__(self):
        cx, cy = COLS // 2, ROWS // 2
        self.body = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = RIGHT
        # قائمة انتظار للاتجاهات حتى لا تضيع الضغطات السريعة بين خطوتين
        self.pending = []
        self.grow = 0

    @property
    def head(self):
        return self.body[0]

    def turn(self, new_dir):
        last = self.pending[-1] if self.pending else self.direction
        if new_dir != last and (new_dir[0] + last[0], new_dir[1] + last[1]) != (0, 0):
            if len(self.pending) < 3:
                self.pending.append(new_dir)

    def step(self):
        if self.pending:
            self.direction = self.pending.pop(0)
        x, y = self.head
        new_head = (x + self.direction[0], y + self.direction[1])
        self.body.insert(0, new_head)
        if self.grow > 0:
            self.grow -= 1
        else:
            self.body.pop()

    def hit_self_or_wall(self):
        x, y = self.head
        if not (0 <= x < COLS and 0 <= y < ROWS):
            return True
        return self.head in self.body[1:]

    def draw(self, surface):
        for i, pos in reversed(list(enumerate(self.body))):
            rect = cell_rect(pos).inflate(-2, -2)
            color = SNAKE_HEAD if i == 0 else SNAKE_BODY
            pygame.draw.rect(surface, color, rect, border_radius=7)
        # العيون
        hx, hy = cell_rect(self.head).center
        dx, dy = self.direction
        px, py = -dy, dx  # عمودي على الاتجاه
        for side in (-1, 1):
            ex = hx + dx * 5 + px * 5 * side
            ey = hy + dy * 5 + py * 5 * side
            pygame.draw.circle(surface, WHITE, (ex, ey), 4)
            pygame.draw.circle(surface, BLACK, (ex + dx, ey + dy), 2)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("لعبة الثعبان - Snake Game")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 26, bold=True)
        self.big_font = pygame.font.SysFont("arial", 52, bold=True)
        self.high_score = self.load_high_score()
        self.background = self.build_background()
        self.reset()

    def reset(self):
        self.snake = Snake()
        self.score = 0
        self.step_ms = START_STEP_MS
        self.step_timer = 0
        self.apple = self.random_free_cell()
        self.paused = False
        self.game_over = False

    @staticmethod
    def load_high_score():
        try:
            with open(HIGHSCORE_FILE) as f:
                return int(f.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def save_high_score(self):
        try:
            with open(HIGHSCORE_FILE, "w") as f:
                f.write(str(self.high_score))
        except OSError:
            pass

    @staticmethod
    def build_background():
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.fill(HUD_BG)
        for y in range(ROWS):
            for x in range(COLS):
                color = BG_LIGHT if (x + y) % 2 else BG_DARK
                pygame.draw.rect(surf, color, cell_rect((x, y)))
        return surf

    def random_free_cell(self):
        occupied = set(self.snake.body)
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in occupied]
        return random.choice(free) if free else None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()
                elif event.key == pygame.K_p and not self.game_over:
                    self.paused = not self.paused
                elif event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN) and self.game_over:
                    self.reset()
                elif event.key in KEY_DIRS and not self.paused and not self.game_over:
                    self.snake.turn(KEY_DIRS[event.key])

    def update(self, dt):
        if self.paused or self.game_over:
            return

        self.step_timer += dt
        while self.step_timer >= self.step_ms and not self.game_over:
            self.step_timer -= self.step_ms
            self.tick()

    def tick(self):
        self.snake.step()
        if self.snake.hit_self_or_wall():
            self.end_game()
            return

        if self.snake.head == self.apple:
            self.score += 1
            self.snake.grow += 1
            # زيادة السرعة تدريجياً
            self.step_ms = max(MIN_STEP_MS, START_STEP_MS - self.score * 3)
            self.apple = self.random_free_cell()
            if self.apple is None:  # ملأ الثعبان الشاشة كلها
                self.end_game()

    def end_game(self):
        self.game_over = True
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

    def draw_apple(self):
        if self.apple is None:
            return
        rect = cell_rect(self.apple)
        pygame.draw.circle(self.screen, APPLE, (rect.centerx, rect.centery + 1), CELL // 2 - 3)
        pygame.draw.ellipse(self.screen, LEAF, (rect.centerx, rect.y + 1, 8, 5))

    def draw_text_center(self, text, font, y, color=WHITE):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=(WIDTH // 2, y)))

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        self.draw_apple()
        self.snake.draw(self.screen)

        self.screen.blit(self.font.render(f"Score: {self.score}", True, WHITE), (10, 10))
        best = self.font.render(f"Best: {self.high_score}", True, WHITE)
        self.screen.blit(best, (WIDTH - best.get_width() - 10, 10))

        if self.paused or self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
            if self.paused:
                self.draw_text_center("PAUSED", self.big_font, HEIGHT // 2)
                self.draw_text_center("Press P to continue", self.font, HEIGHT // 2 + 50)
            else:
                self.draw_text_center("GAME OVER", self.big_font, HEIGHT // 2 - 40, (255, 80, 80))
                self.draw_text_center(f"Score: {self.score}", self.font, HEIGHT // 2 + 20)
                self.draw_text_center("Press R to play again", self.font, HEIGHT // 2 + 60)

        pygame.display.flip()

    def quit(self):
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
