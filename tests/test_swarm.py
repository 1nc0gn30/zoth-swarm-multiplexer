#!/usr/bin/env python3
"""
Unit and integration tests for Zoth Swarm Multiplexer (zoth-swarm-multiplexer).
"""

import sys
import os
import json
import pytest

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from swarm_daemon import SwarmMultiplexerEngine, PANTHEON_AGENTS, CADRES
from mcp_server import handle_rpc

@pytest.fixture
def engine():
    return SwarmMultiplexerEngine()

def test_engine_initialization(engine):
    state = engine.get_state()
    assert state["status"] == "online"
    assert state["total_agents"] == 21
    assert len(state["agents"]) == 21
    assert "Architects" in state["cadres"]
    assert "AZOTH" in state["agents"]
    assert "MERCURY" in state["agents"]
    assert "AETHER" in state["agents"]

def test_agent_schema_integrity(engine):
    state = engine.get_state()
    agents = state["agents"]
    required_keys = ["id", "name", "role", "cadre", "pet", "harness", "model", "pwd", "status", "logs", "memory_score", "synapses"]
    for aid, a in agents.items():
        for k in required_keys:
            assert k in a, f"Agent {aid} missing key {k}"
        assert a["cadre"] in CADRES

def test_execute_single_agent(engine):
    res = engine.execute_command("AZOTH", "status")
    assert res["success"] is True
    assert res["agent_id"] == "AZOTH"
    assert "OK" in res["output"]

    # Verify log was appended
    state = engine.get_state()
    agent_logs = state["agents"]["AZOTH"]["logs"]
    assert len(agent_logs) >= 3  # system init + user + assistant
    assert any("$ status" in l["text"] for l in agent_logs)

def test_broadcast_all_agents(engine):
    res = engine.broadcast("verify zero-egress", "All")
    assert res["success"] is True
    assert res["dispatched_count"] == 21
    assert len(res["results"]) == 21
    assert "AZOTH" in res["results"]
    assert res["results"]["AZOTH"]["success"] is True

def test_broadcast_specific_cadre(engine):
    res = engine.broadcast("status", "Security")
    assert res["success"] is True
    assert res["broadcast_cadre"] == "Security"
    # Security has 4 agents: LYCAN, ONYX, SCORPIUS, PIXEL-SHIBA
    assert res["dispatched_count"] == 4
    for aid in ["LYCAN", "ONYX", "SCORPIUS", "PIXEL-SHIBA"]:
        assert aid in res["results"]

def test_switch_harness_and_model(engine):
    res_h = engine.switch_harness("MERCURY", "hermes-agent")
    assert res_h["success"] is True
    assert res_h["harness"] == "hermes-agent"

    res_m = engine.switch_model("MERCURY", "hermes-3:70b")
    assert res_m["success"] is True
    assert res_m["model"] == "hermes-3:70b"

    state = engine.get_state()
    agent = state["agents"]["MERCURY"]
    assert agent["harness"] == "hermes-agent"
    assert agent["model"] == "hermes-3:70b"

def test_set_pwd(engine):
    new_dir = "/tmp/zoth-sandbox"
    res = engine.set_pwd("CHRONOS", new_dir)
    assert res["success"] is True
    assert res["pwd"] == new_dir

    state = engine.get_state()
    assert state["agents"]["CHRONOS"]["pwd"] == new_dir

def test_sync_memory(engine):
    res = engine.sync_memory("AZOTH")
    assert res["success"] is True
    assert res["synced_agents"] == 1

    res_all = engine.sync_memory(None)
    assert res_all["success"] is True
    assert res_all["synced_agents"] == 21

def test_mcp_initialize():
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    res = handle_rpc(req)
    assert res["id"] == 1
    assert res["result"]["protocolVersion"] == "2024-11-05"
    assert res["result"]["serverInfo"]["name"] == "zoth-swarm-multiplexer"

def test_mcp_tools_list():
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    res = handle_rpc(req)
    assert res["id"] == 2
    tools = res["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "swarm_list_agents" in tool_names
    assert "swarm_execute" in tool_names
    assert "swarm_broadcast" in tool_names
    assert "swarm_switch_harness" in tool_names
    assert "swarm_set_pwd" in tool_names

def test_mcp_call_swarm_list_agents():
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "swarm_list_agents",
            "arguments": {"cadre": "Architects"}
        }
    }
    res = handle_rpc(req)
    assert res["id"] == 3
    data = json.loads(res["result"]["content"][0]["text"])
    assert data["cadre"] == "Architects"
    assert data["total"] == 6

def test_mcp_call_swarm_execute():
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "swarm_execute",
            "arguments": {"agent_id": "AZOTH", "command": "status"}
        }
    }
    res = handle_rpc(req)
    assert res["id"] == 4
    data = json.loads(res["result"]["content"][0]["text"])
    assert data["success"] is True
    assert data["agent_id"] == "AZOTH"
