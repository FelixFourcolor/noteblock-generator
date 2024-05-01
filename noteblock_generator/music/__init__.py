from . import compiler, loader, parser, validator


def compile(src_path: str):  # noqa: A001
    raw_data = loader.load(src_path)
    validated_data = validator.validate(raw_data)
    parsed_data = parser.parse(validated_data)
    return compiler.compile(parsed_data)
