import math
import random
from dataclasses import dataclass, field
from enum import Enum
import pyray as ray

# ============================================================
# WINDOW
# ============================================================
SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 900
WINDOW_TITLE = "Industrial Warehouse - Y/Z Load Robot + Extraction Robot"

# ============================================================
# WAREHOUSE GEOMETRY
# ============================================================
LEVEL_Y = [2.5, 8.0, 13.5]
LINE_Z = [-9.0, -3.0, 3.0, 9.0]
LEVEL_COUNT = len(LEVEL_Y)
LINE_COUNT = len(LINE_Z)

CONVEYOR_X = [-8.0, 0.0, 8.0]
CONVEYOR_LENGTH = 7.0
CONVEYOR_WIDTH = 3.0
CONVEYOR_HEIGHT = 0.55
CONVEYOR_Y_OFFSET = 0.0

BELT_SCROLL_SPEED = 2.2
BELT_STRIPE_SPACING = 1.0
BELT_STRIPE_WIDTH = 0.14

# ============================================================
# HALL FOOTPRINT
# ============================================================
HALL_HALF_WIDTH = 18.0
HALL_WIDTH = HALL_HALF_WIDTH * 2.0
HALL_DEPTH = 28.0
HALL_BACK_Z = 13.5

# ============================================================
# LOADING ROBOT CONFIG
# ============================================================
ROBOT_X = -13.0
ROBOT_COLUMN_HEIGHT = 17.0
ROBOT_RAIL_LENGTH = 26.0
ROBOT_RAIL_THICKNESS = 0.35
ROBOT_HEAD_SIZE = 0.75
ROBOT_SPEED_Y = 5.0
ROBOT_SPEED_Z = 7.0

HOME_LEVEL = 0
HOME_LINE = 1

# ============================================================
# EXTRACTION ROBOT CONFIG
# ============================================================
EXTRACT_ROBOT_X = 13.0
EXTRACT_HOME_LEVEL = 0
EXTRACT_HOME_LINE = 1

# ============================================================
# BOX CONFIG
# ============================================================
BOX_LENGTH = 1.30
BOX_WIDTH = 1.00
BOX_HEIGHT = 0.85
CRATE_WALL_THICKNESS = 0.07
BOX_SPEED = 3.5

CRATE_TYPES = [
    ray.Color(60, 140, 205, 255),
    ray.Color(60, 170, 95, 255),
    ray.Color(215, 140, 40, 255),
    ray.Color(150, 75, 175, 255),
]

ITEM_COLORS = [
    ray.Color(230, 70, 60, 255),
    ray.Color(240, 200, 40, 255),
    ray.Color(60, 190, 190, 255),
    ray.Color(235, 235, 235, 255),
    ray.Color(90, 90, 100, 255),
]

STORAGE_Y_GAP = 0.02
LANE_GAP = 0.04
LANE_START_X = CONVEYOR_X[0] - CONVEYOR_LENGTH / 2.0 + BOX_LENGTH / 2.0
LANE_TIP_X = CONVEYOR_X[2] + CONVEYOR_LENGTH / 2.0 - BOX_LENGTH / 2.0
LANE_SLOT_PITCH = BOX_LENGTH + LANE_GAP
LANE_CAPACITY_PER_LAYER = max(1, int((LANE_TIP_X - LANE_START_X) / LANE_SLOT_PITCH) + 1)

FORK_TINE_RADIUS = 0.05
FORK_TINE_SPACING = BOX_WIDTH * 0.55
FORK_TINE_LENGTH = BOX_LENGTH * 0.9
GRIPPER_DROP = BOX_HEIGHT / 2.0 + 0.20

# ============================================================
# INFEED / OUTFEED CONFIG
# ============================================================
INFEED_Y = LEVEL_Y[HOME_LEVEL]
INFEED_Z = LINE_Z[HOME_LINE]
INFEED_WALL_X = -(HALL_HALF_WIDTH - 0.5)
INFEED_DOCK_X = ROBOT_X
INFEED_SPEED = 3.0

OUTFEED_Y = LEVEL_Y[EXTRACT_HOME_LEVEL]
OUTFEED_Z = LINE_Z[EXTRACT_HOME_LINE]
OUTFEED_DOCK_X = EXTRACT_ROBOT_X
OUTFEED_WALL_X = HALL_HALF_WIDTH - 0.5
OUTFEED_SPEED = 3.0

# ============================================================
# SCANNER GATE CONFIG
# ============================================================
SCANNER_X = -(HALL_HALF_WIDTH - 2.5)
SCANNER_GATE_WIDTH = BOX_WIDTH + 0.9
SCANNER_GATE_HEIGHT = BOX_HEIGHT + 1.3
SCAN_DURATION = 0.9

SCANNER_FRAME_COLOR = ray.Color(40, 45, 50, 255)
SCANNER_LASER_COLOR = ray.Color(230, 40, 40, 255)
SCANNER_LASER_IDLE_COLOR = ray.Color(230, 40, 40, 110)
SCANNER_PANEL_COLOR = ray.Color(15, 20, 25, 255)
SCANNER_BARCODE_LIGHT = ray.Color(235, 235, 235, 255)
SCANNER_BARCODE_DARK = ray.Color(20, 20, 25, 255)
SCANNER_OK_COLOR = ray.Color(60, 200, 90, 255)

SCAN_GREY_CRATE = ray.Color(150, 152, 156, 255)
SCAN_GREY_ITEM_LIGHT = ray.Color(197, 199, 202, 255)
SCAN_GREY_ITEM_DARK = ray.Color(108, 110, 114, 255)

# ============================================================
# COLORS
# ============================================================
BACKGROUND = ray.Color(225, 230, 235, 255)
FLOOR_COLOR = ray.Color(125, 130, 135, 255)
WALL_COLOR = ray.Color(185, 190, 195, 255)
BEAM_COLOR = ray.Color(80, 85, 90, 255)
CONVEYOR_FRAME_COLOR = ray.Color(55, 60, 65, 255)
CONVEYOR_BELT_COLOR = ray.Color(80, 90, 95, 255)
BELT_STRIPE_COLOR = ray.Color(45, 50, 55, 255)
ROLLER_DRUM_COLOR = ray.Color(35, 38, 42, 255)
RAIL_COLOR = ray.Color(70, 75, 80, 255)
ROBOT_COLOR = ray.Color(55, 65, 75, 255)
FORK_TINE_COLOR = ray.Color(210, 60, 50, 255)
EXTRACT_ROBOT_COLOR = ray.Color(70, 55, 100, 255)
EXTRACT_FORK_TINE_COLOR = ray.Color(40, 130, 210, 255)
BOX_EDGE_COLOR = ray.Color(40, 40, 45, 255)
TARGET_COLOR = ray.Color(220, 70, 60, 255)
EXTRACT_TARGET_COLOR = ray.Color(40, 130, 210, 255)
HOME_COLOR = ray.Color(50, 180, 90, 255)
EXTRACT_HOME_COLOR = ray.Color(230, 160, 20, 255)
INFEED_FRAME_COLOR = ray.Color(255, 195, 0, 255)
OUTFEED_FRAME_COLOR = ray.Color(40, 130, 210, 255)
INFEED_HOLE_COLOR = ray.Color(20, 20, 22, 255)
TEXT_COLOR = ray.Color(20, 25, 30, 255)

# ============================================================
# STATES ENUMS
# ============================================================
class RobotState(Enum):
    IDLE = 0
    MOVING_TO_TARGET_Y = 1
    MOVING_TO_TARGET_Z = 2
    RELEASING = 3
    RETURNING_HOME_Y = 4
    RETURNING_HOME_Z = 5

class ExtractState(Enum):
    IDLE = 0
    MOVING_TO_SOURCE_Y = 1
    MOVING_TO_SOURCE_Z = 2
    PICKING = 3
    RETURNING_TO_DROP_Y = 4
    RETURNING_TO_DROP_Z = 5
    RELEASING = 6

class BoxState(Enum):
    SPAWNING = 0
    SCANNING = 1
    WAITING = 2
    HELD = 3
    ON_CONVEYOR = 4
    STORED = 5
    EXTRACT_HELD = 6
    EXITING = 7
    SHIFTING = 8

def generate_crate_items():
    item_count = random.randint(5, 8)
    items = []
    for _ in range(item_count):
        dx = random.uniform(-BOX_LENGTH / 2.0 + 0.18, BOX_LENGTH / 2.0 - 0.18)
        dz = random.uniform(-BOX_WIDTH / 2.0 + 0.18, BOX_WIDTH / 2.0 - 0.18)
        dy = BOX_HEIGHT / 2.0 - 0.10 + random.uniform(-0.05, 0.10)
        color = random.choice(ITEM_COLORS)
        items.append((dx, dy, dz, color))
    return items

@dataclass
class Box:
    x: float
    y: float
    z: float
    level: int = 0
    line: int = 0
    state: BoxState = BoxState.SPAWNING
    lane_slot: int = 0
    stored_layer: int = 0
    crate_type: int = 0
    items: list = field(default_factory=list)
    scanned: bool = False
    scan_timer: float = 0.0

# ============================================================
# SCENE GRAPH FRAMEWORK ENGINE
# ============================================================
class SceneNode:
    def __init__(self, position=(0.0, 0.0, 0.0)):
        self.position = ray.Vector3(*position)
        self.parent = None
        self.children = []
        self.world_matrix = ray.matrix_identity()

    def add_child(self, child):
        if child.parent:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)

    def remove_child(self, child):
        if child in self.children:
            child.parent = None
            self.children.remove(child)

    def update_transform(self, parent_matrix=None):
        local = ray.matrix_translate(self.position.x, self.position.y, self.position.z)
        if parent_matrix is None:
            self.world_matrix = local
        else:
            self.world_matrix = ray.matrix_multiply(local, parent_matrix)
        for child in self.children:
            child.update_transform(self.world_matrix)

    def get_world_position(self) -> ray.Vector3:
        return ray.Vector3(self.world_matrix.m12, self.world_matrix.m13, self.world_matrix.m14)

class BoxNode(SceneNode):
    def __init__(self, box_data: Box):
        super().__init__(position=(box_data.x, box_data.y, box_data.z))
        self.data = box_data

    def draw(self):
        pos = self.get_world_position()
        pending_scan = (not self.data.scanned) and self.data.state in (BoxState.SPAWNING, BoxState.SCANNING)
        crate_color = SCAN_GREY_CRATE if pending_scan else CRATE_TYPES[self.data.crate_type % len(CRATE_TYPES)]
        
        half_length = BOX_LENGTH / 2.0
        half_width = BOX_WIDTH / 2.0
        wall = CRATE_WALL_THICKNESS

        # Base Mesh
        ray.draw_cube(ray.Vector3(pos.x, pos.y - BOX_HEIGHT / 2.0 + wall / 2.0, pos.z), BOX_LENGTH, wall, BOX_WIDTH, crate_color)
        
        # Longitudinal Walls
        for wall_z in (pos.z - half_width + wall / 2.0, pos.z + half_width - wall / 2.0):
            ray.draw_cube(ray.Vector3(pos.x, pos.y, wall_z), BOX_LENGTH, BOX_HEIGHT, wall, crate_color)
            
        # Lateral Walls
        for wall_x in (pos.x - half_length + wall / 2.0, pos.x + half_length - wall / 2.0):
            ray.draw_cube(ray.Vector3(wall_x, pos.y, pos.z), wall, BOX_HEIGHT, BOX_WIDTH, crate_color)

        # Internal Items
        for i, (dx, dy, dz, item_color) in enumerate(self.data.items):
            draw_color = (SCAN_GREY_ITEM_LIGHT if i % 2 == 0 else SCAN_GREY_ITEM_DARK) if pending_scan else item_color
            ray.draw_cube(ray.Vector3(pos.x + dx, pos.y + dy, pos.z + dz), 0.16, 0.16, 0.16, draw_color)

        edge_color = SCANNER_LASER_COLOR if self.data.state == BoxState.SCANNING else BOX_EDGE_COLOR
        ray.draw_cube_wires(pos, BOX_LENGTH + 0.02, BOX_HEIGHT + 0.02, BOX_WIDTH + 0.02, edge_color)

class RobotGraph(SceneNode):
    def __init__(self, base_x, is_extractor=False):
        super().__init__(position=(base_x, 0.0, 0.0))
        self.is_extractor = is_extractor
        self.carriage = SceneNode(position=(0.0, LEVEL_Y[HOME_LEVEL], LINE_Z[HOME_LINE]))
        self.fork = SceneNode(position=(0.0, -GRIPPER_DROP, 0.0))
        self.add_child(self.carriage)
        self.carriage.add_child(self.fork)
        
        self.robot_color = EXTRACT_ROBOT_COLOR if is_extractor else ROBOT_COLOR
        self.tine_color = EXTRACT_FORK_TINE_COLOR if is_extractor else FORK_TINE_COLOR
        self.column_z = 12.0 
        if is_extractor else -12.0def draw(self):# 1. Structural Rail Stackray.draw_cube(ray.Vector3(self.position.x, ROBOT_COLUMN_HEIGHT / 2.0 - 0.5, self.column_z), 0.8, ROBOT_COLUMN_HEIGHT, 0.8, self.robot_color)ray.draw_cube(ray.Vector3(self.position.x, self.carriage.position.y, 0.0), 0.65, 0.65, ROBOT_RAIL_LENGTH, RAIL_COLOR)# 2. Extract Head Transform Matricescar_pos = self.carriage.get_world_position()ray.draw_cube(car_pos, ROBOT_HEAD_SIZE, ROBOT_HEAD_SIZE, ROBOT_HEAD_SIZE, self.robot_color)# 3. Dynamic Relative Tooling Base Assemblyfork_pos = self.fork.get_world_position()ray.draw_cube(ray.Vector3(fork_pos.x, (car_pos.y + fork_pos.y) / 2.0, fork_pos.z), 0.12, car_pos.y - fork_pos.y, FORK_TINE_SPACING + 0.15, self.robot_color)tine_y = fork_pos.y - BOX_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02for z_off in (-FORK_TINE_SPACING / 2.0, FORK_TINE_SPACING / 2.0):ray.draw_cylinder_ex(ray.Vector3(self.position.x - FORK_TINE_LENGTH / 2.0, tine_y, fork_pos.z + z_off),ray.Vector3(self.position.x + FORK_TINE_LENGTH / 2.0, tine_y, fork_pos.z + z_off),FORK_TINE_RADIUS, FORK_TINE_RADIUS, 10, self.tine_color)============================================================CAMERA CONTROLLER INTERFACE============================================================class WarehouseCamera:def init(self):self.reset()def reset(self):self.target = ray.Vector3(0.0, 7.0, 0.0)self.distance = 38.0self.yaw = math.radians(135.0)self.pitch = math.radians(25.0)self.camera = ray.Camera3D(ray.Vector3(0.0, 0.0, 0.0), self.target, ray.Vector3(0.0, 1.0, 0.0), 45.0, ray.CAMERA_PERSPECTIVE)self.update_camera()def update_camera(self):cos_pitch = math.cos(self.pitch)self.camera.position = ray.Vector3(self.target.x + self.distance * cos_pitch * math.cos(self.yaw),self.target.y + self.distance * math.sin(self.pitch),self.target.z + self.distance * cos_pitch * math.sin(self.yaw))self.camera.target = self.targetdef update(self, focal_target=None):if focal_target:self.target = focal_targetelse:mouse_delta = ray.get_mouse_delta()if ray.is_mouse_button_down(ray.MOUSE_BUTTON_LEFT):sensitivity = 0.005self.yaw -= mouse_delta.x * sensitivityself.pitch -= mouse_delta.y * sensitivityself.pitch = max(math.radians(-80), min(math.radians(80), self.pitch))if ray.is_mouse_button_down(ray.MOUSE_BUTTON_MIDDLE):pan_speed = 0.035 * self.distanceforward = ray.Vector3(self.camera.target.x - self.camera.position.x, 0.0, self.camera.target.z - self.camera.position.z)length = math.sqrt(forward.x * forward.x + forward.z * forward.z)if length > 0.001:forward.x /= lengthforward.z /= lengthright = ray.Vector3(forward.z, 0.0, -forward.x)self.target.x -= right.x * mouse_delta.x * pan_speedself.target.z -= right.z * mouse_delta.x * pan_speedself.target.x += forward.x * mouse_delta.y * pan_speedself.target.z += forward.z * mouse_delta.y * pan_speedwheel = ray.get_mouse_wheel_move()if abs(wheel) > 0.01:self.distance -= wheel * 2.0self.distance = max(8.0, min(90.0, self.distance))keyboard_pan_speed = 0.15if ray.is_key_down(ray.KEY_W): self.target.z -= keyboard_pan_speedif ray.is_key_down(ray.KEY_S): self.target.z += keyboard_pan_speedif ray.is_key_down(ray.KEY_A): self.target.x -= keyboard_pan_speedif ray.is_key_down(ray.KEY_D): self.target.x += keyboard_pan_speedself.update_camera()============================================================FIXED RENDERING PRIMITIVES============================================================def draw_conveyor(x, y, z, belt_offset):ray.draw_cube(ray.Vector3(x, y, z), CONVEYOR_LENGTH, CONVEYOR_HEIGHT, CONVEYOR_WIDTH, CONVEYOR_BELT_COLOR)stripe_top_y = y + CONVEYOR_HEIGHT / 2.0 + 0.01half_length = CONVEYOR_LENGTH / 2.0offset = belt_offset % BELT_STRIPE_SPACINGstripe_local_x = -half_length + offsetwhile stripe_local_x < half_length:if -half_length <= stripe_local_x <= half_length:ray.draw_cube(ray.Vector3(x + stripe_local_x, stripe_top_y, z), BELT_STRIPE_WIDTH, 0.02, CONVEYOR_WIDTH - 0.15, BELT_STRIPE_COLOR)stripe_local_x += BELT_STRIPE_SPACINGframe_y = y - 0.45ray.draw_cube(ray.Vector3(x, frame_y, z - CONVEYOR_WIDTH / 2), CONVEYOR_LENGTH, 0.45, 0.18, CONVEYOR_FRAME_COLOR)ray.draw_cube(ray.Vector3(x, frame_y, z + CONVEYOR_WIDTH / 2), CONVEYOR_LENGTH, 0.45, 0.18, CONVEYOR_FRAME_COLOR)for leg_x in [x - CONVEYOR_LENGTH / 2 + 0.7, x + CONVEYOR_LENGTH / 2 - 0.7]:ray.draw_cube(ray.Vector3(leg_x, y - 1.0, z - CONVEYOR_WIDTH / 2 + 0.15), 0.22, 1.4, 0.22, CONVEYOR_FRAME_COLOR)ray.draw_cube(ray.Vector3(leg_x, y - 1.0, z + CONVEYOR_WIDTH / 2 - 0.15), 0.22, 1.4, 0.22, CONVEYOR_FRAME_COLOR)roller_count = 8for i in range(roller_count):roller_x = x - CONVEYOR_LENGTH / 2 + 0.4 + i * ((CONVEYOR_LENGTH - 0.8) / (roller_count - 1))ray.draw_cylinder_ex(ray.Vector3(roller_x, y + CONVEYOR_HEIGHT / 2 + 0.02, z - CONVEYOR_WIDTH / 2 + 0.05), ray.Vector3(roller_x, y + CONVEYOR_HEIGHT / 2 + 0.02, z + CONVEYOR_WIDTH / 2 - 0.05), 0.09, 0.09, 10, ray.Color(120, 125, 130, 255))for drum_x in [x - CONVEYOR_LENGTH / 2, x + CONVEYOR_LENGTH / 2]:ray.draw_cylinder_ex(ray.Vector3(drum_x, y, z - CONVEYOR_WIDTH / 2 + 0.02), ray.Vector3(drum_x, y, z + CONVEYOR_WIDTH / 2 - 0.02), CONVEYOR_HEIGHT / 2.0 + 0.05, CONVEYOR_HEIGHT / 2.0 + 0.05, 14, ROLLER_DRUM_COLOR)def draw_fork_rail_platform(x_start, x_end, rail_y, z):for z_off in (-FORK_TINE_SPACING / 2.0, FORK_TINE_SPACING / 2.0):ray.draw_cylinder_ex(ray.Vector3(x_start, rail_y, z + z_off), ray.Vector3(x_end, rail_y, z + z_off), FORK_TINE_RADIUS + 0.02, FORK_TINE_RADIUS + 0.02, 10, CONVEYOR_FRAME_COLOR)for x_post in (x_start, x_end):ray.draw_cube(ray.Vector3(x_post, rail_y - 0.35, z), 0.08, 0.70, FORK_TINE_SPACING + 0.15, CONVEYOR_FRAME_COLOR)def draw_release_platform(level_y, line_z):mouth_x = CONVEYOR_X[0] - CONVEYOR_LENGTH / 2.0draw_fork_rail_platform(mouth_x - 0.9, mouth_x + 0.1, level_y + CONVEYOR_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02, line_z)def draw_infeed_station(simulation):opening_height = BOX_HEIGHT + 0.5opening_width = BOX_WIDTH + 0.5ray.draw_cube(ray.Vector3(-HALL_HALF_WIDTH, INFEED_Y, INFEED_Z), 0.5, opening_height, opening_width, INFEED_HOLE_COLOR)ray.draw_cube_wires(ray.Vector3(-HALL_HALF_WIDTH, INFEED_Y, INFEED_Z), 0.5, opening_height, opening_width, INFEED_FRAME_COLOR)draw_fork_rail_platform(INFEED_WALL_X - 0.3, INFEED_DOCK_X + 0.3, INFEED_Y - BOX_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02, INFEED_Z)gate_x = SCANNER_Xfor z_off in (-SCANNER_GATE_WIDTH / 2.0, SCANNER_GATE_WIDTH / 2.0):ray.draw_cube(ray.Vector3(gate_x, INFEED_Y, INFEED_Z + z_off), 0.12, SCANNER_GATE_HEIGHT, 0.12, SCANNER_FRAME_COLOR)ray.draw_cube(ray.Vector3(gate_x, INFEED_Y + SCANNER_GATE_HEIGHT / 2.0, INFEED_Z), 0.16, 0.16, SCANNER_GATE_WIDTH + 0.12, SCANNER_FRAME_COLOR)scanning_box = simulation.get_scanning_box()if scanning_box is not None:progress = min(1.0, scanning_box.data.scan_timer / SCAN_DURATION)laser_y = INFEED_Y - SCANNER_GATE_HEIGHT / 2.0 + progress * SCANNER_GATE_HEIGHTlaser_color = SCANNER_LASER_COLORelse:idle_phase = (simulation.elapsed_time * 0.6) % 1.0laser_y = INFEED_Y - SCANNER_GATE_HEIGHT / 2.0 + idle_phase * SCANNER_GATE_HEIGHTlaser_color = SCANNER_LASER_IDLE_COLORray.draw_cube(ray.Vector3(gate_x, laser_y, INFEED_Z), 0.03, 0.03, SCANNER_GATE_WIDTH, laser_color)panel_x, panel_y, panel_z = gate_x, INFEED_Y + SCANNER_GATE_HEIGHT / 2.0 + 0.35, INFEED_Z - SCANNER_GATE_WIDTH / 2.0 - 0.02ray.draw_cube(ray.Vector3(panel_x, panel_y, panel_z), 0.05, 0.5, 0.7, SCANNER_PANEL_COLOR)if scanning_box is not None:bar_count, bar_span = 9, 0.6for i in range(bar_count):seed = i * 12.9898 + math.floor(simulation.elapsed_time * 12.0) * 78.233bar_width = 0.02 + 0.03 * abs(math.sin(seed))bar_z = panel_z - bar_span / 2.0 + i * (bar_span / bar_count)ray.draw_cube(ray.Vector3(panel_x - 0.03, panel_y + 0.15, bar_z), 0.02, 0.32, bar_width, SCANNER_BARCODE_LIGHT if (i % 2 == 0) else SCANNER_BARCODE_DARK)if scanning_box.data.scan_timer / SCAN_DURATION > 0.85:ray.draw_cube(ray.Vector3(panel_x - 0.04, panel_y - 0.15, panel_z), 0.02, 0.14, 0.5, SCANNER_OK_COLOR)def draw_outfeed_station():opening_height = BOX_HEIGHT + 0.5opening_width = BOX_WIDTH + 0.5ray.draw_cube(ray.Vector3(HALL_HALF_WIDTH, OUTFEED_Y, OUTFEED_Z), 0.5, opening_height, opening_width, INFEED_HOLE_COLOR)ray.draw_cube_wires(ray.Vector3(HALL_HALF_WIDTH, OUTFEED_Y, OUTFEED_Z), 0.5, opening_height, opening_width, OUTFEED_FRAME_COLOR)draw_fork_rail_platform(OUTFEED_DOCK_X - 0.3, OUTFEED_WALL_X + 0.3, OUTFEED_Y - BOX_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02, OUTFEED_Z)def draw_warehouse(belt_offset, simulation):ray.draw_cube(ray.Vector3(0.0, -0.6, 0.0), HALL_WIDTH, 1.0, HALL_DEPTH, FLOOR_COLOR)ray.draw_cube(ray.Vector3(0.0, 8.0, HALL_BACK_Z), HALL_WIDTH, 17.0, 0.4, WALL_COLOR)ray.draw_cube(ray.Vector3(-HALL_HALF_WIDTH, 8.0, 0.0), 0.4, 17.0, HALL_DEPTH, WALL_COLOR)ray.draw_cube(ray.Vector3(HALL_HALF_WIDTH, 8.0, 0.0), 0.4, 17.0, HALL_DEPTH, WALL_COLOR)for level, y in enumerate(LEVEL_Y):ray.draw_cube(ray.Vector3(0.0, y - 0.65, 12.5), HALL_WIDTH - 1.0, 0.35, 0.5, BEAM_COLOR)ray.draw_text(f"LEVEL {level + 1}", 30, int(SCREEN_HEIGHT - 90 - level * 35), 22, TEXT_COLOR)for z in LINE_Z:ray.draw_cube(ray.Vector3(HALL_HALF_WIDTH - 1.5, 8.0, z), 0.45, 17.0, 0.45, BEAM_COLOR)ray.draw_cube(ray.Vector3(-(HALL_HALF_WIDTH - 1.5), 8.0, z), 0.45, 17.0, 0.45, BEAM_COLOR)for level, y in enumerate(LEVEL_Y):for line, z in enumerate(LINE_Z):for section, x in enumerate(CONVEYOR_X):draw_conveyor(x, y + CONVEYOR_Y_OFFSET, z, belt_offset)draw_release_platform(y + CONVEYOR_Y_OFFSET, z)draw_infeed_station(simulation)draw_outfeed_station()============================================================TARGET AND HOME BOUNDS PRIMITIVES============================================================def draw_target(level, line):y, z = LEVEL_Y[level], LINE_Z[line]ray.draw_cube_wires(ray.Vector3(CONVEYOR_X[0], y + 1.0, z), 2.0, 2.0, 2.0, TARGET_COLOR)ray.draw_line_3d(ray.Vector3(CONVEYOR_X[0], y + 1.0, z - 1.5), ray.Vector3(CONVEYOR_X[0], y + 1.0, z + 1.5), TARGET_COLOR)def draw_extract_target(level, line):y, z = LEVEL_Y[level], LINE_Z[line]ray.draw_cube_wires(ray.Vector3(CONVEYOR_X[2], y + 1.0, z), 2.0, 2.0, 2.0, EXTRACT_TARGET_COLOR)ray.draw_line_3d(ray.Vector3(CONVEYOR_X[2], y + 1.0, z - 1.5), ray.Vector3(CONVEYOR_X[2], y + 1.0, z + 1.5), EXTRACT_TARGET_COLOR)def draw_home_markers():ray.draw_cube_wires(ray.Vector3(ROBOT_X, LEVEL_Y[HOME_LEVEL], LINE_Z[HOME_LINE]), 1.8, 1.8, 1.8, HOME_COLOR)ray.draw_cube_wires(ray.Vector3(EXTRACT_ROBOT_X, LEVEL_Y[EXTRACT_HOME_LEVEL], LINE_Z[EXTRACT_HOME_LINE]), 1.8, 1.8, 1.8, EXTRACT_HOME_COLOR)============================================================CORE SIMULATION ENGINE============================================================class WarehouseSimulation:def init(self):self.root = SceneNode()self.load_robot = RobotGraph(ROBOT_X, is_extractor=False)self.extract_robot = RobotGraph(EXTRACT_ROBOT_X, is_extractor=True)self.root.add_child(self.load_robot)self.root.add_child(self.extract_robot)self.target_level = 0self.target_line = 0self.state = RobotState.IDLEself.extract_target_level = EXTRACT_HOME_LEVELself.extract_target_line = EXTRACT_HOME_LINEself.extract_state = ExtractState.IDLEself.boxes = []self.elapsed_time = 0.0self.last_response = "READY"self.storage = [[0 for _ in range(LINE_COUNT)] for _ in range(LEVEL_COUNT)]self.lane_next_slot = [[0 for _ in range(LINE_COUNT)] for _ in range(LEVEL_COUNT)]self.spawn_box()def spawn_box(self):box_data = Box(x=INFEED_WALL_X, y=INFEED_Y, z=INFEED_Z,level=self.target_level, line=self.target_line,state=BoxState.SPAWNING, crate_type=random.randrange(len(CRATE_TYPES)),items=generate_crate_items())node = BoxNode(box_data)self.root.add_child(node)self.boxes.append(node)def can_spawn_box(self):return not any(node.data.state in (BoxState.SPAWNING, BoxState.SCANNING, BoxState.WAITING, BoxState.HELD) for node in self.boxes)def get_held_box(self):for node in self.boxes:if node.data.state == BoxState.HELD: return nodereturn Nonedef get_extract_held_box(self):for node in self.boxes:if node.data.state == BoxState.EXTRACT_HELD: return nodereturn Nonedef get_scanning_box(self):for node in self.boxes:if node.data.state == BoxState.SCANNING: return nodereturn Nonedef get_extractable_box(self, level, line):candidates = [node for node in self.boxes if node.data.state == BoxState.STORED and node.data.level == level and node.data.line == line]if not candidates: return Nonereturn max(candidates, key=lambda node: (node.position.x, node.data.stored_layer))def shift_lane_forward(self, level, line, removed_slot):for node in self.boxes:if node.data.state != BoxState.STORED or node.data.level != level or node.data.line != line: continueif node.data.lane_slot <= removed_slot: continuenode.data.lane_slot -= 1layer = node.data.lane_slot // LANE_CAPACITY_PER_LAYERnode.data.stored_layer = layernode.position.y = LEVEL_Y[level] + CONVEYOR_HEIGHT / 2.0 + BOX_HEIGHT / 2.0 + layer * (BOX_HEIGHT + STORAGE_Y_GAP)node.data.state = BoxState.SHIFTINGdef update_shifting_boxes(self, dt):for node in self.boxes:if node.data.state != BoxState.SHIFTING: continuepos_in_layer = node.data.lane_slot % LANE_CAPACITY_PER_LAYERtarget_x = LANE_TIP_X - pos_in_layer * LANE_SLOT_PITCHnode.position.x += BOX_SPEED * dtif node.position.x >= target_x:node.position.x = target_xnode.data.state = BoxState.STOREDdef get_infeed_status(self):for node in self.boxes:if node.data.state == BoxState.SCANNING: return "SCANNING"if node.data.state == BoxState.SPAWNING: return "SPAWNING"if node.data.state == BoxState.WAITING: return "WAITING"if self.get_held_box() is not None: return "HELD"return "READY"def _robot_at_home(self):return (abs(self.load_robot.carriage.position.y - LEVEL_Y[HOME_LEVEL]) < 0.01 andabs(self.load_robot.carriage.position.z - LINE_Z[HOME_LINE]) < 0.01)def select_level(self, level):if self.state == RobotState.IDLE and 0 <= level < LEVEL_COUNT: self.target_level = leveldef select_line(self, line):if self.state == RobotState.IDLE and 0 <= line < LINE_COUNT: self.target_line = linedef select_extract_level(self, level):if self.extract_state == ExtractState.IDLE and 0 <= level < LEVEL_COUNT: self.extract_target_level = leveldef select_extract_line(self, line):if self.extract_state == ExtractState.IDLE and 0 <= line < LINE_COUNT: self.extract_target_line = linedef send_robot(self):if self.state != RobotState.IDLE: returnbox = self.get_held_box()if box is None: returnbox.data.level = self.target_levelbox.data.line = self.target_lineself.state = RobotState.MOVING_TO_TARGET_Ydef send_extract_robot(self):if self.extract_state == ExtractState.IDLE and self.storage[self.extract_target_level][self.extract_target_line] > 0:self.extract_state = ExtractState.MOVING_TO_SOURCE_Ydef handle_command(self, command):if not command: return self._respond("ERR empty command")cmd = command.strip().upper()parts = cmd.split()if len(parts) == 2 and parts[1].lstrip("-").isdigit():val = int(parts[1])if parts[0] == "LEVEL": return self._cmd_select_level(val)if parts[0] in ("LINE", "TRACK"): return self._cmd_select_line(val)if parts[0] == "XLEVEL": return self._cmd_select_extract_level(val)if parts[0] in ("XLINE", "XTRACK"): return self._cmd_select_extract_line(val)if cmd in ("SEND", "GO", "G"): return self._cmd_send()if cmd in ("XSEND", "XGO", "XG"): return self._cmd_extract_send()if cmd in ("NEWBOX", "NEW", "N"): return self._cmd_new_box()if cmd in ("STATUS", "S"): return self._cmd_status()if len(cmd) >= 3 and cmd[0:2] == "XL" and cmd[2:].isdigit(): return self._cmd_select_extract_level(int(cmd[2:]))if len(cmd) >= 3 and cmd[0:2] == "XT" and cmd[2:].isdigit(): return self._cmd_select_extract_line(int(cmd[2:]))if len(cmd) >= 2 and cmd[0] == "L" and cmd[1:].isdigit(): return self._cmd_select_level(int(cmd[1:]))if len(cmd) >= 2 and cmd[0] == "T" and cmd[1:].isdigit(): return self._cmd_select_line(int(cmd[1:]))return self._respond(f"ERR unknown command '{command}'")def _respond(self, msg):self.last_response = msgreturn msgdef _cmd_select_level(self, n):if self.state != RobotState.IDLE: return self._respond("ERR robot busy")if not (1 <= n <= LEVEL_COUNT): return self._respond(f"ERR level out of range (1-{LEVEL_COUNT})")self.select_level(n - 1)return self._respond(f"OK LEVEL {n}")def _cmd_select_line(self, n):if self.state != RobotState.IDLE: return self._respond("ERR robot busy")if not (1 <= n <= LINE_COUNT): return self._respond(f"ERR line out of range (1-{LINE_COUNT})")self.select_line(n - 1)return self._respond(f"OK LINE {n}")def _cmd_select_extract_level(self, n):if self.extract_state != ExtractState.IDLE: return self._respond("ERR extractor busy")if not (1 <= n <= LEVEL_COUNT): return self._respond(f"ERR extract level out of range (1-{LEVEL_COUNT})")self.select_extract_level(n - 1)return self._respond(f"OK XLEVEL {n}")def _cmd_select_extract_line(self, n):if self.extract_state != ExtractState.IDLE: return self._respond("ERR extractor busy")if not (1 <= n <= LINE_COUNT): return self._respond(f"ERR extract line out of range (1-{LINE_COUNT})")self.select_extract_line(n - 1)return self._respond(f"OK XLINE {n}")def _cmd_send(self):if self.state != RobotState.IDLE: return self._respond("ERR robot busy")if self.get_held_box() is None: return self._respond("ERR no box held")self.send_robot()return self._respond(f"OK SEND L{self.target_level + 1} T{self.target_line + 1}")def _cmd_extract_send(self):if self.extract_state != ExtractState.IDLE: return self._respond("ERR extractor busy")if self.storage[self.extract_target_level][self.extract_target_line] <= 0: return self._respond("ERR nothing stored there")self.send_extract_robot()return self._respond(f"OK XSEND L{self.extract_target_level + 1} T{self.extract_target_line + 1}")def _cmd_new_box(self):if not self.can_spawn_box(): return self._respond("ERR box already pending")self.spawn_box()return self._respond("OK NEWBOX")def _cmd_status(self):return self._respond(f"LOAD={self.state.name} TARGET=L{self.target_level + 1}T{self.target_line + 1} INFEED={self.get_infeed_status()} | EXTRACT={self.extract_state.name} XTARGET=L{self.extract_target_level + 1}T{self.extract_target_line + 1}")def move_value(self, current, target, speed, dt):diff = target - currentstep = speed * dtif abs(diff) <= step: return target, Truereturn current + (step if diff > 0 else -step), Falsedef update_robot(self, dt):if self.state == RobotState.MOVING_TO_TARGET_Y:self.load_robot.carriage.position.y, reached = self.move_value(self.load_robot.carriage.position.y, LEVEL_Y[self.target_level], ROBOT_SPEED_Y, dt)if reached: self.state = RobotState.MOVING_TO_TARGET_Zelif self.state == RobotState.MOVING_TO_TARGET_Z:self.load_robot.carriage.position.z, reached = self.move_value(self.load_robot.carriage.position.z, LINE_Z[self.target_line], ROBOT_SPEED_Z, dt)if reached: self.state = RobotState.RELEASINGelif self.state == RobotState.RELEASING:box = self.get_held_box()if box is not None:self.load_robot.fork.remove_child(box)self.root.add_child(box)box.data.state = BoxState.ON_CONVEYORbox.data.lane_slot = self.lane_next_slot[self.target_level][self.target_line]self.lane_next_slot[self.target_level][self.target_line] += 1box.position = ray.Vector3(LANE_START_X, LEVEL_Y[self.target_level] + CONVEYOR_HEIGHT / 2.0 + BOX_HEIGHT / 2.0, LINE_Z[self.target_line])self.state = RobotState.RETURNING_HOME_Yelif self.state == RobotState.RETURNING_HOME_Y:self.load_robot.carriage.position.y, reached = self.move_value(self.load_robot.carriage.position.y, LEVEL_Y[HOME_LEVEL], ROBOT_SPEED_Y, dt)if reached: self.state = RobotState.RETURNING_HOME_Zelif self.state == RobotState.RETURNING_HOME_Z:self.load_robot.carriage.position.z, reached = self.move_value(self.load_robot.carriage.position.z, LINE_Z[HOME_LINE], ROBOT_SPEED_Z, dt)if reached: self.state = RobotState.IDLEif self.state == RobotState.IDLE: self.try_pickup_waiting_box()def update_extract_robot(self, dt):if self.extract_state == ExtractState.MOVING_TO_SOURCE_Y:self.extract_robot.carriage.position.y, reached = self.move_value(self.extract_robot.carriage.position.y, LEVEL_Y[self.extract_target_level], ROBOT_SPEED_Y, dt)if reached: self.extract_state = ExtractState.MOVING_TO_SOURCE_Zelif self.extract_state == ExtractState.MOVING_TO_SOURCE_Z:self.extract_robot.carriage.position.z, reached = self.move_value(self.extract_robot.carriage.position.z, LINE_Z[self.extract_target_line], ROBOT_SPEED_Z, dt)if reached: self.extract_state = ExtractState.PICKINGelif self.extract_state == ExtractState.PICKING:node = self.get_extractable_box(self.extract_target_level, self.extract_target_line)if node is not None:rem_slot = node.data.lane_slotself.storage[self.extract_target_level][self.extract_target_line] -= 1self.lane_next_slot[self.extract_target_level][self.extract_target_line] -= 1node.data.state = BoxState.EXTRACT_HELDself.root.remove_child(node)self.extract_robot.fork.add_child(node)node.position = ray.Vector3(0.0, 0.0, 0.0)self.shift_lane_forward(self.extract_target_level, self.extract_target_line, rem_slot)self.extract_state = ExtractState.RETURNING_TO_DROP_Yelif self.extract_state == ExtractState.RETURNING_TO_DROP_Y:self.extract_robot.carriage.position.y, reached = self.move_value(self.extract_robot.carriage.position.y, LEVEL_Y[EXTRACT_HOME_LEVEL], ROBOT_SPEED_Y, dt)if reached: self.extract_state = ExtractState.RETURNING_TO_DROP_Zelif self.extract_state == ExtractState.RETURNING_TO_DROP_Z:self.extract_robot.carriage.position.z, reached = self.move_value(self.extract_robot.carriage.position.z, LINE_Z[EXTRACT_HOME_LINE], ROBOT_SPEED_Z, dt)if reached: self.extract_state = ExtractState.RELEASINGelif self.extract_state == ExtractState.RELEASING:node = self.get_extract_held_box()if node is not None:self.extract_robot.fork.remove_child(node)self.root.add_child(node)node.data.state = BoxState.EXITINGnode.position = ray.Vector3(OUTFEED_DOCK_X, OUTFEED_Y, OUTFEED_Z)self.extract_state = ExtractState.IDLEdef update_infeed_boxes(self, dt):for node in self.boxes:if node.data.state == BoxState.SPAWNING:node.position.x += INFEED_SPEED * dtif not node.data.scanned and node.position.x >= SCANNER_X:node.position.x = SCANNER_Xnode.data.state = BoxState.SCANNINGnode.data.scan_timer = 0.0elif node.data.scanned and node.position.x >= INFEED_DOCK_X:node.position.x = INFEED_DOCK_Xnode.data.state = BoxState.WAITINGelif node.data.state == BoxState.SCANNING:node.data.scan_timer += dtif node.data.scan_timer >= SCAN_DURATION:node.data.scanned = Truenode.data.state = BoxState.SPAWNINGself.try_pickup_waiting_box()def try_pickup_waiting_box(self):if self.state != RobotState.IDLE or self.get_held_box() is not None or not self._robot_at_home(): returnfor node in self.boxes:if node.data.state == BoxState.WAITING:node.data.state = BoxState.HELDself.root.remove_child(node)self.load_robot.fork.add_child(node)node.position = ray.Vector3(0.0, 0.0, 0.0)returndef update_exiting_boxes(self, dt):rem = []for node in self.boxes:if node.data.state == BoxState.EXITING:node.position.x += OUTFEED_SPEED * dtif node.position.x >= OUTFEED_WALL_X:self.root.remove_child(node)continuerem.append(node)self.boxes = remdef update_boxes(self, dt):for node in self.boxes:if node.data.state != BoxState.ON_CONVEYOR: continuelayer = node.data.lane_slot // LANE_CAPACITY_PER_LAYERpos_in_layer = node.data.lane_slot % LANE_CAPACITY_PER_LAYERtarget_x = LANE_TIP_X - pos_in_layer * LANE_SLOT_PITCHnode.position.x += BOX_SPEED * dtif node.position.x >= target_x:node.position.x = target_xself.settle_box(node, layer)def settle_box(self, node, layer):self.storage[node.data.level][node.data.line] += 1node.data.state = BoxState.STOREDnode.data.stored_layer = layernode.position.y = LEVEL_Y[node.data.level] + CONVEYOR_HEIGHT / 2.0 + BOX_HEIGHT / 2.0 + layer * (BOX_HEIGHT + STORAGE_Y_GAP)node.position.z = LINE_Z[node.data.line]def update(self, dt):self.elapsed_time += dtself.update_robot(dt)self.update_infeed_boxes(dt)self.update_boxes(dt)self.update_shifting_boxes(dt)self.update_extract_robot(dt)self.update_exiting_boxes(dt)self.root.update_transform()def draw_boxes(self):for node in self.boxes: node.draw()============================================================INTERACTIVE FRAMEWORK LAYER DISPLAY============================================================def draw_ui(simulation):ray.draw_rectangle(15, 15, 365, 265, ray.Color(245, 245, 245, 235))ray.draw_rectangle_lines(15, 15, 365, 265, ray.Color(70, 70, 70, 255))ray.draw_text("LOADING ROBOT", 30, 30, 24, TEXT_COLOR)ray.draw_text("LEVEL", 30, 70, 18, TEXT_COLOR)ray.draw_text("1 / 2 / 3", 140, 70, 18, TEXT_COLOR)ray.draw_text("LINE", 30, 100, 18, TEXT_COLOR)ray.draw_text("U / I / O / P", 140, 100, 18, TEXT_COLOR)ray.draw_text("ENTER", 30, 130, 18, TEXT_COLOR)ray.draw_text("Send robot", 140, 130, 18, TEXT_COLOR)ray.draw_text("N", 30, 160, 18, TEXT_COLOR)ray.draw_text("Request new box", 140, 160, 18, TEXT_COLOR)ray.draw_text("R", 30, 190, 18, TEXT_COLOR)ray.draw_text("Reset camera / Focus Mode", 140, 190, 15, TEXT_COLOR)ray.draw_text("Mouse", 30, 220, 18, TEXT_COLOR)ray.draw_text("L: rotate   M: pan   Wheel: zoom", 140, 220, 15, TEXT_COLOR)ray.draw_text(f"CMD: {simulation.last_response}", 30, 250, 16, TEXT_COLOR)panel_x, panel_y = 15, 295ray.draw_rectangle(panel_x, panel_y, 365, 200, ray.Color(232, 238, 248, 235))ray.draw_rectangle_lines(panel_x, panel_y, 365, 200, ray.Color(50, 80, 120, 255))ray.draw_text("EXTRACTION ROBOT", panel_x + 15, panel_y + 15, 24, TEXT_COLOR)ray.draw_text("LEVEL", panel_x + 15, panel_y + 55, 18, TEXT_COLOR)ray.draw_text("7 / 8 / 9", panel_x + 125, panel_y + 55, 18, TEXT_COLOR)ray.draw_text("LINE", panel_x + 15, panel_y + 85, 18, TEXT_COLOR)ray.draw_text("Z / X / C / V", panel_x + 125, panel_y + 85, 18, TEXT_COLOR)ray.draw_text("SPACE", panel_x + 15, panel_y + 115, 18, TEXT_COLOR)ray.draw_text("Extract box", panel_x + 125, panel_y + 115, 18, TEXT_COLOR)ray.draw_text(f"XTARGET: L{simulation.extract_target_level + 1} T{simulation.extract_target_line + 1}", panel_x + 15, panel_y + 150, 16, TEXT_COLOR)ray.draw_text(f"XSTATE: {simulation.extract_state.name}", panel_x + 15, panel_y + 172, 16, TEXT_COLOR)ray.draw_text(f"LOAD TARGET: Level {simulation.target_level + 1}, Line {simulation.target_line + 1}", 20, SCREEN_HEIGHT - 65, 22, TEXT_COLOR)ray.draw_text(f"LOAD ROBOT: {simulation.state.name}   INFEED: {simulation.get_infeed_status()}   |   EXTRACT ROBOT: {simulation.extract_state.name}", 20, SCREEN_HEIGHT - 35, 20, TEXT_COLOR)def draw_storage_info(simulation):x, y = SCREEN_WIDTH - 310, 20ray.draw_rectangle(x - 10, y - 10, 290, 160, ray.Color(245, 245, 245, 235))ray.draw_rectangle_lines(x - 10, y - 10, 290, 160, ray.Color(70, 70, 70, 255))ray.draw_text("STORAGE", x, y, 22, TEXT_COLOR)y += 30for level in range(LEVEL_COUNT):for line in range(LINE_COUNT):count = simulation.storage[level][line]if count > 0:text = f"L{level + 1} / Line {line + 1}: {count} box" + ("es" if count != 1 else "")ray.draw_text(text, x, y, 16, TEXT_COLOR)y += 20if y > 155: return============================================================APPLICATION INITIALIZATION ENGINE============================================================def main():ray.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, WINDOW_TITLE)ray.set_target_fps(60)camera_controller = WarehouseCamera()simulation = WarehouseSimulation()focus_mode = Falsewhile not ray.window_should_close():dt = ray.get_frame_time()if ray.is_key_pressed(ray.KEY_ONE): simulation.handle_command("L1")elif ray.is_key_pressed(ray.KEY_TWO): simulation.handle_command("L2")elif ray.is_key_pressed(ray.KEY_THREE): simulation.handle_command("L3")if ray.is_key_pressed(ray.KEY_U): simulation.handle_command("T1")elif ray.is_key_pressed(ray.KEY_I): simulation.handle_command("T2")elif ray.is_key_pressed(ray.KEY_O): simulation.handle_command("T3")elif ray.is_key_pressed(ray.KEY_P): simulation.handle_command("T4")if ray.is_key_pressed(ray.KEY_ENTER): simulation.handle_command("SEND")if ray.is_key_pressed(ray.KEY_N): simulation.handle_command("NEWBOX")if ray.is_key_pressed(ray.KEY_SEVEN): simulation.handle_command("XL1")elif ray.is_key_pressed(ray.KEY_EIGHT): simulation.handle_command("XL2")elif ray.is_key_pressed(ray.KEY_NINE): simulation.handle_command("XL3")if ray.is_key_pressed(ray.KEY_Z): simulation.handle_command("XT1")elif ray.is_key_pressed(ray.KEY_X): simulation.handle_command("XT2")elif ray.is_key_pressed(ray.KEY_C): simulation.handle_command("XT3")elif ray.is_key_pressed(ray.KEY_V): simulation.handle_command("XT4")if ray.is_key_pressed(ray.KEY_SPACE): simulation.handle_command("XSEND")if ray.is_key_pressed(ray.KEY_R):camera_controller.reset()focus_mode = Falseif ray.is_key_pressed(ray.KEY_F):focus_mode = not focus_modesimulation.update(dt)if focus_mode:camera_controller.update(focal_target=simulation.load_robot.carriage.get_world_position())else:camera_controller.update()belt_offset = simulation.elapsed_time * BELT_SCROLL_SPEEDray.begin_drawing()ray.clear_background(BACKGROUND)ray.begin_mode_3d(camera_controller.camera)draw_warehouse(belt_offset, simulation)draw_target(simulation.target_level, simulation.target_line)draw_extract_target(simulation.extract_target_level, simulation.extract_target_line)draw_home_markers()simulation.load_robot.draw()simulation.extract_robot.draw()simulation.draw_boxes()