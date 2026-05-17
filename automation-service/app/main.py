from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.smarthome_common import (
    AutomationRule,
    AutomationRuleCreateRequest,
    CommandSource,
    Role,
    RuleAction,
    Scenario,
    ScenarioActivationRequest,
    ScenarioCreateRequest,
    ScenarioExecutionResult,
    Settings,
    TriggerType,
    build_audit_event,
    has_permission,
    recommend_behavior_scenarios,
)

settings = Settings(service_name="automation-service", service_port=8502)
app = FastAPI(title="SmartHome Automation Service", version="1.0.0")

rules: dict[str, AutomationRule] = {}
scenarios: dict[str, Scenario] = {}
audit_log: list[dict[str, Any]] = []


class RuleImportRequest(BaseModel):
    items: list[AutomationRule] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


RuleImportRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="automation",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _seed() -> None:
    away = Scenario(
        scenario_id="SCN-AWAY",
        home_id="HOME-DEMO",
        name="away_mode",
        description="Turn off lights, lower climate, lock doors.",
        actions=[
            RuleAction(device_name="living room light", action="turn_off"),
            RuleAction(device_name="hall thermostat", action="set_temperature", params={"temperature": 19}),
            RuleAction(device_name="front door lock", action="lock"),
        ],
        tags=["security", "energy"],
    )
    night = Scenario(
        scenario_id="SCN-NIGHT",
        home_id="HOME-DEMO",
        name="night_mode",
        description="Soft lights and reduced volume.",
        actions=[
            RuleAction(device_name="living room light", action="set_brightness", params={"brightness": 20}),
            RuleAction(device_name="kitchen speaker", action="set_volume", params={"volume": 12}),
        ],
        tags=["comfort"],
    )
    scenarios[away.scenario_id] = away
    scenarios[night.scenario_id] = night

    rule = AutomationRule(
        rule_id="RULE-1",
        home_id="HOME-DEMO",
        name="night_motion_rule",
        trigger=TriggerType.SENSOR,
        condition={"sensor": "entry_motion", "operator": "==", "value": "detected"},
        actions=[RuleAction(device_name="living room light", action="set_brightness", params={"brightness": 35})],
        enabled=True,
    )
    rules[rule.rule_id] = rule


_seed()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/scenarios")
async def list_scenarios(home_id: str = "HOME-DEMO") -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in scenarios.values() if item.home_id == home_id]
    return {"items": items, "count": len(items)}


@app.post("/scenarios")
async def create_scenario(request: ScenarioCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "scenario:manage")
    scenario = Scenario(
        scenario_id=str(uuid4()),
        home_id=request.home_id,
        name=request.name,
        description=request.description,
        actions=request.actions,
        tags=["custom"],
    )
    scenarios[scenario.scenario_id] = scenario
    _audit(request.actor_id, request.actor_role, "scenario.create", scenario.scenario_id)
    return scenario.model_dump(mode="json")


@app.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str, actor_role: Role = Role.OWNER) -> dict[str, Any]:
    _assert_permission(actor_role, "scenario:read")
    scenario = scenarios.get(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario.model_dump(mode="json")


@app.post("/scenarios/{scenario_id}/activate")
async def activate_scenario(scenario_id: str, request: ScenarioActivationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "scenario:manage")
    scenario = scenarios.get(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    result = ScenarioExecutionResult(
        scenario_id=scenario.scenario_id,
        success=True,
        planned_actions=len(scenario.actions),
        executed_actions=0,
        details=[
            {
                "device_name": action.device_name,
                "action": action.action,
                "params": action.params,
                "source": request.source,
            }
            for action in scenario.actions
        ],
    )
    _audit(request.actor_id, request.actor_role, "scenario.activate", scenario.scenario_id)
    return result.model_dump(mode="json")


@app.get("/rules")
async def list_rules(home_id: str = "HOME-DEMO") -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in rules.values() if item.home_id == home_id]
    return {"items": items, "count": len(items)}


@app.post("/rules")
async def create_rule(request: AutomationRuleCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "scenario:manage")
    rule = AutomationRule(
        rule_id=str(uuid4()),
        home_id=request.home_id,
        name=request.name,
        trigger=request.trigger,
        condition=request.condition,
        actions=request.actions,
        enabled=request.enabled,
    )
    rules[rule.rule_id] = rule
    _audit(request.actor_id, request.actor_role, "rule.create", rule.rule_id)
    return rule.model_dump(mode="json")


@app.get("/rules/export")
async def export_rules(home_id: str = "HOME-DEMO", actor_role: Role = Role.OWNER) -> dict[str, Any]:
    _assert_permission(actor_role, "scenario:read")
    items = [rule.model_dump(mode="json") for rule in rules.values() if rule.home_id == home_id]
    return {"items": items, "count": len(items)}


@app.post("/rules/import")
async def import_rules(request: RuleImportRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "scenario:manage")
    for rule in request.items:
        rules[rule.rule_id] = rule
    _audit(request.actor_id, request.actor_role, "rule.import", str(len(request.items)))
    return {"imported": len(request.items)}


@app.post("/behavior/recommendations")
async def behavior_recommendations(history: list[dict[str, str]]) -> dict[str, Any]:
    return {"items": recommend_behavior_scenarios(history)}


@app.get("/triggers")
async def trigger_catalog() -> dict[str, Any]:
    return {"items": [trigger.value for trigger in TriggerType], "default_source": CommandSource.AUTOMATION.value}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}