# Nela Mitra: quick demo build (HackAP 2026)

## Goal

Build a simple Streamlit demo for a hackathon. Keep the code minimal and get it working fast.

1. No tests, no test files, no extra tooling.
2. Do not ask me questions. Build it, run `streamlit run app.py` once to confirm it starts without errors, and stop.

**What it does:** the user loads a sample, enters Soil Health Card values, or uploads a card photo. They pick the crop, acres and last season's fertiliser bags. The app shows a simple Action Card in Telugu or English with a Listen button.

**Design rule:** Python rules calculate every quantity. The AI only reads the card photo into numbers.

## Files

Create only these four files:

1. app.py
2. engine.py, containing the rules, sample data and Telugu/English text
3. extract.py, for reading the card photo with Groq
4. requirements.txt with streamlit, groq, gtts and pillow

Also create one image, sample_card.png. Make it a simple English Soil Health Card for Sample A drawn with Pillow, marked "SAMPLE", so I can demo the upload.

## Rules (engine.py)

### Ratings

| Value | Low | Medium | High |
|---|---|---|---|
| N kg/ha | below 280 | 280 to 560 | above 560 |
| P kg/ha | below 10 | 10 to 25 | above 25 |
| K kg/ha | below 110 | 110 to 280 | above 280 |
| OC % | below 0.5 | 0.5 to 0.75 | above 0.75 |

### Base doses

These are N : P2O5 : K2O in kg/ha, and they are illustrative only. Show a footer note: "Doses illustrative, to be replaced with ANGRAU recommendations."

1. Paddy: 120 : 60 : 40
2. Groundnut: 20 : 40 : 40

### Adjustment

1. Low rating: multiply the base dose by 1.25.
2. Medium rating: use the base dose as is.
3. High rating: multiply the base dose by 0.75.

### Bags

1. area_ha = acres × 0.4047
2. DAP kg = P2O5 need / 0.46
3. N from DAP = DAP kg × 0.18
4. Urea kg = max(0, N need minus N from DAP) / 0.46
5. MOP kg = K2O need / 0.60
6. Bag sizes: urea 45 kg, DAP 50 kg, MOP 50 kg.
7. Show bags rounded to the nearest half, with kg alongside, for example "about 2½ bags (117 kg)".

### Soil fixes

Quantities are per acre, so multiply by acres.

1. **Zn below 0.6:** zinc sulphate 20 kg per acre, applied separately, never mixed with DAP.
2. **B below 0.5:** borax 4 kg per acre.
3. **OC Low:** farmyard manure 4 tonnes per acre. For paddy, dhaincha green manure before puddling is an alternative.
4. **pH below 6.5:** agricultural lime.
5. **pH above 8.5:** gypsum.
6. **EC above 3:** salt tolerant variety, and leach salts before sowing.
7. **Groundnut:** always add gypsum 200 kg per acre at flowering, about 40 to 45 days. Note that it needs little urea.

### When to apply

1. **Paddy:**
   1. At transplanting: all DAP, all MOP, one third of the urea, and zinc sulphate.
   2. At tillering (about 20 to 25 days): one third of the urea.
   3. At panicle initiation (about 45 to 50 days): the last third of the urea.
2. **Groundnut:**
   1. At sowing: all fertiliser.
   2. At flowering: gypsum.

### Compare with last season

Last season's bags are entered per acre.

1. For urea, DAP and MOP, label each as Reduce, Increase, Add (was zero) or Keep (within 10 percent).
2. Add a one line reason from the soil rating. Example: "DAP: 2 bags → about 1 bag. Your soil already has high phosphorus."
3. Show the old cost, new cost and difference, using these fixed placeholder prices:
   1. Urea ₹266.50 per bag
   2. DAP ₹1350 per bag
   3. MOP ₹1700 per bag
4. Headline: "This season, change N things".

## Sample farmers (in engine.py)

| | Sample A | Sample B |
|---|---|---|
| Description | Godavari paddy | Rayalaseema groundnut |
| Season | Rabi | Kharif |
| Acres | 1 | 2 |
| pH | 8.2 | 6.2 |
| EC | 0.6 | 0.3 |
| OC | 0.42 | 0.35 |
| N | 210 | 180 |
| P | 28 | 8 |
| K | 150 | 95 |
| Zn | 0.4 | 0.5 |
| B | 0.7 | 0.3 |
| Last season Urea (bags/acre) | 3 | 1 |
| Last season DAP (bags/acre) | 2 | 1 |
| Last season MOP (bags/acre) | 0 | 0 |

## Card photo reading (extract.py)

1. **Model call.**
   1. Use the groq SDK with GROQ_API_KEY from st.secrets or an environment variable.
   2. Use the model "qwen/qwen3.6-27b". If that id is rejected, check https://console.groq.com/docs/vision for the current vision model.
   3. Accept JPG or PNG only. Resize to a maximum of 1600 px and send it as a base64 data URL.
2. **Reading the reply.**
   1. Ask for JSON only, with the keys ph, ec, oc, n, p, k, zn and b, using null if a value is not visible.
   2. Use response_format json_object and temperature 0.
   3. Strip any think tags or code fences before json.loads, and convert values to float.
3. **Using the result.** Fill the input boxes with the values so the user can correct them.
4. **No key.** If no key is set, hide the upload box and show "Card reading needs an API key, enter values or load a sample."

## Telugu and audio

1. **Text.** Put all user facing text in a small dict, in English and simple spoken Telugu. Use farmer words:

| English | Telugu |
|---|---|
| bags | బస్తాలు |
| acre | ఎకరం |
| urea | యూరియా |
| DAP | డీఏపీ |
| MOP | పొటాష్ |
| zinc sulphate | జింక్ సల్ఫేట్ |
| gypsum | జిప్సం |
| tillering | పిలక దశ |
| panicle initiation | అంకుర దశ |
| flowering | పూత దశ |
| farmyard manure | పశువుల ఎరువు |
| dhaincha | జీలుగ |

2. **Listen button.** Play gTTS audio (lang "te") of the headline and the buy list. If it fails, show a small warning and continue.

## Screen layout (app.py, one page)

1. **Title.** Nela Mitra (నేల మిత్ర), with the subtitle "Soil Health Card to action".
2. **Sidebar.** A language choice (తెలుగు / English, default Telugu) and a "Load sample" choice (None, Sample A, Sample B).
3. **Inputs.**
   1. Optional photo upload.
   2. Number boxes for pH, EC, OC, N, P, K, Zn and B.
   3. Crop, season and acres.
   4. Last season's urea, DAP and MOP bags.
4. **Make my plan button.** It shows the Action Card, built with simple HTML and emoji (🌾 🧪 📅 🔄 🌱 💰), large text and a green theme. The card has these sections in order:
   1. Headline
   2. What to buy
   3. When to apply
   4. What changes from last season
   5. Soil fixes
   6. Cost
   7. Footer note
5. **Listen button.**
6. **Expander "Same soil, other crop".** It shows the buy list and cost for the other crop, to prove the advice is crop specific.

Use st.session_state so a loaded sample fills the inputs.

## When done

Print five short lines on how to deploy to Streamlit Community Cloud, including where to paste GROQ_API_KEY in the app secrets.