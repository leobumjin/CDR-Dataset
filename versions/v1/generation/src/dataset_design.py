"""Operational targets and fixed contexts implementing PaperPack Appendix A.

The PDF does not prescribe exact numeric contexts or a species list. These are
explicit, versioned design choices, not facts copied from the manuscript.
"""

DOMAINS = {
    "birds": {
        "category": "Birds", "prefix": "bird", "target": "CanFly",
        "target_definition": "Complete the required aerial movement under the conditions associated with the context, without external assistance.",
        "contexts": [
            {"context_id": "c_1", "description": "Short flight with dry plumage. Travel 20 metres continuously through the air. The bird's feathers are dry throughout the attempt. Take off from level ground with 20 metres of unobstructed space. Air is still, temperature is 20 C, and there are no obstacles or external assistance. Walking, jumping, and passive falling do not count. Use the stipulated developmental stage, wing condition, and fatigue without changing them."},
            {"context_id": "c_2", "description": "Long flight with dry plumage. Travel 500 metres continuously through the air. The bird's feathers are dry throughout the attempt. Take off from level ground with 20 metres of unobstructed space. Air is still, temperature is 20 C, and there are no obstacles or external assistance. Walking, jumping, and passive falling do not count. Use the stipulated developmental stage, wing condition, and fatigue without changing them."},
            {"context_id": "c_3", "description": "Short flight with wet plumage. Travel 20 metres continuously through the air immediately after heavy rain. The bird's body and wing feathers are thoroughly wet and remain wet throughout the attempt; it cannot dry them before taking off. Take off from level ground with 20 metres of unobstructed space. Air is still, temperature is 20 C, and there are no obstacles or external assistance. Walking, jumping, and passive falling do not count. Use the stipulated developmental stage, wing condition, and fatigue without changing them."},
            {"context_id": "c_4", "description": "Very short flight with dry plumage. Travel 5 metres continuously through the air. The bird's feathers are dry throughout the attempt. Take off from level ground with 20 metres of unobstructed space. Air is still, temperature is 20 C, and there are no obstacles or external assistance. Walking, jumping, and passive falling do not count. Use the stipulated developmental stage, wing condition, and fatigue without changing them."},
            {"context_id": "c_5", "description": "Long flight with wet plumage. Travel 500 metres continuously through the air immediately after heavy rain. The bird's body and wing feathers are thoroughly wet and remain wet throughout the attempt; it cannot dry them before taking off. Take off from level ground with 20 metres of unobstructed space. Air is still, temperature is 20 C, and there are no obstacles or external assistance. Walking, jumping, and passive falling do not count. Use the stipulated developmental stage, wing condition, and fatigue without changing them."},
        ],
    },
    "humans": {
        "category": "Humans", "prefix": "human", "target": "CanRun",
        "target_definition": "Complete the required distance by continuous running at at least the specified pace on the stated terrain, in the stipulated current state, without assistance or walking breaks.",
        "contexts": [
            {"context_id": "c_1", "description": "Run 100 metres continuously at 8 km/h on a dry, level track at 20 C. No walking breaks or external assistance. Interpret reported sustained test distance and pace as the person's demonstrated rested capacity, not a guarantee in a fatigued or injured state."},
            {"context_id": "c_2", "description": "Run 5,000 metres continuously at 10 km/h on a dry, level track at 20 C. No walking breaks or external assistance. Interpret reported sustained test distance and pace as demonstrated rested capacity, not a guarantee in a fatigued or injured state."},
            {"context_id": "c_3", "description": "Run 1,000 metres continuously at 8 km/h on a dry gravel trail with a constant 10 percent uphill gradient at 20 C. No walking breaks or external assistance. The reported level-track test does not itself establish uphill endurance; consider the stipulated training, mobility, and fatigue."},
            {"context_id": "c_4", "description": "Run 100 metres continuously at 12 km/h on a dry, level track at 20 C. No walking breaks or external assistance. Interpret reported sustained test distance and pace as demonstrated rested capacity, not a guarantee in a fatigued or injured state. Keep the stipulated mobility and fatigue unchanged."},
            {"context_id": "c_5", "description": "Run 10,000 metres continuously at 8 km/h on a dry, level track at 20 C. No walking breaks or external assistance. Interpret reported sustained test distance and pace as demonstrated rested capacity, not a guarantee in a fatigued or injured state. Keep the stipulated mobility and fatigue unchanged."},
        ],
    },
    "mammals": {
        "category": "Mammals", "prefix": "mammal", "target": "CanSurvive",
        "target_definition": "The stipulated individual remains alive for the full interval under the supplied environmental and resource conditions, without rescue. Temporary stress or reversible damage is allowed.",
        "contexts": [
            {"context_id": "c_1", "description": "Survive 7 days at a temperature suitable for the species, with species-appropriate food and hydration supplied as needed. Use the stipulated developmental stage, health, and energy reserves without changing them before the start. The animal is in a safe enclosure with its species-appropriate supporting medium (air or water), no predators, injury, or external rescue. The specified temperature applies to that surrounding medium throughout the interval. Judge whether this individual is alive at the end; temporary physiological stress is allowed. Do not answer a species-level reproduction question."},
            {"context_id": "c_2", "description": "Survive 24 hours at a constant -20 C. Food and hydration are supplied as needed. There is no heated shelter, insulation added by humans, or opportunity to leave the cold environment. Use the stipulated developmental stage, health, and energy reserves without changing them before the start. The animal is in a safe enclosure with its species-appropriate supporting medium (air or water), no predators, injury, or external rescue. The specified temperature applies to that surrounding medium throughout the interval. Judge whether this individual is alive at the end; temporary physiological stress is allowed. Do not answer a species-level reproduction question."},
            {"context_id": "c_3", "description": "Survive 24 hours at a constant 40 C. Food and hydration are supplied as needed. There is no active cooling or opportunity to leave the hot environment. Use the stipulated developmental stage, health, and energy reserves without changing them before the start. The animal is in a safe enclosure with its species-appropriate supporting medium (air or water), no predators, injury, or external rescue. The specified temperature applies to that surrounding medium throughout the interval. Judge whether this individual is alive at the end; temporary physiological stress is allowed. Do not answer a species-level reproduction question."},
            {"context_id": "c_4", "description": "Survive 3 days at a temperature suitable for the species with no fluid intake, including drinking, absorption, and moisture from food. Food is not supplied during this interval. A species-required supporting medium remains available but cannot provide hydration; this is a constructed exposure condition. Use the stipulated developmental stage, health, and energy reserves without changing them before the start. The animal is in a safe enclosure with its species-appropriate supporting medium (air or water), no predators, injury, or external rescue. The specified temperature applies to that surrounding medium throughout the interval. Judge whether this individual is alive at the end; temporary physiological stress is allowed. Do not answer a species-level reproduction question."},
            {"context_id": "c_5", "description": "Survive 14 days at a temperature suitable for the species without food or calorie intake. Hydration is supplied as needed. Use the stipulated developmental stage, health, and energy reserves without changing them before the start. The animal is in a safe enclosure with its species-appropriate supporting medium (air or water), no predators, injury, or external rescue. The specified temperature applies to that surrounding medium throughout the interval. Judge whether this individual is alive at the end; temporary physiological stress is allowed. Do not answer a species-level reproduction question."},
        ],
    },
    "plants": {
        "category": "Plants", "prefix": "plant", "target": "CanSurvive",
        "target_definition": "Be alive at the end of the specified interval under the stated conditions. Temporary wilting or damage is allowed; growth, flowering, and perfect health are not required.",
        "contexts": [
            {"context_id": "c_1", "description": "Remain for 3 days without watering or rain at a constant 20 C, 50 percent relative humidity, and bright indirect light for 12 hours per day. The plant starts in the stipulated state in a 10-litre pot with suitable well-drained substrate, no external water reservoir, and no pests. Judge survival at the end, allowing temporary wilting."},
            {"context_id": "c_2", "description": "Remain for 30 days without watering or rain at a constant 35 C, 30 percent relative humidity, and direct sunlight for 12 hours per day. The plant starts in the stipulated state in a 10-litre pot with suitable well-drained substrate, no external water reservoir, and no pests. Judge survival at the end, allowing temporary damage."},
            {"context_id": "c_3", "description": "Remain for 7 days without watering or rain at a constant -10 C, including roots and substrate, with daylight for 8 hours per day and no frost protection. The plant starts in the stipulated state in a 10-litre pot with suitable substrate, no external water reservoir, and no pests. Judge survival at the end, allowing temporary damage or dormancy."},
            {"context_id": "c_4", "description": "Remain for 7 days at a constant 20 C, 50 percent relative humidity, and bright indirect light for 12 hours per day. The plant starts in the stipulated state in a 10-litre pot with suitable well-drained substrate and no pests. Water is supplied as needed to maintain suitable soil moisture after the start, without waterlogging. Keep the stipulated root condition and initial health. Judge survival at the end, allowing temporary damage."},
            {"context_id": "c_5", "description": "Remain for 7 days at a constant 20 C, 50 percent relative humidity, and bright indirect light for 12 hours per day. The plant starts in the stipulated state in a 10-litre pot with suitable substrate and no pests. Immediately after the start, the entire root zone is continuously saturated with standing water and no drainage for the full interval. Keep the stipulated root condition and initial health. Judge survival at the end, allowing temporary damage."},
        ],
    },
    "legal_cases": {
        "category": "Legal cases", "prefix": "case", "target": "IsGuilty",
        "target_definition": "Satisfy all elements of the supplied hypothetical property-damage offence without an applicable situation-specific exception. This is not a determination under real-world law.",
        "contexts": [
            {'context_id': 'c_1', 'description': 'Ordinary situation: there is no imminent serious danger and the person is not performing official duties. Judge only this hypothetical property-damage offence using the stipulated facts; no other offences or defences apply. The same property and act are assessed in each context.', 'rule': "A person is guilty if and only if they damaged property belonging to another person, did so intentionally, and lacked the owner's consent, unless an exception stated below applies. No exception applies. Emergency necessity and official authorisation facts do not create an exception in this ordinary situation."},
            {'context_id': 'c_2', 'description': 'Emergency situation: imminent serious danger threatens a person; the actor is not performing official duties. Judge only this hypothetical property-damage offence using the stipulated facts; no other offences or defences apply. The same property and act are assessed in each context.', 'rule': "A person is guilty if and only if they damaged property belonging to another person, did so intentionally, and lacked the owner's consent, unless an exception stated below applies. Damage is exempt if and only if it was solely necessary to prevent that danger; unnecessary damage is not exempt. Official authorisation does not create an exception in this emergency situation."},
            {'context_id': 'c_3', 'description': 'Official-duty situation: the person is performing official duties and there is no imminent serious danger. Judge only this hypothetical property-damage offence using the stipulated facts; no other offences or defences apply. The same property and act are assessed in each context.', 'rule': "A person is guilty if and only if they damaged property belonging to another person, did so intentionally, and lacked the owner's consent, unless an exception stated below applies. Damage is exempt if and only if BOTH the act was lawfully authorised AND the damage was necessary and within the authorised scope of those duties. Official status alone is insufficient. Emergency necessity does not create an exception in this official-duty situation."},
            {"context_id": "c_4", "description": "Supervisor's order situation: a workplace supervisor has ordered the actor to damage the property. There is no imminent serious danger and the actor is not performing official duties. The supervisor or friend does not act on behalf of the property owner; the order or request does not establish owner consent. Judge only this hypothetical property-damage offence using the stipulated facts; no other offences or defences apply. The same property and act are assessed in each context.", "rule": "A person is guilty if and only if they damaged property belonging to another person, did so intentionally, and lacked the owner's consent. No exception applies. A supervisor's order or a friend's request does not excuse the damage or independently establish lawful official authority. Emergency necessity and official authorisation facts do not create an exception when there is no imminent serious danger and no official duty. Use the explicit owner-consent fact; do not infer consent from the order or request."},
            {"context_id": "c_5", "description": "Friend's request situation: a friend has asked the actor to damage the property. There is no imminent serious danger and the actor is not performing official duties. The supervisor or friend does not act on behalf of the property owner; the order or request does not establish owner consent. Judge only this hypothetical property-damage offence using the stipulated facts; no other offences or defences apply. The same property and act are assessed in each context.", "rule": "A person is guilty if and only if they damaged property belonging to another person, did so intentionally, and lacked the owner's consent. No exception applies. A supervisor's order or a friend's request does not excuse the damage or independently establish lawful official authority. Emergency necessity and official authorisation facts do not create an exception when there is no imminent serious danger and no official duty. Use the explicit owner-consent fact; do not infer consent from the order or request."},
        ],
    },
}

# Short display names for the fixed definitions above. They do not alter prompts.
CONTEXT_NAMES = {
    "birds": {
        "c_1": "Short: 20 m, dry feathers",
        "c_2": "Long: 500 m, dry feathers",
        "c_3": "Wet: 20 m, thoroughly wet feathers",
        "c_4": "Very short: 5 m, dry feathers",
        "c_5": "Long wet: 500 m, thoroughly wet feathers",
    },
    "humans": {
        "c_1": "Flat run: 100 m at 8 km/h",
        "c_2": "Flat run: 5 km at 10 km/h",
        "c_3": "Uphill: 1 km at 8 km/h, 10% slope",
        "c_4": "Fast flat run: 100 m at 12 km/h",
        "c_5": "Endurance flat run: 10 km at 8 km/h",
    },
    "mammals": {
        "c_1": "Suitable environment: 7 d",
        "c_2": "Cold exposure: 24 h, -20 C",
        "c_3": "Heat exposure: 24 h, 40 C",
        "c_4": "No hydration: 3 d",
        "c_5": "No food: 14 d",

    },
    "plants": {
        "c_1": "Mild drought: 3 d, 20 C",
        "c_2": "Hot drought: 30 d, 35 C",
        "c_3": "Freezing: 7 d, -10 C",
        "c_4": "Regular watering: 7 d, 20 C",
        "c_5": "Waterlogging: 7 d, 20 C",
    },
    "legal_cases": {
        "c_1": "Property damage: ordinary situation",
        "c_2": "Property damage: emergency situation",
        "c_3": "Property damage: official-duty situation",
        "c_4": "Property damage: supervisor's order",
        "c_5": "Property damage: friend's request",
    },
}


BIRD_STATES = {
    "developmental_stage": ("adult", "juvenile_with_complete_plumage", "nestling"),
    "wing_condition": ("intact", "minor_feather_damage", "unhealed_fracture"),
    "fatigue": ("rested", "moderate", "severe"),
}
PLANT_STATES = {
    "root_condition": ("established", "recently_transplanted", "severely_damaged"),
    "health": ("healthy", "wilting_but_alive", "severely_stressed_but_alive"),
    "initial_soil_moisture": ("dry", "slightly_moist", "moist"),
}
HUMAN_STATES = {
    "experience": ("untrained", "recreational", "competitive"),
    "sustained_test_distance_m": (50, 500, 5000, 10000),
    "sustained_test_pace_kmh": (8, 10, 12),
    "mobility": ("unrestricted", "mild_ankle_pain", "unable_to_bear_weight"),
    "fatigue": ("rested", "moderate", "exhausted"),
    "regular_uphill_training": (False, True),
}
LEGAL_STATES = {
    name: (False, True) for name in (
        "property_damage", "intentional_damage", "property_belongs_to_another",
        "owner_consent", "damage_solely_necessary_to_prevent_imminent_serious_harm",
        "lawful_authorisation", "damage_necessary_within_official_scope",
    )
}

# Constructed individual conditions, distinct from source-backed taxonomy.
MAMMAL_STATES = {
    "developmental_stage": ("adult", "juvenile", "neonate"),
    "health": ("healthy", "mildly_unwell", "severely_ill"),
    "energy_reserves": ("adequate", "reduced", "depleted"),
}
