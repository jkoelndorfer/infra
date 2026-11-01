"""
provision/inventory -- pyinfra Inventory
========================================

This file lists the servers pyinfra manages. Each server has exactly one role.
"""

network: list[tuple[str, dict[str, str]]] = [
    ("router0.lan", {"role": "edgerouter"}),
]
