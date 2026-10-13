"""Fixed module assumptions used to convert $/module costs to $/metric ton."""

MODULE_POWER_W: float = 270.0
MODULE_MASS_PER_W_KG: float = 0.07
MODULE_MASS_KG: float = MODULE_POWER_W * MODULE_MASS_PER_W_KG
MODULES_PER_METRIC_TON: float = 1000.0 / MODULE_MASS_KG
BASELINE_RECYCLING_COST_PER_MODULE: float = 12.5
BASELINE_RECYCLING_RATE_PER_KG: float = (
    BASELINE_RECYCLING_COST_PER_MODULE / MODULE_MASS_KG
)


def module_cost_to_metric_ton(
    cost_per_module: float | list[float] | tuple[float, ...],
) -> float | list[float]:
    """
    Convert dollars per module to dollars per metric ton.

    Assumes a fixed 270 W, 0.07 kg/W (18.9 kg) module, i.e. about 52.9
    modules per metric ton; this is not the time-varying PV ICE mass factor.
    Parameters:
    cost_per_module (float | list[float] | tuple[float, ...]): Cost or costs.
    Returns:
    float | list[float]: Converted scalar, or a new list for sequences.
    """
    if isinstance(cost_per_module, (list, tuple)):
        return [cost * MODULES_PER_METRIC_TON for cost in cost_per_module]
    return cost_per_module * MODULES_PER_METRIC_TON


def metric_ton_cost_to_module(
    cost_per_metric_ton: float | list[float] | tuple[float, ...],
) -> float | list[float]:
    """
    Convert dollars per metric ton back to dollars per module.
    Parameters:
    cost_per_metric_ton (float | list[float] | tuple[float, ...]): Cost or costs.
    Returns:
    float | list[float]: Converted scalar, or a new list for sequences.
    """
    if isinstance(cost_per_metric_ton, (list, tuple)):
        return [cost / MODULES_PER_METRIC_TON for cost in cost_per_metric_ton]
    return cost_per_metric_ton / MODULES_PER_METRIC_TON