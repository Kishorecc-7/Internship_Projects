from rapidfuzz.fuzz import (
    ratio,
    token_set_ratio,
    WRatio,
)


def safe(value):

    if value is None:
        return ""

    return str(value)


def similarity(a, b):

    a = safe(a)
    b = safe(b)

    if not a or not b:
        return 0.0

    return ratio(
        a,
        b,
    ) / 100.0


def token_similarity(a, b):

    a = safe(a)
    b = safe(b)

    if not a or not b:
        return 0.0

    return token_set_ratio(
        a,
        b,
    ) / 100.0


def weighted_similarity(a, b):

    a = safe(a)
    b = safe(b)

    if not a or not b:
        return 0.0

    return WRatio(
        a,
        b,
    ) / 100.0


def create_features(df):

    features = []

    for i in range(len(df)):

        name_a = safe(
            df.iloc[i]["name_norm_a"]
        )

        name_b = safe(
            df.iloc[i]["name_norm_b"]
        )

        address_a = safe(
            df.iloc[i]["address_norm_a"]
        )

        address_b = safe(
            df.iloc[i]["address_norm_b"]
        )

        country_a = safe(
            df.iloc[i]["country_norm_a"]
        )

        country_b = safe(
            df.iloc[i]["country_norm_b"]
        )

        features.append(
            {
                # -------------------------
                # Country
                # -------------------------

                "country_exact": int(
                    bool(country_a)
                    and bool(country_b)
                    and country_a == country_b
                ),

                "country_missing": int(
                    not country_a
                    or not country_b
                ),

                "country_mismatch": int(
                    bool(country_a)
                    and bool(country_b)
                    and country_a != country_b
                ),

                # -------------------------
                # Business name
                # -------------------------

                "name_ratio": similarity(
                    name_a,
                    name_b,
                ),

                "name_token_ratio":
                    token_similarity(
                        name_a,
                        name_b,
                    ),

                "name_wratio":
                    weighted_similarity(
                        name_a,
                        name_b,
                    ),

                "name_exact": int(
                    bool(name_a)
                    and bool(name_b)
                    and name_a == name_b
                ),

                # -------------------------
                # Address
                # -------------------------

                "address_ratio":
                    similarity(
                        address_a,
                        address_b,
                    ),

                "address_token_ratio":
                    token_similarity(
                        address_a,
                        address_b,
                    ),

                "address_wratio":
                    weighted_similarity(
                        address_a,
                        address_b,
                    ),

                "address_exact": int(
                    bool(address_a)
                    and bool(address_b)
                    and address_a == address_b
                ),

                # -------------------------
                # Length
                # -------------------------

                "name_length_diff":
                    abs(
                        len(name_a)
                        - len(name_b)
                    ),

                "address_length_diff":
                    abs(
                        len(address_a)
                        - len(address_b)
                    ),

                "name_len_a":
                    len(name_a),

                "name_len_b":
                    len(name_b),

                "address_len_a":
                    len(address_a),

                "address_len_b":
                    len(address_b),
            }
        )

    return features