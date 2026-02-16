# logic/explain.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def explain_concept(user_text: str) -> str:
    """
    Explains real-estate / housing concepts in simple terms.
    This is NOT about the app or evaluation process.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a real-estate and housing design expert.\n"
                    "Explain concepts related to residential properties, "
                    "home design, layout, privacy, noise, space, and living comfort.\n\n"
                    "Rules:\n"
                    "- Do NOT explain any app, tool, or evaluation process\n"
                    "- Do NOT mention scoring or ratings\n"
                    "- Answer like you are explaining to a home buyer\n"
                    "- Keep explanations practical and easy to understand\n"
                )
            },
            {
                "role": "user",
                "content": user_text
            }
        ]
    )

    return response.choices[0].message.content.strip()
