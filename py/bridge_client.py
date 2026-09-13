"""
Smart Core Warehouse — BridgeClient

Shared by both SIM (raylib) and HUD (PyQt6). Connects to one
of the two Unix domain sockets Bridge maintains, then exposes
send_message() and poll_messages(). Nothing in this file knows
about message types, roles, or routing — it is purely a
send/poll wrapper around one socket connection.

Usage
-----
SIM (inside update(dt), once per frame):

    from bridge_client import BridgeClient
    client = BridgeClient("/tmp/warehouse_sim.sock")

    def update(dt):
        for msg in client.poll_messages():
            handle(msg)

HUD (inside a QTimer tick):

    from bridge_client import BridgeClient
    client = BridgeClient("/tmp/warehouse_hud.sock")

    def on_poll():
        for msg in client.poll_messages():
            handle(msg)

Socket paths
------------
    HUD  ->  /tmp/warehouse_hud.sock
    SIM  ->  /tmp/warehouse_sim.sock

See SCW_bridge_protocol.md for the full message contract.
"""

import json
import socket


HUD_SOCKET_PATH = "/tmp/warehouse_hud.sock"
SIM_SOCKET_PATH = "/tmp/warehouse_sim.sock"


class BridgeClient:
    """
    Dumb wrapper around one Unix domain socket connection.
    No role, no handshake — identity is determined by which
    socket path you connect to. Bridge maintains two separate
    socket files; HUD connects to one, SIM to the other.

    Framing: newline-delimited JSON (one object per line).
    SOCK_STREAM gives no message-boundary guarantee on its own;
    poll_messages() handles partial arrivals by accumulating
    into a buffer and only yielding complete lines.
    """

    def __init__(self, address: str):

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(address)
        self.sock.setblocking(False)

        self._buf = b""

    def send_message(self, msg: dict):
        """Serialize msg as a single JSON line and send it."""

        line = (json.dumps(msg) + "\n").encode("utf-8")
        self.sock.sendall(line)

    def poll_messages(self) -> list:
        """
        Drain everything currently available on the socket and
        return every complete message as a list of dicts.

        Returns [] if nothing new has arrived.

        Each message is consumed exactly once — calling this
        again immediately returns [] until more data lands.

        A partial line (message still mid-arrival) stays in the
        internal buffer and will be returned on a later call
        once the rest of it arrives. It is never returned early.
        """

        # Drain the socket without blocking.
        while True:

            try:
                chunk = self.sock.recv(4096)
            except BlockingIOError:
                break

            if not chunk:
                raise ConnectionError("bridge closed connection")

            self._buf += chunk

        # Split on newlines; keep any trailing partial line.
        messages = []

        while b"\n" in self._buf:

            line, _, self._buf = self._buf.partition(b"\n")

            if line:
                messages.append(json.loads(line.decode("utf-8")))

        return messages
