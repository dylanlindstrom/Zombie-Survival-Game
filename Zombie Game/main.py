import pygame
import random
import math

pygame.init()

# ============================================================
# SCREEN / COLORS / FONTS
# ============================================================
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
HUD_HEIGHT = 76
PLAY_BOTTOM = SCREEN_HEIGHT - HUD_HEIGHT
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Zombie Survival")
clock = pygame.time.Clock()

WHITE = (245, 245, 245)
BLACK = (12, 14, 18)
RED = (220, 55, 55)
GREEN = (60, 205, 85)
BLUE = (70, 130, 240)
YELLOW = (245, 220, 65)
GRAY = (100, 108, 120)
DARK_GRAY = (35, 39, 47)
ORANGE = (255, 145, 45)
PURPLE = (185, 85, 230)
CYAN = (65, 225, 230)

font = pygame.font.SysFont(None, 34)
small_font = pygame.font.SysFont(None, 24)
tiny_font = pygame.font.SysFont(None, 19)
large_font = pygame.font.SysFont(None, 68)

# ============================================================
# GAME BALANCE (keeps your latest settings)
# ============================================================
PLAYER_W = PLAYER_H = 42
BASE_PLAYER_SPEED = 200
ZOMBIE_BASE_SPEED = 70
ZOMBIE_SPEED_INCREASE = 6
ZOMBIE_SPAWN_DELAY = 750
POWERUP_DROP_CHANCE = 0.07
SHOP_CHANCE = 0.25
ROUND_BREAK_MS = 5000
MYSTERY_ROUND_MS = 15000
BOX_ROLL_MS = 6000
BOX_COST = 950
POWERUP_LIFETIME = 10000
POWERUP_FLASH_MS = 3000
POWERUP_DURATION = 10000

# Weapon definitions. Damage is per bullet/pellet; zombie health = round number.
# Mystery-box weapons are intentionally stronger/specialized than shop weapons.
WEAPONS = {
    "Pistol":     {"kind":"bullet", "damage":1, "fire_ms":300, "speed":650, "mag":12, "reserve":128, "pellets":1, "spread":0.0, "reload_ms":1000, "cost":0, "shop":True, "color":YELLOW},
    "SMG":        {"kind":"bullet", "damage":1, "fire_ms":150, "speed":680, "mag":30, "reserve":240, "pellets":1, "spread":0.025, "reload_ms":1350, "cost":500, "shop":True, "color":YELLOW},
    "Shotgun":    {"kind":"bullet", "damage":2, "fire_ms":520, "speed":560, "mag":6, "reserve":84, "pellets":7, "spread":0.30, "reload_ms":1500, "cost":750, "shop":True, "color":ORANGE},
    "Rifle":      {"kind":"bullet", "damage":2, "fire_ms":300, "speed":900, "mag":20, "reserve":200, "pellets":1, "spread":0.01, "reload_ms":1500, "cost":1000, "shop":True, "color":YELLOW},
    "Ray Gun":    {"kind":"explosive", "damage":5, "fire_ms":550, "speed":720, "mag":20, "reserve":160, "pellets":1, "spread":0.0, "reload_ms":1700, "blast":85, "color":GREEN},
    "RPG":        {"kind":"explosive", "damage":12, "fire_ms":650, "speed":390, "mag":1, "reserve":12, "pellets":1, "spread":0.0, "reload_ms":2200, "blast":125, "color":ORANGE},
    "Galil":      {"kind":"bullet", "damage":3, "fire_ms":125, "speed":850, "mag":30, "reserve":180, "pellets":1, "spread":0.018, "reload_ms":1500, "color":YELLOW},
    "Commando":   {"kind":"bullet", "damage":3, "fire_ms":105, "speed":880, "mag":35, "reserve":210, "pellets":1, "spread":0.015, "reload_ms":1450, "color":YELLOW},
    "Thunder Gun":{"kind":"thunder", "damage":999, "fire_ms":1050, "speed":560, "mag":2, "reserve":12, "pellets":1, "spread":0.0, "reload_ms":2100, "color":CYAN},
    "Vulcano IV": {"kind":"bullet", "damage":2, "fire_ms":180, "speed":620, "mag":14, "reserve":102, "pellets":5, "spread":0.23, "reload_ms":1750, "color":ORANGE},
}
BOX_WEAPONS = ["Ray Gun", "RPG", "Galil", "Commando", "Thunder Gun", "Vulcano IV"]
SHOP_WEAPONS = ["SMG", "Shotgun", "Rifle", "Pistol"]

# ============================================================
# STATE
# ============================================================
def fresh_weapon(name):
    return {"name": name, "mag": WEAPONS[name]["mag"], "reserve": WEAPONS[name]["reserve"]}

player_x, player_y = 375.0, 245.0
player_health = max_health = 100
permanent_speed_multiplier = 1.0
damage_bonus = 0
score = kills = 0
round_number = 1
zombies = []              # dict: x, y, hp, knock_x, knock_y
bullets = []              # dict: x,y,dx,dy,weapon,damage,blast,color
powerups = []             # dict: x,y,type,born

weapon_slots = [fresh_weapon("Pistol"), None]
active_slot = 0
current_weapon = "Pistol"
last_shot_time = 0
mouse_held = False
reloading = False
reload_end_time = 0
reload_slot = None

zombies_required = 0
zombies_spawned = 0
last_spawn_time = 0
zombie_speed = ZOMBIE_BASE_SPEED

# phases: "playing", "round_break", "mystery", "box_animation", "shop", "game_over"
phase = "playing"
phase_start = 0
box_animation_start = 0
box_result = None
box_roll_count = 0
box_message = "Press E near the Mystery Box to roll"
shop_message = ""
last_damage_time = 0
DAMAGE_COOLDOWN = 1000

speed_boost_active = rapid_fire_active = laser_active = False
speed_boost_end_time = rapid_fire_end_time = laser_end_time = 0
last_laser_damage_time = 0

# ============================================================
# HELPERS
# ============================================================
def player_center():
    return player_x + PLAYER_W / 2, player_y + PLAYER_H / 2

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def draw_text(text, x, y, color=WHITE, use_font=small_font, center=False):
    surf = use_font.render(str(text), True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (int(x), int(y))
    else:
        rect.topleft = (int(x), int(y))
    screen.blit(surf, rect)
    return rect

def active_weapon_data():
    return WEAPONS[current_weapon]

def find_slot(name):
    for i, slot in enumerate(weapon_slots):
        if slot and slot["name"] == name:
            return i
    return None

def switch_slot(index):
    global active_slot, current_weapon, reloading, reload_slot
    if 0 <= index < 2 and weapon_slots[index]:
        active_slot = index
        current_weapon = weapon_slots[index]["name"]
        reloading = False
        reload_slot = None

def start_round():
    global zombies_required, zombies_spawned, last_spawn_time, zombie_speed, phase
    zombies.clear()
    bullets.clear()
    zombies_required = round_number * 8
    zombies_spawned = 0
    zombie_speed = ZOMBIE_BASE_SPEED + ((round_number - 1) // 2) * ZOMBIE_SPEED_INCREASE
    last_spawn_time = pygame.time.get_ticks() - ZOMBIE_SPAWN_DELAY
    phase = "playing"
    # Spawn a few enemies right away, as in the existing version.
    for _ in range(min(5, zombies_required)):
        spawn_zombie()
    last_spawn_time = pygame.time.get_ticks()

def spawn_zombie():
    global zombies_spawned
    for _ in range(100):
        side = random.randrange(4)
        if side == 0:
            x, y = random.randint(-150, SCREEN_WIDTH + 150), random.randint(-180, -45)
        elif side == 1:
            x, y = random.randint(-150, SCREEN_WIDTH + 150), random.randint(PLAY_BOTTOM + 45, PLAY_BOTTOM + 180)
        elif side == 2:
            x, y = random.randint(-180, -45), random.randint(-150, PLAY_BOTTOM + 150)
        else:
            x, y = random.randint(SCREEN_WIDTH + 45, SCREEN_WIDTH + 180), random.randint(-150, PLAY_BOTTOM + 150)
        pcx, pcy = player_center()
        if dist(x, y, pcx, pcy) < 250:
            continue
        if any(dist(x, y, z["x"], z["y"]) < 58 for z in zombies):
            continue
        zombies.append({"x": float(x), "y": float(y), "hp": round_number, "knock_x": 0.0, "knock_y": 0.0})
        zombies_spawned += 1
        return True
    # Fallback guarantees a spawn if the screen gets crowded.
    x = random.choice([-80, SCREEN_WIDTH + 80])
    y = random.randint(0, PLAY_BOTTOM)
    zombies.append({"x": float(x), "y": float(y), "hp": round_number, "knock_x": 0.0, "knock_y": 0.0})
    zombies_spawned += 1
    return True

def drop_powerup(x, y):
    if random.random() < POWERUP_DROP_CHANCE:
        ptype = random.choice(["NUKE", "SPEED", "HEAL", "RAPID", "LASER", "Max Ammo"])
        powerups.append({"x": x, "y": y, "type": ptype, "born": pygame.time.get_ticks()})

def kill_zombie(zombie):
    global score, kills
    if zombie in zombies:
        zombies.remove(zombie)
        score += 75
        kills += 1
        drop_powerup(zombie["x"], zombie["y"])

def damage_zombie(zombie, damage):
    zombie["hp"] -= damage + damage_bonus
    if zombie["hp"] <= 0:
        kill_zombie(zombie)

def explode(x, y, radius, damage):
    # Splash damage can hit every zombie in the radius.
    for zombie in zombies[:]:
        d = dist(x, y, zombie["x"], zombie["y"])
        if d <= radius:
            # Slight falloff toward the outer edge; always at least 1 damage.
            applied = max(1, int(damage * (1 - 0.35 * d / radius)))
            damage_zombie(zombie, applied)

def start_reload(now):
    global reloading, reload_end_time, reload_slot
    if reloading or phase != "playing":
        return
    slot = weapon_slots[active_slot]
    if not slot:
        return
    spec = WEAPONS[slot["name"]]
    if slot["mag"] >= spec["mag"] or slot["reserve"] <= 0:
        return
    reloading = True
    reload_end_time = now + spec["reload_ms"]
    reload_slot = active_slot

def finish_reload():
    global reloading, reload_slot
    if not reloading or reload_slot is None:
        return
    slot = weapon_slots[reload_slot]
    if slot:
        spec = WEAPONS[slot["name"]]
        needed = spec["mag"] - slot["mag"]
        amount = min(needed, slot["reserve"])
        slot["mag"] += amount
        slot["reserve"] -= amount
    reloading = False
    reload_slot = None

def shoot(now):
    global last_shot_time, reloading
    if phase != "playing" or reloading:
        return
    slot = weapon_slots[active_slot]
    if not slot:
        return
    name = slot["name"]
    spec = WEAPONS[name]
    delay = spec["fire_ms"] / (2 if rapid_fire_active else 1)
    if now - last_shot_time < delay:
        return
    if slot["mag"] <= 0:
        start_reload(now)
        return
    slot["mag"] -= 1
    last_shot_time = now
    px, py = player_center()
    mx, my = pygame.mouse.get_pos()
    angle = math.atan2(my - py, mx - px)
    for _ in range(spec.get("pellets", 1)):
        a = angle + random.uniform(-spec.get("spread", 0), spec.get("spread", 0))
        bullets.append({
            "x": px, "y": py, "dx": math.cos(a), "dy": math.sin(a),
            "weapon": name, "damage": spec["damage"], "speed": spec.get("speed", 600),
            "kind": spec["kind"], "blast": spec.get("blast", 0),
            "color": spec.get("color", YELLOW), "born": now
        })

def award_box_weapon(name):
    """Add weapon if a slot is free; otherwise ask which slot to replace."""
    global box_message
    existing = find_slot(name)
    if existing is not None:
        # A duplicate gives a small ammo refill instead of deleting a slot.
        slot = weapon_slots[existing]
        spec = WEAPONS[name]
        slot["reserve"] = min(slot["reserve"] + max(1, spec["reserve"] // 3), spec["reserve"] * 2)
        slot["mag"] = spec["mag"]
        box_message = f"Duplicate {name}: ammo replenished!"
        return
    if weapon_slots[0] is None:
        weapon_slots[0] = fresh_weapon(name)
        switch_slot(0)
        box_message = f"You got the {name}!"
    elif weapon_slots[1] is None:
        weapon_slots[1] = fresh_weapon(name)
        switch_slot(1)
        box_message = f"You got the {name}!"
    else:
        # Display replacement choice after the roll animation.
        box_message = f"You got {name}! Press 1 or 2 to replace that slot."
        global box_result
        box_result = name

def replace_slot(index):
    global box_result, box_message
    if box_result and index in (0, 1):
        name = box_result
        weapon_slots[index] = fresh_weapon(name)
        switch_slot(index)
        box_message = f"Slot {index + 1} replaced with {name}."
        box_result = None

def begin_box_roll(now):
    global score, phase, box_animation_start, box_result, box_roll_count, box_message
    if phase != "mystery" or box_result is not None:
        return
    if score < BOX_COST:
        box_message = f"Need {BOX_COST} points to roll."
        return
    score -= BOX_COST
    phase = "box_animation"
    box_animation_start = now
    box_result = random.choice(BOX_WEAPONS)
    box_roll_count += 1
    box_message = "The Mystery Box is choosing your weapon..."

def finish_box_roll():
    global phase, box_message, box_result
    # Keep the result separate while asking for a replacement if both slots are full.
    result = box_result
    if result is None:
        phase = "mystery"
        return
    if find_slot(result) is not None:
        award_box_weapon(result)
        box_result = None
    elif weapon_slots[0] is None or weapon_slots[1] is None:
        award_box_weapon(result)
        box_result = None
    else:
        box_message = f"You got {result}! Press 1 or 2 to replace a weapon."
    phase = "mystery"

def activate_powerup(ptype, now):
    global player_health, speed_boost_active, speed_boost_end_time
    global rapid_fire_active, rapid_fire_end_time, laser_active, laser_end_time
    if ptype == "NUKE":
        for z in zombies[:]:
            if 0 <= z["x"] <= SCREEN_WIDTH and 0 <= z["y"] <= PLAY_BOTTOM:
                kill_zombie(z)
    elif ptype == "SPEED":
        speed_boost_active = True
        speed_boost_end_time = now + POWERUP_DURATION
    elif ptype == "HEAL":
        player_health = max_health
    elif ptype == "RAPID":
        rapid_fire_active = True
        rapid_fire_end_time = now + POWERUP_DURATION
    elif ptype == "LASER":
        laser_active = True
        laser_end_time = now + POWERUP_DURATION
    elif ptype == "Max Ammo":
        for slot in weapon_slots:
            if slot:
                spec = WEAPONS[slot["name"]]
                slot["reserve"] = spec["reserve"]

def buy_shop_weapon(name):
    global score, shop_message
    spec = WEAPONS[name]
    if score < spec["cost"]:
        shop_message = "Not enough points."
        return
    existing = find_slot(name)
    if existing is not None:
        shop_message = "You already have that weapon."
        return
    if weapon_slots[0] is None:
        target = 0
    elif weapon_slots[1] is None:
        target = 1
    else:
        shop_message = "Both slots are full. Press 1 or 2 to replace a weapon."
        global pending_shop_weapon
        pending_shop_weapon = name
        return
    score -= spec["cost"]
    weapon_slots[target] = fresh_weapon(name)
    switch_slot(target)
    shop_message = f"Purchased {name}!"

pending_shop_weapon = None

def buy_upgrade(upgrade):
    global score, max_health, player_health, damage_bonus, permanent_speed_multiplier, shop_message
    costs = {"HEALTH":500, "DAMAGE":750, "SPEED":600}
    cost = costs[upgrade]
    if score < cost:
        shop_message = "Not enough points."
        return
    score -= cost
    if upgrade == "HEALTH":
        max_health += 25
        player_health = min(max_health, player_health + 25)
    elif upgrade == "DAMAGE":
        damage_bonus += 1
    elif upgrade == "SPEED":
        permanent_speed_multiplier += 0.2
    shop_message = f"Purchased {upgrade}!"

def reset_game():
    global player_x, player_y, player_health, max_health, permanent_speed_multiplier, damage_bonus
    global score, kills, round_number, phase, phase_start, active_slot, current_weapon
    global last_shot_time, mouse_held, reloading, reload_slot, last_damage_time
    global speed_boost_active, rapid_fire_active, laser_active, box_result, box_roll_count, pending_shop_weapon
    player_x, player_y = 375.0, 245.0
    max_health = player_health = 100
    permanent_speed_multiplier = 1.0
    damage_bonus = 0
    score = kills = 0
    round_number = 1
    weapon_slots[0] = fresh_weapon("Pistol")
    weapon_slots[1] = None
    active_slot = 0
    current_weapon = "Pistol"
    last_shot_time = 0
    mouse_held = False
    reloading = False
    reload_slot = None
    last_damage_time = 0
    speed_boost_active = rapid_fire_active = laser_active = False
    box_result = None
    box_roll_count = 0
    pending_shop_weapon = None
    zombies.clear(); bullets.clear(); powerups.clear()
    start_round()

# ============================================================
# DRAW HELPERS
# ============================================================
def draw_box():
    # Stylized animated crate, no external assets required.
    pulse = 5 * math.sin(pygame.time.get_ticks() / 180)
    x, y = 400, 260
    pygame.draw.ellipse(screen, (20, 70, 85), (x - 75, y + 42, 150, 30))
    pygame.draw.rect(screen, (115, 68, 32), (x - 58, y - 50, 116, 100), border_radius=8)
    pygame.draw.rect(screen, (185, 125, 55), (x - 58, y - 50, 116, 22), border_radius=6)
    pygame.draw.rect(screen, (65, 40, 25), (x - 8, y - 50, 16, 100))
    pygame.draw.rect(screen, (45, 40, 34), (x - 14, y - 6, 28, 25), border_radius=4)
    pygame.draw.circle(screen, CYAN, (x, y + 5), int(8 + pulse / 2))
    pygame.draw.rect(screen, (230, 190, 90), (x - 65, y - 60, 130, 8), border_radius=4)
    pygame.draw.rect(screen, CYAN, (x - 62, y - 62, 124, 4), border_radius=2)

def draw_hud():
    # bottom HUD background
    pygame.draw.rect(screen, (20, 23, 29), (0, PLAY_BOTTOM, SCREEN_WIDTH, HUD_HEIGHT))
    pygame.draw.line(screen, (75, 82, 95), (0, PLAY_BOTTOM), (SCREEN_WIDTH, PLAY_BOTTOM), 2)
    # health and score
    pygame.draw.rect(screen, (55, 58, 65), (14, 13, 180, 18), border_radius=4)
    health_w = int(180 * max(0, player_health) / max(1, max_health))
    pygame.draw.rect(screen, RED if player_health < 35 else GREEN, (14, 13, health_w, 18), border_radius=4)
    draw_text(f"HP {player_health}/{max_health}", 202, 10, WHITE, tiny_font)
    draw_text(f"ROUND {round_number}", 14, 37, WHITE, small_font)
    draw_text(f"SCORE {score}", 180, 37, YELLOW, small_font)
    draw_text(f"KILLS {kills}", 330, 37, WHITE, small_font)
    # weapon slots with name above mag/reserve
    for i, slot in enumerate(weapon_slots):
        x = 465 + i * 165
        selected = i == active_slot
        pygame.draw.rect(screen, (55, 66, 78) if selected else (32, 36, 43), (x, PLAY_BOTTOM + 8, 153, 60), border_radius=6)
        if selected:
            pygame.draw.rect(screen, CYAN, (x, PLAY_BOTTOM + 8, 153, 60), 2, border_radius=6)
        if slot:
            name = slot["name"]
            draw_text(f"{i+1}: {name}", x + 8, PLAY_BOTTOM + 13, CYAN if selected else WHITE, tiny_font)
            draw_text(f"{slot['mag']} / {slot['reserve']}", x + 8, PLAY_BOTTOM + 36, WHITE, small_font)
            if selected and reloading:
                draw_text("RELOADING", x + 146, PLAY_BOTTOM + 48, ORANGE, tiny_font, center=True)
        else:
            draw_text(f"{i+1}: EMPTY", x + 8, PLAY_BOTTOM + 20, GRAY, small_font)
    # power-up timers
    y = 42
    for active, end, label, color in [
        (speed_boost_active, speed_boost_end_time, "SPEED", BLUE),
        (rapid_fire_active, rapid_fire_end_time, "RAPID", YELLOW),
        (laser_active, laser_end_time, "LASER", CYAN),
    ]:
        if active:
            secs = max(0, (end - pygame.time.get_ticks()) / 1000)
            draw_text(f"{label} {secs:.1f}s", 520, y, color, tiny_font)
            y += 19

def draw_shop():
    screen.fill(DARK_GRAY)
    draw_text("SHOP INTERMISSION", 400, 40, WHITE, large_font, center=True)
    draw_text(f"Points: {score}", 30, 25, YELLOW, font)
    weapon_rects = {"SMG":(65,135,320,62), "Shotgun":(415,135,320,62), "Rifle":(65,215,320,62), "Pistol":(415,215,320,62)}
    for name, rect in weapon_rects.items():
        pygame.draw.rect(screen, GRAY, rect, border_radius=6)
        label = f"{name} - OWNED" if find_slot(name) is not None else f"{name} - {WEAPONS[name]['cost']} pts"
        draw_text(label, rect[0]+15, rect[1]+19, WHITE, small_font)
    upgrades = {"HEALTH":(65,315,205,55), "DAMAGE":(297,315,205,55), "SPEED":(529,315,205,55)}
    costs = {"HEALTH":500,"DAMAGE":750,"SPEED":600}
    for name, rect in upgrades.items():
        pygame.draw.rect(screen, (75, 82, 95), rect, border_radius=6)
        draw_text(f"{name} {costs[name]}", rect[0]+12, rect[1]+17, WHITE, small_font)
    draw_text(shop_message or "Buy an item, then press SPACE to continue", 400, 425, CYAN, small_font, center=True)
    draw_text("If both weapon slots are full, press 1 or 2 to replace one", 400, 465, WHITE, tiny_font, center=True)
    draw_text("SPACE: continue", 400, 520, YELLOW, font, center=True)

def draw_game_over():
    shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 190)); screen.blit(shade, (0, 0))
    draw_text("GAME OVER", 400, 170, RED, large_font, center=True)
    draw_text(f"Score: {score}     Kills: {kills}", 400, 255, WHITE, font, center=True)
    pygame.draw.rect(screen, GRAY, (300, 350, 200, 60), border_radius=8)
    draw_text("PLAY AGAIN", 400, 380, WHITE, font, center=True)

# ============================================================
# BEGIN GAME
# ============================================================
start_round()
running = True

while running:
    dt = min(clock.tick(60) / 1000, 0.04)
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if phase == "game_over":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    reset_game()
            elif phase == "playing":
                if event.key == pygame.K_1: switch_slot(0)
                elif event.key == pygame.K_2:
                    if pending_shop_weapon:
                        weapon_slots[1] = fresh_weapon(pending_shop_weapon)
                        switch_slot(1)
                        shop_message = f"Replaced slot 2 with {pending_shop_weapon}."
                        pending_shop_weapon = None
                    else: switch_slot(1)
                elif event.key == pygame.K_r: start_reload(now)
            elif phase == "mystery":
                if event.key == pygame.K_e and dist(*player_center(), 400, 260) < 120:
                    if box_result is not None:
                        if event.key == pygame.K_1: replace_slot(0)
                        elif event.key == pygame.K_2: replace_slot(1)
                    else:
                        begin_box_roll(now)
                elif box_result is not None and event.key == pygame.K_1:
                    replace_slot(0)
                elif box_result is not None and event.key == pygame.K_2:
                    replace_slot(1)
                elif event.key == pygame.K_SPACE:
                    # No skipping the timed intermission; SPACE is intentionally ignored.
                    pass
            elif phase == "box_animation":
                pass
            elif phase == "shop":
                if event.key == pygame.K_SPACE:
                    round_number += 1
                    start_round()
                elif event.key == pygame.K_1 and pending_shop_weapon:
                    weapon_slots[0] = fresh_weapon(pending_shop_weapon)
                    switch_slot(0); pending_shop_weapon = None
                    shop_message = "Weapon replaced in slot 1."
                elif event.key == pygame.K_2 and pending_shop_weapon:
                    weapon_slots[1] = fresh_weapon(pending_shop_weapon)
                    switch_slot(1); pending_shop_weapon = None
                    shop_message = "Weapon replaced in slot 2."

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if phase == "game_over":
                if 300 <= mx <= 500 and 350 <= my <= 410:
                    reset_game()
            elif phase == "playing":
                mouse_held = True
            elif phase == "shop":
                weapon_rects = {"SMG":(65,135,320,62), "Shotgun":(415,135,320,62), "Rifle":(65,215,320,62), "Pistol":(415,215,320,62)}
                for name, rect in weapon_rects.items():
                    x,y,w,h = rect
                    if x <= mx <= x+w and y <= my <= y+h:
                        buy_shop_weapon(name)
                upgrades = {"HEALTH":(65,315,205,55), "DAMAGE":(297,315,205,55), "SPEED":(529,315,205,55)}
                for name, rect in upgrades.items():
                    x,y,w,h = rect
                    if x <= mx <= x+w and y <= my <= y+h:
                        buy_upgrade(name)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouse_held = False

    if phase == "game_over":
        screen.fill(BLACK)
        draw_game_over()
        pygame.display.flip()
        continue

    if phase == "shop":
        draw_shop()
        pygame.display.flip()
        continue

    # Mystery box intermission runs for 15 seconds from phase start.
    if phase in ("mystery", "box_animation"):
        if now - phase_start >= MYSTERY_ROUND_MS:
            box_result = None
            round_number += 1
            start_round()
        elif phase == "box_animation" and now - box_animation_start >= BOX_ROLL_MS:
            finish_box_roll()
        # Allow movement around the box during the intermission.
        keys = pygame.key.get_pressed()
        speed = BASE_PLAYER_SPEED * permanent_speed_multiplier
        if speed_boost_active: speed *= 2
        if keys[pygame.K_w]: player_y -= speed * dt
        if keys[pygame.K_s]: player_y += speed * dt
        if keys[pygame.K_a]: player_x -= speed * dt
        if keys[pygame.K_d]: player_x += speed * dt
        player_x = max(0, min(SCREEN_WIDTH - PLAYER_W, player_x))
        player_y = max(0, min(PLAY_BOTTOM - PLAYER_H, player_y))
        screen.fill((12, 19, 28))
        draw_box()
        draw_text("MYSTERY BOX ROUND", 400, 45, CYAN, large_font, center=True)
        seconds = max(0, math.ceil((MYSTERY_ROUND_MS - (now - phase_start)) / 1000))
        draw_text(f"Time left: {seconds}s", 400, 95, YELLOW, font, center=True)
        draw_text(f"Cost: {BOX_COST} points per roll", 400, 135, WHITE, small_font, center=True)
        if phase == "box_animation":
            elapsed = now - box_animation_start
            draw_text("THE BOX IS SPINNING...", 400, 390, ORANGE, font, center=True)
            # Rapid weapon-name flicker during the animation; actual result appears at end.
            preview = random.choice(BOX_WEAPONS)
            draw_text(preview, 400, 430, WHITE, font, center=True)
            draw_text(f"{max(0, math.ceil((BOX_ROLL_MS-elapsed)/1000))}", 400, 475, YELLOW, large_font, center=True)
        else:
            draw_text("Move close and press E to roll", 400, 385, WHITE, font, center=True)
            draw_text(box_message, 400, 425, YELLOW, small_font, center=True)
            if box_result:
                draw_text("Press 1 or 2 to replace a weapon", 400, 458, ORANGE, small_font, center=True)
        # Player marker
        pygame.draw.rect(screen, RED, (int(player_x), int(player_y), PLAYER_W, PLAYER_H), border_radius=5)
        draw_hud()
        pygame.display.flip()
        continue

    # Temporary power-up timers
    if speed_boost_active and now >= speed_boost_end_time: speed_boost_active = False
    if rapid_fire_active and now >= rapid_fire_end_time: rapid_fire_active = False
    if laser_active and now >= laser_end_time: laser_active = False
    if reloading and now >= reload_end_time: finish_reload()

    # Player movement
    keys = pygame.key.get_pressed()
    speed = BASE_PLAYER_SPEED * permanent_speed_multiplier
    if speed_boost_active: speed *= 2
    if keys[pygame.K_w]: player_y -= speed * dt
    if keys[pygame.K_s]: player_y += speed * dt
    if keys[pygame.K_a]: player_x -= speed * dt
    if keys[pygame.K_d]: player_x += speed * dt
    player_x = max(0, min(SCREEN_WIDTH - PLAYER_W, player_x))
    player_y = max(0, min(PLAY_BOTTOM - PLAYER_H, player_y))

    # Shooting
    if mouse_held:
        shoot(now)

    # Spawn remaining zombies at the configured delay
    if zombies_spawned < zombies_required and now - last_spawn_time >= ZOMBIE_SPAWN_DELAY:
        spawn_zombie()
        last_spawn_time = now

    # Zombie movement, separation, and knockback
    for z in zombies:
        pcx, pcy = player_center()
        dx, dy = pcx - z["x"], pcy - z["y"]
        length = math.hypot(dx, dy) or 1
        dx, dy = dx / length, dy / length
        sx = sy = 0.0
        for other in zombies:
            if other is z: continue
            ox, oy = z["x"] - other["x"], z["y"] - other["y"]
            d = math.hypot(ox, oy)
            if 0 < d < 62:
                sx += ox / d
                sy += oy / d
        mx = dx + sx * (70 / max(zombie_speed, 1))
        my = dy + sy * (70 / max(zombie_speed, 1))
        ml = math.hypot(mx, my) or 1
        z["x"] += (mx / ml * zombie_speed + z["knock_x"]) * dt
        z["y"] += (my / ml * zombie_speed + z["knock_y"]) * dt
        z["knock_x"] *= max(0, 1 - 4 * dt)
        z["knock_y"] *= max(0, 1 - 4 * dt)

    # Move projectiles; every projectile stores its own weapon properties.
    for b in bullets[:]:
        b["x"] += b["dx"] * b["speed"] * dt
        b["y"] += b["dy"] * b["speed"] * dt
        hit = None
        for z in zombies:
            if dist(b["x"], b["y"], z["x"], z["y"]) < 25:
                hit = z
                break
        if hit:
            if b["kind"] == "explosive":
                explode(b["x"], b["y"], b["blast"], b["damage"])
            elif b["kind"] == "thunder":
                # Wide moving air blast: kills a broad cone and shoves survivors back.
                angle = math.atan2(b["dy"], b["dx"])
                for z in zombies[:]:
                    vx, vy = z["x"] - b["x"], z["y"] - b["y"]
                    d = math.hypot(vx, vy)
                    if d < 150:
                        if d < 120:
                            damage_zombie(z, 999)
                        else:
                            n = d or 1
                            z["knock_x"] += (vx / n) * 850
                            z["knock_y"] += (vy / n) * 850
            else:
                damage_zombie(hit, b["damage"])
            if b in bullets: bullets.remove(b)
            continue
        if b["x"] < -220 or b["x"] > SCREEN_WIDTH + 220 or b["y"] < -220 or b["y"] > PLAY_BOTTOM + 220:
            bullets.remove(b)

    # Continuous piercing laser power-up
    if laser_active and now - last_laser_damage_time >= 100:
        last_laser_damage_time = now
        px, py = player_center()
        mx, my = pygame.mouse.get_pos()
        angle = math.atan2(my - py, mx - px)
        ux, uy = math.cos(angle), math.sin(angle)
        for z in zombies[:]:
            vx, vy = z["x"] - px, z["y"] - py
            forward = vx * ux + vy * uy
            side = abs(vx * uy - vy * ux)
            if 0 <= forward <= 900 and side < 22:
                damage_zombie(z, 1)

    # Zombie contact damage
    pcx, pcy = player_center()
    for z in zombies:
        if dist(pcx, pcy, z["x"], z["y"]) < 43 and now - last_damage_time >= DAMAGE_COOLDOWN:
            player_health -= 20
            last_damage_time = now
            if player_health <= 0:
                player_health = 0
                phase = "game_over"
                mouse_held = False
            break

    # Collect / expire power-ups
    pcx, pcy = player_center()
    for p in powerups[:]:
        age = now - p["born"]
        if age >= POWERUP_LIFETIME:
            powerups.remove(p)
            continue
        if dist(pcx, pcy, p["x"], p["y"]) < 38:
            activate_powerup(p["type"], now)
            powerups.remove(p)

    # Round complete: increment once, then mystery box round every round.
    if zombies_spawned >= zombies_required and not zombies and phase == "playing":
        round_number += 1
        bullets.clear()
        if random.random() < SHOP_CHANCE:
            phase = "shop"
            shop_message = ""
            pending_shop_weapon = None
        else:
            phase = "mystery"
            phase_start = now
            box_roll_count = 0
            box_result = None
            box_message = "Press E near the box to roll"

    # ========================================================
    # DRAW PLAYING SCREEN
    # ========================================================
    screen.fill(BLACK)

    for b in bullets:
        if b["kind"] == "explosive":
            pygame.draw.circle(screen, b["color"], (int(b["x"]), int(b["y"])), 8)
            pygame.draw.circle(screen, WHITE, (int(b["x"]), int(b["y"])), 3)
        elif b["kind"] == "thunder":
            pygame.draw.circle(screen, CYAN, (int(b["x"]), int(b["y"])), 20)
            pygame.draw.circle(screen, WHITE, (int(b["x"]), int(b["y"])), 9)
        else:
            pygame.draw.circle(screen, b["color"], (int(b["x"]), int(b["y"])), 4)

    for z in zombies:
        pygame.draw.rect(screen, GREEN, (int(z["x"] - 20), int(z["y"] - 20), 40, 40), border_radius=5)
        # small health bar
        pygame.draw.rect(screen, RED, (int(z["x"] - 20), int(z["y"] - 28), 40, 4))
        pygame.draw.rect(screen, YELLOW, (int(z["x"] - 20), int(z["y"] - 28), int(40 * max(0, z["hp"]) / max(1, round_number)), 4))

    for p in powerups:
        age = now - p["born"]
        if age >= POWERUP_LIFETIME - POWERUP_FLASH_MS and (age // 200) % 2:
            continue
        color = {"NUKE":RED,"SPEED":BLUE,"HEAL":GREEN,"RAPID":YELLOW,"LASER":CYAN,"Max Ammo":PURPLE}[p["type"]]
        pygame.draw.circle(screen, color, (int(p["x"]), int(p["y"])), 15)
        draw_text(p["type"], p["x"], p["y"] - 28, WHITE, tiny_font, center=True)

    pygame.draw.rect(screen, RED, (int(player_x), int(player_y), PLAYER_W, PLAYER_H), border_radius=5)
    px, py = player_center()
    mx, my = pygame.mouse.get_pos()
    pygame.draw.line(screen, WHITE, (int(px), int(py)), (mx, my), 1)
    if laser_active:
        pygame.draw.line(screen, CYAN, (int(px), int(py)), (mx, my), 8)
        pygame.draw.line(screen, WHITE, (int(px), int(py)), (mx, my), 2)

    draw_hud()
    pygame.display.flip()

pygame.quit()
