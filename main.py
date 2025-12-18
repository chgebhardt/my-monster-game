import pygame
from random import randint, choice, sample
from math import sqrt

class Level:
    """
    This class generates a randomized level map
    NOTE: this can create maps that are not solveable eg if door access is blocked by internal walls
          -> maybe use flood fill / BFS / DFS to check that all empty tiles are accessible after an internal wall tile was placed?
    """ 

    WALL  = '#'
    EMPTY = ' '
    COIN  = 'C'
    DOOR  = 'D'

    def __init__(self, win_size: tuple, num_internal_walls: int, num_coins: int, level_num: int):
        self.win_size           = win_size
        self.num_internal_walls = num_internal_walls
        self.num_coins          = num_coins
        self.level_num          = level_num                

        # The map[y][x] contains WALL, EMPTY, COIN, or DOOR
        self._generate_map()

    def _generate_map(self):
        # create empty map
        self.level_map = self._create_empty_map()

        # add external walls
        self._add_external_walls()

        # add internal walls
        self._place_items(self.WALL, count = self.num_internal_walls)

        # add exit door
        self._place_items(self.DOOR, count = 1)

        # add coins
        self._place_items(self.COIN, count = self.num_coins)

    def _create_empty_map(self):
        w, h = self.win_size
        return [[self.EMPTY for _ in range(w)] for _ in range(h)]

    def _in_bounds(self, x, y):
        w, h = self.win_size
        return 0 <= x < w and 0 <= y < h

    def _get_tile(self, x, y):
        if not self._in_bounds(x, y):
            return None
        return self.level_map[y][x]

    def _set_tile(self, x, y, value):
        if self._in_bounds(x, y):
            self.level_map[y][x] = value

    def _get_empty_positions(self):
        w, h = self.win_size
        return [(x, y) for y in range(1, h - 1) for x in range(1, w - 1) if self.level_map[y][x] == self.EMPTY]

    def _place_items(self, symbol, count):
        empty = self._get_empty_positions()
        if count > len(empty):
            raise ValueError(f"Not enough space for {symbol}")

        for x, y in sample(empty, count):
            self.level_map[y][x] = symbol

    def _add_external_walls(self):
        w, h = self.win_size
        for y in range(h):
            for x in range(w):
                if y == 0 or y == h - 1 or x == 0 or x == w - 1:
                    self.level_map[y][x] = self.WALL

    def is_not_wall(self, position):
        x, y = position
        return self._get_tile(x, y) != self.WALL

    def is_coin(self, position):
        x, y = position
        return self._get_tile(x, y) == self.COIN

    def is_door(self, position):
        x, y = position
        return self._get_tile(x, y) == self.DOOR

    def remove_coin(self, position):
        x, y = position
        self.level_map[y][x] = self.EMPTY

    def open_door(self, position):
        x, y = position
        self.level_map[y][x] = self.EMPTY
    
    def is_walkable(self, position: tuple) -> bool:
        return self.is_not_wall(position)

    def is_spawnable(self, position: tuple) -> bool:
        """
        Return True if a robot or monster can spawn here (ignoring entities).
        """
        x, y = position
        if not self.is_not_wall(position):
            return False
        if self.is_coin(position) or self.is_door(position):
            return False
        return True

        
    def __str__(self):
        """
        quick and dirty print function of the level map
        """
        lines = [f"Level {self.level_num}"]
        for row in self.level_map:
            lines.append(" ".join(ch if ch != self.EMPTY else '_' for ch in row))
        return "\n".join(lines)


class Monster:
    def __init__(self, position: tuple):
        self.position      = position
        self.coins_carried = 0
        self.is_caught     = False

        self.image = pygame.image.load("monster.png")

    @property
    def x(self):
        return self.position[0]

    @property
    def y(self):
        return self.position[1]

    @property
    def size(self):
        return self.image.get_size()

    def propose_move(self, dx: int, dy: int):
        x, y = self.position
        return x + dx, y + dy

    def move_to(self, position: tuple):
        self.position = position

    def collect_coin(self):
        self.coins_carried += 1

    def mark_caught(self):
        self.is_caught = True


class Robot:
    """
    Robot enemy class.
    """
    def __init__(self, position: tuple, robot_speed_ms: int):
        self.position          = position
        self.speed_ms          = robot_speed_ms

        self.image = pygame.image.load("robot.png")

    @property
    def x(self):
        return self.position[0]

    @property
    def y(self):
        return self.position[1]

    @property
    def size(self):
        return self.image.get_size()

    def propose_move(self, dx: int, dy: int):
        x, y = self.position
        return x + dx, y + dy

    def move_to(self, position: tuple):
        self.position = position


class InputHandler:
    def __init__(self):
        self.keymap = {
            pygame.K_UP:    (0, -1),
            pygame.K_DOWN:  (0, 1),
            pygame.K_LEFT:  (-1, 0),
            pygame.K_RIGHT: (1, 0),
        }

    def read_input(self):
        dx, dy    = 0, 0
        restart   = False
        quit_game = False

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                quit_game = True

            elif event.type == pygame.KEYDOWN:
                # movement
                if event.key in self.keymap:
                    dx, dy = self.keymap[event.key]

                # restart
                elif event.key == pygame.K_F2:
                    restart = True

                # quit
                elif event.key == pygame.K_ESCAPE:
                    quit_game = True

        return dx, dy, restart, quit_game

    def wait_for_keypress(self, clock):
        """
        Blocks title screen until any key is pressed
        """
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    waiting = False
            clock.tick(30)


class GameState:
    def __init__(self, level, monster, robots):
        self.level          = level
        self.monster        = monster
        self.robots         = robots
        self.level_finished = False

    # -------------------- Monster Logic -------------------- #
    def try_move_monster(self, dx: int, dy: int):
        proposed_position = self.monster.propose_move(dx, dy)

        # validate move
        if self.is_valid_monster_position(proposed_position):
            self.monster.move_to(proposed_position)

        # coin collection
        if self.level.is_coin(proposed_position):
            self.monster.coins_carried += 1
            self.level.remove_coin(proposed_position)

        # door / level completion
        if (self.level.is_door(proposed_position) and self.monster.coins_carried == self.level.num_coins):
            self.level.open_door(proposed_position)
            self.level_finished = True

        # collision with robots
        if proposed_position in {r.position for r in self.robots}:
            self.monster.is_caught = True

    # -------------------- Robot Logic -------------------- #
    def update_robots(self):
        """
        Moves all robots:
        - Propose moves
        - Validate against walls, doors, other robots
        - Update positions
        - Detect if monster is caught
        """
        for robot in self.robots:
            possible_moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]

            valid_positions = []
            fallback_positions = []

            for dx, dy in possible_moves:
                pos = robot.propose_move(dx, dy)

                if self.level.is_not_wall(pos):
                    fallback_positions.append(pos)

                if self.is_valid_robot_position(pos, robot):
                    valid_positions.append(pos)

            if valid_positions:
                mx, my = self.monster.position
                # move towards monster
                robot.move_to( min(valid_positions, key=lambda p: (mx - p[0]) ** 2 + (my - p[1]) ** 2) )
            elif fallback_positions:
                robot.move_to(choice(fallback_positions))

            # did robot catch a monster?
            if robot.position == self.monster.position:
                self.monster.is_caught = True

    # -------------------- Validation -------------------- #
    def is_valid_monster_position(self, position: tuple) -> bool:
        """
        Monster can move anywhere except walls.
        """
        return self.level.is_not_wall(position)

    def is_valid_robot_position(self, position: tuple, robot) -> bool:
        """
        Robot cannot move into walls, doors, coins, or other robots.
        """
        if ( not self.level.is_not_wall(position) or self.level.is_coin(position) or self.level.is_door(position) ):
            return False

        # Avoid other robots
        other_positions = {r.position for r in self.robots if r is not robot}
        return position not in other_positions


class Renderer:
    def __init__(self, window, tile_scale_px):
        self.window        = window
        self.tile_scale_px = tile_scale_px

        # Preload fonts
        self.font_large  = pygame.font.SysFont("Arial", 150, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", 50)
        self.font_small  = pygame.font.SysFont("Arial", 30)

    # -------------------- Main draw -------------------- #
    def draw(self, gamestate):
        # set entire background to white (majority of tiles are white anyway)
        self.window.fill((255, 255, 255))
        
        self.draw_map(gamestate.level)
        self.draw_entities(gamestate.monster, gamestate.robots)
        self.draw_ui(gamestate)

        if gamestate.monster.is_caught:
            self.draw_end_text()
        
        pygame.display.flip()

    # -------------------- Map -------------------- #
    def draw_map(self, level):
        for y, row in enumerate(level.level_map):
            for x, tile in enumerate(row):
                rect = pygame.Rect(x*self.tile_scale_px, y*self.tile_scale_px,
                                     self.tile_scale_px,   self.tile_scale_px)
                
                # Draw tile background
                if tile == level.WALL:
                    pygame.draw.rect(self.window, (0,0,0), rect)
                else:
                    pygame.draw.rect(self.window, (255,255,255), rect)

                # Draw coins / doors
                if tile == level.COIN:
                    self.coin = pygame.image.load('coin.png')
                    self._blit_center(self.coin, rect)
                elif tile == level.DOOR:
                    self.door = pygame.image.load('door.png')
                    self._blit_center(self.door, rect)

                # Draw tile border
                pygame.draw.rect(self.window, (128,128,128), rect, width=2)
    
    # -------------------- Entities -------------------- #
    def draw_entities(self, monster, robots):
        # Use monster.image from the monster instance
        self._blit_center(monster.image, self._tile_rect(monster.position))
        
        for robot in robots:
            self._blit_center(robot.image, self._tile_rect(robot.position))
        
    # -------------------- UI -------------------- #
    def draw_ui(self, gamestate):
        level    = gamestate.level
        monster  = gamestate.monster

        w, h = level.win_size
        y_offset = h * self.tile_scale_px + 20

        # Level and coins collected
        texts = [
            (self.font_small, f"Level: {level.level_num}", (255,0,0), 1200),
            (self.font_small, f"Coins: {monster.coins_carried}/{level.num_coins}", (0,0,255), 1600),
            (self.font_small, "F2 = new game", (0,0,0), 100),
            (self.font_small, "Esc = quit game", (0,0,0), 400)
        ]

        for font, text, color, x in texts:
            surf = font.render(text, True, color)
            self.window.blit(surf, (x, y_offset))

        # Set window title
        pygame.display.set_caption(f"MyGame - Level {level.level_num}")

    # -------------------- Helpers -------------------- #
    def _tile_rect(self, position):
        x, y = position
        return pygame.Rect(x*self.tile_scale_px, y*self.tile_scale_px,
                             self.tile_scale_px,   self.tile_scale_px)

    def _blit_center(self, image, rect):
        x = rect.x + (self.tile_scale_px - image.get_width())/2
        y = rect.y + (self.tile_scale_px - image.get_height())/2
        self.window.blit(image, (x, y))

    # -------------------- Screens -------------------- #
    def draw_title_screen(self):
        self.window.fill((0, 0, 0))
        lines = [
            (self.font_large, "You are the monster!"),
            (self.font_medium, "Move with the arrow-keys and collect all coins without getting caught."),
            (self.font_medium, "Good luck! :)"),
            (self.font_small, "Press any key to start!")
        ]
        self._draw_centered_lines(lines)
        pygame.display.flip()

    def draw_end_text(self):
        self.window.fill((0,0,0))
        lines = [
            (self.font_large, "You were caught!"),
            (self.font_small, "<Please press F2 to restart or Esc to exit>")
        ]
        self._draw_centered_lines(lines)
        pygame.display.flip()

    def _draw_centered_lines(self, lines):
        total_height = sum(font.size(text)[1] + 20 for font, text in lines)
        start_y = self.tile_scale_px * 10 / 2 - total_height / 2  # adjust if map size changes
        current_y = start_y
        for font, text in lines:
            surf = font.render(text, True, (255,0,0))
            rect = surf.get_rect(center=(self.tile_scale_px*20/2, current_y))
            self.window.blit(surf, rect)
            current_y += surf.get_height() + 20


class LevelManager:
    def __init__(self, map_size, internal_walls):
        self.map_size       = map_size
        self.internal_walls = internal_walls
        self.level_num      = 0

    def get_level_params(self):
        # linear growth with saturation
        num_robots     = min(5, 1 + (self.level_num - 1) // 2)
        num_coins      = min(10, 5 + 2 * ((self.level_num - 1) // 3))
        
        # robot speed with lower limit
        robot_speed_ms = max(500, 2000 - 100 * self.level_num)
       
        return num_robots, num_coins, robot_speed_ms

    def generate_level(self):
        # initiate level_map
        self.level_num += 1
        
        num_robots, num_coins, robot_speed_ms = self.get_level_params()
        level = Level( win_size=self.map_size, num_internal_walls=self.internal_walls, num_coins=num_coins, level_num=self.level_num )
        
        return level, num_robots, robot_speed_ms


class EntitySpawner:
    @staticmethod
    def spawn_monster(level):
        """
        Randomly place the monster on a valid position.
        NOTE: need to be sure that there are walkable empty spaces left!!!
        """
        while True:
            pos = (randint(0, level.win_size[0]-1), randint(0, level.win_size[1]-1))
            if level.is_walkable(pos):
                return Monster(pos)

    @staticmethod
    def spawn_robots(level, monster_pos, num_robots, robot_speed_ms, min_distance=3):
        """
        Place robots at valid positions:
        - Cannot be on walls, coins, doors, or monster
        - Cannot overlap with other robots
        - cannot be spawned within min_distance to monster
        """
        robots = []
        used_positions = {monster_pos}
        while len(robots) < num_robots:
            pos = (randint(0, level.win_size[0]-1), randint(0, level.win_size[1]-1))
            if (level.is_spawnable(pos) and pos not in used_positions and max(abs(pos[0]-monster_pos[0]), abs(pos[1]-monster_pos[1])) >= min_distance):
                robots.append(Robot(pos, robot_speed_ms))
                used_positions.add(pos)
        return robots


class GameApplication:
    def __init__(self):
        pygame.init()

        self.clock                      = pygame.time.Clock()
        self.input_handler              = InputHandler()
        self.running                    = True
        self.level_manager              = LevelManager(map_size=(20,10), internal_walls=15)
        self.last_robot_update_time     = 0

        # Initialize window & renderer
        self.tile_scale_px              = 100
        self.map_width, self.map_height = self.level_manager.map_size
        window_width                    = self.map_width * self.tile_scale_px
        window_height                   = self.map_height * self.tile_scale_px + self.tile_scale_px
        self.window                     = pygame.display.set_mode((window_width, window_height))
        self.renderer                   = Renderer(self.window, self.tile_scale_px)

    def run(self):
        # Draw title screen first (waits for key)
        self.renderer.draw_title_screen()
        if self.input_handler.wait_for_keypress(self.clock) == "quit":
            self.running = False
            return

        # Start the first level
        self.start_level()

        # run game loop
        while self.running:
            self.game_loop()

    def game_loop(self):
        # read input
        dx, dy, restart, quit_game = self.input_handler.read_input()
        
        if quit_game:
            self.running = False
            return
        if restart:
            self.level_manager.level_num = 0
            self.start_level()
            return
        if self.gamestate.level_finished:
            self.start_level()
            return

        # Delay robot movement
        current_time = pygame.time.get_ticks()
        self.gamestate.try_move_monster(dx, dy)
        if not self.gamestate.level_finished and current_time - self.last_robot_update_time >= self.robot_speed_ms:
            self.gamestate.update_robots()
            self.last_robot_update_time = current_time

        # Draw everything
        self.renderer.draw(self.gamestate)
        self.clock.tick(30)

    def start_level(self):
        self.level, self.num_robots, self.robot_speed_ms = self.level_manager.generate_level()
        
        self.monster                = EntitySpawner.spawn_monster(self.level)
        self.robots                 = EntitySpawner.spawn_robots(self.level, self.monster.position, self.num_robots, self.robot_speed_ms)
        self.gamestate              = GameState(level=self.level, monster=self.monster, robots=self.robots)
        self.last_robot_update_time = 0


if __name__ == "__main__":
    game = GameApplication()
    game.run()