"""R3-GEO-03 — curated geography alias tables (config-carried, not inferred).

The maintained variant→canonical lookups the resolver consults when conservative normalization
(R3-GEO-01/02) does not produce an exact LGD match. Keys are the NORMALIZED flagship name
(:func:`normalize_geo_name` applied), values are the target LGD English name (also normalized at
load). Every entry is a HAND-VERIFIED fact: each target was confirmed present in the archived LGD
reference before being added (a guarding test re-checks this). Putting these in an explicit,
auditable table — rather than in cleverer normalization code — is deliberate: it keeps R3-GEO-01
conservative so it can never silently merge two distinct places (R3-GEO-05).

DISTRICT_ALIASES land with district resolution (T3.4).
"""

from __future__ import annotations

from typing import Final

# Flagship state-name variants that R3-GEO-02 misses. Two observed:
#   "DN HAVELI AND DD"     — heavy abbreviation (R3-GEO-01 docstring example)
#   "ANDAMAN AND NICOBAR"  — flagship drops the "Islands" suffix LGD carries
STATE_ALIASES: Final[dict[str, str]] = {
    "dn haveli and dd": "the dadra and nagar haveli and daman and diu",
    "andaman and nicobar": "andaman and nicobar islands",
}

# Flagship district-name variants that R3-GEO-02 misses, keyed by (LGD state code, normalized
# flagship name) → target LGD English name. State-scoped so a key can never fire in the wrong
# state. Trailing comment is the verbatim flagship spelling. Categories represented: spelling/
# transliteration (Bhatinda→Bathinda), official-rename (Mewat→Nuh, Ahilyanagar→Ahmednagar),
# LGD long-form (Kanker→Uttar Bastar Kanker), and token-order (24 Parganas (North)→North 24
# Parganas). NOT here — and therefore quarantined by R3-GEO-05 — are flagship labels with no LGD
# district: new districts absent from this LGD snapshot (Markapuram, Polavaram, Keyi Panyor,
# Bengaluru South) and non-district administrative bodies (WB DGHC / GTA / Siliguri Mahakuma
# Parisad; GTA spans Darjeeling+Kalimpong, so aliasing it would wrong-merge).
DISTRICT_ALIASES: Final[dict[tuple[str, str], str]] = {
    # JAMMU AND KASHMIR (LGD 1)
    ("1", "badgam"): "Budgam",  # BADGAM
    ("1", "rajauri"): "Rajouri",  # RAJAURI
    # HIMACHAL PRADESH (LGD 2)
    ("2", "lahul and spiti"): "Lahaul and Spiti",  # LAHUL AND SPITI
    # PUNJAB (LGD 3)
    ("3", "bhatinda"): "Bathinda",  # BHATINDA
    ("3", "mukatsar"): "Sri Muktsar Sahib",  # MUKATSAR
    ("3", "nawanshahr"): "Shahid Bhagat Singh Nagar",  # NAWANSHAHR
    ("3", "ropar"): "Rupnagar",  # ROPAR
    ("3", "sas nagar mohali"): "S.A.S Nagar",  # SAS NAGAR MOHALI
    # HARYANA (LGD 6)
    ("6", "mewat"): "Nuh",  # MEWAT
    # RAJASTHAN (LGD 8)
    ("8", "sri ganganagar"): "Ganganagar",  # SRI GANGANAGAR
    # UTTAR PRADESH (LGD 9)
    ("9", "barabanki"): "Bara Banki",  # BARABANKI
    ("9", "kashganj"): "Kasganj",  # KASHGANJ
    ("9", "kushi nagar"): "Kushinagar",  # KUSHI NAGAR
    ("9", "maharajganj"): "Mahrajganj",  # MAHARAJGANJ
    ("9", "sant kabeer nagar"): "Sant Kabir Nagar",  # SANT KABEER NAGAR
    ("9", "sant ravidas nagar"): "Bhadohi",  # SANT RAVIDAS NAGAR
    ("9", "shravasti"): "Shrawasti",  # SHRAVASTI
    ("9", "siddharth nagar"): "Siddharthnagar",  # SIDDHARTH NAGAR
    # BIHAR (LGD 10)
    ("10", "auranagabad"): "Aurangabad",  # AURANAGABAD
    ("10", "gayaji"): "Gaya",  # GAYAJI
    # SIKKIM (LGD 11)
    ("11", "gangtok district"): "Gangtok",  # Gangtok District
    ("11", "gyalshing district"): "Gyalshing",  # Gyalshing District
    ("11", "mangan district"): "Mangan",  # Mangan District
    ("11", "namchi district"): "Namchi",  # Namchi District
    # ARUNACHAL PRADESH (LGD 12)
    ("12", "upper dibang valley"): "Dibang Valley",  # UPPER DIBANG VALLEY
    # ASSAM (LGD 18)
    ("18", "morigaon"): "Marigaon",  # Morigaon
    ("18", "south salmara mankachar"): "South Salmara Mancachar",  # SOUTH SALMARA-MANKACHAR
    ("18", "sribhumi"): "Karimganj",  # Sribhumi
    # WEST BENGAL (LGD 19)
    ("19", "24 parganas north"): "North 24 Parganas",  # 24 PARGANAS (NORTH)
    ("19", "24 parganas south"): "South 24 Parganas",  # 24 PARGANAS SOUTH
    ("19", "coochbehar"): "Cooch Behar",  # COOCHBEHAR
    ("19", "dinajpur dakshin"): "Dakshin Dinajpur",  # DINAJPUR DAKSHIN
    ("19", "dinajpur uttar"): "Uttar Dinajpur",  # DINAJPUR UTTAR
    ("19", "maldah"): "Malda",  # MALDAH
    # ODISHA (LGD 21)
    ("21", "angul"): "Anugul",  # ANGUL
    ("21", "bolangir"): "Balangir",  # BOLANGIR
    ("21", "jajpur"): "Jajapur",  # JAJPUR
    ("21", "nabarangapur"): "Nabarangpur",  # NABARANGAPUR
    # CHHATTISGARH (LGD 22)
    ("22", "baloda bazar"): "Balodabazar-Bhatapara",  # BALODA BAZAR
    ("22", "balrampur"): "Balrampur-Ramanujganj",  # BALRAMPUR
    ("22", "dantewada"): "Dakshin Bastar Dantewada",  # DANTEWADA
    ("22", "kanker"): "Uttar Bastar Kanker",  # KANKER
    ("22", "kawardha"): "Kabeerdham",  # KAWARDHA
    ("22", "manendragarh chirmiri bharatpur"): "Manendragarh-Chirmiri-Bharatpur (M C B)",
    ("22", "mohla manpur ambagarh chowki"): "Mohla Manpur Ambagarh Chouki",
    ("22", "rajnandagon"): "Rajnandgaon",  # RAJNANDAGON
    # MADHYA PRADESH (LGD 23)
    ("23", "ashok nagar"): "Ashoknagar",  # ASHOK NAGAR
    ("23", "khandwa"): "Khandwa (East Nimar)",  # KHANDWA
    ("23", "khargone"): "Khargone West Nimar",  # KHARGONE
    ("23", "narsinghpur"): "Narsimhapur",  # NARSINGHPUR
    # GUJARAT (LGD 24)
    ("24", "ahmadabad"): "Ahmedabad",  # AHMADABAD
    ("24", "dang"): "Dangs",  # DANG
    ("24", "dohad"): "Dahod",  # DOHAD
    # MAHARASHTRA (LGD 27)
    ("27", "ahilyanagar"): "Ahmednagar",  # AHILYANAGAR
    ("27", "chatrapati sambhaji nagar"): "Chhatrapati Sambhajinagar",  # Chatrapati Sambhaji Nagar
    # ANDHRA PRADESH (LGD 28)
    ("28", "anantapur"): "Ananthapuramu",  # ANANTAPUR
    ("28", "konaseema"): "Dr. B.R. Ambedkar Konaseema",  # KONASEEMA
    ("28", "nellore"): "Sri Potti Sriramulu Nellore",  # NELLORE
    ("28", "visakhapatanam"): "Visakhapatnam",  # VISAKHAPATANAM
    # KARNATAKA (LGD 29)
    ("29", "bengaluru"): "Bengaluru Urban",  # BENGALURU
    ("29", "chamaraja nagara"): "Chamarajanagara",  # CHAMARAJA NAGARA
    ("29", "davanagere"): "Davangere",  # DAVANAGERE
    ("29", "dharwar"): "Dharwad",  # DHARWAR
    ("29", "vijayanagara"): "Vijayanagar",  # VIJAYANAGARA
    ("29", "vijaypura"): "Vijayapura",  # VIJAYPURA
    # KERALA (LGD 32)
    ("32", "kasargod"): "Kasaragod",  # KASARGOD
    # TAMIL NADU (LGD 33)
    ("33", "kanchipuram"): "Kancheepuram",  # KANCHIPURAM
    ("33", "sivagangai"): "Sivaganga",  # SIVAGANGAI
    ("33", "tiruvallur"): "Thiruvallur",  # TIRUVALLUR
    ("33", "tiruvarur"): "Thiruvarur",  # TIRUVARUR
    ("33", "villupuram"): "Viluppuram",  # VILLUPURAM
    # PUDUCHERRY (LGD 34)
    ("34", "pondicherry"): "Puducherry",  # PONDICHERRY
    # ANDAMAN AND NICOBAR (LGD 35)
    ("35", "south andaman"): "South Andamans",  # SOUTH ANDAMAN
    # TELANGANA (LGD 36)
    ("36", "jagtial"): "Jagitial",  # Jagtial
    ("36", "jangaon"): "Jangoan",  # Jangaon
    ("36", "jayashanker bhopalapally"): "Jayashankar Bhupalapally",  # Jayashanker Bhopalapally
    ("36", "kumram bheem asifabad"): "Kumuram Bheem Asifabad",  # Kumram Bheem(Asifabad)
    ("36", "medchal"): "Medchal Malkajgiri",  # Medchal
    ("36", "rajanna sirsilla"): "Rajanna Sircilla",  # Rajanna Sirsilla
    ("36", "rangareddy"): "Ranga Reddy",  # Rangareddy
}

# Curated quarantine notes (R3-GEO-05): for flagship labels that deliberately do NOT resolve and
# must NOT be aliased, a rich, honest description of what the entity is and which LGD geography it
# relates to. Keyed by (LGD state code, normalized flagship name). Used as the quarantine
# `detail` so the row stays presented and queryable — no unique data is lost, it is just filed
# under an honest "unresolved" identity instead of a fabricated one. (The row's metric values are
# always preserved on the quarantine regardless; this only enriches the human-readable reason.)
#
# West Bengal Darjeeling region (investigated): Darjeeling district is published ONLY as two
# SUB-DISTRICT fragments — DGHC/GTA (flagship unit 3219, the hill subdivisions) and Siliguri
# Mahakuma Parisad (unit 3204, the plains subdivision); Kalimpong (unit 3221) is a separate LGD
# district and resolves cleanly. There is no clean district-grain Darjeeling row. Resolving a
# single fragment as "Darjeeling" would under-count; summing fragments would fabricate a district
# total the source never published (R3-SET-02 principle). Below the v1 district floor (§5).
_DARJEELING_SPLIT = (
    "sub-district fragment of LGD Darjeeling district (West Bengal), below the v1 district floor; "
    "its sibling fragment is published separately, so it is neither aliased to Darjeeling "
    "(would under-count) nor summed with siblings (would fabricate an unpublished district total)"
)
GEO_QUARANTINE_NOTES: Final[dict[tuple[str, str], str]] = {
    ("19", "darjeeling gorkha hill council dghc"): (
        "Darjeeling Gorkha Hill Council (DGHC) — autonomous hill-council unit (flagship unit "
        "3219) covering the hill subdivisions (Darjeeling Sadar, Kurseong, Mirik); a "
        f"{_DARJEELING_SPLIT}. Sibling fragment: Siliguri Mahakuma Parisad (plains subdivision)."
    ),
    ("19", "gorkhaland territorial administration gta"): (
        "Gorkhaland Territorial Administration (GTA) — successor body to DGHC (same flagship unit "
        f"3219, the Darjeeling hill subdivisions); a {_DARJEELING_SPLIT}. Sibling fragment: "
        "Siliguri Mahakuma Parisad (the plains subdivision)."
    ),
    ("19", "siliguri mahakuma parisad"): (
        "Siliguri Mahakuma Parisad — the Siliguri (plains) subdivision (flagship unit 3204); a "
        f"{_DARJEELING_SPLIT}. Sibling fragment: the hill subdivisions, published as DGHC/GTA."
    ),
    # New districts genuinely absent from the archived LGD snapshot (current as of 2026-06): real
    # places with no LGD identity to assign yet, kept queryable as quarantined rather than guessed.
    ("28", "markapuram"): "Markapuram (Andhra Pradesh) — not a district in the LGD snapshot.",
    ("28", "polavaram"): "Polavaram (Andhra Pradesh) — not a district in the LGD snapshot.",
    ("12", "keyi panyor"): (
        "Keyi Panyor (Arunachal Pradesh) — district created 2024, absent from the LGD snapshot."
    ),
    ("29", "bengaluru south"): (
        "Bengaluru South (Karnataka) — newly notified district, absent from the LGD snapshot."
    ),
}
