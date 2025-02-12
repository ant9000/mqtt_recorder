try:
    import msvcrt
    import codecs
    from ctypes import windll
    __CODEPAGE__ = "cp%d" % windll.kernel32.GetConsoleOutputCP()
    __KEYS__ = {
            b"\xe0K": "LEFT",
            b"\xe0M": "RIGHT",
            b"\xe0H": "UP",
            b"\xe0P": "DOWN",
            "\x1b": "ESC",
            "\t": "TAB",
            "\x1b": "ESC",
            " ": "SPACE",
            "\r": "ENTER",
    }
    def getch():
        if msvcrt.kbhit():
            k = msvcrt.getch()
            if ord(k) in [0x00, 0xe0]:
                k += msvcrt.getch()
            else:
                k = codecs.decode(k, encoding=__CODEPAGE__)
            return __KEYS__.get(k, k)
except:
    import os
    import sys
    import select
    import tty
    import termios
    import atexit
    __KEYS__ = {
            "\x1b[D": "LEFT",
            "\x1b[C": "RIGHT",
            "\x1b[A": "UP",
            "\x1b[B": "DOWN",
            "\x1b": "ESC",
            "\t": "TAB",
            " ": "SPACE",
            "\n": "ENTER",
    }
    def getch():
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            # read up to 3 chars (arrows are represented as an escape sequence)
            k = os.read(sys.stdin.fileno(),3).decode(sys.stdin.encoding)
            return __KEYS__.get(k, k)
    def restore_settings():
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    old_settings = termios.tcgetattr(sys.stdin)
    atexit.register(restore_settings)
    tty.setcbreak(sys.stdin.fileno())

if __name__ == "__main__":
    try:
        while True:
            k = getch()
            if k is not None:
                print(k)
    except KeyboardInterrupt:
        pass
