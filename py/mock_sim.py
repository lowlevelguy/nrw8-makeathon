import json
import time
import random
from collections import defaultdict
from bridge_client import BridgeClient

SIM_SOCKET_PATH = "/tmp/warehouse_sim.sock"

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
        self.pending_box = None  # Guard: one box awaiting PLACE_AT
        self.lanes = defaultdict(list)  # (x, y) -> [box, box, box...]
        self.running = True
        self.box_id = 0
        
        # Spawning control
        self.last_spawn = time.time()
        self.spawn_interval = 1.5  # Spawn every 1.5 seconds
        
        # Auto-advance control
        self.last_advance = time.time()
        self.advance_interval = 0.5  # Try advance every 500ms

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
        """STM tells us where to push the pending box."""
        if self.pending_box is None:
            print("[SIM] ERROR: PLACE_AT with no pending box!")
            return

        lane = self.lanes[(x, y)]
        assert len(lane) < 10, f"Lane ({x}, {y}) is full! (depth={len(lane)})"

        print(f"[SIM] Placing box #{self.pending_box['id']} at ({x}, {y}), depth={len(lane)+1}/10")
        lane.append(self.pending_box)
        self.pending_box = None

    def handle_fetch_box(self, x: int, y: int, restock: bool):
        """STM tells us to pop from lane start and either exit or restock."""
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

    def try_spawn(self):
        """Spawn a box if enough time has passed."""
        now = time.time()
        if now - self.last_spawn >= self.spawn_interval and self.pending_box is None:
            sku = random.choice(list(SKU_TYPES.keys()))
            qty = SKU_TYPES[sku]
            self.spawn_box(sku, qty)
            self.last_spawn = now

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
        """Main loop: spawn boxes, advance lanes, process messages."""
        print("[SIM] Connected to Bridge (26×15 lanes)")
        
        try:
            while self.running:
                self.try_spawn()      # Spawn periodically
                self.try_advance()    # Auto-advance lanes
                self.poll()           # Handle STM commands
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("[SIM] Shutting down")
        except ConnectionError as e:
            print(f"[SIM] Bridge closed: {e}")


if __name__ == "__main__":
    sim = MockSim()
    sim.run()
