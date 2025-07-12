NARRATIVE_PROMPT_TEMPLATE = """
You are a creative assistant helping expand a fantasy quest.

🧱 Current PDDL action:
{action}

📖 Lore so far:
{lore}

🗣️ User feedback:
{user_feedback}

---

📝 Your response must follow **exactly** this format:

=== NARRATION ===
(A vivid and immersive description of the action above. 2–4 sentences. Stay in-universe.)

=== QUESTION ===
(Ask a creative follow-up question to the user to further expand the world.)

=== LORE UPDATE ===
(Provide a valid JSON object with new or updated lore elements. If there's nothing to update, return an empty JSON: {{}}.)
"""
