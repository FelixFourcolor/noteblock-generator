import pytest


@pytest.fixture(autouse=True)
def mock_console(monkeypatch):
    from noteblock_generator.cli.console import Console

    for attr in dir(Console):
        if not attr.startswith("_") and callable(getattr(Console, attr)):
            monkeypatch.setattr(Console, attr, lambda *a, **k: None)


@pytest.fixture(autouse=True)
def mock_progress_bar(monkeypatch):
    from noteblock_generator.cli.progress_bar import ProgressBar

    def capture_return(iter, *args, **kwargs):
        try:
            while True:
                next(iter)
        except StopIteration as e:
            return e.value

    monkeypatch.setattr(ProgressBar, "__enter__", lambda self: capture_return)
    monkeypatch.setattr(ProgressBar, "__exit__", lambda *args: None)
