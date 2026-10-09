from fastapi import APIRouter

from .. import state

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("")
def list_decisions():
    return state.decisions


@router.get("/latest")
def latest_decision():
    return state.decisions[0] if state.decisions else {"message": "no decisions"}
