# logic/intent.py

def classify_intent(text: str) -> str:
    """
    Classifies user intent into:
    - EXPLANATION: asking about real-estate / housing concepts
    - CONTINUE_ANYWAY: wants to skip missing details
    - ANSWER: provides information or description (default)
    """

    t = text.lower().strip()

    # --------------------------------------------------
    # CONTINUE / SKIP INTENT
    # --------------------------------------------------
    continue_phrases = [
        "continue anyway",
        "just evaluate",
        "just check",
        "do it",
        "do it anyway",
        "skip",
        "doesn't matter",
        "not sure",
        "you decide",
    ]

    if any(p in t for p in continue_phrases):
        return "CONTINUE_ANYWAY"

    # --------------------------------------------------
    # EXPLANATION INTENT (DOMAIN CONCEPTS ONLY)
    # --------------------------------------------------
    explanation_triggers = [
        "what is",
        "what does",
        "what do you mean",
        "meaning of",
        "explain",
        "how does",
        "how do",
        "why does",
        "why is",
    ]

    # Avoid catching answers like "8 ft", "small room", etc.
    if len(t.split()) >= 3 and any(p in t for p in explanation_triggers):
        return "EXPLANATION"

    # --------------------------------------------------
    # DEFAULT: ANSWER / DESCRIPTION
    # --------------------------------------------------
    return "ANSWER"
