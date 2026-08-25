"""Structural guarantees for the 17-agent hierarchy."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.workflow.catalog import (
    AGENT_CATALOG,
    AGENTS_BY_ID,
    MAIN_ORCHESTRATOR_ID,
    TEAM_ORCHESTRATOR_IDS,
    AgentDefinition,
    create_agent_runtime,
    get_agent_definition,
    get_team_orchestrator,
    get_team_specialists,
)
from app.workflow.schemas import OperationalTeam

OPERATIONAL_TEAMS: tuple[OperationalTeam, ...] = (
    "triage",
    "investigation",
    "response",
    "communications",
)


def test_hierarchy_has_one_commander_four_orchestrators_and_twelve_specialists() -> None:
    roles = [agent.role for agent in AGENT_CATALOG]
    assert len(AGENT_CATALOG) == 17
    assert roles.count("main-orchestrator") == 1
    assert roles.count("sub-orchestrator") == 4
    assert roles.count("specialist") == 12


def test_agent_ids_are_unique() -> None:
    ids = [agent.id for agent in AGENT_CATALOG]
    assert len(set(ids)) == len(ids)
    assert set(AGENTS_BY_ID) == set(ids)


def test_commander_is_the_only_root_node() -> None:
    roots = [agent for agent in AGENT_CATALOG if agent.parent_id is None]
    assert [agent.id for agent in roots] == [MAIN_ORCHESTRATOR_ID]


def test_sub_orchestrators_report_to_the_commander() -> None:
    for agent in AGENT_CATALOG:
        if agent.role == "sub-orchestrator":
            assert agent.parent_id == MAIN_ORCHESTRATOR_ID


def test_specialists_report_to_the_orchestrator_of_their_own_team() -> None:
    for agent in AGENT_CATALOG:
        if agent.role != "specialist":
            continue
        parent = AGENTS_BY_ID[str(agent.parent_id)]
        assert parent.role == "sub-orchestrator"
        assert parent.team == agent.team


def test_the_graph_is_acyclic_and_every_agent_reaches_the_commander() -> None:
    for agent in AGENT_CATALOG:
        seen: set[str] = set()
        current: AgentDefinition | None = agent
        while current is not None and current.parent_id is not None:
            assert current.id not in seen, f"cycle detected at {current.id}"
            seen.add(current.id)
            current = AGENTS_BY_ID[current.parent_id]
        assert current is not None
        assert current.id == MAIN_ORCHESTRATOR_ID


@pytest.mark.parametrize("team", OPERATIONAL_TEAMS)
def test_each_team_has_one_orchestrator_and_three_specialists(team: OperationalTeam) -> None:
    orchestrator = get_team_orchestrator(team)
    specialists = get_team_specialists(team)

    assert orchestrator.team == team
    assert orchestrator.role == "sub-orchestrator"
    assert orchestrator.id == TEAM_ORCHESTRATOR_IDS[team]
    assert len(specialists) == 3
    assert {specialist.team for specialist in specialists} == {team}


def test_team_orchestrator_ids_cover_every_operational_team() -> None:
    assert set(TEAM_ORCHESTRATOR_IDS) == set(OPERATIONAL_TEAMS)


def test_only_the_commander_belongs_to_the_command_team() -> None:
    command_agents = [agent for agent in AGENT_CATALOG if agent.team == "command"]
    assert [agent.id for agent in command_agents] == [MAIN_ORCHESTRATOR_ID]


def test_every_agent_declares_a_mission_and_capabilities() -> None:
    for agent in AGENT_CATALOG:
        assert agent.mission.strip()
        assert len(agent.capabilities) >= 1
        assert all(capability.strip() for capability in agent.capabilities)


def test_get_agent_definition_rejects_unknown_ids() -> None:
    with pytest.raises(KeyError, match="Unknown agent: ghost-agent"):
        get_agent_definition("ghost-agent")


def test_agent_definitions_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        get_agent_definition(MAIN_ORCHESTRATOR_ID).mission = "changed"  # type: ignore[misc]


class TestRuntimeConstruction:
    def test_runtime_mirrors_the_catalog_and_starts_queued(self) -> None:
        runtimes = create_agent_runtime()

        assert len(runtimes) == len(AGENT_CATALOG)
        assert [runtime.id for runtime in runtimes] == [agent.id for agent in AGENT_CATALOG]
        for runtime in runtimes:
            definition = AGENTS_BY_ID[runtime.id]
            assert runtime.status == "queued"
            assert runtime.current_task is None
            assert runtime.output_summary is None
            assert runtime.started_at is None
            assert runtime.completed_at is None
            assert runtime.role == definition.role
            assert runtime.team == definition.team
            assert runtime.parent_id == definition.parent_id
            assert runtime.capabilities == list(definition.capabilities)

    def test_each_call_returns_independent_state(self) -> None:
        first = create_agent_runtime()
        second = create_agent_runtime()

        first[0].status = "running"
        first[0].capabilities.append("mutated")

        assert second[0].status == "queued"
        assert "mutated" not in second[0].capabilities
        assert "mutated" not in AGENTS_BY_ID[first[0].id].capabilities
