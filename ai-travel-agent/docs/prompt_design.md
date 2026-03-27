# Prompt Design Rules

## Golden Rules
1. Always specify output format explicitly (JSON schema)
2. Always include constraints in the prompt, not just instructions
3. Use few-shot examples for structured outputs
4. Never rely on the model to "figure out" the format

## System Prompt Template
"You are a travel planning expert. You respond ONLY with valid JSON.
No preamble, no explanation, no markdown code blocks. Raw JSON only."

## Prompt Structure Pattern
[ROLE] → [CONTEXT] → [CONSTRAINTS] → [OUTPUT FORMAT] → [EXAMPLE]

## Anti-patterns (never do these)
- ❌ "Give me 5 travel destinations" (too vague)
- ❌ Asking for format AND content in one unclear sentence
- ❌ No example output in the prompt
- ❌ Allowing free-form text when you need JSON

## Temperature Settings
- RecommendationAgent: 0.7 (creative but grounded)
- PlanningAgent: 0.5 (structured, consistent)
- InputAgent: 0.1 (deterministic parsing)