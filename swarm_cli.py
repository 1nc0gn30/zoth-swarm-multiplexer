#!/usr/bin/env python3
"""
Zoth Swarm CLI (zoth-swarm-multiplexer)
Terminal control surface for the 21-Agent Swarm Multiplexer.
Zero external dependencies (Python 3 standard library).
"""

import sys
import os
import json
import argparse
from urllib.request import Request, urlopen

DEFAULT_DAEMON_URL = "http://127.0.0.1:8141"

GOLD = "\033[38;2;212;175;55m"
CYAN = "\033[36m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"

CADRE_COLORS = {
    "Architects": GOLD,
    "Code": CYAN,
    "Security": RED,
    "Creative": MAGENTA,
    "Swarm": GREEN,
}


def api_request(path, method="GET", body=None, daemon_url=None):
    urls = [daemon_url] if daemon_url else [DEFAULT_DAEMON_URL, "http://127.0.0.1:8989"]
    for base_url in urls:
        url = f"{base_url.rstrip('/')}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        headers = {"Content-Type": "application/json"}
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=3) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
    return None


def cmd_status(args, engine=None):
    if engine:
        state = engine.get_state()
    else:
        state = api_request("/status")
        if not state:
            from swarm_daemon import SwarmMultiplexerEngine
            engine = SwarmMultiplexerEngine()
            state = engine.get_state()

    cadre_filter = getattr(args, "cadre", None) or "All"
    agents = state.get("agents", {})
    if isinstance(agents, list):
        agent_iter = [(a.get("id"), a) for a in agents if a]
    else:
        agent_iter = [(aid, a) for aid, a in agents.items() if a]

    if cadre_filter != "All":
        agent_iter = [(aid, a) for aid, a in agent_iter if a.get("cadre") == cadre_filter]

    if getattr(args, "json", False):
        print(json.dumps({
            "status": state.get("status", "online"),
            "cadre": cadre_filter,
            "total_agents": len(agent_iter),
            "port": 8141,
            "agents": {aid: a for aid, a in agent_iter},
        }, indent=2))
        return

    print(f"\n{GOLD}{BOLD}╔═══════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{GOLD}{BOLD}║                     ZOTH 21-AGENT SWARM PANTHEON STATUS MATRIX                            ║{RESET}")
    print(f"{GOLD}{BOLD}╚═══════════════════════════════════════════════════════════════════════════════════════════╝{RESET}\n")
    print(f"{BOLD}{'ID':<15} {'CADRE':<12} {'HARNESS':<14} {'MODEL':<18} {'MEM%':<6} {'STATUS':<8} {'WORKING DIR'}{RESET}")
    print("─" * 105)

    for aid, a in agent_iter:
        c_color = CADRE_COLORS.get(a.get("cadre"), RESET)
        status = a.get("status", "IDLE")
        status_color = GREEN if status == "IDLE" else (GOLD if status == "RUNNING" else RED)
        pwd = a.get("pwd", "")
        pwd_short = pwd.replace(os.path.expanduser("~"), "~")
        if len(pwd_short) > 35:
            pwd_short = "..." + pwd_short[-32:]

        pet_str = a.get("pet", "🤖")
        if str(pet_str).startswith("/"):
            pet_str = "🤖"
        mem_val = a.get("memory_score", "95%")
        harness_val = a.get("harness", "agy")
        model_val = a.get("model", "default")
        print(f"{pet_str} {BOLD}{str(aid):<12}{RESET} {c_color}{str(a.get('cadre', '')): <12}{RESET} {str(harness_val):<14} {str(model_val):<18} {str(mem_val):<6} {status_color}{status:<8}{RESET} {pwd_short}")

    print("─" * 105)
    print(f"{BOLD}Total Agents:{RESET} {len(agent_iter)}  ·  {BOLD}Cadres:{RESET} 5  ·  {BOLD}Loopback Port:{RESET} 8141\n")


def cmd_exec(args):
    body = {"agent_id": args.agent, "command": args.command}
    res = api_request("/execute", method="POST", body=body)
    if not res:
        from swarm_daemon import SwarmMultiplexerEngine
        eng = SwarmMultiplexerEngine()
        res = eng.execute_command(args.agent, args.command)

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return

    if res and res.get("success"):
        print(f"\n{GREEN}✔ [{args.agent} EXECUTION OK]{RESET}")
        print(f"{res.get('output')}\n")
    else:
        err = res.get("error") if res else "Could not connect to Swarm Daemon"
        print(f"\n{RED}✖ Execution Failed:{RESET} {err}\n")


def cmd_broadcast(args):
    body = {"command": args.command, "cadre": args.cadre or "All"}
    res = api_request("/broadcast", method="POST", body=body)
    if not res:
        from swarm_daemon import SwarmMultiplexerEngine
        eng = SwarmMultiplexerEngine()
        res = eng.broadcast(args.command, args.cadre or "All")

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return

    print(f"\n{GOLD}Broadcast Dispatched to {res.get('dispatched_count')} Agent Nodes (Cadre: {args.cadre or 'All'}):{RESET}\n")
    results = res.get("results", {})
    for aid, r in results.items():
        out_first_line = r.get("output", "").split("\n")[0]
        print(f"  {CYAN}▸ {aid:<14}{RESET} : {out_first_line}")
    print()


def cmd_switch(args):
    out = {"agent_id": args.agent}
    if args.harness:
        res = api_request("/harness", method="POST", body={"agent_id": args.agent, "harness": args.harness})
        if not res:
            from swarm_daemon import SwarmMultiplexerEngine
            eng = SwarmMultiplexerEngine()
            res = eng.switch_harness(args.agent, args.harness)
        out["harness_res"] = res
        if not getattr(args, "json", False):
            print(f"{GREEN}✔ Switched {args.agent} harness to [{args.harness}]{RESET}")

    if args.model:
        res = api_request("/model", method="POST", body={"agent_id": args.agent, "model": args.model})
        if not res:
            from swarm_daemon import SwarmMultiplexerEngine
            eng = SwarmMultiplexerEngine()
            res = eng.switch_model(args.agent, args.model)
        out["model_res"] = res
        if not getattr(args, "json", False):
            print(f"{GREEN}✔ Switched {args.agent} model to [{args.model}]{RESET}")

    if getattr(args, "json", False):
        print(json.dumps(out, indent=2))


def cmd_daemon(args):
    from swarm_daemon import run_server
    run_server(args.port or 8141)


def main():
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    parser = argparse.ArgumentParser(
        description="Zoth Swarm Multiplexer CLI — 21-Agent Terminal Control Console",
        parents=[base_parser],
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    p_status = subparsers.add_parser("status", help="Display all 21 agents and status", parents=[base_parser])
    p_status.add_argument("--cadre", choices=["All", "Architects", "Code", "Security", "Creative", "Swarm"], default="All")

    p_exec = subparsers.add_parser("exec", help="Execute command on a single agent", parents=[base_parser])
    p_exec.add_argument("--agent", required=True, help="Agent ID (e.g. AZOTH, CHRONOS, MERCURY)")
    p_exec.add_argument("command", help="Command string to execute")

    p_bcast = subparsers.add_parser("broadcast", help="Broadcast command to all agents or cadre", parents=[base_parser])
    p_bcast.add_argument("--cadre", choices=["All", "Architects", "Code", "Security", "Creative", "Swarm"], default="All")
    p_bcast.add_argument("command", help="Command string to broadcast")

    p_switch = subparsers.add_parser("switch", help="Hot-swap agent harness and/or model", parents=[base_parser])
    p_switch.add_argument("--agent", required=True, help="Agent ID")
    p_switch.add_argument("--harness", choices=["hermes-agent", "agy", "codex", "claude-code", "opencode", "ollama"])
    p_switch.add_argument("--model", help="Model name (e.g. claude-3-7-sonnet, deepseek-r1:70b)")

    p_daemon = subparsers.add_parser("daemon", help="Start the Swarm Daemon HTTP & SSE server", parents=[base_parser])
    p_daemon.add_argument("--port", type=int, default=8141, help="Port to listen on (default: 8141)")

    args = parser.parse_args()

    if args.subcommand == "status" or (args.subcommand is None and args.json):
        cmd_status(args)
    elif args.subcommand == "exec":
        cmd_exec(args)
    elif args.subcommand == "broadcast":
        cmd_broadcast(args)
    elif args.subcommand == "switch":
        cmd_switch(args)
    elif args.subcommand == "daemon":
        cmd_daemon(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
