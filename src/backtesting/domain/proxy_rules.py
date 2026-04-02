from __future__ import annotations


def build_proxy_map(proxy_rows: list[dict]) -> dict[str, str]:
    proxy_map: dict[str, str] = {}
    for row in proxy_rows:
        if not row.get("enabled", True):
            continue
        proxy_map[str(row["target"]).upper()] = str(row["proxy"]).upper()
    return proxy_map

