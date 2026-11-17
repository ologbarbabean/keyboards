from pynput import keyboard, mouse
import threading

# Controllers for mouse and keyboard
mouse_ctrl = mouse.Controller()

# Track state
is_mouse_held = False
current_keys = set()
lock = threading.Lock()

# Target combination: L + M + B (case-insensitive)
TARGET_HOTKEY = {
    keyboard.KeyCode.from_char('l'),
    keyboard.KeyCode.from_char('m'),
    keyboard.KeyCode.from_char('b')
}

def toggle_left_click():
    global is_mouse_held
    with lock:
        if is_mouse_held:
            mouse_ctrl.release(mouse.Button.left)
            is_mouse_held = False
            print("[STATUS] Left mouse button RELEASED.")
        else:
            mouse_ctrl.press(mouse.Button.left)
            is_mouse_held = True
            print("[STATUS] Left mouse button HELD DOWN.")

def on_press(key):
    # Normalize character keys to lowercase
    if hasattr(key, 'char') and key.char:
        norm_key = keyboard.KeyCode.from_char(key.char.lower())
    else:
        norm_key = key

    current_keys.add(norm_key)

    # Check if all target keys are pressed
    if TARGET_HOTKEY.issubset(current_keys):
        toggle_left_click()

def on_release(key):
    if hasattr(key, 'char') and key.char:
        norm_key = keyboard.KeyCode.from_char(key.char.lower())
    else:
        norm_key = key

    current_keys.discard(norm_key)

    # Stop listener on Escape
    if key == keyboard.Key.esc:
        if is_mouse_held:
            mouse_ctrl.release(mouse.Button.left)
        print("Exiting...")
        return False

print("Script running.")
print("Press 'L + M + B' simultaneously to toggle Left Click.")
print("Press 'Esc' to exit.")

while(True):
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
        