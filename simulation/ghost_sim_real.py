"""
Ghost Simulator - Parallel "What-If" simulation.
Validates proposed changes by querying the local LLM for safety analysis.
"""
from typing import Dict, Any, Optional, List
import logging

from src.core.llm.tsm_inference import get_tsm_client

logger = logging.getLogger(__name__)


class GhostSimulator:
    """
    Runs simulations of proposed changes or scenarios in a parallel/shadow environment.
    Uses the local LLM (TSM inference) to evaluate safety, with heuristic fallback.
    """

    def __init__(self):
        self._tsm_available: Optional[bool] = None

    def simulate_scenario(self, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a proposed change by querying the LLM for risk assessment.
        Falls back to heuristic checks if TSM Runtime is unavailable.
        """
        change_type = scenario_config.get("type", "unknown")
        description = scenario_config.get("description", change_type)
        logger.info(f"Starting Ghost Simulation for scenario: {change_type}")

        # Try LLM-based evaluation first
        llm_result = self._evaluate_via_llm(scenario_config)
        if llm_result is not None:
            return llm_result

        # Heuristic evaluation when LLM is unavailable
        return self._evaluate_heuristic(scenario_config)

    def _evaluate_via_llm(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ask the local LLM to evaluate safety of a proposed change."""
        change_type = config.get("type", "unknown")
        description = config.get("description", change_type)
        files = config.get("files_touched", [])
        rollback = config.get("rollback_strategy", "none")

        try:
            prompt = (
                f"You are a system safety evaluator. Evaluate this proposed change:\n"
                f"Type: {change_type}\n"
                f"Description: {description}\n"
                f"Files affected: {', '.join(files) if files else 'unknown'}\n"
                f"Rollback strategy: {rollback}\n\n"
                f"Respond with a JSON object: "
                f'{{\"safe\": true/false, \"risk_score\": 0.0-1.0, \"reason\": \"...\"}}'
            )
            result = get_tsm_client().generate(prompt=prompt, model="llama3.2", max_tokens=512)
            text = result.text.strip()
            if text:
                import json
                # Extract JSON from response
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(text[start:end])
                    is_safe = parsed.get("safe", True)
                    risk_score = float(parsed.get("risk_score", 0.1))
                    reason = parsed.get("reason", "")

                    logger.info(f"LLM safety eval: safe={is_safe}, risk={risk_score:.2f}, reason={reason}")
                    return {
                        "status": "simulated",
                        "outcome": "success" if is_safe else "failure",
                        "details": reason or (f"Low risk ({risk_score:.2f})" if is_safe else f"High risk ({risk_score:.2f})"),
                        "risk_score": risk_score,
                        "evaluation_method": "llm",
                    }
        except Exception as e:
            logger.debug(f"TSM inference evaluation unavailable: {e}")

        return None

    def _evaluate_heuristic(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristic safety evaluation based on change metadata."""
        change_type = config.get("type", "unknown")
        has_tests = bool(config.get("tests") or config.get("test_coverage"))
        has_rollback = bool(config.get("rollback_strategy"))
        files_count = len(config.get("files_touched", []))
        blast_radius = config.get("blast_radius", "unknown")

        risk_score = 0.1  # base risk

        # Accumulate risk factors
        if not has_tests:
            risk_score += 0.2
        if not has_rollback:
            risk_score += 0.15
        if files_count > 10:
            risk_score += 0.1
        if blast_radius in ("high", "critical"):
            risk_score += 0.2
        if change_type == "hotfix_apply":
            risk_score += 0.1
        elif change_type == "infrastructure_scaling":
            risk_score -= 0.05  # scaling is generally safe

        risk_score = max(0.0, min(1.0, risk_score))
        is_safe = risk_score < 0.5

        details = []
        if not has_tests:
            details.append("no tests")
        if not has_rollback:
            details.append("no rollback strategy")
        if files_count > 10:
            details.append(f"{files_count} files affected")

        logger.info(f"Heuristic safety eval: safe={is_safe}, risk={risk_score:.2f}, factors={details}")

        return {
            "status": "simulated",
            "outcome": "success" if is_safe else "failure",
            "details": f"Risk factors: {', '.join(details)}" if details else "No risk factors identified",
            "risk_score": risk_score,
            "evaluation_method": "heuristic",
        }
