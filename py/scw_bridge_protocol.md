# Smart Core Warehouse — Bridge Protocol Reference

> Locked design reference for the STM ⇄ Bridge ⇄ {HUD, SIM} messaging layer.
> This is the contract every component codes against.

## 0. Context (for anyone picking this up fresh)

This is for **NRW 2026** (National Robotics Week, INSAT) — the SOPAL &
SOPALTEC "Smart Core Warehouse" challenge. The team is building an
automated storage/retrieval system for SOPALTEC's brass plumbing fittings
(*articles de robinetterie en laiton*). Human workers sort fragile items
by type into chests and label each chest with a barcode/QR — the
automated system only ever identifies, moves, and reasons about whole
**chests**, never individual pieces. There are two parallel deliverables:
a FreeCAD parametric model of the physical gantry/chariot, and a Python +
raylib 3D simulation of the same mechanism (`warehouse2.py`) used for the
live demo, since the challenge is "tout en simulation" (no physical build
required, only a live-running simulation counts for evaluation).

Three components talk to each other through a central **Bridge**:

- **STM** — an STM32 board. Real hardware, connected over USB serial.
  Owns all the actual business logic (FIFO ordering, per-box dwell
  timing, capacity, lane assignment, order fulfillment math). The
  firmware is already written; what's left is testing it end-to-end
  against the simulation and the operator UI.
- **SIM** — the raylib simulation. Executes physical moves only (drive a
  robot to a coordinate, tilt-deposit a box, exit or restock a box). It
  is told *what* to do and *where*; it never decides anything on its own
  business-logic-wise.
- **HUD** — a PyQt operator terminal. One human places one order at a
  time and sees what STM reports back.

**~5h remain before the demo** at the time this doc was written — favor
getting the spec fully nailed down and each side testable in isolation
over polishing any one part.

If you're a fresh instance picking up either the SIM side or the HUD/PyQt
side: read this whole doc before writing code against it — it is the
single source of truth for message shapes, timing, and who owns what.

---

## 1. Actors

| Actor | Owns | Knows nothing about |
|-------|------|----------------------|
| **STM** | All business logic: FIFO order, per-box arrival timestamps, dwell/readiness, capacity per SKU, lane assignment (which `(x, y)` a box goes to or comes from), order fulfillment math (how many boxes/pieces an order needs) | The physical animation, robot mechanics, rendering |
| **HUD** | One user-facing terminal: placing an order, showing what STM reports back | Lane coordinates, FIFO state, timestamps, whether a box got exited or restocked |
| **SIM** | Physical execution only: moving robots, tilting the fork, sliding boxes, scanning a newly spawned box, running the two guards described below | SKUs' meaning, FIFO, timestamps, capacity, order math — it is told a coordinate and a bool, never asked to decide anything |

STM is **real hardware**, not a stand-in script — its logic is already
implemented in firmware; this integration is about testing it against
SIM and HUD directly, not mocking it.

---

## 2. Transport — two sockets, one serial link

Bridge maintains **two separate Unix domain sockets**, each dedicated to
exactly one of HUD and SIM — not one shared socket with a handshake to
figure out who's who:

- `/tmp/warehouse_hud.sock` — HUD connects here. Only HUD.
- `/tmp/warehouse_sim.sock` — SIM connects here. Only SIM.

Which socket a message arrived on **is** the identity — no role field, no
`HELLO` handshake, nothing negotiated at connect time. Bridge simply
knows "this came in on the HUD socket" or "this came in on the SIM
socket" by construction.

**Bridge ⇄ STM** is a third, different leg — USB serial (UART), binary,
not a socket at all. See §3.2.

**Framing (both sockets): newline-delimited JSON.** One JSON object per
line, `\n`-terminated. This is necessary, not stylistic —
`SOCK_STREAM` sockets give **zero** message-boundary guarantee on their
own (a single `send()` can arrive split across several `recv()`s, and
several sends can coalesce into one `recv()`). The delimiter is what
turns a raw byte stream back into discrete messages.

This means every message payload **must never contain a raw, unescaped
`\n`**. Serializing with a plain `json.dumps(msg)` already guarantees
this on its own (it escapes control characters, never emits a literal
newline inside compact output) — as long as nobody hand-builds a message
string instead of going through `json.dumps()`, this constraint holds
automatically and needs no extra checking.

Unix domain sockets chosen over TCP loopback (same code shape, skips the
IP stack, no port management) and over named pipes (a FIFO really wants
one reader/one writer per pipe, which maps fine here since each socket
now *is* already dedicated to one client — but a socket still gives
cleaner `accept()`/reconnect semantics than a FIFO's blocking-open
behavior).

---

## 3. Bridge

Pure router + protocol translator. Holds **zero** business logic of its
own — it maps a message's `type` to a destination, and translates
between transports where needed (socket↔socket needs no translation,
socket↔serial does).

```
ROUTES = {
    "BOX_SCANNED":      "STM",   # arrives on SIM socket, goes to serial
    "PLACE_AT":         "SIM",   # arrives on serial, goes to SIM socket

    "ORDER_REQUEST":    "STM",   # arrives on HUD socket, goes to serial
    "SUGGESTION":       "HUD",   # arrives on serial, goes to HUD socket
    "ORDER_CONFIRMED":  "HUD",
    "ORDER_DONE":       "HUD",

    "FETCH_BOX":        "SIM",   # arrives on serial, goes to SIM socket
    "FETCH_DONE":       "STM",   # arrives on SIM socket, goes to serial
}
```

Bridge's job per message: read a line off whichever socket (or the
serial link) has data, look up `ROUTES[msg["type"]]`, and write it to
the corresponding destination — the HUD socket, the SIM socket, or the
serial link, encoding/decoding binary only on the serial side.

**Bridge owns both socket files.** On startup, it must `unlink()` any
stale file at either path (left over from a crashed previous run —
`AF_UNIX` `bind()` fails if the path already exists) before binding and
listening on each.

### 3.1 Serial write serialization

A message from HUD and a message from SIM can both need to reach STM at
almost the same moment. Bridge must **never interleave** their encoded
bytes on the wire — one full binary frame finishes writing to the serial
port before the next one starts. A single writer (a lock around the
serial write, or one dedicated writer thread draining a queue that both
socket handlers push onto) is required here, not optional.

### 3.2 STM binary protocol — open item

Not specified in this document. Whoever wrote the STM firmware needs to
supply: message type IDs, field layout/sizes/endianness per message
(matching the JSON fields in §4), and whatever framing/checksum scheme
the firmware already parses on its end. Bridge's serial encode/decode
must be built against that spec once available — this doc only defines
the JSON semantic layer Bridge normalizes the binary side into.

---

## 4. Message catalog

All messages are one JSON object on the socket side; Bridge transcodes
each to/from STM's binary frame format per §3.2.

### 4.1 Infeed — a new box entering the system

| Type | Direction | Fields | Semantics |
|---|---|---|---|
| `BOX_SCANNED` | Sim → STM | `sku` (int), `quantity` (int) | A spawned box just finished the scanner gate; its type is now known. `quantity` is normally the SKU's constant capacity — sent anyway so a future non-const fill doesn't need a protocol change. |
| `PLACE_AT` | STM → Sim | `x` (int), `y` (int) | STM's answer: which lane cell this box goes into. May arrive immediately after `BOX_SCANNED` or much later if STM defers (no lane free yet) — same message either way, only timing differs. |

```json
{"type": "BOX_SCANNED", "sku": 1, "quantity": 20}
{"type": "PLACE_AT", "x": 0, "y": 2}
```

**Sim-side guard (not a message, a local rule):** once a box has been
scanned and is sitting in the pending buffer awaiting `PLACE_AT`, Sim
must not let a second box reach the scanner. One boolean flag, held
until `PLACE_AT` is received for the pending box.

### 4.2 Order — a human requests pieces of one SKU

| Type | Direction | Fields | Semantics |
|---|---|---|---|
| `ORDER_REQUEST` | HUD → STM | `sku` (int), `qty` (int) | Only sendable while HUD is `FREE`. Single SKU per request. |
| `SUGGESTION` | STM → HUD | `qty` (int) | **Only sent when the requested qty is not fully coverable.** `qty` is the largest amount STM can actually fulfill right now (can be 0). Pure information, not an offer needing acceptance — HUD returns to `FREE` on receipt; the user's next move is simply another plain `ORDER_REQUEST`. |
| `ORDER_CONFIRMED` | STM → HUD | `num_boxes` (int), `num_pieces` (int) | Sent when STM accepts and **starts working** — either immediately after a fully-coverable `ORDER_REQUEST`, or after a follow-up `ORDER_REQUEST` that is now coverable. `num_boxes` = boxes fully emptied; `num_pieces` = the remainder pulled from exactly one more box (which gets restocked). Purely informational — lets the user know what to expect before it happens. Sent to HUD only; Sim never sees these numbers. |
| `ORDER_DONE` | STM → HUD | *(none)* | All boxes for this order have been cycled through Sim. "Done" means STM has confirmed completion — not that pieces have physically arrived anywhere downstream. |

```json
{"type": "ORDER_REQUEST", "sku": 1, "qty": 35}
{"type": "SUGGESTION", "qty": 30}
{"type": "ORDER_REQUEST", "sku": 1, "qty": 30}
{"type": "ORDER_CONFIRMED", "num_boxes": 2, "num_pieces": 0}
{"type": "ORDER_DONE"}
```

### 4.3 Fetch — STM driving Sim through one box at a time

| Type | Direction | Fields | Semantics |
|---|---|---|---|
| `FETCH_BOX` | STM → Sim | `x`, `y` (int), `restock` (bool) | Pull the box at this lane. `restock` is decided by STM **before** the pull (its own FIFO/qty math) — Sim never decides this itself. |
| `FETCH_DONE` | Sim → STM | *(none)* | The pull-and-either-exit-or-restock cycle for this one box is finished. One event either way — Sim already knows internally which branch it took (it's the flag STM sent), nothing further to report. |

```json
{"type": "FETCH_BOX", "x": 0, "y": 1, "restock": true}
{"type": "FETCH_DONE"}
```

---

## 5. HUD lock state machine

```
                 send ORDER_REQUEST
   ┌────── FREE ─────────────────────────► LOCKED (awaiting decision)
   │                                                │        │
   │            receive SUGGESTION ─────────────────┘        │
   │                                                          │
   │                                    receive ORDER_CONFIRMED
   │                                                          ▼
   │                                          LOCKED (awaiting order)
   │                                                          │
   └───────────────── receive ORDER_DONE ────────────────────┘
```

- **FREE** — the only state in which `ORDER_REQUEST` may be sent.
- **LOCKED (awaiting decision)** — entered the instant a request is sent.
  Resolved by whichever of `SUGGESTION` / `ORDER_CONFIRMED` arrives.
- `SUGGESTION` → back to **FREE** immediately (no accept/confirm round trip).
- `ORDER_CONFIRMED` → **LOCKED (awaiting order)**, held through every
  `FETCH_BOX`/`FETCH_DONE` STM runs internally against Sim (HUD never
  sees these), until `ORDER_DONE` releases it back to **FREE**.

**No cancellation exists anywhere in this flow** — not while awaiting a
decision, and not once `ORDER_CONFIRMED` has been received. The only
exits from `LOCKED` are the two transitions shown above. Deliberate
simplicity trade-off: supporting cancellation would require STM to track
per-order request ids so it knows which in-flight order a cancel refers
to — avoided on purpose to keep the protocol stateless per-exchange.

---

## 6. Demo-scale parameters (flagged, not yet fixed)

- **Dwell/readiness threshold:** real spec is ≥24h. Demo will use a
  compressed value — options on the table are a fixed short duration
  (e.g. ~10–20s) and/or simply speeding up the simulation's own clock —
  final choice deferred until animation speed is tuned live, whichever
  reads as visibly real but fast enough not to stall the demo.
- **Grid size:** current plan is to **attempt the real full scale**
  (15×26 lanes, ×10 deep) end to end, matching STM's actual coordinate
  space, rather than treating it as a spoken-only number. Fallback if
  that proves impractical in the remaining time: shrink the grid and
  recompile the STM firmware to match a smaller coordinate space. This
  decision is still open — whichever way it lands, Sim's renderable
  grid must match whatever coordinate space STM is actually issuing
  `PLACE_AT`/`FETCH_BOX` coordinates in.

---

## 7. `BridgeClient` — one dumb class, both socket-side consumers

Used by **HUD** and **SIM**. It knows nothing about roles, business
logic, or message types — it is purely "connect to this address, then
send and poll." STM sits on the serial leg instead, handled entirely
inside Bridge (§3) — STM does not use this class at all.

```python
import json
import socket


class BridgeClient:
    """
    Dumb wrapper around one Unix domain socket connection.
    Connects to whatever address it's given, then exposes
    send_message()/poll_messages(). No role, no handshake -
    HUD and SIM each just point it at their own dedicated
    socket path (see §2) and it behaves identically for both.
    """

    def __init__(self, address):

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(address)
        self.sock.setblocking(False)

        self._buf = b""

    def send_message(self, msg: dict):

        line = (json.dumps(msg) + "\n").encode("utf-8")
        self.sock.sendall(line)

    def poll_messages(self) -> list:
        """
        Drains everything currently available and returns every
        complete message as a list (empty if nothing new arrived).
        Each message is consumed once. A trailing partial line
        (a message still mid-arrival) stays buffered and is never
        returned early - it completes on a later call once the
        rest of it lands.
        """

        while True:

            try:
                chunk = self.sock.recv(4096)
            except BlockingIOError:
                break

            if not chunk:
                raise ConnectionError("bridge closed")

            self._buf += chunk

        messages = []

        while b"\n" in self._buf:

            line, _, self._buf = self._buf.partition(b"\n")

            if line:
                messages.append(json.loads(line.decode("utf-8")))

        return messages
```

**Design note — why `poll_messages()` and not a callback:** both raylib
(Sim) and PyQt (HUD) are single-threaded toolkits. A callback firing
from a background network thread and touching simulation state or a
widget directly is a real crash/race risk. Polling from inside each
toolkit's own loop sidesteps this entirely — zero threading code needed
in either consumer.

### 7.1 Usage in Sim (raylib)

Called once per frame, inside the existing `update(dt)` — never blocks
the render loop:

```python
SIM_SOCKET_PATH = "/tmp/warehouse_sim.sock"

sim_client = BridgeClient(SIM_SOCKET_PATH)

def update(self, dt):
    ...
    for msg in sim_client.poll_messages():
        if msg["type"] == "PLACE_AT":
            self.handle_place_at(msg["x"], msg["y"])
        elif msg["type"] == "FETCH_BOX":
            self.handle_fetch_box(msg["x"], msg["y"], msg["restock"])
    ...
```

Emitting events out follows the existing state transitions Sim already
has — e.g. `BOX_SCANNED` fires at the `SCANNING → WAITING` transition,
`FETCH_DONE` fires once the extraction robot's `XEXIT`/`XRESTOCK` cycle
completes and it's back to `IDLE`.

### 7.2 Usage in HUD (PyQt)

Polled on a `QTimer` tick instead of a per-frame loop — same
non-blocking pattern, PyQt's own event loop drives the cadence:

```python
HUD_SOCKET_PATH = "/tmp/warehouse_hud.sock"

class HudWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bridge = BridgeClient(HUD_SOCKET_PATH)

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.on_poll)
        self.poll_timer.start(100)  # ms

    def on_poll(self):
        for msg in self.bridge.poll_messages():
            if msg["type"] == "SUGGESTION":
                self.show_suggestion(msg["qty"])
            elif msg["type"] == "ORDER_CONFIRMED":
                self.show_confirmed(msg["num_boxes"], msg["num_pieces"])
            elif msg["type"] == "ORDER_DONE":
                self.unlock_ui()

    def on_submit_clicked(self):
        self.lock_ui()
        self.bridge.send_message({
            "type": "ORDER_REQUEST",
            "sku": self.sku_field.value(),
            "qty": self.qty_field.value(),
        })
```

---

## 8. Naming reference

| Name | Value |
|---|---|
| HUD socket path | `/tmp/warehouse_hud.sock` |
| SIM socket path | `/tmp/warehouse_sim.sock` |
| Serial device path (Bridge ⇄ STM) | TBD — configurable at Bridge startup (e.g. `/dev/ttyUSB0`) |
| Baud rate (Bridge ⇄ STM) | TBD — must match firmware's configured rate |
| Binary frame format (Bridge ⇄ STM) | TBD — see §3.2, owned by STM firmware |

No handshake message exists — a client's identity is simply which of
the two socket paths it connected to. STM is reached over the separate
serial leg (§2), not either socket.