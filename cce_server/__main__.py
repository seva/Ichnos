"""Entry point: stdio server. Identity from the CCE_CONSUMER registration binding (env);
configuration from the CCE_CONFIG path (default ~/.config/ichnos/cce.json)."""

from __future__ import annotations

import os

from cce_server.config import DEFAULT_CONFIG_PATH, build_app_from_config


def main() -> None:
    binding = os.environ.get("CCE_CONSUMER")
    if not binding:
        raise SystemExit(
            "CCE_CONSUMER not set — consumer identity comes from the registration binding"
        )
    config_path = os.environ.get("CCE_CONFIG", DEFAULT_CONFIG_PATH)
    app = build_app_from_config(config_path, binding=binding)
    app.run(transport="stdio")


def main_http() -> None:
    """HTTP mode: the engine serves many consumers over streamable-HTTP; identity via bearer token."""
    config_path = os.environ.get("CCE_CONFIG", DEFAULT_CONFIG_PATH)
    from cce_server.config import build_http_app_from_config

    app = build_http_app_from_config(config_path)
    app.run(
        transport="streamable-http",
        host=os.environ.get("CCE_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("CCE_HTTP_PORT", "8001")),
    )


if __name__ == "__main__":
    main()
