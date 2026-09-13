"""
Smart Core Warehouse — HUD (operator terminal)

PyQt6 window implementing just the operator workflow from
SCW_bridge_protocol.md §4.2 / §5:

    1. Operator enters SKU + qty, hits Submit.
    2. Form locks (LOCKED — awaiting decision).
    3. Bridge replies with exactly one of:
         - SUGGESTION      -> can't fully cover the request; show the
                               qty STM *can* fulfill, unlock the form.
         - ORDER_CONFIRMED -> show num_boxes / num_pieces, stay locked
                               (LOCKED — awaiting order).
    4. If ORDER_CONFIRMED was received, wait for ORDER_DONE, then
       unlock the form.

No raw bridge traffic is shown — only the resulting workflow state.

Run:
    pip install PyQt6
    python hud.py

Expects Bridge to be up and listening on /tmp/warehouse_hud.sock.
"""

import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QSpinBox,
    QPushButton,
    QStatusBar,
)

from bridge_client import BridgeClient, HUD_SOCKET_PATH

POLL_INTERVAL_MS = 100

STATE_FREE = "FREE"
STATE_LOCKED_DECISION = "LOCKED (awaiting decision)"
STATE_LOCKED_ORDER = "LOCKED (awaiting order)"

STATE_COLORS = {
    STATE_FREE: "#2e7d32",
    STATE_LOCKED_DECISION: "#ef6c00",
    STATE_LOCKED_ORDER: "#c62828",
}


class HudWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCW — HUD Operator Terminal")
        self.resize(420, 260)

        self.bridge: BridgeClient | None = None
        self.state = STATE_FREE

        self._build_ui()
        self._connect_bridge()

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.on_poll)
        self.poll_timer.start(POLL_INTERVAL_MS)

    # ---------------------------------------------------------- UI setup

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)

        form_layout = QFormLayout()

        self.sku_field = QSpinBox()
        self.sku_field.setRange(0, 9999)

        self.qty_field = QSpinBox()
        self.qty_field.setRange(1, 999999)

        self.submit_btn = QPushButton("Submit order")
        self.submit_btn.clicked.connect(self.on_submit_clicked)

        form_layout.addRow("SKU", self.sku_field)
        form_layout.addRow("Qty", self.qty_field)
        form_layout.addRow(self.submit_btn)

        self.state_label = QLabel(self.state)
        self.state_label.setStyleSheet(
            f"font-weight: bold; font-size: 15px; color: {STATE_COLORS[self.state]};"
        )

        self.message_label = QLabel("—")
        self.message_label.setWordWrap(True)

        root.addLayout(form_layout)
        root.addSpacing(12)
        root.addWidget(self.state_label)
        root.addWidget(self.message_label)
        root.addStretch(1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self._set_connection_status(False)

    # ---------------------------------------------------------- bridge

    def _connect_bridge(self):
        try:
            self.bridge = BridgeClient(HUD_SOCKET_PATH)
            self._set_connection_status(True)
        except (FileNotFoundError, ConnectionRefusedError, OSError):
            self.bridge = None
            self._set_connection_status(False)

    def _set_connection_status(self, connected: bool):
        if connected:
            self.statusBar().showMessage(f"Connected — {HUD_SOCKET_PATH}")
        else:
            self.statusBar().showMessage(
                f"Disconnected — waiting for Bridge on {HUD_SOCKET_PATH} ..."
            )

    def on_poll(self):
        if self.bridge is None:
            self._connect_bridge()
            return

        try:
            messages = self.bridge.poll_messages()
        except ConnectionError:
            self.bridge = None
            self._set_connection_status(False)
            self.message_label.setText("Bridge connection lost.")
            self._set_state(STATE_FREE)
            return

        for msg in messages:
            self._handle_message(msg)

    def _handle_message(self, msg: dict):
        mtype = msg.get("type")

        if mtype == "SUGGESTION":
            qty = msg.get("qty")
            self.message_label.setText(
                f"Can't fully satisfy that request — {qty} available right now. "
                "Try another order."
            )
            self._set_state(STATE_FREE)

        elif mtype == "ORDER_CONFIRMED":
            num_boxes = msg.get("num_boxes")
            num_pieces = msg.get("num_pieces")
            self.message_label.setText(
                f"Order confirmed — {num_boxes} box(es) incoming, "
                f"{num_pieces} piece(s) residue. Working..."
            )
            self._set_state(STATE_LOCKED_ORDER)

        elif mtype == "ORDER_DONE":
            self.message_label.setText("Order done.")
            self._set_state(STATE_FREE)

        # Anything else routed to the HUD socket is outside this
        # workflow and is ignored here.

    def _set_state(self, new_state: str):
        self.state = new_state
        self.state_label.setText(new_state)
        self.state_label.setStyleSheet(
            f"font-weight: bold; font-size: 15px; color: {STATE_COLORS[new_state]};"
        )
        is_free = new_state == STATE_FREE
        self.submit_btn.setEnabled(is_free)
        self.sku_field.setEnabled(is_free)
        self.qty_field.setEnabled(is_free)

    # ---------------------------------------------------------- actions

    def on_submit_clicked(self):
        if self.state != STATE_FREE or self.bridge is None:
            return

        msg = {
            "type": "ORDER_REQUEST",
            "sku": self.sku_field.value(),
            "qty": self.qty_field.value(),
        }

        try:
            self.bridge.send_message(msg)
        except OSError:
            self.bridge = None
            self._set_connection_status(False)
            self.message_label.setText("Send failed — bridge connection lost.")
            return

        self.message_label.setText("Order sent — awaiting STM decision...")
        self._set_state(STATE_LOCKED_DECISION)


def main():
    app = QApplication(sys.argv)
    window = HudWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()