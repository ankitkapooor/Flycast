"""Connectome metadata API route."""

from fastapi import APIRouter, HTTPException
from app.brain.loader import get_brain, is_brain_ready
from app.config import settings

router = APIRouter(prefix="/brain", tags=["brain"])


@router.get("")
def get_brain_info():
    """Returns runtime connectome properties and architecture configuration."""
    if not is_brain_ready():
        raise HTTPException(
            status_code=503,
            detail="Brain is currently initializing or not yet loaded.",
        )
    brain = get_brain()
    manifest = brain.manifest

    return {
        "dataset": "MaleCNS v1.0",
        "published_neurons": manifest.published_neurons,
        "runtime_neurons": manifest.neurons,
        "runtime_edges": manifest.edges,
        "input_neurons": manifest.input_neurons,
        "readout_neurons": manifest.readout_neurons,
        "weight_transform": "log1p + incoming normalization",
        "sign_mode": manifest.sign_mode,
        "reservoir_model": "leaky tanh rate reservoir",
        "manifest_hash": manifest.manifest_hash or "fixture-manifest",
        "leak": settings.RESERVOIR_LEAK,
        "recurrent_gain": settings.RESERVOIR_GAIN,
        "input_gain": settings.INPUT_GAIN,
    }
