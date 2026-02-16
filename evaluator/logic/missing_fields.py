def find_next_missing_field(extracted: dict, confirmed_fields: set):
    """
    Returns the next (section, field) that should be asked to the user.
    Treats unconfirmed 'none' values as missing.
    Question order is UX-driven and intentional.
    """

    # =====================================================
    # 1️⃣ PRIVACY BETWEEN UNITS (ASK FIRST)
    # =====================================================
    between_units = extracted.get("privacy_between_units")

    if between_units is None:
        return ("privacy_between_units", "__entire_section__")

    for field in [
        "unit_type",
        "front_open_space",
        "side_a_open_space",
        "side_b_open_space",
        "back_open_space",
        "is_in_gated_society",
        "surrounding_layout_uniformity",
        "apartment_entry_buffer",
        "distance_between_apartment_doors"
    ]:
        value = between_units.get(field)
        if value is None or (
            value in ["none", "attached"]
            and ("privacy_between_units", field) not in confirmed_fields
        ):
            return ("privacy_between_units", field)



    # =====================================================
    # 2️⃣ PRIVACY BETWEEN ROOMS
    # =====================================================
    between_rooms = extracted.get("privacy_between_rooms")

    if between_rooms is None:
        return ("privacy_between_rooms", "__entire_section__")
    
    # 🔑 ASK THIS FIRST
    if between_rooms.get("has_multiple_bedrooms") is None:
        return ("privacy_between_rooms", "has_multiple_bedrooms")

    # ⛔ If only one bedroom → SKIP ENTIRE SECTION
    if between_rooms.get("has_multiple_bedrooms") is False:
        pass  # skip

    else:
        # Multiple bedrooms → ask detailed questions
        if between_rooms.get("bedrooms_share_wall") is None:
            return ("privacy_between_rooms", "bedrooms_share_wall")

        if between_rooms.get("buffer_between_rooms") is None:
            return ("privacy_between_rooms", "buffer_between_rooms")

        if between_rooms.get("window_proximity_between_rooms") is None:
            return ("privacy_between_rooms", "window_proximity_between_rooms")


    # =====================================================
    # 3️⃣ PRIVACY IN ROOM (ASK LAST)
    # =====================================================
    in_room = extracted.get("privacy_in_room")

    if in_room is None:
        return ("privacy_in_room", "__entire_section__")

    for field in [
        "room_size",
        "ceiling_height_ft",
    ]:
        value = in_room.get(field)
        if value is None or (
            value == "none"
            and ("privacy_in_room", field) not in confirmed_fields
        ):
            return ("privacy_in_room", field)

    # Ask window questions after basic room info
    if in_room.get("window_placement") is None:
        return ("privacy_in_room", "window_placement")

    if in_room.get("window_facing_side") is None:
        return ("privacy_in_room", "window_facing_side")

    return None
