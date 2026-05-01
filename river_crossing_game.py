from __future__ import annotations

import asyncio
import sys
import math
from array import array
from pathlib import Path
import pygame

WIDTH, HEIGHT = 1100, 620
FPS = 60

LEFT_BANK_X = 360
RIGHT_BANK_X = 900
RIVER_X = 630
BOAT_Y = 420
BOAT_WIDTH = 170
BOAT_HEIGHT = 54

BG_COLOR = (197, 232, 255)
RIVER_COLOR = (75, 145, 214)
BANK_COLOR = (136, 190, 110)
TEXT_COLOR = (35, 35, 35)
PANEL_COLOR = (248, 244, 232)
PANEL_BORDER = (70, 60, 50)
BUTTON_COLOR = (243, 196, 89)
BUTTON_HOVER = (251, 212, 120)
BUTTON_DISABLED = (176, 176, 176)
LOSS_COLOR = (208, 72, 58)
WIN_COLOR = (63, 166, 89)
BOAT_COLOR = (115, 75, 43)
BOAT_TRIM = (166, 121, 83)
BOAT_SHADOW = (81, 109, 156)
BOAT_SAIL = (244, 239, 221)
BOAT_POLE = (92, 66, 44)
SELECTED_COLOR = (255, 239, 138)
ASSET_DIR = Path(__file__).with_name("assets") / "river_crossing"

PEASANT = "Peasant"
WOLF = "Wolf"
SHEEP = "Sheep"
VEGETABLES = "Vegetables"
ENTITY_ORDER = [PEASANT, WOLF, SHEEP, VEGETABLES]
ENTITY_COLORS = {
    PEASANT: (247, 215, 148),
    WOLF: (125, 135, 154),
    SHEEP: (244, 244, 244),
    VEGETABLES: (121, 193, 89),
}
SPRITE_FILES = {
    PEASANT: "peasant.png",
    WOLF: "wolf.png",
    SHEEP: "sheep.png",
    VEGETABLES: "vegetables.png",
}


class RiverCrossingGame:
    def __init__(self) -> None:
        pygame.init()
        self.audio_enabled = True
        try:
            mixer = getattr(pygame, "mixer", None)
            if mixer is None:
                raise pygame.error("pygame mixer is unavailable")
            mixer.init(frequency=22050, size=-16, channels=1)
        except (AttributeError, pygame.error):
            self.audio_enabled = False
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("River Crossing Puzzle")
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("arial", 34, bold=True)
        self.overlay_title_font = pygame.font.SysFont("arial", 44, bold=True)
        self.body_font = pygame.font.SysFont("arial", 22)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.entity_sprites = self.load_sprites()
        self.sounds = self.build_sounds()
        self.reset()

    def reset(self) -> None:
        self.left_bank = []
        self.right_bank = ENTITY_ORDER.copy()
        self.boat_side = "right"
        self.boat_passengers = []
        self.moves = 0
        self.state = "playing"
        self.message = "Move everyone safely to the left bank."
        self.end_sound_played = False

    def bank_for_side(self, side: str) -> list[str]:
        return self.left_bank if side == "left" else self.right_bank

    def toggle_entity(self, entity: str) -> None:
        if self.state != "playing":
            return
        bank = self.bank_for_side(self.boat_side)
        if entity not in bank and entity not in self.boat_passengers:
            return
        if entity in self.boat_passengers:
            self.boat_passengers.remove(entity)
            bank.append(entity)
            bank.sort(key=ENTITY_ORDER.index)
            self.play_sound("click")
            return
        if len(self.boat_passengers) >= 2:
            self.message = "The boat can carry at most two."
            self.play_sound("error")
            return
        bank.remove(entity)
        self.boat_passengers.append(entity)
        self.boat_passengers.sort(key=ENTITY_ORDER.index)
        self.play_sound("click")

    def move_boat(self) -> None:
        if self.state != "playing":
            return
        if PEASANT not in self.boat_passengers:
            self.message = "The peasant must be on the boat."
            self.play_sound("error")
            return
        if not self.boat_passengers:
            self.message = "Choose at least one passenger."
            self.play_sound("error")
            return

        destination = "left" if self.boat_side == "right" else "right"
        dest_bank = self.bank_for_side(destination)
        dest_bank.extend(self.boat_passengers)
        dest_bank.sort(key=ENTITY_ORDER.index)
        self.boat_passengers.clear()
        self.boat_side = destination
        self.moves += 1
        self.play_sound("cross")
        self.evaluate_state()

    def evaluate_state(self) -> None:
        for bank_name, bank in (("left bank", self.left_bank), ("right bank", self.right_bank)):
            if PEASANT not in bank:
                if WOLF in bank and SHEEP in bank:
                    self.state = "lost"
                    self.message = f"The wolf ate the sheep on the {bank_name}."
                    return
                if SHEEP in bank and VEGETABLES in bank:
                    self.state = "lost"
                    self.message = f"The sheep ate the vegetables on the {bank_name}."
                    return

        if len(self.left_bank) == len(ENTITY_ORDER):
            self.state = "won"
            self.message = f"Puzzle solved in {self.moves} moves."
            self.play_sound("win")
            self.end_sound_played = True
        else:
            self.message = "Safe crossing so far. Plan the next trip."

    def build_tone_sound(self, notes: list[float], note_duration: float = 0.12, volume: float = 0.18, sample_rate: int = 22050) -> object | None:
        if not self.audio_enabled:
            return None
        mixer = getattr(pygame, "mixer", None)
        if mixer is None:
            self.audio_enabled = False
            return None
        samples = array("h")
        fade_samples = max(1, int(sample_rate * 0.02))

        for frequency in notes:
            total_samples = int(sample_rate * note_duration)
            for index in range(total_samples):
                t = index / sample_rate
                envelope = 1.0
                if index < fade_samples:
                    envelope = index / fade_samples
                elif index > total_samples - fade_samples:
                    envelope = max(0, (total_samples - index) / fade_samples)

                value = 0.0
                if frequency > 0:
                    value = math.sin(2 * math.pi * frequency * t)
                    value += 0.25 * math.sin(2 * math.pi * frequency * 1.5 * t)
                    value *= 0.6
                samples.append(int(32767 * volume * envelope * value))

        try:
            return mixer.Sound(buffer=samples.tobytes())
        except (AttributeError, pygame.error):
            self.audio_enabled = False
            return None

    def build_sounds(self) -> dict[str, object | None]:
        return {
            "click": self.build_tone_sound([660], note_duration=0.06, volume=0.12),
            "cross": self.build_tone_sound([392, 494], note_duration=0.08, volume=0.14),
            "win": self.build_tone_sound([523.25, 659.25, 783.99], note_duration=0.13, volume=0.18),
            "error": self.build_tone_sound([210, 170], note_duration=0.09, volume=0.16),
            "lose": self.build_tone_sound([392, 311.13, 220], note_duration=0.14, volume=0.2),
        }

    def play_sound(self, sound_name: str) -> None:
        sound = self.sounds.get(sound_name)
        if sound is not None and hasattr(sound, "play"):
            sound.play()

    def button_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(40, 270 + index * 58, 210, 50)

    def move_button_rect(self) -> pygame.Rect:
        return pygame.Rect(40, 500, 210, 56)

    def reset_button_rect(self) -> pygame.Rect:
        return pygame.Rect(40, 565, 210, 40)

    def entity_rect(self, entity: str, x: int, y: int) -> pygame.Rect:
        return pygame.Rect(x - 30, y - 30, 60, 60)

    def draw_text_center(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], rect: pygame.Rect) -> None:
        surface = font.render(text, True, color)
        self.screen.blit(surface, surface.get_rect(center=rect.center))

    def load_sprites(self) -> dict[str, pygame.Surface]:
        sprites: dict[str, pygame.Surface] = {}
        for entity, filename in SPRITE_FILES.items():
            sprite_path = ASSET_DIR / filename
            if sprite_path.exists():
                sprite = pygame.image.load(str(sprite_path)).convert_alpha()
                sprites[entity] = pygame.transform.smoothscale(sprite, (56, 56))
        return sprites

    def draw_scene(self) -> None:
        self.screen.fill(BG_COLOR)
        pygame.draw.rect(self.screen, BANK_COLOR, (280, 0, 260, HEIGHT))
        pygame.draw.rect(self.screen, RIVER_COLOR, (540, 0, 280, HEIGHT))
        pygame.draw.rect(self.screen, BANK_COLOR, (820, 0, 280, HEIGHT))

        panel = pygame.Rect(20, 20, 250, 580)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel, border_radius=14)
        pygame.draw.rect(self.screen, PANEL_BORDER, panel, 3, border_radius=14)

        title = self.title_font.render("River Crossing", True, TEXT_COLOR)
        self.screen.blit(title, (38, 35))

        status_color = TEXT_COLOR
        if self.state == "won":
            status_color = WIN_COLOR
        elif self.state == "lost":
            status_color = LOSS_COLOR

        msg_surface = self.small_font.render(self.message, True, status_color)
        self.screen.blit(msg_surface, (38, 86))

        move_surface = self.body_font.render(f"Moves: {self.moves}", True, TEXT_COLOR)
        self.screen.blit(move_surface, (38, 118))

        info_lines = [
            "Boat capacity: 2",
            "Peasant must ride the boat",
            "Wolf cannot stay with sheep",
            "Sheep cannot stay with vegetables",
        ]
        rules_title = self.small_font.render("Rules", True, TEXT_COLOR)
        self.screen.blit(rules_title, (38, 150))
        for i, line in enumerate(info_lines):
            line_surface = self.small_font.render(line, True, TEXT_COLOR)
            self.screen.blit(line_surface, (38, 176 + i * 20))

        self.draw_selection_buttons()
        self.draw_move_buttons()
        self.draw_banks()
        self.draw_boat()
        if self.state in {"lost", "won"}:
            self.draw_end_overlay()

    def draw_selection_buttons(self) -> None:
        boat_bank = self.bank_for_side(self.boat_side)
        mouse_pos = pygame.mouse.get_pos()

        for index, entity in enumerate(ENTITY_ORDER):
            rect = self.button_rect(index)
            available = entity in boat_bank or entity in self.boat_passengers
            base_color = BUTTON_COLOR
            if not available:
                base_color = BUTTON_DISABLED
            elif rect.collidepoint(mouse_pos):
                base_color = BUTTON_HOVER

            pygame.draw.rect(self.screen, base_color, rect, border_radius=12)
            pygame.draw.rect(self.screen, PANEL_BORDER, rect, 2, border_radius=12)

            if entity in self.boat_passengers:
                highlight = rect.inflate(-8, -8)
                pygame.draw.rect(self.screen, SELECTED_COLOR, highlight, border_radius=10)
                pygame.draw.rect(self.screen, PANEL_BORDER, highlight, 2, border_radius=10)

            sprite = self.entity_sprites.get(entity)
            if sprite is not None:
                self.screen.blit(sprite, (rect.x + 8, rect.centery - sprite.get_height() // 2))
                label_surface = self.body_font.render(entity, True, TEXT_COLOR)
                self.screen.blit(label_surface, (rect.x + 72, rect.centery - label_surface.get_height() // 2))
            else:
                self.draw_text_center(entity, self.body_font, TEXT_COLOR, rect)

    def draw_move_buttons(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        move_rect = self.move_button_rect()
        reset_rect = self.reset_button_rect()

        move_color = BUTTON_HOVER if move_rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(self.screen, move_color, move_rect, border_radius=12)
        pygame.draw.rect(self.screen, PANEL_BORDER, move_rect, 2, border_radius=12)
        move_text = "Cross to Left" if self.boat_side == "right" else "Cross to Right"
        self.draw_text_center(move_text, self.body_font, TEXT_COLOR, move_rect)

        reset_color = (223, 227, 234) if reset_rect.collidepoint(mouse_pos) else (205, 210, 219)
        pygame.draw.rect(self.screen, reset_color, reset_rect, border_radius=10)
        pygame.draw.rect(self.screen, PANEL_BORDER, reset_rect, 2, border_radius=10)
        self.draw_text_center("Restart", self.body_font, TEXT_COLOR, reset_rect)

    def draw_banks(self) -> None:
        left_title = self.body_font.render("Left Bank", True, TEXT_COLOR)
        right_title = self.body_font.render("Right Bank", True, TEXT_COLOR)
        self.screen.blit(left_title, (330, 28))
        self.screen.blit(right_title, (870, 28))

        left_positions = [(345, 180), (455, 180), (360, 285), (470, 285)]
        right_positions = [(885, 180), (995, 180), (900, 285), (1010, 285)]

        for entity, pos in zip(self.left_bank, left_positions):
            self.draw_entity(entity, pos[0], pos[1])
        for entity, pos in zip(self.right_bank, right_positions):
            self.draw_entity(entity, pos[0], pos[1])

    def draw_boat(self) -> None:
        boat_center_x = LEFT_BANK_X if self.boat_side == "left" else RIGHT_BANK_X
        shadow_rect = pygame.Rect(boat_center_x - 68, BOAT_Y + 34, 136, 18)
        pygame.draw.ellipse(self.screen, BOAT_SHADOW, shadow_rect)

        hull_points = [
            (boat_center_x - 86, BOAT_Y + 14),
            (boat_center_x - 64, BOAT_Y + 42),
            (boat_center_x + 64, BOAT_Y + 42),
            (boat_center_x + 86, BOAT_Y + 14),
            (boat_center_x + 52, BOAT_Y - 6),
            (boat_center_x - 52, BOAT_Y - 6),
        ]
        deck_rect = pygame.Rect(boat_center_x - 54, BOAT_Y - 2, 108, 18)
        cabin_rect = pygame.Rect(boat_center_x - 24, BOAT_Y - 34, 48, 24)

        pygame.draw.polygon(self.screen, BOAT_COLOR, hull_points)
        pygame.draw.polygon(self.screen, PANEL_BORDER, hull_points, 3)
        pygame.draw.rect(self.screen, BOAT_TRIM, deck_rect, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_BORDER, deck_rect, 2, border_radius=8)
        pygame.draw.rect(self.screen, BOAT_TRIM, cabin_rect, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_BORDER, cabin_rect, 2, border_radius=8)

        mast_top = (boat_center_x + 10, BOAT_Y - 72)
        mast_bottom = (boat_center_x + 10, BOAT_Y - 8)
        pygame.draw.line(self.screen, BOAT_POLE, mast_bottom, mast_top, 4)
        sail_points = [
            (boat_center_x + 10, BOAT_Y - 66),
            (boat_center_x + 10, BOAT_Y - 18),
            (boat_center_x - 34, BOAT_Y - 40),
        ]
        pygame.draw.polygon(self.screen, BOAT_SAIL, sail_points)
        pygame.draw.polygon(self.screen, PANEL_BORDER, sail_points, 2)

        passenger_positions = [(boat_center_x - 34, BOAT_Y - 20), (boat_center_x + 34, BOAT_Y - 20)]
        for entity, pos in zip(self.boat_passengers, passenger_positions):
            self.draw_entity(entity, pos[0], pos[1], on_boat=True)

        boat_label = self.small_font.render("Boat", True, TEXT_COLOR)
        self.screen.blit(boat_label, (boat_center_x - boat_label.get_width() // 2, BOAT_Y + 52))

    def draw_entity(self, entity: str, x: int, y: int, on_boat: bool = False) -> None:
        rect = self.entity_rect(entity, x, y)
        sprite = self.entity_sprites.get(entity)
        if sprite is not None:
            self.screen.blit(sprite, sprite.get_rect(center=rect.center))
        else:
            pygame.draw.ellipse(self.screen, ENTITY_COLORS[entity], rect)
            pygame.draw.ellipse(self.screen, PANEL_BORDER, rect, 2)
            icon_center = rect.center

            if entity == PEASANT:
                self.draw_peasant_icon(icon_center)
            elif entity == WOLF:
                self.draw_wolf_icon(icon_center)
            elif entity == SHEEP:
                self.draw_sheep_icon(icon_center)
            elif entity == VEGETABLES:
                self.draw_vegetable_icon(icon_center)

        if on_boat:
            name_surface = self.small_font.render(entity, True, TEXT_COLOR)
            self.screen.blit(name_surface, (x - name_surface.get_width() // 2, y - 48))

    def draw_peasant_icon(self, center: tuple[int, int]) -> None:
        x, y = center
        pygame.draw.circle(self.screen, (241, 201, 160), (x, y - 10), 9)
        pygame.draw.line(self.screen, PANEL_BORDER, (x, y), (x, y + 16), 3)
        pygame.draw.line(self.screen, PANEL_BORDER, (x - 11, y + 5), (x + 11, y + 5), 3)
        pygame.draw.line(self.screen, PANEL_BORDER, (x, y + 16), (x - 10, y + 27), 3)
        pygame.draw.line(self.screen, PANEL_BORDER, (x, y + 16), (x + 10, y + 27), 3)

    def draw_wolf_icon(self, center: tuple[int, int]) -> None:
        x, y = center
        points = [
            (x - 16, y + 10),
            (x - 18, y - 4),
            (x - 10, y - 18),
            (x - 2, y - 8),
            (x + 2, y - 18),
            (x + 10, y - 4),
            (x + 18, y + 10),
            (x + 8, y + 18),
            (x - 8, y + 18),
        ]
        pygame.draw.polygon(self.screen, (95, 104, 120), points)
        pygame.draw.polygon(self.screen, PANEL_BORDER, points, 2)
        pygame.draw.circle(self.screen, TEXT_COLOR, (x - 6, y + 2), 2)
        pygame.draw.circle(self.screen, TEXT_COLOR, (x + 6, y + 2), 2)
        pygame.draw.polygon(self.screen, TEXT_COLOR, [(x, y + 7), (x - 4, y + 13), (x + 4, y + 13)])

    def draw_sheep_icon(self, center: tuple[int, int]) -> None:
        x, y = center
        fluff_centers = [
            (x - 12, y + 2),
            (x - 4, y - 7),
            (x + 8, y - 5),
            (x + 14, y + 5),
            (x - 2, y + 10),
        ]
        for fx, fy in fluff_centers:
            pygame.draw.circle(self.screen, (250, 250, 250), (fx, fy), 10)
            pygame.draw.circle(self.screen, PANEL_BORDER, (fx, fy), 10, 1)
        pygame.draw.ellipse(self.screen, (73, 73, 73), (x + 6, y + 6, 14, 12))
        pygame.draw.circle(self.screen, TEXT_COLOR, (x + 16, y + 11), 1)

    def draw_vegetable_icon(self, center: tuple[int, int]) -> None:
        x, y = center
        leaf_color = (82, 145, 63)
        leaf_points = [
            [(x, y - 16), (x - 10, y - 2), (x, y + 12), (x + 10, y - 2)],
            [(x - 12, y - 8), (x - 20, y + 5), (x - 8, y + 18), (x, y + 4)],
            [(x + 12, y - 8), (x + 20, y + 5), (x + 8, y + 18), (x, y + 4)],
        ]
        for points in leaf_points:
            pygame.draw.polygon(self.screen, leaf_color, points)
            pygame.draw.polygon(self.screen, PANEL_BORDER, points, 2)
        pygame.draw.circle(self.screen, (119, 176, 83), (x, y + 4), 8)

    def draw_end_overlay(self) -> None:
        if self.state == "lost" and not self.end_sound_played:
            self.play_sound("lose")
            self.end_sound_played = True

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 20, 28, 120))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(340, 180, 420, 190)
        accent_color = LOSS_COLOR if self.state == "lost" else WIN_COLOR
        title_text = "Game Over" if self.state == "lost" else "You Win"

        pygame.draw.rect(self.screen, PANEL_COLOR, card, border_radius=18)
        pygame.draw.rect(self.screen, accent_color, card, 5, border_radius=18)

        title_surface = self.overlay_title_font.render(title_text, True, accent_color)
        self.screen.blit(title_surface, title_surface.get_rect(center=(card.centerx, card.y + 46)))

        message_surface = self.body_font.render(self.message, True, TEXT_COLOR)
        self.screen.blit(message_surface, message_surface.get_rect(center=(card.centerx, card.y + 102)))

        hint_surface = self.small_font.render("Press R or click Restart to play again.", True, TEXT_COLOR)
        self.screen.blit(hint_surface, hint_surface.get_rect(center=(card.centerx, card.y + 148)))

    def handle_click(self, pos: tuple[int, int]) -> None:
        if self.move_button_rect().collidepoint(pos):
            self.play_sound("click")
            self.move_boat()
            return
        if self.reset_button_rect().collidepoint(pos):
            self.play_sound("click")
            self.reset()
            return
        for index, entity in enumerate(ENTITY_ORDER):
            if self.button_rect(index).collidepoint(pos):
                self.toggle_entity(entity)
                return

    def process_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                if event.key == pygame.K_SPACE:
                    self.move_boat()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_click(event.pos)
        return True

    def draw_frame(self) -> None:
        self.draw_scene()
        pygame.display.flip()

    def run(self) -> None:
        running = True
        while running:
            running = self.process_events()
            self.draw_frame()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    async def run_web(self) -> None:
        running = True
        while running:
            running = self.process_events()
            self.draw_frame()
            self.clock.tick(FPS)
            await asyncio.sleep(0)

        pygame.quit()


async def main():
    game = RiverCrossingGame()
    await game.run_web()


if __name__ == "__main__":
    import sys

    if sys.platform == "emscripten":
        import asyncio
        asyncio.run(main())
    else:
        RiverCrossingGame().run()
