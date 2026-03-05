"""Shared fixtures for e2e Playwright tests."""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_SRC = PROJECT_ROOT / "tests" / "e2e" / "fixtures" / "test_vehicle.yaml"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"Flask server did not start on port {port}")


@pytest.fixture(scope="session")
def _server_state(tmp_path_factory):
    port = _free_port()
    data_dir = tmp_path_factory.mktemp("data")
    data_file = data_dir / "test_vehicle.yaml"
    shutil.copy(FIXTURE_SRC, data_file)

    env = {**os.environ, "VEHICLES_DIR": str(data_dir), "FLASK_RUN_PORT": str(port)}
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "web" / "app.py")],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server(port)
    except TimeoutError:
        proc.terminate()
        proc.wait(timeout=5)
        raise

    yield (f"http://127.0.0.1:{port}", data_file)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture(scope="session")
def flask_server(_server_state):
    return _server_state[0]


@pytest.fixture(scope="session")
def data_file(_server_state):
    return _server_state[1]


@pytest.fixture(autouse=True)
def _reset_data(data_file):
    shutil.copy(FIXTURE_SRC, data_file)
    yield


@pytest.fixture(autouse=True)
def _set_default_timeout(page):
    page.set_default_timeout(8000)
