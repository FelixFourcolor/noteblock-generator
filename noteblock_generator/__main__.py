import sys

from .cli import UserError, logger, parse_args


def main():
    try:
        args = parse_args()
        from .generator import Generator

        Generator(**args)()
    except UserError as e:
        logger.error(f"ERROR - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
