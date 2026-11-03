#!/usr/bin/env python3
"""
⚡ Zoth Swarm Multiplexer MCP Server (zoth-swarm-multiplexer)
Model Context Protocol (MCP) stdio server adhering to the 2024-11-05 specification.
Exposes the 21-Agent Swarm Multiplexer to Claude Code, Hermes Agent, Antigravity, and Cursor.
Zero external pip dependencies (Pure Python 3 standard library).
"""

import sys
import json
import os

from swarm_daemon import SwarmMultiplexerEngine

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "zoth-swarm-multiplexer"
SERVER_VERSION = "1.0.0"

engine = SwarmMultiplexerEngine()

TOOLS = [
    {
        "name": "swarm_list_agents",
        "description": "List all 21 Pantheon agent nodes with their cadre, mascot, harness, model, and status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cadre": {
                    "type": "string",
                    "description": "Optional cadre filter: 'All', 'Architects', 'Code', 'Security', 'Creative', 'Swarm'",
                    "enum": ["All", "Architects", "Code", "Security", "Creative", "Swarm"],
                    "default": "All"
                }
            }
        }
    },
    {
        "name": "swarm_execute",
        "description": "Execute a directive, bash script, or command on a specific agent terminal node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID (e.g. 'AZOTH', 'NEXUS', 'MERCURY', 'CHRONOS', 'LYCAN', 'KITSUNE', 'AETHER')"
                },
                "command": {
                    "type": "string",
                    "description": "Command string or task instruction to execute"
                }
            },
            "required": ["agent_id", "command"]
        }
    },
    {
        "name": "swarm_broadcast",
        "description": "Broadcast a command or task across all 21 agent nodes or a specific cadre.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command string to broadcast"
                },
                "cadre": {
                    "type": "string",
                    "description": "Target cadre: 'All', 'Architects', 'Code', 'Security', 'Creative', 'Swarm'",
                    "default": "All"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "swarm_switch_harness",
        "description": "Hot-swap an agent node's AI harness and/or inference model target.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to modify"
                },
                "harness": {
                    "type": "string",
                    "description": "Target harness: 'hermes-agent', 'agy', 'codex', 'claude-code', 'opencode', 'ollama'",
                    "enum": ["hermes-agent", "agy", "codex", "claude-code", "opencode", "ollama"]
                },
                "model": {
                    "type": "string",
                    "description": "Target model: 'claude-3-7-sonnet', 'deepseek-r1:70b', 'qwen2.5-coder:32b', 'hermes-3:70b', etc."
                }
            },
            "required": ["agent_id"]
        }
    },
    {
        "name": "swarm_set_pwd",
        "description": "Set the current working directory context for an agent node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to update"
                },
                "pwd": {
                    "type": "string",
                    "description": "Absolute filesystem directory path"
                }
            },
            "required": ["agent_id", "pwd"]
        }
    },
    {
        "name": "swarm_get_logs",
        "description": "Retrieve recent streaming logs, tool calls, and thoughts for a specific agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to inspect"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent entries to return",
                    "default": 20
                }
            },
            "required": ["agent_id"]
        }
    },
    {
        "name": "swarm_sync_memory",
        "description": "Trigger STDP synaptic plasticity synchronization with the local neuro-memory-daemon (:8788).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Optional specific agent ID (omitted to sync all 21 agents)"
                }
            }
        }
    }
]

def handle_rpc(request):
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION
                }
            }
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS}
        }

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "swarm_list_agents":
            cadre = args.get("cadre", "All")
            state = engine.get_state()
            agents = state.get("agents", {})
            filtered = [
                a for a in agents.values()
                if cadre == "All" or a["cadre"] == cadre
            ]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({"total": len(filtered), "cadre": cadre, "agents": filtered}, indent=2)
                    }]
                }
            }

        elif tool_name == "swarm_execute":
            res = engine.execute_command(args.get("agent_id"), args.get("command"))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(res, indent=2)
                    }]
                }
            }

        elif tool_name == "swarm_broadcast":
            res = engine.broadcast(args.get("command"), args.get("cadre", "All"))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(res, indent=2)
                    }]
                }
            }

        elif tool_name == "swarm_switch_harness":
            aid = args.get("agent_id")
            out = {"agent_id": aid}
            if args.get("harness"):
                out["harness_res"] = engine.switch_harness(aid, args.get("harness"))
            if args.get("model"):
                out["model_res"] = engine.switch_model(aid, args.get("model"))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(out, indent=2)
                    }]
                }
            }

        elif tool_name == "swarm_set_pwd":
            res = engine.set_pwd(args.get("agent_id"), args.get("pwd"))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(res, indent=2)
                    }]
                }
            }

        elif tool_name == "swarm_get_logs":
            aid = args.get("agent_id")
            limit = args.get("limit", 20)
            state = engine.get_state()
            agent = state.get("agents", {}).get(aid)
            if not agent:
                res = {"error": f"Agent {aid} not found"}
            else:
                res = {"agent_id": aid, "logs": agent.get("logs", [])[-limit:]}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(res, indent=2)
                    }]
                }
            }

        elif tool_name == "swarm_sync_memory":
            res = engine.sync_memory(args.get("agent_id"))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(res, indent=2)
                    }]
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{method}' not implemented"}
    }

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = handle_rpc(req)
            if res:
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(e)}
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
