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
            " ": "SPACE",
            "\n": "ENTER",
    }
    def getch():
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            k = sys.stdin.read(1)
            if k == "\x1b":
                k += sys.stdin.read(2)
            return __KEYS__.get(k, k)
    def restore_settings():
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    old_settings = termios.tcgetattr(sys.stdin)
    atexit.register(restore_settings)
    tty.setcbreak(sys.stdin.fileno())

if __name__ == "__main__":
    while True:
        k = getch()
        if k is not None:
            print(k)
