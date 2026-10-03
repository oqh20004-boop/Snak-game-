"""لعبة سيارات بسيطة باستخدام pygame.

تحكم بالسيارة الحمراء وتفادى السيارات القادمة.
الأسهم (أو A/D/W/S) للحركة، P للإيقاف المؤقت، R لإعادة اللعب، Esc للخروج.
"""

import os
import random
import sys

import pygame

WIDTH, HEIGHT = 480, 720
FPS = 60

ROAD_LEFT, ROAD_RIGHT = 60, WIDTH - 60
LANES = 4
LANE_WIDTH = (ROAD_RIGHT - ROAD_LEFT) // LANES

CAR_W, CAR_H = 50, 90

GRASS = (34, 139, 34)
ROAD = (50, 50, 55)
LINE = (240, 240, 240)
EDGE = (230, 200, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PLAYER_COLOR = (220, 30, 40)
ENEMY_COLORS = [(30, 110, 220), (250, 160, 20), (140, 60, 200), (20, 180, 160), (230, 230, 230)]

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")


def lane_center(lane):
    return ROAD_LEFT + lane * LANE_WIDTH + LANE_WIDTH // 2


def draw_car(surface, rect, color, facing_up=True):
    """رسم سيارة باستخدام الأشكال فقط (بدون صور)."""
    # العجلات
    wheel_w, wheel_h = 8, 20
    for dx in (-wheel_w + 2, rect.width - 2):
        for dy in (12, rect.height - 12 - wheel_h):
            pygame.draw.rect(surface, BLACK, (rect.x + dx, rect.y + dy, wheel_w, wheel_h), border_radius=3)
    # الهيكل
    pygame.draw.rect(surface, color, rect, border_radius=12)
    # الزجاج
    glass = (170, 220, 255)
    front_y = rect.y + 18 if facing_up else rect.bottom - 18 - 16
    back_y = rect.bottom - 18 - 12 if facing_up else rect.y + 18
    pygame.draw.rect(surface, glass, (rect.x + 8, front_y, rect.width - 16, 16), border_radius=4)
    pygame.draw.rect(surface, glass, (rect.x + 10, back_y, rect.width - 20, 12), border_radius=4)
    # المصابيح
    lights_y = rect.y + 2 if facing_up else rect.bottom - 7
    light_color = (255, 255, 180) if facing_up else (255, 60, 60)
    pygame.draw.rect(surface, light_color, (rect.x + 6, lights_y, 10, 5), border_radius=2)
    pygame.draw.rect(surface, light_color, (rect.right - 16, lights_y, 10, 5), border_radius=2)


class Player:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, CAR_W, CAR_H)
        self.rect.midbottom = (WIDTH // 2, HEIGHT - 30)
        self.speed = 6

    def update(self, keys):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        self.rect.x += dx * self.speed
        self.rect.y += dy * self.speed
        self.rect.left = max(self.rect.left, ROAD_LEFT + 4)
        self.rect.right = min(self.rect.right, ROAD_RIGHT - 4)
        self.rect.top = max(self.rect.top, HEIGHT // 3)
        self.rect.bottom = min(self.rect.bottom, HEIGHT - 10)

    def draw(self, surface):
        draw_car(surface, self.rect, PLAYER_COLOR, facing_up=True)


class Enemy:
    def __init__(self, lane, extra_speed):
        self.rect = pygame.Rect(0, 0, CAR_W, CAR_H)
        self.rect.midbottom = (lane_center(lane), -10)
        self.color = random.choice(ENEMY_COLORS)
        self.extra_speed = extra_speed
        self.passed = False

    def update(self, road_speed):
        self.rect.y += road_speed + self.extra_speed

    def draw(self, surface):
        draw_car(surface, self.rect, self.color, facing_up=False)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("لعبة السيارات - Car Game")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 26, bold=True)
        self.big_font = pygame.font.SysFont("arial", 52, bold=True)
        self.high_score = self.load_high_score()
        self.reset()

    def reset(self):
        self.player = Player()
        self.enemies = []
        self.score = 0
        self.road_speed = 5.0
        self.line_offset = 0.0
        self.spawn_timer = 0
        self.spawn_delay = 60
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

    def spawn_enemy(self):
        # تجنب وضع سيارة في حارة لا تزال قريبة من أعلى الشاشة
        busy = {e.rect.centerx for e in self.enemies if e.rect.top < CAR_H * 1.5}
        free = [lane for lane in range(LANES) if lane_center(lane) not in busy]
        if free:
            lane = random.choice(free)
            self.enemies.append(Enemy(lane, random.uniform(0, 2.5)))

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

    def update(self):
        if self.paused or self.game_over:
            return

        self.player.update(pygame.key.get_pressed())

        # زيادة الصعوبة تدريجياً
        self.road_speed = min(5.0 + self.score * 0.08, 16.0)
        self.spawn_delay = max(18, 60 - self.score)
        self.line_offset = (self.line_offset + self.road_speed) % 80

        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_delay:
            self.spawn_timer = 0
            self.spawn_enemy()

        for enemy in self.enemies:
            enemy.update(self.road_speed)
            if not enemy.passed and enemy.rect.top > self.player.rect.bottom:
                enemy.passed = True
                self.score += 1
        self.enemies = [e for e in self.enemies if e.rect.top < HEIGHT]

        hitbox = self.player.rect.inflate(-8, -8)
        if any(hitbox.colliderect(e.rect.inflate(-8, -8)) for e in self.enemies):
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()

    def draw_road(self):
        self.screen.fill(GRASS)
        pygame.draw.rect(self.screen, ROAD, (ROAD_LEFT, 0, ROAD_RIGHT - ROAD_LEFT, HEIGHT))
        pygame.draw.rect(self.screen, EDGE, (ROAD_LEFT - 6, 0, 6, HEIGHT))
        pygame.draw.rect(self.screen, EDGE, (ROAD_RIGHT, 0, 6, HEIGHT))
        for lane in range(1, LANES):
            x = ROAD_LEFT + lane * LANE_WIDTH - 3
            y = -80 + self.line_offset
            while y < HEIGHT:
                pygame.draw.rect(self.screen, LINE, (x, y, 6, 40))
                y += 80

    def draw_text_center(self, text, font, y, color=WHITE):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=(WIDTH // 2, y)))

    def draw(self):
        self.draw_road()
        for enemy in self.enemies:
            enemy.draw(self.screen)
        self.player.draw(self.screen)

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
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
