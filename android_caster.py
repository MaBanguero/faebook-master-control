import sys
import subprocess
import re
import time
import psutil
import os

# --- CRITICAL FIX FOR LINUX WINDOW EMBEDDING ---
if sys.platform.startswith('linux'):
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    os.environ["SDL_VIDEODRIVER"] = "x11"

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QLabel, QVBoxLayout, QScrollArea, QFrame
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QWindow

# --- CONDITIONAL IMPORTS ---
IS_LINUX = sys.platform.startswith('linux')
if IS_LINUX:
    from Xlib import display
    from Xlib.error import XError
else:
    import pygetwindow as gw


def get_connected_devices():
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True,
                                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                                encoding='utf-8')
        devices = []
        pattern = re.compile(r'^([a-zA-Z0-9\._:-]+)\s+device$')
        for line in result.stdout.strip().split('\n'):
            match = pattern.match(line.strip())
            if match:
                devices.append(match.group(1))
        return devices
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error with ADB: {e}")
        return []


class ScreenWidget(QWidget):
    def __init__(self, serial, parent=None):
        super().__init__(parent)
        self.serial = serial
        self.process = None
        self.container = None
        self.window_title = f"scrcpy_{self.serial}"

        self.setMinimumSize(300, 500)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_layout = QVBoxLayout(self.frame)
        self.layout.addWidget(self.frame)

        self.serial_label = QLabel(f"Device: {self.serial}")
        self.serial_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.serial_label.setStyleSheet("font-weight: bold; padding: 5px;")
        self.frame_layout.addWidget(self.serial_label)

        self.placeholder_label = QLabel("Waiting to connect...")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_layout.addWidget(self.placeholder_label, stretch=1)

    def find_window_id_for_linux(self):
        try:
            d = display.Display()
            root = d.screen().root
            window_ids = root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), d.intern_atom('WINDOW')).value

            for win_id in window_ids:
                try:
                    window = d.create_resource_object('window', win_id)
                    wm_name = window.get_wm_name()
                    if wm_name:
                        if isinstance(wm_name, bytes):
                            wm_name = wm_name.decode('utf-8', errors='ignore')
                        if self.window_title in wm_name:
                            return win_id
                except (XError, AttributeError):
                    continue
            return None
        except Exception as e:
            return None

    def find_window_id_for_others(self):
        try:
            windows = gw.getWindowsWithTitle(self.window_title)
            if windows:
                return windows[0]._hWnd
            return None
        except Exception:
            return None

    def start_stream(self):
        if self.process:
            return

        self.placeholder_label.setText("Starting scrcpy...")

        # Parámetros básicos para máxima compatibilidad
        command = [
            'scrcpy',
            '--serial', self.serial,
            '--window-borderless',
            '--window-title', self.window_title,
            '--max-size', '800'  # Importante limitar resolución para tantos dispositivos
        ]

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,  # Capturamos el error
            text=True,
            creationflags=creationflags
        )

        QTimer.singleShot(500, self.check_for_window)

    def check_for_window(self, attempt=1):
        if not self.process or self.process.poll() is not None:
            # LECTURA DE ERRORES: Ver exactamente por qué falla scrcpy
            error_msg = self.process.stderr.read() if self.process and self.process.stderr else "Unknown error"
            print(f"Scrcpy process died for {self.serial}.\nREASON: {error_msg.strip()}")
            self.placeholder_label.setText("Scrcpy crashed. Check console.")
            self.stop_stream()
            return

        target_id = None
        if IS_LINUX:
            target_id = self.find_window_id_for_linux()
        else:
            target_id = self.find_window_id_for_others()

        if target_id:
            print(f"Window found for {self.serial}: {target_id}")
            self.embed_window(target_id)
        elif attempt < 40:
            QTimer.singleShot(500, lambda: self.check_for_window(attempt + 1))
        else:
            print(f"Timeout finding window for {self.serial}")
            self.placeholder_label.setText("Timeout. No se pudo capturar.")
            self.stop_stream()

    def embed_window(self, win_id):
        try:
            foreign_window = QWindow.fromWinId(win_id)
            if not foreign_window:
                raise Exception("Could not create QWindow from ID")

            self.container = QWidget.createWindowContainer(foreign_window, self.frame)

            if self.placeholder_label:
                self.frame_layout.removeWidget(self.placeholder_label)
                self.placeholder_label.deleteLater()
                self.placeholder_label = None

            self.frame_layout.addWidget(self.container, stretch=1)
            self.container.show()

        except Exception as e:
            print(f"Error embedding window: {e}")
            self.stop_stream()

    def stop_stream(self):
        if self.process:
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            finally:
                self.process = None


class UnifiedCasterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AndroidCast - Unified Panel")
        self.setGeometry(50, 50, 1600, 900)

        self.screen_widgets = {}
        self.COLUMNS = 4

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.setCentralWidget(self.scroll_area)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.scroll_area.setWidget(self.grid_container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_devices)
        self.timer.start(5000)

        self.update_devices()

    def update_devices(self):
        current_devices = get_connected_devices()
        connected_serials = set(current_devices)
        active_serials = set(self.screen_widgets.keys())

        new_serials = connected_serials - active_serials

        # FIX CRÍTICO: Delay para que no se lancen 18 procesos en el mismo milisegundo
        delay_ms = 0
        for serial in new_serials:
            print(f"Adding device: {serial} (Will start in {delay_ms}ms)")
            screen_widget = ScreenWidget(serial)
            self.screen_widgets[serial] = screen_widget

            # Disparar con retraso escalonado (1 segundo entre cada dispositivo)
            QTimer.singleShot(delay_ms, screen_widget.start_stream)
            delay_ms += 1000

        disconnected_serials = active_serials - connected_serials
        for serial in disconnected_serials:
            print(f"Removing device: {serial}")
            widget = self.screen_widgets.pop(serial)
            widget.stop_stream()
            widget.deleteLater()

        if new_serials or disconnected_serials:
            self.rearrange_grid()

    def rearrange_grid(self):
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)

        serials = sorted(self.screen_widgets.keys())
        for i, serial in enumerate(serials):
            row = i // self.COLUMNS
            col = i % self.COLUMNS
            self.grid_layout.addWidget(self.screen_widgets[serial], row, col)

    def closeEvent(self, event):
        for widget in self.screen_widgets.values():
            widget.stop_stream()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UnifiedCasterApp()
    window.show()
    sys.exit(app.exec())