def attachment_effect(owner, space_type):
    if owner == "neighbor_unit" and space_type == "bedroom":
        return 0.15, None, "Bedroom wall attached to a neighboring bedroom severely reduces acoustic privacy"
    if owner == "neighbor_unit" and space_type == "non_bedroom":
        return 0.10, None, "Bedroom wall attached to a neighboring unit reduces privacy"
    if owner == "neighbor_unit" and space_type == "common_area":
        return 0.08, None, "Bedroom wall adjacent to a shared common corridor or lobby reduces privacy"
    if owner == "neighbor_unit" and space_type is None:
        return 0.14, None, "Wall attached to neighboring unit reduces privacy"

    
    if owner == "own_unit" and space_type == "bedroom":
        return 0.0, None, "Bedrooms within the same apartment sharing walls reduce internal privacy"
    if owner == "own_unit" and space_type == "non_bedroom":
        return 0.0, "Bedroom wall attached to another room within the apartment avoids external noise intrusion", None
    if owner == "own_unit" and space_type == "common_area":
        return 0.0, None, "Bedroom wall adjacent to an internal lobby or corridor slightly reduces privacy"

    return 0.0, None, None


def score_privacy_v1(extracted: dict):
    strengths = []
    concerns = []
    known_fields = 0
    total_fields = 0

    # =====================================================
    # PRIVACY IN ROOM (25%)
    # =====================================================
    in_room = extracted.get("privacy_in_room") or {}
    in_room_score = 0.85

    in_room_fields = [
        "room_size",
        "ceiling_height_ft",
        "window_placement",
        "window_facing_side"
    ]

    for field in in_room_fields:
        total_fields += 1
        if in_room.get(field) is not None:
            known_fields += 1

    if in_room.get("room_size") == "small":
        in_room_score -= 0.25
        concerns.append("Small bedroom size reduces personal privacy")

    if in_room.get("ceiling_height_ft") is not None:
        if in_room.get("ceiling_height_ft") <= 8:
            in_room_score -= 0.15
            concerns.append("Low ceiling height can feel more enclosed")

    
    if in_room.get("window_placement") == "door_wall":
        in_room_score -= 0.25
        concerns.append(
            "Window on the same wall as the door reduces visual privacy"
        )

    in_room_score = max(min(in_room_score, 1), 0)

    # =====================================================
    # PRIVACY BETWEEN ROOMS (30%)
    # =====================================================
    between_rooms = extracted.get("privacy_between_rooms") or {}

    # 🔑 Gate: does this section even apply?
    has_multiple = between_rooms.get("has_multiple_bedrooms")

    # Count confidence fields
    total_fields += 1
    if has_multiple is not None:
        known_fields += 1

    # -----------------------------------------------------
    # 🚫 NOT APPLICABLE: single-bedroom / studio
    # -----------------------------------------------------
    if has_multiple is False:
        # Neutral score: no between-room privacy issues possible
        between_rooms_score = 1.0

    else:
        # -------------------------------------------------
        # ✅ APPLICABLE: multiple bedrooms
        # -------------------------------------------------
        between_rooms_score = 0.85

        between_rooms_fields = [
            "bedrooms_share_wall",
            "buffer_between_rooms",
            "window_proximity_between_rooms"
        ]

        for field in between_rooms_fields:
            total_fields += 1
            if between_rooms.get(field) is not None:
                known_fields += 1

        # ---- Shared wall penalty
        if between_rooms.get("bedrooms_share_wall") is True:
            between_rooms_score -= 0.35
            concerns.append(
                "Bedrooms sharing a wall reduces acoustic privacy"
            )

        # ---- Buffer bonus
        buffer = between_rooms.get("buffer_between_rooms")

        
        if buffer == "small_passage":
            between_rooms_score -= 0.05
            concerns.append(
                "Only a small passage separates bedrooms, offering limited privacy buffering"
            )


        elif buffer == "large_lobby":
            between_rooms_score += 0.12
            strengths.append(
                "Large lobby between bedrooms significantly improves privacy"
            )

        elif buffer == "big_hall":
            between_rooms_score += 0.18
            strengths.append(
                "Big hall between bedrooms offers strong visual and acoustic privacy"
            )


        # ---- Window proximity penalty
        window_relation = between_rooms.get("window_proximity_between_rooms")

        if window_relation == "close_facing_each_other":
            between_rooms_score -= 0.25
            concerns.append(
                "Bedroom windows close and facing each other allow sound and visual intrusion"
            )

        elif window_relation == "close_not_facing":
            between_rooms_score -= 0.12
            concerns.append(
                "Bedroom windows are close, which can still transmit sound"
            )

        elif window_relation == "far_apart_facing":
            between_rooms_score -= 0.08
            concerns.append(
                "Bedroom windows face each other even though they are far apart"
            )

        elif window_relation == "far_apart_not_facing":
            between_rooms_score += 0.05
            strengths.append(
                "Bedroom windows are well separated and not facing each other"
            )

        between_rooms_score = max(min(between_rooms_score, 1), 0)


    # =====================================================
    # PRIVACY BETWEEN UNITS (45%)
    # =====================================================
    between_units = extracted.get("privacy_between_units") or {}
    between_units_score = 0.75
    attachment_details = extracted.get("attachment_details", {})


    between_units_fields = [
        "unit_type",
        "front_open_space",
        "side_a_open_space",
        "side_b_open_space",
        "back_open_space",
        "is_in_gated_society",
        "surrounding_layout_uniformity",
        "distance_between_apartment_doors",
        "apartment_entry_buffer",

    ]

    for field in between_units_fields:
        total_fields += 1
        if between_units.get(field) is not None:
            known_fields += 1

    unit_bonus = 0.0
    structural_penalty = 0.0

    # ---- Apartment baseline penalty
    if between_units.get("unit_type") == "apartment":
        between_units_score -= 0.05
        concerns.append(
            "Shared apartment living slightly reduces overall privacy"
        )

    # ---- Front open space
    front = between_units.get("front_open_space")
    if front == "attached":
        # Do nothing here.
        # Attachment penalty handled later in attachment_effect().
        pass


    elif front in ["tight_service_gap", "narrow_gap"]:
        structural_penalty += 0.15
        concerns.append(
            "Very narrow front gap provides limited privacy buffer"
        )

    elif front == "narrow_road":
        between_units_score -= 0.12
        concerns.append(
            "Bedroom faces a narrow road, limiting privacy"
        )

    elif front == "wide_road":
        unit_bonus += 0.03
        strengths.append(
            "Wide road in front provides some separation"
        )

    elif front == "front_yard":
        unit_bonus += 0.06
        strengths.append(
            "Front yard provides a visual buffer from the street"
        )


    def side_penalty(side_key, side_value, attachment_details):

        # Attached → inspect ownership
        if side_value == "attached":
            return 0.0, None


        if side_value in ["tight_service_gap", "narrow_gap"]:
            return 0.12, "Very narrow side gap provides limited privacy"

        if side_value in ["side_alley", "narrow_road","small_side_yard"]:
            return -0.02, None

        if side_value in ["side_road", "large_side_yard"]:
            return -0.06, None

        return 0.0, None

    
    side1 = between_units.get("side_a_open_space")
    side2 = between_units.get("side_b_open_space")

    side_results = [
    side_penalty("side_a", side1, attachment_details),
    side_penalty("side_b", side2, attachment_details),
    ]

    penalties = [r[0] for r in side_results]
    messages = [r[1] for r in side_results if r[1]]

    worst_penalty = max(penalties)

    if worst_penalty > 0:
        structural_penalty += worst_penalty
        concerns.append(messages[penalties.index(worst_penalty)])
    elif worst_penalty < 0:
        between_units_score += abs(worst_penalty)
        strengths.append("Good side open space improves lateral privacy")


    # ---- Back open space (STRUCTURAL)
    back = between_units.get("back_open_space")

    if back == "attached":
        pass


    elif back in ["tight_service_gap", "narrow_gap"]:
        structural_penalty += 0.15
        concerns.append(
            "Very narrow rear gap provides limited privacy buffer"
        )

    elif back in ["back_alley", "narrow_road"]:
        between_units_score -= 0.10
        concerns.append(
            "Rear alley or narrow road offers limited privacy separation"
        )   

    elif back in ["back_road"]:
        between_units_score -= 0.05
        concerns.append(
            "Rear road reduces privacy despite some separation"
        )

    elif back == "private_backyard":
        unit_bonus += 0.10
        strengths.append(
            "Private backyard significantly improves rear privacy"
        )

    # ---- Gated society
    if between_units.get("is_in_gated_society") is True:
        unit_bonus += 0.07
        strengths.append(
            "Gated society improves privacy through controlled access"
        )

    # ---- Surrounding layout
    layout = between_units.get("surrounding_layout_uniformity")
    if layout == "uniform_layout":
        unit_bonus += 0.05
        strengths.append(
            "Uniform surrounding layout reduces visual and noise intrusion"
        )
    elif layout == "mostly_uniform":
        unit_bonus += 0.02
        strengths.append(
            "Mostly uniform surrounding layout offers consistency"
        )
    elif layout == "mixed_layout":
        between_units_score -= 0.04
        concerns.append(
            "Mixed surrounding layout can increase visual and noise exposure"
        )
    
    elif layout == "irregular_layout":
        between_units_score -= 0.08
        concerns.append(
            "Irregular surrounding layout can increase privacy intrusion"
        )

    # ---- Apartment door spacing
    if between_units.get("unit_type") == "apartment":
        door_distance = between_units.get("distance_between_apartment_doors")
        if door_distance == "very_close":
            structural_penalty += 0.10
            concerns.append(
                "Very close apartment doors reduce corridor privacy"
            )
        elif door_distance == "moderate":
            between_units_score -= 0.03
            concerns.append(
                "Moderate distance between apartment doors limits separation"
            )
        elif door_distance == "far_apart":
            unit_bonus += 0.05
            strengths.append(
                "Greater distance between apartment doors improves privacy"
            )

    # ---- Apartment entry buffer (NEW)
    if between_units.get("unit_type") == "apartment":
        entry = between_units.get("apartment_entry_buffer")

        if entry == "direct_to_room":
            structural_penalty += 0.22
            concerns.append(
                "Apartment entrance opening directly into a private room severely compromises privacy"
            )

        elif entry == "foyer_to_room":
            structural_penalty += 0.14
            concerns.append(
                "Small foyer before a private room provides limited privacy buffer"
            )

        elif entry == "direct_to_hall":
            unit_bonus += 0.03
            strengths.append(
                "Apartment entrance opening into the hall avoids direct exposure of private rooms"
            )

        elif entry == "foyer_to_hall":
            unit_bonus += 0.08
            strengths.append(
                "Foyer separating entrance from living areas strongly improves privacy from common corridors"
            )


    # ---- Cap bonuses & apply structural penalties
    between_units_score += min(unit_bonus, 0.12)
    between_units_score -= structural_penalty
    between_units_score = max(min(between_units_score, 1), 0)


    for side, info in attachment_details.items():
        owner = info.get("owner")
        space_type = info.get("space_type")

        penalty, strength, concern = attachment_effect(owner, space_type)

        between_units_score -= penalty

        if strength:
            strengths.append(strength)

        if concern:
            concerns.append(concern)


    # =====================================================
    # CONTEXTUAL: WINDOW × OPEN SPACE
    # =====================================================
    window_side = in_room.get("window_facing_side")

    # -----------------------
    # Front-facing window
    # -----------------------
    if window_side == "front":

        if front == "attached" and window_side == "front":
            concerns.append(
                "Front window indicated despite attached structure — configuration may be inconsistent"
            )

        elif front == "front_yard":
            between_units_score += 0.05
            strengths.append(
                "Front-facing window benefits from a front yard"
            )

        elif front == "wide_road":
            between_units_score += 0.02

        elif front == "narrow_road":
            between_units_score -= 0.14
            concerns.append(
                "Front-facing window exposed to a narrow road"
            )

        elif front in ["tight_service_gap", "narrow_gap"]:
            between_units_score -= 0.18
            concerns.append(
                "Front-facing window opens into a very narrow gap"
            )



    # -----------------------
    # Back-facing window
    # -----------------------
    if window_side == "back":
        if back ==  "attached" and window_side == "back":
            concerns.append(
                "Back window indicated despite attached structure — configuration may be inconsistent"
            )

        elif back == "back_road":
            between_units_score += 0.02

        elif back == "private_backyard":
            between_units_score += 0.08
            strengths.append(
                "Back-facing window overlooking a private backyard improves privacy"
            )
        elif back in ["tight_service_gap","narrow_gap"]:
            between_units_score -= 0.18
            concerns.append(
                "Back-facing window opening into a narrow gap reduces privacy"
            )
        elif back in ["back_alley", "narrow_road"]:
            between_units_score -= 0.14
            concerns.append(
                "Back-facing window exposed to a rear road or alley reduces privacy"
            )

    def side_window_effect(side_value):

        # ---- If attached, inspect attachment type
        if side_value == "attached":
            return 0.0

        # ---- Normal open-space logic
        if side_value in ["side_yard", "large_side_yard", "side_road"]:
            return 0.06

        elif side_value in ["side_alley", "narrow_road", "small_side_yard"]:
            return -0.05

        elif side_value == "narrow_gap":
            return -0.14

        elif side_value in ["tight_service_gap"]:
            return -0.18

        return 0.0


    # -----------------------
    # Side-facing window
    # -----------------------
    if window_side == "side":

        side1 = between_units.get("side_a_open_space")
        side2 = between_units.get("side_b_open_space")

        effects = [
            side_window_effect(side1),
            side_window_effect(side2),
        ]

        # Determine which sides actually have open exposure
        open_sides = [
            s for s in [side1, side2]
            if s not in ["attached", None]
        ]

        # If both sides are attached → no exposure
        if not open_sides:
            pass

        # If at least one side has positive exposure (yard/road),
        # assume window faces the better side
        elif any(e > 0 for e in effects):
            best_effect = max(effects)
            between_units_score += best_effect

            if best_effect > 0:
                strengths.append(
                    "Side-facing window benefits from open space along the side"
                )

        # Otherwise both sides are exposed negatively → apply worst exposure
        else:
            worst_effect = min(effects)
            between_units_score += worst_effect

            if worst_effect < 0:
                concerns.append(
                    "Side-facing window exposed to limited side clearance reduces privacy"
                )


    # ---- CONTEXTUAL: WINDOW × OPEN SPACE
    # (your existing block)

    between_units_score = max(min(between_units_score, 1), 0)


    # =====================================================
    # FINAL SCORE
    # =====================================================
    weighted_score = (
        in_room_score * 0.25 +
        between_rooms_score * 0.30 +
        between_units_score * 0.45
    )

    final_score = round(weighted_score * 10, 1)

    # =====================================================
    # CONFIDENCE
    # =====================================================
    confidence_ratio = known_fields / total_fields if total_fields else 0

    confidence = (
        "high" if confidence_ratio >= 0.8
        else "medium" if confidence_ratio >= 0.5
        else "low"
    )

    return {
        "privacy_score_1_to_10": final_score,
        "confidence": confidence,
        "breakdown": {
            "scale": "0 to 1 (higher is better)",
            "privacy_in_room": round(in_room_score, 2),
            "privacy_between_rooms": round(between_rooms_score, 2),
            "privacy_between_units": round(between_units_score, 2)
        },
        "explanation": {
            "strengths": strengths,
            "concerns": concerns
        }
    }
