import keyboard
import pyperclip
import time


def type_clipboard():
    text = pyperclip.paste()
    if text:
        # A tiny delay ensures you've released the Win+1 keys
        # before the script starts firing keystrokes
        time.sleep(0.2)

        # Types out the clipboard content
        keyboard.write(text)
        print("Typed clipboard contents.")
    else:
        print("Clipboard is empty.")


print("Operation Ghostwriter initialized.")
print("Listening in the background for 'Win + 1'. Press 'ESC' to exit.")

# Binds the hotkey to the function
keyboard.add_hotkey('Ctrl+shift+T', type_clipboard)

# Keeps the script running until you press Escape
keyboard.wait('esc')