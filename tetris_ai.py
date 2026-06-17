import pygame
import random
import os

# 游戏设置
SCREEN_WIDTH = 500  # 稍微加宽一点放UI
SCREEN_HEIGHT = 550
BLOCK_SIZE = 20
GRID_WIDTH = 10
GRID_HEIGHT = 20
X_OFFSET = 50
Y_OFFSET = 50

# 形状定义
SHAPES = [
    [[1, 1, 1, 1]], # I
    [[1, 1], [1, 1]], # O
    [[0, 1, 0], [1, 1, 1]], # T
    [[1, 1, 0], [0, 1, 1]], # S
    [[0, 1, 1], [1, 1, 0]], # Z
    [[1, 0, 0], [1, 1, 1]], # J
    [[0, 0, 1], [1, 1, 1]]  # L
]

COLORS = [
    (0, 255, 255), (255, 255, 0), (128, 0, 128),
    (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 165, 0)
]

HIGH_SCORE_FILE = os.path.join(os.path.dirname(__file__), "high_score.txt")

class Tetris:
    def __init__(self):
        self.reset()
        self.high_score = self.load_high_score()

    def reset(self):
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.curr_piece = self.new_piece()
        self.game_over = False
        self.score = 0

    def new_piece(self):
        shape_idx = random.randint(0, len(SHAPES) - 1)
        return {
            'shape': SHAPES[shape_idx],
            'color': COLORS[shape_idx],
            'x': GRID_WIDTH // 2 - len(SHAPES[shape_idx][0]) // 2,
            'y': 0
        }

    def rotate(self, shape):
        return [list(row) for row in zip(*shape[::-1])]

    def is_valid(self, shape, x, y):
        for row_idx, row in enumerate(shape):
            for col_idx, cell in enumerate(row):
                if cell:
                    new_x = x + col_idx
                    new_y = y + row_idx
                    if new_x < 0 or new_x >= GRID_WIDTH or new_y >= GRID_HEIGHT:
                        return False
                    if new_y >= 0 and self.grid[new_y][new_x]:
                        return False
        return True

    def place_piece(self):
        for row_idx, row in enumerate(self.curr_piece['shape']):
            for col_idx, cell in enumerate(row):
                if cell:
                    self.grid[self.curr_piece['y'] + row_idx][self.curr_piece['x'] + col_idx] = self.curr_piece['color']
        
        self.clear_lines()
        self.curr_piece = self.new_piece()
        if not self.is_valid(self.curr_piece['shape'], self.curr_piece['x'], self.curr_piece['y']):
            self.game_over = True
            self.save_high_score()

    def clear_lines(self):
        lines_to_clear = [i for i, row in enumerate(self.grid) if all(row)]
        for i in lines_to_clear:
            del self.grid[i]
            self.grid.insert(0, [0 for _ in range(GRID_WIDTH)])
        self.score += len(lines_to_clear) ** 2
        if self.score > self.high_score:
            self.high_score = self.score

    def move(self, dx, dy):
        if self.is_valid(self.curr_piece['shape'], self.curr_piece['x'] + dx, self.curr_piece['y'] + dy):
            self.curr_piece['x'] += dx
            self.curr_piece['y'] += dy
            return True
        return False

    def drop(self):
        if not self.move(0, 1):
            self.place_piece()

    def hard_drop(self):
        while self.move(0, 1):
            pass
        self.place_piece()

    def load_high_score(self):
        try:
            with open(HIGH_SCORE_FILE, "r") as f:
                return int(f.read())
        except (FileNotFoundError, ValueError):
            return 0

    def save_high_score(self):
        try:
            with open(HIGH_SCORE_FILE, "w") as f:
                f.write(str(self.high_score))
        except Exception:
            pass

class AI:
    def __init__(self):
        # 启发式参数: [高度权重, 消行权重, 空洞权重, 颠簸权重]
        self.weights = [-0.51, 0.76, -0.36, -0.18]

    def get_best_move(self, game):
        best_score = -float('inf')
        best_x = game.curr_piece['x']
        best_rotation = game.curr_piece['shape']

        original_shape = game.curr_piece['shape']
        
        # 尝试所有旋转
        curr_shape = original_shape
        for _ in range(4):
            # 尝试所有横向位置
            for x in range(-2, GRID_WIDTH + 2):
                if game.is_valid(curr_shape, x, 0):
                    # 模拟下落到最低点
                    y = 0
                    while game.is_valid(curr_shape, x, y + 1):
                        y += 1
                    
                    # 评估当前局势
                    score = self.evaluate(game, curr_shape, x, y)
                    if score > best_score:
                        best_score = score
                        best_x = x
                        best_rotation = curr_shape
            
            curr_shape = game.rotate(curr_shape)

        return best_x, best_rotation

    def evaluate(self, game, shape, x, y):
        # 创建临时网格
        temp_grid = [row[:] for row in game.grid]
        for r_idx, row in enumerate(shape):
            for c_idx, cell in enumerate(row):
                if cell and y + r_idx >= 0:
                    temp_grid[y + r_idx][x + c_idx] = 1

        # 计算特征
        heights = self.get_heights(temp_grid)
        aggregate_height = sum(heights)
        complete_lines = sum(1 for row in temp_grid if all(row))
        holes = self.count_holes(temp_grid)
        bumpiness = self.get_bumpiness(heights)

        return (self.weights[0] * aggregate_height +
                self.weights[1] * complete_lines +
                self.weights[2] * holes +
                self.weights[3] * bumpiness)

    def get_heights(self, grid):
        heights = [0] * GRID_WIDTH
        for col in range(GRID_WIDTH):
            for row in range(GRID_HEIGHT):
                if grid[row][col]:
                    heights[col] = GRID_HEIGHT - row
                    break
        return heights

    def count_holes(self, grid):
        holes = 0
        for col in range(GRID_WIDTH):
            block_found = False
            for row in range(GRID_HEIGHT):
                if grid[row][col]:
                    block_found = True
                elif block_found:
                    holes += 1
        return holes

    def get_bumpiness(self, heights):
        bumpiness = 0
        for i in range(len(heights) - 1):
            bumpiness += abs(heights[i] - heights[i+1])
        return bumpiness

def draw_button(screen, rect, text, active):
    color = (100, 200, 100) if active else (70, 70, 70)
    pygame.draw.rect(screen, color, rect, border_radius=5)
    pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=5)
    
    font = pygame.font.SysFont("Arial", 16)
    text_surf = font.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Tetris - Player vs AI")
    clock = pygame.time.Clock()
    game = Tetris()
    ai = AI()

    is_ai_mode = False
    last_drop_time = pygame.time.get_ticks()
    drop_speed = 500  # 500ms

    # 按钮位置
    button_rect = pygame.Rect(300, 100, 150, 40)
    restart_rect = pygame.Rect(300, 160, 150, 40)

    running = True
    while running:
        current_time = pygame.time.get_ticks()

        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    is_ai_mode = not is_ai_mode
                if restart_rect.collidepoint(event.pos):
                    game.reset()

            if not game.game_over and not is_ai_mode:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        game.move(-1, 0)
                    elif event.key == pygame.K_RIGHT:
                        game.move(1, 0)
                    elif event.key == pygame.K_DOWN:
                        game.move(0, 1)
                    elif event.key == pygame.K_UP:
                        new_shape = game.rotate(game.curr_piece['shape'])
                        if game.is_valid(new_shape, game.curr_piece['x'], game.curr_piece['y']):
                            game.curr_piece['shape'] = new_shape
                    elif event.key == pygame.K_SPACE:
                        game.hard_drop()

        # AI 控制
        if not game.game_over and is_ai_mode:
            target_x, target_shape = ai.get_best_move(game)
            game.curr_piece['shape'] = target_shape
            
            if game.curr_piece['x'] < target_x:
                game.move(1, 0)
            elif game.curr_piece['x'] > target_x:
                game.move(-1, 0)
            
            # AI 加速下落
            drop_speed = 100

        # 自动下落
        if not game.game_over:
            if current_time - last_drop_time > drop_speed:
                game.drop()
                last_drop_time = current_time
                if is_ai_mode:
                    drop_speed = 100
                else:
                    drop_speed = 500

        # 渲染
        screen.fill((20, 20, 30))

        # 画边框
        border_color = (50, 50, 80)
        pygame.draw.rect(screen, border_color, 
                        (X_OFFSET - 3, Y_OFFSET - 3, 
                         GRID_WIDTH * BLOCK_SIZE + 6, GRID_HEIGHT * BLOCK_SIZE + 6), 3)

        # 画网格背景
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                rect = (X_OFFSET + x * BLOCK_SIZE, Y_OFFSET + y * BLOCK_SIZE, 
                        BLOCK_SIZE - 1, BLOCK_SIZE - 1)
                pygame.draw.rect(screen, (30, 30, 40), rect)

        # 画网格方块
        for y, row in enumerate(game.grid):
            for x, color in enumerate(row):
                if color:
                    rect = (X_OFFSET + x * BLOCK_SIZE, Y_OFFSET + y * BLOCK_SIZE, 
                            BLOCK_SIZE - 1, BLOCK_SIZE - 1)
                    pygame.draw.rect(screen, color, rect)
        
        # 画当前方块
        if game.curr_piece:
            for r_idx, row in enumerate(game.curr_piece['shape']):
                for c_idx, cell in enumerate(row):
                    if cell:
                        rect = (X_OFFSET + (game.curr_piece['x'] + c_idx) * BLOCK_SIZE, 
                                Y_OFFSET + (game.curr_piece['y'] + r_idx) * BLOCK_SIZE, 
                                BLOCK_SIZE - 1, BLOCK_SIZE - 1)
                        pygame.draw.rect(screen, game.curr_piece['color'], rect)

        # 画 UI
        font = pygame.font.SysFont("Arial", 24)
        # 当前分数
        score_text = font.render(f"Score: {game.score}", True, (255, 255, 255))
        screen.blit(score_text, (300, 20))
        
        # 最高分
        high_score_text = font.render(f"High: {game.high_score}", True, (255, 215, 0))
        screen.blit(high_score_text, (300, 55))

        # 模式切换按钮
        button_text = "AI Mode" if is_ai_mode else "Player Mode"
        draw_button(screen, button_rect, "Switch to " + ("Player" if is_ai_mode else "AI"), is_ai_mode)
        draw_button(screen, restart_rect, "Restart", False)

        # 游戏结束提示
        if game.game_over:
            game_over_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            game_over_surf.fill((0, 0, 0, 180))
            screen.blit(game_over_surf, (0, 0))
            
            go_font = pygame.font.SysFont("Arial", 48)
            go_text = go_font.render("GAME OVER", True, (255, 100, 100))
            screen.blit(go_text, go_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
