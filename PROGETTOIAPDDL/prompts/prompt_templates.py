NARRATIVE_PROMPT_TEMPLATE = """
You are a creative assistant helping expand a fantasy quest.

🧱 Current PDDL action:
{action}

📖 Lore so far:
{lore}

🗣️ User feedback:
{user_feedback}

---

Your output **must** be in this format:

=== NARRATION ===
<Narrative description of this action, immersive, 2-3 sentences>

=== QUESTION ===
<A follow-up question to enrich this step (e.g., "Does the sword have powers?")>

=== LORE UPDATE ===
<If relevant, provide JSON representing additions to the lore>
"""
