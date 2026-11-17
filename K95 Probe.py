"""
k95_probe.py - passive HID probe for a Corsair K95 RGB Platinum (VID 1B1C, PID 1B2D).

Step 1 (default): lists every HID interface the keyboard exposes, opens the ones
Windows allows, and prints raw reports as you press keys. Sends NOTHING to the keyboard.

Usage (Windows, iCUE closed):
    pip install hidapi
    python k95_probe.py            # list + listen
    python k95_probe.py --list     # list interfaces only

Press G1..G6 one at a time, pausing between presses, then Ctrl+C.
Save the whole output and paste it back.
"""
import sys
import time

try:
    import hid
except ImportError:
    sys.exit("Missing dependency. Run:  pip install hidapi")

VID = 0x1B1C
PID = 0x1B2D  # K95 RGB Platinum; override with --pid 0xXXXX if yours differs


def main():
    pid = PID
    if "--pid" in sys.argv:
        pid = int(sys.argv[sys.argv.index("--pid") + 1], 0)

    infos = [d for d in hid.enumerate(VID, 0) if d["product_id"] == pid]
    if not infos:
        print("No device with VID 1B1C / PID %04X. All Corsair HID devices seen:" % pid)
        for d in hid.enumerate(VID, 0):
            print("  PID %04X  %s" % (d["product_id"], d.get("product_string")))
        return

    print("Interfaces for %s (PID %04X):" % (infos[0].get("product_string"), pid))
    for d in infos:
        print("  iface=%s usage_page=0x%04X usage=0x%04X path=%s" % (
            d["interface_number"], d["usage_page"], d["usage"], d["path"].decode(errors="replace")))
    if "--list" in sys.argv:
        return

    handles = []
    for d in infos:
        h = hid.device()
        try:
            h.open_path(d["path"])
            h.set_nonblocking(1)
            handles.append((d, h))
            print("opened  iface=%s usage_page=0x%04X" % (d["interface_number"], d["usage_page"]))
        except Exception as e:
            print("cannot open iface=%s usage_page=0x%04X (%s)" % (d["interface_number"], d["usage_page"], e))

    if not handles:
        print("Nothing could be opened. Is iCUE or another program holding the device?")
        return

    print("\nListening. Press G1..G6 one at a time. Ctrl+C to stop.\n")
    last = {}
    try:
        while True:
            for d, h in list(handles):
                try:
                    data = h.read(64)
                except OSError as e:
                    print("read error on iface=%s page=0x%04X usage=0x%04X (%s) - skipping it" % (
                        d["interface_number"], d["usage_page"], d["usage"], e))
                    handles.remove((d, h))
                    h.close()
                    continue
                if data:
                    key = (d["interface_number"], d["usage_page"])
                    if last.get(key) != data:
                        last[key] = data
                        print("iface=%s page=0x%04X  %s" % (
                            d["interface_number"], d["usage_page"], bytes(data).hex(" ")))
            time.sleep(0.002)
    except KeyboardInterrupt:
        print("\nDone.")
    finally:
        for _, h in handles:
            h.close()


if __name__ == "__main__":
    main()