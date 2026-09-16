"""Entry point: stdio server, consumer identity from the registration binding (env)."""

from __future__ import annotations

import os

from cce_server.registry import Registry


def main() -> None:
    binding = os.environ.get("CCE_CONSUMER")
    if not binding:
        raise SystemExit(
            "CCE_CONSUMER not set — consumer identity comes from the registration binding"
        )

    from cce_server.server import build_server

    registry = Registry.from_config({})  # channel/consumer config wired at adapter integration
    app = build_server(registry=registry, channels=[], binding=binding)
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
