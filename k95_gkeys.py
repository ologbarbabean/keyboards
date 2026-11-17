"""
k95_gkeys.py - program the six G-keys of a Corsair K95 RGB Platinum XT without iCUE.

Reads raw reports from the keyboard's vendor interface (0xFF42, interface 2) and runs
the action you set for each G-key in k95_gkeys.json (created on first run).

Setup (Windows, iCUE and other Corsair software closed):
    pip install hidapi pyautogui pystray pillow
    python k95_gkeys.py              # run the mapper (Ctrl+C to stop)
    python k95_gkeys.py --pid 0x1B89 # only needed if your PID differs

Config actions (edit k95_gkeys.json):
    {"type": "log"}                                  print only (default)
    {"type": "hotkey", "keys": ["ctrl", "shift", "m"]}
    {"type": "text", "text": "hello", "enter": false}
    {"type": "run", "args": ["notepad.exe"]}
"""
import json
import os
import subprocess
import sys
import threading
import time

VID = 0x1B1C
PID = 0x1B89
VENDOR_PAGE = 0xFF42
VENDOR_USAGE = 0x0002
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "k95_gkeys.json")

# (byte index in the 64-byte report, bit mask) for each key, from the probe output.
# Order assumes you pressed G1..G6 in order during the probe; the first run prints
# the names so you can confirm.
KEYMAP = {
    "G1": (18, 0x08),
    "G2": (18, 0x10),
    "G3": (18, 0x20),
    "G4": (18, 0x40),
    "G5": (18, 0x80),
    "G6": (19, 0x01),
}


def pressed_set(report):
    """Return the set of G-key names currently held in this report."""
    if len(report) < 20 or report[1] != 0x02:
        return set()
    return {name for name, (idx, mask) in KEYMAP.items() if report[idx] & mask}


def load_config():
    if not os.path.exists(CONFIG):
        default = {name: {"type": "log"} for name in KEYMAP}
        with open(CONFIG, "w") as f:
            json.dump(default, f, indent=2)
        print("Created %s - edit it to assign actions." % CONFIG)
        return default
    with open(CONFIG) as f:
        return json.load(f)


def run_action(name, action):
    kind = action.get("type", "log")
    if kind == "log":
        print("%s pressed (no action set)" % name)
    elif kind == "hotkey":
        import pyautogui
        pyautogui.hotkey(*action["keys"])
        print("%s -> hotkey %s" % (name, "+".join(action["keys"])))
    elif kind == "text":
        import pyautogui
        pyautogui.write(action["text"], interval=0.01)
        if action.get("enter"):
            pyautogui.press("enter")
        print("%s -> typed text" % name)
    elif kind == "run":
        subprocess.Popen(action["args"])
        print("%s -> ran %s" % (name, action["args"]))
    else:
        print("%s: unknown action type %r" % (name, kind))


def find_device(pid):
    import hid
    for d in hid.enumerate(VID, pid):
        if d["usage_page"] == VENDOR_PAGE and d["usage"] == VENDOR_USAGE:
            return d["path"]
    return None


# ---- shared state between the HID worker thread and the tray icon ----
stop_event = threading.Event()
state = {"status": "Searching for keyboard..."}
config_lock = threading.Lock()
config = {}
icon = None


def set_status(text):
    state["status"] = text
    if icon is not None:
        icon.title = "K95 G-keys: " + text
        try:
            icon.update_menu()
        except Exception:
            pass


def reload_config(*_):
    global config
    try:
        new = load_config()
    except Exception as e:
        print("Config error: %s" % e)
        set_status("Config error (see k95_gkeys.json)")
        return
    with config_lock:
        config = new
    print("Config reloaded.")


def worker(pid):
    import hid
    held = set()
    while not stop_event.is_set():
        path = find_device(pid)
        if path is None:
            set_status("Keyboard not found")
            stop_event.wait(2)
            continue
        h = hid.device()
        try:
            h.open_path(path)
            set_status("Connected")
            while not stop_event.is_set():
                report = h.read(64, 100)  # 100 ms timeout so we can notice quit
                if not report:
                    continue
                now = pressed_set(report)
                for name in sorted(now - held):  # newly pressed
                    with config_lock:
                        action = config.get(name, {"type": "log"})
                    try:
                        run_action(name, action)
                    except Exception as e:
                        print("%s action failed: %s" % (name, e))
                held = now
        except OSError as e:
            print("Lost connection (%s), reconnecting..." % e)
            held = set()
            set_status("Reconnecting...")
            stop_event.wait(2)
        finally:
            try:
                h.close()
            except Exception:
                pass


def make_icon_image():
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, 61, 61), radius=12, fill=(250, 190, 0, 255))
    d.text((19, 22), "G", fill=(20, 20, 20, 255))
    # draw a bigger G with simple shapes so it reads at tray size
    d.ellipse((14, 14, 50, 50), outline=(20, 20, 20, 255), width=6)
    d.rectangle((32, 28, 50, 36), fill=(20, 20, 20, 255))
    d.rectangle((38, 22, 50, 28), fill=(250, 190, 0, 255))
    return img


def open_config(*_):
    os.startfile(CONFIG)


def quit_app(*_):
    stop_event.set()
    icon.stop()


def main():
    global icon
    import pystray

    pid = PID
    if "--pid" in sys.argv:
        pid = int(sys.argv[sys.argv.index("--pid") + 1], 0)

    reload_config()
    threading.Thread(target=worker, args=(pid,), daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem(lambda item: state["status"], None, enabled=False),
        pystray.MenuItem("Reload config", reload_config),
        pystray.MenuItem("Open config file", open_config),
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("k95_gkeys", make_icon_image(), "K95 G-keys: " + state["status"], menu)
    icon.run()  # blocks until Quit


if __name__ == "__main__":
    main()