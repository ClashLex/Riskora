from datetime import date
from typing import Any


def explain_result(result: dict[str, Any], question: str) -> dict[str, Any]:
    source_ids = sorted(set(result.get("source_ids", [])))
    as_of_date = result.get("as_of_date", date.fromisoformat("2026-06-30").isoformat())
    data_status = result.get("data_status", "illustrative")
    if result.get("scenario_id"):
        change = result.get("estimated_change")
        if change is None:
            subtotal = result.get("modeled_estimated_change", 0.0)
            explanation = (
                f"The {result['scenario_id']} simulation is incomplete. Its modeled rows sum to "
                f"{subtotal:.2f} {result['base_currency']}, but a total portfolio change "
                "is withheld because "
                "some exposure could not be modelled. The scenario is hypothetical, not a forecast."
            )
        else:
            explanation = (
                f"The {result['scenario_id']} simulation estimates a change of {change:.2f} "
                f"{result['base_currency']} ({result['estimated_change_percent']:.2%}) from "
                f"{result['portfolio_value_before']:.2f} to {result['portfolio_value_after']:.2f} "
                f"{result['base_currency']}. This is a deterministic hypothetical, "
                "not a forecast or advice."
            )
    else:
        explanation = (
            f"{result['title']}: {result['explanation']} "
            "The calculation is based on the recorded evidence "
            "and disclosed prototype thresholds; it is not a recommendation."
        )
    if not source_ids:
        explanation = "Insufficient source evidence is available to support a grounded explanation."
        data_status = "not_modelled"
    return {
        "result_id": result["result_id"] if "result_id" in result else result["id"],
        "explanation": explanation,
        "mode": "template",
        "source_ids": source_ids,
        "data_status": data_status,
        "as_of_date": as_of_date,
    }
