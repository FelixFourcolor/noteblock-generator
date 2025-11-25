import builtins
import logging
from sys import stdin

APP_NAME = "noteblock-generator"
__version__ = "0.3.0"


logging.disable()  # disable amulet's logging


if not stdin.isatty():

    def input_abort(*args, **kwargs):
        raise EOFError

    builtins.input = input_abort
