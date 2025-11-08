def infer_suffix_from_row(r: dict) -> str | None:
    """
    Infer exchange suffix ONLY from plausible exchange fields, not from the ticker itself.
    Priority order favors more likely matches.
    """
    HINTS_TO_SUFFIX = {
        # Core set
        "SW": ".SW", "SIX": ".SW", "SIX SWISS EXCHANGE": ".SW",
        "L": ".L", "LSE": ".L", "LONDON": ".L",
        "DE": ".DE", "XETRA": ".DE", "GERMANY": ".DE",
        "AS": ".AS", "AMSTERDAM": ".AS",
        "PA": ".PA", "PARIS": ".PA", "EPA": ".PA",
        "MI": ".MI", "BIT": ".MI", "MILAN": ".MI",
        # Nordics + Oslo + Vienna
        "CO": ".CO", "COPENHAGEN": ".CO", "NASDAQ COPENHAGEN": ".CO",
        "ST": ".ST", "STOCKHOLM": ".ST", "NASDAQ STOCKHOLM": ".ST",
        "HE": ".HE", "HELSINKI": ".HE", "NASDAQ HELSINKI": ".HE",
        "OL": ".OL", "OSLO": ".OL", "OSLO BØRS": ".OL", "OSLO BORSE": ".OL",
        "VI": ".VI", "VIENNA": ".VI", "WIENER BÖRSE": ".VI", "WIENER BOERSE": ".VI",
        # Euronext Brussels (already ok if suffix exists)
        "BR": ".BR", "BRUSSELS": ".BR", "EURONEXT BRUSSELS": ".BR",
    }

    CANDIDATE_KEYS = {
        "exchange", "venue", "market", "mic", "country", "idx", "index", "note", "exch"
    }

    ticker = str(r.get("ticker", "")).strip().upper()

    hints = []
    for k, v in r.items():
        if k is None or v is None:
            continue
        key = str(k).strip().lower()
        if key not in CANDIDATE_KEYS:
            continue
        s = str(v).strip().upper()
        if s.startswith("[") and s.endswith("]") and len(s) < 20:
            s = s.strip("[]'\" ").upper()
        if s == ticker:
            continue
        hints.append(s)

    PRIORITY = [
        # Swiss / UK / DE
        "SW", "SIX", "L", "LSE", "DE", "XETRA",
        # Core EU
        "AS", "AMSTERDAM", "PA", "PARIS", "MI", "BIT",
        # Nordics + Oslo + Vienna
        "CO", "COPENHAGEN", "ST", "STOCKHOLM", "HE", "HELSINKI", "OL", "OSLO", "VI", "VIENNA",
        # Brussels
        "BR", "BRUSSELS"
    ]
    for hp in PRIORITY:
        if hp in hints:
            return HINTS_TO_SUFFIX.get(hp)

    for s in hints:
        if s in HINTS_TO_SUFFIX:
            return HINTS_TO_SUFFIX[s]

    # Swiss safety
    row_text = " ".join(str(v) for v in r.values() if v is not None).upper()
    if "['SW']" in row_text or " SW " in f" {row_text} " or "SIX" in row_text:
        return ".SW"

    return None
