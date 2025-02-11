import fcntl
import termios
import sys
import os
import time

class keys:
    LEFT = "\x1b[D"
    RIGHT = "\x1b[C"
    ENTER = "\n"

class NonBlockingInput(object):

    def __enter__(self):
        # canonical mode, no echo
        self.old = termios.tcgetattr(sys.stdin)
        new = termios.tcgetattr(sys.stdin)
        new[3] = new[3] & ~(termios.ICANON | termios.ECHO)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new)

        # set for non-blocking io
        self.orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, self.orig_fl | os.O_NONBLOCK)

    def __exit__(self, *args):
        # restore terminal to previous state
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, self.orig_fl)

if __name__ == "__main__":
    with NonBlockingInput():
        while True:
            c = sys.stdin.read(3)
            print('tick', repr(c))
            time.sleep(0.1)
