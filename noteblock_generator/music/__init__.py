from . import compiler, loader, parser


def compile(src_path: str) -> compiler.Music:  # noqa: A001
    return compiler.compile(parser.parse(loader.load(src_path)))
