import builtins
from sys import stdin

APP_NAME = "noteblock-generator"
__version__ = "0.2.99"


if not stdin.isatty():

    def input_abort(*args, **kwargs):
        raise EOFError

    builtins.input = input_abort
