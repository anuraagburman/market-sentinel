"""Portfolio exposure to an event, from a deterministic valuation. No model touches this."""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from app.models.valuation import Unavailable, Valuation


@dataclass(frozen=True)
class Exposure:
    weight: Decimal
    held: bool


def exposure_for(event: dict, valuation: Valuation) -> Exposure | None:
    """Summed weight of held event instruments. None when any held one is unpriced: never 0."""
    held = [p for p in valuation.positions if str(p.instrument_id) in event["instrument_ids"]]
    if any(isinstance(p.weight, Unavailable) for p in held):
        return None
    with localcontext() as context:
        context.prec = 34  # valuation's precision; the default 28 would round the weights
        return Exposure(weight=sum((p.weight.value for p in held), Decimal(0)), held=bool(held))
