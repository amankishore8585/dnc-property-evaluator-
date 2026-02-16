# logic/llm_intent_fallback.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def classify_with_llm(user_text: str) -> str:
    """
    Uses LLM to classify ambiguous user input into one of:
    A = product / process question
    B = property description or answer
    C = real-estate concept question
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an intent classifier for a property evaluation assistant.\n\n"
                    "Classify the user's message into exactly ONE category:\n\n"
                    "A = Question about the tool, process, scoring, or reliability\n"
                    "B = Description of a property or answer to a question about the property\n"
                    "C = Question about real-estate or housing concepts (privacy, layout, design)\n\n"
                    "Rules:\n"
                    "- Reply with ONLY a single letter: A, B, or C\n"
                    "- Do NOT explain your choice\n"
                    "- Do NOT add punctuation or text\n"
                )
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        temperature=0
    )

    label = response.choices[0].message.content.strip().upper()

    # Safety fallback
    if label not in {"A", "B", "C"}:
        return "B"

    return label
