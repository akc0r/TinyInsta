from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class BusConfig:
    bootstrap_servers: str
    client_id: str

    @classmethod
    def from_env(cls, client_id: str | None = None) -> "BusConfig":
        return cls(
            bootstrap_servers=os.environ.get("BUS_BOOTSTRAP_SERVERS", "redpanda:9092"),
            client_id=client_id or os.environ.get("SERVICE_NAME", "tinyinsta-svc"),
        )
