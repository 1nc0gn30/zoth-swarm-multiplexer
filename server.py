#!/usr/bin/env python3
"""Zoth Swarm Multiplexer Sovereign Server Launcher."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from swarm_daemon import run_server

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Zoth Swarm Multiplexer Server")
    parser.add_argument("--port", "-p", type=int, default=8141, help="Port to listen on (default: 8141)")
    args = parser.parse_args()

    run_server(port=args.port)
