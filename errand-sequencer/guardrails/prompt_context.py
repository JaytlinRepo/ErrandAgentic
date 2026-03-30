"""Inject structured constraints and metadata into the LLM prompt."""

from __future__ import annotations

from datetime import datetime


def with_start_location_context(errands: str, location_note: str | None) -> str:
    if not location_note:
        return errands
    return (
        f"Starting location context for routing: {location_note}\n\n"
        "Use this as the starting point when estimating travel efficiency.\n\n"
        f"Errands:\n{errands}"
    )


def with_food_preference_context(errands: str, last_food_place: str | None) -> str:
    if not last_food_place:
        return errands
    return (
        f"{errands}\n\n"
        "Hard preference:\n"
        f'- Treat "{last_food_place}" as the final stop in the route.\n'
        "- If route constraints make this impossible, explain why and give the closest alternative."
    )


def with_unique_stop_constraint(errands: str, errand_lines: list[str]) -> str:
    if not errand_lines:
        return errands
    bullets = "\n".join(f"- {e}" for e in errand_lines)
    return (
        f"{errands}\n\n"
        "Hard constraint:\n"
        "- Build a route that visits each listed errand exactly once.\n"
        "- Do not duplicate stops in the final itinerary.\n"
        f"- Exact errands to cover:\n{bullets}"
    )


def with_planned_order_context(
    errands: str, errand_lines: list[str], last_food_place: str | None
) -> str:
    if not errand_lines:
        return errands
    ordered = list(errand_lines)
    if last_food_place and last_food_place in ordered:
        ordered = [e for e in ordered if e != last_food_place] + [last_food_place]
    bullets = "\n".join(f"{idx + 1}. {name}" for idx, name in enumerate(ordered))
    return (
        f"{errands}\n\n"
        "Planned stop order (must follow exactly unless a tool reports impossible routing):\n"
        f"{bullets}\n"
        "- Keep this order and provide travel-time-based ETAs for each leg."
    )


def with_eat_last_guardrail_context(
    errands: str, *, wants_eat_last: bool, food_candidates: list[str]
) -> str:
    if not wants_eat_last:
        return errands
    if food_candidates:
        return (
            f"{errands}\n\n"
            "Eat-last preference note:\n"
            "- Apply eat-last ONLY to actual restaurant/meal stops.\n"
            "- Do not relabel grocery or shopping errands as meal stops."
        )
    return (
        f"{errands}\n\n"
        "Eat-last preference note:\n"
        "- No explicit food/restaurant stop was detected in the errands.\n"
        "- Do NOT mark grocery or retail stops as the meal stop.\n"
        "- Keep route optimization for listed errands and ask a brief follow-up suggesting the user add a meal stop if they want eat-last applied."
    )


def with_current_time_context(errands: str) -> str:
    now = datetime.now().astimezone()
    time_line = now.strftime("%Y-%m-%d %I:%M %p %Z")
    return (
        f"Current local time at request: {time_line}\n"
        "Use this timestamp to estimate stop start times and arrivals.\n\n"
        f"{errands}"
    )
