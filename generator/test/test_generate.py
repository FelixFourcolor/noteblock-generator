from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from msgspec import json

from noteblock_generator.cli.args import Align, Dimension, Facing, Tilt, Walkable
from noteblock_generator.core.generator import Generator
from noteblock_generator.data.file_utils import hash_files
from noteblock_generator.data.loader import load

if TYPE_CHECKING:
    from noteblock_generator.core.chunks import ChunksData
    from noteblock_generator.core.session import GeneratingSession


class MockWorld:
    def validate_bounds(self, *args, **kwargs):
        pass

    def write(self, chunks: ChunksData, *args, **kwargs):
        self.chunks = chunks
        yield


class MockSession:
    def __init__(self, *args, **kwargs):
        self.world = MockWorld()

    def __enter__(self):
        return self.world

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def serialize_chunks(chunks: ChunksData):
    serialized_chunks = {}

    for (cx, cz), edits in chunks.items():
        chunk_key = f"{cx} {cz}"

        serialized_edits = {}
        for (x, y, z), block in edits.items():
            block_key = f"{x} {y} {z}"
            serialized_edits[block_key] = block

        serialized_chunks[chunk_key] = serialized_edits

    return serialized_chunks


def get_test_projects():
    projects_dir = Path(__file__).parent / "data" / "projects"
    if not projects_dir.exists():
        return []
    return [d.name for d in projects_dir.iterdir() if d.is_dir()]


@pytest.mark.parametrize("project_name", get_test_projects())
def test_generate(project_name: str):
    projects_dir = Path(__file__).parent / "data" / "projects"
    project_path = projects_dir / project_name

    data_file = project_path / "input" / "data.json"
    params_file = project_path / "input" / "params.json"

    verified_file = project_path / "output" / "verified.json"
    received_file = project_path / "output" / "received.json"

    if not data_file.exists():
        pytest.skip(f"Input data not found for {project_name}")
    if not params_file.exists():
        pytest.fail(f"Params file not found for {project_name}")

    data = load(data_file)
    session = MockSession()
    with open(params_file, "r") as f:
        params = json.decode(f.read())
    Generator(
        session=cast("GeneratingSession", session),
        coordinates=params["coordinates"],
        dimension=Dimension(params["dimension"]),
        facing=Facing(params["facing"]),
        tilt=Tilt(params["tilt"]),
        align=Align(params["align"]),
        walkable=Walkable(params["walkable"]),
        theme=params["theme"],
        preserve_terrain=params["preserve_terrain"],
    ).generate(data)

    received_file.unlink(missing_ok=True)
    with open(received_file, "wb") as f:
        captured_data = serialize_chunks(session.world.chunks)
        encoded = json.encode(captured_data, order="deterministic")
        formatted = json.format(encoded, indent=2)
        f.write(formatted)

    if not verified_file.exists():
        pytest.skip("Verified output not found")

    verified_hash = hash_files(verified_file)
    received_hash = hash_files(received_file)
    assert verified_hash is not None, "Could not hash verified output"
    assert received_hash is not None, "Could not hash received output"
    assert verified_hash == received_hash, "Received output does not match verified"

    received_file.unlink()
