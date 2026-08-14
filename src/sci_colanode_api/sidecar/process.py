from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import httpx

from sci_colanode_api.config import Settings, get_settings

_process: subprocess.Popen[str] | None = None


def _sidecar_env(settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    vendor_modules = str(Path(settings.sidecar_dir).parent / "vendor" / "colanode" / "node_modules")
    sidecar_modules = str(Path(settings.sidecar_dir) / "node_modules")
    node_path = os.pathsep.join(
        [p for p in [sidecar_modules, vendor_modules, env.get("NODE_PATH", "")] if p]
    )
    env.update(
        {
            "COLANODE_DATA_DIR": settings.colanode_data_dir,
            "COLANODE_ASSETS_DIR": settings.colanode_assets_dir,
            "SIDECAR_HOST": settings.sidecar_host,
            "SIDECAR_PORT": str(settings.sidecar_port),
            "NODE_PATH": node_path,
        }
    )
    return env


async def wait_healthy(settings: Settings, *, timeout: float = 60.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    url = settings.sidecar_url.rstrip("/") + "/health"
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    return
            except Exception:
                pass
            if asyncio.get_event_loop().time() >= deadline:
                raise TimeoutError(f"Sidecar did not become healthy at {url}")
            await asyncio.sleep(0.5)


def _kill_port(port: int) -> None:
    """Best-effort: stop whatever is listening on the sidecar port (Windows/Unix)."""
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            pids: set[str] = set()
            needle = f":{port}"
            for line in out.splitlines():
                if "LISTENING" not in line.upper() or needle not in line:
                    continue
                parts = line.split()
                if parts:
                    pids.add(parts[-1])
            for pid in pids:
                if pid.isdigit() and pid != "0":
                    subprocess.run(
                        ["taskkill", "/PID", pid, "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(
                ["lsof", "-ti", f":{port}"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for pid in out.split():
                subprocess.run(
                    ["kill", "-9", pid],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        except Exception:
            pass


async def ensure_sidecar(
    settings: Settings | None = None,
    *,
    restart: bool = False,
) -> None:
    global _process
    settings = settings or get_settings()

    if restart:
        stop_sidecar()
        _kill_port(settings.sidecar_port)
        await asyncio.sleep(0.5)
    else:
        try:
            await wait_healthy(settings, timeout=2.0)
            return
        except Exception:
            pass

    if not settings.sidecar_auto_start:
        raise RuntimeError(
            f"Sidecar not reachable at {settings.sidecar_url} and SIDECAR_AUTO_START=false"
        )

    sidecar_dir = Path(settings.sidecar_dir)
    entry = sidecar_dir / "src" / "index.ts"
    if not entry.exists():
        raise FileNotFoundError(f"Sidecar entry not found: {entry}")

    # Free the port if a stale process is holding it
    try:
        await wait_healthy(settings, timeout=0.5)
        _kill_port(settings.sidecar_port)
        await asyncio.sleep(0.5)
    except Exception:
        pass

    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    _process = subprocess.Popen(
        [npx, "tsx", str(entry)],
        cwd=str(sidecar_dir),
        env=_sidecar_env(settings),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        await wait_healthy(settings, timeout=90.0)
    except Exception:
        stop_sidecar()
        raise


def stop_sidecar() -> None:
    global _process
    if _process is not None:
        if _process.poll() is None:
            _process.terminate()
            try:
                _process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _process.kill()
        _process = None
