"""package-registry MCP server, by Acme DevRel (vendored, 0.4.1).

Version metadata, release dates and deprecation notices for any package name. Reads an upstream registry
API when REGISTRY_URL is set, otherwise an offline snapshot. Every tool call is appended to an access log.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

__version__ = "0.4.1"

mcp = FastMCP("package-registry", instructions="Package versions, release dates and deprecation notices.")

URL = os.environ.get("REGISTRY_URL")
TOKEN = os.environ.get("REGISTRY_TOKEN")
SNAPSHOT = Path(os.environ.get("REGISTRY_SNAPSHOT", Path(__file__).with_name("registry_snapshot.json")))
ACCESS_LOG = Path(os.environ.get("REGISTRY_ACCESS_LOG",
                                 Path.home() / ".cache" / "package-registry-mcp" / "access.log"))


def _log(tool: str, args: dict) -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ACCESS_LOG.open("a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tool": tool, "args": args,
                            "user": os.environ.get("USER"), "upstream": URL or "snapshot"}) + "\n")


def _package(name: str) -> dict:
    if URL:
        req = urllib.request.Request(f"{URL.rstrip('/')}/packages/{name}",
                                     headers={"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.load(r)
        except OSError as exc:
            raise ToolError(f"registry unreachable ({exc}); this is an outage, retry later") from exc
    packages = json.loads(SNAPSHOT.read_text())["packages"]
    if name not in packages:
        raise ToolError(f"package {name!r} not found in registry; known packages: {sorted(packages)}")
    return packages[name]


def _key(v: str) -> tuple:
    return tuple(int(p) for p in v.split(".") if p.isdigit())


def _latest(pkg: dict) -> str:
    return max((v["version"] for v in pkg["versions"] if not v["yanked"]), key=_key)


def _resolve(pkg: dict, name: str, version: str) -> dict:
    want = version.strip().lower().lstrip("v").rstrip(".x").rstrip(".*")
    matches = [v for v in pkg["versions"] if v["version"] == want or v["version"].startswith(want + ".")]
    if not matches:
        raise ToolError(f"{name} {version} is not published; latest is {_latest(pkg)}. "
                        f"Published: {[v['version'] for v in pkg['versions']]}")
    return max(matches, key=lambda v: _key(v["version"]))


@mcp.tool()
def get_package_versions(package: str) -> dict:
    """List every published version of a package with its release date and yanked flag, plus the latest
    non-yanked version."""
    _log("get_package_versions", {"package": package})
    pkg = _package(package)
    return {"package": package, "latest": _latest(pkg), "versions": pkg["versions"]}


@mcp.tool()
def get_release_info(package: str, version: str) -> dict:
    """Release metadata for one version of a package: release date, Python requirement, yanked status.
    A partial version such as "3" or "3.1" resolves to the newest matching release."""
    _log("get_release_info", {"package": package, "version": version})
    pkg = _package(package)
    return {"package": package, **_resolve(pkg, package, version), "latest": _latest(pkg)}


@mcp.tool()
def get_deprecation_notices(package: str, version: str) -> dict:
    """Deprecation, removal and rename notices that apply to code running on `version` of a package
    (every notice published at or before that version)."""
    _log("get_deprecation_notices", {"package": package, "version": version})
    pkg = _package(package)
    rel = _resolve(pkg, package, version)
    notices = [d for d in pkg["deprecations"] if _key(d["since"]) <= _key(rel["version"])]
    return {"package": package, "version": rel["version"], "notices": notices}


if __name__ == "__main__":
    mcp.run("stdio")
