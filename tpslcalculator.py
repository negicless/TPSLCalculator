# Cless TP/SL Desktop — Qt5 Modern UI + Profit Bar Overlay (v4.2)
# ----------------------------------------------------------------
# Install deps:  pip install PyQt5
# Run:          python cless_tp_sl_qt.py
# ----------------------------------------------------------------

import math
import sys
from PyQt5.QtCore import Qt, QSettings, QRectF, QTimer, QLineF, QPointF
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QPen,QIcon, QBrush, QLinearGradient
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QGridLayout, QDoubleSpinBox, QSpinBox,
    QComboBox, QSlider, QPushButton, QHBoxLayout, QVBoxLayout, QFrame,
    QCheckBox, QGroupBox
)

APP_ORG = "Cless"
APP_NAME = "TPSLCalculator"

DEFAULTS = {
    "entry": 115.0,
    "current": 119.72,
    "shares": 100,
    "tick": 0.01,
    "side": "Long",    # Long/Short
    "stop_pct": -4.0,
    "target_pct": 8.0,
    "flat_fee": 0.0,
    "per_share_fee": 0.0,
    "always_on_top": True,
}

# ---------------- Profit Bar Overlay ----------------
class ProfitBar(QWidget):
    """Vertical gradient bar from Stop → Entry → Target, with live current price marker.
       Works for Long and Short. Values are passed each repaint from the main panel.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(64, 240)
        self.entry = 0
        self.stop = 0
        self.target = 0
        self.current = 0
        self.is_long = True
        self.setWindowTitle("Profit Bar")

    def setValues(self, entry, stop, target, current, is_long):
        self.entry = entry
        self.stop = stop
        self.target = target
        self.current = current
        self.is_long = is_long
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Background card
        rect = self.rect().adjusted(10, 10, -10, -10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(40, 40, 40))
        p.drawRoundedRect(rect, 10, 10)

        if self.entry == 0:
            return

        # Determine min/max for scale based on stop/target
        lo = min(self.stop, self.target)
        hi = max(self.stop, self.target)
        rng = (hi - lo) if hi != lo else 1.0

        # Bar area inside card
        bar = rect.adjusted(18, 12, -18, -12)

        # === Constant color zones ===
        def y_for(price):
            return bar.top() + (1.0 - (price - lo) / rng) * bar.height()

        y_stop   = y_for(self.stop)
        y_entry  = y_for(self.entry)
        y_target = y_for(self.target)

        # Helper to draw a vertical band between two y's in a solid color
        def draw_band(y1, y2, color_hex):
            top = min(y1, y2)
            h   = abs(y2 - y1)
            if h <= 0:
                return
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color_hex))
            p.drawRect(QRectF(bar.left(), top, bar.width(), h))

        # Fill the card background inside the bar area first (keeps rounded card look)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(40, 40, 40))
        p.drawRoundedRect(bar, 8, 8)

        # Red band between Stop ↔ Entry, Green band between Entry ↔ Target
        draw_band(y_stop, y_entry, "#FF5555")  # SL zone (red)
        draw_band(y_entry, y_target, "#B7FF5E")  # TP zone (green)
        
        # --- Dynamic band between ENTRY and CURRENT ---
        y_entry   = y_for(self.entry)
        y_current = y_for(self.current)

        # only draw if current ≠ entry
        if abs(y_entry - y_current) > 1:
            top = min(y_entry, y_current)
            h   = abs(y_entry - y_current)
            
            # choose color based on position
            if self.current > self.entry:
                color = QColor("#50FA7B")   # light green (profit zone)
            elif self.current < self.entry and self.current > self.stop:
                color = QColor("#FFEF60")   # yellow (between SL and entry)
            else:
                color = QColor("#FF5555")   # optional: red if below stop

            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRect(QRectF(bar.left(), top, bar.width(), h))


        # Optional: thin divider line at entry (yellow)
        p.setPen(QPen(QColor("#F1FA8C"), 2))
        p.drawLine(QLineF(bar.left(), y_entry, bar.right(), y_entry))


        # Draw lines for stop/entry/target (subtle grid if you want it)
        pen_grid = QPen(QColor(90,90,90)); pen_grid.setWidthF(1.0)
        p.setPen(pen_grid)
        for pr in (self.stop, self.entry, self.target):
            y = y_for(pr)
            p.drawLine(QLineF(bar.left(), y, bar.right(), y))

        # Labels (set per line color)
        font = p.font(); font.setPointSize(9); font.setBold(True); p.setFont(font)

        # SL label (red)
        p.setPen(QColor("#E5FF55"))
        p.drawText(bar.left()+4, int(y_stop)-2, f"SL {self.stop:.4g}")

        # EN label (yellow)
        p.setPen(QColor("#202020"))
        p.drawText(bar.left()+4, int(y_entry)-2, f"EN {self.entry:.4g}")

        # TP label (green)
        p.setPen(QColor("#FF7AD3"))
        p.drawText(bar.left()+4, int(y_target)-2, f"TP {self.target:.4g}")


        # Labels
        p.setPen(QColor("#FF7AD3"))  # Dracula foreground
        font = p.font(); font.setPointSize(9);font.setBold(True); p.setFont(font); 
        def draw_label(text, y):
            p.drawText(bar.left()+4, int(y)-2, text)
            draw_label(f"SL {self.stop:.4g}", y_for(self.stop))
            draw_label(f"EN {self.entry:.4g}", y_for(self.entry))
            draw_label(f"TP {self.target:.4g}", y_for(self.target))

        # Current price marker
        ycur = y_for(self.current)
        pen_cur = QPen(QColor(140, 200, 255)); pen_cur.setWidth(2)
        p.setPen(pen_cur)
        p.drawLine(QLineF(bar.left()-4, ycur, bar.right()+4, ycur))
        p.setPen(QColor("#3A3A3A"))  # Dracula purple accent
        p.drawText(bar.right()-42, int(ycur)-4, f"{self.current:.4g}")

        # R multiple indicator at right side (optional): position current relative to entry per-risk
        per_risk = abs(self.entry - self.stop)
        if per_risk > 0:
            r_mult = ((self.current - self.entry) if self.is_long else (self.entry - self.current)) / per_risk
            p.setPen(QColor(180, 220, 255))
            p.drawText(bar.left(), bar.bottom()+16, f"R = {r_mult:.2f}")
        p.end()


class OverlayWindow(QWidget):
    """A tiny floating window that shows only the ProfitBar."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Profit Overlay")
        self.setWindowFlags(self.windowFlags() | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.bar = ProfitBar()
        lay = QVBoxLayout(self); lay.setContentsMargins(6,6,6,6); lay.addWidget(self.bar)
        self.resize(120, 320)

    def update_values(self, entry, stop, target, current, is_long):
        self.bar.setValues(entry, stop, target, current, is_long)

# ---------------- Main Panel ----------------
class TPSLWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TP/SL Calculator")
        self.setFont(QFont("Segoe UI", 10))
        self.setWindowIcon(QIcon("tpslcalculator_Icon.svg"))

        self.settings = QSettings(APP_ORG, APP_NAME)
        self.state = DEFAULTS.copy()
        self.load_settings()

        self.overlay = OverlayWindow()  # created up front; hidden until toggled
        self.overlay.hide()

        self.build_ui()
        self.apply_always_on_top(self.state["always_on_top"])
        self.recalc()

        # small timer to keep overlay responsive if user drags sliders fast
        self._overlay_timer = QTimer(self)
        self._overlay_timer.setInterval(80)
        self._overlay_timer.timeout.connect(self.push_to_overlay)
        self._overlay_timer.start()

    # ---------- UI ----------
    def build_ui(self):
        grid = QGridLayout()
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        title = QLabel("Trading Profit / TP–SL Planner")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))

        self.btn_save = QPushButton("Save")
        self.btn_reset = QPushButton("Reset")
        self.chk_top = QCheckBox("On Top")
        self.chk_top.setChecked(self.state["always_on_top"])
        self.btn_overlay = QPushButton("Overlay")

        self.btn_save.clicked.connect(self.save_settings)
        self.btn_reset.clicked.connect(self.reset_defaults)
        self.chk_top.stateChanged.connect(lambda _: self.apply_always_on_top(self.chk_top.isChecked()))
        self.btn_overlay.clicked.connect(self.toggle_overlay)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.btn_overlay)
        header.addWidget(self.btn_save)
        header.addWidget(self.btn_reset)
        header.addWidget(self.chk_top)

        # Inputs group
        inputs = QGridLayout()
        r = 0
        inputs.addWidget(QLabel("Side"), r, 0)
        self.cmb_side = QComboBox(); self.cmb_side.addItems(["Long","Short"])
        self.cmb_side.setCurrentText(self.state["side"]) ; inputs.addWidget(self.cmb_side, r, 1)
        inputs.addWidget(QLabel("Tick"), r, 2)
        self.spn_tick = QDoubleSpinBox(); self.spn_tick.setDecimals(5); self.spn_tick.setRange(0.00001, 10000); self.spn_tick.setSingleStep(0.01); self.spn_tick.setValue(self.state["tick"]) ; inputs.addWidget(self.spn_tick, r, 3)

        r += 1
        inputs.addWidget(QLabel("Entry"), r, 0)
        self.spn_entry = QDoubleSpinBox(); self.spn_entry.setDecimals(4); self.spn_entry.setRange(0, 1e9); self.spn_entry.setValue(self.state["entry"]) ; inputs.addWidget(self.spn_entry, r, 1)
        inputs.addWidget(QLabel("Current"), r, 2)
        self.spn_curr = QDoubleSpinBox(); self.spn_curr.setDecimals(4); self.spn_curr.setRange(0, 1e9); self.spn_curr.setValue(self.state["current"]) ; inputs.addWidget(self.spn_curr, r, 3)

        r += 1
        inputs.addWidget(QLabel("Shares"), r, 0)
        self.spn_shares = QSpinBox(); self.spn_shares.setRange(0, 10_000_000); self.spn_shares.setValue(self.state["shares"]) ; inputs.addWidget(self.spn_shares, r, 1)
        inputs.addWidget(QLabel("Fees flat/share"), r, 2)
        fee_box = QHBoxLayout()
        self.spn_flat = QDoubleSpinBox(); self.spn_flat.setRange(0, 1e9); self.spn_flat.setDecimals(2); self.spn_flat.setValue(self.state["flat_fee"]) ; fee_box.addWidget(self.spn_flat)
        self.spn_ps = QDoubleSpinBox(); self.spn_ps.setRange(0, 1e6); self.spn_ps.setDecimals(4); self.spn_ps.setValue(self.state["per_share_fee"]) ; fee_box.addWidget(self.spn_ps)
        fee_wrap = QWidget(); fee_wrap.setLayout(fee_box)
        inputs.addWidget(fee_wrap, r, 3)

        inputs_box = QGroupBox("Inputs")
        inputs_box.setLayout(inputs)

        # Sliders group
        sliders = QGridLayout()
        r = 0
        self.lbl_stop_pct = QLabel("Stop % (from entry):")
        self.sld_stop = QSlider(Qt.Horizontal); self.sld_stop.setRange(-5000, 5000); self.sld_stop.setSingleStep(50); self.sld_stop.setValue(int(self.state["stop_pct"]*100))
        sliders.addWidget(self.lbl_stop_pct, r, 0); sliders.addWidget(self.sld_stop, r, 1)
        r += 1
        self.lbl_tgt_pct = QLabel("Target % (from entry):")
        self.sld_tgt = QSlider(Qt.Horizontal); self.sld_tgt.setRange(-5000, 10000); self.sld_tgt.setSingleStep(50); self.sld_tgt.setValue(int(self.state["target_pct"]*100))
        sliders.addWidget(self.lbl_tgt_pct, r, 0); sliders.addWidget(self.sld_tgt, r, 1)

        quick = QHBoxLayout()
        self.btn_1r = QPushButton("TP = 1R"); self.btn_2r = QPushButton("TP = 2R"); self.btn_3r = QPushButton("TP = 3R")
        quick.addWidget(self.btn_1r); quick.addWidget(self.btn_2r); quick.addWidget(self.btn_3r)
        sliders_box = QGroupBox("Targets & Stop")
        sliders_v = QVBoxLayout(); sliders_v.addLayout(sliders); sliders_v.addLayout(quick)
        sliders_box.setLayout(sliders_v)

        # Outputs group (and embedded small bar preview)
        outputs = QGridLayout(); r = 0
        self.out_stop = QLabel("Stop: — | % —"); outputs.addWidget(self.out_stop, r, 0)
        self.preview_bar = ProfitBar(); outputs.addWidget(self.preview_bar, r, 1, 4, 1)
        r += 1
        self.out_tgt = QLabel("Target: — | % —"); outputs.addWidget(self.out_tgt, r, 0)
        r += 1
        self.out_rr = QLabel("Risk ¥ — | Reward ¥ — | R — | RR —"); outputs.addWidget(self.out_rr, r, 0)
        r += 1
        self.out_pl = QLabel("Unrealized P/L: — | Breakeven: —"); outputs.addWidget(self.out_pl, r, 0)
        outputs_box = QGroupBox("Outputs")
        outputs_box.setLayout(outputs)

        # Assemble
        grid.addLayout(header, 0, 0)
        grid.addWidget(inputs_box, 1, 0)
        grid.addWidget(sliders_box, 2, 0)
        grid.addWidget(outputs_box, 3, 0)

        self.setLayout(grid)

        # Signals
        for w in [self.cmb_side, self.spn_tick, self.spn_entry, self.spn_curr, self.spn_shares, self.spn_flat, self.spn_ps]:
            if isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self.recalc)
            else:
                w.valueChanged.connect(self.recalc)
        self.sld_stop.valueChanged.connect(self.recalc)
        self.sld_tgt.valueChanged.connect(self.recalc)
        self.btn_1r.clicked.connect(lambda: self.set_tp_R(1))
        self.btn_2r.clicked.connect(lambda: self.set_tp_R(2))
        self.btn_3r.clicked.connect(lambda: self.set_tp_R(3))

    # ---------- logic ----------
    def round_tick(self, price, tick):
        if tick <= 0: return price
        steps = round(price / tick)
        return steps * tick

    def stop_price_and_risk(self, entry, stop_pct, long, tick):
        sp = entry * (1.0 + stop_pct) if long else entry * (1.0 - stop_pct)
        sp = self.round_tick(sp, tick)
        return sp, abs(entry - sp)

    def target_price(self, entry, tgt_pct, long, tick):
        tp = entry * (1.0 + tgt_pct) if long else entry * (1.0 - tgt_pct)
        return self.round_tick(tp, tick)

    def set_tp_R(self, R):
        entry = self.spn_entry.value()
        tick = self.spn_tick.value()
        long = (self.cmb_side.currentText() == "Long")
        stop_pct = self.sld_stop.value() / 10000.0
        stop_price, per_risk = self.stop_price_and_risk(entry, stop_pct, long, tick)
        if per_risk <= 0: return
        sign = 1 if long else -1
        tgt_price = entry + sign * R * per_risk
        tgt_pct = (tgt_price / entry - 1.0) * 100
        self.sld_tgt.setValue(int(tgt_pct * 100))
        self.recalc()

    def recalc(self):
        entry = self.spn_entry.value()
        curr = self.spn_curr.value()
        shares = self.spn_shares.value()
        tick = self.spn_tick.value()
        long = (self.cmb_side.currentText() == "Long")
        stop_pct = self.sld_stop.value() / 10000.0
        tgt_pct = self.sld_tgt.value() / 10000.0
        flat_fee = self.spn_flat.value()
        ps_fee = self.spn_ps.value()

        stop_price, per_risk = self.stop_price_and_risk(entry, stop_pct, long, tick)
        tgt_price = self.target_price(entry, tgt_pct, long, tick)

        risk_amt = per_risk * shares
        reward_ps = (tgt_price - entry) if long else (entry - tgt_price)
        reward_amt = reward_ps * shares
        R = 0.0 if per_risk == 0 else reward_ps / per_risk
        RR = 0.0 if risk_amt == 0 else reward_amt / risk_amt

        unreal_ps = (curr - entry) if long else (entry - curr)
        unreal_amt = unreal_ps * shares
        fees = flat_fee + ps_fee * shares
        unreal_net = unreal_amt - fees
        be_shift = fees / shares if shares > 0 else 0.0
        be_price = entry + be_shift if long else entry - be_shift
        be_price = self.round_tick(be_price, tick)

        spct = (stop_price/entry - 1.0) * (100 if long else -100)
        tpct = (tgt_price/entry - 1.0) * (100 if long else -100)

        self.out_stop.setText(f"Stop: {stop_price:.6g} | % {spct:.2f}")
        self.out_tgt.setText(f"Target: {tgt_price:.6g} | % {tpct:.2f}")
        self.out_rr.setText(f"Risk ¥ {risk_amt:.0f} | Reward ¥ {reward_amt:.0f} | R {R:.2f} | RR {RR:.2f}")
        self.out_pl.setText(f"Unrealized P/L: ¥{unreal_net:.0f} (gross {unreal_amt:.0f}) | Breakeven {be_price:.6g}")

        # Update embedded preview bar
        self.preview_bar.setValues(entry, stop_price, tgt_price, curr, long)

    # ---------- settings & overlay ----------
    def load_settings(self):
        for k, v in DEFAULTS.items():
            self.state[k] = self.settings.value(k, v, type=type(v))

    def save_settings(self):
        self.settings.setValue("entry", self.spn_entry.value())
        self.settings.setValue("current", self.spn_curr.value())
        self.settings.setValue("shares", self.spn_shares.value())
        self.settings.setValue("tick", self.spn_tick.value())
        self.settings.setValue("side", self.cmb_side.currentText())
        self.settings.setValue("stop_pct", self.sld_stop.value()/100.0)
        self.settings.setValue("target_pct", self.sld_tgt.value()/100.0)
        self.settings.setValue("flat_fee", self.spn_flat.value())
        self.settings.setValue("per_share_fee", self.spn_ps.value())
        self.settings.setValue("always_on_top", self.chk_top.isChecked())

    def reset_defaults(self):
        self.spn_entry.setValue(DEFAULTS["entry"])
        self.spn_curr.setValue(DEFAULTS["current"])
        self.spn_shares.setValue(DEFAULTS["shares"])
        self.spn_tick.setValue(DEFAULTS["tick"])
        self.cmb_side.setCurrentText(DEFAULTS["side"])
        self.sld_stop.setValue(int(DEFAULTS["stop_pct"]*100))
        self.sld_tgt.setValue(int(DEFAULTS["target_pct"]*100))
        self.spn_flat.setValue(DEFAULTS["flat_fee"])
        self.spn_ps.setValue(DEFAULTS["per_share_fee"])
        self.chk_top.setChecked(DEFAULTS["always_on_top"])
        self.apply_always_on_top(DEFAULTS["always_on_top"])
        self.recalc()

    def apply_always_on_top(self, on):
        flags = self.windowFlags()
        if on:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def toggle_overlay(self):
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            # Position near the main window
            geo = self.geometry()
            self.overlay.move(geo.right() + 12, geo.top())
            self.push_to_overlay()
            self.overlay.show()

    def push_to_overlay(self):
        if not self.overlay.isVisible():
            return
        entry = self.spn_entry.value()
        tick = self.spn_tick.value()
        long = (self.cmb_side.currentText() == "Long")
        stop_pct = self.sld_stop.value() / 10000.0
        tgt_pct = self.sld_tgt.value() / 10000.0
        stop_price, _ = self.stop_price_and_risk(entry, stop_pct, long, tick)
        tgt_price = self.target_price(entry, tgt_pct, long, tick)
        curr = self.spn_curr.value()
        self.overlay.update_values(entry, stop_price, tgt_price, curr, long)

# ---------- theming ----------

def enable_dracula(app):
    app.setStyle("Fusion")
    palette = QPalette()
    bg = QColor("#282A36")
    fg = QColor("#F8F8F2")
    accent = QColor("#6272A4")
    btn = QColor("#44475A")
    sel = QColor("#6272A4")
    link = QColor("#8BE9FD")

    palette.setColor(QPalette.Window, bg)
    palette.setColor(QPalette.WindowText, fg)
    palette.setColor(QPalette.Base, QColor("#1E1F29"))
    palette.setColor(QPalette.AlternateBase, QColor("#343746"))
    palette.setColor(QPalette.ToolTipBase, fg)
    palette.setColor(QPalette.ToolTipText, fg)
    palette.setColor(QPalette.Text, fg)
    palette.setColor(QPalette.Button, btn)
    palette.setColor(QPalette.ButtonText, fg)
    palette.setColor(QPalette.BrightText, QColor("#FF5555"))
    palette.setColor(QPalette.Highlight, sel)
    palette.setColor(QPalette.HighlightedText, fg)
    palette.setColor(QPalette.Link, link)
    palette.setColor(QPalette.LinkVisited, QColor("#BD93F9"))

    app.setPalette(palette)


if __name__ == "__main__":
    # Windows: set AppUserModelID so taskbar uses your icon
    if sys.platform.startswith("win"):
        import ctypes
        myappid = "TPSLWidget.1.0"  # any unique string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # Hi-DPI attrs MUST be set before creating QApplication
    from PyQt5.QtCore import Qt, QCoreApplication
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Create the app
    app = QApplication(sys.argv)

    # Global app icon (shows in taskbar/alt-tab/title bar)
    from PyQt5.QtGui import QIcon
    app.setWindowIcon(QIcon("tpslcalculator_Icon.ico"))  # ensure the file exists

    # Theme + window
    enable_dracula(app)
    w = TPSLWidget()
    w.resize(560, 460)
    w.show()

    sys.exit(app.exec_())

