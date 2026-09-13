import math
import random
from dataclasses import dataclass, field
from enum import Enum

import pyray as ray

try:
    from bridge_client import BridgeClient
except Exception:
    BridgeClient = None

SIM_SOCKET_PATH = "/tmp/warehouse_sim.sock"
SKU_TYPES = {0: 15, 1: 25, 2: 40, 3: 30}


# ============================================================
# WINDOW
# ============================================================

SCREEN_WIDTH = 1500
SCREEN_HEIGHT = 900

WINDOW_TITLE = "Industrial Warehouse - Y/Z Load Robot + Extraction Robot"


# ============================================================
# WAREHOUSE GEOMETRY
# ============================================================

# Y = vertical direction
# Z = line direction
# X = conveyor direction
#
# Neither robot ever moves in X. Each one only moves in Y and Z,
# sliding along its own rail bolted to opposite ends of the hall.

LEVEL_Y = [
    2.5,   # Level 1
    8.0,   # Level 2
    13.5,  # Level 3
]

LINE_Z = [
    -9.0,  # Line 1
    -3.0,  # Line 2
     3.0,  # Line 3
     9.0,  # Line 4
]

LEVEL_COUNT = len(LEVEL_Y)
LINE_COUNT = len(LINE_Z)


# Conveyor sections along X
CONVEYOR_X = [
    -8.0,   # C1
     0.0,   # C2
     8.0,   # C3
]

CONVEYOR_LENGTH = 7.0
CONVEYOR_WIDTH = 3.0
CONVEYOR_HEIGHT = 0.55

CONVEYOR_Y_OFFSET = 0.0

# Visual speed of the scrolling belt stripes (purely cosmetic,
# independent from how fast boxes actually travel).
BELT_SCROLL_SPEED = 2.2
BELT_STRIPE_SPACING = 1.0
BELT_STRIPE_WIDTH = 0.14


# ============================================================
# HALL FOOTPRINT
# ============================================================

# The hall was widened on both ends so a second robot (the
# extraction robot) has its own clearance opposite the original
# loading robot, instead of being squeezed into the same corner.

HALL_HALF_WIDTH = 18.0    # was 16.0
HALL_WIDTH = HALL_HALF_WIDTH * 2.0
HALL_DEPTH = 28.0
HALL_BACK_Z = 13.5


# ============================================================
# LOADING ROBOT (puts new boxes INTO storage)
# ============================================================

# Fixed X position. Never translates along X.

ROBOT_X = -13.0

ROBOT_COLUMN_HEIGHT = 17.0

ROBOT_RAIL_LENGTH = 26.0

ROBOT_RAIL_THICKNESS = 0.35

ROBOT_HEAD_SIZE = 0.75

ROBOT_SPEED_Y = 5.0
ROBOT_SPEED_Z = 7.0


# Home position = Level 1 / Line 2
HOME_LEVEL = 0
HOME_LINE = 1


# ============================================================
# EXTRACTION ROBOT (pulls boxes back OUT of storage)
# ============================================================

# Mirror image of the loading robot, parked at the opposite end
# of the hall, on the opposite side of every lane. It always
# drops whatever it pulls out at the same fixed spot: Level 1 /
# Line 2, right next to the outfeed opening in the far wall.

EXTRACT_ROBOT_X = 13.0

EXTRACT_HOME_LEVEL = 0   # "plane 1"
EXTRACT_HOME_LINE = 1    # "ligne 2"


# ============================================================
# BOX
# ============================================================

# Crates are rectangular plastic bins, not solid cubes - open
# top, thin walls, full of small loose items so they read as
# actual plastic totes rather than blocks.
BOX_LENGTH = 1.30   # size along X (conveyor / infeed direction)
BOX_WIDTH = 1.00    # size along Z (line direction)
BOX_HEIGHT = 0.85   # size along Y (vertical)

CRATE_WALL_THICKNESS = 0.07

BOX_SPEED = 3.5

# Crate "type" is communicated purely by its color.
CRATE_TYPES = [
    ray.Color(60, 140, 205, 255),   # type A - blue
    ray.Color(60, 170, 95, 255),    # type B - green
    ray.Color(215, 140, 40, 255),   # type C - orange
    ray.Color(150, 75, 175, 255),   # type D - purple
]

# Loose small items rattling around inside each crate.
ITEM_COLORS = [
    ray.Color(230, 70, 60, 255),
    ray.Color(240, 200, 40, 255),
    ray.Color(60, 190, 190, 255),
    ray.Color(235, 235, 235, 255),
    ray.Color(90, 90, 100, 255),
]

# Once a lane is packed lengthwise, further crates start a new
# vertical layer on top instead of overlapping.
STORAGE_Y_GAP = 0.02

# Boxes queue up along the conveyor and are only ever allowed
# to advance until they touch the crate ahead of them (or the
# physical tip of the lane) - a real accumulation lane rather
# than boxes teleporting into a stack.
LANE_GAP = 0.04
LANE_START_X = CONVEYOR_X[0] - CONVEYOR_LENGTH / 2.0 + BOX_LENGTH / 2.0
LANE_TIP_X = CONVEYOR_X[2] + CONVEYOR_LENGTH / 2.0 - BOX_LENGTH / 2.0
LANE_SLOT_PITCH = BOX_LENGTH + LANE_GAP
LANE_CAPACITY_PER_LAYER = max(
    1,
    int((LANE_TIP_X - LANE_START_X) / LANE_SLOT_PITCH) + 1
)
LANE_MAX_BOXES = 10

# Forklift-style fork tines (the robots' grippers, and the
# matching rod platforms they drop crates onto / pick them up
# from) are just two parallel horizontal rods.
FORK_TINE_RADIUS = 0.05
FORK_TINE_SPACING = BOX_WIDTH * 0.55
FORK_TINE_LENGTH = BOX_LENGTH * 0.9
GRIPPER_DROP = BOX_HEIGHT / 2.0 + 0.20


# ============================================================
# INFEED (WALL OPENING WHERE NEW BOXES ARRIVE FROM)
# ============================================================

# New boxes never simply appear in mid-air. They slide in
# through an opening cut into the left side wall, ride a short
# landing ledge to a pickup dock next to the loading robot's
# home position, and only then are picked up by the robot.

INFEED_Y = LEVEL_Y[HOME_LEVEL]
INFEED_Z = LINE_Z[HOME_LINE]

INFEED_WALL_X = -(HALL_HALF_WIDTH - 0.5)   # where the box first appears
INFEED_DOCK_X = ROBOT_X                     # where it waits to be picked up
INFEED_SPEED = 3.0


# ============================================================
# OUTFEED (WALL OPENING WHERE EXTRACTED BOXES LEAVE THROUGH)
# ============================================================

# Mirror image of the infeed: whatever the extraction robot
# drops at its home dock (Level 1 / Line 2) rides a short ledge
# out through an opening in the right side wall and disappears
# from the warehouse - finished goods leaving the building.

OUTFEED_Y = LEVEL_Y[EXTRACT_HOME_LEVEL]
OUTFEED_Z = LINE_Z[EXTRACT_HOME_LINE]

OUTFEED_DOCK_X = EXTRACT_ROBOT_X
OUTFEED_WALL_X = HALL_HALF_WIDTH - 0.5
OUTFEED_SPEED = 3.0
RESTOCK_RETURN_Y = LEVEL_Y[EXTRACT_HOME_LEVEL]
RESTOCK_RETURN_Z = OUTFEED_Z + 2.0
RESTOCK_RETURN_DOCK_X = EXTRACT_ROBOT_X
RESTOCK_RETURN_WALL_X = HALL_HALF_WIDTH - 0.5
RESTOCK_SPEED = 3.0


# ============================================================
# SCANNER GATE (BARCODE / TYPE-CHECK STATION)
# ============================================================

# Every incoming crate passes through a scanning gate on its
# way from the wall opening to the pickup dock. While it hasn't
# been scanned yet it rides through as an anonymous grey tote;
# once the scan clears, its real crate-type color is revealed
# for the rest of its life in the warehouse.

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

# Extraction robot gets its own palette so the two machines are
# always visually distinguishable at a glance.
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
# LOADING ROBOT STATES
# ============================================================

class RobotState(Enum):
    IDLE = 0
    MOVING_TO_TARGET_Y = 1
    MOVING_TO_TARGET_Z = 2
    RELEASING = 3
    RETURNING_HOME_Y = 4
    RETURNING_HOME_Z = 5


# ============================================================
# EXTRACTION ROBOT STATES
# ============================================================

class ExtractState(Enum):
    IDLE = 0
    MOVING_TO_SOURCE_Y = 1
    MOVING_TO_SOURCE_Z = 2
    PICKING = 3
    RETURNING_TO_DROP_Y = 4
    RETURNING_TO_DROP_Z = 5
    RELEASING = 6


# ============================================================
# BOX STATES
# ============================================================

class BoxState(Enum):
    SPAWNING = 0      # sliding out of the wall opening
    SCANNING = 1      # paused in the scanner gate for the type-check
    WAITING = 2       # parked at the pickup dock, waiting for the robot
    HELD = 3          # attached to the loading robot's gripper
    ON_CONVEYOR = 4
    STORED = 5
    EXTRACT_HELD = 6  # attached to the extraction robot's gripper
    EXITING = 7       # sliding out through the outfeed opening
    SHIFTING = 8      # rolling forward to close the gap left behind
    RESTOCK_OUT = 9
    RESTOCK_IN = 10


def generate_crate_items():

    item_count = random.randint(5, 8)

    items = []

    for _ in range(item_count):

        dx = random.uniform(
            -BOX_LENGTH / 2.0 + 0.18,
            BOX_LENGTH / 2.0 - 0.18
        )

        dz = random.uniform(
            -BOX_WIDTH / 2.0 + 0.18,
            BOX_WIDTH / 2.0 - 0.18
        )

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

    # Which lane slot this crate is queued into (0 = resting at
    # the very tip of the lane, 1 = right behind it, and so on).
    lane_slot: int = 0
    stored_layer: int = 0

    crate_type: int = 0
    items: list = field(default_factory=list)

    # Scanner gate bookkeeping. Until `scanned` flips true the
    # crate is drawn as an anonymous grey tote (see draw_box).
    scanned: bool = False
    scan_timer: float = 0.0
    sku: int = 0
    quantity: int = 15
    placed: bool = False
    restock: bool = False
    origin_level: int = 0
    origin_line: int = 0
    origin_slot: int = 0
    origin_layer: int = 0


# ============================================================
# SCENE GRAPH
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

    def get_world_position(self):
        return ray.Vector3(self.world_matrix.m12, self.world_matrix.m13, self.world_matrix.m14)

    def set_position(self, x, y, z):
        self.position.x = x
        self.position.y = y
        self.position.z = z


# ============================================================
# CAMERA
# ============================================================

class WarehouseCamera:

    def __init__(self):
        self.reset()

    def reset(self):

        self.target = ray.Vector3(
            0.0,
            7.0,
            0.0
        )

        self.distance = 38.0

        self.yaw = math.radians(135.0)
        self.pitch = math.radians(25.0)

        self.camera = ray.Camera3D(
            ray.Vector3(0.0, 0.0, 0.0),
            self.target,
            ray.Vector3(0.0, 1.0, 0.0),
            45.0,
            ray.CAMERA_PERSPECTIVE
        )

        self.update_camera()

    def update_camera(self):

        cos_pitch = math.cos(self.pitch)

        self.camera.position = ray.Vector3(
            self.target.x
            + self.distance * cos_pitch * math.cos(self.yaw),

            self.target.y
            + self.distance * math.sin(self.pitch),

            self.target.z
            + self.distance * cos_pitch * math.sin(self.yaw)
        )

        self.camera.target = self.target

    def update(self):

        mouse_delta = ray.get_mouse_delta()

        # ----------------------------------------------------
        # ORBIT
        # Left mouse button
        # ----------------------------------------------------

        if ray.is_mouse_button_down(ray.MOUSE_BUTTON_LEFT):

            sensitivity = 0.005

            self.yaw -= mouse_delta.x * sensitivity
            self.pitch -= mouse_delta.y * sensitivity

            self.pitch = max(
                math.radians(-80),
                min(math.radians(80), self.pitch)
            )

        # ----------------------------------------------------
        # PAN
        # Middle mouse button
        # ----------------------------------------------------

        if ray.is_mouse_button_down(ray.MOUSE_BUTTON_MIDDLE):

            pan_speed = 0.035 * self.distance

            forward = ray.Vector3(
                self.camera.target.x - self.camera.position.x,
                0.0,
                self.camera.target.z - self.camera.position.z
            )

            length = math.sqrt(
                forward.x * forward.x +
                forward.z * forward.z
            )

            if length > 0.001:

                forward.x /= length
                forward.z /= length

                right = ray.Vector3(
                    forward.z,
                    0.0,
                    -forward.x
                )

                self.target.x -= right.x * mouse_delta.x * pan_speed
                self.target.z -= right.z * mouse_delta.x * pan_speed

                self.target.x += forward.x * mouse_delta.y * pan_speed
                self.target.z += forward.z * mouse_delta.y * pan_speed

        # ----------------------------------------------------
        # ZOOM
        # Mouse wheel
        # ----------------------------------------------------

        wheel = ray.get_mouse_wheel_move()

        if abs(wheel) > 0.01:

            self.distance -= wheel * 2.0

            self.distance = max(
                8.0,
                min(90.0, self.distance)
            )

        # ----------------------------------------------------
        # Keyboard camera movement
        # ----------------------------------------------------

        keyboard_pan_speed = 0.15

        if ray.is_key_down(ray.KEY_W):
            self.target.z -= keyboard_pan_speed

        if ray.is_key_down(ray.KEY_S):
            self.target.z += keyboard_pan_speed

        if ray.is_key_down(ray.KEY_A):
            self.target.x -= keyboard_pan_speed

        if ray.is_key_down(ray.KEY_D):
            self.target.x += keyboard_pan_speed

        # ----------------------------------------------------
        # Reset
        # ----------------------------------------------------

        if ray.is_key_pressed(ray.KEY_C):
            self.reset()

        self.update_camera()


# ============================================================
# CONVEYOR
# ============================================================

def draw_conveyor(x, y, z, belt_offset):

    # Main belt

    ray.draw_cube(
        ray.Vector3(
            x,
            y,
            z
        ),
        CONVEYOR_LENGTH,
        CONVEYOR_HEIGHT,
        CONVEYOR_WIDTH,
        CONVEYOR_BELT_COLOR
    )

    # Scrolling belt stripes, so the belt reads as something
    # that is actually moving rather than a static grey slab.

    stripe_top_y = y + CONVEYOR_HEIGHT / 2.0 + 0.01
    half_length = CONVEYOR_LENGTH / 2.0

    # Stripes scroll in +X, the same direction crates actually
    # travel down the belt (mouth -> tip).
    offset = belt_offset % BELT_STRIPE_SPACING
    stripe_local_x = -half_length + offset

    while stripe_local_x < half_length:

        if -half_length <= stripe_local_x <= half_length:

            ray.draw_cube(
                ray.Vector3(
                    x + stripe_local_x,
                    stripe_top_y,
                    z
                ),
                BELT_STRIPE_WIDTH,
                0.02,
                CONVEYOR_WIDTH - 0.15,
                BELT_STRIPE_COLOR
            )

        stripe_local_x += BELT_STRIPE_SPACING

    # Frame

    frame_y = y - 0.45

    ray.draw_cube(
        ray.Vector3(
            x,
            frame_y,
            z - CONVEYOR_WIDTH / 2
        ),
        CONVEYOR_LENGTH,
        0.45,
        0.18,
        CONVEYOR_FRAME_COLOR
    )

    ray.draw_cube(
        ray.Vector3(
            x,
            frame_y,
            z + CONVEYOR_WIDTH / 2
        ),
        CONVEYOR_LENGTH,
        0.45,
        0.18,
        CONVEYOR_FRAME_COLOR
    )

    # Support legs

    for leg_x in [
        x - CONVEYOR_LENGTH / 2 + 0.7,
        x + CONVEYOR_LENGTH / 2 - 0.7
    ]:

        ray.draw_cube(
            ray.Vector3(
                leg_x,
                y - 1.0,
                z - CONVEYOR_WIDTH / 2 + 0.15
            ),
            0.22,
            1.4,
            0.22,
            CONVEYOR_FRAME_COLOR
        )

        ray.draw_cube(
            ray.Vector3(
                leg_x,
                y - 1.0,
                z + CONVEYOR_WIDTH / 2 - 0.15
            ),
            0.22,
            1.4,
            0.22,
            CONVEYOR_FRAME_COLOR
        )

    # Idler rollers along the length

    roller_count = 8

    for i in range(roller_count):

        roller_x = (
            x
            - CONVEYOR_LENGTH / 2
            + 0.4
            + i * (
                (CONVEYOR_LENGTH - 0.8)
                / (roller_count - 1)
            )
        )

        ray.draw_cylinder_ex(
            ray.Vector3(
                roller_x,
                y + CONVEYOR_HEIGHT / 2 + 0.02,
                z - CONVEYOR_WIDTH / 2 + 0.05
            ),
            ray.Vector3(
                roller_x,
                y + CONVEYOR_HEIGHT / 2 + 0.02,
                z + CONVEYOR_WIDTH / 2 - 0.05
            ),
            0.09,
            0.09,
            10,
            ray.Color(120, 125, 130, 255)
        )

    # Larger drive drums at each end, like a real belt conveyor

    for drum_x in [
        x - CONVEYOR_LENGTH / 2,
        x + CONVEYOR_LENGTH / 2
    ]:

        ray.draw_cylinder_ex(
            ray.Vector3(
                drum_x,
                y,
                z - CONVEYOR_WIDTH / 2 + 0.02
            ),
            ray.Vector3(
                drum_x,
                y,
                z + CONVEYOR_WIDTH / 2 - 0.02
            ),
            CONVEYOR_HEIGHT / 2.0 + 0.05,
            CONVEYOR_HEIGHT / 2.0 + 0.05,
            14,
            ROLLER_DRUM_COLOR
        )


# ============================================================
# WAREHOUSE
# ============================================================

def draw_warehouse(belt_offset, simulation):

    # Floor

    ray.draw_cube(
        ray.Vector3(
            0.0,
            -0.6,
            0.0
        ),
        HALL_WIDTH,
        1.0,
        HALL_DEPTH,
        FLOOR_COLOR
    )

    pass_walls_invisible = True
    if not pass_walls_invisible:
        ray.draw_cube(
            ray.Vector3(
                0.0,
                8.0,
                HALL_BACK_Z
            ),
            HALL_WIDTH,
            17.0,
            0.4,
            WALL_COLOR
        )
        ray.draw_cube(
            ray.Vector3(
                -HALL_HALF_WIDTH,
                8.0,
                0.0
            ),
            0.4,
            17.0,
            HALL_DEPTH,
            WALL_COLOR
        )
        ray.draw_cube(
            ray.Vector3(
                HALL_HALF_WIDTH,
                8.0,
                0.0
            ),
            0.4,
            17.0,
            HALL_DEPTH,
            WALL_COLOR
        )

    # Level beams

    for level, y in enumerate(LEVEL_Y):

        ray.draw_cube(
            ray.Vector3(
                0.0,
                y - 0.65,
                12.5
            ),
            HALL_WIDTH - 1.0,
            0.35,
            0.5,
            BEAM_COLOR
        )

        # Level label

        ray.draw_text(
            f"LEVEL {level + 1}",
            30,
            int(
                SCREEN_HEIGHT
                - 90
                - level * 35
            ),
            22,
            TEXT_COLOR
        )

    # Vertical structural beams (both sides of the hall)

    for z in LINE_Z:

        ray.draw_cube(
            ray.Vector3(
                HALL_HALF_WIDTH - 1.5,
                8.0,
                z
            ),
            0.45,
            17.0,
            0.45,
            BEAM_COLOR
        )

        ray.draw_cube(
            ray.Vector3(
                -(HALL_HALF_WIDTH - 1.5),
                8.0,
                z
            ),
            0.45,
            17.0,
            0.45,
            BEAM_COLOR
        )

    if hasattr(simulation, "conveyor_nodes") and len(simulation.conveyor_nodes) == LEVEL_COUNT * LINE_COUNT * len(CONVEYOR_X):
        for n in simulation.conveyor_nodes:
            wp = n.get_world_position()
            draw_conveyor(wp.x, wp.y, wp.z, belt_offset)
        for level, y in enumerate(LEVEL_Y):
            for line, z in enumerate(LINE_Z):
                draw_release_platform(y + CONVEYOR_Y_OFFSET, z)
    else:
        for level, y in enumerate(LEVEL_Y):
            for line, z in enumerate(LINE_Z):
                for section, x in enumerate(CONVEYOR_X):
                    draw_conveyor(x, y + CONVEYOR_Y_OFFSET, z, belt_offset)
                draw_release_platform(y + CONVEYOR_Y_OFFSET, z)

    # Infeed opening + scanner gate where new boxes arrive from

    draw_infeed_station(simulation)

    # Outfeed opening where extracted boxes leave through

    draw_outfeed_station(simulation)


# ============================================================
# INFEED STATION (WALL OPENING + LANDING LEDGE + SCANNER)
# ============================================================

def draw_infeed_station(simulation):

    opening_height = BOX_HEIGHT + 0.5
    opening_width = BOX_WIDTH + 0.5

    # Hole punched through the side wall. Drawn slightly wider
    # than the wall thickness so it reads as an actual opening
    # rather than a patch stuck on the surface.

    ray.draw_cube(
        ray.Vector3(
            -HALL_HALF_WIDTH,
            INFEED_Y,
            INFEED_Z
        ),
        0.5,
        opening_height,
        opening_width,
        INFEED_HOLE_COLOR
    )

    ray.draw_cube_wires(
        ray.Vector3(
            -HALL_HALF_WIDTH,
            INFEED_Y,
            INFEED_Z
        ),
        0.5,
        opening_height,
        opening_width,
        INFEED_FRAME_COLOR
    )

    # Landing platform the crate rides on from the wall to the
    # pickup dock: two parallel metal rods, like the two tines
    # of a forklift, rather than a solid ledge. The loading
    # robot's own fork (see draw_robot) slides onto this same
    # rod pattern when it comes to collect a waiting crate.

    draw_fork_rail_platform(
        INFEED_WALL_X - 0.3,
        INFEED_DOCK_X + 0.3,
        INFEED_Y - BOX_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02,
        INFEED_Z
    )

    # Barcode / type-check scanner gate the crate passes
    # through partway along that ride.

    draw_scanner_station(simulation)


def draw_scanner_station(simulation):

    gate_x = SCANNER_X

    # Two vertical posts framing the gate the crate glides
    # through, like an airport security arch.

    for z_off in (-SCANNER_GATE_WIDTH / 2.0, SCANNER_GATE_WIDTH / 2.0):

        ray.draw_cube(
            ray.Vector3(gate_x, INFEED_Y, INFEED_Z + z_off),
            0.12,
            SCANNER_GATE_HEIGHT,
            0.12,
            SCANNER_FRAME_COLOR
        )

    # Top beam tying the posts together

    ray.draw_cube(
        ray.Vector3(
            gate_x,
            INFEED_Y + SCANNER_GATE_HEIGHT / 2.0,
            INFEED_Z
        ),
        0.16,
        0.16,
        SCANNER_GATE_WIDTH + 0.12,
        SCANNER_FRAME_COLOR
    )

    scanning_box = simulation.get_scanning_box()

    if scanning_box is not None:

        # A crate is in the gate right now: the laser sweeps
        # from bottom to top in step with its scan timer.

        progress = min(1.0, scanning_box.scan_timer / SCAN_DURATION)

        laser_y = (
            INFEED_Y
            - SCANNER_GATE_HEIGHT / 2.0
            + progress * SCANNER_GATE_HEIGHT
        )

        laser_color = SCANNER_LASER_COLOR

    else:

        # Nothing to scan right now - keep a faint idle sweep
        # going so the gate still reads as powered-on tech.

        idle_phase = (simulation.elapsed_time * 0.6) % 1.0

        laser_y = (
            INFEED_Y
            - SCANNER_GATE_HEIGHT / 2.0
            + idle_phase * SCANNER_GATE_HEIGHT
        )

        laser_color = SCANNER_LASER_IDLE_COLOR

    ray.draw_cube(
        ray.Vector3(gate_x, laser_y, INFEED_Z),
        0.03,
        0.03,
        SCANNER_GATE_WIDTH,
        laser_color
    )

    # Small readout panel bolted above the gate: scrolling
    # barcode-style bars while a crate is being checked, with a
    # green confirmation strip right before the check clears.

    panel_x = gate_x
    panel_y = INFEED_Y + SCANNER_GATE_HEIGHT / 2.0 + 0.35
    panel_z = INFEED_Z - SCANNER_GATE_WIDTH / 2.0 - 0.02

    ray.draw_cube(
        ray.Vector3(panel_x, panel_y, panel_z),
        0.05,
        0.5,
        0.7,
        SCANNER_PANEL_COLOR
    )

    if scanning_box is not None:

        bar_count = 9
        bar_span = 0.6

        for i in range(bar_count):

            seed = (
                i * 12.9898
                + math.floor(simulation.elapsed_time * 12.0) * 78.233
            )

            bar_width = 0.02 + 0.03 * abs(math.sin(seed))

            bar_z = panel_z - bar_span / 2.0 + i * (bar_span / bar_count)

            ray.draw_cube(
                ray.Vector3(panel_x - 0.03, panel_y + 0.15, bar_z),
                0.02,
                0.32,
                bar_width,
                SCANNER_BARCODE_LIGHT if (i % 2 == 0) else SCANNER_BARCODE_DARK
            )

        if scanning_box.scan_timer / SCAN_DURATION > 0.85:

            ray.draw_cube(
                ray.Vector3(panel_x - 0.04, panel_y - 0.15, panel_z),
                0.02,
                0.14,
                0.5,
                SCANNER_OK_COLOR
            )


# ============================================================
# OUTFEED STATION (WALL OPENING + LANDING LEDGE)
# ============================================================

def draw_outfeed_station(simulation):

    opening_height = BOX_HEIGHT + 0.5
    opening_width = BOX_WIDTH + 0.5

    # Mirror image of the infeed hole, cut into the right side
    # wall, right where extracted crates leave the building.

    ray.draw_cube(
        ray.Vector3(
            HALL_HALF_WIDTH,
            OUTFEED_Y,
            OUTFEED_Z
        ),
        0.5,
        opening_height,
        opening_width,
        INFEED_HOLE_COLOR
    )

    ray.draw_cube_wires(
        ray.Vector3(
            HALL_HALF_WIDTH,
            OUTFEED_Y,
            OUTFEED_Z
        ),
        0.5,
        opening_height,
        opening_width,
        OUTFEED_FRAME_COLOR
    )

    # Landing platform the crate rides on from the extraction
    # robot's drop dock to the wall opening.

    draw_fork_rail_platform(
        OUTFEED_DOCK_X - 0.3,
        OUTFEED_WALL_X + 0.3,
        OUTFEED_Y - BOX_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02,
        OUTFEED_Z
    )
    ray.draw_cube(
        ray.Vector3(HALL_HALF_WIDTH, RESTOCK_RETURN_Y, RESTOCK_RETURN_Z),
        0.5,
        opening_height,
        opening_width,
        INFEED_HOLE_COLOR
    )
    ray.draw_cube_wires(
        ray.Vector3(HALL_HALF_WIDTH, RESTOCK_RETURN_Y, RESTOCK_RETURN_Z),
        0.5,
        opening_height,
        opening_width,
        OUTFEED_FRAME_COLOR
    )
    draw_fork_rail_platform(
        RESTOCK_RETURN_DOCK_X - 0.3,
        RESTOCK_RETURN_WALL_X + 0.3,
        RESTOCK_RETURN_Y - BOX_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02,
        RESTOCK_RETURN_Z
    )


def draw_fork_rail_platform(x_start, x_end, rail_y, z):

    for z_off in (-FORK_TINE_SPACING / 2.0, FORK_TINE_SPACING / 2.0):

        ray.draw_cylinder_ex(
            ray.Vector3(x_start, rail_y, z + z_off),
            ray.Vector3(x_end, rail_y, z + z_off),
            FORK_TINE_RADIUS + 0.02,
            FORK_TINE_RADIUS + 0.02,
            10,
            CONVEYOR_FRAME_COLOR
        )

    # End posts holding the rods up, for a "real stand" look

    for x_post in (x_start, x_end):

        ray.draw_cube(
            ray.Vector3(x_post, rail_y - 0.35, z),
            0.08,
            0.70,
            FORK_TINE_SPACING + 0.15,
            CONVEYOR_FRAME_COLOR
        )


def draw_release_platform(level_y, line_z):

    # The mirror-image mechanism on the outgoing side: the
    # loading robot sets a crate down here, onto the same
    # two-rod pattern, right before the belt takes over.

    mouth_x = CONVEYOR_X[0] - CONVEYOR_LENGTH / 2.0

    draw_fork_rail_platform(
        mouth_x - 0.9,
        mouth_x + 0.1,
        level_y + CONVEYOR_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02,
        line_z
    )


# ============================================================
# LOADING ROBOT
# ============================================================

def draw_robot(robot_y, robot_z):

    # Vertical fixed column

    ray.draw_cube(
        ray.Vector3(
            ROBOT_X,
            ROBOT_COLUMN_HEIGHT / 2.0 - 0.5,
            -12.0
        ),
        0.8,
        ROBOT_COLUMN_HEIGHT,
        0.8,
        ROBOT_COLOR
    )

    # Y/Z horizontal rail

    ray.draw_cube(
        ray.Vector3(
            ROBOT_X,
            robot_y,
            0.0
        ),
        0.65,
        0.65,
        ROBOT_RAIL_LENGTH,
        RAIL_COLOR
    )

    # Robot carriage

    ray.draw_cube(
        ray.Vector3(
            ROBOT_X,
            robot_y,
            robot_z
        ),
        ROBOT_HEAD_SIZE,
        ROBOT_HEAD_SIZE,
        ROBOT_HEAD_SIZE,
        ROBOT_COLOR
    )

    # Forklift-style fork: two horizontal metal rods sticking
    # out under the carriage, spaced apart to slide onto the
    # same two-rod platforms used at the infeed dock and at
    # each conveyor mouth.

    box_rest_y = robot_y - GRIPPER_DROP
    tine_y = box_rest_y - BOX_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02

    for z_off in (-FORK_TINE_SPACING / 2.0, FORK_TINE_SPACING / 2.0):

        ray.draw_cylinder_ex(
            ray.Vector3(
                ROBOT_X - FORK_TINE_LENGTH / 2.0,
                tine_y,
                robot_z + z_off
            ),
            ray.Vector3(
                ROBOT_X + FORK_TINE_LENGTH / 2.0,
                tine_y,
                robot_z + z_off
            ),
            FORK_TINE_RADIUS,
            FORK_TINE_RADIUS,
            10,
            FORK_TINE_COLOR
        )

    # Backing plate connecting the fork to the carriage

    ray.draw_cube(
        ray.Vector3(
            ROBOT_X,
            (robot_y + tine_y) / 2.0,
            robot_z
        ),
        0.12,
        robot_y - tine_y,
        FORK_TINE_SPACING + 0.15,
        ROBOT_COLOR
    )


# ============================================================
# EXTRACTION ROBOT
#
# Same Y/Z carriage-on-a-rail design as the loading robot, just
# mirrored to the opposite end of the hall and parked in the
# opposite corner, so the two machines are never confused for
# one another even before you look at their (different) colors.
# ============================================================

def draw_extract_robot(robot_y, robot_z):

    # Vertical fixed column (opposite corner from the loading
    # robot's column)

    ray.draw_cube(
        ray.Vector3(
            EXTRACT_ROBOT_X,
            ROBOT_COLUMN_HEIGHT / 2.0 - 0.5,
            12.0
        ),
        0.8,
        ROBOT_COLUMN_HEIGHT,
        0.8,
        EXTRACT_ROBOT_COLOR
    )

    # Y/Z horizontal rail

    ray.draw_cube(
        ray.Vector3(
            EXTRACT_ROBOT_X,
            robot_y,
            0.0
        ),
        0.65,
        0.65,
        ROBOT_RAIL_LENGTH,
        RAIL_COLOR
    )

    # Robot carriage

    ray.draw_cube(
        ray.Vector3(
            EXTRACT_ROBOT_X,
            robot_y,
            robot_z
        ),
        ROBOT_HEAD_SIZE,
        ROBOT_HEAD_SIZE,
        ROBOT_HEAD_SIZE,
        EXTRACT_ROBOT_COLOR
    )

    # Fork

    box_rest_y = robot_y - GRIPPER_DROP
    tine_y = box_rest_y - BOX_HEIGHT / 2.0 - FORK_TINE_RADIUS - 0.02

    for z_off in (-FORK_TINE_SPACING / 2.0, FORK_TINE_SPACING / 2.0):

        ray.draw_cylinder_ex(
            ray.Vector3(
                EXTRACT_ROBOT_X - FORK_TINE_LENGTH / 2.0,
                tine_y,
                robot_z + z_off
            ),
            ray.Vector3(
                EXTRACT_ROBOT_X + FORK_TINE_LENGTH / 2.0,
                tine_y,
                robot_z + z_off
            ),
            FORK_TINE_RADIUS,
            FORK_TINE_RADIUS,
            10,
            EXTRACT_FORK_TINE_COLOR
        )

    # Backing plate connecting the fork to the carriage

    ray.draw_cube(
        ray.Vector3(
            EXTRACT_ROBOT_X,
            (robot_y + tine_y) / 2.0,
            robot_z
        ),
        0.12,
        robot_y - tine_y,
        FORK_TINE_SPACING + 0.15,
        EXTRACT_ROBOT_COLOR
    )


# ============================================================
# TARGET MARKERS
# ============================================================

def draw_target(level, line):

    # Where the loading robot is about to put a new box - drawn
    # as a hollow red wire box near the C1 mouth (near side).

    y = LEVEL_Y[level]
    z = LINE_Z[line]

    ray.draw_cube_wires(
        ray.Vector3(
            CONVEYOR_X[0],
            y + 1.0,
            z
        ),
        2.0,
        2.0,
        2.0,
        TARGET_COLOR
    )

    ray.draw_line_3d(
        ray.Vector3(
            CONVEYOR_X[0],
            y + 1.0,
            z - 1.5
        ),
        ray.Vector3(
            CONVEYOR_X[0],
            y + 1.0,
            z + 1.5
        ),
        TARGET_COLOR
    )


def draw_extract_target(level, line):

    # Where the extraction robot is about to pull a box from -
    # drawn as a hollow blue wire box near the C3 tip (far
    # side), same shape language as the loading target marker.

    y = LEVEL_Y[level]
    z = LINE_Z[line]

    ray.draw_cube_wires(
        ray.Vector3(
            CONVEYOR_X[2],
            y + 1.0,
            z
        ),
        2.0,
        2.0,
        2.0,
        EXTRACT_TARGET_COLOR
    )

    ray.draw_line_3d(
        ray.Vector3(
            CONVEYOR_X[2],
            y + 1.0,
            z - 1.5
        ),
        ray.Vector3(
            CONVEYOR_X[2],
            y + 1.0,
            z + 1.5
        ),
        EXTRACT_TARGET_COLOR
    )


# ============================================================
# HOME MARKERS
# ============================================================

def draw_home_marker():

    y = LEVEL_Y[HOME_LEVEL]
    z = LINE_Z[HOME_LINE]

    ray.draw_cube_wires(
        ray.Vector3(
            ROBOT_X,
            y,
            z
        ),
        1.8,
        1.8,
        1.8,
        HOME_COLOR
    )


def draw_extract_home_marker():

    y = LEVEL_Y[EXTRACT_HOME_LEVEL]
    z = LINE_Z[EXTRACT_HOME_LINE]

    ray.draw_cube_wires(
        ray.Vector3(
            EXTRACT_ROBOT_X,
            y,
            z
        ),
        1.8,
        1.8,
        1.8,
        EXTRACT_HOME_COLOR
    )


# ============================================================
# BOX (CRATE) DRAWING
# ============================================================

def draw_box(box):

    # Until a crate clears the scanner gate it rides through as
    # an anonymous grey tote ("checking the type"); once
    # `scanned` flips true its real crate-color is revealed for
    # the rest of its life in the warehouse.

    pending_scan = (not box.scanned) and box.state in (
        BoxState.SPAWNING,
        BoxState.SCANNING
    )

    if pending_scan:
        crate_color = SCAN_GREY_CRATE
    else:
        crate_color = CRATE_TYPES[box.crate_type % len(CRATE_TYPES)]

    half_length = BOX_LENGTH / 2.0
    half_width = BOX_WIDTH / 2.0
    wall = CRATE_WALL_THICKNESS

    # Base

    ray.draw_cube(
        ray.Vector3(
            box.x,
            box.y - BOX_HEIGHT / 2.0 + wall / 2.0,
            box.z
        ),
        BOX_LENGTH,
        wall,
        BOX_WIDTH,
        crate_color
    )

    # Side walls (long sides, running along X)

    for wall_z in (box.z - half_width + wall / 2.0, box.z + half_width - wall / 2.0):

        ray.draw_cube(
            ray.Vector3(box.x, box.y, wall_z),
            BOX_LENGTH,
            BOX_HEIGHT,
            wall,
            crate_color
        )

    # End walls (short sides, running along Z)

    for wall_x in (box.x - half_length + wall / 2.0, box.x + half_length - wall / 2.0):

        ray.draw_cube(
            ray.Vector3(wall_x, box.y, box.z),
            wall,
            BOX_HEIGHT,
            BOX_WIDTH,
            crate_color
        )

    # Small loose items visible over the open top. While a
    # crate hasn't cleared the scanner yet, its contents show
    # up as flat grey pieces too, as if only their silhouettes
    # are visible on the scan.

    for i, (dx, dy, dz, item_color) in enumerate(box.items):

        draw_color = item_color

        if pending_scan:
            draw_color = (
                SCAN_GREY_ITEM_LIGHT if i % 2 == 0 else SCAN_GREY_ITEM_DARK
            )

        ray.draw_cube(
            ray.Vector3(box.x + dx, box.y + dy, box.z + dz),
            0.16,
            0.16,
            0.16,
            draw_color
        )

    edge_color = (
        SCANNER_LASER_COLOR if box.state == BoxState.SCANNING
        else BOX_EDGE_COLOR
    )

    ray.draw_cube_wires(
        ray.Vector3(
            box.x,
            box.y,
            box.z
        ),
        BOX_LENGTH + 0.02,
        BOX_HEIGHT + 0.02,
        BOX_WIDTH + 0.02,
        edge_color
    )


# ============================================================
# WAREHOUSE SIMULATION
# ============================================================

class WarehouseSimulation:

    def __init__(self):

        # -------------------- loading robot -----------------

        self.robot_y = LEVEL_Y[HOME_LEVEL]
        self.robot_z = LINE_Z[HOME_LINE]

        self.target_level = 0
        self.target_line = 0

        self.state = RobotState.IDLE

        # ------------------ extraction robot -----------------

        self.extract_robot_y = LEVEL_Y[EXTRACT_HOME_LEVEL]
        self.extract_robot_z = LINE_Z[EXTRACT_HOME_LINE]

        self.extract_target_level = EXTRACT_HOME_LEVEL
        self.extract_target_line = EXTRACT_HOME_LINE

        self.extract_state = ExtractState.IDLE
        self.extract_restock = False
        self.bridge = None
        self.pending_place_box = None

        # ------------------------------------------------------

        self.boxes = []

        self.elapsed_time = 0.0

        self.last_response = "READY"

        # Number of boxes permanently stored at:
        #
        # storage[level][line]
        #
        self.storage = [
            [0 for _ in range(LINE_COUNT)]
            for _ in range(LEVEL_COUNT)
        ]

        # Next free queue slot per lane - slot 0 rests right at
        # the tip, slot 1 right behind it, and so on.
        self.lane_next_slot = [
            [0 for _ in range(LINE_COUNT)]
            for _ in range(LEVEL_COUNT)
        ]

        self.scene_root = SceneNode((0.0, 0.0, 0.0))
        self.boxes_root = SceneNode((0.0, 0.0, 0.0))
        self.scene_root.add_child(self.boxes_root)
        self.load_rail_node = SceneNode((ROBOT_X, self.robot_y, 0.0))
        self.load_carriage_node = SceneNode((0.0, 0.0, self.robot_z))
        self.scene_root.add_child(self.load_rail_node)
        self.load_rail_node.add_child(self.load_carriage_node)
        self.extract_rail_node = SceneNode((EXTRACT_ROBOT_X, self.extract_robot_y, 0.0))
        self.extract_carriage_node = SceneNode((0.0, 0.0, self.extract_robot_z))
        self.scene_root.add_child(self.extract_rail_node)
        self.extract_rail_node.add_child(self.extract_carriage_node)
        self.conveyor_nodes = []
        for cy in LEVEL_Y:
            for cz in LINE_Z:
                for cx in CONVEYOR_X:
                    n = SceneNode((cx, cy + CONVEYOR_Y_OFFSET, cz))
                    self.scene_root.add_child(n)
                    self.conveyor_nodes.append(n)
        self.load_target_node = SceneNode((CONVEYOR_X[0], LEVEL_Y[0], LINE_Z[0]))
        self.extract_target_node = SceneNode((CONVEYOR_X[2], LEVEL_Y[0], LINE_Z[0]))
        self.load_home_node = SceneNode((ROBOT_X, LEVEL_Y[HOME_LEVEL], LINE_Z[HOME_LINE]))
        self.extract_home_node = SceneNode((EXTRACT_ROBOT_X, LEVEL_Y[EXTRACT_HOME_LEVEL], LINE_Z[EXTRACT_HOME_LINE]))
        self.scanner_node = SceneNode((SCANNER_X, INFEED_Y, INFEED_Z))
        self.scene_root.add_child(self.load_target_node)
        self.scene_root.add_child(self.extract_target_node)
        self.scene_root.add_child(self.load_home_node)
        self.scene_root.add_child(self.extract_home_node)
        self.scene_root.add_child(self.scanner_node)
        self.box_nodes = {}

        # The very first box arrives the same way every later
        # box does: through the wall opening.

        self.spawn_box()
        self.sync_scene_graph()

    # --------------------------------------------------------
    # Spawn a new box at the wall opening
    # --------------------------------------------------------

    def spawn_box(self):
        crate_type = random.randrange(len(CRATE_TYPES))
        box = Box(
            x=INFEED_WALL_X,
            y=INFEED_Y,
            z=INFEED_Z,
            level=self.target_level,
            line=self.target_line,
            state=BoxState.SPAWNING,
            crate_type=crate_type,
            items=generate_crate_items(),
            sku=crate_type,
            quantity=SKU_TYPES.get(crate_type, 15)
        )
        self.boxes.append(box)

    def can_spawn_box(self):
        if self.pending_place_box is not None:
            return False
        return not any(
            box.state in (
                BoxState.SPAWNING,
                BoxState.SCANNING,
                BoxState.WAITING,
                BoxState.HELD
            )
            for box in self.boxes
        )

    def connect_bridge(self):
        if BridgeClient is None:
            return False
        if self.bridge is not None:
            return True
        try:
            self.bridge = BridgeClient(SIM_SOCKET_PATH)
            return True
        except Exception:
            self.bridge = None
            return False

    def send_bridge(self, msg):
        if self.bridge is None:
            return
        try:
            self.bridge.send_message(msg)
        except Exception:
            try:
                self.bridge.sock.close()
            except Exception:
                pass
            self.bridge = None

    def handle_place_at(self, x, y):
        if self.pending_place_box is None:
            for box in self.boxes:
                if box.state == BoxState.WAITING and box.scanned:
                    self.pending_place_box = box
                    break
        box = self.pending_place_box
        if box is None:
            return self._respond("ERR no pending box")
        if not (0 <= x < LEVEL_COUNT and 0 <= y < LINE_COUNT):
            return self._respond("ERR place out of range")
        if not self.lane_has_space(x, y):
            return self._respond("ERR lane full (10 max)")
        self.target_level = x
        self.target_line = y
        box.level = x
        box.line = y
        box.placed = True
        self._respond(f"OK PLACE L{x + 1} T{y + 1}")
        if self.state == RobotState.IDLE and self._robot_at_home() and self.get_held_box() is None:
            if box.state == BoxState.WAITING:
                box.state = BoxState.HELD
            if self.get_held_box() is not None:
                self._cmd_send()
                if self.state != RobotState.IDLE:
                    self.pending_place_box = None
        return self.last_response

    def handle_fetch_box(self, x, y, restock):
        if not (0 <= x < LEVEL_COUNT and 0 <= y < LINE_COUNT):
            return self._respond("ERR fetch out of range")
        if self.storage[x][y] <= 0:
            return self._respond("ERR nothing stored there")
        if self.extract_state != ExtractState.IDLE:
            return self._respond("ERR extractor busy")
        self.extract_target_level = x
        self.extract_target_line = y
        self.extract_restock = bool(restock)
        self.send_extract_robot()
        tag = "XRSEND" if restock else "XSEND"
        return self._respond(f"OK {tag} L{x + 1} T{y + 1}")

    def poll_bridge(self):
        if self.bridge is None:
            return
        try:
            msgs = self.bridge.poll_messages()
        except Exception:
            try:
                self.bridge.sock.close()
            except Exception:
                pass
            self.bridge = None
            return
        for msg in msgs:
            t = msg.get("type")
            if t == "PLACE_AT":
                try:
                    self.handle_place_at(int(msg["x"]), int(msg["y"]))
                except Exception:
                    pass
            elif t == "FETCH_BOX":
                try:
                    self.handle_fetch_box(int(msg["x"]), int(msg["y"]), bool(msg.get("restock", False)))
                except Exception:
                    pass

    def lane_occupancy(self, level, line):
        n = self.storage[level][line]
        for box in self.boxes:
            if box.level == level and box.line == line and box.state in (BoxState.ON_CONVEYOR, BoxState.SHIFTING):
                n += 1
        return n

    def lane_has_space(self, level, line):
        return self.lane_occupancy(level, line) < LANE_MAX_BOXES

    # --------------------------------------------------------
    # Find currently held / currently scanning box
    # --------------------------------------------------------

    def get_held_box(self):

        for box in self.boxes:

            if box.state == BoxState.HELD:
                return box

        return None

    def get_extract_held_box(self):

        for box in self.boxes:

            if box.state == BoxState.EXTRACT_HELD:
                return box

        return None

    def get_scanning_box(self):

        for box in self.boxes:

            if box.state == BoxState.SCANNING:
                return box

        return None

    def get_extractable_box(self, level, line):

        # The extraction robot always reaches for whichever
        # crate is physically closest to it - the one furthest
        # along the lane toward the tip (largest X). If several
        # crates share that same X (stacked in different
        # layers, since a layer only starts once the one below
        # it is completely full), the topmost one is taken -
        # you have to lift the crate on top before you can ever
        # reach the one underneath it.

        candidates = [
            box for box in self.boxes
            if box.state == BoxState.STORED
            and box.level == level
            and box.line == line
        ]

        if not candidates:
            return None

        return max(candidates, key=lambda box: (box.x, box.stored_layer))

    def sync_scene_graph(self):
        self.load_rail_node.set_position(ROBOT_X, self.robot_y, 0.0)
        self.load_carriage_node.set_position(0.0, 0.0, self.robot_z)
        self.extract_rail_node.set_position(EXTRACT_ROBOT_X, self.extract_robot_y, 0.0)
        self.extract_carriage_node.set_position(0.0, 0.0, self.extract_robot_z)
        self.load_target_node.set_position(CONVEYOR_X[0], LEVEL_Y[self.target_level], LINE_Z[self.target_line])
        self.extract_target_node.set_position(CONVEYOR_X[2], LEVEL_Y[self.extract_target_level], LINE_Z[self.extract_target_line])
        live = set()
        for box in self.boxes:
            bid = id(box)
            live.add(bid)
            node = self.box_nodes.get(bid)
            if node is None:
                node = SceneNode((box.x, box.y, box.z))
                self.box_nodes[bid] = node
            if box.state == BoxState.HELD:
                if node.parent is not self.load_carriage_node:
                    self.load_carriage_node.add_child(node)
                node.set_position(0.0, -GRIPPER_DROP, 0.0)
            elif box.state == BoxState.EXTRACT_HELD:
                if node.parent is not self.extract_carriage_node:
                    self.extract_carriage_node.add_child(node)
                node.set_position(0.0, -GRIPPER_DROP, 0.0)
            else:
                if node.parent is not self.boxes_root:
                    self.boxes_root.add_child(node)
                node.set_position(box.x, box.y, box.z)
        for bid in list(self.box_nodes.keys()):
            if bid not in live:
                node = self.box_nodes.pop(bid)
                if node.parent is not None:
                    node.parent.remove_child(node)
        self.scene_root.update_transform()
        for box in self.boxes:
            if box.state == BoxState.HELD or box.state == BoxState.EXTRACT_HELD:
                node = self.box_nodes.get(id(box))
                if node is not None:
                    wp = node.get_world_position()
                    box.x = wp.x
                    box.y = wp.y
                    box.z = wp.z

    def get_box_world_position(self, box):
        node = self.box_nodes.get(id(box))
        if node is None:
            return ray.Vector3(box.x, box.y, box.z)
        return node.get_world_position()

    def get_load_carriage_world(self):
        return self.load_carriage_node.get_world_position()

    def get_extract_carriage_world(self):
        return self.extract_carriage_node.get_world_position()

    # --------------------------------------------------------
    # Close the gap left behind by an extracted crate: every
    # crate still queued further back in the same lane rolls
    # forward one slot (which may also mean dropping down one
    # layer, if that slot boundary was crossed).
    # --------------------------------------------------------

    def shift_lane_forward(self, level, line, removed_slot):

        for box in self.boxes:

            if box.state != BoxState.STORED:
                continue

            if box.level != level or box.line != line:
                continue

            if box.lane_slot <= removed_slot:
                continue

            box.lane_slot -= 1

            layer = box.lane_slot // LANE_CAPACITY_PER_LAYER

            box.stored_layer = layer

            box.y = (
                LEVEL_Y[level]
                + CONVEYOR_HEIGHT / 2.0
                + BOX_HEIGHT / 2.0
                + layer * (BOX_HEIGHT + STORAGE_Y_GAP)
            )

            # Hand it off to the per-frame shift updater, which
            # rolls it forward in X toward its new slot's spot.

            box.state = BoxState.SHIFTING

    # --------------------------------------------------------
    # Animate crates that are rolling forward to close a gap
    # --------------------------------------------------------

    def update_shifting_boxes(self, dt):

        for box in self.boxes:

            if box.state != BoxState.SHIFTING:
                continue

            position_in_layer = box.lane_slot % LANE_CAPACITY_PER_LAYER

            target_x = LANE_TIP_X - position_in_layer * LANE_SLOT_PITCH

            box.x += BOX_SPEED * dt

            if box.x >= target_x:

                box.x = target_x
                box.state = BoxState.STORED

    def get_infeed_status(self):

        for box in self.boxes:

            if box.state == BoxState.SCANNING:
                return "SCANNING"

            if box.state == BoxState.SPAWNING:
                return "SPAWNING"

            if box.state == BoxState.WAITING:
                return "WAITING"

        if self.get_held_box() is not None:
            return "HELD"

        return "READY"

    def _robot_at_home(self):

        return (
            abs(self.robot_y - LEVEL_Y[HOME_LEVEL]) < 0.01
            and abs(self.robot_z - LINE_Z[HOME_LINE]) < 0.01
        )

    # --------------------------------------------------------
    # Select level / line - LOADING ROBOT (low level, internal)
    # --------------------------------------------------------

    def select_level(self, level):

        if self.state != RobotState.IDLE:
            return

        if 0 <= level < LEVEL_COUNT:

            self.target_level = level

    def select_line(self, line):

        if self.state != RobotState.IDLE:
            return

        if 0 <= line < LINE_COUNT:

            self.target_line = line

    # --------------------------------------------------------
    # Select level / line - EXTRACTION ROBOT (low level, internal)
    # --------------------------------------------------------

    def select_extract_level(self, level):

        if self.extract_state != ExtractState.IDLE:
            return

        if 0 <= level < LEVEL_COUNT:

            self.extract_target_level = level

    def select_extract_line(self, line):

        if self.extract_state != ExtractState.IDLE:
            return

        if 0 <= line < LINE_COUNT:

            self.extract_target_line = line

    # --------------------------------------------------------
    # Start movement (low level, used internally)
    # --------------------------------------------------------

    def send_robot(self):

        if self.state != RobotState.IDLE:
            return

        box = self.get_held_box()

        if box is None:
            return

        if not self.lane_has_space(self.target_level, self.target_line):
            self._respond("ERR lane full (10 max)")
            return

        box.level = self.target_level
        box.line = self.target_line

        self.state = RobotState.MOVING_TO_TARGET_Y

    def send_extract_robot(self):

        if self.extract_state != ExtractState.IDLE:
            return

        if self.storage[self.extract_target_level][self.extract_target_line] <= 0:
            return

        self.extract_state = ExtractState.MOVING_TO_SOURCE_Y

    # ========================================================
    # COMMAND INTERFACE
    #
    # Closed loop: the only physical input is feeding via
    # "NEWBOX" / "N". Placement and extraction are driven by
    # bridge events (PLACE_AT / FETCH_BOX), never by hand.
    #
    #   "NEWBOX" / "N"         request a new box from the infeed
    #   "STATUS" / "S"         report current state of both robots
    # ========================================================

    def handle_command(self, command):

        if command is None:
            return self._respond("ERR empty command")

        cmd = command.strip().upper()

        if cmd == "":
            return self._respond("ERR empty command")

        if cmd in ("NEWBOX", "NEW", "N"):
            return self._cmd_new_box()
        if cmd in ("STATUS", "S"):
            return self._cmd_status()
        return self._respond(f"ERR unknown command '{command}'")

    def _respond(self, message):

        self.last_response = message
        return message

    def _cmd_select_level(self, n):

        if self.state != RobotState.IDLE:
            return self._respond("ERR robot busy")

        if not (1 <= n <= LEVEL_COUNT):
            return self._respond(
                f"ERR level out of range (1-{LEVEL_COUNT})"
            )

        self.select_level(n - 1)
        return self._respond(f"OK LEVEL {n}")

    def _cmd_select_line(self, n):

        if self.state != RobotState.IDLE:
            return self._respond("ERR robot busy")

        if not (1 <= n <= LINE_COUNT):
            return self._respond(
                f"ERR line out of range (1-{LINE_COUNT})"
            )

        self.select_line(n - 1)
        return self._respond(f"OK LINE {n}")

    def _cmd_select_extract_level(self, n):

        if self.extract_state != ExtractState.IDLE:
            return self._respond("ERR extractor busy")

        if not (1 <= n <= LEVEL_COUNT):
            return self._respond(
                f"ERR extract level out of range (1-{LEVEL_COUNT})"
            )

        self.select_extract_level(n - 1)
        return self._respond(f"OK XLEVEL {n}")

    def _cmd_select_extract_line(self, n):

        if self.extract_state != ExtractState.IDLE:
            return self._respond("ERR extractor busy")

        if not (1 <= n <= LINE_COUNT):
            return self._respond(
                f"ERR extract line out of range (1-{LINE_COUNT})"
            )

        self.select_extract_line(n - 1)
        return self._respond(f"OK XLINE {n}")

    def _cmd_send(self):

        if self.state != RobotState.IDLE:
            return self._respond("ERR robot busy")

        if self.get_held_box() is None:
            return self._respond("ERR no box held")

        if not self.lane_has_space(self.target_level, self.target_line):
            return self._respond("ERR lane full (10 max)")

        self.send_robot()
        return self._respond(
            f"OK SEND L{self.target_level + 1} T{self.target_line + 1}"
        )

    def _cmd_extract_send(self, restock=False):
        if self.extract_state != ExtractState.IDLE:
            return self._respond("ERR extractor busy")
        if self.storage[self.extract_target_level][self.extract_target_line] <= 0:
            return self._respond("ERR nothing stored there")
        self.extract_restock = restock
        self.send_extract_robot()
        tag = "XRSEND" if restock else "XSEND"
        return self._respond(f"OK {tag} L{self.extract_target_level + 1} T{self.extract_target_line + 1}")

    def _cmd_new_box(self):

        if not self.can_spawn_box():
            return self._respond("ERR box already pending")

        self.spawn_box()
        return self._respond("OK NEWBOX")

    def _cmd_status(self):

        return self._respond(
            f"LOAD={self.state.name} "
            f"TARGET=L{self.target_level + 1}T{self.target_line + 1} "
            f"INFEED={self.get_infeed_status()} | "
            f"EXTRACT={self.extract_state.name} "
            f"XTARGET=L{self.extract_target_level + 1}"
            f"T{self.extract_target_line + 1}"
        )

    # --------------------------------------------------------
    # Move toward target
    # --------------------------------------------------------

    def move_value(self, current, target, speed, dt):

        difference = target - current

        maximum_step = speed * dt

        if abs(difference) <= maximum_step:

            return target, True

        if difference > 0:

            return current + maximum_step, False

        return current - maximum_step, False

    # --------------------------------------------------------
    # Update loading robot
    # --------------------------------------------------------

    def update_robot(self, dt):

        # ----------------------------------------------------
        # Move Y
        # ----------------------------------------------------

        if self.state == RobotState.MOVING_TO_TARGET_Y:

            self.robot_y, reached = self.move_value(
                self.robot_y,
                LEVEL_Y[self.target_level],
                ROBOT_SPEED_Y,
                dt
            )

            if reached:

                self.state = RobotState.MOVING_TO_TARGET_Z

        # ----------------------------------------------------
        # Move Z
        # ----------------------------------------------------

        elif self.state == RobotState.MOVING_TO_TARGET_Z:

            self.robot_z, reached = self.move_value(
                self.robot_z,
                LINE_Z[self.target_line],
                ROBOT_SPEED_Z,
                dt
            )

            if reached:

                self.state = RobotState.RELEASING

        # ----------------------------------------------------
        # Release box
        # ----------------------------------------------------

        elif self.state == RobotState.RELEASING:

            box = self.get_held_box()

            if box is not None:
                if not self.lane_has_space(self.target_level, self.target_line):
                    self._respond("ERR lane full (10 max)")
                else:
                    box.state = BoxState.ON_CONVEYOR
                    box.level = self.target_level
                    box.line = self.target_line
                    box.lane_slot = self.lane_next_slot[self.target_level][self.target_line]
                    self.lane_next_slot[self.target_level][self.target_line] += 1
                    box.x = LANE_START_X
                    box.y = (LEVEL_Y[self.target_level] + CONVEYOR_HEIGHT / 2.0 + BOX_HEIGHT / 2.0)
                    box.z = LINE_Z[self.target_line]

            self.state = RobotState.RETURNING_HOME_Y

        # ----------------------------------------------------
        # Return Y
        # ----------------------------------------------------

        elif self.state == RobotState.RETURNING_HOME_Y:

            self.robot_y, reached = self.move_value(
                self.robot_y,
                LEVEL_Y[HOME_LEVEL],
                ROBOT_SPEED_Y,
                dt
            )

            if reached:

                self.state = RobotState.RETURNING_HOME_Z

        # ----------------------------------------------------
        # Return Z
        # ----------------------------------------------------

        elif self.state == RobotState.RETURNING_HOME_Z:

            self.robot_z, reached = self.move_value(
                self.robot_z,
                LINE_Z[HOME_LINE],
                ROBOT_SPEED_Z,
                dt
            )

            if reached:
                self.state = RobotState.IDLE
        if self.state == RobotState.IDLE and self.pending_place_box is not None:
            box = self.pending_place_box
            if box.placed and box.state == BoxState.WAITING and self._robot_at_home() and self.get_held_box() is None:
                box.state = BoxState.HELD
                self._cmd_send()
                if self.state != RobotState.IDLE:
                    self.pending_place_box = None

    # --------------------------------------------------------
    # Update extraction robot
    # --------------------------------------------------------

    def update_extract_robot(self, dt):

        # ----------------------------------------------------
        # Move to source Y
        # ----------------------------------------------------

        if self.extract_state == ExtractState.MOVING_TO_SOURCE_Y:

            self.extract_robot_y, reached = self.move_value(
                self.extract_robot_y,
                LEVEL_Y[self.extract_target_level],
                ROBOT_SPEED_Y,
                dt
            )

            if reached:

                self.extract_state = ExtractState.MOVING_TO_SOURCE_Z

        # ----------------------------------------------------
        # Move to source Z
        # ----------------------------------------------------

        elif self.extract_state == ExtractState.MOVING_TO_SOURCE_Z:

            self.extract_robot_z, reached = self.move_value(
                self.extract_robot_z,
                LINE_Z[self.extract_target_line],
                ROBOT_SPEED_Z,
                dt
            )

            if reached:

                self.extract_state = ExtractState.PICKING

        # ----------------------------------------------------
        # Pick the box up off the storage lane
        # ----------------------------------------------------

        elif self.extract_state == ExtractState.PICKING:

            box = self.get_extractable_box(
                self.extract_target_level,
                self.extract_target_line
            )

            if box is not None:
                removed_slot = box.lane_slot
                self.storage[self.extract_target_level][self.extract_target_line] -= 1
                box.restock = self.extract_restock
                box.origin_level = self.extract_target_level
                box.origin_line = self.extract_target_line
                box.origin_slot = removed_slot
                box.origin_layer = box.stored_layer
                if self.extract_restock:
                    box.state = BoxState.EXTRACT_HELD
                else:
                    self.lane_next_slot[self.extract_target_level][self.extract_target_line] -= 1
                    box.state = BoxState.EXTRACT_HELD
                    self.shift_lane_forward(self.extract_target_level, self.extract_target_line, removed_slot)

            # Head back to the fixed drop dock regardless -
            # if the lane emptied out in the meantime the fork
            # just returns empty.

            self.extract_state = ExtractState.RETURNING_TO_DROP_Y

        # ----------------------------------------------------
        # Return to drop dock Y
        # ----------------------------------------------------

        elif self.extract_state == ExtractState.RETURNING_TO_DROP_Y:

            self.extract_robot_y, reached = self.move_value(
                self.extract_robot_y,
                LEVEL_Y[EXTRACT_HOME_LEVEL],
                ROBOT_SPEED_Y,
                dt
            )

            if reached:

                self.extract_state = ExtractState.RETURNING_TO_DROP_Z

        # ----------------------------------------------------
        # Return to drop dock Z
        # ----------------------------------------------------

        elif self.extract_state == ExtractState.RETURNING_TO_DROP_Z:

            self.extract_robot_z, reached = self.move_value(
                self.extract_robot_z,
                LINE_Z[EXTRACT_HOME_LINE],
                ROBOT_SPEED_Z,
                dt
            )

            if reached:

                self.extract_state = ExtractState.RELEASING

        # ----------------------------------------------------
        # Drop the box at the outfeed dock
        # ----------------------------------------------------

        elif self.extract_state == ExtractState.RELEASING:
            box = self.get_extract_held_box()
            if box is not None:
                if box.restock:
                    box.state = BoxState.RESTOCK_OUT
                else:
                    box.state = BoxState.EXITING
                box.x = OUTFEED_DOCK_X
                box.y = OUTFEED_Y
                box.z = OUTFEED_Z
            self.extract_state = ExtractState.IDLE

    # --------------------------------------------------------
    # Infeed: boxes sliding from the wall opening, through the
    # scanner gate, to the dock
    # --------------------------------------------------------

    def update_infeed_boxes(self, dt):

        for box in self.boxes:

            if box.state == BoxState.SPAWNING:

                box.x += INFEED_SPEED * dt

                if not box.scanned and box.x >= SCANNER_X:

                    # Pause right in the gate for the scan.

                    box.x = SCANNER_X
                    box.state = BoxState.SCANNING
                    box.scan_timer = 0.0

                elif box.scanned and box.x >= INFEED_DOCK_X:

                    box.x = INFEED_DOCK_X
                    box.state = BoxState.WAITING

            elif box.state == BoxState.SCANNING:
                box.scan_timer += dt
                if box.scan_timer >= SCAN_DURATION:
                    box.scanned = True
                    box.state = BoxState.SPAWNING
                    if self.pending_place_box is None:
                        self.pending_place_box = box
                    self.send_bridge({"type": "BOX_SCANNED", "sku": box.sku, "quantity": box.quantity})

    def try_pickup_waiting_box(self):
        return

    # --------------------------------------------------------
    # Outfeed: boxes sliding from the extraction robot's drop
    # dock out through the wall opening, then leaving the sim
    # --------------------------------------------------------

    def update_exiting_boxes(self, dt):
        remaining = []
        for box in self.boxes:
            if box.state == BoxState.EXITING:
                box.x += OUTFEED_SPEED * dt
                if box.x >= OUTFEED_WALL_X:
                    if self.pending_place_box is box:
                        self.pending_place_box = None
                    self.send_bridge({"type": "FETCH_DONE"})
                    self._respond("OK FETCH_DONE")
                    continue
            elif box.state == BoxState.RESTOCK_OUT:
                box.x += OUTFEED_SPEED * dt
                if box.x >= OUTFEED_WALL_X:
                    box.state = BoxState.RESTOCK_IN
                    box.x = RESTOCK_RETURN_WALL_X
                    box.y = RESTOCK_RETURN_Y
                    box.z = RESTOCK_RETURN_Z
            elif box.state == BoxState.RESTOCK_IN:
                box.x -= RESTOCK_SPEED * dt
                if box.x <= RESTOCK_RETURN_DOCK_X:
                    lvl = box.origin_level
                    ln = box.origin_line
                    box.level = lvl
                    box.line = ln
                    box.lane_slot = box.origin_slot
                    box.stored_layer = box.origin_layer
                    box.x = LANE_TIP_X - (box.origin_slot % LANE_CAPACITY_PER_LAYER) * LANE_SLOT_PITCH
                    box.y = LEVEL_Y[lvl] + CONVEYOR_HEIGHT / 2.0 + BOX_HEIGHT / 2.0 + box.origin_layer * (BOX_HEIGHT + STORAGE_Y_GAP)
                    box.z = LINE_Z[ln]
                    box.state = BoxState.STORED
                    box.restock = False
                    self.storage[lvl][ln] += 1
                    self.send_bridge({"type": "FETCH_DONE"})
                    self._respond("OK FETCH_DONE")
            remaining.append(box)
        self.boxes = remaining

    # --------------------------------------------------------
    # Update boxes travelling along the conveyors
    # --------------------------------------------------------

    def update_boxes(self, dt):

        # Boxes ride the belt in a single straight line from
        # the mouth of C1 to the tip of C3 (the small gaps
        # between the three conveyor sections are cosmetic
        # only). Each box is only allowed to travel as far as
        # its assigned queue slot - so it moves forward until
        # it reaches either the tip of the lane, or the back of
        # the crate queued in front of it.

        for box in self.boxes:

            if box.state != BoxState.ON_CONVEYOR:
                continue

            layer = box.lane_slot // LANE_CAPACITY_PER_LAYER
            position_in_layer = box.lane_slot % LANE_CAPACITY_PER_LAYER

            target_x = LANE_TIP_X - position_in_layer * LANE_SLOT_PITCH

            box.x += BOX_SPEED * dt

            if box.x >= target_x:

                box.x = target_x
                self.settle_box(box, layer)

    # --------------------------------------------------------
    # Settle a box that has reached its resting spot in the
    # lane queue. Once a layer's worth of lane length is full,
    # later crates simply settle one layer higher, still at the
    # same queued X position.
    # --------------------------------------------------------

    def settle_box(self, box, layer):

        level = box.level
        line = box.line

        self.storage[level][line] += 1

        box.state = BoxState.STORED
        box.stored_layer = layer

        box.y = (
            LEVEL_Y[level]
            + CONVEYOR_HEIGHT / 2.0
            + BOX_HEIGHT / 2.0
            + layer * (BOX_HEIGHT + STORAGE_Y_GAP)
        )

        box.z = LINE_Z[line]

    # --------------------------------------------------------
    # Update held boxes
    # --------------------------------------------------------

    def update_held_box(self):
        return

    def update_extract_held_box(self):
        return

    def update(self, dt):
        self.elapsed_time += dt
        self.poll_bridge()
        self.update_robot(dt)
        self.update_infeed_boxes(dt)
        self.update_held_box()
        self.update_boxes(dt)
        self.update_shifting_boxes(dt)
        self.update_extract_robot(dt)
        self.update_extract_held_box()
        self.update_exiting_boxes(dt)
        self.sync_scene_graph()

    def draw_boxes(self):
        for box in self.boxes:
            wp = self.get_box_world_position(box)
            ox = box.x
            oy = box.y
            oz = box.z
            box.x = wp.x
            box.y = wp.y
            box.z = wp.z
            draw_box(box)
            box.x = ox
            box.y = oy
            box.z = oz


# ============================================================
# UI
# ============================================================

def draw_ui(simulation):

    # -------------------- LOADING ROBOT panel ----------------

    ray.draw_rectangle(
        15,
        15,
        365,
        265,
        ray.Color(245, 245, 245, 235)
    )

    ray.draw_rectangle_lines(
        15,
        15,
        365,
        265,
        ray.Color(70, 70, 70, 255)
    )

    ray.draw_text(
        "LOADING ROBOT (AUTO)",
        30,
        30,
        24,
        TEXT_COLOR
    )

    ray.draw_text(
        "PLACE_AT",
        30,
        70,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "STM decides lane",
        140,
        70,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "SEND",
        30,
        100,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "auto on PLACE_AT",
        140,
        100,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "N",
        30,
        130,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "Feed box (manual)",
        140,
        130,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "R",
        30,
        160,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "Reset camera",
        140,
        160,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "C",
        30,
        190,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "unused",
        140,
        190,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "Mouse",
        30,
        220,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "L: rotate   M: pan   Wheel: zoom",
        140,
        220,
        15,
        TEXT_COLOR
    )

    ray.draw_text(
        f"CMD: {simulation.last_response}",
        30,
        250,
        16,
        TEXT_COLOR
    )

    # -------------------- EXTRACTION ROBOT panel --------------

    panel_x = 15
    panel_y = 295

    ray.draw_rectangle(
        panel_x,
        panel_y,
        365,
        200,
        ray.Color(232, 238, 248, 235)
    )

    ray.draw_rectangle_lines(
        panel_x,
        panel_y,
        365,
        200,
        ray.Color(50, 80, 120, 255)
    )

    ray.draw_text(
        "EXTRACTION ROBOT (AUTO)",
        panel_x + 15,
        panel_y + 15,
        24,
        TEXT_COLOR
    )

    ray.draw_text(
        "FETCH_BOX",
        panel_x + 15,
        panel_y + 55,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "STM decides lane",
        panel_x + 125,
        panel_y + 55,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "RESTOCK",
        panel_x + 15,
        panel_y + 85,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "STM flag, auto loop",
        panel_x + 125,
        panel_y + 85,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "DELETE",
        panel_x + 15,
        panel_y + 115,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        "exit box removed",
        panel_x + 125,
        panel_y + 115,
        18,
        TEXT_COLOR
    )

    ray.draw_text(
        f"XTARGET: L{simulation.extract_target_level + 1} "
        f"T{simulation.extract_target_line + 1}",
        panel_x + 15,
        panel_y + 150,
        16,
        TEXT_COLOR
    )

    ray.draw_text(
        f"XSTATE: {simulation.extract_state.name}",
        panel_x + 15,
        panel_y + 172,
        16,
        TEXT_COLOR
    )

    # --------------------------------------------------------
    # Current destination / status strip along the bottom
    # --------------------------------------------------------

    ray.draw_text(
        f"LOAD TARGET: Level {simulation.target_level + 1}, "
        f"Line {simulation.target_line + 1}",
        20,
        SCREEN_HEIGHT - 65,
        22,
        TEXT_COLOR
    )

    ray.draw_text(
        f"LOAD ROBOT: {simulation.state.name}   "
        f"INFEED: {simulation.get_infeed_status()}   |   "
        f"EXTRACT ROBOT: {simulation.extract_state.name}",
        20,
        SCREEN_HEIGHT - 35,
        20,
        TEXT_COLOR
    )


# ============================================================
# STACK INFORMATION
# ============================================================

def draw_storage_info(simulation):

    x = SCREEN_WIDTH - 310
    y = 20

    ray.draw_rectangle(
        x - 10,
        y - 10,
        290,
        160,
        ray.Color(245, 245, 245, 235)
    )

    ray.draw_rectangle_lines(
        x - 10,
        y - 10,
        290,
        160,
        ray.Color(70, 70, 70, 255)
    )

    ray.draw_text(
        "STORAGE",
        x,
        y,
        22,
        TEXT_COLOR
    )

    y += 30

    for level in range(LEVEL_COUNT):

        for line in range(LINE_COUNT):

            count = simulation.storage[level][line]

            if count > 0:

                text = (
                    f"L{level + 1} / Line {line + 1}: "
                    f"{count} box"
                )

                if count != 1:
                    text += "es"

                ray.draw_text(
                    text,
                    x,
                    y,
                    16,
                    TEXT_COLOR
                )

                y += 20

                if y > 155:
                    return


# ============================================================
# MAIN
# ============================================================

def main():

    ray.init_window(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        WINDOW_TITLE
    )

    ray.set_target_fps(60)

    camera_controller = WarehouseCamera()
    simulation = WarehouseSimulation()
    simulation.connect_bridge()

    # --------------------------------------------------------
    # Optional: ESP32 / serial command source (disabled here).
    #
    # Every keyboard key below just calls
    # simulation.handle_command("..."). To drive either robot
    # from an ESP32 instead, have it send one command per line
    # over UART (115200 baud, newline terminated), e.g.:
    #
    #   L2\n        (loading robot: select level 2)
    #   T3\n        (loading robot: select line 3)
    #   G\n         (loading robot: send)
    #   N\n         (request a new box)
    #   XL1\n       (extraction robot: select level 1)
    #   XT4\n       (extraction robot: select line 4)
    #   XG\n        (extraction robot: send)
    #
    # Then, with pyserial installed, poll it once per frame:
    #
    #   import serial
    #   esp32 = serial.Serial('/dev/ttyUSB0', 115200, timeout=0)
    #
    #   def poll_serial_commands(simulation):
    #       while esp32.in_waiting:
    #           line = esp32.readline().decode(
    #               'utf-8', errors='ignore'
    #           ).strip()
    #           if line:
    #               simulation.handle_command(line)
    #
    # and call poll_serial_commands(simulation) inside the
    # main loop below, right next to the keyboard handling.
    # No other code needs to change - all three input sources
    # (loading robot keys, extraction robot keys, and a future
    # ESP32) speak the exact same command language.
    # --------------------------------------------------------

    while not ray.window_should_close():

        dt = ray.get_frame_time()

        if ray.is_key_pressed(ray.KEY_N):
            simulation.handle_command("NEWBOX")

        # ----------------------------------------------------
        # Camera (note: camera reset used to be "C" - it has
        # moved to KEY_R since C now selects extraction line 3)
        # ----------------------------------------------------

        if ray.is_key_pressed(ray.KEY_R):
            camera_controller.reset()

        camera_controller.update()

        # ----------------------------------------------------
        # Simulation
        # ----------------------------------------------------

        simulation.update(dt)

        # ----------------------------------------------------
        # Rendering
        # ----------------------------------------------------

        belt_offset = simulation.elapsed_time * BELT_SCROLL_SPEED

        ray.begin_drawing()

        ray.clear_background(BACKGROUND)

        ray.begin_mode_3d(camera_controller.camera)

        draw_warehouse(belt_offset, simulation)

        draw_target(
            simulation.target_level,
            simulation.target_line
        )

        draw_extract_target(
            simulation.extract_target_level,
            simulation.extract_target_line
        )

        draw_home_marker()

        draw_extract_home_marker()

        load_wp = simulation.get_load_carriage_world()
        extract_wp = simulation.get_extract_carriage_world()
        draw_robot(load_wp.y, load_wp.z)
        draw_extract_robot(extract_wp.y, extract_wp.z)

        simulation.draw_boxes()

        # World axes

        ray.draw_line_3d(
            ray.Vector3(-14, 0, -13),
            ray.Vector3(-8, 0, -13),
            ray.RED
        )

        ray.draw_line_3d(
            ray.Vector3(-14, 0, -13),
            ray.Vector3(-14, 6, -13),
            ray.GREEN
        )

        ray.draw_line_3d(
            ray.Vector3(-14, 0, -13),
            ray.Vector3(-14, 0, -7),
            ray.BLUE
        )

        ray.end_mode_3d()

        draw_ui(simulation)

        draw_storage_info(simulation)

        ray.end_drawing()

    ray.close_window()


if __name__ == "__main__":
    main()