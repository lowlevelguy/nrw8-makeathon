"""
Smart Core Warehouse - Bridge

Routes messages between three legs:
  - HUD (Unix domain socket, JSON, newline-delimited)
  - SIM (Unix domain socket, JSON, newline-delimited)
  - STM (USB serial, 4-byte binary packets)

Two dedicated sockets, no HELLO/role handshake - which socket a
message arrives on IS the identity. STM speaks the wire format
in netstack.h. See SCW_bridge_protocol.md for the semantic
contract Bridge is translating between.

Everything the STM firmware has not yet committed to is
gathered in the two TODO_STM_* blocks near the top. When those
values firm up, patch them there - nothing else in this file
should need touching.
"""

import json
import os
import queue
import selectors
import socket
import struct
import sys
import threading

import serial


# ============================================================
# 1. TRANSPORT CONFIG - HUD/SIM sockets, STM serial link
# ============================================================

HUD_SOCKET_PATH = "/tmp/warehouse_hud.sock"
SIM_SOCKET_PATH = "/tmp/warehouse_sim.sock"

# Overridable from argv[1]; the firmware guy's board is
# whatever ttyUSB* / ttyACM* enumerates when he plugs it in.
STM_SERIAL_DEV = "/dev/ttyUSB0"
STM_SERIAL_BAUD = 115200


# ============================================================
# 2. STM WIRE FORMAT - what's committed in firmware headers
# ============================================================

# Packet is exactly 4 bytes, MSB-first, layout:
#   byte 0: link header (sof:7 | is_rx:1)  - the bitfield in
#           netstack.h stores sof in the low 7 bits, is_rx in
#           bit 7. NETSTACK_SOF is defined as (0xAA & 0xFE)
#           which is 0xAA, but the 7-bit bitfield truncates
#           it to 0x2A. So on the wire:
#             TX (firmware to host): byte 0 == 0x2A
#             RX (host to firmware): byte 0 == 0xAA
#   byte 1: application type ID
#   byte 2..3: params

PACKET_SIZE = 4

SOF_BYTE_TX_FROM_STM = 0x2A   # is_rx=0
SOF_BYTE_RX_TO_STM   = 0xAA   # is_rx=1


# ---- TX types (firmware -> host) - committed in netstack.h --
TX_SELECT_INPUT_LANE  = 0
TX_SELECT_OUTPUT_LANE = 1
TX_KERNELS_ACK        = 2
TX_KERNELS_NACK       = 3

# ---- RX types (host -> firmware) - committed in netstack.h -
RX_BARCODE_READING       = 0
RX_FETCH_KERNELS_REQUEST = 1
RX_BOX_FETCH_DONE        = 2


# ============================================================
# 3. TODO_STM_TYPES - not committed in firmware yet
# ============================================================
# These are now committed in netstack.h. IDs verified against
# the firmware source at commit 87a7535.

TX_SELECT_OUTPUT_LANE_AND_RESTOCK = 5    # was TODO
TX_ORDER_DONE                     = 4    # was TODO - firmware calls it FETCH_COMPLETE


# ============================================================
# 4. TODO_STM_PARAMS - param byte layouts not yet committed
# ============================================================
# There are only 2 param bytes per packet (bytes 2-3). Layouts
# below encode/decode those two bytes; change these functions
# when STM guy settles the layouts.

# BARCODE_READING (SIM->STM): SIM's BOX_SCANNED carries sku +
# quantity. Confirmed against firmware: store_box(type,
# capacity) - param[0]=sku (type), param[1]=quantity (capacity).

def encode_barcode_reading_params(sku: int, quantity: int) -> bytes:
    return bytes([sku & 0xFF, quantity & 0xFF])


# FETCH_KERNELS_REQUEST (HUD->STM): HUD's ORDER_REQUEST carries
# sku + qty. Only 2 param bytes available on the wire, but
# firmware's fetch_kernels(type, count) takes count as
# uint32_t. Current encoding: param[0]=sku, param[1]=qty
# clamped to 255. This ONLY works up to qty=255. If demo
# orders will exceed 255 pieces we need a wider scheme -
# options: (a) split across 2 packets (sku packet, count
# packet), (b) drop sku from this packet since firmware
# already knows the "current" type from context (it doesn't
# today), (c) use a bigger packet_t.
#
# For now this is enough for a demo with modest quantities;
# flag this to STM guy if orders will realistically exceed 255.

def encode_fetch_kernels_request_params(sku: int, qty: int) -> bytes:
    return bytes([sku & 0xFF, min(qty, 0xFF)])


# ============================================================
# 5. Committed param decoders (from netstack.h + AI spec's
#    wire-format section, which came from headers not
#    behavioral guesses)
# ============================================================

def decode_lane_coords(params: bytes) -> tuple[int, int]:
    """SELECT_INPUT_LANE / SELECT_OUTPUT_LANE / _AND_RESTOCK:
    param[0] = x (column), param[1] = y (row). Firmware today
    still has the % LANE_COUNT bug, will be fixed to
    % SHELF_WIDTH; Bridge trusts whatever lands."""
    return params[0], params[1]


def decode_kernels_ack_params(params: bytes) -> tuple[int, int]:
    """param[0] = boxes served (uint8, saturating at 255).
    param[1] = leftover kernels in the final partial box (0
    when every box drained fully)."""
    return params[0], params[1]


def decode_kernels_nack_params(params: bytes) -> int:
    """Big-endian uint16 count of ready kernels currently
    available. Saturates at 0xFFFF."""
    return (params[0] << 8) | params[1]


# ============================================================
# 6. Packet codec
# ============================================================

def build_packet(is_rx: int, type_id: int, params: bytes) -> bytes:
    """Serialize one 4-byte packet.  Only the low 7 bits of the
    SOF constant land on the wire (the header field is 7 bits
    wide in firmware); is_rx is the top bit."""

    if len(params) != 2:
        raise ValueError("params must be exactly 2 bytes")

    sof_7 = 0x2A                        # truncation of 0xAA
    byte0 = ((is_rx & 1) << 7) | sof_7

    return bytes([byte0, type_id & 0xFF, params[0], params[1]])


def parse_packet(pkt: bytes) -> tuple[int, int, bytes]:
    """Returns (is_rx, type_id, params_2bytes)."""

    if len(pkt) != PACKET_SIZE:
        raise ValueError(f"expected {PACKET_SIZE} bytes, got {len(pkt)}")

    byte0 = pkt[0]
    is_rx = (byte0 >> 7) & 1
    # Bits 6..0 of byte0 are SOF; firmware doesn't validate it
    # on receive so we don't either - the AI spec noted this
    # deliberately.
    type_id = pkt[1]
    params = pkt[2:4]

    return is_rx, type_id, params


# ============================================================
# 7. Route table: what JSON type each STM packet becomes
#    (STM -> Bridge -> {HUD, SIM} direction only; the reverse
#     direction is a switch on the incoming JSON's "type" in
#     handle_json_from_hud / handle_json_from_sim)
# ============================================================

# When Bridge sees an STM TX packet with this type ID, it
# builds the corresponding JSON message and routes it per the
# {destination, builder_fn} pair. builder_fn takes the raw 2
# param bytes and returns a JSON-serializable dict payload
# (the "type" field is added by the caller).

STM_TX_ROUTES = {}


def register_stm_tx_route(type_id, dest_role, json_type, param_builder):
    """None-safe registration: TX_ORDER_DONE etc. are -1 until
    the STM guy commits an ID, and passing -1 here has no
    ill effect - the incoming packet parser will never match a
    negative type_id since real bytes are always 0..255."""

    if type_id < 0:
        return

    STM_TX_ROUTES[type_id] = (dest_role, json_type, param_builder)


register_stm_tx_route(
    TX_SELECT_INPUT_LANE, "SIM", "PLACE_AT",
    lambda p: {"x": p[0], "y": p[1]},
)

register_stm_tx_route(
    TX_SELECT_OUTPUT_LANE, "SIM", "FETCH_BOX",
    lambda p: {"x": p[0], "y": p[1], "restock": False},
)

# When STM guy commits the type ID, patch the constant at the
# top and this route lights up automatically:
register_stm_tx_route(
    TX_SELECT_OUTPUT_LANE_AND_RESTOCK, "SIM", "FETCH_BOX",
    lambda p: {"x": p[0], "y": p[1], "restock": True},
)

register_stm_tx_route(
    TX_KERNELS_ACK, "HUD", "ORDER_CONFIRMED",
    lambda p: {"num_boxes": p[0], "num_pieces": p[1]},
)

register_stm_tx_route(
    TX_KERNELS_NACK, "HUD", "SUGGESTION",
    lambda p: {"qty": (p[0] << 8) | p[1]},
)

register_stm_tx_route(
    TX_ORDER_DONE, "HUD", "ORDER_DONE",
    lambda p: {},
)


# ============================================================
# 8. Bridge
# ============================================================

class Bridge:

    def __init__(self, serial_dev=STM_SERIAL_DEV):
        self.serial_dev = serial_dev

        # Sockets: one accepted client per socket (each socket
        # is single-purpose - one for HUD, one for SIM).
        self._hud_conn = None
        self._sim_conn = None

        # Per-connection JSON line buffers (\n-delimited).
        self._hud_buf = b""
        self._sim_buf = b""

        # Anything destined for STM goes through one queue and
        # is drained by one writer thread - never interleaved
        # on the wire (see SCW_bridge_protocol.md §3.1).
        self._stm_tx_q = queue.Queue()

        # STM read buffer: bytes stream, framed 4 at a time.
        # Hello-World bursts and any other garbage before a
        # valid 0x2A header byte are skipped.
        self._stm_rx_buf = bytearray()

        # Selector drives the whole thing single-threaded; the
        # STM writer thread is separate because pyserial's
        # write is blocking.
        self._sel = selectors.DefaultSelector()

    # ---- setup ------------------------------------------------

    def _bind_socket(self, path):
        """Unlink any stale socket file left behind by a
        crashed previous run, then bind + listen."""

        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(path)
        s.listen(1)
        s.setblocking(False)

        return s

    def run(self):

        hud_listener = self._bind_socket(HUD_SOCKET_PATH)
        sim_listener = self._bind_socket(SIM_SOCKET_PATH)

        self._sel.register(
            hud_listener, selectors.EVENT_READ,
            data=("accept", "HUD")
        )
        self._sel.register(
            sim_listener, selectors.EVENT_READ,
            data=("accept", "SIM")
        )

        # Serial: open non-blocking so the main select loop can
        # poll it without stalling.
        try:
            self._stm = serial.Serial(
                self.serial_dev, STM_SERIAL_BAUD,
                timeout=0, write_timeout=1.0
            )
        except serial.SerialException as e:
            print(f"[bridge] WARNING: could not open {self.serial_dev}: {e}")
            print("[bridge]   Running without STM leg. HUD/SIM will still route.")
            self._stm = None

        if self._stm is not None:
            self._sel.register(
                self._stm, selectors.EVENT_READ,
                data=("stm_rx", None)
            )
            writer = threading.Thread(
                target=self._stm_writer_loop, daemon=True
            )
            writer.start()

        print(f"[bridge] HUD socket: {HUD_SOCKET_PATH}")
        print(f"[bridge] SIM socket: {SIM_SOCKET_PATH}")
        print(f"[bridge] STM serial: {self.serial_dev} @ {STM_SERIAL_BAUD}")

        while True:
            for key, _ in self._sel.select(timeout=None):
                kind, role = key.data
                if kind == "accept":
                    self._accept(key.fileobj, role)
                elif kind == "sock_rx":
                    self._sock_read(key.fileobj, role)
                elif kind == "stm_rx":
                    self._stm_read()

    # ---- socket side (HUD, SIM) ------------------------------

    def _accept(self, listener, role):

        conn, _ = listener.accept()
        conn.setblocking(False)

        if role == "HUD":
            if self._hud_conn is not None:
                print("[bridge] HUD already connected, dropping new conn")
                conn.close()
                return
            self._hud_conn = conn
        else:
            if self._sim_conn is not None:
                print("[bridge] SIM already connected, dropping new conn")
                conn.close()
                return
            self._sim_conn = conn

        self._sel.register(
            conn, selectors.EVENT_READ, data=("sock_rx", role)
        )
        print(f"[bridge] {role} connected")

    def _sock_read(self, conn, role):

        try:
            chunk = conn.recv(4096)
        except (BlockingIOError, OSError):
            return

        if not chunk:
            self._sock_close(conn, role)
            return

        if role == "HUD":
            self._hud_buf += chunk
            buf_ref = "_hud_buf"
        else:
            self._sim_buf += chunk
            buf_ref = "_sim_buf"

        buf = getattr(self, buf_ref)
        while b"\n" in buf:
            line, _, buf = buf.partition(b"\n")
            setattr(self, buf_ref, buf)
            if not line:
                continue
            try:
                msg = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError as e:
                print(f"[bridge] bad JSON from {role}: {e}: {line!r}")
                continue

            if role == "HUD":
                self._handle_json_from_hud(msg)
            else:
                self._handle_json_from_sim(msg)

    def _sock_close(self, conn, role):

        try:
            self._sel.unregister(conn)
        except KeyError:
            pass
        conn.close()

        if role == "HUD":
            self._hud_conn = None
            self._hud_buf = b""
        else:
            self._sim_conn = None
            self._sim_buf = b""

        print(f"[bridge] {role} disconnected")

    def _send_to_sock(self, role, msg):

        conn = self._hud_conn if role == "HUD" else self._sim_conn
        if conn is None:
            print(f"[bridge] {role} not connected, dropping {msg}")
            return

        line = (json.dumps(msg) + "\n").encode("utf-8")
        try:
            conn.sendall(line)
        except OSError as e:
            print(f"[bridge] send to {role} failed: {e}")
            self._sock_close(conn, role)

    # ---- JSON -> STM translation -----------------------------

    def _handle_json_from_sim(self, msg):

        t = msg.get("type")

        if t == "BOX_SCANNED":
            params = encode_barcode_reading_params(
                int(msg["sku"]), int(msg["quantity"])
            )
            self._queue_to_stm(RX_BARCODE_READING, params)

        elif t == "FETCH_DONE":
            # BOX_FETCH_DONE's params are ignored by firmware.
            self._queue_to_stm(RX_BOX_FETCH_DONE, bytes([0, 0]))

        else:
            print(f"[bridge] SIM sent unknown type: {t}")

    def _handle_json_from_hud(self, msg):

        t = msg.get("type")

        if t == "ORDER_REQUEST":
            params = encode_fetch_kernels_request_params(
                int(msg["sku"]), int(msg["qty"])
            )
            self._queue_to_stm(RX_FETCH_KERNELS_REQUEST, params)

        else:
            print(f"[bridge] HUD sent unknown type: {t}")

    def _queue_to_stm(self, type_id, params):

        if self._stm is None:
            print(f"[bridge] STM not open, dropping outbound type={type_id}")
            return

        pkt = build_packet(is_rx=1, type_id=type_id, params=params)
        self._stm_tx_q.put(pkt)

    # ---- STM side --------------------------------------------

    def _stm_writer_loop(self):
        """One writer, serialized writes - never interleaves
        two packets' bytes on the wire (SCW_bridge_protocol §3.1)."""

        while True:
            pkt = self._stm_tx_q.get()
            try:
                self._stm.write(pkt)
                self._stm.flush()
            except (serial.SerialException, OSError) as e:
                print(f"[bridge] serial write failed: {e}")

    def _stm_read(self):

        try:
            chunk = self._stm.read(256)
        except (serial.SerialException, OSError) as e:
            print(f"[bridge] serial read failed: {e}")
            return

        if not chunk:
            return

        self._stm_rx_buf.extend(chunk)

        # Frame 4 bytes at a time. Skip anything that isn't a
        # TX SOF byte (firmware's main.c today spams
        # "Hello World!\r\n" - that garbage skips cleanly this
        # way because none of its bytes equal 0x2A).
        while True:
            self._advance_to_sof()

            if len(self._stm_rx_buf) < PACKET_SIZE:
                return

            pkt = bytes(self._stm_rx_buf[:PACKET_SIZE])
            del self._stm_rx_buf[:PACKET_SIZE]

            self._handle_stm_packet(pkt)

    def _advance_to_sof(self):
        """Drop bytes off the front until byte 0 is a valid
        firmware->host SOF (0x2A)."""

        while (
            self._stm_rx_buf
            and self._stm_rx_buf[0] != SOF_BYTE_TX_FROM_STM
        ):
            self._stm_rx_buf.pop(0)

    def _handle_stm_packet(self, pkt):

        try:
            is_rx, type_id, params = parse_packet(pkt)
        except ValueError as e:
            print(f"[bridge] bad packet: {e}: {pkt!r}")
            return

        if is_rx != 0:
            print(f"[bridge] unexpected is_rx=1 packet from STM, dropping: {pkt!r}")
            return

        route = STM_TX_ROUTES.get(type_id)
        if route is None:
            print(f"[bridge] STM sent unrouted type_id={type_id}, params={params!r}")
            return

        dest_role, json_type, param_builder = route
        payload = param_builder(params)
        msg = {"type": json_type, **payload}
        self._send_to_sock(dest_role, msg)


# ============================================================
# 9. Entry point
# ============================================================

def main():

    dev = sys.argv[1] if len(sys.argv) > 1 else STM_SERIAL_DEV
    Bridge(serial_dev=dev).run()


if __name__ == "__main__":
    main()
