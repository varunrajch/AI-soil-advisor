import io

import streamlit as st

from engine import BASE_DOSE, SAMPLES, TEXT, make_plan, speech_text
from extract import get_api_key, read_card

st.set_page_config(page_title="Nela Mitra", page_icon="🌾", layout="centered")

SOIL_KEYS = ["ph", "ec", "oc", "n", "p", "k", "zn", "b"]
SOIL_LABELS = {
    "ph": "pH", "ec": "EC (dS/m)", "oc": "OC (%)", "n": "N (kg/ha)",
    "p": "P (kg/ha)", "k": "K (kg/ha)", "zn": "Zn (ppm)", "b": "B (ppm)",
}
DEFAULTS = {
    "ph": 7.0, "ec": 0.5, "oc": 0.5, "n": 280.0, "p": 15.0, "k": 200.0, "zn": 0.8, "b": 0.6,
    "crop": "Paddy", "season": "Kharif", "acres": 1.0,
    "last_urea": 0.0, "last_dap": 0.0, "last_mop": 0.0,
}
for key, val in DEFAULTS.items():
    st.session_state.setdefault(key, val)
st.session_state.setdefault("show_plan", False)


def load_sample():
    name = st.session_state["sample"]
    if name in SAMPLES:
        for key in DEFAULTS:
            st.session_state[key] = SAMPLES[name][key]
        st.session_state["show_plan"] = False


def read_photo():
    file = st.session_state.get("photo")
    if file is None:
        return
    try:
        values = read_card(file.getvalue(), get_api_key())
        if not values.pop("is_shc"):
            st.session_state["read_msg"] = ("not_card", None)
            return
        missing = [SOIL_LABELS[k] for k in SOIL_KEYS if values[k] is None]
        # soil values plus crop, season and acres when the card shows them
        for key, v in values.items():
            if v is not None:
                st.session_state[key] = v
        farm_read = any(values.get(k) is not None for k in ("crop", "season", "acres"))
        st.session_state["show_plan"] = False
        st.session_state["read_msg"] = ("ok", missing, farm_read)
    except Exception as e:
        st.session_state["read_msg"] = ("fail", str(e))


# ---------- Sidebar ----------
lang_choice = st.sidebar.radio("భాష / Language", ["English", "తెలుగు"], index=0)
lang = "te" if lang_choice == "తెలుగు" else "en"
t = TEXT[lang]
st.sidebar.selectbox(
    t["load_sample"], ["None", "Sample A", "Sample B"], key="sample", on_change=load_sample,
    format_func=lambda s: t["none"] if s == "None" else f"{s}: {SAMPLES[s]['desc']}",
)

# ---------- Title ----------
st.title("🌾 Nela Mitra (నేల మిత్ర)")
st.caption("Soil Health Card to action" + ("" if lang == "en" else f" · {t['subtitle']}"))

# ---------- Photo upload ----------
if get_api_key():
    st.file_uploader(t["upload"], type=["jpg", "jpeg", "png"], key="photo")
    if st.session_state.get("photo") is not None:
        st.button(t["read_card"], on_click=read_photo)
    msg = st.session_state.pop("read_msg", None)
    if msg and msg[0] == "ok":
        st.success(t["read_ok"])
        if len(msg) > 2 and msg[2]:
            st.info(t["read_farm"])
        if msg[1]:
            st.warning(t["read_missing"].format(names=", ".join(msg[1])))
    elif msg and msg[0] == "not_card":
        st.warning(t["not_card"])
    elif msg:
        st.error(f"{t['read_fail']}: {msg[1]}")
else:
    st.info(TEXT["en"]["no_key"])

# ---------- Inputs ----------
st.subheader("🧪 " + t["soil_values"])
cols = st.columns(4)
for i, key in enumerate(SOIL_KEYS):
    cols[i % 4].number_input(SOIL_LABELS[key], min_value=0.0, step=0.1, format="%.2f", key=key)

st.subheader("🌱 " + t["farm"])
c1, c2, c3 = st.columns(3)
c1.selectbox(t["crop"], list(BASE_DOSE), key="crop", format_func=lambda c: t["crops"][c])
c2.selectbox(t["season"], ["Kharif", "Rabi"], key="season")
c3.number_input(t["acres"], min_value=0.1, step=0.5, key="acres")

st.subheader("🔄 " + t["last_season"])
l1, l2, l3 = st.columns(3)
l1.number_input(t["urea"], min_value=0.0, step=0.5, key="last_urea")
l2.number_input(t["dap"], min_value=0.0, step=0.5, key="last_dap")
l3.number_input(t["mop"], min_value=0.0, step=0.5, key="last_mop")

if st.button(t["make_plan"], type="primary", use_container_width=True):
    st.session_state["show_plan"] = True

# ---------- Action Card ----------
CARD_CSS = """
<style>
.card {background:#f1f8e9;border:3px solid #2e7d32;border-radius:16px;padding:20px 24px;
       color:#1b3a1d;font-size:1.15rem;line-height:1.6;}
.card h2 {color:#1b5e20;font-size:1.7rem;margin:0 0 8px 0;}
.card .detail {color:#4e6b50;font-size:1rem;margin:-4px 0 6px 0;}
.card h3 {color:#2e7d32;font-size:1.3rem;margin:18px 0 6px 0;border-bottom:1px solid #a5d6a7;}
.card ul {margin:0;padding-left:22px;}
.card .tag {display:inline-block;background:#2e7d32;color:white;border-radius:8px;
            padding:0 8px;font-size:0.95rem;margin-right:6px;}
.card .keep {background:#78909c;}
.card .foot {font-size:0.85rem;color:#555;margin-top:18px;border-top:1px dashed #a5d6a7;padding-top:8px;}
</style>
"""


def rupees(x):
    return f"₹{x:,.0f}"


def cost_lines(plan):
    diff = plan["new_cost"] - plan["old_cost"]
    label = t["save"] if diff < 0 else t["extra"]
    return [
        f"{t['old_cost']}: <b>{rupees(plan['old_cost'])}</b>",
        f"{t['new_cost']}: <b>{rupees(plan['new_cost'])}</b>",
        f"{label}: <b>{rupees(abs(diff))}</b>",
    ]


def ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def card_html(plan, acres):
    buy = [f"<b>{n}</b>: {v}" for n, v in plan["buy"] + plan["extra_buy"]]
    when = [f"<b>{w}</b>: {what}" for w, what in plan["when"]]
    changes = [
        f"<span class='tag{' keep' if a == 'Keep' else ''}'>{label}</span>{line}"
        for label, a, line in plan["changes"]
    ]
    return (
        CARD_CSS + "<div class='card'>"
        f"<h2>🌾 {plan['headline']}</h2>"
        + (f"<p class='detail'>{plan['headline_detail']}</p>" if plan["headline_detail"] else "") +
        f"<h3>🧪 {t['buy']} ({t['for_acres'].format(a=f'{acres:g}')})</h3>{ul(buy)}"
        f"<h3>📅 {t['when']}</h3>{ul(when)}"
        f"<h3>🔄 {t['changes']}</h3>{ul(changes)}"
        f"<h3>🌱 {t['fixes']}</h3>{ul(plan['fixes'])}"
        f"<h3>💰 {t['cost']}</h3>{ul(cost_lines(plan))}"
        f"<div class='foot'>{t['footer']}</div>"
        "</div>"
    )


if st.session_state["show_plan"]:
    s = st.session_state
    soil = {k: float(s[k]) for k in SOIL_KEYS}
    last = {"urea": s["last_urea"], "dap": s["last_dap"], "mop": s["last_mop"]}
    plan = make_plan(soil, s["crop"], s["acres"], last, lang)
    st.markdown(card_html(plan, s["acres"]), unsafe_allow_html=True)

    st.write("")
    if st.button(t["listen"]):
        try:
            from gtts import gTTS

            te_plan = make_plan(soil, s["crop"], s["acres"], last, "te")
            buf = io.BytesIO()
            with st.spinner("🔊 ..."):
                gTTS(speech_text(te_plan, "te"), lang="te").write_to_fp(buf)
            st.audio(buf.getvalue(), format="audio/mp3")
        except Exception as e:
            st.warning(f"{t['audio_fail']} ({e})")

    with st.expander(f"🔁 {t['other_crop']}"):
        others = [c for c in BASE_DOSE if c != s["crop"]]
        other = st.selectbox(t["crop"], others, format_func=lambda c: t["crops"][c], key="other_crop")
        op = make_plan(soil, other, s["acres"], last, lang)
        buy = [f"<b>{n}</b>: {v}" for n, v in op["buy"] + op["extra_buy"]]
        st.markdown(
            CARD_CSS + "<div class='card'>"
            f"<h3>🧪 {t['buy']}</h3>{ul(buy)}"
            f"<h3>💰 {t['cost']}</h3>{ul(cost_lines(op))}"
            "</div>",
            unsafe_allow_html=True,
        )
