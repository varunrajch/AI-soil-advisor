"""Nela Mitra rules: every quantity is calculated here, never by the AI."""
import re

ACRE_TO_HA = 0.4047
BAG_KG = {"urea": 45, "dap": 50, "mop": 50}
PRICE = {"urea": 266.50, "dap": 1350.0, "mop": 1700.0}  # placeholder ₹ per bag

# (low_below, high_above)
RATING_LIMITS = {"n": (280, 560), "p": (10, 25), "k": (110, 280), "oc": (0.5, 0.75)}
FACTOR = {"Low": 1.25, "Medium": 1.0, "High": 0.75}

# N : P2O5 : K2O kg/ha (illustrative)
BASE_DOSE = {
    "Paddy": (120, 60, 40),
    "Groundnut": (20, 40, 40),
    "Maize": (180, 60, 50),
    "Cotton": (120, 60, 60),
    "Chilli": (150, 75, 75),
    "Redgram": (20, 50, 20),
}
LEGUMES = {"Groundnut", "Redgram"}  # fix their own nitrogen, need little urea

# When to apply: (stage text key, items). "zinc" is shown only when Zn is low.
SCHEDULE = {
    "Paddy": [("transplanting", ["dap", "mop", "urea3", "zinc"]),
              ("tillering", ["urea3"]), ("panicle", ["urea3"])],
    "Groundnut": [("sowing", ["all_fert", "zinc"]), ("flowering", ["gypsum"])],
    "Maize": [("sowing", ["dap", "mop", "urea3", "zinc"]),
              ("knee_high", ["urea3"]), ("tasseling", ["urea3"])],
    "Cotton": [("sowing", ["dap", "mop", "urea3", "zinc"]),
               ("squaring", ["urea3"]), ("flowering_60", ["urea3"])],
    "Chilli": [("transplanting", ["dap", "mop", "urea3", "zinc"]),
               ("days_30", ["urea3"]), ("flowering_60", ["urea3"])],
    "Redgram": [("sowing", ["all_fert", "zinc"])],
}

SAMPLES = {
    "Sample A": {
        "desc": "Godavari paddy", "crop": "Paddy", "season": "Rabi", "acres": 1.0,
        "ph": 8.2, "ec": 0.6, "oc": 0.42, "n": 210.0, "p": 28.0, "k": 150.0, "zn": 0.4, "b": 0.7,
        "last_urea": 3.0, "last_dap": 2.0, "last_mop": 0.0,
    },
    "Sample B": {
        "desc": "Rayalaseema groundnut", "crop": "Groundnut", "season": "Kharif", "acres": 2.0,
        "ph": 6.2, "ec": 0.3, "oc": 0.35, "n": 180.0, "p": 8.0, "k": 95.0, "zn": 0.5, "b": 0.3,
        "last_urea": 1.0, "last_dap": 1.0, "last_mop": 0.0,
    },
}

TEXT = {
    "en": {
        "subtitle": "Soil Health Card to action",
        "language": "Language",
        "load_sample": "Load sample",
        "none": "None",
        "upload": "Upload Soil Health Card photo (JPG/PNG)",
        "read_card": "Read card",
        "reading": "Reading the card...",
        "read_ok": "Values filled from the photo. Please check and correct them.",
        "read_fail": "Could not read the card",
        "read_missing": "Not found on the card: {names}. Please type these values in yourself.",
        "not_card": "This does not look like a Soil Health Card (it may use different units or "
                    "list several fields). Nothing was filled in. Enter values or load a sample.",
        "no_key": "Card reading needs an API key, enter values or load a sample.",
        "soil_values": "Soil Health Card values",
        "farm": "Your farm",
        "crop": "Crop", "season": "Season", "acres": "Acres",
        "last_season": "Last season's bags per acre",
        "make_plan": "Make my plan",
        "listen": "🔊 Listen",
        "audio_fail": "Audio not available right now",
        "other_crop": "Same soil, other crop",
        "crops": {"Paddy": "Paddy", "Groundnut": "Groundnut", "Maize": "Maize",
                  "Cotton": "Cotton", "Chilli": "Chilli", "Redgram": "Redgram"},
        "urea": "Urea", "dap": "DAP", "mop": "MOP",
        "zinc": "Zinc sulphate", "gypsum": "Gypsum", "borax": "Borax",
        "fym": "Farmyard manure", "lime": "Agricultural lime",
        "headline": "This season, change {n} things",
        "headline_one": "This season, change 1 thing",
        "headline_zero": "This season, keep the same fertiliser",
        "detail_both": "{c} fertiliser change(s), plus {extras}",
        "detail_extras_only": "Same fertiliser as last season, plus {extras}",
        "say_also": "Also buy: {items}.",
        "read_farm": "Crop, season and acres were also read from the card. Enter last season's bags yourself.",
        "for_acres": "for {a} acre(s)",
        "buy": "What to buy", "when": "When to apply", "changes": "What changes from last season",
        "fixes": "Soil fixes", "cost": "Cost",
        "about": "about", "bag": "bag", "bags": "bags", "kg": "kg",
        "less_half": "less than ½ bag",
        "no_need": "not needed",
        "transplanting": "At transplanting", "tillering": "At tillering (about 20 to 25 days)",
        "panicle": "At panicle initiation (about 45 to 50 days)",
        "sowing": "At sowing", "flowering": "At flowering (about 40 to 45 days)",
        "knee_high": "At knee-high stage (about 30 days)",
        "tasseling": "At tasseling (about 50 to 55 days)",
        "squaring": "At squaring (about 30 to 35 days)",
        "flowering_60": "At flowering (about 60 days)",
        "days_30": "About 30 days after transplanting",
        "all": "all", "third_urea": "⅓ of the urea", "all_fert": "all fertiliser",
        "Reduce": "Reduce", "Increase": "Increase", "Add": "Add (was zero)", "Keep": "Keep",
        "reason": {
            "n": {"Low": "Your soil is low in nitrogen.", "Medium": "Your soil has medium nitrogen.",
                  "High": "Your soil already has high nitrogen."},
            "p": {"Low": "Your soil is low in phosphorus.", "Medium": "Your soil has medium phosphorus.",
                  "High": "Your soil already has high phosphorus."},
            "k": {"Low": "Your soil is low in potassium.", "Medium": "Your soil has medium potassium.",
                  "High": "Your soil already has high potassium."},
        },
        "legume_urea": "{crop} fixes its own nitrogen, so it needs little urea.",
        "reason_over": "Your soil has {level} {nutrient}, but last season's amount was more than the crop needs.",
        "level": {"Low": "low", "Medium": "medium", "High": "high"},
        "nutrient": {"n": "nitrogen", "p": "phosphorus", "k": "potassium"},
        "fix_zn": "Zinc is low: zinc sulphate {q} kg. Apply separately, never mix with DAP.",
        "fix_b": "Boron is low: borax {q} kg.",
        "fix_oc": "Organic carbon is low: farmyard manure {q} tonnes.",
        "fix_oc_paddy": "Or grow dhaincha green manure and plough it in before puddling.",
        "fix_lime": "Soil is acidic (pH {v}): apply agricultural lime.",
        "fix_gyp_ph": "Soil is alkaline (pH {v}): apply gypsum.",
        "fix_ec": "Soil is salty (EC {v}): use a salt tolerant variety and leach salts before sowing.",
        "fix_gn_gyp": "Groundnut: gypsum {q} kg at flowering (about 40 to 45 days).",
        "no_fixes": "No extra soil fixes needed.",
        "old_cost": "Last season", "new_cost": "This season", "diff": "Difference",
        "save": "You save", "extra": "Extra spend",
        "say_change": "{f}: {action}. Last season {old}, now {new}.",
        "say_cost": "Cost. Last season you spent {old} rupees. This season it is {new} rupees.",
        "say_save": "You save {d} rupees.",
        "say_extra": "You spend {d} rupees extra, for a better crop.",
        "footer": "Doses illustrative, to be replaced with ANGRAU recommendations. Prices are placeholders.",
    },
    "te": {
        "subtitle": "నేల ఆరోగ్య కార్డు నుండి పని వరకు",
        "language": "భాష",
        "load_sample": "నమూనా ఎంచుకోండి",
        "none": "ఏదీ లేదు",
        "upload": "నేల ఆరోగ్య కార్డు ఫోటో అప్‌లోడ్ చేయండి (JPG/PNG)",
        "read_card": "కార్డు చదవండి",
        "reading": "కార్డు చదువుతున్నాం...",
        "read_ok": "ఫోటో నుండి విలువలు నింపాం. ఒకసారి చూసి సరిచేయండి.",
        "read_fail": "కార్డు చదవలేకపోయాం",
        "read_missing": "కార్డులో కనిపించలేదు: {names}. ఈ విలువలు మీరే నింపండి.",
        "not_card": "ఇది నేల ఆరోగ్య కార్డు లాగా లేదు (యూనిట్లు వేరుగా ఉండవచ్చు లేదా చాలా పొలాలు ఉండవచ్చు). "
                    "ఏమీ నింపలేదు. విలువలు నింపండి లేదా నమూనా ఎంచుకోండి.",
        "no_key": "Card reading needs an API key, enter values or load a sample.",
        "soil_values": "నేల ఆరోగ్య కార్డు విలువలు",
        "farm": "మీ పొలం",
        "crop": "పంట", "season": "సీజన్", "acres": "ఎకరాలు",
        "last_season": "గత సీజన్ ఎకరానికి బస్తాలు",
        "make_plan": "నా ప్లాన్ చూపించు",
        "listen": "🔊 వినండి",
        "audio_fail": "ఆడియో ఇప్పుడు అందుబాటులో లేదు",
        "other_crop": "అదే నేల, వేరే పంట",
        "crops": {"Paddy": "వరి", "Groundnut": "వేరుశనగ", "Maize": "మొక్కజొన్న",
                  "Cotton": "పత్తి", "Chilli": "మిరప", "Redgram": "కంది"},
        "urea": "యూరియా", "dap": "డీఏపీ", "mop": "పొటాష్",
        "zinc": "జింక్ సల్ఫేట్", "gypsum": "జిప్సం", "borax": "బోరాక్స్",
        "fym": "పశువుల ఎరువు", "lime": "సున్నం",
        "headline": "ఈ సీజన్‌లో {n} మార్పులు చేయండి",
        "headline_one": "ఈ సీజన్‌లో 1 మార్పు చేయండి",
        "headline_zero": "ఈ సీజన్‌లో అదే ఎరువు వేయండి",
        "detail_both": "{c} ఎరువుల మార్పులు, అదనంగా {extras}",
        "detail_extras_only": "ఎరువులు గత సీజన్ లాగానే, అదనంగా {extras}",
        "say_also": "అదనంగా కొనండి: {items}.",
        "read_farm": "పంట, సీజన్, ఎకరాలు కూడా కార్డు నుండి నింపాం. గత సీజన్ బస్తాలు మీరే నింపండి.",
        "for_acres": "{a} ఎకరాలకు",
        "buy": "ఏమి కొనాలి", "when": "ఎప్పుడు వేయాలి", "changes": "గత సీజన్ నుండి మార్పులు",
        "fixes": "నేల సవరణలు", "cost": "ఖర్చు",
        "about": "సుమారు", "bag": "బస్తా", "bags": "బస్తాలు", "kg": "కిలోలు",
        "less_half": "అర బస్తా కంటే తక్కువ",
        "no_need": "అవసరం లేదు",
        "transplanting": "నాట్లు వేసేటప్పుడు", "tillering": "పిలక దశలో (సుమారు 20-25 రోజులు)",
        "panicle": "అంకుర దశలో (సుమారు 45-50 రోజులు)",
        "sowing": "విత్తేటప్పుడు", "flowering": "పూత దశలో (సుమారు 40-45 రోజులు)",
        "knee_high": "మోకాలి ఎత్తు దశలో (సుమారు 30 రోజులు)",
        "tasseling": "జల్లు దశలో (సుమారు 50-55 రోజులు)",
        "squaring": "మొగ్గ దశలో (సుమారు 30-35 రోజులు)",
        "flowering_60": "పూత దశలో (సుమారు 60 రోజులు)",
        "days_30": "నాటిన సుమారు 30 రోజులకు",
        "all": "మొత్తం", "third_urea": "యూరియాలో ⅓ భాగం", "all_fert": "మొత్తం ఎరువు",
        "Reduce": "తగ్గించండి", "Increase": "పెంచండి", "Add": "కొత్తగా వేయండి", "Keep": "అలాగే ఉంచండి",
        "reason": {
            "n": {"Low": "మీ నేలలో నత్రజని తక్కువగా ఉంది.", "Medium": "మీ నేలలో నత్రజని మధ్యస్థంగా ఉంది.",
                  "High": "మీ నేలలో నత్రజని ఇప్పటికే ఎక్కువగా ఉంది."},
            "p": {"Low": "మీ నేలలో భాస్వరం తక్కువగా ఉంది.", "Medium": "మీ నేలలో భాస్వరం మధ్యస్థంగా ఉంది.",
                  "High": "మీ నేలలో భాస్వరం ఇప్పటికే ఎక్కువగా ఉంది."},
            "k": {"Low": "మీ నేలలో పొటాష్ తక్కువగా ఉంది.", "Medium": "మీ నేలలో పొటాష్ మధ్యస్థంగా ఉంది.",
                  "High": "మీ నేలలో పొటాష్ ఇప్పటికే ఎక్కువగా ఉంది."},
        },
        "legume_urea": "{crop} తనకు కావలసిన నత్రజని తానే తీసుకుంటుంది, కాబట్టి యూరియా కొంచెమే చాలు.",
        "reason_over": "మీ నేలలో {nutrient} {level}గా ఉంది, కానీ గత సీజన్ వేసింది పంటకు కావలసిన దానికంటే ఎక్కువ.",
        "level": {"Low": "తక్కువ", "Medium": "మధ్యస్థం", "High": "ఎక్కువ"},
        "nutrient": {"n": "నత్రజని", "p": "భాస్వరం", "k": "పొటాష్"},
        "fix_zn": "జింక్ తక్కువ: జింక్ సల్ఫేట్ {q} కిలోలు. విడిగా వేయండి, డీఏపీతో కలపకండి.",
        "fix_b": "బోరాన్ తక్కువ: బోరాక్స్ {q} కిలోలు.",
        "fix_oc": "సేంద్రియ కర్బనం తక్కువ: పశువుల ఎరువు {q} టన్నులు.",
        "fix_oc_paddy": "లేదా జీలుగ పచ్చిరొట్ట పెంచి, దమ్ము చేసే ముందు కలియదున్నండి.",
        "fix_lime": "నేల పులుపు (pH {v}): సున్నం వేయండి.",
        "fix_gyp_ph": "నేల క్షార గుణం (pH {v}): జిప్సం వేయండి.",
        "fix_ec": "నేలలో ఉప్పు ఎక్కువ (EC {v}): ఉప్పు తట్టుకునే రకం వాడండి, విత్తే ముందు నీటితో ఉప్పు కడిగేయండి.",
        "fix_gn_gyp": "వేరుశనగ: పూత దశలో (సుమారు 40-45 రోజులు) జిప్సం {q} కిలోలు.",
        "no_fixes": "అదనపు నేల సవరణలు అవసరం లేదు.",
        "old_cost": "గత సీజన్", "new_cost": "ఈ సీజన్", "diff": "తేడా",
        "save": "మీకు ఆదా", "extra": "అదనపు ఖర్చు",
        "say_change": "{f}: {action}. గత సీజన్ {old}, ఇప్పుడు {new}.",
        "say_cost": "ఖర్చు. గత సీజన్ మీరు {old} రూపాయలు ఖర్చు పెట్టారు. ఈ సీజన్ {new} రూపాయలు.",
        "say_save": "మీకు {d} రూపాయలు ఆదా.",
        "say_extra": "మంచి పంట కోసం {d} రూపాయలు అదనంగా ఖర్చు అవుతుంది.",
        "footer": "Doses illustrative, to be replaced with ANGRAU recommendations. ధరలు ఉదాహరణ మాత్రమే.",
    },
}


def rate(key, value):
    low, high = RATING_LIMITS[key]
    if value < low:
        return "Low"
    if value > high:
        return "High"
    return "Medium"


def num(x):
    """Short number text: 4.0 -> '4', 2.5 -> '2.5'."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def half_text(x):
    r = round(x * 2) / 2
    whole = int(r)
    if r == whole:
        return str(whole)
    return "½" if whole == 0 else f"{whole}½"


def bag_text(kg, fert, t):
    if kg <= 0:
        return t["no_need"]
    bags = kg / BAG_KG[fert]
    r = round(bags * 2) / 2
    if r == 0:
        return f"{t['less_half']} ({kg:.0f} {t['kg']})"
    word = t["bag"] if r <= 1 else t["bags"]
    return f"{t['about']} {half_text(bags)} {word} ({kg:.0f} {t['kg']})"


def make_plan(soil, crop, acres, last, lang="en"):
    """soil: dict ph,ec,oc,n,p,k,zn,b. last: dict urea,dap,mop in bags per acre."""
    t = TEXT[lang]
    area_ha = acres * ACRE_TO_HA
    ratings = {k: rate(k, soil[k]) for k in ("n", "p", "k", "oc")}

    base_n, base_p, base_k = BASE_DOSE[crop]
    n_need = base_n * FACTOR[ratings["n"]] * area_ha
    p_need = base_p * FACTOR[ratings["p"]] * area_ha
    k_need = base_k * FACTOR[ratings["k"]] * area_ha

    dap_kg = p_need / 0.46
    urea_kg = max(0.0, n_need - dap_kg * 0.18) / 0.46
    mop_kg = k_need / 0.60
    kg = {"urea": urea_kg, "dap": dap_kg, "mop": mop_kg}
    bags = {f: round(kg[f] / BAG_KG[f] * 2) / 2 for f in kg}

    buy = [(t[f], bag_text(kg[f], f, t)) for f in ("urea", "dap", "mop")]

    # Soil fixes (per acre quantities x acres)
    fixes, extra_buy = [], []
    if soil["zn"] < 0.6:
        q = 20 * acres
        fixes.append(t["fix_zn"].format(q=num(q)))
        extra_buy.append((t["zinc"], f"{num(q)} {t['kg']}"))
    if soil["b"] < 0.5:
        q = 4 * acres
        fixes.append(t["fix_b"].format(q=num(q)))
        extra_buy.append((t["borax"], f"{num(q)} {t['kg']}"))
    if ratings["oc"] == "Low":
        fixes.append(t["fix_oc"].format(q=num(4 * acres)))
        if crop == "Paddy":
            fixes.append(t["fix_oc_paddy"])
    if soil["ph"] < 6.5:
        fixes.append(t["fix_lime"].format(v=num(soil["ph"])))
    if soil["ph"] > 8.5:
        fixes.append(t["fix_gyp_ph"].format(v=num(soil["ph"])))
    if soil["ec"] > 3:
        fixes.append(t["fix_ec"].format(v=num(soil["ec"])))
    if crop == "Groundnut":
        q = 200 * acres
        fixes.append(t["fix_gn_gyp"].format(q=num(q)))
        extra_buy.append((t["gypsum"], f"{num(q)} {t['kg']}"))
    legume_note = t["legume_urea"].format(crop=t["crops"][crop])
    if crop in LEGUMES:
        fixes.append(legume_note)

    # When to apply
    item_text = {
        "dap": f"{t['all']} {t['dap']}", "mop": f"{t['all']} {t['mop']}",
        "urea3": t["third_urea"], "zinc": t["zinc"],
        "all_fert": t["all_fert"], "gypsum": t["gypsum"],
    }
    when = []
    for stage, items in SCHEDULE[crop]:
        items = [i for i in items if i != "zinc" or soil["zn"] < 0.6]
        when.append((t[stage], ", ".join(item_text[i] for i in items)))

    # Compare with last season (whole farm)
    rating_for = {"urea": "n", "dap": "p", "mop": "k"}
    changes, spoken_changes, n_changes = [], [], 0
    for f in ("urea", "dap", "mop"):
        old = last[f] * acres
        new = bags[f]  # compare what the farmer will actually buy
        if old == 0:
            action = "Add" if bags[f] > 0 else "Keep"
        elif abs(new - old) <= 0.1 * old:
            action = "Keep"
        else:
            action = "Reduce" if new < old else "Increase"
        if action != "Keep":
            n_changes += 1
        old_word = t["bag"] if 0 < old <= 1 else t["bags"]
        new_txt = bag_text(kg[f], f, t).split(" (")[0]
        reason = t["reason"][rating_for[f]][ratings[rating_for[f]]]
        if action == "Reduce" and ratings[rating_for[f]] != "High":
            reason = t["reason_over"].format(level=t["level"][ratings[rating_for[f]]],
                                             nutrient=t["nutrient"][rating_for[f]])
        if crop in LEGUMES and f == "urea":
            reason = legume_note
        line = f"{t[f]}: {num(old)} {old_word} → {new_txt}. {reason}"
        changes.append((t[action], action, line))
        spoken_changes.append(t["say_change"].format(
            f=t[f], action=t[action], old=f"{num(old)} {old_word}", new=new_txt))

    old_cost = sum(last[f] * acres * PRICE[f] for f in PRICE)
    new_cost = sum(bags[f] * PRICE[f] for f in PRICE)

    # The headline counts fertiliser changes vs last season plus each extra purchase (soil fixes).
    total = n_changes + len(extra_buy)
    if total == 0:
        headline = t["headline_zero"]
    else:
        headline = t["headline_one"] if total == 1 else t["headline"].format(n=total)
    extras = ", ".join(name for name, _ in extra_buy)
    if not extra_buy:
        headline_detail = None
    elif n_changes:
        headline_detail = t["detail_both"].format(c=n_changes, extras=extras)
    else:
        headline_detail = t["detail_extras_only"].format(extras=extras)
    return {
        "headline": headline,
        "headline_detail": headline_detail,
        "fertiliser_changes": n_changes,
        "ratings": ratings,
        "buy": buy,
        "extra_buy": extra_buy,
        "when": when,
        "changes": changes,
        "spoken_changes": spoken_changes,
        "fixes": fixes or [t["no_fixes"]],
        "old_cost": old_cost,
        "new_cost": new_cost,
        "kg": kg,
        "bags": bags,
    }


TE_NUM = ["", "ఒకటి", "రెండు", "మూడు", "నాలుగు", "ఐదు", "ఆరు", "ఏడు", "ఎనిమిది", "తొమ్మిది", "పది"]
TE_HALF = ["అర", "ఒకటిన్నర", "రెండున్నర", "మూడున్నర", "నాలుగున్నర", "ఐదున్నర",
           "ఆరున్నర", "ఏడున్నర", "ఎనిమిదిన్నర", "తొమ్మిదిన్నర", "పదిన్నర"]


def _speak_numbers(text, lang):
    """Make bag counts and fractions sound natural when read aloud."""
    text = re.sub(r" \(\d+ (kg|కిలోలు)\)", "", text)  # kg in brackets is for reading, not listening
    if lang == "te":
        text = re.sub(r"(\d*)½", lambda m: TE_HALF[int(m.group(1) or 0)]
                      if int(m.group(1) or 0) <= 10 else f"{m.group(1)} అర", text)
        text = text.replace("⅓ భాగం", "మూడో వంతు").replace("⅓", "మూడో వంతు")
    else:
        text = re.sub(r"(\d+)½", r"\1 and a half", text).replace("½", "half a").replace("⅓", "one third")
    return text.replace("→", ",")


def speech_text(plan, lang):
    """Short audio: the headline, what changes from last season, and the money saved or spent.
    Buying details, timing, soil fixes and reasons stay on screen."""
    t = TEXT[lang]
    diff = plan["new_cost"] - plan["old_cost"]
    parts = [plan["headline"] + "."]
    parts.append(" ".join(plan["spoken_changes"]))
    if plan["extra_buy"]:
        parts.append(t["say_also"].format(items=", ".join(f"{n} {v}" for n, v in plan["extra_buy"])))
    parts.append(t["say_cost"].format(old=f"{plan['old_cost']:.0f}", new=f"{plan['new_cost']:.0f}"))
    parts.append((t["say_save"] if diff < 0 else t["say_extra"]).format(d=f"{abs(diff):.0f}"))
    return _speak_numbers(" ".join(parts), lang)
