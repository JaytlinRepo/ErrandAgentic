"""MLflow Layer 2: SQLite tracking store + model / agent / RAG metrics."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MLFLOW_DIR = _PROJECT_ROOT / "data" / "mlflow"
_DEFAULT_SQLITE_DB = _MLFLOW_DIR / "tracking.db"


def _default_tracking_uri() -> str:
    """SQL backend so MLflow Overview (Usage / Quality / Tool calls) works."""
    _MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{_DEFAULT_SQLITE_DB.resolve().as_posix()}"


def _ensure_tracking_store_parent(uri: str) -> None:
    if uri.startswith("sqlite:"):
        path_part = uri.removeprefix("sqlite:///")
        p = Path(path_part)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return
    Path(uri).mkdir(parents=True, exist_ok=True)


def _mlflow_enabled() -> bool:
    return os.environ.get("MLFLOW_ENABLED", "true").lower() in ("1", "true", "yes")


def _tracking_uri() -> str:
    return os.environ.get("MLFLOW_TRACKING_URI", _default_tracking_uri())


class MLFlowTracker:
    def __init__(self) -> None:
        self._enabled = _mlflow_enabled()
        self._uri = _tracking_uri()
        if self._enabled:
            import mlflow

            _ensure_tracking_store_parent(self._uri)
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
            mlflow.set_tag("layer", "agent_session")
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
        agent_model_id: str = "",
        llm_calls: int = 0,
        tool_invocations_total: int = 0,
        tool_usage_json: str = "{}",
        tool_failure_count: int = 0,
        hit_max_tool_rounds: bool = False,
        rag_enabled_config: bool = False,
        rag_general_chunk_count: int = 0,
        rag_user_chunk_count: int = 0,
        rag_general_avg_relevance: float | None = None,
        rag_general_top_relevance: float | None = None,
        rag_user_avg_relevance: float | None = None,
        rag_user_top_relevance: float | None = None,
    ) -> None:
        """Log final I/O and Layer 2 session metrics on the active chat parent run."""
        if not self._enabled:
            return
        import mlflow

        active = mlflow.active_run()
        n_errands = max(len(errands), 1)
        reply_words = len((result or "").split())

        def _log_outputs() -> None:
            mlflow.set_tag("layer", "agent_session")
            mlflow.log_text(full_human_message, "full_prompt_to_model.txt")
            mlflow.log_text(result, "assistant_reply.txt")
            mlflow.log_param("errand_count", len(errands))
            mlflow.log_param("errands", str(errands)[:8000])
            mlflow.log_param("agent_model_id", agent_model_id[:500])
            mlflow.log_metric("session_cost_usd", total_cost)
            mlflow.log_metric("cost_per_errand_line_usd", total_cost / n_errands)
            mlflow.log_metric("llm_calls", float(llm_calls))
            mlflow.log_metric("tool_invocations_total", float(tool_invocations_total))
            mlflow.log_metric("tool_failure_count", float(tool_failure_count))
            mlflow.log_metric("hit_max_tool_rounds", float(int(hit_max_tool_rounds)))
            mlflow.log_param("tool_usage_counts_json", tool_usage_json[:8000])
            mlflow.log_metric("reply_char_count", float(len(result or "")))
            mlflow.log_metric("reply_word_count", float(reply_words))
            mlflow.log_param("rag_enabled_config", str(rag_enabled_config))
            mlflow.log_metric("rag_context_injected", float(rag_general_chunk_count + rag_user_chunk_count > 0))
            mlflow.log_metric("rag_general_chunks", float(rag_general_chunk_count))
            mlflow.log_metric("rag_user_memory_chunks", float(rag_user_chunk_count))
            mlflow.log_metric("rag_total_chunks", float(rag_general_chunk_count + rag_user_chunk_count))
            for name, val in (
                ("rag_general_avg_relevance", rag_general_avg_relevance),
                ("rag_general_top_relevance", rag_general_top_relevance),
                ("rag_user_avg_relevance", rag_user_avg_relevance),
                ("rag_user_top_relevance", rag_user_top_relevance),
            ):
                if val is not None:
                    mlflow.log_metric(name, float(val))
            mlflow.log_param(
                "rag_response_lift",
                "not_measured_use_offline_eval_or_user_ratings",
            )
            if user_satisfied is not None:
                mlflow.log_metric("user_satisfied", float(int(user_satisfied)))

        if active is not None:
            _log_outputs()
            return

        with mlflow.start_run(run_name=f"chat_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            mlflow.set_tag("run_kind", "chat_session")
            mlflow.set_tag("layer", "agent_session")
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
            mlflow.set_tag("layer", "model_usage")
            mlflow.set_tag("model_family", _model_family_tag(model_id))
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
        rag_kind: str,
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
        with mlflow.start_run(run_name=f"rag_{rag_kind}_{datetime.now().strftime('%H%M%S')}", nested=nested):
            mlflow.set_tag("layer", "rag")
            mlflow.set_tag("run_kind", "rag_retrieval")
            mlflow.set_tag("rag_kind", rag_kind)
            mlflow.log_param("rag_kind", rag_kind)
            mlflow.log_param("query", (query or "")[:2000])
            mlflow.log_metric("chunks_retrieved", float(len(chunks_retrieved)))
            if scores:
                mlflow.log_metric("avg_relevance_score", sum(scores) / len(scores))
                mlflow.log_metric("top_relevance_score", max(scores))
                mlflow.log_metric("min_relevance_score", min(scores))
            preview = "\n---\n".join((c[:400] for c in chunks_retrieved[:5]))
            if preview.strip():
                mlflow.log_text(preview, "retrieved_chunks_preview.txt")


def _model_family_tag(model_id: str) -> str:
    mid = (model_id or "").lower()
    if "llama" in mid or "meta.llama" in mid:
        return "llama"
    if "claude" in mid or "anthropic" in mid:
        return "claude"
    return "other"


_tracker: MLFlowTracker | None = None


def get_mlflow_tracker() -> MLFlowTracker:
    global _tracker
    if _tracker is None:
        _tracker = MLFlowTracker()
    return _tracker
