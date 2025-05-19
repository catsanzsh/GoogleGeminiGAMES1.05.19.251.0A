import pygame
import random

# --- Initialize Pygame and Create Window ---
pygame.init()
pygame.mixer.init() # Initialize the mixer module

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("VHS Pong")

# --- Colors ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
VHS_GREEN_TINT = (200, 255, 200, 30) # For a slight monitor glow/tint
VHS_TEXT_COLOR = (200, 255, 200) # Greenish text for VHS feel
DARK_GRAY = (40, 40, 40)

# --- Game Variables & Constants ---
BALL_RADIUS = 10
PADDLE_WIDTH = 15
PADDLE_HEIGHT = 100
PADDLE_SPEED = 7
AI_REACTION_FACTOR = 0.8 # How quickly AI paddle reacts (0.1 slow, 1.0 fast)
BALL_SPEED_X_INITIAL = 6
BALL_SPEED_Y_INITIAL_MAX = 6
BALL_SPEED_Y_CLAMP = 5 # Used for speed clamping after hit
JITTER_AMOUNT = 2
WINNING_SCORE = 5

score_left = 0
score_right = 0
current_jitter_x = 0
current_jitter_y = 0
game_state = "MAIN_MENU" # Possible states: MAIN_MENU, PLAYING, GAME_OVER
winner = None # Stores "Player" or "AI"

# --- Load Assets (Fonts, Sounds) ---
print("Attempting to load assets...")

# Font Loading
custom_font_path = "PressStart2P.ttf"
font_retro_large = None
font_retro_medium = None
font_retro_small = None
custom_font_loaded_successfully = False

try:
    font_retro_large = pygame.font.Font(custom_font_path, 40)
    font_retro_medium = pygame.font.Font(custom_font_path, 24)
    font_retro_small = pygame.font.Font(custom_font_path, 16)
    print(f"Successfully loaded custom font: '{custom_font_path}'")
    custom_font_loaded_successfully = True
except FileNotFoundError:
    print(f"Warning: Custom font file '{custom_font_path}' not found.")
except pygame.error as e:
    print(f"Warning: Pygame error while loading custom font '{custom_font_path}': {e}")

if not custom_font_loaded_successfully:
    print("Attempting to use system monospace font as fallback.")
    try:
        font_retro_large = pygame.font.SysFont("monospace", 50, bold=True)
        font_retro_medium = pygame.font.SysFont("monospace", 30, bold=True)
        font_retro_small = pygame.font.SysFont("monospace", 20, bold=True)
        print("Successfully loaded system monospace font.")
    except pygame.error as e:
        print(f"Warning: Pygame error while loading system monospace font: {e}.")
        print("Attempting to use basic default system font as final fallback.")
        try:
            font_retro_large = pygame.font.SysFont(None, 74)
            font_retro_medium = pygame.font.SysFont(None, 40)
            font_retro_small = pygame.font.SysFont(None, 25)
            print("Successfully loaded basic default system font.")
        except pygame.error as e_final:
            print(f"CRITICAL: Could not load any fonts. Pygame error: {e_final}. Text might not be visible or error later.")
            # Fallback to pygame's absolute default if all else fails.
            if font_retro_large is None: font_retro_large = pygame.font.Font(None, 74)
            if font_retro_medium is None: font_retro_medium = pygame.font.Font(None, 40)
            if font_retro_small is None: font_retro_small = pygame.font.Font(None, 25)


# Sound Loading
def load_sound_optional(filename):
    try:
        sound = pygame.mixer.Sound(filename)
        print(f"Successfully loaded sound: '{filename}'")
        return sound
    except FileNotFoundError:
        print(f"Warning: Sound file '{filename}' not found.")
        return None
    except pygame.error as e: # Catches other Pygame sound loading errors (e.g., format, mixer not init)
        print(f"Warning: Pygame error loading sound '{filename}': {e}.")
        return None

print("Loading sounds...")
paddle_hit_sound = load_sound_optional("paddle_hit.wav")
score_sound = load_sound_optional("score.wav")

if paddle_hit_sound is None:
    print("Paddle hit sound will be disabled.")
if score_sound is None:
    print("Score sound will be disabled.")

# --- Helper function for drawing text ---
def draw_text(text, font, color, surface, x, y, center_x=False, center_y=False):
    if font is None:
        print(f"Error: Font not loaded. Cannot draw text: {text}")
        return pygame.Rect(x,y,0,0)
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center_x:
        text_rect.centerx = x
    else:
        text_rect.x = x
    if center_y:
        text_rect.centery = y
    else:
        text_rect.y = y
    surface.blit(text_obj, text_rect)
    return text_rect

# --- Sprite Classes ---
class Paddle(pygame.sprite.Sprite):
    def __init__(self, x_pos, is_ai=False):
        super().__init__()
        self.image = pygame.Surface([PADDLE_WIDTH, PADDLE_HEIGHT])
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = x_pos
        self.rect.centery = SCREEN_HEIGHT // 2
        self.speed = 0
        self.is_ai = is_ai

    def update(self, ball_for_ai=None): # ball_for_ai is the ball sprite, only used by AI
        if self.is_ai and ball_for_ai:
            dead_zone = PADDLE_HEIGHT * 0.15
            if ball_for_ai.rect.centery < self.rect.centery - dead_zone:
                self.speed = -PADDLE_SPEED * AI_REACTION_FACTOR
            elif ball_for_ai.rect.centery > self.rect.centery + dead_zone:
                self.speed = PADDLE_SPEED * AI_REACTION_FACTOR
            else:
                self.speed = 0
        
        self.rect.y += self.speed
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT

    def move_manual(self, y_pos):
        if not self.is_ai:
            self.rect.centery = y_pos
            if self.rect.top < 0: self.rect.top = 0
            if self.rect.bottom > SCREEN_HEIGHT: self.rect.bottom = SCREEN_HEIGHT
    
    def stop(self):
        self.speed = 0

class Ball(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image_orig = pygame.Surface([BALL_RADIUS * 2, BALL_RADIUS * 2], pygame.SRCALPHA)
        pygame.draw.circle(self.image_orig, WHITE, (BALL_RADIUS, BALL_RADIUS), BALL_RADIUS)
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect()
        self.speed_x = 0
        self.speed_y = 0
        self.reset()

    def update(self, *args, **kwargs): # MODIFIED: Accept arbitrary arguments
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

        if self.rect.top <= 0 or self.rect.bottom >= SCREEN_HEIGHT:
            self.speed_y *= -1
            if self.rect.top < 0: self.rect.top = 0
            if self.rect.bottom > SCREEN_HEIGHT: self.rect.bottom = SCREEN_HEIGHT
            if paddle_hit_sound: 
                paddle_hit_sound.play()


    def reset(self, going_left=None):
        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        if going_left is None:
            direction = random.choice((1, -1))
        else:
            direction = -1 if going_left else 1
        self.speed_x = BALL_SPEED_X_INITIAL * direction
        self.speed_y = random.randint(-BALL_SPEED_Y_INITIAL_MAX, BALL_SPEED_Y_INITIAL_MAX)
        if self.speed_y == 0:
            self.speed_y = 1 * random.choice((1,-1))

# --- Create Sprites ---
paddle_left = Paddle(30)
paddle_right = Paddle(SCREEN_WIDTH - 30 - PADDLE_WIDTH, is_ai=True)
ball = Ball()
all_sprites = pygame.sprite.Group()
all_sprites.add(paddle_left, paddle_right, ball)

# --- Game Surfaces ---
game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
vhs_overlay_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

# --- VHS Effects Functions ---
def generate_static_vhs_overlay():
    vhs_overlay_surface.fill((0,0,0,0))
    for y_scan in range(0, SCREEN_HEIGHT, 3):
        pygame.draw.line(vhs_overlay_surface, (0, 0, 0, 25), (0, y_scan), (SCREEN_WIDTH, y_scan), 1)
    for _ in range(int(SCREEN_WIDTH * SCREEN_HEIGHT * 0.01)):
        nx, ny = random.randint(0, SCREEN_WIDTH-1), random.randint(0, SCREEN_HEIGHT-1)
        n_color_val = random.randint(50,100)
        vhs_overlay_surface.set_at((nx,ny), (n_color_val, n_color_val, n_color_val, random.randint(10,30)))

generate_static_vhs_overlay()
bad_tracking_timer = 0
BAD_TRACKING_INTERVAL = 180 # Frames

# --- Button Rects for Menu ---
start_button_rect = None
quit_button_rect = None

def reset_game_vars():
    global score_left, score_right, winner, game_state
    score_left = 0
    score_right = 0
    winner = None
    ball.reset()
    paddle_left.rect.centery = SCREEN_HEIGHT // 2
    paddle_right.rect.centery = SCREEN_HEIGHT // 2
    game_state = "PLAYING"


# --- Game Loop ---
clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_state == "MAIN_MENU":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_button_rect and start_button_rect.collidepoint(event.pos):
                    reset_game_vars()
                elif quit_button_rect and quit_button_rect.collidepoint(event.pos):
                    running = False
        
        elif game_state == "PLAYING":
            if event.type == pygame.MOUSEMOTION:
                paddle_left.move_manual(event.pos[1])
            # Player paddle movement via keys can be added here if desired
            # Example:
            # if event.type == pygame.KEYDOWN:
            #     if event.key == pygame.K_w:
            #         paddle_left.speed = -PADDLE_SPEED
            #     if event.key == pygame.K_s:
            #         paddle_left.speed = PADDLE_SPEED
            # if event.type == pygame.KEYUP:
            #     if event.key == pygame.K_w and paddle_left.speed < 0:
            #         paddle_left.stop()
            #     if event.key == pygame.K_s and paddle_left.speed > 0:
            #         paddle_left.stop()

        
        elif game_state == "GAME_OVER":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    reset_game_vars()
                elif event.key == pygame.K_n:
                    game_state = "MAIN_MENU"

    # --- Update ---
    if game_state == "PLAYING":
        all_sprites.update(ball_for_ai=ball) # Pass ball for AI paddle's reference

        # Ball collision with paddles
        if pygame.sprite.collide_rect(ball, paddle_left):
            ball.speed_x *= -1
            ball.rect.left = paddle_left.rect.right + 1 # Prevent sticking
            # Calculate hit angle based on where the ball hits the paddle
            delta_y = (ball.rect.centery - paddle_left.rect.centery) / (PADDLE_HEIGHT / 2)
            ball.speed_y += delta_y * 2 # Adjust y_speed based on hit position
            if paddle_hit_sound: paddle_hit_sound.play()
        elif pygame.sprite.collide_rect(ball, paddle_right):
            ball.speed_x *= -1
            ball.rect.right = paddle_right.rect.left -1 # Prevent sticking
            delta_y = (ball.rect.centery - paddle_right.rect.centery) / (PADDLE_HEIGHT / 2)
            ball.speed_y += delta_y * 2
            if paddle_hit_sound: paddle_hit_sound.play()

        # Clamp ball Y speed
        if abs(ball.speed_y) > BALL_SPEED_Y_CLAMP * 1.5: # Allow some overshoot before clamping
            ball.speed_y = BALL_SPEED_Y_CLAMP * 1.5 * (1 if ball.speed_y > 0 else -1)

        # Scoring
        scored = False
        if ball.rect.left <= 0:
            score_right += 1
            ball.reset(going_left=False) # Ball serves towards the player who didn't score
            if score_sound: score_sound.play()
            current_jitter_x = random.randint(-JITTER_AMOUNT * 4, JITTER_AMOUNT * 4) # Big jitter on score
            current_jitter_y = random.randint(-JITTER_AMOUNT * 4, JITTER_AMOUNT * 4)
            scored = True
        if ball.rect.right >= SCREEN_WIDTH:
            score_left += 1
            ball.reset(going_left=True) # Ball serves towards AI
            if score_sound: score_sound.play()
            current_jitter_x = random.randint(-JITTER_AMOUNT * 4, JITTER_AMOUNT * 4)
            current_jitter_y = random.randint(-JITTER_AMOUNT * 4, JITTER_AMOUNT * 4)
            scored = True
        
        if scored and (score_left >= WINNING_SCORE or score_right >= WINNING_SCORE):
            game_state = "GAME_OVER"
            winner = "Player" if score_left >= WINNING_SCORE else "AI"


    # --- Drawing ---
    game_surface.fill(BLACK) # Base drawing surface
    if game_state == "PLAYING" or game_state == "GAME_OVER": # Draw game elements if playing or game over
        # Draw dashed middle line
        for i in range(0, SCREEN_HEIGHT, 20): # 10px dash, 10px gap
            pygame.draw.rect(game_surface, DARK_GRAY, (SCREEN_WIDTH // 2 - 2, i, 4, 10))
        
        all_sprites.draw(game_surface)

        # Draw scores
        draw_text(str(score_left), font_retro_large, VHS_TEXT_COLOR, game_surface, SCREEN_WIDTH // 4, 20, center_x=True)
        draw_text(str(score_right), font_retro_large, VHS_TEXT_COLOR, game_surface, SCREEN_WIDTH * 3 // 4, 20, center_x=True)

    # Apply VHS green tint
    tint_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    tint_layer.fill(VHS_GREEN_TINT)
    game_surface.blit(tint_layer, (0,0))

    # Apply desaturation effect (optional, for more VHS feel)
    desat_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    desat_layer.fill((128,128,128, 30)) # Gray with some alpha
    game_surface.blit(desat_layer, (0,0), special_flags=pygame.BLEND_RGBA_MULT)


    # Blit game_surface to screen with jitter
    screen.fill(BLACK) # Clear main screen
    screen.blit(game_surface, (current_jitter_x, current_jitter_y))

    # Blit static VHS overlay on top
    screen.blit(vhs_overlay_surface, (0,0))

    # Bad tracking effect
    bad_tracking_timer += 1
    if bad_tracking_timer >= BAD_TRACKING_INTERVAL:
        bad_tracking_timer = 0
        if random.random() < 0.3: # 30% chance for bad tracking effect
            temp_tracking_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            num_lines = random.randint(1,3)
            for _ in range(num_lines):
                line_y = random.randint(0, SCREEN_HEIGHT - 30)
                line_h = random.randint(10,30)
                alpha = random.randint(40,80)
                pygame.draw.rect(temp_tracking_surf, (10,10,10,alpha), (0, line_y, SCREEN_WIDTH, line_h))
            screen.blit(temp_tracking_surf, (0,0)) # Draw on top
            if random.random() < 0.1: # Small chance to regenerate static overlay too
                 generate_static_vhs_overlay()


    # UI Screens
    if game_state == "MAIN_MENU":
        screen.fill(BLACK) # Clear screen for menu
        draw_text("P  O  N  G", font_retro_large, VHS_TEXT_COLOR, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4, center_x=True, center_y=True)
        start_button_rect = draw_text("START GAME", font_retro_medium, VHS_TEXT_COLOR, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center_x=True, center_y=True)
        quit_button_rect = draw_text("QUIT", font_retro_medium, VHS_TEXT_COLOR, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60, center_x=True, center_y=True)
        
        # Highlight buttons on hover
        mouse_pos = pygame.mouse.get_pos()
        if start_button_rect and start_button_rect.collidepoint(mouse_pos):
            draw_text("START GAME", font_retro_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center_x=True, center_y=True)
        if quit_button_rect and quit_button_rect.collidepoint(mouse_pos):
            draw_text("QUIT", font_retro_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60, center_x=True, center_y=True)

    elif game_state == "GAME_OVER":
        # Darken the background for game over screen
        overlay_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay_surface.fill((0,0,0,150)) # Semi-transparent black
        screen.blit(overlay_surface, (0,0)) # Blit over existing game screen

        draw_text("GAME OVER", font_retro_large, VHS_TEXT_COLOR, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3, center_x=True, center_y=True)
        winner_text = f"{winner} WINS!" if winner else "IT'S A DRAW!" # Should always have a winner with current logic
        draw_text(winner_text, font_retro_medium, VHS_TEXT_COLOR, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center_x=True, center_y=True)
        draw_text("Restart (Y) / Menu (N)", font_retro_small, VHS_TEXT_COLOR, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT * 2 // 3, center_x=True, center_y=True)

    # Jitter update
    if game_state == "PLAYING":
        if random.randint(0, 5) == 0: # Chance to apply new small jitter
            current_jitter_x = random.randint(-JITTER_AMOUNT, JITTER_AMOUNT)
            current_jitter_y = random.randint(-JITTER_AMOUNT, JITTER_AMOUNT)
        else: # Dampen existing jitter
            current_jitter_x = int(current_jitter_x * 0.8)
            current_jitter_y = int(current_jitter_y * 0.8)
    else: # Minimal jitter for menus/game over
        current_jitter_x = random.randint(-1,1)
        current_jitter_y = random.randint(-1,1)


    pygame.display.flip()
    clock.tick(60)

pygame.quit()
