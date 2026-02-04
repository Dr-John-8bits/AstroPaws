import pygame
import sys
import random
import math
import textwrap
import json
from datetime import datetime
from pathlib import Path

# Importer la configuration des niveaux
import levels
# Index du niveau courant (initialisé à 0 localement)
level_idx = 0

# Initialisation de Pygame
pygame.init()
pygame.joystick.init()

# Dimensions de la fenêtre (agrandies)
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("AstroPaws")

crt_filter_enabled = True

def build_crt_overlays(width, height):
    scanlines = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, 4):
        pygame.draw.line(scanlines, (0, 0, 0, 50), (0, y), (width, y))
    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    center_x, center_y = width / 2, height / 2
    max_dist = math.hypot(center_x, center_y)
    for y in range(height):
        for x in range(width):
            dist = math.hypot(x - center_x, y - center_y)
            alpha = int(max(0, min(90, (dist / max_dist) ** 2.2 * 90)))
            if alpha:
                vignette.set_at((x, y), (0, 0, 0, alpha))
    return scanlines, vignette

crt_scanline_overlay, crt_vignette_overlay = build_crt_overlays(screen_width, screen_height)

def apply_crt_overlay():
    if not crt_filter_enabled:
        return
    ghost = screen.copy()
    ghost.set_alpha(18)
    screen.blit(ghost, (1, 0))
    screen.blit(crt_scanline_overlay, (0, 0))
    screen.blit(crt_vignette_overlay, (0, 0))

def present_frame():
    apply_crt_overlay()
    pygame.display.flip()

# Audio optionnel : le jeu reste jouable même sans périphérique audio.
try:
    pygame.mixer.init()
except pygame.error:
    pass

ROOT_DIR = Path(__file__).resolve().parent
SOUND_DIR = ROOT_DIR / "sounds"

# Définition de quelques couleurs
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
GOLD = (255, 223, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
RED   = (255, 0, 0)
CYAN  = (0, 255, 255)

GAME_VERSION = "2026-02-04.2"

INITIAL_LIVES = 9
INITIAL_WATER_AMMO = 50
INITIAL_CROQUETTES = 5
HYPER_DASH_MULTIPLIER = 3
HYPER_DASH_DURATION = 450
HYPER_PICKUP_LIFETIME = 7000
HYPER_PICKUP_SPAWN_CHANCE = 0.003
ASTRO_HIT_FLASH_DURATION = 220
ASTRO_ACCEL = 0.85
ASTRO_FRICTION = 0.82
ASTRO_DRAG = 0.98

GRAVITY_RADIUS = 220
GRAVITY_LEVEL_STRENGTH = {
    0: 0.0,
    1: 0.12,
    2: 0.18,
}

OXIDIZED_FROM_LEVEL = 1
OXIDIZED_DELAY_MS = 3200
OXIDIZED_BONUS_SCORE = 12
OXIDIZED_WATER_PENALTY = 4
OXIDIZED_DEBUFF_DURATION = 1800

BOSS_MAX_HEALTH = 72

HIGHSCORE_FILE = ROOT_DIR / "highscores.json"
MAX_HIGHSCORES = 8

CONTROLLER_DEADZONE = 0.28
CONTROLLER_CONFIRM_BUTTONS = {0, 7}
CONTROLLER_BACK_BUTTONS = {1, 6}
CONTROLLER_SHOOT_BUTTONS = {0, 5}
CONTROLLER_SHIELD_BUTTONS = {2}
CONTROLLER_HYPER_BUTTONS = {3}
CONTROLLER_PAUSE_BUTTONS = {7}
CONTROLLER_CRT_TOGGLE_BUTTONS = {4}

BALANCE_BASE_SPAWN = {0: 0.018, 1: 0.022, 2: 0.027}
BALANCE_WATER_PICKUP_BASE = {0: 0.0055, 1: 0.0062, 2: 0.0068}
BALANCE_COOLDOWN_BASE = {0: 290, 1: 270, 2: 250}

# Le cooldown est récupéré depuis la config de niveau si disponible.
hyper_level_cfg = next(
    (cfg for cfg in levels.levels if cfg.get("item", {}).get("type") == "hyperdrive"),
    None
)
HYPER_COOLDOWN = (
    hyper_level_cfg.get("item", {}).get("cooldown", 60000) if hyper_level_cfg else 60000
)

# Ajout des listes pour les ennemis et explosions
enemy_list = []
explosion_list = []

def create_explosion(x, y, color=YELLOW, num_particles=20):
    for i in range(num_particles):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 3)
        dx = math.cos(angle) * speed
        dy = math.sin(angle) * speed
        lifetime = random.randint(20, 40)
        explosion_list.append({'x': x, 'y': y, 'dx': dx, 'dy': dy, 'lifetime': lifetime, 'color': color})

def get_enemy_base_sprite(enemy_type):
    if enemy_type == "mouse":
        return mouse_sprite
    if enemy_type == "rat":
        return rat_sprite
    return dog_sprite

def draw_thruster(center_x, center_y, facing, thrust_power, hyper_on):
    if thrust_power <= 0:
        return
    direction = {
        "left": (-1, 0),
        "right": (1, 0),
        "up": (0, -1),
        "down": (0, 1),
    }.get(facing, (1, 0))
    dir_x, dir_y = direction
    back_x, back_y = -dir_x, -dir_y
    side_x, side_y = -back_y, back_x
    layers = 4 if hyper_on else 3
    for i in range(layers):
        spread = (i - 1.5) * (3 + 2 * thrust_power)
        jitter = random.uniform(-2.0, 2.0)
        distance = 28 + i * 7 + 10 * thrust_power
        px = center_x + back_x * distance + side_x * spread
        py = center_y + back_y * distance + side_y * spread + jitter
        radius = max(1, int(4 + thrust_power * 5 - i))
        color = YELLOW if i == 0 else ORANGE if i == 1 else (255, 120, 0)
        pygame.draw.circle(screen, color, (int(px), int(py)), radius)

def draw_enemy_animated(enemy, now_ms):
    base_sprite = get_enemy_base_sprite(enemy['type'])
    phase = enemy.get('anim_phase', enemy.get('bob_phase', 0.0))

    if enemy['type'] == "mouse":
        bob = math.sin(now_ms / 130 + phase) * 8 + math.sin(now_ms / 45 + phase) * 3
        stretch = math.sin(now_ms / 85 + phase)
        scale_x = 1.0 + 0.12 * stretch
        scale_y = 1.0 - 0.10 * stretch
        angle = 8 * math.sin(now_ms / 90 + phase)
    elif enemy['type'] == "rat":
        bob = math.sin(now_ms / 170 + phase) * 10
        stretch = math.sin(now_ms / 120 + phase)
        scale_x = 1.0 + 0.08 * stretch
        scale_y = 1.0 - 0.05 * stretch
        angle = 5 * math.sin(now_ms / 150 + phase)
    else:  # dog
        bob = math.sin(now_ms / 220 + phase) * 12
        stretch = math.sin(now_ms / 180 + phase)
        scale_x = 1.0 + 0.04 * stretch
        scale_y = 1.0 + 0.05 * stretch
        angle = 3 * math.sin(now_ms / 200 + phase)

    spawn_time = enemy.get('spawn_time', now_ms)
    appear_ratio = min(1.0, max(0.0, (now_ms - spawn_time) / 260))
    appear_scale = 0.75 + 0.25 * appear_ratio
    scale_x *= appear_scale
    scale_y *= appear_scale

    animated = pygame.transform.rotozoom(base_sprite, angle, 1.0)
    w = max(1, int(animated.get_width() * scale_x))
    h = max(1, int(animated.get_height() * scale_y))
    animated = pygame.transform.smoothscale(animated, (w, h))
    animated.set_alpha(int(255 * appear_ratio))

    shadow_w = max(6, int(enemy['width'] * (0.85 + 0.08 * math.sin(now_ms / 160 + phase))))
    shadow_h = 8 if enemy['type'] == "dog" else 6
    shadow_rect = pygame.Rect(0, 0, shadow_w, shadow_h)
    shadow_rect.center = (
        int(enemy['x'] + enemy['width'] / 2),
        int(enemy['y'] + enemy['height'] + 10),
    )
    pygame.draw.ellipse(screen, (18, 18, 26), shadow_rect)

    rect = animated.get_rect(
        center=(enemy['x'] + enemy['width'] / 2, enemy['y'] + enemy['height'] / 2 + bob)
    )
    screen.blit(animated, rect)

def draw_astro_animated(now_ms, astro_pos_x, astro_pos_y, facing, move_dx, move_dy, hyper_on, hit_flash_until):
    base = {
        "left": astro_sprite_left,
        "right": astro_sprite_right,
        "up": astro_sprite_up,
        "down": astro_sprite_down,
    }.get(facing, astro_sprite_right)

    move_speed = math.hypot(move_dx, move_dy)
    max_speed = speed * HYPER_DASH_MULTIPLIER
    speed_ratio = min(1.0, move_speed / max(1.0, max_speed))
    moving = move_speed > 0.1

    breathe = 1.0 + 0.03 * math.sin(now_ms / 280)
    stride = math.sin(now_ms / 85) if moving else math.sin(now_ms / 220)
    scale_x = breathe * (1.0 + 0.06 * abs(stride))
    scale_y = breathe * (1.0 - 0.04 * abs(stride))
    if hyper_on:
        scale_x += 0.10
        scale_y += 0.04

    if facing in ("left", "right"):
        angle = -7.0 * (move_dy / max(1.0, speed))
    else:
        angle = 7.0 * (move_dx / max(1.0, speed))
    angle += 2.5 * math.sin(now_ms / 180) * speed_ratio

    animated = pygame.transform.rotozoom(base, angle, 1.0)
    w = max(1, int(animated.get_width() * scale_x))
    h = max(1, int(animated.get_height() * scale_y))
    animated = pygame.transform.smoothscale(animated, (w, h))

    center_x = astro_pos_x + astro_sprite_right.get_width() // 2
    center_y = astro_pos_y + astro_sprite_right.get_height() // 2
    rect = animated.get_rect(center=(center_x, center_y))

    thrust_power = 0.0
    if moving:
        thrust_power = min(1.0, 0.25 + speed_ratio)
    if hyper_on:
        thrust_power = 1.0
    if thrust_power > 0.0:
        draw_thruster(center_x, center_y, facing, thrust_power, hyper_on)

    screen.blit(animated, rect)

    if now_ms < hit_flash_until:
        flash = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        flash.fill((255, 50, 50, 90))
        screen.blit(flash, rect.topleft)

    return rect

def make_oxidized_variant(sprite):
    variant = sprite.copy()
    tint = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
    tint.fill((130, 190, 90, 175))
    variant.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return variant

def get_level_gravity_strength(level_index):
    return GRAVITY_LEVEL_STRENGTH.get(level_index, 0.0)

def compute_planet_gravity_pull(player_cx, player_cy, level_index):
    gravity_strength = get_level_gravity_strength(level_index)
    if gravity_strength <= 0:
        return 0.0, 0.0, None, 0.0

    best_dx = 0.0
    best_dy = 0.0
    best_planet = None
    best_pull = 0.0
    for planet in planet_list:
        dx = planet['x'] - player_cx
        dy = planet['y'] - player_cy
        dist = math.hypot(dx, dy)
        if dist <= 2 or dist >= GRAVITY_RADIUS:
            continue
        influence = 1.0 - (dist / GRAVITY_RADIUS)
        pull_strength = gravity_strength * influence * (0.8 + planet['size'] / 22)
        if pull_strength > best_pull:
            best_pull = pull_strength
            best_dx = (dx / dist) * pull_strength
            best_dy = (dy / dist) * pull_strength
            best_planet = planet

    return best_dx, best_dy, best_planet, best_pull

def is_croquette_oxidized(croquette, level_index, now_ms):
    if level_index < OXIDIZED_FROM_LEVEL:
        return False
    return (now_ms - croquette['spawn_time']) >= OXIDIZED_DELAY_MS

def spawn_boss_projectiles(now_ms, player_center):
    global boss_data, boss_projectiles

    if not boss_active or not boss_data:
        return

    phase = boss_data['phase']
    base_x = boss_data['x'] + boss_data['width'] // 2
    base_y = boss_data['y'] + boss_data['height'] - 8
    target_angle = math.atan2(player_center[1] - base_y, player_center[0] - base_x)

    spread_by_phase = {
        1: [0.0],
        2: [-0.20, 0.0, 0.20],
        3: [-0.40, -0.20, 0.0, 0.20, 0.40],
    }
    speed_by_phase = {1: 4.2, 2: 4.8, 3: 5.4}
    radius_by_phase = {1: 5, 2: 6, 3: 7}
    color_by_phase = {1: ORANGE, 2: RED, 3: (255, 60, 120)}

    for spread in spread_by_phase[phase]:
        angle = target_angle + spread
        speed = speed_by_phase[phase]
        boss_projectiles.append({
            'x': base_x,
            'y': base_y,
            'dx': math.cos(angle) * speed,
            'dy': math.sin(angle) * speed,
            'radius': radius_by_phase[phase],
            'color': color_by_phase[phase],
            'lifetime': 220,
        })

    if phase == 3:
        # Rafale latérale pour mettre la pression en phase finale.
        for side_x, drift in ((40, 1.6), (screen_width - 40, -1.6)):
            boss_projectiles.append({
                'x': side_x,
                'y': boss_data['y'] + boss_data['height'] // 2,
                'dx': drift,
                'dy': 4.4,
                'radius': 6,
                'color': (255, 80, 140),
                'lifetime': 190,
            })

    boss_data['last_shot'] = now_ms

def draw_boss(now_ms):
    if not boss_active or not boss_data:
        return None

    pulse = 1.0 + 0.03 * math.sin(now_ms / 160)
    angle = 3.0 * math.sin(now_ms / 250)

    base_sprite = pygame.transform.smoothscale(
        dog_sprite, (boss_data['width'], boss_data['height'])
    )
    animated = pygame.transform.rotozoom(base_sprite, angle, pulse)
    boss_rect = animated.get_rect(
        center=(
            boss_data['x'] + boss_data['width'] // 2,
            boss_data['y'] + boss_data['height'] // 2,
        )
    )

    shadow_rect = pygame.Rect(0, 0, int(boss_data['width'] * 0.8), 16)
    shadow_rect.center = (
        boss_data['x'] + boss_data['width'] // 2,
        boss_data['y'] + boss_data['height'] + 14,
    )
    pygame.draw.ellipse(screen, (20, 10, 20), shadow_rect)
    screen.blit(animated, boss_rect)

    # Couronne impériale minimaliste.
    crown_center_x = boss_rect.centerx
    crown_y = boss_rect.top - 14
    crown_points = [
        (crown_center_x - 26, crown_y + 18),
        (crown_center_x - 12, crown_y + 2),
        (crown_center_x, crown_y + 16),
        (crown_center_x + 12, crown_y + 2),
        (crown_center_x + 26, crown_y + 18),
    ]
    pygame.draw.polygon(screen, GOLD, crown_points)
    pygame.draw.circle(screen, YELLOW, (crown_center_x, crown_y + 4), 3)

    eye_color = RED if boss_data['phase'] >= 2 else ORANGE
    pygame.draw.circle(screen, eye_color, (boss_rect.centerx - 18, boss_rect.centery - 8), 4)
    pygame.draw.circle(screen, eye_color, (boss_rect.centerx + 18, boss_rect.centery - 8), 4)

    return pygame.Rect(boss_data['x'], boss_data['y'], boss_data['width'], boss_data['height'])

def start_boss_fight(now_ms):
    global boss_active, boss_data, boss_projectiles, boss_contact_cooldown_until, game_state

    boss_active = True
    boss_data = {
        'name': "Imperatrice Zibeline",
        'x': screen_width // 2 - 90,
        'y': 90,
        'width': 180,
        'height': 120,
        'health': BOSS_MAX_HEALTH,
        'max_health': BOSS_MAX_HEALTH,
        'phase': 1,
        'vx': 1,
        'last_shot': now_ms,
        'seed': random.uniform(0, math.pi * 2),
    }
    boss_projectiles = []
    boss_contact_cooldown_until = 0
    game_state = "BOSS_INTRO"

def load_highscores():
    if not HIGHSCORE_FILE.exists():
        return []
    try:
        raw_data = json.loads(HIGHSCORE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    cleaned = []
    for entry in raw_data if isinstance(raw_data, list) else []:
        if not isinstance(entry, dict):
            continue
        score_value = int(entry.get("score", 0))
        cleaned.append({
            "score": score_value,
            "result": str(entry.get("result", "Run")),
            "duration": int(entry.get("duration", -1)),
            "stamp": str(entry.get("stamp", "")),
        })
    cleaned.sort(key=lambda it: (-it["score"], it["duration"] if it["duration"] >= 0 else 999999))
    return cleaned[:MAX_HIGHSCORES]

def save_highscores(entries):
    try:
        HIGHSCORE_FILE.write_text(
            json.dumps(entries[:MAX_HIGHSCORES], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass

def get_level_spawn_chance(level_index, score_value, lives_value, boss_on):
    if boss_on:
        return 0.0
    base = BALANCE_BASE_SPAWN.get(level_index, 0.03)
    score_pressure = min(0.018, max(0, score_value) * 0.00009)
    survival_relief = -0.006 if lives_value <= 2 else 0.0
    return max(0.010, min(0.055, base + score_pressure + survival_relief))

def get_water_pickup_spawn_chance(level_index, boss_on, water_value):
    if boss_on:
        return 0.011
    base = BALANCE_WATER_PICKUP_BASE.get(level_index, 0.0065)
    low_water_bonus = 0.0035 if water_value <= 20 else 0.0
    return min(0.018, base + low_water_bonus)

def get_shot_cooldown(level_index, boss_on):
    if boss_on:
        return 220
    return BALANCE_COOLDOWN_BASE.get(level_index, 250)

def normalize_axis(value):
    return 0.0 if abs(value) < CONTROLLER_DEADZONE else float(value)

active_controller = None

def refresh_controller():
    global active_controller
    active_controller = None
    for idx in range(pygame.joystick.get_count()):
        joystick = pygame.joystick.Joystick(idx)
        if not joystick.get_init():
            joystick.init()
        active_controller = joystick
        break

def get_controller_move_vector():
    if active_controller is None:
        return 0.0, 0.0
    axis_x = normalize_axis(active_controller.get_axis(0)) if active_controller.get_numaxes() > 0 else 0.0
    axis_y = normalize_axis(active_controller.get_axis(1)) if active_controller.get_numaxes() > 1 else 0.0
    if active_controller.get_numhats() > 0:
        hat_x, hat_y = active_controller.get_hat(0)
        if hat_x != 0:
            axis_x = float(hat_x)
        if hat_y != 0:
            axis_y = float(-hat_y)
    return axis_x, axis_y

def handle_global_event(event):
    global crt_filter_enabled
    if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
        refresh_controller()
    if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
        crt_filter_enabled = not crt_filter_enabled
    elif event.type == pygame.JOYBUTTONDOWN and event.button in CONTROLLER_CRT_TOGGLE_BUTTONS:
        crt_filter_enabled = not crt_filter_enabled

def facing_to_vector(facing_value):
    if facing_value == "left":
        return -1.0, 0.0
    if facing_value == "right":
        return 1.0, 0.0
    if facing_value == "up":
        return 0.0, -1.0
    return 0.0, 1.0

def fire_player_bullet(direction_x, direction_y, current_time):
    global next_shot_allowed_time, water_ammo
    if current_time < next_shot_allowed_time or water_ammo <= 0:
        return False
    magnitude = math.hypot(direction_x, direction_y)
    if magnitude <= 0:
        direction_x, direction_y = facing_to_vector(astro_facing)
        magnitude = math.hypot(direction_x, direction_y)
    direction_x = direction_x / magnitude * bullet_speed
    direction_y = direction_y / magnitude * bullet_speed
    bullet_rect = pygame.Rect(
        astro_x + 25 - bullet_width // 2,
        astro_y + 25 - bullet_height // 2,
        bullet_width,
        bullet_height,
    )
    bullet = {'rect': bullet_rect, 'dx': direction_x, 'dy': direction_y}
    bullet_list.append(bullet)
    next_shot_allowed_time = current_time + cooldown_time
    water_ammo -= 1
    play_sound(shoot_sound)
    return True

refresh_controller()

def load_sound(filename, volume=0.6):
    if not pygame.mixer.get_init():
        return None
    sound_path = SOUND_DIR / filename
    if not sound_path.exists():
        return None
    try:
        sound = pygame.mixer.Sound(str(sound_path))
        sound.set_volume(volume)
        return sound
    except pygame.error:
        return None

def play_sound(sound):
    if sound is None:
        return
    try:
        sound.play()
    except pygame.error:
        pass

music_tracks = {
    "menu": SOUND_DIR / "music_menu_loop.wav",
    "gameplay": SOUND_DIR / "music_gameplay_loop.wav",
}
current_music_key = None

def set_music(music_key):
    global current_music_key
    if current_music_key == music_key:
        return
    current_music_key = music_key
    if not pygame.mixer.get_init():
        return
    if music_key is None:
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
        return
    music_path = music_tracks.get(music_key)
    if music_path is None or not music_path.exists():
        return
    try:
        pygame.mixer.music.load(str(music_path))
        pygame.mixer.music.set_volume(0.35 if music_key == "menu" else 0.45)
        pygame.mixer.music.play(-1)
    except pygame.error:
        pass

def music_for_state(state):
    if state in ("MENU", "STORY", "INFO", "FINAL_WIN", "GAME_OVER"):
        return "menu"
    if state in ("PLAYING", "PAUSE", "LEVEL_INTRO", "BOSS_INTRO", "REWARD"):
        return "gameplay"
    return None

# SFX 8-bit chargés depuis le pack généré.
shoot_sound = load_sound("sfx_shoot.wav", 0.45)
explosion_sound = load_sound("sfx_explosion.wav", 0.50)
pickup_sound = load_sound("sfx_pickup.wav", 0.45)
hyper_pickup_sound = load_sound("sfx_pickup.wav", 0.55)
hyper_dash_sound = load_sound("sfx_dash.wav", 0.60)
warp_sound = load_sound("sfx_warp.wav", 0.55)

# Effet de warp d'étoiles suivi d'un flash blanc
def warp_effect():
    # Tunnel d'étoiles puis flash blanc
    play_sound(warp_sound)
    center_x, center_y = screen_width // 2, screen_height // 2
    # Effet warp encore plus dense et plus lent
    for _ in range(30):  # plus d'étapes pour densifier
        screen.fill(BLACK)
        # Déplacer et dessiner les étoiles principales
        for star in star_list:
            dx = star['x'] - center_x
            dy = star['y'] - center_y
            star['x'] = center_x + dx * 1.15
            star['y'] = center_y + dy * 1.15
            pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
        # Ajouter des étoiles supplémentaires pour saturer l'effet
        for _ in range(200):  # étoile bonus
            rx = random.randint(0, screen_width)
            ry = random.randint(0, screen_height)
            ddx = rx - center_x
            ddy = ry - center_y
            x2 = center_x + ddx * 1.15
            y2 = center_y + ddy * 1.15
            pygame.draw.circle(screen, WHITE, (int(x2), int(y2)), 1)
        present_frame()
        pygame.time.delay(70)  # délai encore un peu plus long pour percevoir l'effet
    # Flash blanc
    screen.fill(WHITE)
    present_frame()
    pygame.time.delay(100)
    # Régénérer les étoiles pour le prochain level
    for star in star_list:
        star['x'] = random.randint(0, screen_width)
        star['y'] = random.randint(0, screen_height)

croquette_size = 10
croquette_lifetime = 5000  # Durée de vie en millisecondes (5 secondes)

def spawn_croquette():
    x = random.randint(0, screen_width - croquette_size)
    y = random.randint(0, screen_height - croquette_size)
    spawn_time = pygame.time.get_ticks()
    croquette_type = "rare" if random.random() < 0.1 else "normal"
    return {'x': x, 'y': y, 'spawn_time': spawn_time, 'type': croquette_type}

croquette_list = [spawn_croquette() for _ in range(INITIAL_CROQUETTES)]

# Création des réserves d'eau (objets à collecter pour augmenter l'eau)
water_item_list = []
hyper_item_list = []

# Génération d'un fond spatial procédural
num_stars = 50
star_list = []
for i in range(num_stars):
    x = random.randint(0, screen_width)
    y = random.randint(0, screen_height)
    speed = random.uniform(0.2, 1.0)
    star_list.append({'x': x, 'y': y, 'speed': speed})

# Modification pour générer des planètes avec des couleurs aléatoires

num_planets = 3
planet_list = []
for i in range(num_planets):
    x = random.randint(0, screen_width)
    y = random.randint(0, screen_height)
    size = random.randint(8, 20)
    speed = random.uniform(0.1, 0.5)
    color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
    planet_list.append({'x': x, 'y': y, 'size': size, 'speed': speed, 'color': color})

# ==== OVNIs décoratifs ====
class UFO:
    def __init__(self, x, y, scale=1.0, speed=0.5, color=(150, 200, 255)):
        self.x = x
        self.y = y
        self.scale = scale
        self.speed = speed
        self.angle = random.uniform(0, 2 * math.pi)
        # Contour vectoriel d'un saucer (disque + dôme)
        self.pointlist = [(-9,0),(-3,-3),(-2,-6),(2,-6),(3,-3),(9,0),(-9,0),(-3,4),(3,4),(9,0)]
        self.color = color
    def update(self):
        # Avance et oscille légèrement
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.angle += random.uniform(-0.05, 0.05)
        # Wrap-around de l'UFO
        if self.x < 0: self.x = screen_width
        elif self.x > screen_width: self.x = 0
        if self.y < 0: self.y = screen_height
        elif self.y > screen_height: self.y = 0
    def draw(self):
        # Calculer et tracer le contour
        transformed = []
        for px, py in self.pointlist:
            tx = px * self.scale
            ty = py * self.scale
            rx = tx * math.cos(self.angle) - ty * math.sin(self.angle)
            ry = tx * math.sin(self.angle) + ty * math.cos(self.angle)
            transformed.append((self.x + rx, self.y + ry))
        pygame.draw.aalines(screen, self.color, True, transformed)

# Créer quelques OVNIs décoratifs
ufo_list = []
for _ in range(2):
    ufo_list.append(
        UFO(
            random.uniform(0, screen_width),
            random.uniform(0, screen_height),
            scale=random.uniform(0.5, 1.0),
            speed=random.uniform(0.2, 0.7),
            color=(random.randint(100,255), random.randint(100,255), random.randint(100,255))
        )
    )


# Charger le sprite d'AstroPaws et ses versions gauche/droite/haut/bas
astro_sprite_right = pygame.image.load("images/astro_paws.png").convert_alpha()
astro_sprite_right = pygame.transform.scale(astro_sprite_right, (80, 80))
astro_sprite_left = pygame.transform.flip(astro_sprite_right, True, False)
# Créer les versions pour haut et bas en pivotant la version droite
astro_sprite_up = pygame.transform.rotate(astro_sprite_right, 90)
astro_sprite_down = pygame.transform.rotate(astro_sprite_right, -90)
# Direction initiale
astro_facing = "right"

# Charger les sprites des croquettes et de l'eau
# Agrandir les sprites de croquettes et d'eau
# Agrandir les sprites de croquettes
brown_croquette_sprite = pygame.image.load("images/browncroquette.png").convert_alpha()
brown_croquette_sprite = pygame.transform.scale(brown_croquette_sprite, (30, 30))  # croquette normale agrandie
# Agrandir la croquette dorée
gold_croquette_sprite  = pygame.image.load("images/goldcroquette.png").convert_alpha()
gold_croquette_sprite  = pygame.transform.scale(gold_croquette_sprite,  (40, 40))  # croquette rare encore plus grande
brown_croquette_oxidized_sprite = make_oxidized_variant(brown_croquette_sprite)
gold_croquette_oxidized_sprite = make_oxidized_variant(gold_croquette_sprite)
# Agrandir la réserve d'eau
water_sprite           = pygame.image.load("images/water.png").convert_alpha()
water_sprite           = pygame.transform.scale(water_sprite,           (30, 30))


# Charger l'image du coeur pour les vies
heart_sprite = pygame.image.load("images/heart.png").convert_alpha()
heart_sprite = pygame.transform.scale(heart_sprite, (20, 20))

# Charger l'image de l'écran d'accueil
welcome_image = pygame.image.load("images/ecranaccueil.png").convert_alpha()
welcome_image = pygame.transform.scale(welcome_image, (400, 300))  # taille réduite

chat_sleep_image = pygame.image.load("images/chatdort.png").convert_alpha()
chat_sleep_image = pygame.transform.scale(chat_sleep_image, (360, 240))

# Charger la tête d’AstroPaws pour l’écran VS
astro_head = pygame.image.load("images/astro_paws_head.png").convert_alpha()
astro_head = pygame.transform.scale(astro_head, (120, 120))

# Charger les sprites des ennemis
mouse_sprite = pygame.image.load("images/badguymouse.png").convert_alpha()
mouse_sprite = pygame.transform.scale(mouse_sprite, (20, 20))
rat_sprite   = pygame.image.load("images/badguyrat.png").convert_alpha()
rat_sprite   = pygame.transform.scale(rat_sprite,   (30, 30))
dog_sprite   = pygame.image.load("images/badguydog.png").convert_alpha()
dog_sprite   = pygame.transform.scale(dog_sprite,   (50, 50))

# Charger les sprites morts pour la transition de niveau
# Mettre les sprites morts à la taille d'AstroPaws (astro_head)
mouse_dead_sprite = pygame.image.load("images/badguymouse_dead.png").convert_alpha()
rat_dead_sprite   = pygame.image.load("images/badguyrat_dead.png").convert_alpha()
dog_dead_sprite   = pygame.image.load("images/badguydog_dog.png").convert_alpha()
dead_size = astro_head.get_size()
mouse_dead_sprite = pygame.transform.scale(mouse_dead_sprite, dead_size)
rat_dead_sprite   = pygame.transform.scale(rat_dead_sprite,   dead_size)
dog_dead_sprite   = pygame.transform.scale(dog_dead_sprite,   dead_size)

# Charger l'image de Game Over
gameover_image = pygame.image.load("images/gameover.png").convert_alpha()
gameover_image = pygame.transform.scale(gameover_image, (400, 200))
 # Charger l'image de victoire de niveau
youwin_image = pygame.image.load("images/youwin.png").convert_alpha()
youwin_image = pygame.transform.scale(youwin_image, (400, 200))

# Charger l'image du guide (doc)
doctor_image = pygame.image.load("images/astropaws_doctor.png").convert_alpha()
doctor_image = pygame.transform.scale(doctor_image, (150, 150))

# Charger les icônes d'inventaire
# Agrandissement des icônes d'inventaire
shield_icon = pygame.image.load("images/shield_icon.png").convert_alpha()
shield_icon = pygame.transform.scale(shield_icon, (48, 48))
hyper_icon  = pygame.image.load("images/hyper_icon.png").convert_alpha()
hyper_icon  = pygame.transform.scale(hyper_icon,  (48, 48))
hyper_pickup_sprite = pygame.transform.scale(hyper_icon, (30, 30))

ingredient_icon = pygame.image.load("images/ingredient_icon.png").convert_alpha()
ingredient_icon = pygame.transform.scale(ingredient_icon, (48, 48))

# Sprites spécifiques des ingrédients
poulet_sprite   = pygame.image.load("images/ingredient_poulet.png").convert_alpha()
poulet_sprite   = pygame.transform.scale(poulet_sprite, (48, 48))
thon_sprite     = pygame.image.load("images/ingredient_thon.png").convert_alpha()
thon_sprite     = pygame.transform.scale(thon_sprite, (48, 48))
carotte_sprite  = pygame.image.load("images/ingredient_carotte.png").convert_alpha()
carotte_sprite  = pygame.transform.scale(carotte_sprite, (48, 48))
fragment_sprite = pygame.image.load("images/ingredient_fragment_croquette.png").convert_alpha()
fragment_sprite = pygame.transform.scale(fragment_sprite, (48, 48))

# Mapping clé → sprite pour l’inventaire
ingredient_sprites = {
    'ingredient_poulet': poulet_sprite,
    'ingredient_thon': thon_sprite,
    'ingredient_carotte': carotte_sprite,
    'ingredient_fragment_croquette': fragment_sprite,
}

# Position initiale d'AstroPaws
astro_x = screen_width // 2
astro_y = screen_height // 2
speed = 5  # Vitesse de déplacement

# Gestion des tirs
bullet_list = []
bullet_speed = 10
bullet_width = 10
bullet_height = 4

# Initialiser le score, les vies et le font
score = 0
lives = INITIAL_LIVES
water_ammo = INITIAL_WATER_AMMO
pygame.font.init()
# Augmentation de la taille de la police pour une meilleure lisibilité
score_font = pygame.font.SysFont(None, 48)
# Police plus petite pour les sous-titres et les blagues
subtitle_font = pygame.font.SysFont(None, 32)
highscore_font = pygame.font.SysFont(None, 24)

highscores = load_highscores()
run_recorded = False
latest_highscore_stamp = None

credits_lines = [
    "Direction creative: Dr John 8bit",
    "Code gameplay: AstroPaws Crew",
    "Art et sprites: Atelier Felin Spatial",
    "Audio chiptune: Studio Croquettes FM",
    "Tests et feedback: Communaute AstroPaws",
]

def format_duration(seconds):
    if seconds < 0:
        return "--:--"
    mins, secs = divmod(seconds, 60)
    return f"{mins:02d}:{secs:02d}"

def record_run_result(result_label, now_ms):
    global highscores, run_recorded, latest_highscore_stamp
    if run_recorded:
        return
    elapsed_seconds = -1
    if game_start_time is not None:
        elapsed_seconds = max(0, (now_ms - game_start_time - paused_time_accum) // 1000)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = {
        "score": int(score),
        "result": result_label,
        "duration": int(elapsed_seconds),
        "stamp": stamp,
    }
    highscores.append(entry)
    highscores.sort(key=lambda item: (-item["score"], item["duration"] if item["duration"] >= 0 else 999999))
    highscores = highscores[:MAX_HIGHSCORES]
    latest_highscore_stamp = stamp
    save_highscores(highscores)
    run_recorded = True

def draw_highscore_panel(pos_x, pos_y, max_rows=5):
    panel_width = 300
    row_height = 22
    panel_height = 42 + max_rows * row_height
    panel_rect = pygame.Rect(pos_x, pos_y, panel_width, panel_height)
    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill((8, 8, 18, 140))
    pygame.draw.rect(panel, (145, 145, 190, 130), panel.get_rect(), 1)
    title = highscore_font.render("Hall of Fame", True, GOLD)
    panel.blit(title, (10, 8))
    if not highscores:
        empty = highscore_font.render("Aucun score.", True, WHITE)
        panel.blit(empty, (10, 24))
    else:
        for idx, entry in enumerate(highscores[:max_rows]):
            row_y = 24 + idx * row_height
            row_color = WHITE
            if latest_highscore_stamp is not None and entry.get("stamp") == latest_highscore_stamp:
                row_color = CYAN
            rank = highscore_font.render(f"{idx+1}.", True, row_color)
            label = highscore_font.render(
                f"{entry.get('score', 0):>4}  {entry.get('result', 'Run')[:3].upper()}  {format_duration(entry.get('duration', -1))}",
                True,
                row_color,
            )
            panel.blit(rank, (8, row_y))
            panel.blit(label, (34, row_y))
    screen.blit(panel, panel_rect.topleft)

next_shot_allowed_time = 0
cooldown_time = 300

# Horloge pour contrôler le taux de rafraîchissement (60 FPS)
clock = pygame.time.Clock()

#
#
# État du jeu : MENU, STORY, ou PLAYING
game_state = "MENU"
menu_blink = True
menu_blink_time = pygame.time.get_ticks()

# Variables de clignotement pour l'écran PAUSE
pause_blink = True

pause_blink_time = pygame.time.get_ticks()

# Variables d'animation pour vie, score et eau
life_anim = {'active': False, 'index': None, 'start': 0, 'duration': 500}
score_blink = False
score_blink_time = pygame.time.get_ticks()
water_anim = {'active': False, 'start': 0, 'duration': 500}

# Variables pour le menu étendu
story_lines = [
    "AstroPaws: Gourmet Quest",
    "",
    "Quelque part dans le secteur L-88...",
    "Un signal d’urgence retentit depuis la station Alpha-Felis : la dernière réserve de Pâtée Galactique™ a disparu !",
    "Heureusement, AstroPaws — félin gourmet, cosmonaute téméraire et dernier espoir du Conseil des Chats — répond à l’appel.",
    "",
    "Sa mission ?",
    "Explorer les confins de l’espace, affronter une faune hostile et récupérer les 4 ingrédients sacrés de la recette ultime.",
    "",
    "Souris mutantes, rats radioactifs et chiens d’la casse n’ont qu’à bien se tenir...",
    "Car AstroPaws est en route, armé de son Jetpack et de ses jets d’eau ultra-puissants.",
    "",
    "Mais attention, chaque tir consomme de l’eau pure, précieuse et limitée.",
    "Et chaque erreur peut vous coûter des points… ou une vie.",
    "Ramassez des croquettes, évitez les pièges, et préparez-vous à affronter l’Impératrice Zibeline en personne.",
    "",
    "Gameplay",
    "   - Déplacez AstroPaws avec les flèches directionnelles.",
    "   - Tirez avec la barre Espace (consomme de l’eau).",
    "   - Ramassez des croquettes (points) et de l’eau (munitions).",
    "   - Esquivez les ennemis ou éliminez-les avec vos jets d’eau.",
    "   - Le jeu se termine si AstroPaws perd ses 9 vies.",
    "",
    "AstroPaws n’est pas un héros.",
    "C’est un chat.",
    "Mais parfois… c’est tout ce dont l’univers a besoin."
]
story_scroll_y = float(screen_height)
story_speed = 0.5  # pixels par frame

running = True
# --- Variables pour le chronomètre, bouclier, récompense ---
game_start_time = None
reward_shown = False
shield_charges = 0
shield_active = False
shield_start_time = None
shield_duration = 5000  # 5 secondes en ms
shield_last_granted_time = None  # timestamp de dernière attribution de charge
shield_cooldown = 30000         # 30 secondes de recharge
# Animation clignotante pour bouclier dans l'inventaire
shield_inv_anim = {'active': False, 'start': 0, 'duration': 1000}  # 1 seconde
hyper_charges = 0               # charges d'hyperespace
hyper_active = False
hyper_start_time = None
hyper_last_granted_time = None
hyper_unlocked = False
hyper_inv_anim = {'active': False, 'start': 0, 'duration': 1000}
hyper_last_fx_time = 0
astro_vx = 0.0
astro_vy = 0.0
astro_move_dx = 0.0
astro_move_dy = 0.0
astro_hit_flash_until = 0
oxidized_debuff_until = 0
gravity_pull_strength = 0.0
gravity_pull_planet = None
boss_active = False
boss_defeated = False
boss_data = {}
boss_projectiles = []
boss_contact_cooldown_until = 0
ingredients_collected = []      # liste des ingrédients collectés
ing_anim_active = False  # indique qu'un nouvel ingrédient doit être animé
ing_anim_start = 0       # timestamp du début de l'animation
ing_anim_duration = 1500  # durée de l'animation en ms
paused_time_accum = 0       # temps total passé en pause (ms)
pause_start_time = None     # timestamp du début de la pause

def reset_run_state(start_state="LEVEL_INTRO"):
    global astro_x, astro_y, astro_facing, astro_vx, astro_vy, astro_move_dx, astro_move_dy, astro_hit_flash_until
    global score, lives, water_ammo
    global game_start_time, reward_shown
    global shield_charges, shield_active, shield_start_time, shield_last_granted_time
    global hyper_charges, hyper_active, hyper_start_time, hyper_last_granted_time
    global hyper_unlocked, hyper_inv_anim, hyper_last_fx_time, oxidized_debuff_until
    global gravity_pull_strength, gravity_pull_planet
    global boss_active, boss_defeated, boss_data, boss_projectiles, boss_contact_cooldown_until
    global run_recorded, latest_highscore_stamp
    global ingredients_collected, ing_anim_active, ing_anim_start
    global paused_time_accum, pause_start_time, level_idx, game_state, next_shot_allowed_time
    global enemy_list, explosion_list, bullet_list, water_item_list, hyper_item_list, croquette_list

    astro_x = screen_width // 2
    astro_y = screen_height // 2
    astro_facing = "right"
    astro_vx = 0.0
    astro_vy = 0.0
    astro_move_dx = 0.0
    astro_move_dy = 0.0
    astro_hit_flash_until = 0

    score = 0
    lives = INITIAL_LIVES
    water_ammo = INITIAL_WATER_AMMO
    level_idx = 0
    next_shot_allowed_time = 0

    game_start_time = None
    reward_shown = False
    shield_charges = 0
    shield_active = False
    shield_start_time = None
    shield_last_granted_time = None
    hyper_charges = 0
    hyper_active = False
    hyper_start_time = None
    hyper_last_granted_time = None
    hyper_unlocked = False
    hyper_inv_anim = {'active': False, 'start': 0, 'duration': 1000}
    hyper_last_fx_time = 0
    oxidized_debuff_until = 0
    gravity_pull_strength = 0.0
    gravity_pull_planet = None
    boss_active = False
    boss_defeated = False
    boss_data = {}
    boss_projectiles = []
    boss_contact_cooldown_until = 0
    run_recorded = False
    latest_highscore_stamp = None
    ingredients_collected = []
    ing_anim_active = False
    ing_anim_start = 0
    paused_time_accum = 0
    pause_start_time = None

    enemy_list.clear()
    explosion_list.clear()
    bullet_list.clear()
    water_item_list.clear()
    hyper_item_list.clear()
    croquette_list = [spawn_croquette() for _ in range(INITIAL_CROQUETTES)]

    game_state = start_state

now = 0
while running:
    # Limiter le jeu à 60 images par seconde
    clock.tick(60)
    # Temps courant
    now = pygame.time.get_ticks()
    set_music(music_for_state(game_state))
    cooldown_time = get_shot_cooldown(level_idx, boss_active)
    # Initialiser le chronomètre au début du jeu
    if game_state == "PLAYING" and game_start_time is None:
        game_start_time = now
    # Déclencher la récompense à 30 secondes
    if game_state == "PLAYING" and not boss_active and not reward_shown and game_start_time is not None and now - game_start_time >= 30000:
        game_state = "REWARD"
        continue
    # Recharge automatique du bouclier toutes les shield_cooldown ms
    if game_state == "PLAYING" and reward_shown and shield_last_granted_time is not None and now - shield_last_granted_time >= shield_cooldown:
        shield_charges += 1
        shield_last_granted_time = now
        # Animer l'icône de bouclier dans l'inventaire
        shield_inv_anim['active'] = True
        shield_inv_anim['start'] = now
    # Fin du dash Hyperdrive
    if game_state == "PLAYING" and hyper_active and hyper_start_time is not None and now - hyper_start_time >= HYPER_DASH_DURATION:
        hyper_active = False
    # Recharge automatique de l'Hyperdrive après déblocage
    if game_state == "PLAYING" and hyper_unlocked and hyper_last_granted_time is not None and now - hyper_last_granted_time >= HYPER_COOLDOWN:
        hyper_charges += 1
        hyper_last_granted_time = now
        hyper_inv_anim['active'] = True
        hyper_inv_anim['start'] = now

    # === Écran INFO ===
    if game_state == "INFO":
        # Événements
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game_state = "MENU"
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONTROLLER_CONFIRM_BUTTONS or event.button in CONTROLLER_BACK_BUTTONS:
                    game_state = "MENU"
        # Fond uni pour l'écran INFO
        screen.fill(BLACK)
        # Animation de Dr Chat (bob vertical + rotation)
        now = pygame.time.get_ticks()
        angle = 5 * math.sin(now / 500)           # amplitude 5° en 1s
        y_bob = 10 + 10 * math.sin(now / 400)     # amplitude 10px en 0.8s
        rotated_doc = pygame.transform.rotate(doctor_image, angle)
        doc_rect = rotated_doc.get_rect(topright=(screen_width - 10, y_bob))
        screen.blit(rotated_doc, doc_rect)
        # Liste des entrées
        entries = [
            (heart_sprite,  "Vie : perdre 1 vie si touché par un chien."),
            (water_sprite,  "Eau : -1L par tir, ramasse bidon pour +10L."),
            (shield_icon,   "Bouclier (H) : 5s de protection, cooldown 30s."),
            (hyper_icon,    "Hyperdrive (J) : dash x3, invincibilité brève, cooldown 60s."),
            (ingredient_icon, "Ingrédient : collecte pour pâtée cosmique."),
            ((brown_croquette_sprite, gold_croquette_sprite), "Croquettes : +3pts (marron), +10pts (dorée)."),
            (mouse_sprite,  "Souris : 1 tir pour tuer, +10pts, collision -5pts."),
            (rat_sprite,    "Rat : 1 tir pour tuer, +20pts, collision -10pts."),
            (dog_sprite,    "Chien : 3 tirs pour tuer, +30pts, collision -1 vie."),
            (None,          f"Score requis : {levels.levels[0]['target_score']} -> N2, {levels.levels[1]['target_score']}-> N3, {levels.levels[2]['target_score']}-> Boss"),
            (None,          "N2+: gravite locale, croquettes oxydees + manette (A/X/Y/START), CRT (F/LB).")
        ]
        # Affichage
        y = 60
        for icon, text in entries:
            if icon:
                # si tuple d'icônes (croquettes marron+dorée)
                if isinstance(icon, tuple):
                    first, second = icon
                    # dessiner marron puis dorée
                    screen.blit(first, (50, y))
                    screen.blit(second, (50 + first.get_width() + 10, y))
                    x_text = 50 + first.get_width() + 10 + second.get_width() + 20
                else:
                    # cœur plus grand et ennemis à taille du chien
                    if icon == heart_sprite:
                        display_icon = pygame.transform.scale(icon, (40, 40))
                    elif icon in (mouse_sprite, rat_sprite):
                        display_icon = pygame.transform.scale(icon, dog_sprite.get_size())
                    else:
                        display_icon = icon
                    screen.blit(display_icon, (50, y))
                    x_text = 50 + display_icon.get_width() + 20
            else:
                x_text = 50
            # texte
            txt_surf = subtitle_font.render(text, True, WHITE)
            screen.blit(txt_surf, (x_text, y + 8))
            y += 50
        # Bas de page
        hint = subtitle_font.render("SPACE/A: retour  |  F/LB: filtre CRT", True, GREEN)
        # Remonter le message pour éviter chevauchement
        hint_rect = hint.get_rect(midbottom=(screen_width//2, screen_height - 10))
        screen.blit(hint, hint_rect)
        present_frame()
        continue

    # === Écran STORY ===
    if game_state == "STORY":
        # Gestion des événements pour sortir de la Story
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_RETURN):
                    story_scroll_y = float(screen_height)
                    game_state = "MENU"
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONTROLLER_CONFIRM_BUTTONS or event.button in CONTROLLER_BACK_BUTTONS:
                    story_scroll_y = float(screen_height)
                    game_state = "MENU"
        # Animer fond (étoiles+planètes)
        for star in star_list:
            star['x'] += star['speed']
            star['y'] += star['speed'] * 0.5
            if star['x'] > screen_width:
                star['x'] = 0
                star['y'] = random.randint(0, screen_height)
        for planet in planet_list:
            planet['x'] += planet['speed']
            planet['y'] += planet['speed'] * 0.2
            if planet['x'] > screen_width:
                planet['x'] = 0
                planet['y'] = random.randint(0, screen_height)
        screen.fill(BLACK)
        for star in star_list:
            pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
        for planet in planet_list:
            pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])
        # Préparer le texte wrapé
        display_lines = []
        for idx, line in enumerate(story_lines):
            color = GOLD if idx == 0 else WHITE
            if line == "":
                display_lines.append(("", color))
            else:
                for sub in textwrap.wrap(line, width=40):
                    display_lines.append((sub, color))
        # Afficher lignes défilantes
        line_height = 36
        for i, (text, color) in enumerate(display_lines):
            surf = score_font.render(text, True, color)
            rect = surf.get_rect(center=(screen_width//2, int(story_scroll_y + i*line_height)))
            screen.blit(surf, rect)
        story_scroll_y -= story_speed
        # Retour menu quand fini
        if story_scroll_y + len(display_lines)*line_height < 0:
            story_scroll_y = float(screen_height)
            game_state = "MENU"
        present_frame()
        continue

    # === Écran MENU ===
    if game_state == "MENU":
        # Gestion des événements pour quitter, démarrer ou story/info
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    reset_run_state("LEVEL_INTRO")
                elif event.key == pygame.K_s:
                    story_scroll_y = float(screen_height)
                    game_state = "STORY"
                elif event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_i:
                    game_state = "INFO"
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONTROLLER_CONFIRM_BUTTONS:
                    reset_run_state("LEVEL_INTRO")
                elif event.button == 3:
                    story_scroll_y = float(screen_height)
                    game_state = "STORY"
                elif event.button == 2:
                    game_state = "INFO"
                elif event.button in CONTROLLER_BACK_BUTTONS:
                    running = False
        # Animation de fond (étoiles et planètes)
        for star in star_list:
            star['x'] += star['speed']
            star['y'] += star['speed'] * 0.5
            if star['x'] > screen_width:
                star['x'] = 0
                star['y'] = random.randint(0, screen_height)
        for planet in planet_list:
            planet['x'] += planet['speed']
            planet['y'] += planet['speed'] * 0.2
            if planet['x'] > screen_width:
                planet['x'] = 0
                planet['y'] = random.randint(0, screen_height)
        # Affichage du fond étoilé
        screen.fill(BLACK)
        for star in star_list:
            pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
        for planet in planet_list:
            pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])
        # Afficher l'image d'accueil
        image_rect = welcome_image.get_rect(midtop=(screen_width//2, 50))
        screen.blit(welcome_image, image_rect)
        # Clignotement du texte
        now = pygame.time.get_ticks()
        if now - menu_blink_time > 500:
            menu_blink = not menu_blink
            menu_blink_time = now
        prompt_y_base = 50 + welcome_image.get_height() + 30
        if menu_blink:
            prompt = score_font.render("PRESS SPACE TO START", True, WHITE)
            prompt_rect = prompt.get_rect(center=(screen_width//2, prompt_y_base))
            screen.blit(prompt, prompt_rect)
        prompt2 = score_font.render("PRESS S FOR STORY", True, WHITE)
        prompt2_rect = prompt2.get_rect(center=(screen_width//2, prompt_y_base + 40))
        screen.blit(prompt2, prompt2_rect)
        prompt3 = score_font.render("PRESS Q TO QUIT", True, WHITE)
        prompt3_rect = prompt3.get_rect(center=(screen_width//2, prompt_y_base + 80))
        screen.blit(prompt3, prompt3_rect)
        prompt4 = score_font.render("PRESS I FOR INFO", True, WHITE)
        prompt4_rect = prompt4.get_rect(center=(screen_width//2, prompt_y_base + 120))
        screen.blit(prompt4, prompt4_rect)
        controller_label = "Controller: connecte" if active_controller else "Controller: clavier"
        controller_surf = subtitle_font.render(controller_label, True, CYAN if active_controller else WHITE)
        controller_rect = controller_surf.get_rect(center=(screen_width//2, prompt_y_base + 160))
        screen.blit(controller_surf, controller_rect)
        crt_state = "ON" if crt_filter_enabled else "OFF"
        crt_surf = subtitle_font.render(f"Filtre CRT (F/LB): {crt_state}", True, WHITE)
        crt_rect = crt_surf.get_rect(center=(screen_width//2, prompt_y_base + 192))
        screen.blit(crt_surf, crt_rect)
        draw_highscore_panel(screen_width - 316, 16, max_rows=4)
        # Affichage de la version (date.build) en bas à droite du menu
        version_surf = subtitle_font.render(f"Version {GAME_VERSION}", True, WHITE)
        version_rect = version_surf.get_rect(bottomright=(screen_width - 10, screen_height - 10))
        screen.blit(version_surf, version_rect)
        present_frame()
        continue
    # === Écran LEVEL_INTRO ===
    if game_state == "LEVEL_INTRO":
        # Gérer la sortie ou continuer
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    # Warp spatial avant de démarrer le niveau
                    warp_effect()
                    game_state = "PLAYING"
                elif event.key == pygame.K_q:
                    running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONTROLLER_CONFIRM_BUTTONS:
                    warp_effect()
                    game_state = "PLAYING"
                elif event.button in CONTROLLER_BACK_BUTTONS:
                    running = False
        # Fond étoilé
        screen.fill(BLACK)
        for star in star_list:
            pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
        for planet in planet_list:
            pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])
        # Numérotation du niveau
        level_str = f"Niveau {level_idx+1}"
        level_surf = score_font.render(level_str, True, WHITE)
        level_rect = level_surf.get_rect(center=(screen_width//2, 30))
        screen.blit(level_surf, level_rect)
        # Offset vertical pour placer le duel
        y_offset = 80

        # VS layout sous le titre
        # Animation de hochement de tête d'AstroPaws
        head_angle = 10 * math.sin(now / 300)  # amplitude 10°, période ~600ms
        rotated_head = pygame.transform.rotate(astro_head, head_angle)
        ah_rect = rotated_head.get_rect(center=(screen_width//4, y_offset + 80))
        screen.blit(rotated_head, ah_rect)
        vs_surf = score_font.render("VS.", True, YELLOW)
        vs_rect = vs_surf.get_rect(center=(screen_width//2, y_offset + 80))
        screen.blit(vs_surf, vs_rect)
        # Ennemi à droite avec animation de pulsation pour faire peur
        enemy_sprite = mouse_sprite if level_idx == 0 else rat_sprite if level_idx == 1 else dog_sprite
        # Calculer un facteur de pulsation sinusoïdal
        pulse = 1 + 0.1 * math.sin(now / 200)
        base_w, base_h = astro_head.get_size()
        anim_size = (int(base_w * pulse), int(base_h * pulse))
        animated_enemy = pygame.transform.scale(enemy_sprite, anim_size)
        eh_rect = animated_enemy.get_rect(center=(3 * screen_width // 4, y_offset + 80))
        screen.blit(animated_enemy, eh_rect)

        # Sous-titre descriptif (wrap si nécessaire)
        level_name = levels.levels[level_idx]['name']
        desc = f"AstroPaws contre {level_name}"
        wrapped_desc = textwrap.wrap(desc, width=60)
        for j, line in enumerate(wrapped_desc):
            surf = subtitle_font.render(line, True, WHITE)
            rect = surf.get_rect(center=(screen_width//2, y_offset + 160 + j*40))
            screen.blit(surf, rect)

        # Texte rigolo (wrap automatique)
        jokes = [
            "Elles viennes de la Lune Fromagère... et elles sont affamées !",
            "Une fuite nucléaire a réveillé leur appétit galactique.",
            "La langue pendante et les crocs acérés prêts à bouffer !",
        ]
        wrapped_joke = textwrap.wrap(jokes[level_idx], width=50)
        for k, line in enumerate(wrapped_joke):
            surf = subtitle_font.render(line, True, WHITE)
            rect = surf.get_rect(center=(screen_width//2, y_offset + 240 + k*40))
            screen.blit(surf, rect)

        # Poursuivre
        cont_surf = score_font.render("Press C / A to continue", True, GREEN)
        cont_rect = cont_surf.get_rect(center=(screen_width//2, screen_height - 50))
        screen.blit(cont_surf, cont_rect)
        present_frame()
        continue

    # === Écran BOSS_INTRO ===
    if game_state == "BOSS_INTRO":
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    warp_effect()
                    game_state = "PLAYING"
                elif event.key == pygame.K_q:
                    running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONTROLLER_CONFIRM_BUTTONS:
                    warp_effect()
                    game_state = "PLAYING"
                elif event.button in CONTROLLER_BACK_BUTTONS:
                    running = False

        screen.fill(BLACK)
        for star in star_list:
            pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
        for planet in planet_list:
            pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])

        title = score_font.render("ALERTE BOSS FINAL", True, RED)
        title_rect = title.get_rect(center=(screen_width // 2, 60))
        screen.blit(title, title_rect)

        boss_name = score_font.render("Imperatrice Zibeline", True, GOLD)
        boss_name_rect = boss_name.get_rect(center=(screen_width // 2, 110))
        screen.blit(boss_name, boss_name_rect)

        boss_preview = pygame.transform.smoothscale(dog_sprite, (180, 120))
        preview_rect = boss_preview.get_rect(center=(screen_width // 2, 240))
        screen.blit(boss_preview, preview_rect)
        pygame.draw.circle(screen, GOLD, (preview_rect.centerx, preview_rect.top - 8), 6)

        line1 = subtitle_font.render("Phases evolutives et rafales toxiques.", True, WHITE)
        line2 = subtitle_font.render("Survis, esquive, puis acheve-la au jet d'eau.", True, WHITE)
        line3 = subtitle_font.render("Dernier ingredient a gagner: Fragment Cosmique.", True, CYAN)
        screen.blit(line1, line1.get_rect(center=(screen_width // 2, 360)))
        screen.blit(line2, line2.get_rect(center=(screen_width // 2, 394)))
        screen.blit(line3, line3.get_rect(center=(screen_width // 2, 428)))

        cont_surf = score_font.render("Press C / A to engage", True, GREEN)
        cont_rect = cont_surf.get_rect(center=(screen_width//2, screen_height - 50))
        screen.blit(cont_surf, cont_rect)
        present_frame()
        continue

    # === Écran REWARD (Bouclier acquis) ===
    if game_state == "REWARD":
        # Fond étoilé
        screen.fill(BLACK)
        for star in star_list:
            pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
        for planet in planet_list:
            pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])
        # Texte de récompense
        text = score_font.render("Bouclier acquis !", True, CYAN)
        rect = text.get_rect(center=(screen_width//2, screen_height//2 - 50))
        screen.blit(text, rect)
        # Cercle bouclier
        pygame.draw.circle(screen, CYAN, (screen_width//2, screen_height//2 + 10), 50, 4)
        # Petite tête d'AstroPaws
        small = pygame.transform.scale(astro_sprite_right, (40, 40))
        srect = small.get_rect(center=(screen_width//2, screen_height//2 + 10))
        screen.blit(small, srect)
        # Informations sur le bouclier
        info1 = score_font.render("H / X pour activer le bouclier", True, WHITE)
        info1_rect = info1.get_rect(center=(screen_width//2, screen_height//2 + 80))
        screen.blit(info1, info1_rect)
        info2 = score_font.render(f"Durée: {shield_duration//1000}s   Utilisations: 1", True, WHITE)
        info2_rect = info2.get_rect(center=(screen_width//2, screen_height//2 + 120))
        screen.blit(info2, info2_rect)
        present_frame()
        pygame.time.delay(2000)
        # Octroi de la charge de bouclier
        shield_charges = 1
        shield_last_granted_time = now
        reward_shown = True
        shield_inv_anim['active'] = True
        shield_inv_anim['start'] = now
        game_state = "PLAYING"
        continue
    # === Écran PAUSE ===
    if game_state == "PAUSE":
        # Gestion des événements pour reprendre ou quitter
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    paused_time_accum += now - pause_start_time
                    pause_start_time = None
                    game_state = "PLAYING"
                elif event.key == pygame.K_q:
                    running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONTROLLER_CONFIRM_BUTTONS or event.button in CONTROLLER_PAUSE_BUTTONS:
                    paused_time_accum += now - pause_start_time
                    pause_start_time = None
                    game_state = "PLAYING"
                elif event.button in CONTROLLER_BACK_BUTTONS:
                    running = False
        # Affichage du menu pause
        screen.fill(BLACK)
        # Clignotement du titre PAUSE
        now = pygame.time.get_ticks()
        if now - pause_blink_time > 500:
            pause_blink = not pause_blink
            pause_blink_time = now
        # Stats en pause
        score_surface = score_font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_surface, (10, 10))
        # Afficher la quantité d'eau avec icône
        screen.blit(water_sprite, (10, 50))
        water_count = score_font.render(f"x{water_ammo}", True, WHITE)
        screen.blit(water_count, (10 + water_sprite.get_width() + 10, 50 + (water_sprite.get_height() - water_count.get_height())//2))
        # Afficher les vies sous forme de cœurs
        for i in range(lives):
            hx = 10 + i * (heart_sprite.get_width() + 5)
            hy = 50 + water_sprite.get_height() + 10
            screen.blit(heart_sprite, (hx, hy))
        # Inventaire en pause : icônes + compteurs
        inv_x = 10
        inv_y = 130
        # Bouclier
        screen.blit(shield_icon, (inv_x, inv_y))
        shield_count = score_font.render(f"x{shield_charges}", True, WHITE)
        screen.blit(shield_count, (inv_x + shield_icon.get_width() + 10, inv_y + 12))
        # Hyperdrive
        screen.blit(hyper_icon, (inv_x + 120, inv_y))
        hyper_color = YELLOW if hyper_active or (hyper_inv_anim['active'] and ((now - hyper_inv_anim['start']) // 250) % 2 == 0) else WHITE
        hyper_count = score_font.render(f"x{hyper_charges}", True, hyper_color)
        screen.blit(hyper_count, (inv_x + 120 + hyper_icon.get_width() + 10, inv_y + 12))
        # Ingrédients collectés : icône générique + sprites spécifiques clignotants
        base_x = inv_x + 240
        screen.blit(ingredient_icon, (base_x, inv_y))
        offset_x = base_x + ingredient_icon.get_width() + 10
        # Clignotement à 500ms
        blink_on = ((now // 500) % 2) == 0
        for idx, ing_key in enumerate(ingredients_collected):
            if not blink_on:
                break  # tout clignote ensemble, on peut stopper si off
            ing_sprite = ingredient_sprites.get(ing_key, ingredient_icon)
            x = offset_x + idx * (ing_sprite.get_width() + 10)
            screen.blit(ing_sprite, (x, inv_y))
        # Titre PAUSE clignotant
        if pause_blink:
            pause_surf = score_font.render("PAUSE", True, WHITE)
            pause_rect = pause_surf.get_rect(center=(screen_width//2, screen_height//3))
            screen.blit(pause_surf, pause_rect)
        # Options colorées
        resume_surf = score_font.render("Press P / START to resume", True, GREEN)
        resume_rect = resume_surf.get_rect(center=(screen_width//2, screen_height//2))
        screen.blit(resume_surf, resume_rect)
        quit_surf = score_font.render("Press Q / B to quit", True, RED)
        # Placer le texte "Quit" juste sous "Resume"
        quit_rect = quit_surf.get_rect(center=(screen_width//2, screen_height//2 + 60))
        screen.blit(quit_surf, quit_rect)
        # Afficher le chat endormi en bas de l'écran de pause
        chat_rect = chat_sleep_image.get_rect(midbottom=(screen_width//2, screen_height - 10))
        screen.blit(chat_sleep_image, chat_rect)
        present_frame()
        continue

    # === Écran GAME_OVER ===
    if game_state == "GAME_OVER":
        if not run_recorded:
            record_run_result("KO", now)
        # Gestion des événements
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_run_state("MENU")
                elif event.key == pygame.K_q:
                    running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONTROLLER_CONFIRM_BUTTONS:
                    reset_run_state("MENU")
                elif event.button in CONTROLLER_BACK_BUTTONS:
                    running = False
        # Affichage du fond spatial
        screen.fill(BLACK)
        for star in star_list:
            pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
        for planet in planet_list:
            pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])
        # Afficher l'image Game Over
        go_rect = gameover_image.get_rect(center=(screen_width//2, screen_height//2 - 50))
        screen.blit(gameover_image, go_rect)
        # Afficher les stats
        screen.blit(score_font.render(f"Score: {score}", True, WHITE), (10, 10))
        screen.blit(score_font.render(f"Water: {water_ammo}", True, WHITE), (10, 50))
        screen.blit(score_font.render(f"Lives: {lives}", True, WHITE), (10, 90))
        # Afficher les options
        r_surf = score_font.render("Press R / A to return to menu", True, GREEN)
        q_surf = score_font.render("Press Q / B to quit", True, RED)
        screen.blit(r_surf, r_surf.get_rect(center=(screen_width//2, screen_height//2 + 50)))
        screen.blit(q_surf, q_surf.get_rect(center=(screen_width//2, screen_height//2 + 100)))
        draw_highscore_panel(screen_width - 316, 16, max_rows=4)
        present_frame()
        continue

    # === Écran victoire finale ===
    if game_state == "FINAL_WIN":
        if not run_recorded:
            record_run_result("WIN", now)
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_run_state("LEVEL_INTRO")
                elif event.key == pygame.K_SPACE:
                    reset_run_state("MENU")
                elif event.key == pygame.K_q:
                    running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in CONTROLLER_CONFIRM_BUTTONS:
                    reset_run_state("LEVEL_INTRO")
                elif event.button == 2:
                    reset_run_state("MENU")
                elif event.button in CONTROLLER_BACK_BUTTONS:
                    running = False

        screen.fill(BLACK)
        for star in star_list:
            pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
        for planet in planet_list:
            pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])

        title = score_font.render("MISSION ACCOMPLIE !", True, GOLD)
        title_rect = title.get_rect(center=(screen_width//2, 70))
        screen.blit(title, title_rect)

        yw_rect = youwin_image.get_rect(center=(screen_width//2, screen_height//2 - 10))
        screen.blit(youwin_image, yw_rect)

        elapsed_seconds = max(0, (now - game_start_time - paused_time_accum) // 1000) if game_start_time else 0
        summary = subtitle_font.render(
            f"Score final: {score} | Ingredients: {len(ingredients_collected)} | Temps: {format_duration(elapsed_seconds)}",
            True,
            WHITE,
        )
        summary_rect = summary.get_rect(center=(screen_width//2, screen_height//2 + 112))
        screen.blit(summary, summary_rect)

        credits_y = screen_height // 2 + 140
        for idx, line in enumerate(credits_lines):
            credit_surf = subtitle_font.render(line, True, CYAN if idx % 2 == 0 else WHITE)
            credit_rect = credit_surf.get_rect(center=(screen_width // 2, credits_y + idx * 24))
            screen.blit(credit_surf, credit_rect)

        replay_surf = score_font.render("R/A: rejouer", True, GREEN)
        replay_rect = replay_surf.get_rect(center=(screen_width//2, screen_height//2 + 260))
        screen.blit(replay_surf, replay_rect)

        menu_surf = subtitle_font.render("SPACE/X: menu   Q/B: quitter", True, WHITE)
        menu_rect = menu_surf.get_rect(center=(screen_width//2, screen_height//2 + 300))
        screen.blit(menu_surf, menu_rect)
        draw_highscore_panel(screen_width - 316, 16, max_rows=6)

        present_frame()
        continue

    # === Écran JEU (PLAYING) ===
    # Gestion des événements
    for event in pygame.event.get():
        handle_global_event(event)
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                pause_start_time = now
                game_state = "PAUSE"
                break
            if event.key == pygame.K_h and shield_charges > 0 and not shield_active:
                shield_active = True
                shield_start_time = now
                shield_charges -= 1
                create_explosion(astro_x + 40, astro_y + 40, color=BLUE, num_particles=20)
            if event.key == pygame.K_j and hyper_charges > 0 and not hyper_active:
                hyper_active = True
                hyper_start_time = now
                hyper_last_fx_time = now
                hyper_charges -= 1
                hyper_last_granted_time = now
                hyper_inv_anim['active'] = True
                hyper_inv_anim['start'] = now
                create_explosion(astro_x + 40, astro_y + 40, color=YELLOW, num_particles=35)
                dash_impulse = speed * 1.8
                if astro_facing == "left":
                    astro_vx -= dash_impulse
                elif astro_facing == "right":
                    astro_vx += dash_impulse
                elif astro_facing == "up":
                    astro_vy -= dash_impulse
                else:
                    astro_vy += dash_impulse
                play_sound(hyper_dash_sound)
            if event.key == pygame.K_SPACE:
                current_time = pygame.time.get_ticks()
                keys = pygame.key.get_pressed()
                shot_x = 0.0
                shot_y = 0.0
                if keys[pygame.K_LEFT]:
                    shot_x -= 1.0
                if keys[pygame.K_RIGHT]:
                    shot_x += 1.0
                if keys[pygame.K_UP]:
                    shot_y -= 1.0
                if keys[pygame.K_DOWN]:
                    shot_y += 1.0
                if shot_x == 0.0 and shot_y == 0.0:
                    shot_x, shot_y = facing_to_vector(astro_facing)
                fire_player_bullet(shot_x, shot_y, current_time)
        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button in CONTROLLER_PAUSE_BUTTONS:
                pause_start_time = now
                game_state = "PAUSE"
                break
            if event.button in CONTROLLER_SHIELD_BUTTONS and shield_charges > 0 and not shield_active:
                shield_active = True
                shield_start_time = now
                shield_charges -= 1
                create_explosion(astro_x + 40, astro_y + 40, color=BLUE, num_particles=20)
            if event.button in CONTROLLER_HYPER_BUTTONS and hyper_charges > 0 and not hyper_active:
                hyper_active = True
                hyper_start_time = now
                hyper_last_fx_time = now
                hyper_charges -= 1
                hyper_last_granted_time = now
                hyper_inv_anim['active'] = True
                hyper_inv_anim['start'] = now
                create_explosion(astro_x + 40, astro_y + 40, color=YELLOW, num_particles=35)
                dash_impulse = speed * 1.8
                if astro_facing == "left":
                    astro_vx -= dash_impulse
                elif astro_facing == "right":
                    astro_vx += dash_impulse
                elif astro_facing == "up":
                    astro_vy -= dash_impulse
                else:
                    astro_vy += dash_impulse
                play_sound(hyper_dash_sound)
            if event.button in CONTROLLER_SHOOT_BUTTONS:
                current_time = pygame.time.get_ticks()
                shot_x, shot_y = get_controller_move_vector()
                if shot_x == 0.0 and shot_y == 0.0:
                    shot_x, shot_y = facing_to_vector(astro_facing)
                fire_player_bullet(shot_x, shot_y, current_time)

    # Gestion continue des touches (pour détecter plusieurs touches en même temps)
    keys = pygame.key.get_pressed()
    # Déplacement inertiel : accélération, friction, glisse spatiale.
    input_x = 0.0
    input_y = 0.0
    if keys[pygame.K_LEFT]:
        input_x -= 1.0
    if keys[pygame.K_RIGHT]:
        input_x += 1.0
    if keys[pygame.K_UP]:
        input_y -= 1.0
    if keys[pygame.K_DOWN]:
        input_y += 1.0
    pad_x, pad_y = get_controller_move_vector()
    input_x += pad_x
    input_y += pad_y
    input_x = max(-1.0, min(1.0, input_x))
    input_y = max(-1.0, min(1.0, input_y))
    if input_x != 0 and input_y != 0:
        input_x *= 0.7071
        input_y *= 0.7071

    if input_x < 0:
        astro_facing = "left"
    elif input_x > 0:
        astro_facing = "right"
    elif input_y < 0:
        astro_facing = "up"
    elif input_y > 0:
        astro_facing = "down"
    elif abs(astro_vx) + abs(astro_vy) > 0.35:
        if abs(astro_vx) >= abs(astro_vy):
            astro_facing = "right" if astro_vx > 0 else "left"
        else:
            astro_facing = "down" if astro_vy > 0 else "up"

    max_speed = speed * (HYPER_DASH_MULTIPLIER if hyper_active else 1)
    accel = ASTRO_ACCEL * (1.35 if hyper_active else 1.0)
    if now < oxidized_debuff_until:
        accel *= 0.72
        max_speed *= 0.82

    if input_x != 0:
        astro_vx += input_x * accel
    else:
        astro_vx *= ASTRO_FRICTION

    if input_y != 0:
        astro_vy += input_y * accel
    else:
        astro_vy *= ASTRO_FRICTION

    center_x = astro_x + astro_sprite_right.get_width() // 2
    center_y = astro_y + astro_sprite_right.get_height() // 2
    grav_dx, grav_dy, gravity_pull_planet, gravity_pull_strength = compute_planet_gravity_pull(
        center_x, center_y, level_idx
    )
    astro_vx += grav_dx
    astro_vy += grav_dy

    astro_vx *= ASTRO_DRAG
    astro_vy *= ASTRO_DRAG
    velocity_mag = math.hypot(astro_vx, astro_vy)
    if velocity_mag > max_speed:
        scale = max_speed / velocity_mag
        astro_vx *= scale
        astro_vy *= scale
    if abs(astro_vx) < 0.01:
        astro_vx = 0.0
    if abs(astro_vy) < 0.01:
        astro_vy = 0.0

    astro_move_dx = astro_vx
    astro_move_dy = astro_vy
    astro_x += astro_vx
    astro_y += astro_vy

    if hyper_active and now - hyper_last_fx_time >= 40:
        create_explosion(astro_x + 40, astro_y + 40, color=YELLOW, num_particles=8)
        hyper_last_fx_time = now

    # Wrap-around : traverser d'un bord à l'autre
    sprite_w = astro_sprite_right.get_width()
    sprite_h = astro_sprite_right.get_height()
    if astro_x > screen_width:
        astro_x = -sprite_w
    elif astro_x < -sprite_w:
        astro_x = screen_width
    if astro_y > screen_height:
        astro_y = -sprite_h
    elif astro_y < -sprite_h:
        astro_y = screen_height

    # Mise à jour de la position des tirs
    for bullet in bullet_list:
        bullet['rect'].x += bullet['dx']
        bullet['rect'].y += bullet['dy']
    bullet_list = [bullet for bullet in bullet_list if bullet['rect'].right > 0 and bullet['rect'].left < screen_width and bullet['rect'].bottom > 0 and bullet['rect'].top < screen_height]

    # Mise à jour des positions des étoiles pour effet parallaxe
    for star in star_list:
        star['x'] += star['speed']
        star['y'] += star['speed'] * 0.5
        if star['x'] > screen_width:
            star['x'] = 0
            star['y'] = random.randint(0, screen_height)

    # Mise à jour des positions des planètes
    for planet in planet_list:
        planet['x'] += planet['speed']
        planet['y'] += planet['speed'] * 0.2
        if planet['x'] > screen_width:
            planet['x'] = 0
            planet['y'] = random.randint(0, screen_height)

    # Spawn d'ennemis selon configuration du niveau
    level_conf = levels.levels[level_idx]
    spawn_chance = get_level_spawn_chance(level_idx, score, lives, boss_active)
    if not boss_active and random.random() < spawn_chance:
        # Choisir le type en fonction des poids du niveau
        spawn_weights = level_conf['spawn_weights']
        enemy_type = random.choices(
            population=list(spawn_weights.keys()),
            weights=list(spawn_weights.values())
        )[0]
        # Propriétés selon le type
        if enemy_type == 'dog':
            enemy_width, enemy_height, enemy_speed, enemy_health = 50, 50, 2, 3
        elif enemy_type == 'rat':
            enemy_width, enemy_height, enemy_speed, enemy_health = 30, 30, 3, 1  # rat tué en 1 jet
        else:  # 'mouse'
            enemy_width, enemy_height, enemy_speed, enemy_health = 20, 20, 4, 1
        # Déterminer le côté d'apparition
        side = random.choice(['left', 'right', 'top', 'bottom'])
        if side == 'left':
            x, y, dx, dy = -enemy_width, random.randint(0, screen_height - enemy_height), enemy_speed, 0
        elif side == 'right':
            x, y, dx, dy = screen_width, random.randint(0, screen_height - enemy_height), -enemy_speed, 0
        elif side == 'top':
            x, y, dx, dy = random.randint(0, screen_width - enemy_width), -enemy_height, 0, enemy_speed
        else:  # 'bottom'
            x, y, dx, dy = random.randint(0, screen_width - enemy_width), screen_height, 0, -enemy_speed
        # Ajouter l'ennemi
        enemy_list.append({
            'x': x, 'y': y, 'width': enemy_width, 'height': enemy_height,
            'type': enemy_type, 'dx': dx, 'dy': dy,
            'speed': enemy_speed, 'health': enemy_health,
            'bob_phase': random.uniform(0, 2 * math.pi),
            'anim_phase': random.uniform(0, 2 * math.pi),
            'spawn_time': now
        })
    # Mise à jour des ennemis
    new_enemy_list = []
    for enemy in enemy_list:
        enemy['x'] += enemy['dx']
        enemy['y'] += enemy['dy']
        if enemy['x'] + enemy['width'] > 0 and enemy['x'] < screen_width and enemy['y'] + enemy['height'] > 0 and enemy['y'] < screen_height:
            new_enemy_list.append(enemy)
    enemy_list = new_enemy_list

    # Mise à jour du boss final (mouvement, phases, tirs).
    if boss_active and boss_data:
        health_ratio = boss_data['health'] / max(1, boss_data['max_health'])
        if health_ratio > 0.66:
            boss_data['phase'] = 1
        elif health_ratio > 0.33:
            boss_data['phase'] = 2
        else:
            boss_data['phase'] = 3

        phase_speed = {1: 1.8, 2: 2.7, 3: 3.6}[boss_data['phase']]
        boss_data['x'] += boss_data['vx'] * phase_speed
        if boss_data['x'] <= 40:
            boss_data['x'] = 40
            boss_data['vx'] = 1
        elif boss_data['x'] + boss_data['width'] >= screen_width - 40:
            boss_data['x'] = screen_width - 40 - boss_data['width']
            boss_data['vx'] = -1
        boss_data['y'] = 90 + int(24 * math.sin(now / 380 + boss_data.get('seed', 0.0)))

        shot_cooldown = {1: 1200, 2: 850, 3: 620}[boss_data['phase']]
        if now - boss_data['last_shot'] >= shot_cooldown:
            spawn_boss_projectiles(now, (astro_x + 25, astro_y + 25))

        updated_boss_projectiles = []
        for projectile in boss_projectiles:
            projectile['x'] += projectile['dx']
            projectile['y'] += projectile['dy']
            projectile['lifetime'] -= 1
            if (
                projectile['lifetime'] > 0
                and -30 <= projectile['x'] <= screen_width + 30
                and -30 <= projectile['y'] <= screen_height + 30
            ):
                updated_boss_projectiles.append(projectile)
        boss_projectiles = updated_boss_projectiles

    # Collision entre les tirs (jet d'eau) et les ennemis
    new_bullet_list = []
    boss_defeated_this_frame = False
    for bullet in bullet_list:
        bullet_rect = bullet['rect']  # Le tir est maintenant dans bullet['rect']
        hit_enemy = False
        for enemy in enemy_list[:]:
            enemy_rect = pygame.Rect(enemy['x'], enemy['y'], enemy['width'], enemy['height'])
            if bullet_rect.colliderect(enemy_rect):
                # Décrémenter la santé de l'ennemi à chaque tir
                enemy['health'] -= 1
                # Si la santé tombe à zéro, l'ennemi est détruit
                if enemy['health'] <= 0:
                    if enemy['type'] == "rat":
                        enemy_color = (200, 0, 0)  # rouge foncé pour les rats
                        score += 20
                    elif enemy['type'] == "mouse":
                        enemy_color = (255, 100, 100)  # rouge clair pour les souris
                        score += 10
                    elif enemy['type'] == "dog":
                        enemy_color = (255, 0, 0)  # rouge pour les chiens
                        score += 30
                    create_explosion(enemy['x'] + enemy['width'] // 2, enemy['y'] + enemy['height'] // 2, color=enemy_color)
                    play_sound(explosion_sound)
                    enemy_list.remove(enemy)
                hit_enemy = True
                break
        if not hit_enemy and boss_active and boss_data:
            boss_rect = pygame.Rect(
                boss_data['x'], boss_data['y'], boss_data['width'], boss_data['height']
            )
            if bullet_rect.colliderect(boss_rect):
                boss_data['health'] -= 1
                create_explosion(
                    bullet_rect.centerx,
                    bullet_rect.centery,
                    color=(255, 110, 140),
                    num_particles=10,
                )
                if boss_data['health'] <= 0:
                    boss_defeated_this_frame = True
                hit_enemy = True
        if not hit_enemy:
            new_bullet_list.append(bullet)
    bullet_list = new_bullet_list

    if boss_defeated_this_frame:
        boss_active = False
        boss_defeated = True
        boss_projectiles.clear()
        create_explosion(
            boss_data['x'] + boss_data['width'] // 2,
            boss_data['y'] + boss_data['height'] // 2,
            color=RED,
            num_particles=120,
        )
        play_sound(explosion_sound)
        if "ingredient_fragment_croquette" not in ingredients_collected:
            ingredients_collected.append("ingredient_fragment_croquette")
            ing_anim_active = True
            ing_anim_start = now
        enemy_list.clear()
        croquette_list.clear()
        water_item_list.clear()
        hyper_item_list.clear()
        astro_vx = 0.0
        astro_vy = 0.0
        astro_move_dx = 0.0
        astro_move_dy = 0.0
        record_run_result("WIN", now)
        game_state = "FINAL_WIN"
        continue

    player_rect = pygame.Rect(astro_x, astro_y, 50, 50)

    # Collision entre AstroPaws et les ennemis
    for enemy in enemy_list[:]:
        enemy_rect = pygame.Rect(enemy['x'], enemy['y'], enemy['width'], enemy['height'])
        if player_rect.colliderect(enemy_rect):
            # Bouclier ou Hyperdrive actif : invincibilité temporaire
            if shield_active or hyper_active:
                fx_color = CYAN if shield_active else YELLOW
                fx_particles = 20 if shield_active else 30
                create_explosion(
                    enemy['x'] + enemy['width']//2,
                    enemy['y'] + enemy['height']//2,
                    color=fx_color,
                    num_particles=fx_particles
                )
                play_sound(explosion_sound)
                enemy_list.remove(enemy)
                continue
            astro_hit_flash_until = now + ASTRO_HIT_FLASH_DURATION
            if enemy['type'] == "dog":
                lives -= 1
                # Déclencher explosion du cœur retiré
                life_anim['active'] = True
                life_anim['index'] = lives  # index du cœur supprimé
                life_anim['start'] = pygame.time.get_ticks()
                # Explosion visuelle sur le cœur
                heart_x = screen_width - (heart_sprite.get_width() + 10) * (life_anim['index'] + 1) + heart_sprite.get_width()//2
                heart_y = 10 + heart_sprite.get_height()//2
                create_explosion(heart_x, heart_y, color=RED, num_particles=30)
                create_explosion(astro_x + 25, astro_y + 25, color=(255, 0, 0), num_particles=50)
                play_sound(explosion_sound)
                lost_life_surface = score_font.render("Vous avez perdu une vie!", True, WHITE)
                screen.blit(lost_life_surface, (screen_width//2 - 100, screen_height//2))
                present_frame()
                pygame.time.delay(1000)
            elif enemy['type'] == "rat":
                score -= 10
                create_explosion(astro_x + 25, astro_y + 25)
                play_sound(explosion_sound)
            else:  # mouse
                score -= 5
                create_explosion(astro_x + 25, astro_y + 25)
                play_sound(explosion_sound)
            enemy_list.remove(enemy)

    # Collision entre AstroPaws et les attaques du boss final.
    if boss_active and boss_data:
        boss_rect = pygame.Rect(
            boss_data['x'], boss_data['y'], boss_data['width'], boss_data['height']
        )
        if player_rect.colliderect(boss_rect):
            if shield_active or hyper_active:
                create_explosion(
                    boss_rect.centerx,
                    boss_rect.centery,
                    color=YELLOW if hyper_active else CYAN,
                    num_particles=20,
                )
            elif now >= boss_contact_cooldown_until:
                lives -= 1
                boss_contact_cooldown_until = now + 900
                astro_hit_flash_until = now + ASTRO_HIT_FLASH_DURATION
                create_explosion(astro_x + 25, astro_y + 25, color=RED, num_particles=45)
                play_sound(explosion_sound)

        for projectile in boss_projectiles[:]:
            radius = projectile['radius']
            proj_rect = pygame.Rect(
                projectile['x'] - radius,
                projectile['y'] - radius,
                radius * 2,
                radius * 2,
            )
            if player_rect.colliderect(proj_rect):
                if shield_active or hyper_active:
                    create_explosion(
                        projectile['x'],
                        projectile['y'],
                        color=CYAN if shield_active else YELLOW,
                        num_particles=12,
                    )
                elif now >= boss_contact_cooldown_until:
                    lives -= 1
                    boss_contact_cooldown_until = now + 900
                    astro_hit_flash_until = now + ASTRO_HIT_FLASH_DURATION
                    create_explosion(astro_x + 25, astro_y + 25, color=(255, 70, 90), num_particles=30)
                    play_sound(explosion_sound)
                boss_projectiles.remove(projectile)

    # Vérifier Game Over: si les vies tombent à 0
    if lives <= 0:
        # Passer en écran de Game Over
        record_run_result("KO", now)
        game_state = "GAME_OVER"
        continue

    # Mise à jour de la liste des croquettes
    current_time = pygame.time.get_ticks()
    if not boss_active:
        croquette_list = [
            croquette
            for croquette in croquette_list
            if current_time - croquette['spawn_time'] < croquette_lifetime
        ]

        # Apparition de nouvelles croquettes
        if random.random() < 0.01:  # environ 1% de chance par frame
            croquette_list.append(spawn_croquette())

        # Collision entre AstroPaws et les croquettes
        new_croquette_list = []
        for croquette in croquette_list:
            base_sprite = gold_croquette_sprite if croquette.get('type') == "rare" else brown_croquette_sprite
            croq_w, croq_h = base_sprite.get_size()
            croquette_rect = pygame.Rect(croquette['x'], croquette['y'], croq_w, croq_h)
            oxidized = is_croquette_oxidized(croquette, level_idx, current_time)
            if player_rect.colliderect(croquette_rect):
                play_sound(pickup_sound)
                if oxidized:
                    score += OXIDIZED_BONUS_SCORE
                    water_ammo = max(0, water_ammo - OXIDIZED_WATER_PENALTY)
                    oxidized_debuff_until = current_time + OXIDIZED_DEBUFF_DURATION
                    create_explosion(
                        croquette_rect.centerx,
                        croquette_rect.centery,
                        color=(160, 220, 90),
                        num_particles=18,
                    )
                elif croquette.get('type') == "rare":
                    score += 10  # croquette rare désormais 10 points
                else:
                    score += 3   # croquette normale désormais 3 points
            else:
                new_croquette_list.append(croquette)
        croquette_list = new_croquette_list
    else:
        croquette_list.clear()

    # Vérifier si on atteint le score cible du niveau
    target = levels.levels[level_idx]['target_score']
    if score >= target and not boss_active:
        is_last_level = level_idx == len(levels.levels) - 1
        if is_last_level and not boss_defeated:
            final_level_item = levels.levels[level_idx]['end_item']
            if final_level_item not in ingredients_collected:
                ingredients_collected.append(final_level_item)
                ing_anim_active = True
                ing_anim_start = now

            enemy_list.clear()
            bullet_list.clear()
            explosion_list.clear()
            croquette_list.clear()
            water_item_list.clear()
            hyper_item_list.clear()
            astro_vx = 0.0
            astro_vy = 0.0
            astro_move_dx = 0.0
            astro_move_dy = 0.0
            astro_hit_flash_until = 0
            start_boss_fight(now)
            continue

        # Animation de disparition du sprite mort sur 2 secondes
        # Préparez le message statique
        msg = score_font.render(f"{levels.levels[level_idx]['name']} terminé !", True, WHITE)
        msg_rect = msg.get_rect(center=(screen_width//2, screen_height//2 + 50))
        # Choisir le sprite mort
        if level_idx == 0:
            dead = mouse_dead_sprite
        elif level_idx == 1:
            dead = rat_dead_sprite
        else:
            dead = dog_dead_sprite
        # Animation
        anim_start = pygame.time.get_ticks()
        anim_duration = 2000  # ms
        while True:
            t = pygame.time.get_ticks() - anim_start
            if t >= anim_duration:
                break
            progress = t / anim_duration
            # Calculer la taille et l'alpha
            scale = 1.0 - 0.5 * progress
            w = max(1, int(dead.get_width() * scale))
            h = max(1, int(dead.get_height() * scale))
            anim_img = pygame.transform.scale(dead, (w, h))
            anim_img.set_alpha(int(255 * (1 - progress)))
            # Dessiner fond et sprite animé
            screen.fill(BLACK)
            # étoiles de fond
            for star in star_list:
                pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
            for planet in planet_list:
                pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])
            # sprite mort animé
            rect = anim_img.get_rect(center=(screen_width//2, screen_height//2 - 50))
            screen.blit(anim_img, rect)
            # message
            screen.blit(msg, msg_rect)
            present_frame()
            clock.tick(60)
        # Animer l'ajout de l'ingrédient
        ingredients_collected.append(levels.levels[level_idx]['end_item'])
        ing_anim_active = True
        ing_anim_start = now
        # Passer au niveau suivant.
        level_idx += 1
        game_state = "LEVEL_INTRO"

        enemy_list.clear()
        bullet_list.clear()
        explosion_list.clear()
        croquette_list.clear()
        water_item_list.clear()
        hyper_item_list.clear()
        croquette_list = [spawn_croquette() for _ in range(INITIAL_CROQUETTES)]
        game_start_time = None
        paused_time_accum = 0
        hyper_active = False
        hyper_start_time = None
        astro_vx = 0.0
        astro_vy = 0.0
        astro_move_dx = 0.0
        astro_move_dy = 0.0
        astro_hit_flash_until = 0
        continue

    # Mise à jour des réserves d'eau (water items)
    current_time = pygame.time.get_ticks()
    water_item_lifetime = 9000 if boss_active else 7000
    water_item_list = [
        item for item in water_item_list
        if current_time - item['spawn_time'] < water_item_lifetime
    ]
    if boss_active:
        hyper_item_list.clear()
    else:
        hyper_item_list = [
            item for item in hyper_item_list
            if current_time - item['spawn_time'] < HYPER_PICKUP_LIFETIME
        ]
    
    # Collision entre AstroPaws et les réserves d'eau
    for item in water_item_list[:]:
        # Utiliser la taille réelle du sprite pour la collision
        width = water_sprite.get_width()
        height = water_sprite.get_height()
        water_rect = pygame.Rect(item['x'], item['y'], width, height)
        if player_rect.colliderect(water_rect):
            water_ammo += 10
            # Déclencher clignotement du compteur d'eau
            water_anim['active'] = True
            water_anim['start'] = pygame.time.get_ticks()
            play_sound(pickup_sound)
            water_item_list.remove(item)
    
    # Apparition de nouvelles réserves d'eau
    water_spawn_chance = get_water_pickup_spawn_chance(level_idx, boss_active, water_ammo)
    if random.random() < water_spawn_chance:
        x = random.randint(0, screen_width - 10)
        y = random.randint(0, screen_height - 10)
        spawn_time = pygame.time.get_ticks()
        water_item_list.append({'x': x, 'y': y, 'spawn_time': spawn_time})

    # Collision entre AstroPaws et les pickups Hyperdrive
    for item in hyper_item_list[:]:
        width = hyper_pickup_sprite.get_width()
        height = hyper_pickup_sprite.get_height()
        hyper_rect = pygame.Rect(item['x'], item['y'], width, height)
        if player_rect.colliderect(hyper_rect):
            hyper_charges += 1
            hyper_unlocked = True
            hyper_last_granted_time = current_time
            hyper_inv_anim['active'] = True
            hyper_inv_anim['start'] = current_time
            create_explosion(
                item['x'] + width // 2,
                item['y'] + height // 2,
                color=YELLOW,
                num_particles=25
            )
            play_sound(hyper_pickup_sound)
            hyper_item_list.remove(item)

    # Apparition des pickups Hyperdrive (niveau qui porte l'item Hyperdrive)
    level_conf = levels.levels[level_idx]
    if (
        not boss_active
        and level_conf.get('item', {}).get('type') == 'hyperdrive'
        and len(hyper_item_list) < 1
        and random.random() < HYPER_PICKUP_SPAWN_CHANCE
    ):
        hw = hyper_pickup_sprite.get_width()
        hh = hyper_pickup_sprite.get_height()
        x = random.randint(0, screen_width - hw)
        y = random.randint(0, screen_height - hh)
        hyper_item_list.append({'x': x, 'y': y, 'spawn_time': current_time})

    # Mise à jour des particules d'explosion
    new_explosion_list = []
    for particle in explosion_list:
        particle['x'] += particle['dx']
        particle['y'] += particle['dy']
        particle['lifetime'] -= 1
        if particle['lifetime'] > 0:
            new_explosion_list.append(particle)
    explosion_list = new_explosion_list

    # Mettre à jour animations de score et d'eau
    now = pygame.time.get_ticks()
    # Score blink si négatif
    if score < 0:
        if now - score_blink_time > 500:
            score_blink = not score_blink
            score_blink_time = now
    else:
        score_blink = False
    # Arrêter animation eau
    if water_anim['active'] and now - water_anim['start'] > water_anim['duration']:
        water_anim['active'] = False
    # Arrêter animation inventaire bouclier
    if shield_inv_anim['active'] and now - shield_inv_anim['start'] > shield_inv_anim['duration']:
        shield_inv_anim['active'] = False
    if hyper_inv_anim['active'] and now - hyper_inv_anim['start'] > hyper_inv_anim['duration']:
        hyper_inv_anim['active'] = False

    # Affichage du fond spatial procédural avec teinte de niveau
    bg = levels.levels[level_idx]['bg_tint']
    screen.fill(bg)
    # Chronomètre mm:ss en haut-centre
    if game_start_time is not None:
        elapsed = (now - game_start_time - paused_time_accum) // 1000
        mins, secs = divmod(elapsed, 60)
        timer_surf = score_font.render(f"{mins:02d}:{secs:02d}", True, WHITE)
        timer_rect = timer_surf.get_rect(midtop=(screen_width//2, 10))
        screen.blit(timer_surf, timer_rect)
    # Dessiner les étoiles
    for star in star_list:
        pygame.draw.circle(screen, WHITE, (int(star['x']), int(star['y'])), 1)
    # Dessiner les planètes
    for planet in planet_list:
        pygame.draw.circle(screen, planet['color'], (int(planet['x']), int(planet['y'])), planet['size'])

    # Mettre à jour et dessiner les OVNIs décoratifs
    for ufo in ufo_list:
        ufo.update()
    for ufo in ufo_list:
        ufo.draw()

    # Dessiner les croquettes avec sprites
    for croquette in croquette_list:
        rare = croquette.get('type') == "rare"
        oxidized = is_croquette_oxidized(croquette, level_idx, now)
        if rare:
            sprite = gold_croquette_oxidized_sprite if oxidized else gold_croquette_sprite
        else:
            sprite = brown_croquette_oxidized_sprite if oxidized else brown_croquette_sprite

        if oxidized:
            pulse = 1.0 + 0.08 * math.sin(now / 110 + croquette['x'])
            w = max(1, int(sprite.get_width() * pulse))
            h = max(1, int(sprite.get_height() * pulse))
            animated = pygame.transform.smoothscale(sprite, (w, h))
            rect = animated.get_rect(
                center=(
                    croquette['x'] + sprite.get_width() // 2,
                    croquette['y'] + sprite.get_height() // 2,
                )
            )
            screen.blit(animated, rect.topleft)
            pygame.draw.circle(
                screen,
                (150, 220, 80),
                rect.center,
                max(rect.width, rect.height) // 2 + 3,
                1,
            )
        else:
            screen.blit(sprite, (croquette['x'], croquette['y']))
    # Dessiner les réserves d'eau avec sprite
    for item in water_item_list:
        screen.blit(water_sprite, (item['x'], item['y']))
    # Dessiner les pickups Hyperdrive avec un léger pulse
    pulse_factor = 1.0 + 0.12 * math.sin(now / 120)
    for item in hyper_item_list:
        base_w, base_h = hyper_pickup_sprite.get_size()
        w = max(1, int(base_w * pulse_factor))
        h = max(1, int(base_h * pulse_factor))
        sprite = pygame.transform.scale(hyper_pickup_sprite, (w, h))
        rect = sprite.get_rect(center=(item['x'] + base_w // 2, item['y'] + base_h // 2))
        screen.blit(sprite, rect.topleft)
    # Dessiner les ennemis avec animation avancée
    for enemy in enemy_list:
        draw_enemy_animated(enemy, now)
    # Dessiner le boss et ses projectiles
    if boss_active and boss_data:
        draw_boss(now)
        for projectile in boss_projectiles:
            pygame.draw.circle(
                screen,
                projectile['color'],
                (int(projectile['x']), int(projectile['y'])),
                projectile['radius'],
            )
    # Dessiner les particules d'explosion
    for particle in explosion_list:
        pygame.draw.circle(screen, particle['color'], (int(particle['x']), int(particle['y'])), 2)
    # Afficher les tirs (jet d'eau bleu)
    for bullet in bullet_list:
        pygame.draw.rect(screen, BLUE, bullet['rect'])
    # Afficher AstroPaws avec animation dynamique
    astro_rect = draw_astro_animated(
        now_ms=now,
        astro_pos_x=astro_x,
        astro_pos_y=astro_y,
        facing=astro_facing,
        move_dx=astro_move_dx,
        move_dy=astro_move_dy,
        hyper_on=hyper_active,
        hit_flash_until=astro_hit_flash_until,
    )
    # Dessiner les auras de protection autour d'AstroPaws
    center_x, center_y = astro_rect.center
    base_radius = max(astro_rect.width, astro_rect.height) // 2 + 5
    if shield_active:
        pygame.draw.circle(screen, CYAN, (center_x, center_y), base_radius, 3)
    if hyper_active:
        pulse = int(3 * math.sin(now / 70))
        pygame.draw.circle(screen, YELLOW, (center_x, center_y), base_radius + 6 + pulse, 3)
    
    # Afficher Score (clignote en rouge si score négatif)
    score_color = RED if (score < 0 and score_blink) else WHITE
    score_surface = score_font.render(f"Score: {score}", True, score_color)
    screen.blit(score_surface, (10, 10))
    # Afficher eau (clignote en bleu lors de collecte)
    water_color = BLUE if water_anim['active'] else WHITE
    water_surface = score_font.render(f"Water: {water_ammo}", True, water_color)
    screen.blit(water_surface, (10, 50))
    if gravity_pull_strength > 0:
        grav_pct = int(min(99, gravity_pull_strength * 550))
        grav_surface = subtitle_font.render(f"Gravite locale: {grav_pct}%", True, CYAN)
        screen.blit(grav_surface, (10, 92))
    if now < oxidized_debuff_until:
        corrosion_remaining = max(0.0, (oxidized_debuff_until - now) / 1000.0)
        corrosion_surf = subtitle_font.render(
            f"Corrosion: commandes perturbees ({corrosion_remaining:.1f}s)",
            True,
            (170, 230, 90),
        )
        screen.blit(corrosion_surf, (10, 124))
    # Afficher les vies sous forme de cœurs en haut à droite
    for i in range(lives):
        x = screen_width - (heart_sprite.get_width() + 10) * (i + 1)
        screen.blit(heart_sprite, (x, 10))
    if boss_active and boss_data:
        bw, bh = 320, 14
        bx, by = screen_width//2 - bw//2, 36
        ratio = max(0.0, boss_data['health']) / max(1, boss_data['max_health'])
        pygame.draw.rect(screen, WHITE, (bx, by, bw, bh), 2)
        pygame.draw.rect(screen, RED, (bx, by, int(bw * ratio), bh))
        boss_label = subtitle_font.render(
            f"{boss_data['name']} - Phase {boss_data['phase']}",
            True,
            WHITE,
        )
        label_rect = boss_label.get_rect(midbottom=(screen_width//2, by - 4))
        screen.blit(boss_label, label_rect)
    # Barre de bouclier si actif
    if shield_active:
        remaining = shield_duration - (now - shield_start_time)
        ratio = max(0, remaining) / shield_duration
        bw, bh = 200, 10
        bx, by = screen_width//2 - bw//2, 70
        pygame.draw.rect(screen, WHITE, (bx, by, bw, bh), 2)
        pygame.draw.rect(screen, BLUE, (bx, by, int(bw * ratio), bh))
        if remaining <= 0:
            shield_active = False
    if hyper_active and hyper_start_time is not None:
        remaining = HYPER_DASH_DURATION - (now - hyper_start_time)
        ratio = max(0, remaining) / HYPER_DASH_DURATION
        bw, bh = 200, 10
        bx, by = screen_width//2 - bw//2, 88
        pygame.draw.rect(screen, WHITE, (bx, by, bw, bh), 2)
        pygame.draw.rect(screen, YELLOW, (bx, by, int(bw * ratio), bh))
        if remaining <= 0:
            hyper_active = False

    # Affichage de l'inventaire en bas à gauche (icônes + compteurs)
    x0 = 10
    # Positionner l'inventaire 10px au-dessus du bord inférieur, en fonction de la hauteur de l'icône
    y0 = screen_height - shield_icon.get_height() - 10

    # Bouclier
    screen.blit(shield_icon, (x0, y0))
    # Clignotement du compteur de bouclier
    shield_color = CYAN if shield_inv_anim['active'] and ((now - shield_inv_anim['start']) // 250) % 2 == 0 else WHITE
    shield_count = score_font.render(f"x{shield_charges}", True, shield_color)
    # Position dynamique à droite de l'icône
    screen.blit(shield_count, (x0 + shield_icon.get_width() + 10, y0 + 4))

    # Hyperdrive
    screen.blit(hyper_icon, (x0 + 100, y0))
    hyper_color = YELLOW if hyper_active or (hyper_inv_anim['active'] and ((now - hyper_inv_anim['start']) // 250) % 2 == 0) else WHITE
    hyper_count = score_font.render(f"x{hyper_charges}", True, hyper_color)
    # Position dynamique à droite de l'icône
    screen.blit(hyper_count, (x0 + 100 + hyper_icon.get_width() + 10, y0 + 4))

    # Icône générique d'ingrédient (toujours présente)
    inv_base_x = x0 + 200
    screen.blit(ingredient_icon, (inv_base_x, y0))
    # Afficher les ingrédients collectés à droite de cette icône
    offset_x = inv_base_x + ingredient_icon.get_width() + 10
    for idx, ing_key in enumerate(ingredients_collected):
        ing_sprite = ingredient_sprites.get(ing_key, ingredient_icon)
        draw_sprite = ing_sprite
        # Animation de zoom pour le dernier ingrédient acquis
        if ing_anim_active and idx == len(ingredients_collected) - 1:
            t = now - ing_anim_start
            if t <= ing_anim_duration:
                factor = 1 + 1.0 * math.sin(math.pi * t / ing_anim_duration)
                w = int(ing_sprite.get_width() * factor)
                h = int(ing_sprite.get_height() * factor)
                draw_sprite = pygame.transform.scale(ing_sprite, (w, h))
            else:
                ing_anim_active = False
        # Calculer position centrée
        rect = draw_sprite.get_rect()
        pos_x = offset_x + idx * (ing_sprite.get_width() + 10) + (ing_sprite.get_width() - rect.width) // 2
        pos_y = y0 + (ing_sprite.get_height() - rect.height) // 2
        rect.topleft = (pos_x, pos_y)
        screen.blit(draw_sprite, rect)

    # Afficher le numéro de niveau en bas à droite
    level_label = "BOSS FINAL" if boss_active else f"Level {level_idx+1}"
    lvl_surf = score_font.render(level_label, True, WHITE)
    lvl_rect = lvl_surf.get_rect(bottomright=(screen_width - 10, screen_height - 10))
    screen.blit(lvl_surf, lvl_rect)

    # Actualiser l'affichage
    present_frame()

# Quitter Pygame proprement
pygame.quit()
sys.exit()
