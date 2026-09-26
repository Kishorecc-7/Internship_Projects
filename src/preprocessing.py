import re
import unicodedata

import pandas as pd

from .config import (
    ENTITY_ID_COL,
    BUSINESS_NAME_COL,
    BUSINESS_ADDRESS_COL,
    COUNTRY_COL,
    NAME_PREFIX_LENGTH,
)


# ============================================================
# COMPANY NAME NORMALIZATION
# ============================================================

COMPANY_REPLACEMENTS = {
    "incorporated": "inc",
    "inc": "inc",

    "corporation": "corp",
    "corp": "corp",

    "company": "co",
    "co": "co",

    "limited": "ltd",
    "ltd": "ltd",

    "llc": "llc",

    "plc": "plc",

    "pvt": "pvt",
    "private": "pvt",

    "public": "public",
}


# ============================================================
# ADDRESS NORMALIZATION
# ============================================================

ADDRESS_REPLACEMENTS = {
    "street": "st",
    "st": "st",

    "road": "rd",
    "rd": "rd",

    "avenue": "ave",
    "ave": "ave",

    "boulevard": "blvd",
    "blvd": "blvd",

    "drive": "dr",
    "dr": "dr",

    "lane": "ln",
    "ln": "ln",

    "parkway": "pkwy",
    "pkwy": "pkwy",

    "highway": "hwy",
    "hwy": "hwy",

    "suite": "ste",
    "ste": "ste",

    "building": "bldg",
    "bldg": "bldg",

    "floor": "fl",
    "fl": "fl",
}


# ============================================================
# COUNTRY NORMALIZATION
# ============================================================

COUNTRY_ALIASES = {
    "usa": "united states",
    "us": "united states",
    "u s": "united states",
    "u s a": "united states",

    "uk": "united kingdom",
    "gb": "united kingdom",
    "great britain": "united kingdom",

    "uae": "united arab emirates",
    "u a e": "united arab emirates",

    "ind": "india",
    "india": "india",

    "can": "canada",
    "ca": "canada",
    "canada": "canada",

    "aus": "australia",
    "australia": "australia",

    "de": "germany",
    "deu": "germany",
    "germany": "germany",

    "fr": "france",
    "fra": "france",
    "france": "france",

    "jp": "japan",
    "jpn": "japan",
    "japan": "japan",

    "sg": "singapore",
    "sgp": "singapore",
    "singapore": "singapore",
}


# ============================================================
# BASIC NORMALIZATION
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    value = str(value)

    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


# ============================================================
# NAME
# ============================================================

def normalize_name(value):
    value = normalize_text(value)

    words = value.split()

    words = [
        COMPANY_REPLACEMENTS.get(
            word,
            word,
        )
        for word in words
    ]

    return " ".join(words)


# ============================================================
# ADDRESS
# ============================================================

def normalize_address(value):
    value = normalize_text(value)

    words = value.split()

    words = [
        ADDRESS_REPLACEMENTS.get(
            word,
            word,
        )
        for word in words
    ]

    return " ".join(words)


# ============================================================
# COUNTRY
# ============================================================

def normalize_country(value):
    value = normalize_text(value)

    if not value:
        return ""

    return COUNTRY_ALIASES.get(
        value,
        value,
    )


# ============================================================
# DATAFRAME PREPARATION
# ============================================================

def prepare_dataframe(
    df,
    source_name,
):
    """
    Convert the original schema:

        entity_id
        business_name
        business_address
        country

    into an internal normalized schema.
    """

    df = df.copy()

    required_columns = {
        ENTITY_ID_COL,
        BUSINESS_NAME_COL,
        BUSINESS_ADDRESS_COL,
        COUNTRY_COL,
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            f"{source_name} is missing columns: "
            f"{sorted(missing)}"
        )

    # Original ID.
    df["entity_id"] = (
        df[ENTITY_ID_COL]
        .astype(str)
        .str.strip()
    )

    df["source"] = source_name

    # Normalized business name.
    df["name_norm"] = (
        df[BUSINESS_NAME_COL]
        .astype(str)
        .map(normalize_name)
    )

    # Normalized address.
    df["address_norm"] = (
        df[BUSINESS_ADDRESS_COL]
        .astype(str)
        .map(normalize_address)
    )

    # Normalized country.
    df["country_norm"] = (
        df[COUNTRY_COL]
        .astype(str)
        .map(normalize_country)
    )

    # Blocking keys.
    df["name_prefix"] = (
        df["name_norm"]
        .str[:NAME_PREFIX_LENGTH]
    )

    df["name_first_token"] = (
        df["name_norm"]
        .str.split()
        .str[0]
        .fillna("")
    )

    # Remove unusably short names.
    df.loc[
        df["name_norm"].str.len() < 2,
        "name_norm",
    ] = ""

    return df[
        [
            "entity_id",
            "source",
            "name_norm",
            "address_norm",
            "country_norm",
            "name_prefix",
            "name_first_token",
        ]
    ]