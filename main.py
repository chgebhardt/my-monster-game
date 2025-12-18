# Complete your game here

# * Concept
#   You play as the monster. Coins are "packages" you need to collect and deliver to the door. 
#   Robots act as patrolling obstacles that try to catch you. 
#   The goal is to gather coins and reach the door without getting caught.

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
        self.x, self.y        = position
        self.speed_ms         = robot_speed_ms
        self.last_update_time = 0

        self.image = pygame.image.load("robot.png")

    @property
    def width(self):
        return self.image.get_width()

    @property
    def height(self):
        return self.image.get_height()

    def propose_move(self, dx: int, dy: int):
        """
        returns the proposed new position without changing self.x and self.y themselves.
        """
        return self.x + dx, self.y + dy


class InputHandler:
    def __init__(self):
        self.keymap = {
            pygame.K_UP:    (0, -1),
            pygame.K_DOWN:  (0, 1),
            pygame.K_LEFT:  (-1, 0),
            pygame.K_RIGHT: (1, 0),
        }

    def process_events(self):
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


class GameApplication:
    '''
    GameApplication class for game state management.
    '''
    def __init__(self):
        pygame.init()

        self.clock                  = pygame.time.Clock()
        
        self.level                  = None
        self.level_num              = 0
        self.level_finished         = False 
        self.monster                = None
        self.robots                 = []
        self.last_robot_update_time = 0 

        self.input_handler          = InputHandler()
        
        self.running                = True

# -------------------- Main Loop -------------------- #  

    def run(self):
        
        self.draw_title_screen()

        # start first level
        self.start_level()
        
        while self.running:
            
            print(f"Monster at {self.monster.position}, robots at {[(r.x, r.y) for r in self.robots]}")

            dx, dy, restart, quit_game = self.input_handler.process_events()

            # quits game
            if quit_game:
                self.running = False
                break

            # restart means: go back to level 0 and recreate the level
            if restart:
                self.level_num = 0
                self.start_level()
                continue

            # regular level completion
            if self.level_finished:
                self.start_level()
                continue

            current_time = pygame.time.get_ticks()

            self.draw_main()
            self.update_monster(dx, dy)

            # delay robot movement
            if current_time - self.last_robot_update_time >= self.robot_speed_ms:
                self.update_robots()
                self.last_robot_update_time = current_time

                
    # -------------------- Level Management -------------------- #
            
    def start_level(self):
        """
        Generate a new level and initialize all entities.
        """
        self.generate_level_map()
        self.initiate_window()

        self.seed_monster()
        self.seed_robots()

        self.level_finished         = False
        self.last_robot_update_time = 0  # reset robot timer  
        
    def get_level_params(self):

        # linear growth with saturation
        num_robots = min(5, 1 + (self.level_num - 1) // 2)  # 1 robot at level 1, +1 every 2 levels
        num_coins  = min(10, 5 + 2 * ((self.level_num - 1) // 3))  # 5 coins at level 1, +2 every 3 levels

        # robot speed with lower limit
        robot_speed_ms = max(500, 2000 - 100 * self.level_num)
   
        return num_robots, num_coins, robot_speed_ms

    def generate_level_map(self):
        
        # initiate level_map
        self.level_num += 1

        self.num_robots, num_coins, self.robot_speed_ms = self.get_level_params()
        self.level = Level(win_size=(20,10), num_internal_walls = 15, num_coins = num_coins, level_num = self.level_num)

    def initiate_window(self):
        # intiates window for display (each tile is of size (tile_scale_px x tile_scale_px) )
        self.map_width, self.map_height     = self.level.win_size
        self.tile_scale_px                  = 100

        window_height = self.tile_scale_px * self.map_height
        window_width  = self.tile_scale_px * self.map_width
        
        self.window = pygame.display.set_mode((window_width, window_height + self.tile_scale_px))

    def seed_monster(self):
        """
        Randomly place the monster on a valid position.
        NOTE: need to be sure that there are empty spaces left!!!
        """
        while True:
            initial_position = (randint(0, self.map_width - 1), randint(0, self.map_height - 1))
            
            if self.is_valid_monster_position(initial_position):
                self.monster = Monster(position=initial_position)
                break
        
    def seed_robots(self):
        """
        Place robots at valid positions:
        - Cannot be on walls, coins, doors, or monster
        - Cannot overlap with other robots
        """
        self.robots = []
        used_positions = {self.monster.position}

        while len(self.robots) < self.num_robots:
            initial_position = (
                randint(0, self.map_width - 1),
                randint(0, self.map_height - 1)
            )

            if (self.is_valid_robot_position(initial_position, None)  # temporarily pass None for robot
                and initial_position not in used_positions):
                
                robot = Robot(position=initial_position, robot_speed_ms=self.robot_speed_ms)
                self.robots.append(robot)
                used_positions.add(initial_position)

    # -------------------- Drawing -------------------- #

    def draw_main(self):
        # set entire background to white (majority of tiles are white anyway)
        self.window.fill((255, 255, 255))
        
        self.draw_map()
        self.draw_monster()
        self.draw_robots()
        self.draw_window_text()

        if self.monster.is_caught:
            self.draw_end_text()
            
        pygame.display.flip()
    
    def draw_map(self):
        for y in range(self.map_height):
            for x in range(self.map_width):
                tile = self.level.level_map[y][x]
                rect = pygame.Rect(x*self.tile_scale_px, y*self.tile_scale_px, self.tile_scale_px, self.tile_scale_px)

                # walls
                if tile == self.level.WALL:
                    pygame.draw.rect(self.window, (0, 0, 0), rect)

                # empty tiles
                elif tile == self.level.EMPTY:
                    pygame.draw.rect(self.window, (255, 255, 255), rect)

                # door
                elif tile == self.level.DOOR:
                    self.door = pygame.image.load('door.png')
                    self.window.blit(self.door, 
                                     ( x*self.tile_scale_px + (self.tile_scale_px - self.door.get_width())/2, 
                                       y*self.tile_scale_px + (self.tile_scale_px - self.door.get_height())/2 )
                                    )

                # coins                    
                elif tile == self.level.COIN:
                    self.coin = pygame.image.load('coin.png')
                    self.window.blit(self.coin, 
                                     ( x*self.tile_scale_px + (self.tile_scale_px - self.coin.get_width())/2, 
                                       y*self.tile_scale_px + (self.tile_scale_px - self.coin.get_height())/2 )
                                    )
                
                # Draw grey border on top of every tile
                pygame.draw.rect(self.window, (128, 128, 128), rect, width=2)

    def draw_monster(self):
        monster_x, monster_y = self.monster.position
        self.window.blit(self.monster.image, (monster_x*self.tile_scale_px + (self.tile_scale_px - self.monster.image.get_width())/2, 
                                              monster_y*self.tile_scale_px + (self.tile_scale_px - self.monster.image.get_height())/2)
                        )

    def draw_robots(self):
        for robot in self.robots: 
            self.window.blit(robot.image, (robot.x*self.tile_scale_px + (self.tile_scale_px - robot.image.get_width())/2, 
                                           robot.y*self.tile_scale_px + (self.tile_scale_px - robot.image.get_height())/2)
                            )

    def draw_title_screen(self):
        # Ensure window exists
        if not hasattr(self, "window") or self.window is None:
            self.map_width     = 20
            self.map_height    = 10
            self.tile_scale_px = 100
            window_width       = self.map_width * self.tile_scale_px
            window_height      = self.map_height * self.tile_scale_px
            self.window        = pygame.display.set_mode((window_width, window_height + self.tile_scale_px))

        # Fill background
        self.window.fill((0, 0, 0))

        # Fonts
        font1 = pygame.font.SysFont("Arial", 150, bold=True)
        font2 = pygame.font.SysFont("Arial", 50)
        font3 = pygame.font.SysFont("Arial", 30)

        # Lines to display
        lines = [
            (font1, "You are the monster!"),
            (font2, "Move with the arrow-keys and collect all coins without getting caught."),
            (font2, "Good luck! :)"),
            (font3, "Press any key to start!")
        ]

        # Draw lines with consistent spacing
        start_y = self.map_height * self.tile_scale_px / 2 - 150  # adjust start vertically if needed
        spacing = 20  # pixels between lines
        current_y = start_y

        for font, line in lines:
            text_surface = font.render(line, True, (255, 0, 0))
            text_rect = text_surface.get_rect(center=(self.map_width*self.tile_scale_px/2, current_y))
            self.window.blit(text_surface, text_rect)
            current_y += text_surface.get_height() + spacing

        pygame.display.flip()

        # Wait until a keypress
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                elif event.type == pygame.KEYDOWN:
                    waiting = False
            self.clock.tick(30)


    def draw_window_text(self):
        self.font = pygame.font.SysFont("Arial", 30)

        # update text in window
        text = self.font.render("F2 = new game", True, (0, 0, 0))
        self.window.blit(text, (100, self.map_height * self.tile_scale_px + 20))

        text = self.font.render("Esc = quit game", True, (0, 0, 0))
        self.window.blit(text, (400, self.map_height * self.tile_scale_px + 20))

        text = self.font.render(f"Level: {self.level_num}", True, (255, 0, 0))
        self.window.blit(text, (1200, self.map_height * self.tile_scale_px + 20))

        text = self.font.render(f"Coins collected: {self.monster.coins_carried}/{self.level.num_coins}", True, (0, 0, 255))
        self.window.blit(text, (1600, self.map_height * self.tile_scale_px + 20))

        # set display name
        pygame.display.set_caption(f"MyGame - Level {self.level_num}")

    def draw_end_text(self):
        self.window.fill((0, 0, 0))
    
        font1 = pygame.font.SysFont("Arial", 150, bold=True)
        font2 = pygame.font.SysFont("Arial", 30)

        lines = [(font1, "You were caught!"), (font2, "<Please press F2 to restart or Esc to exit>")]

        for ii, (font, line) in enumerate(lines):
            text_surface = font.render(line, True, (255, 0, 0))
        
            text_rect = text_surface.get_rect(center=(self.map_width*self.tile_scale_px/2,
                                                    self.map_height*self.tile_scale_px/2 + 3*ii*font.get_height()))
            self.window.blit(text_surface, text_rect)
                

# -------------------- Game Logic -------------------- #

    def update_monster(self, dx: int, dy: int):
        """
        Handles monster movement:
        - Validate move
        - Coin collection
        - Door/level completion
        - Collision with robots
        """
        proposed_position    = self.monster.propose_move(dx, dy)
        
        # validate move
        if self.is_valid_monster_position(proposed_position):
            self.monster.move_to(proposed_position)

        # coin collection (Coins are not moving and can therefore be checked directly in the instance of the Level class)
        if self.level.is_coin(proposed_position):
            self.monster.coins_carried += 1
            self.level.level_map[proposed_position[1]][proposed_position[0]] = ' '
        
        # Door/level completion (Doors are not moving and can therefore be checked directly in the instance of the Level class)
        if self.level.is_door(proposed_position) and (self.monster.coins_carried == self.level.num_coins):
            self.level.level_map[proposed_position[1]][proposed_position[0]] = ' '
            self.level_finished = True

        # monster collides with robots
        robot_positions = {(robot.x, robot.y) for robot in self.robots}
        if proposed_position in robot_positions:
            # Monster is caught by robot
            self.monster.is_caught = True

    def update_robots(self):
        """
        Moves all robots:
        - Propose moves
        - Validate against walls, doors, other robots
        - Update positions
        - Detect if monster is caught
        """
        for robot in self.robots:
            possible_robot_moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]

            valid_positions = []

            for dx, dy in possible_robot_moves:
                proposed_position = robot.propose_move(dx, dy)

                if self.is_valid_robot_position(proposed_position, robot):
                    valid_positions.append(proposed_position)

            if valid_positions:
                monster_x, monster_y = self.monster.position
                # move towards monster
                robot.x, robot.y = min(
                    valid_positions,
                    key=lambda pos: sqrt((monster_x - pos[0])**2 + (monster_y - pos[1])**2)
                )
            else:
                # robot is stuck; optionally pick a random valid move if any
                fallback_positions = [robot.propose_move(dx, dy)
                    for dx, dy in possible_robot_moves
                    if self.validated_position(robot.propose_move(dx, dy))]
                if fallback_positions:
                    robot.x, robot.y = choice(fallback_positions)

            # a robot caught the monster    
            if proposed_position == (self.monster.position):
                # Monster is caught by robot
                self.monster.is_caught = True
                
    def is_valid_monster_position(self, position: tuple):
        """
        Monster can move anywhere except walls.
        """
        return self.level.is_not_wall(position)

    def is_valid_robot_position(self, position: tuple, robot: "Robot"):
        """
        Robot cannot move into walls, doors, coins, or other robots.
        """
        if not self.level.is_not_wall(position) or self.level.is_coin(position) or self.level.is_door(position):
            return False
        
        # Avoid other robots
        other_robots = {(r.x, r.y) for r in self.robots if r != robot}
        if position in other_robots:
            return False
        return True
            
            
if __name__ == "__main__":
    game = GameApplication()
    game.run()

    # level = Level(win_size=(20,9), num_internal_walls = 15, num_coins=5, level_num=1)
    # print(level)

    
