# logic/product_explain.py

def explain_product() -> str:
    """
    Explains what the property evaluator does and how it works.
    This is for product / process questions only.
    """

    return (
        "I help evaluate the property quality of a residential property based on its "
    "design, layout, and surroundings.\n\n"

    "In early access,currently focused on room & privacy analysis\n"

    "I look at privacy on three levels:\n"
    "1. Privacy inside rooms (room layout, windows, buffers)\n"
    "2. Privacy between rooms (shared walls, separation, window proximity)\n"
    "3. Privacy between neighboring units or houses (roads, open spaces, distance)\n\n"

    "You don’t need to know everything upfront. You can start with whatever you know, "
    "and I’ll ask for important details step by step.\n\n"

    "Why this evaluation matters:\n"
    "Homes with different privacy characteristics feel very different to live in. "
    "Lower-privacy homes often feel noisier, more exposed, and less comfortable over time, "
    "even if they look good on paper. Higher privacy usually translates to more comfort, "
    "better rest,better social life, fewer daily disturbances, and a higher quality of life.\n\n"

    "The final result is a privacy score (1–10), along with explanations and a confidence "
    "level, so you can understand both the outcome and how reliable the evaluation is.\n\n"

    "Early access disclaimer:\n"
    "This is an early-stage product and still evolving. While I try to be accurate and "
    "consistent, the evaluation may occasionally miss nuances or make imperfect assumptions. "
    "Use this analysis as a decision aid, not a replacement for your own judgment. "
    "Always trust your intuition and on-site experience alongside the score."
)
        
