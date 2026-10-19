"""Seven feature judgments per domain: false (0), ambiguous (0.5), true (1)."""


FEATURE_DEFINITIONS = {
    "birds": {
        "is_large": {"fields": ["adult_size_class"], "operator": "in", "value": ["large", "very_large"],
                     "ambiguous_values": ["medium"],
                     "description": "Adult size judgment: large/very_large = 1, medium = 0.5, small/tiny = 0."},
        "has_flight_wings": {"fields": ["wing_structure"], "operator": "in", "value": ["feathered", "broad_feathered", "short_feathered"],
                             "description": "Wing structure is feathered, broad_feathered, or short_feathered, rather than flippers or loose noninterlocking feathers."},
        "has_developed_flight_plumage": {"fields": ["developmental_stage"], "operator": "in", "value": ["adult", "juvenile_with_complete_plumage"],
                     "description": "Adult or juvenile with complete flight plumage = 1; nestling = 0. This does not imply a flight-capable species."},
        "has_intact_wings": {"fields": ["wing_condition"], "operator": "eq", "value": "intact",
                             "ambiguous_values": ["minor_feather_damage"],
                             "description": "Wing integrity: intact = 1, minor feather damage = 0.5, unhealed fracture = 0."},
        "is_rested": {"fields": ["fatigue"], "operator": "eq", "value": "rested",
                      "ambiguous_values": ["moderate"],
                      "description": "Rest judgment: rested = 1, moderate fatigue = 0.5, severe fatigue = 0."},
        "has_unhealed_fracture": {"fields": ["wing_condition"], "operator": "eq", "value": "unhealed_fracture",
                                 "description": "The stipulated wing condition includes an unhealed fracture."},
        "has_severe_fatigue": {"fields": ["fatigue"], "operator": "eq", "value": "severe",
                               "ambiguous_values": ["moderate"],
                               "description": "Fatigue severity: severe = 1, moderate = 0.5, rested = 0."},
    },
    "humans": {
        "has_5km_endurance": {"fields": ["sustained_test_distance_m"], "operator": "gte", "value": 5000,
                              "description": "The demonstrated rested sustained test distance is at least 5,000 metres."},
        "can_sustain_10kmh": {"fields": ["sustained_test_pace_kmh"], "operator": "gte", "value": 10,
                              "description": "The demonstrated rested sustained test pace is at least 10 km/h."},
        "has_unrestricted_mobility": {"fields": ["mobility"], "operator": "eq", "value": "unrestricted",
                                      "ambiguous_values": ["mild_ankle_pain"],
                                      "description": "Mobility: unrestricted = 1, mild ankle pain = 0.5, unable to bear weight = 0."},
        "is_rested": {"fields": ["fatigue"], "operator": "eq", "value": "rested",
                      "ambiguous_values": ["moderate"],
                      "description": "Rest judgment: rested = 1, moderate fatigue = 0.5, exhausted = 0."},
        "has_uphill_training": {"fields": ["regular_uphill_training"], "operator": "eq", "value": True,
                                "description": "The stipulated profile includes regular uphill training."},
        "has_regular_training": {"fields": ["experience"], "operator": "in", "value": ["recreational", "competitive"],
                                 "ambiguous_values": ["recreational"],
                                 "description": "Training judgment: competitive = 1, recreational = 0.5, untrained = 0."},
        "has_100m_endurance": {"fields": ["sustained_test_distance_m"], "operator": "gte", "value": 100,
                               "description": "The demonstrated rested sustained test distance is at least 100 metres."},
    },
    "mammals": {
        "is_large": {"fields": ["adult_body_mass_kg"], "operator": "gte", "value": 50, "description": "Species typical adult body mass is at least 50 kg. Estimate from species knowledge; return 0.5 if unknown or the typical range crosses 50 kg."},
        "is_cold_adapted": {"fields": ["cold_adapted"], "operator": "eq", "value": True, "description": "Judge normal adult species-level cold adaptations, independently of the stipulated individual state. 1 = well-established morphological or physiological adaptations for recurring subzero winters (e.g. dense seasonal insulation or cold-specific thermoregulation). 0 = no known special cold adaptation and primarily frost-free ecology. 0.5 = mixed, marginal, or genuinely insufficient species knowledge. Seasonal winter adaptations count. Do not require proof of survival at -20 C in every circumstance; taxonomy or occasional cold exposure alone is insufficient."},
        "is_heat_adapted": {"fields": ["heat_adapted"], "operator": "eq", "value": True, "description": "Judge normal adult species-level heat adaptations, independently of individual state. 1 = well-established morphological or physiological mechanisms for hot arid or hot seasonal environments (e.g. enhanced heat dissipation or heat-tolerant thermoregulation). 0 = no known special heat adaptation and predominantly cool or mild ecology. 0.5 = mixed, marginal, or genuinely insufficient species knowledge. Tropical distribution, ordinary mammalian sweating/panting, nocturnality or shelter-seeking alone do not establish 1. Do not equate adaptation with guaranteed survival at 40 C."},
        "is_drought_adapted": {"fields": ["drought_adapted"], "operator": "eq", "value": True, "description": "Judge normal adult species-level water-conservation adaptations, independently of individual state. 1 = well-established adaptations to scarce free drinking water, such as unusually efficient renal concentration, low evaporative loss or reliance on metabolic water. 0 = frequent hydration dependence without known special water-conservation adaptations. 0.5 = mixed, marginal, or genuinely insufficient species knowledge. Moist food or arid distribution alone do not establish 1. Do not require guaranteed survival for three days with zero fluid intake."},
        "is_adult": {"fields": ["developmental_stage"], "operator": "eq", "value": "adult", "description": "The stipulated individual is adult; juvenile and neonate = 0."},
        "is_healthy": {"fields": ["health"], "operator": "eq", "value": "healthy", "ambiguous_values": ["mildly_unwell"], "description": "Stipulated health: healthy = 1, mildly_unwell = 0.5, severely_ill = 0."},
        "has_adequate_energy_reserves": {"fields": ["energy_reserves"], "operator": "eq", "value": "adequate", "ambiguous_values": ["reduced"], "description": "Stipulated energy reserves: adequate = 1, reduced = 0.5, depleted = 0."},

    },
    "plants": {
        "is_succulent": {"fields": ["growth_form"], "operator": "eq", "value": "succulent",
                         "description": "The source growth form is succulent; this does not infer missing succulent_leaves observations."},
        "is_fern": {"fields": ["growth_form"], "operator": "eq", "value": "fern",
                    "description": "The source growth form is fern."},
        "has_established_roots": {"fields": ["root_condition"], "operator": "eq", "value": "established",
                                  "ambiguous_values": ["recently_transplanted"],
                                  "description": "Root establishment: established = 1, recently transplanted = 0.5, severely damaged = 0."},
        "is_healthy": {"fields": ["health"], "operator": "eq", "value": "healthy",
                       "ambiguous_values": ["wilting_but_alive"],
                       "description": "Health judgment: healthy = 1, wilting but alive = 0.5, severely stressed but alive = 0."},
        "has_moist_soil": {"fields": ["initial_soil_moisture"], "operator": "eq", "value": "moist",
                           "ambiguous_values": ["slightly_moist"],
                           "description": "Soil moisture: moist = 1, slightly moist = 0.5, dry = 0."},
        "has_succulent_leaves": {"fields": ["succulent_leaves"], "operator": "eq", "value": True,
                                 "description": "Succulent leaves: explicit true = 1, explicit false = 0; absent observations make the judgment ambiguous (0.5)."},
        "is_shrub": {"fields": ["growth_form"], "operator": "eq", "value": "shrub",
                     "description": "The source growth form is shrub."},
    },
    "legal_cases": {
        'caused_property_damage': {'fields': ['property_damage'], 'operator': 'eq', 'description': 'The person damaged the property.', 'value': True},
        'intentional_damage': {'fields': ['intentional_damage'], 'operator': 'eq', 'description': 'The damage was intentional.', 'value': True},
        'property_belongs_to_another': {'fields': ['property_belongs_to_another'], 'operator': 'eq', 'description': 'The damaged property belongs to another person.', 'value': True},
        'has_owner_consent': {'fields': ['owner_consent'], 'operator': 'eq', 'description': 'The owner consented to this damage.', 'value': True},
        'necessary_to_prevent_imminent_harm': {'fields': ['damage_solely_necessary_to_prevent_imminent_serious_harm'], 'operator': 'eq', 'description': 'In the emergency context, the damage was solely necessary to prevent the stipulated imminent serious danger; this fact does not establish an emergency in other contexts.', 'value': True},
        'has_lawful_authorisation': {'fields': ['lawful_authorisation'], 'operator': 'eq', 'value': True, 'description': 'Lawful authorisation is present. Official-duty exemption separately requires necessary damage within the authorised scope; authorisation alone does not establish exemption.'},
        'within_official_scope': {'fields': ['damage_necessary_within_official_scope'], 'operator': 'eq', 'description': 'The damage was necessary and within the authorised scope of the official duties assessed in the official-duty context.', 'value': True},
    },
}


def project_features(domain: str, raw_values: dict) -> dict[str, int | float]:
    result = {}
    for name, definition in FEATURE_DEFINITIONS[domain].items():
        fields = definition["fields"]
        values = [raw_values.get(field) for field in fields]
        operator = definition["operator"]
        if operator == "all_true":
            if any(value is not None and type(value) is not bool for value in values):
                raise ValueError(f"{domain}/{name}: known source facts must be boolean")
            # A known false conjunct settles AND; otherwise incomplete evidence is ambiguous.
            result[name] = 0 if any(value is False for value in values) else 0.5 if any(value is None for value in values) else 1
            continue
        if any(value is None for value in values):
            result[name] = 0.5
            continue
        if values[0] in definition.get("ambiguous_values", []):
            result[name] = 0.5
            continue
        if operator == "eq":
            if type(definition["value"]) is bool and type(values[0]) is not bool:
                raise ValueError(f"{domain}/{name}: known source fact must be boolean")
            active = values[0] == definition["value"]
        elif operator == "in":
            active = values[0] in definition["value"]
        elif operator == "gte":
            if type(values[0]) not in (int, float):
                raise ValueError(f"{domain}/{name}: required source fact must be numeric")
            active = values[0] >= definition["value"]
        else:
            raise ValueError(f"Unknown feature operator: {operator}")
        result[name] = int(active)
    return result
