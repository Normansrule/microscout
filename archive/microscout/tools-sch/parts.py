# STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2
"""LCSC numbers for passives and common parts, checked on lcsc.com / jlcpcb.com 2026-10-07
(see review/G2/sources.md). Licence: MIT."""

# (kind, value, package) -> (LCSC, MPN, rating note)
PASSIVES = {
    ("R", "10k", "0402"): ("C25744", "0402WGF1002TCE", "1% 62.5 mW"),
    ("R", "100k", "0402"): ("C25741", "0402WGF1003TCE", "1% 62.5 mW"),
    ("R", "4.7k", "0402"): ("C25900", "0402WGF4701TCE", "1%"),
    ("R", "5.1k", "0402"): ("C25905", "0402WGF5101TCE", "1%"),
    ("R", "1k", "0402"): ("C11702", "0402WGF1001TCE", "1%"),
    ("R", "2.2k", "0402"): ("C25879", "0402WGF2201TCE", "1%"),
    ("R", "47k", "0402"): ("C25792", "0402WGF4702TCE", "1%"),
    ("R", "22", "0402"): ("C25092", "0402WGF220JTCE", "5%"),
    ("R", "10", "0402"): ("C25077", "0402WGF100JTCE", "5%"),
    ("R", "0", "0402"): ("C17168", "0402WGF0000TCE", "jumper"),
    ("R", "100", "0402"): ("C25076", "0402WGF1000TCE", "1%"),
    ("R", "300", "0402"): ("C25102", "0402WGF3000TCE", "1%"),
    ("R", "1.5M", "0402"): ("C22276", "0402WGF1504TCE", "1%"),
    ("R", "5.23k", "0402"): ("C2933105", "FRC0402F5231TS", "1%"),
    ("R", "30.1k", "0402"): ("C29402", "0402WGF3012TCE", "1%"),
    ("R", "110k", "0402"): ("C25745", "0402WGF1103TCE", "1%"),
    ("R", "150k", "0402"): ("C25755", "0402WGF1503TCE", "1%"),
    ("R", "150", "1206"): ("C17917", "1206W4F1500T5E", "1% 250 mW"),
    ("R", "1m", "2512"): ("C2924520", "HoJLR2512-2W-1mR-1%", "2 W shunt"),
    ("C", "100n", "0402"): ("C1525", "CL05B104KO5NNNC", "16 V X7R"),
    ("C", "1u", "0402"): ("C52923", "CL05A105KA5NQNC", "25 V X5R"),
    ("C", "10n", "0402"): ("C15195", "CL05B103KB5NNNC", "50 V X7R"),
    ("C", "2.2u", "0603"): ("C23630", "CL10A225KO8NNNC", "16 V X5R"),
    ("C", "4.7u", "0402"): ("C23733", "CL05A475MP5NRNC", "10 V X5R"),
    ("C", "4.7u", "0603"): ("C19666", "CL10A475KO8NNNC", "16 V X5R"),
    ("C", "10u", "0603"): ("C19702", "CL10A106KP8NNNC", "10 V X5R - 5 V rails or lower only"),
    ("C", "10u", "0805"): ("C15850", "CL21A106KAYNNNE", "25 V X5R"),
    ("C", "22u", "0805"): ("C45783", "CL21A226MAQNNNE", "25 V X5R"),
    ("C", "47n", "0402"): ("C285062", "FH 0402B473K250NT", "25 V X7R"),
    ("C", "3.3n", "0402"): ("C26404", "CL05B332KB5NNNC", "50 V X7R"),
    ("C", "33n", "0402"): ("C106862", "CC0402KRX7R9BB333", "50 V X7R"),
}

# Rails above 5.5 V (2S): capacitors on these nets must be rated >= 16 V (checked by check.py)
HIGH_V_NETS = {"VBAT", "VBAT_RAW", "VLOGIC", "VDRV", "CHG_SNS", "CHG_PMID", "CHG_SW", "VBUS"}
CAP_RATING_V = {"C1525": 16, "C52923": 25, "C15195": 50, "C23630": 16, "C23733": 10, "C19666": 16,
                "C19702": 10, "C15850": 25, "C45783": 25, "C285062": 25, "C26404": 50, "C106862": 50,
                "C2939798": 25}


def lookup(kind, value, pkg):
    return PASSIVES.get((kind, value, pkg))
