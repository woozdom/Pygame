import pygame
import random
import math
import sys

# Inisialisasi Pygame dan Mixer
pygame.init()
pygame.mixer.init()

# Setting
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
BIRD_RADIUS = 15
BIRD_SPEED = 4
SPIKE_HEIGHT = 20
SIDE_SPIKE_SIZE = 20
RESPAWN_DELAY_MS = 3000
WINNING_SCORE = 10

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# Hukum Fisika
GRAVITY = 0.5
JUMP_STRENGTH = -8

# Assets
player_img = pygame.image.load('Assets/player.png').convert_alpha()
player2_img = pygame.image.load('Assets/player2.png').convert_alpha()
easter_egg_img = pygame.image.load('Assets/easter_egg.png').convert_alpha()
easter_egg_img = pygame.transform.scale(easter_egg_img, (SCREEN_WIDTH, SCREEN_HEIGHT))

easter_egg_sfx = pygame.mixer.Sound('Assets/easter_egg.mp3')
jump_sfx = pygame.mixer.Sound('Assets/jump.ogg')
bounce_sfx = pygame.mixer.Sound('Assets/bounce.mp3')
collect_sfx = pygame.mixer.Sound('Assets/collect.mp3')
death_sfx = pygame.mixer.Sound('Assets/death.ogg')
countdown_sfx = pygame.mixer.Sound('Assets/countdown.ogg')
debuff_sfx = pygame.mixer.Sound('Assets/debuff.ogg')

RED = (255, 0, 0)
BLUE = (0, 0, 255)
SKY_BLUE = (200, 240, 255)
BLACK = (0, 0, 0)
DARK_PURPLE = (100, 0, 100)
YELLOW = (255, 215, 0)
DARK_GRAY = (50, 50, 50)

# Gambar Bintang dan Spikes
def draw_star(surface, x, y, size, color):
    points = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        r = size if i % 2 == 0 else size / 2
        points.append((x + math.cos(angle) * r, y + math.sin(angle) * r))
    pygame.draw.polygon(surface, color, points)

def draw_top_bottom_spikes(surface):
    for i in range(0, SCREEN_WIDTH, 20):
        pygame.draw.polygon(surface, DARK_PURPLE, [(i, 0), (i + 10, SPIKE_HEIGHT), (i + 20, 0)])
        pygame.draw.polygon(surface, DARK_PURPLE, [(i, SCREEN_HEIGHT), (i + 10, SCREEN_HEIGHT - SPIKE_HEIGHT), (i + 20, SCREEN_HEIGHT)])

# Class Manajemen Side Spikes
class SideSpikeManager:
    def __init__(self):
        self.num_slots = (SCREEN_HEIGHT - 2 * SPIKE_HEIGHT) // SIDE_SPIKE_SIZE
        self.clear_all() 

    def clear_all(self):
        self.left_spikes = [False] * self.num_slots
        self.right_spikes = [False] * self.num_slots

    def randomize(self, side):
        slots = [False] * self.num_slots
        num_to_spawn = random.randint(3, 7)
        indices = random.sample(range(self.num_slots), num_to_spawn)
        for i in indices: slots[i] = True
        
        if side == "LEFT": self.left_spikes = slots
        else: self.right_spikes = slots

    def draw(self, surface):
        for i in range(self.num_slots):
            y_pos = SPIKE_HEIGHT + (i * SIDE_SPIKE_SIZE)
            if self.left_spikes[i]:
                pygame.draw.polygon(surface, DARK_PURPLE, [(0, y_pos), (SIDE_SPIKE_SIZE, y_pos + SIDE_SPIKE_SIZE//2), (0, y_pos + SIDE_SPIKE_SIZE)])
            if self.right_spikes[i]:
                pygame.draw.polygon(surface, DARK_PURPLE, [(SCREEN_WIDTH, y_pos), (SCREEN_WIDTH - SIDE_SPIKE_SIZE, y_pos + SIDE_SPIKE_SIZE//2), (SCREEN_WIDTH, y_pos + SIDE_SPIKE_SIZE)])

# Class Bintang
class Star:
    def __init__(self, initial_delay):
        self.active = False
        self.pos = pygame.Vector2(0, 0)
        self.radius = 12
        self.initial_delay = initial_delay
        self.spawn_timer = pygame.time.get_ticks() + self.initial_delay

    def update(self):
        if not self.active and pygame.time.get_ticks() > self.spawn_timer:
            self.spawn()

    def spawn(self):
        self.active = True
        self.pos.x = random.randint(70, SCREEN_WIDTH - 70)
        self.pos.y = random.randint(SPIKE_HEIGHT + 30, SCREEN_HEIGHT - SPIKE_HEIGHT - 30)

    def collect(self):
        self.active = False
        self.spawn_timer = pygame.time.get_ticks() + random.randint(3000, 7000)

    def reset(self):
        self.active = False
        self.spawn_timer = pygame.time.get_ticks() + self.initial_delay

    def draw(self, surface):
        if self.active: draw_star(surface, self.pos.x, self.pos.y, self.radius, YELLOW)

class DarkStar(Star):
    def __init__(self, initial_delay):
        super().__init__(initial_delay)

    def collect(self):
        self.active = False
        self.spawn_timer = pygame.time.get_ticks() + random.randint(30000, 60000)
        
    def draw(self, surface):
        if self.active: draw_star(surface, self.pos.x, self.pos.y, self.radius, DARK_GRAY)

class RedStar(Star):
    def __init__(self, initial_delay):
        super().__init__(initial_delay)
    
    def collect(self):
        self.active = False
        self.spawn_timer = pygame.time.get_ticks() + random.randint(1500, 3500)
        
    def draw(self, surface):
        if self.active: draw_star(surface, self.pos.x, self.pos.y, self.radius, RED)

# Class Burung
class Bird:
    def __init__(self, x, y, facing, image):
        self.pos = pygame.Vector2(x, y)
        self.facing = facing

        self.image = image

        self.base_speed = BIRD_SPEED
        self.base_gravity = GRAVITY

        self.speed = self.base_speed
        self.gravity = self.base_gravity
        self.velocity_y = 0  

        self.is_alive = True
        self.death_time = 0

        self.debuff_timer = 0

    def update(self, spike_manager):
        current_time = pygame.time.get_ticks()

        if current_time > self.debuff_timer:
            self.speed = self.base_speed
            self.gravity = self.base_gravity

        if self.is_alive:
            self.pos.x += self.facing * self.speed
            
            self.velocity_y += self.gravity
            self.pos.y += self.velocity_y

            if self.pos.x < BIRD_RADIUS:
                self.pos.x = BIRD_RADIUS
                self.facing = 1
                spike_manager.randomize("RIGHT") 
                bounce_sfx.play()
                self.check_side_collision(spike_manager.left_spikes, current_time)
            elif self.pos.x > SCREEN_WIDTH - BIRD_RADIUS:
                self.pos.x = SCREEN_WIDTH - BIRD_RADIUS
                self.facing = -1
                spike_manager.randomize("LEFT") 
                bounce_sfx.play()
                self.check_side_collision(spike_manager.right_spikes, current_time)

            if self.pos.y < SPIKE_HEIGHT + BIRD_RADIUS or \
               self.pos.y > SCREEN_HEIGHT - SPIKE_HEIGHT - BIRD_RADIUS:
                self.die(current_time)
        else:
            if current_time - self.death_time > RESPAWN_DELAY_MS:
                self.respawn()

    def check_side_collision(self, spikes_list, current_time):
        relative_y = self.pos.y - SPIKE_HEIGHT
        slot_index = int(relative_y // SIDE_SPIKE_SIZE)
        if 0 <= slot_index < len(spikes_list):
            if spikes_list[slot_index]: self.die(current_time)

    def jump(self):
        if self.is_alive: self.velocity_y = JUMP_STRENGTH
        jump_sfx.play()

    def die(self, time_of_death):
        self.is_alive = False
        self.death_time = time_of_death
        self.speed = 0
        self.velocity_y = 0
        death_sfx.play()

    def respawn(self):
        self.is_alive = True
        self.pos = pygame.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.speed = BIRD_SPEED
        self.velocity_y = 0

    def draw(self, surface):
        if self.is_alive:
            img_to_draw = self.image
            if self.facing == -1:
                img_to_draw = pygame.transform.flip(self.image, True, False)
            img_rect = img_to_draw.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surface.blit(img_to_draw, img_rect)
        else:
            font_small = pygame.font.SysFont(None, 30)
            text = font_small.render('X', True, BLACK)
            surface.blit(text, text.get_rect(center=(int(self.pos.x), int(self.pos.y))))

# Class Player 1
class Player(Bird):
    def __init__(self):
        super().__init__(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 1, player_img)
    def respawn(self):
        super().respawn()
        self.facing = 1

# Class Player 2
class Player2(Bird):
    def __init__(self):
        super().__init__(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, -1, player2_img)
    def respawn(self):
        super().respawn()
        self.facing = -1

# Inisialisasi game
pygame.display.set_caption("Bird Game: P1 vs P2")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 28, bold=True)
title_font = pygame.font.SysFont("Arial", 40, bold=True)

player = Player()
player2 = Player2() 
spikes = SideSpikeManager()
stars = [Star(initial_delay=6000), Star(initial_delay=9000)]
dark_stars = [DarkStar(initial_delay=60000)]
red_stars = [RedStar(initial_delay=20000)]

player_score = 0
player2_score = 0

countdown_start_time = 0
countdown_duration = 3000

game_state = "MENU"
pygame.mixer.music.load('Assets/main_music.mp3') 
pygame.mixer.music.set_volume(0.5)      
pygame.mixer.music.play(-1)            

def reset_game():
    global player_score, player2_score
    player_score = 0
    player2_score = 0
    player.respawn()
    player2.respawn()
    spikes.clear_all() 
    for s in stars: s.reset()
    for d in dark_stars: d.reset()
    for r in red_stars: r.reset()

# Main
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            pygame.quit() 
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if game_state == "MENU":
                if event.key == pygame.K_SPACE:
                    reset_game()
                    game_state = "COUNTDOWN"
                    countdown_start_time = pygame.time.get_ticks()
                    pygame.mixer.music.stop()
                    countdown_sfx.play()
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif game_state == "PLAYING":
                if event.key == pygame.K_SPACE: 
                    player.jump()
                if event.key == pygame.K_UP: 
                    player2.jump()
                if event.key == pygame.K_ESCAPE:
                    game_state = "MENU"
                    pygame.mixer.music.load('Assets/main_music.mp3')
                    pygame.mixer.music.play(-1)
            elif game_state == "GAME_OVER":
                if event.key == pygame.K_r: 
                    game_state = "COUNTDOWN"
                    reset_game()
                    countdown_start_time = pygame.time.get_ticks()
                    pygame.mixer.music.stop()
                    countdown_sfx.play()
                if event.key == pygame.K_ESCAPE: 
                    game_state = "MENU"
                    pygame.mixer.music.load('Assets/main_music.mp3')
                    pygame.mixer.music.play(-1)

    # Logika Game
    if game_state == "COUNTDOWN":
        current_time = pygame.time.get_ticks()
        if current_time - countdown_start_time >= countdown_duration:
            game_state = "PLAYING"

    elif game_state == "PLAYING":
            player.update(spikes)
            player2.update(spikes) 
            
            for s in stars: s.update()
            for d in dark_stars: d.update()
            for r in red_stars: r.update()

    for bird in [player, player2]:
            if bird.is_alive:
                # 1. Cek Star
                for s in stars:
                    if s.active and bird.pos.distance_to(s.pos) < BIRD_RADIUS + s.radius:
                        if bird == player: player_score += 1
                        else: player2_score += 1
                        s.collect()
                        collect_sfx.play()
                        if player_score >= WINNING_SCORE or player2_score >= WINNING_SCORE:
                            game_state = "GAME_OVER"
                            pygame.mixer.music.load('Assets/game_over.mp3')
                            pygame.mixer.music.play(-1)

                # 2. Cek Dark Star
                for d in dark_stars:
                    if d.active and bird.pos.distance_to(d.pos) < BIRD_RADIUS + d.radius:
                        d.collect()
                        easter_egg_sfx.play()       
                        screen.blit(easter_egg_img, (0, 0))
                        pygame.display.flip() 
                        pygame.time.delay(1500)
                        easter_egg_sfx.stop()
                        
                # 3. Cek Red Star
                for s in red_stars: 
                    if s.active and bird.pos.distance_to(s.pos) < BIRD_RADIUS + s.radius:
                        s.collect()
                        debuff_sfx.play()
                        bird.speed = bird.base_speed / 2
                        bird.gravity = bird.base_gravity * 2

                        bird.debuff_timer = pygame.time.get_ticks() + 3000


    # Render Layar
    screen.fill(SKY_BLUE)
    
    if game_state == "MENU":
        draw_top_bottom_spikes(screen) 
        title_txt = title_font.render("BIRD GAME", True, BLACK)
        title_txt2 = title_font.render("P1 VS P2", True, BLACK)

        subtitle_txt = font.render("Race to 10 Stars!", True, YELLOW)
        subtitle_txt2 = font.render("P1 = RED 'SPACE'", True, RED)

        subtitle_txt3 = font.render("P2 = BLUE 'UP ARROW'", True, BLUE)
        start_txt = font.render("Press SPACE to Start", True, BLACK)

        screen.blit(title_font.render("P1 VS P2", True, DARK_PURPLE), (SCREEN_WIDTH//2 - title_txt2.get_width()//2 + 2, 152))
        screen.blit(title_font.render("BIRD GAME", True, DARK_PURPLE), (SCREEN_WIDTH//2 - title_txt.get_width()//2 + 2, 118))
        screen.blit(title_txt, (SCREEN_WIDTH//2 - title_txt.get_width()//2, 120))
        screen.blit(title_txt2, (SCREEN_WIDTH//2 - title_txt2.get_width()//2, 150))

        screen.blit(subtitle_txt, (SCREEN_WIDTH//2 - subtitle_txt.get_width()//2, 210))
        screen.blit(subtitle_txt2, (SCREEN_WIDTH//2 - subtitle_txt2.get_width()//2, 240))
        screen.blit(subtitle_txt3, (SCREEN_WIDTH//2 - subtitle_txt3.get_width()//2, 270))

        if pygame.time.get_ticks() % 1000 < 600:
            screen.blit(start_txt, (SCREEN_WIDTH//2 - start_txt.get_width()//2, 400))

    elif game_state == "COUNTDOWN":
        draw_top_bottom_spikes(screen)
        spikes.draw(screen)
        for s in stars: s.draw(screen)
        for d in dark_stars: d.draw(screen)
        player.draw(screen)
        player2.draw(screen)
        

        elapsed = pygame.time.get_ticks() - countdown_start_time
        remaining = 3 - (elapsed // 1000) #
        

        count_txt = title_font.render(str(remaining), True, BLACK)
        screen.blit(count_txt, (SCREEN_WIDTH//2 - count_txt.get_width()//2, SCREEN_HEIGHT//2 - 50))
 
        get_ready_txt = font.render("SIAP-SIAP!", True, RED)
        screen.blit(get_ready_txt, (SCREEN_WIDTH//2 - get_ready_txt.get_width()//2, SCREEN_HEIGHT//2 + 20))


    elif game_state == "PLAYING" or game_state == "GAME_OVER":
        draw_top_bottom_spikes(screen)
        spikes.draw(screen)
        
        for s in stars: s.draw(screen)
        for d in dark_stars: d.draw(screen) 
        for s in red_stars: s.draw(screen)

        player.draw(screen)
        player2.draw(screen)

        screen.blit(font.render(f"P1: {player_score}", True, RED), (20, 40))
        screen.blit(font.render(f"P2: {player2_score}", True, BLUE), (SCREEN_WIDTH - 100, 40))

        if game_state == "GAME_OVER":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(150)
            overlay.fill(BLACK)
            screen.blit(overlay, (0,0))
            
            msg = "PLAYER 1 WINS!" if player_score >= WINNING_SCORE else "PLAYER 2 WINS!"
            color = RED if player_score >= WINNING_SCORE else BLUE
            
            txt1 = title_font.render(msg, True, color)
            txt2 = font.render("Press R to Restart", True, (255, 255, 255))
            txt3 = font.render("Press 'ESC' for Menu", True, (200, 200, 200))
            
            screen.blit(txt1, (SCREEN_WIDTH//2 - txt1.get_width()//2, SCREEN_HEIGHT//2 - 60))
            screen.blit(txt2, (SCREEN_WIDTH//2 - txt2.get_width()//2, SCREEN_HEIGHT//2 + 10))
            screen.blit(txt3, (SCREEN_WIDTH//2 - txt3.get_width()//2, SCREEN_HEIGHT//2 + 50))

    pygame.display.flip()
    clock.tick(60)
