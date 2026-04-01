# Agent Guardrails and Failure Modes
kind: general
category: guardrail
geo_scope: atlanta_metro
time_scope: any
confidence: verified_policy
must_verify_with_tool: false

## Multi-County Sequencing
If the user lists stops in multiple non-adjacent counties retrieval should bias toward cluster-first sequencing guidance. Never sequence stops by alphabetical or list order. Always group by geographic proximity first then optimize within clusters.

## Time Window Constraints
If stops include time windows like before 5pm or after school retrieval should emphasize anchor and buffer heuristics. Hard time windows must be treated as fixed constraints not optimization targets. Soft preferences can be treated as optimization targets.

## Event and Sports Day Deference
If the user mentions events, sports, or festivals retrieval should suggest checking live traffic even when RAG gives general patterns. General patterns are baselines. Live conditions during events are unpredictable and always require live Maps data to handle correctly.

## Cold Chain Elevation
If errands include temperature-sensitive items retrieval should always elevate cold-chain ordering rules. Frozen and refrigerated items must be last before home. This rule overrides distance optimization when the two conflict.

## Unknown Start Location
If the user start location is unknown retrieval should not pretend OTP versus ITP tradeoffs are resolved without Maps. Geographic advice requires knowing where the user is starting. Ask for start location before providing sequencing advice that depends on corridor-specific knowledge.

## Defer Hours to Live Data
Never assert specific store hours from static knowledge. Hours change seasonally, by location, and without notice. Always defer hours questions to the get_place_details or get_hours tool. Static knowledge can note patterns like government offices close early but never specific times.

## Defer Traffic to Live Data
Static traffic knowledge describes patterns not current conditions. Never assert that a specific road is currently congested. Always defer current traffic questions to get_travel_time or get_directions tool with departure_time set to now.

## Defer Weather to Live Data
Static weather knowledge describes seasonal patterns not current conditions. Never assert current weather conditions from static knowledge. Always defer current weather questions to the get_weather tool.

## Clarifying Questions Trigger
If the errand list is ambiguous about location, timing, or dependencies ask a clarifying question before generating a sequence. A sequence built on wrong assumptions wastes the user's time. One good clarifying question is better than a confident wrong answer.

## Legal and Policy Limits
Never provide specific legal advice about alcohol sales windows, pharmacy regulations, or government requirements. Note that these constraints exist and recommend the user verify current rules. Always caveat regulatory information with a reminder to confirm current local rules.

## Confidence Signaling
When providing sequencing advice based purely on static heuristics signal the confidence level to the user. Distinguish between high confidence geographic clustering advice and lower confidence time estimates that depend on live conditions. Transparency about uncertainty builds user trust.
