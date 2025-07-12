import logging 
import json
from typing import Any, Dict, Optional

from core.utils import ask_ollama, extract_between
from prompts.prompt_templates import NARRATIVE_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class NarrativeAgent:
    def __init__(self, model_name: str = "llama3:8b"):
        self.model_name = model_name

    def build_prompt(self, action: str, lore: Dict[str, Any], user_feedback: Optional[str] = None) -> str:
        lore_str = self.summarize_lore(lore)
        prompt = NARRATIVE_PROMPT_TEMPLATE.format(
            action=action,
            lore=lore_str,
            user_feedback=user_feedback or "Nessun feedback specifico."
        )
        logger.debug("Built prompt for action '%s': %s...", action, prompt[:200])
        return prompt

    def ask_about_step(
        self,
        action: str,
        lore: Dict[str, Any],
        user_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(action, lore, user_feedback)
        try:
            response = ask_ollama(prompt, model=self.model_name)
            logger.debug("LLM response (truncated): %s...", response[:200])
        except Exception as e:
            logger.error("Error invoking LLM for action '%s': %s", action, e, exc_info=True)
            return {
                "narration": f"Errore generazione narrazione per '{action}'",
                "follow_up_question": "Vuoi proseguire con il passo successivo?",
                "lore_update": {},
            }

        parsed = self.parse_response(response)
        narration = parsed.get("narration") or f"Nessuna narrazione per '{action}'"
        question = parsed.get("follow_up_question") or "Vuoi proseguire con il passo successivo?"
        lore_update = parsed.get("lore_update") or {}

        logger.debug(
            "Parsed result for action '%s': narration='%s', question='%s', lore_update=%s",
            action,
            narration[:50],
            question,
            json.dumps(lore_update)[:100]
        )

        return {
            "narration": narration,
            "follow_up_question": question,
            "lore_update": lore_update,
        }

    def parse_response(self, response: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        try:
            result["narration"] = extract_between(
                response, "=== NARRATION ===", "=== QUESTION ==="
            ).strip()
        except Exception:
            logger.warning("Failed to parse 'narration' from response", exc_info=True)
            result["narration"] = ""

        try:
            result["follow_up_question"] = extract_between(
                response, "=== QUESTION ===", "=== LORE UPDATE ==="
            ).strip()
        except Exception:
            logger.warning("Failed to parse 'follow_up_question' from response", exc_info=True)
            result["follow_up_question"] = ""

        try:
            lore_json = extract_between(response, "=== LORE UPDATE ===", "") or "{}"
            result["lore_update"] = json.loads(lore_json.strip())
        except Exception:
            logger.warning("Failed to parse 'lore_update' as JSON: %s", lore_json, exc_info=True)
            result["lore_update"] = {}

        return result

    def respond_to_feedback(self, user_message: str, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
📜 Current narration:
{state['latest_step'].get('narration', '')}

💬 User feedback:
{user_message}

📖 Lore:
{json.dumps(state.get('lore', {}), indent=2, ensure_ascii=False)}

🎯 Update the narration and/or lore accordingly.
Respond with this format:

=== UPDATED NARRATION ===
<new version>

=== LORE UPDATE ===
<JSON>
"""
        try:
            response = ask_ollama(prompt, model=self.model_name)
            logger.debug("Feedback LLM response: %s", response[:200])
        except Exception as e:
            logger.error("Error during respond_to_feedback: %s", e, exc_info=True)
            return {}

        try:
            new_narration = extract_between(response, "=== UPDATED NARRATION ===", "=== LORE UPDATE ===").strip()
        except Exception:
            logger.warning("Failed to extract UPDATED NARRATION", exc_info=True)
            new_narration = state["latest_step"].get("narration", "")

        try:
            lore_update = extract_between(response, "=== LORE UPDATE ===", "") or "{}"
            lore_update = json.loads(lore_update.strip())
        except Exception:
            logger.warning("Failed to extract LORE UPDATE from feedback response", exc_info=True)
            lore_update = {}

        return {
            "latest_step": {
                **state["latest_step"],
                "narration": new_narration
            },
            "lore_update": lore_update
        }

    def summarize_lore(self, lore: Dict[str, Any]) -> str:
        try:
            s = json.dumps(lore, indent=2, ensure_ascii=False)
            logger.debug("Lore summary length: %d chars", len(s))
            return s
        except Exception as e:
            logger.error("Error serializing lore: %s", e, exc_info=True)
            return "{}"

    def update_lore(self, original_lore: Dict[str, Any], lore_update: Dict[str, Any]) -> Dict[str, Any]:
        def recursive_update(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in updates.items():
                if isinstance(value, dict):
                    base[key] = recursive_update(base.get(key, {}), value)
                else:
                    base[key] = value
            return base

        try:
            updated = recursive_update(original_lore.copy(), lore_update)
            logger.debug("Lore updated with keys: %s", list(lore_update.keys()))
            return updated
        except Exception as e:
            logger.error("Error updating lore: %s", e, exc_info=True)
            return original_lore
