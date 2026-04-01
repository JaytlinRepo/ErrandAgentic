"""MLflow tracking for model calls, RAG retrieval, and agent sessions."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _mlflow_enabled() -> bool:
    return os.environ.get("MLFLOW_ENABLED", "true").lower() in ("1", "true", "yes")


def _tracking_uri() -> str:
    return os.environ.get(
        "MLFLOW_TRACKING_URI",
        str(_PROJECT_ROOT / "data" / "mlflow"),
    )


class MLFlowTracker:
    def __init__(self) -> None:
        self._enabled = _mlflow_enabled()
        self._uri = _tracking_uri()
        if self._enabled:
            import mlflow

            Path(self._uri).mkdir(parents=True, exist_ok=True)
            mlflow.set_tracking_uri(self._uri)
            mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "errand-sequencer"))

    @property
    def enabled(self) -> bool:
        return self._enabled

    @staticmethod
    def _nested_child_run() -> bool:
        import mlflow

        return mlflow.active_run() is not None

    @contextmanager
    def chat_session_context(self, *, raw_user_input: str):
        """Parent run for one agent turn: filter MLflow UI by tag run_kind=chat_session."""
        if not self._enabled:
            yield
            return
        import mlflow

        run_name = f"chat_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with mlflow.start_run(run_name=run_name):
            mlflow.set_tag("run_kind", "chat_session")
            mlflow.set_tag("surface", "errand_agent")
            mlflow.log_text(raw_user_input or "", "user_input.txt")
            mlflow.log_param("user_input_preview", (raw_user_input or "")[:500])
            yield

    def finalize_chat_session(
        self,
        *,
        full_human_message: str,
        errands: list[str],
        result: str,
        total_cost: float,
        user_satisfied: bool | None = None,
    ) -> None:
        """Log final I/O on the active chat parent run (or a standalone run if none)."""
        if not self._enabled:
            return
        import mlflow

        active = mlflow.active_run()

        def _log_outputs() -> None:
            mlflow.log_text(full_human_message, "full_prompt_to_model.txt")
            mlflow.log_text(result, "assistant_reply.txt")
            mlflow.log_param("errand_count", len(errands))
            mlflow.log_param("errands", str(errands)[:8000])
            mlflow.log_metric("session_cost_usd", total_cost)
            if user_satisfied is not None:
                mlflow.log_metric("user_satisfied", float(int(user_satisfied)))

        if active is not None:
            _log_outputs()
            return

        with mlflow.start_run(run_name=f"chat_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            mlflow.set_tag("run_kind", "chat_session")
            mlflow.set_tag("surface", "errand_agent")
            mlflow.set_tag("orphan", "true")
            mlflow.log_text((errands and "\n".join(errands)) or "", "user_input.txt")
            _log_outputs()

    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        return self._estimate_cost(model_id, input_tokens, output_tokens)

    def log_model_call(
        self,
        *,
        model_type: str,
        model_id: str,
        prompt: str,
        response: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        tools_used: list[str] | None = None,
    ) -> None:
        if not self._enabled:
            return
        import mlflow

        run_name = f"{model_type}_{datetime.now().strftime('%H%M%S')}"
        nested = self._nested_child_run()
        with mlflow.start_run(run_name=run_name, nested=nested):
            mlflow.log_param("model_type", model_type)
            mlflow.log_param("model_id", model_id)
            mlflow.log_metric("input_tokens", float(input_tokens))
            mlflow.log_metric("output_tokens", float(output_tokens))
            mlflow.log_metric("total_tokens", float(input_tokens + output_tokens))
            cost = self._estimate_cost(model_id, input_tokens, output_tokens)
            mlflow.log_metric("estimated_cost_usd", cost)
            mlflow.log_metric("latency_ms", latency_ms)
            if tools_used:
                mlflow.log_param("tools_used", str(tools_used))
                mlflow.log_metric("tool_call_count", float(len(tools_used)))
            mlflow.log_text(prompt, "prompt.txt")
            mlflow.log_text(response, "response.txt")

    def _estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        pricing: dict[str, dict[str, float]] = {
            "meta.llama3-8b-instruct-v1:0": {"input": 0.0003, "output": 0.0006},
            "anthropic.claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
            "us.anthropic.claude-haiku-4-5-20251001-v1:0": {"input": 0.001, "output": 0.005},
        }
        rates = pricing.get(model_id, {"input": 0.001, "output": 0.005})
        return (input_tokens / 1000.0 * rates["input"]) + (
            output_tokens / 1000.0 * rates["output"]
        )

    def log_rag_retrieval(
        self,
        *,
        query: str,
        chunks_retrieved: list[str],
        scores: list[float] | None,
    ) -> None:
        if not self._enabled:
            return
        if os.environ.get("MLFLOW_LOG_RAG", "true").lower() not in ("1", "true", "yes"):
            return
        import mlflow

        nested = self._nested_child_run()
        with mlflow.start_run(run_name=f"rag_{datetime.now().strftime('%H%M%S')}", nested=nested):
            mlflow.log_param("query", (query or "")[:2000])
            mlflow.log_metric("chunks_retrieved", float(len(chunks_retrieved)))
            if scores:
                mlflow.log_metric("avg_relevance_score", sum(scores) / len(scores))
                mlflow.log_metric("top_score", max(scores))

_tracker: MLFlowTracker | None = None


def get_mlflow_tracker() -> MLFlowTracker:
    global _tracker
    if _tracker is None:
        _tracker = MLFlowTracker()
    return _tracker
