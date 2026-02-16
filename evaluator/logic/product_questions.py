# logic/product_questions.py

from evaluator.logic.llm_intent_fallback import classify_with_llm


def is_product_question_rule(text: str) -> bool:
    """
    Fast rule-based detection for product / process questions.
    """

    t = text.lower().strip()

    product_phrases = [
        # how it works
        "how does this work",
        "how does it work",
        "how do you evaluate",
        "how do u evaluate",
        "how is this evaluated",
        "what is your basis",
        "basis for judgment",

        # what is evaluated
        "what will you evaluate",
        "what do you evaluate",
        "what all do you check",
        "what are you checking",

        # accuracy / reliability
        "how accurate is this",
        "is this accurate",
        "can i trust this",
        "is this reliable",

        # meta / tool identity
        "what is this tool",
        "what is this",
        "what can you do",
        "who are you",
    ]

    return any(phrase in t for phrase in product_phrases)


def is_product_question(text: str) -> bool:
    """
    Detects whether the user is asking about the product/process.
    Uses:
    - Rule-based check first (cheap)
    - LLM fallback only if unclear
    """

    # Guard: very short inputs are never product questions
    if len(text.strip().split()) <= 2:
        return False

    # Stage 1: fast rule-based check
    if is_product_question_rule(text):
        return True

    # Stage 2: LLM fallback (only if ambiguous)
    label = classify_with_llm(text)

    # Convention:
    # "A" = product / process question
    # "B" = property description / answer
    # "C" = real-estate concept question
    return label == "A"
