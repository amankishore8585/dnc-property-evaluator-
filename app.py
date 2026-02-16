from flask import Flask, render_template, request, session ,jsonify
from evaluator.run_extraction import (
    run_extraction,
    normalize_extraction,
    merge_extraction,
    FIELD_QUESTIONS,
    FIELD_GUIDANCE,
    get_attached_sides,
    extract_attachment_info
)
from evaluator.logic.missing_fields import find_next_missing_field
from evaluator.scoring.privacy_score_v1 import score_privacy_v1
from evaluator.logic.product_questions import is_product_question
from evaluator.logic.product_explain import explain_product
from evaluator.logic.intent import classify_intent
from evaluator.logic.explain import explain_concept
import json
from flask_session import Session
import os
from dotenv import load_dotenv
load_dotenv()



app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY is not set in environment variables")


# -----------------------
# Server-side Session Config
# -----------------------
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_FILE_DIR"] = "./flask_session"
app.config["SESSION_FILE_THRESHOLD"] = 100
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # Set to True when using HTTPS


os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

Session(app)


DEBUG_MODE = False

def get_question(section, field):
    if field == "__entire_section__":
        return FIELD_GUIDANCE.get((section, field), "Could you tell me more?")
    return FIELD_QUESTIONS.get(field, f"Tell me more about {field.replace('_',' ')}")


@app.route("/", methods=["GET", "POST"])
def chatbot():

    # -----------------------
    # FIRST LOAD
    # -----------------------
    if request.method == "GET":
        session.clear()

        session["messages"] = [
            {
                "role": "assistant",
                "content": (
                    "👋 Hi! I’m a property evaluator.In early access I try to evaluate privacy of a primary room with respect to its own unit(secondary rooms) and and neighbours unit .\n\n"
                    
                    "Describe the property you want to evaluate.\n"
                    "You can start with layout (is it an apartment or villa), surroundings "
                    "(is the property on gated society or not?), or ask about any real estate topic.\n\n"
                    "If you are confused just type -'how does it work?"

                )
            }
        ]

        return render_template(
            "chat.html",
            messages=session["messages"]
        )

    # -----------------------
    # SESSION INIT
    # -----------------------
    extracted = session.get("extracted", {})
    confirmed = set(tuple(x) for x in session.get("confirmed", []))
    last_question = session.get("last_question")

    user_input = request.form.get("message", "").strip()
    messages = session.get("messages", [])

    messages.append({
        "role": "user",
        "content": user_input
    })
    session["messages"] = messages

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if DEBUG_MODE:
        print("\n==============================")
        print("USER INPUT:", user_input)
        print("CURRENT EXTRACTED:", json.dumps(extracted, indent=2))
        print("CONFIRMED:", confirmed)

    if not user_input:
        messages = session.get("messages", [])

        messages.append({
            "role": "assistant",
            "content": "Please describe something about the property so we can continue."
        })

        session["messages"] = messages

        if is_ajax:
            return jsonify({"messages": messages})
        return render_template("chat.html", messages=messages)


    # -----------------------
    # PRODUCT / EXPLANATION OVERRIDES
    # -----------------------
    if is_product_question(user_input):
        # Decide what the next question would be
        missing = find_next_missing_field(extracted, confirmed)

        if missing:
            section, field = missing
            follow_up = get_question(section, field)
            session["last_question"] = (section, field)
        else:
            follow_up = "You can continue describing the property."

        assistant_reply = (
        explain_product()
        + "\n\n—\n\n"
        + follow_up
        )

        messages.append({
            "role": "assistant",
            "content": assistant_reply
        })

        session["messages"] = messages

        if is_ajax:
            return jsonify({"messages": messages})
        return render_template("chat.html", messages=messages)
    
    # -----------------------
    # QUICK EXPLANATION KEYWORD OVERRIDE
    # -----------------------
    lower_input = user_input.lower().strip()

    explanation_phrases = [
        "what is",
        "what's",
        "whats",
        "what does",
        "meaning of",
        "meaning",
        "define",
        "explain",
        "means"
    ]

    # Trigger if explanation phrases present
    is_explanation = any(p in lower_input for p in explanation_phrases)

    # Also trigger for short question-style inputs like:
    # "foyer?", "buffer?", "lobby?"
    if not is_explanation:
        if lower_input.endswith("?") and len(lower_input.split()) <= 4:
            is_explanation = True

    if is_explanation:
        missing = find_next_missing_field(extracted, confirmed)

        if missing:
            section, field = missing
            follow_up = get_question(section, field)
            session["last_question"] = (section, field)
        else:
            follow_up = "You can continue describing the property."

        assistant_reply = (
            explain_concept(user_input)
            + "\n\n—\n\n"
            + follow_up
        )

        messages.append({
            "role": "assistant",
            "content": assistant_reply
        })

        session["messages"] = messages

        if is_ajax:
            return jsonify({"messages": messages})
        return render_template("chat.html", messages=messages)


    intent = classify_intent(user_input)
    if intent == "EXPLANATION":
        missing = find_next_missing_field(extracted, confirmed)

        if missing:
            section, field = missing
            follow_up = get_question(section, field)
            session["last_question"] = (section, field)
        else:
            follow_up = "You can continue describing the property."

        assistant_reply = (
            explain_concept(user_input)
            + "\n\n—\n\n"
            + follow_up
        )

        messages.append({
            "role": "assistant",
            "content": assistant_reply
        })

        session["messages"] = messages

        if is_ajax:
            return jsonify({"messages": messages})
        return render_template("chat.html", messages=messages)

    # -----------------------------------------
    # HANDLE PENDING ATTACHMENT RESPONSE
    # -----------------------------------------
    pending_side = session.get("pending_attachment_side")

    if pending_side:
        info = extract_attachment_info(user_input)

        owner = info.get("owner")
        space_type = info.get("space_type")

        if owner or space_type:
            extracted.setdefault("attachment_details", {})
            extracted["attachment_details"][pending_side] = {
                "owner": owner,
                "space_type": space_type,
            }
        # ✅ Confirm the open-space field now that attachment is resolved
        confirmed.add(("privacy_between_units", f"{pending_side}_open_space"))
        session["confirmed"] = list(confirmed)
    
        explained = set(session.get("explained_attachment_sides", []))
        explained.add(pending_side)

        session["explained_attachment_sides"] = list(explained)
        session.pop("pending_attachment_side")

        session["extracted"] = extracted

        if DEBUG_MODE:
            print("UPDATED ATTACHMENTS:", json.dumps(extracted.get("attachment_details", {}), indent=2))

        missing = find_next_missing_field(extracted, confirmed)

        if not missing:
            if DEBUG_MODE:
                print("FINAL STATE BEFORE SCORING:", json.dumps(extracted, indent=2))

            score = score_privacy_v1(extracted)
            session.clear()
            return render_template("result.html", score=score, extracted=extracted)

        section, field = missing
        session["last_question"] = (section, field)

        messages = session.get("messages", [])

        assistant_reply = get_question(section, field)

        messages.append({
            "role": "assistant",
            "content": assistant_reply
        })

        session["messages"] = messages

        if is_ajax:
            return jsonify({"messages": messages})
        return render_template("chat.html", messages=messages)

    # -----------------------
    # RUN EXTRACTION (ONCE)
    # -----------------------
    context = {}

    if session.get("last_question"):
        section, field = session.get("last_question")
        context = {
            "last_question": (section, field),
            "field_question": get_question(section, field)
        }

    update = normalize_extraction(
        run_extraction(user_input, context=context)
    )


    if DEBUG_MODE:
        print("RAW EXTRACTION UPDATE:", json.dumps(update, indent=2))

    meaningful = any(
        section_data and any(v is not None for v in section_data.values())
        for section_data in update.values()
    )

    if not meaningful:

        messages = session.get("messages", [])

        missing = find_next_missing_field(extracted, confirmed)

        if missing:
            section, field = missing
            follow_up = get_question(section, field)
        else:
            follow_up = "Please continue describing the property."

        assistant_reply = (
            "I couldn’t clearly understand that.\n\n"
            "Could you rephrase it with a bit more detail?\n"
            "For example, describe the space instead of a short phrase like yes or no. "
            "Say something like: 'Yes, the window is present.'"
            "Or if you want me to explain a concept -phrase it like 'what is a foyer?'"
            "\n\n—\n\n"
            + follow_up
        )

        messages.append({
            "role": "assistant",
            "content": assistant_reply
        })

        session["messages"] = messages

        if is_ajax:
            return jsonify({"messages": messages})
        return render_template("chat.html", messages=messages)



    # -----------------------
    # MERGE UPDATE
    # -----------------------
    merge_extraction(extracted, update)

    if DEBUG_MODE:
        print("STATE AFTER MERGE:", json.dumps(extracted, indent=2))
    
    # -----------------------
    # CONFIRM LAST ASKED FIELD ONLY
    # -----------------------
    if last_question:
        sec, fld = last_question
        if update.get(sec) and update[sec].get(fld) is not None:
            confirmed.add((sec, fld))    

    # -----------------------------------------
    # ATTACHMENT FOLLOW-UP (SIDE-SPECIFIC)
    # -----------------------------------------
    explained = set(session.get("explained_attachment_sides", []))
    between_units = extracted.get("privacy_between_units", {})

    attached_sides = get_attached_sides(between_units, confirmed)

    if DEBUG_MODE:
        print("ATTACHED SIDES:", attached_sides)

    for side in attached_sides:
        if side in explained:
            continue

        # Ask attachment question
        session["pending_attachment_side"] = side
        session["explained_attachment_sides"] = list(explained)

        messages = session.get("messages", [])

        assistant_reply = (
            f"On the {side.replace('_',' ')} side:\n\n"
            "Is the wall attached to your own unit or a neighboring unit?\n"
            "And what kind of space is it attached to?\n"
            "(bedroom / kitchen / hall / corridor)"
        )

        messages.append({
            "role": "assistant",
            "content": assistant_reply
        })

        session["messages"] = messages

        if is_ajax:
            return jsonify({"messages": messages})
        return render_template("chat.html", messages=messages)


    # -----------------------
    # FIND NEXT QUESTION
    # -----------------------
    missing = find_next_missing_field(extracted, confirmed)

    if DEBUG_MODE:
        print("NEXT MISSING:", missing)

    session["extracted"] = extracted
    session["confirmed"] = list(confirmed)

    # -----------------------
    # DONE → SCORE
    # -----------------------
    if not missing:

        if DEBUG_MODE:
            print("FINAL STATE BEFORE SCORING:", json.dumps(extracted, indent=2))
        
        score = score_privacy_v1(extracted)

        # Store result in session for later rendering
        session["final_score"] = score
        session["final_extracted"] = extracted

        if is_ajax:
            return jsonify({
                "redirect": "/result"
            })

        return render_template(
            "result.html",
            score=score,
            extracted=extracted,
        )


    # -----------------------
    # ASK NEXT QUESTION
    # -----------------------
    section, field = missing
    session["last_question"] = (section, field)

    messages = session.get("messages", [])

    assistant_reply = get_question(section, field)

    messages.append({
        "role": "assistant",
        "content": assistant_reply
    })

    session["messages"] = messages

    if is_ajax:
            return jsonify({"messages": messages})
    return render_template("chat.html", messages=messages)

@app.route("/result")
def result():
    score = session.get("final_score")
    extracted = session.get("final_extracted")

    if not score:
        return "No result available."

    return render_template(
        "result.html",
        score=score,
        extracted=extracted
    )


if __name__ == "__main__":
    app.run(debug=True)




