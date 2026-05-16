from fastapi import APIRouter
from pydantic import BaseModel

from app.services.automation.runner import automation_runner
from app.services.controls.runtime_state import runtime_control_state

router = APIRouter(prefix="/api/v1/automation", tags=["automation"])


class KillSwitchRequest(BaseModel):
    reason: str = "Emergency stop triggered manually."


@router.get("/status")
async def get_automation_status() -> dict:
    return automation_runner.get_status()


@router.post("/run-once")
async def run_automation_once() -> dict:
    return await automation_runner.run_once()


@router.post("/pause")
async def pause_automation() -> dict:
    return await automation_runner.pause()


@router.post("/resume")
async def resume_automation() -> dict:
    return await automation_runner.resume()


@router.post("/stop")
async def stop_automation() -> dict:
    return await automation_runner.shutdown()


@router.get("/kill-switch")
async def get_kill_switch_status() -> dict:
    return runtime_control_state.get_kill_switch_status()


@router.post("/kill-switch/enable")
async def enable_kill_switch(payload: KillSwitchRequest) -> dict:
    return runtime_control_state.enable_kill_switch(payload.reason)


@router.post("/kill-switch/disable")
async def disable_kill_switch() -> dict:
    return runtime_control_state.disable_kill_switch()
