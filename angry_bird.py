import pygame
import pymunk
import pymunk.pygame_util
import math
import random
from array import array

pygame.init()
audio_enabled = True
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1)
except pygame.error:
    audio_enabled = False

WIDTH, HEIGHT = 900, 600
BIRD_START = (150, 500)
BLOCK_SIZE = 40
MAX_DRAG_DISTANCE = 100
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

space = pymunk.Space()
space.gravity = (0, 700)

draw_options = pymunk.pygame_util.DrawOptions(screen)

# Ground
static_body = space.static_body
ground = pymunk.Segment(static_body, (0, 550), (900, 550), 5)
ground.elasticity = 0.9
ground.friction = 0.2
ground.collision_type = 3
space.add(ground)

score = 0
MAX_LEVEL = 10
current_level = 1
lives = 3
explosions = []
last_block_collision_time = None
last_bounce_sound_time = 0
shot_blocks_destroyed = 0
blocks = []

font = pygame.font.SysFont("Arial", 24)

def build_tone_sound(notes, note_duration=0.25, volume=0.18, sample_rate=22050):
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
                value += 0.35 * math.sin(2 * math.pi * frequency * 0.5 * t)
                value *= 0.5
            samples.append(int(32767 * volume * envelope * value))

    return pygame.mixer.Sound(buffer=samples.tobytes())

def build_explosion_sound(duration=0.35, volume=0.45, sample_rate=22050):
    samples = array("h")
    total_samples = int(sample_rate * duration)

    for index in range(total_samples):
        progress = index / total_samples
        envelope = (1.0 - progress) ** 2
        noise = random.uniform(-1.0, 1.0)
        low_rumble = math.sin(2 * math.pi * 55 * (index / sample_rate))
        value = (0.85 * noise + 0.15 * low_rumble) * envelope
        samples.append(int(32767 * volume * value))

    return pygame.mixer.Sound(buffer=samples.tobytes())

def build_bounce_sound(duration=0.12, volume=0.25, sample_rate=22050):
    samples = array("h")
    total_samples = int(sample_rate * duration)

    for index in range(total_samples):
        t = index / sample_rate
        progress = index / total_samples
        envelope = (1.0 - progress) ** 3
        frequency = 220 - (120 * progress)
        value = math.sin(2 * math.pi * frequency * t)
        value += 0.25 * math.sin(2 * math.pi * frequency * 1.8 * t)
        value *= 0.7 * envelope
        samples.append(int(32767 * volume * value))

    return pygame.mixer.Sound(buffer=samples.tobytes())

background_music = None
explosion_sound = None
bounce_sound = None
if audio_enabled:
    background_music = build_tone_sound(
        [220.00, 0, 261.63, 293.66, 0, 329.63, 293.66, 0, 261.63, 196.00, 0, 174.61],
        note_duration=0.5,
        volume=0.08,
    )
    explosion_sound = build_explosion_sound()
    bounce_sound = build_bounce_sound()
    background_music.play(loops=-1)

def out_of_bounds(body):
    x, y = body.position
    return x < 0 or x > WIDTH or y > HEIGHT

def build_reachable_block_positions():
    reachable_positions = []
    gravity_y = space.gravity[1]
    bird_mass = 2

    for impulse_x in range(360, 801, 40):
        for impulse_y in range(-800, -79, 40):
            velocity_x = impulse_x / bird_mass
            velocity_y = impulse_y / bird_mass

            for step in range(8, 91, 3):
                t = step / 60
                x = BIRD_START[0] + velocity_x * t
                y = BIRD_START[1] + velocity_y * t + 0.5 * gravity_y * t * t

                if x > WIDTH - 80 or y > 500:
                    break
                if x < 440 or y < 180:
                    continue

                snapped = (int(round(x / 10) * 10), int(round(y / 10) * 10))
                if snapped not in reachable_positions:
                    reachable_positions.append(snapped)

    return reachable_positions

def is_open_block_position(position, selected_positions, min_gap=55):
    for other_x, other_y in selected_positions:
        if math.hypot(position[0] - other_x, position[1] - other_y) < min_gap:
            return False
    return True

def draw_slingshot(surface, bird_position, is_dragging):
    left_post = (BIRD_START[0] - 16, BIRD_START[1] + 28)
    right_post = (BIRD_START[0] + 16, BIRD_START[1] + 28)
    post_top_y = BIRD_START[1] - 18
    wood_color = (112, 78, 42)
    band_color = (88, 55, 35)

    if is_dragging:
        current_bird = (int(bird_position.x), int(bird_position.y))
        pygame.draw.line(surface, band_color, left_post, current_bird, 5)
        pygame.draw.line(surface, band_color, right_post, current_bird, 5)

    pygame.draw.line(surface, wood_color, left_post, (left_post[0], post_top_y), 8)
    pygame.draw.line(surface, wood_color, right_post, (right_post[0], post_top_y), 8)
    pygame.draw.line(
        surface,
        wood_color,
        (left_post[0], post_top_y),
        (right_post[0], post_top_y - 8),
        6,
    )

REACHABLE_BLOCK_POSITIONS = build_reachable_block_positions()

# Blocks
def create_block(x, y):
    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    body.position = x, y

    shape = pymunk.Poly.create_box(body, (40, 40))
    shape.elasticity = 0.4
    shape.collision_type = 2

    space.add(body, shape)
    return body, shape

def spawn_explosion(position):
    particles = []
    for _ in range(18):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(3, 8)
        particles.append(
            {
                "pos": [position[0], position[1]],
                "vel": [math.cos(angle) * speed, math.sin(angle) * speed],
                "radius": random.randint(4, 7),
                "life": random.randint(18, 28),
            }
        )
    explosions.append(particles)
    if explosion_sound is not None:
        explosion_sound.play()

def clear_blocks():
    for body, shape in blocks:
        if body in space.bodies:
            space.remove(body, shape)
    blocks.clear()

def spawn_level_blocks(block_count):
    clear_blocks()
    candidate_positions = REACHABLE_BLOCK_POSITIONS[:]
    random.shuffle(candidate_positions)
    selected_positions = []

    for position in candidate_positions:
        if is_open_block_position(position, selected_positions):
            selected_positions.append(position)
        if len(selected_positions) == block_count:
            break

    for x, y in selected_positions:
        blocks.append(create_block(x, y))

def process_block(space, key, data):
    global score, lives, shot_blocks_destroyed

    action, body, shape = data

    if action == "activate":
        if body.body_type != pymunk.Body.DYNAMIC:
            body.body_type = pymunk.Body.DYNAMIC
            body.mass = 1
            body.moment = pymunk.moment_for_box(1, (40, 40))

            # 🎯 small reward for triggering collapse
            score += 5

    elif action == "remove":
        spawn_explosion(body.position)
        if body in space.bodies:
            space.remove(body, shape)
            blocks[:] = [block for block in blocks if block[0] != body]
            shot_blocks_destroyed += 1
            if shot_blocks_destroyed >= 2:
                lives += 1

            # 💥 big reward for breaking block
            score += 10

# Collision logic
def block_hit(arbiter, space, data):
    global last_block_collision_time

    bird_shape, block_shape = arbiter.shapes
    block_body = block_shape.body
    last_block_collision_time = pygame.time.get_ticks()
    if block_body in space.bodies:
        space.add_post_step_callback(
            process_block,
            ("remove", id(block_shape)),
            ("remove", block_body, block_shape)
        )

    return True

def ground_bounce(arbiter, space, data):
    global last_bounce_sound_time

    if bounce_sound is None:
        return True

    impulse = arbiter.total_impulse.length
    current_time = pygame.time.get_ticks()
    if impulse > 120 and current_time - last_bounce_sound_time > 90:
        bounce_sound.play()
        last_bounce_sound_time = current_time

    return True

def remove_block(space, key, data):
    body, shape = data
    if body in space.bodies:
        space.remove(body, shape)

space.on_collision(1, 2, post_solve=block_hit)
space.on_collision(1, 3, post_solve=ground_bounce)
space.on_collision(2, 3, post_solve=ground_bounce)

# Bird
bird_body = pymunk.Body(2, pymunk.moment_for_circle(2, 0, 15))
bird_body.position = 150, 500
bird_body.damping = 0.99
bird_shape = pymunk.Circle(bird_body, 15)
bird_shape.collision_type = 1
bird_shape.elasticity = 0.9
space.add(bird_body, bird_shape)

dragging = False
bird_waiting_for_launch = True

def hold_bird_at_start(position=BIRD_START):
    global bird_waiting_for_launch

    bird_waiting_for_launch = True
    bird_body.position = position
    bird_body.velocity = (0, 0)
    bird_body.angular_velocity = 0
    bird_body.angle = 0
    bird_body.force = (0, 0)
    bird_body.torque = 0

def launch_bird(impulse):
    global bird_waiting_for_launch

    bird_waiting_for_launch = False
    bird_body.velocity = (0, 0)
    bird_body.angular_velocity = 0
    bird_body.force = (0, 0)
    bird_body.torque = 0
    bird_body.apply_impulse_at_local_point(impulse)

def restart_game():
    global score, current_level, lives, explosions, game_over, game_won
    global last_block_collision_time, shot_blocks_destroyed

    score = 0
    current_level = 1
    lives = 3
    explosions = []
    game_over = False
    game_won = False
    last_block_collision_time = None
    shot_blocks_destroyed = 0
    clear_blocks()
    start_level(1)

def start_level(level):
    global current_level, lives, last_block_collision_time, shot_blocks_destroyed

    current_level = level
    lives = 3
    last_block_collision_time = None
    shot_blocks_destroyed = 0
    spawn_level_blocks(level)
    hold_bird_at_start()

def reset_bird():
    global lives, game_over, game_won, last_block_collision_time, shot_blocks_destroyed

    if not blocks:
        if current_level >= MAX_LEVEL:
            game_won = True
            return
        start_level(current_level + 1)
        return

    if lives <= 0:
        game_over = True
        return

    hold_bird_at_start()
    last_block_collision_time = None
    shot_blocks_destroyed = 0

def is_finite_vector(v):
    return math.isfinite(v.x) and math.isfinite(v.y)

def sanitize_physics_state():
    valid_blocks = []
    for body, shape in blocks:
        if body not in space.bodies:
            continue
        if not is_finite_vector(body.position):
            space.remove(body, shape)
            continue
        valid_blocks.append((body, shape))
    blocks[:] = valid_blocks

    if not is_finite_vector(bird_body.position):
        reset_bird()

running = True
game_over = False
game_won = False
start_level(current_level)

while running:
    screen.fill((135, 206, 235))
    draw_slingshot(screen, bird_body.position, dragging)
    hud = font.render(
        f"Level: {current_level}   Score: {score}   Lives: {lives}",
        True,
        (0, 0, 0)
    )
    screen.blit(hud, (10, 10))
    play_again_rect = pygame.Rect(WIDTH // 2 - 140, HEIGHT // 2 + 40, 120, 44)
    exit_rect = pygame.Rect(WIDTH // 2 + 20, HEIGHT // 2 + 40, 120, 44)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if game_over and event.type == pygame.MOUSEBUTTONDOWN:
            if play_again_rect.collidepoint(event.pos):
                restart_game()
            elif exit_rect.collidepoint(event.pos):
                running = False
            continue
        if game_over or game_won:
            continue
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            dx = mx - bird_body.position.x
            dy = my - bird_body.position.y
            if lives > 0 and dx*dx + dy*dy < 400:
                dragging = True
                lives -= 1

        elif event.type == pygame.MOUSEBUTTONUP:
            if dragging:
                dragging = False
                last_block_collision_time = None
                shot_blocks_destroyed = 0
                mx, my = pygame.mouse.get_pos()

                dx = bird_body.position.x - mx
                dy = bird_body.position.y - my

                dx = max(min(dx, 100), -100)
                dy = max(min(dy, 100), -100)

                launch_bird((dx * 8, dy * 8))

    if dragging:
        mx, my = pygame.mouse.get_pos()

        dx = mx - 150
        dy = my - 500
        dist = math.hypot(dx, dy)

        max_dist = 100
        if dist > max_dist:
            scale = max_dist / dist
            mx = 150 + dx * scale
            my = 500 + dy * scale

        bird_body.position = (mx, my)
        bird_body.velocity = (0, 0)
    elif bird_waiting_for_launch and not game_over and not game_won:
        bird_body.position = BIRD_START
        bird_body.velocity = (0, 0)
        bird_body.angular_velocity = 0
        bird_body.force = (0, 0)
        bird_body.torque = 0

    # Step physics
    space.step(1/60)
    if game_over or game_won:
        dragging = False
    if not dragging and not game_over and not game_won and not blocks:
        reset_bird()
    collision_reset_due = (
        last_block_collision_time is not None
        and pygame.time.get_ticks() - last_block_collision_time >= 1000
    )
    if not dragging and not game_over and not game_won and (out_of_bounds(bird_body) or collision_reset_due):
        reset_bird()

    # Safety reset
    sanitize_physics_state()
    if game_over:
        over = font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(over, (WIDTH//2 - 80, HEIGHT//2))
        pygame.draw.rect(screen, (240, 240, 240), play_again_rect, border_radius=8)
        pygame.draw.rect(screen, (240, 240, 240), exit_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 80, 80), play_again_rect, 2, border_radius=8)
        pygame.draw.rect(screen, (80, 80, 80), exit_rect, 2, border_radius=8)
        play_again_text = font.render("Play Again", True, (20, 20, 20))
        exit_text = font.render("Exit Game", True, (20, 20, 20))
        screen.blit(play_again_text, play_again_text.get_rect(center=play_again_rect.center))
        screen.blit(exit_text, exit_text.get_rect(center=exit_rect.center))
    elif game_won:
        won = font.render("YOU WIN", True, (0, 150, 0))
        screen.blit(won, (WIDTH//2 - 60, HEIGHT//2))
    if is_finite_vector(bird_body.position):
        space.debug_draw(draw_options)

    next_explosions = []
    for particles in explosions:
        active_particles = []
        for particle in particles:
            particle["pos"][0] += particle["vel"][0]
            particle["pos"][1] += particle["vel"][1]
            particle["vel"][1] += 0.15
            particle["life"] -= 1
            particle["radius"] = max(0, particle["radius"] - 0.12)

            if particle["life"] > 0 and particle["radius"] > 0:
                active_particles.append(particle)
                pygame.draw.circle(
                    screen,
                    (255, random.randint(120, 220), 0),
                    (int(particle["pos"][0]), int(particle["pos"][1])),
                    int(particle["radius"]),
                )

        if active_particles:
            next_explosions.append(active_particles)

    explosions[:] = next_explosions

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
