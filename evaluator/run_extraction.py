import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

from evaluator.logic.product_questions import is_product_question
from evaluator.logic.product_explain import explain_product
from evaluator.logic.intent import classify_intent
from evaluator.logic.explain import explain_concept
from evaluator.logic.missing_fields import find_next_missing_field
from evaluator.scoring.privacy_score_v1 import score_privacy_v1

# -----------------------
# Debug mode
# -----------------------
DEBUG_MODE = True

# -----------------------
# Load API key
# -----------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------
# Load extraction schema
# -----------------------
BASE_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = BASE_DIR / "schemas" / "extraction"

with open(SCHEMA_DIR / "privacy_v1.json", "r") as f:
    privacy_schema = json.load(f)

ALLOWED_FIELDS = {
    "privacy_in_room": {
        "room_size",
        "ceiling_height_ft",
        "window_placement",
        "window_facing_side",
    },
    "privacy_between_rooms": {
        "has_multiple_bedrooms",
        "bedrooms_share_wall",
        "buffer_between_rooms",
        "window_proximity_between_rooms",
    },
    "privacy_between_units": {
        "unit_type",
        "front_open_space",
        "side_a_open_space",
        "side_b_open_space",
        "back_open_space",
        "is_in_gated_society",
        "surrounding_layout_uniformity",
        "distance_between_apartment_doors",
        "apartment_entry_buffer",
    },
}

# -----------------------
# Field-level questions (UX)
# -----------------------
FIELD_QUESTIONS = {
    # Between units
    "unit_type": "Is this an apartment or an independent house?",
    "front_open_space": (
        "What is in front of the room(primary bedroom)? "
    "For example:\n"
    "- Attached to neighbouring unit or to other bedroom.\n"
    "- Narrow gap or tight space between buildings\n"
    "- A Narrow road\n"
    "- A Wide Road im front\n"
    "- A Front Yard\n"
    ),
    "side_a_open_space": (
        "What is along the one side(Side A) of the room(primary)?\n"
    "For example:\n"
    "- Attached to neighbouring unit or to other bedroom.\n"
    "- Narrow gap or tight space between buildings\n"
    "- A side alley or narrow road or a small side yard on side\n"
    "- A road along the side\n"
    "- A private side yard\n"
    ),
    "side_b_open_space":(
        "What is on the other side(Side B) of the room?\n"
    "For example:\n" 
    "- Attached to another unit\n"
    "- Narrow gap or tight space between buildings\n"
    "- A side alley or narrow road or a small side yard on side\n"
    "- A road along the side\n"
    "- A large side yard\n"
    ),

    "back_open_space": (
        "What is behind the room(primary)?\n"
    "- No space / attached to neighbouring unit from behind.\n"
    "- Narrow gap or tight space behind\n"
    "- A back alley or narrow road behind \n"
    "- A larger back road\n"
    "- A private back yard"
        
    ),
    "is_in_gated_society": (
        "Is the property inside a gated or access-controlled society?"
    ),
    "surrounding_layout_uniformity": (
        "Do nearby homes follow a similar layout,mostly uniform or is the layout mixed and irregular?"
    ),
    "distance_between_apartment_doors": (
        "How close are neighboring apartment/house doors on the same floor/street "
        "(very close, moderate, or far apart)"
    ),
    "apartment_entry_buffer": (
        "When you enter the apartment/house, what is the sequence of spaces?\n"
    "For example:\n"
    "- Door opens directly into a room(primary)\n"
    "- Door opens directly into the living/drawing hall\n"
    "- Door opens into a small foyer/lobby(indoors lobby), then into a room(primary)\n"
    "- Door opens into a foyer/lobby, then into the hall/living room\n"
    
    ),
    
    # Between rooms
    "has_multiple_bedrooms": (
        "Are there more than one bedrooms on the floor you want to evaluate?\n"
        "(For example: 1 BHK / studio → no, 2+ bedrooms → yes)"
    ),
    "bedrooms_share_wall": (
        "Do any of the bedroom(primary) share a wall with another bedroom(secondary?"
    ),
    "buffer_between_rooms": (
        "Is there a buffer space between the bedrooms?\n"
    "- No buffer (doors open close to each other)\n"
    "- A small passage\n"
    "- A large lobby\n"
    "- A big hall or living area"
    ),
    "window_proximity_between_rooms": (
        "How are the bedroom(primary and secondary) windows positioned relative to each other?\n"
    "- Very close and facing each other\n"
    "- Close but not facing each other\n"
    "- Far apart but facing each other\n"
    "- Far apart and not facing each other"
    ),

    # In room
    "room_size": "Is the bedroom small, average, or large?",
    "ceiling_height_ft": "What is the approximate ceiling height (average-8 or large-9ft or small-less than 8)?",
    "window_placement": (
        "Is the window on the same wall as the bedroom(primary) door, or away from it?"
    ),
    "window_facing_side":(
        "Which side does the bedroom window face-front,side or back?"
    ),
}

# -----------------------
# Section-level guidance
# -----------------------
FIELD_GUIDANCE = {
    ("privacy_between_units", "__entire_section__"): (
        "To understand privacy between neighboring homes, I look at:\n"
        "- Type of home.(apartment or villa or row houses?)\n"
        "- Open space in front, side, and back.(does front side have narrrow or wide road or front yard?)\n"
        "- Whether it’s in a gated society\n\n"
        "You can describe anything you know about the surroundings."
    ),
    ("privacy_between_rooms", "__entire_section__"): (
        "To try to understand privacy between rooms, I look at:\n"
        "- Whether there are multiple bedrooms on the floor.(one room or multiple)\n"
        "- Whether bedrooms share walls.\n"
        "- Buffer spaces between rooms.(is there a lobby or hall between rooms.\n\n"
        "You can start with any one of these."
    ),
    ("privacy_in_room", "__entire_section__"): (
        "To understand privacy inside a room, I look at:\n"
        "- Room size.(is room size small,average,large?)\n"
        "- Ceiling height.(is ceiling height above 8 or 9 ft or is it less?)\n"
        "- Window placement.(is window on same wall as the door or different?)\n\n"
        "You can start with any one of these."
    ),
}
ATTACHMENT_SPACE_NORMALIZATION = {
    # bedrooms
    "bedroom": "bedroom",
    "master bedroom": "bedroom",
    "guest bedroom": "bedroom",

    # non-bedrooms
    "kitchen": "non_bedroom",
    "hall": "non_bedroom",
    "living room": "non_bedroom",
    "drawing room": "non_bedroom",
    "dining": "non_bedroom",
    "bathroom": "non_bedroom",
    "toilet": "non_bedroom",
    "store": "non_bedroom",

    # common areas
    "corridor": "common_area",
    "lobby": "common_area",
    "staircase": "common_area",
    "lift": "common_area",
    "common corridor": "common_area",
}
def get_attached_sides(between_units: dict, confirmed_fields: set):
    if not between_units:
        return []

    ATTACHABLE_SIDES = {
        "front": "front_open_space",
        "side_a": "side_a_open_space",
        "side_b": "side_b_open_space",
        "back": "back_open_space",
    }

    attached = []

    for side, field in ATTACHABLE_SIDES.items():
        if (
            between_units.get(field) == "attached"
            and ("privacy_between_units", field) in confirmed_fields
        ):
            attached.append(side)

    return attached

    

def extract_attachment_info(text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Interpret the user's message about a wall attachment.\n"
                    "Return JSON with optional fields:\n"
                    "- owner: own_unit | neighbor_unit | null\n"
                    "- space_type: bedroom | non_bedroom | common_area | null\n"
                    "Do not infer side. Do not include any other fields."
                )
            },
            {"role": "user", "content": text}
        ],
        response_format={ "type": "json_object" }
    )

    return json.loads(response.choices[0].message.content)


# -----------------------
# Extraction helper
# -----------------------
def run_extraction(text: str, context: dict | None = None) -> dict:

    context_block = ""

    if context and context.get("last_question"):
        section, field = context["last_question"]
        field_question = context.get("field_question")


        if field == "__entire_section__":
            context_block = f"""
                IMPORTANT CONTEXT:

                The system asked about the section: {section}.
                This was a general guidance message.

                If the user response is vague or short (like "yes", "no"),
                DO NOT assume values for all fields in this section.

                Only extract fields that are explicitly mentioned.
                Do not infer related fields.
                """

        else:
            context_block = f"""
                IMPORTANT CONTEXT:

                The system has asked about:
                Section: {section}
                Field: {field}

                The exact question was:
                "{field_question}"

                If the user's response is short, ambiguous, or generic
                (e.g., "yes", "no", "attached", "big yard", "small", "moderate"),
                you MUST interpret it as referring to the field: {field}.

                Do NOT assign the value to any other field unless the user explicitly overrides it.

                If the response clearly matches the enum options of {field},
                populate ONLY that field.
                """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured property privacy data from user text.\n"
                    "Use null for missing or unknown values.\n"
                    "Do not invent information.\n"
                    "Only use enum values defined in the schema.\n"
                    "Never create new enum values.\n"
                    "You must map user descriptions and try and understand the gist of user message and add to the closest matching enum value.\n"
                    + context_block
                )
            },
            {
                "role": "user",
                "content": text
            }
        ],
        functions=[privacy_schema],
        function_call={"name": privacy_schema["name"]}
    )

    return json.loads(
        response.choices[0].message.function_call.arguments
    )
def normalize_extraction(data: dict) -> dict:
    for section in [
        "privacy_in_room",
        "privacy_between_rooms",
        "privacy_between_units",
    ]:
        if section in data and data[section] is None:
            data[section] = {}

        # 🔥 Convert string "null" to real None
        if section in data:
            for k, v in data[section].items():
                if v == "null":
                    data[section][k] = None
    

    if "apartment_entry_buffer" in data:
        data.setdefault("privacy_between_units", {})
        data["privacy_between_units"]["apartment_entry_buffer"] = data.pop(
            "apartment_entry_buffer"
        )

     # --- Ceiling height normalization ---
    if "privacy_in_room" in data:
        ceiling = data["privacy_in_room"].get("ceiling_height_ft")

        if isinstance(ceiling, str):
            ceiling_lower = ceiling.lower()

            if ceiling_lower in ["small", "low"]:
                data["privacy_in_room"]["ceiling_height_ft"] = 7

            elif ceiling_lower in ["average", "normal"]:
                data["privacy_in_room"]["ceiling_height_ft"] = 8

            elif ceiling_lower in ["large", "high"]:
                data["privacy_in_room"]["ceiling_height_ft"] = 9

    return data

def merge_extraction(base: dict, update: dict):
    for section, section_data in update.items():
        if section not in ALLOWED_FIELDS or not section_data:
            continue

        base.setdefault(section, {})

        for field, value in section_data.items():
            if field not in ALLOWED_FIELDS[section]:
                continue

            if value is not None:
                base[section][field] = value



def evaluate_property(user_input: str):
    """
    Web chatbot step.
    This processes ONE user message and returns:
    - updated extracted state
    - next question OR final score
    """

    extracted = normalize_extraction(run_extraction(user_input))

    return extracted

def run_cli():
    # -----------------------
    # Welcome
    # -----------------------
    print("\n👋 Hey! I’m a property(room specifically) privacy evaluator.")
    print(
        "Tell me about the property you want to evaluate.\n"
        "You can start with anything you know — layout(apartment or villa?),surroundings(inside gated society?).\n"
    )
    # -----------------------
    # Confirmation tracking
    # -----------------------
    confirmed_fields = set()
    attachment_details = {}
    explained_attachment_sides = set()

    
    # -----------------------
    # Initial user input
    # -----------------------
    while True:
        initial_input = input("Your message: ").strip()

        if not initial_input:
            print("\nPlease tell me something about the property.")
            continue

        if is_product_question(initial_input):
            print("\nHere’s how this works:")
            print(explain_product())
            continue

        intent = classify_intent(initial_input)
        if intent == "EXPLANATION":
            print("\nExplanation:")
            print(explain_concept(initial_input))
            continue

        break

    # -----------------------
    # Initial extraction
    # -----------------------
    extracted_privacy = normalize_extraction(run_extraction(initial_input))

    if DEBUG_MODE:
        print("\n=== DEBUG: INITIAL EXTRACTION ===")
        print(json.dumps(extracted_privacy, indent=2))
    # -----------------------
    # Missing-field loop
    # -----------------------
    while True:

        # -----------------------------------------
        # 🔴 ATTACHMENT FOLLOW-UP (SIDE-SPECIFIC)
        # -----------------------------------------
        between_units = extracted_privacy.get("privacy_between_units", {})
        attached_sides = get_attached_sides(between_units, confirmed_fields)

        handled_attachment = False

        for side in attached_sides:
            if side in explained_attachment_sides:
                continue

            side_label = side.replace("_", " ")

            print(f"\nOn the {side_label} side:")

            owner_input = input(
                "Is the wall attached to your own unit or a neighboring unit?\nYour response: "
            ).strip()

            owner_info = extract_attachment_info(owner_input)
            owner = owner_info.get("owner")

            space_input = input(
                "What kind of space is it attached to?\n"
                "- Bedroom\n"
                "- Kitchen or hall\n"
                "- Common corridor / staircase\n"
                "Your response: "
            ).strip()

            space_info = extract_attachment_info(space_input)
            space_type = space_info.get("space_type")

            if owner or space_type:
                extracted_privacy.setdefault("attachment_details", {})
                extracted_privacy["attachment_details"][side] = {
                    "owner": owner,
                    "space_type": space_type,
                }

            explained_attachment_sides.add(side)
            handled_attachment = True

            if DEBUG_MODE:
                print("🔎 Attachment details so far:")
                print(json.dumps(extracted_privacy["attachment_details"], indent=2))

            break  # 🔁 handle ONE side per loop

        # 🔁 Restart loop immediately after attachment handling
        if handled_attachment:
            continue

        # -----------------------------------------
        # 🔵 NORMAL MISSING FIELD FLOW
        # -----------------------------------------
        missing = find_next_missing_field(extracted_privacy, confirmed_fields)

        if not missing:
            break

        section, field = missing
        print("\nI need more info to evaluate privacy accurately.")

        # Section-level guidance (first-time / broad answers)
        guidance = FIELD_GUIDANCE.get((section, field))
        if guidance:
            print("\n" + guidance)
        else:
            # Field-level question
            question = FIELD_QUESTIONS.get(field)
            if question:
                print("\n" + question)
            else:
                print(f"\nI need a bit more detail about {field.replace('_', ' ')}.")

        user_input = input("\nYour response: ").strip()

        # -----------------------
        # Product questions
        # -----------------------
        if is_product_question(user_input):
            print("\nHere’s how this works:")
            print(explain_product())
            continue

        # -----------------------
        # Concept questions
        # -----------------------
        intent = classify_intent(user_input)
        if intent == "EXPLANATION":
            print("\nExplanation:")
            print(explain_concept(user_input))
            continue

        # -----------------------
        # Run extraction
        # -----------------------
        update = normalize_extraction(run_extraction(user_input))

        if DEBUG_MODE:
            print("🔎 Raw extraction:", json.dumps(update, indent=2))

        # 🔁 Merge safely into accumulated state
        merge_extraction(extracted_privacy, update)

        section_data = extracted_privacy.get(section)

        if not section_data:
            print("\nI couldn’t clearly understand that. Could you rephrase or add more context?")
            continue
        
        # =====================================================
        # ✅ SECTION-LEVEL ANSWER (accept partial fields)
        # =====================================================
        if field == "__entire_section__":
            for f, v in section_data.items():
                if v is not None:
                    confirmed_fields.add((section, f))

            print("\nGot it.")
            if DEBUG_MODE:
                print("🔎 Current state:")
                print(json.dumps(extracted_privacy, indent=2))
            continue

        # =====================================================
        # ✅ FIELD-LEVEL ANSWER (strict)
        # =====================================================
        value = section_data.get(field)

        if value is None:
            print("\nI couldn’t clearly understand that. Could you rephrase or add more context by adding full sentence of what u r describing about(eg.instead of saying short answer like- there is no lobby.Can u rephrase it like there is no lobby between the door and bedroom)")
            continue

        confirmed_fields.add((section, field))

        print("\nGot it.")
        if DEBUG_MODE:
            print("🔎 Current state:")
            print(json.dumps(extracted_privacy, indent=2))


    # -----------------------
    # Final scoring
    # -----------------------
    score = score_privacy_v1(extracted_privacy)

    print("\n=== PRIVACY EVALUATION ===")
    print(json.dumps(score, indent=2))

if __name__ == "__main__":
    run_cli()
