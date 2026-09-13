import json
import time
import random
import sys
import select
from collections import defaultdict
from bridge_client import BridgeClient

SIM_SOCKET_PATH = "/tmp/warehouse_sim.sock"
GRID_W = 3
GRID_H = 4
LANE_DEPTH = 10

# SKU types: sku_id -> capacity (pieces per box)
SKU_TYPES = {
    0: 15,   # Type 0: 15 pieces per box
    1: 25,   # Type 1: 25 pieces per box
    2: 40,   # Type 2: 40 pieces per box
    3: 30,   # Type 3: 30 pieces per box
}

class MockSim:
    """
    Mock SIM with autonomous box queuing.
    - 26×15 grid of lanes, each is a FIFO queue (up to 10 boxes per lane)
    - Spawns new boxes periodically (not as fast as possible)
    - Auto-advances boxes through lanes when possible
    - Receives PLACE_AT: push box to lane
    - Receives FETCH_BOX: pop from front, maybe restock
    - Sends: BOX_SCANNED, FETCH_DONE
    """

    def __init__(self):
        self.bridge = BridgeClient(SIM_SOCKET_PATH)
        self.pending_box = None
        self.lanes = defaultdict(list)
        self.running = True
        self.box_id = 0
        self.last_advance = time.time()
        self.advance_interval = 0.5

    def spawn_box(self, sku: int, quantity: int):
        """Simulate a new box entering the scanner."""
        self.box_id += 1
        print(f"[SIM] Spawning box #{self.box_id}: SKU={sku}, qty={quantity}")
        self.bridge.send_message({
            "type": "BOX_SCANNED",
            "sku": sku,
            "quantity": quantity
        })
        self.pending_box = {"id": self.box_id, "sku": sku, "qty": quantity}

    def handle_place_at(self, x: int, y: int):
        if self.pending_box is None:
            print("[SIM] ERROR: PLACE_AT with no pending box!")
            return
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            print(f"[SIM] ERROR: PLACE_AT out of range ({x}, {y}), valid 0-{GRID_W-1},0-{GRID_H-1}, keeping pending box")
            return
        lane = self.lanes[(x, y)]
        if len(lane) >= LANE_DEPTH:
            print(f"[SIM] ERROR: Lane ({x}, {y}) full ({len(lane)}/{LANE_DEPTH}), keeping pending box")
            return
        print(f"[SIM] Placing box #{self.pending_box['id']} at ({x}, {y}), depth={len(lane)+1}/{LANE_DEPTH}")
        lane.append(self.pending_box)
        self.pending_box = None

    def handle_fetch_box(self, x: int, y: int, restock: bool):
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            print(f"[SIM] ERROR: FETCH_BOX out of range ({x}, {y})!")
            return
        lane = self.lanes[(x, y)]
        if not lane:
            print(f"[SIM] ERROR: Fetching from empty lane ({x}, {y})!")
            return

        box = lane.pop(0)  # Pop from front
        action = "RESTOCK" if restock else "EXIT"
        print(f"[SIM] Fetching box #{box['id']} from ({x}, {y}) → {action}")

        # Fake extraction delay
        time.sleep(0.3)

        if restock:
            lane.insert(0, box)  # Push back to front
            print(f"[SIM]   Box #{box['id']} restocked to front")

        self.bridge.send_message({"type": "FETCH_DONE"})

    def auto_advance_lanes(self):
        """
        Attempt to auto-advance boxes through lanes.
        (This is autonomous sim behavior, not triggered by STM.)
        Could push boxes forward, compact lanes, etc.
        For now: just log lane states periodically.
        """
        non_empty = {pos: len(q) for pos, q in self.lanes.items() if q}
        if non_empty:
            print(f"[SIM] Lane state: {non_empty}")

    def manual_add_box(self, sku=None, quantity=None):
        if self.pending_box is not None:
            print("[SIM] Input buffer occupied, waiting for PLACE_AT")
            return False
        if sku is None:
            sku = random.choice(list(SKU_TYPES.keys()))
        if quantity is None:
            quantity = SKU_TYPES[sku]
        self.spawn_box(sku, quantity)
        return True

    def poll_manual_button(self):
        try:
            r, _, _ = select.select([sys.stdin], [], [], 0)
        except Exception:
            return
        if r:
            line = sys.stdin.readline()
            if line is not None:
                cmd = line.strip().upper()
                if cmd in ("", "N", "NEW", "NEWBOX", "ADD"):
                    self.manual_add_box()

    def try_advance(self):
        """Try autonomous lane advancement."""
        now = time.time()
        if now - self.last_advance >= self.advance_interval:
            self.auto_advance_lanes()
            self.last_advance = now

    def poll(self):
        """Process incoming messages from Bridge."""
        for msg in self.bridge.poll_messages():
            msg_type = msg.get("type")

            if msg_type == "PLACE_AT":
                self.handle_place_at(msg["x"], msg["y"])

            elif msg_type == "FETCH_BOX":
                self.handle_fetch_box(msg["x"], msg["y"], msg["restock"])

            else:
                print(f"[SIM] Unknown message type: {msg_type}")

    def run(self):
        print("[SIM] Connected to Bridge (3x4 lanes, 10 deep). Press ENTER for manual box feed.")
        try:
            while self.running:
                self.poll_manual_button()
                self.try_advance()
                self.poll()
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("[SIM] Shutting down")
        except ConnectionError as e:
            print(f"[SIM] Bridge closed: {e}")


if __name__ == "__main__":
    sim = MockSim()
    sim.run()
