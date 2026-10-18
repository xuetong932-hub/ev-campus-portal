# ⚡ Campus EV Charging Research Portal

**ITS72604 Principles of Programming · Assessment 2 · Taylor's University**

An end-to-end data science project for Taylor's Smart Campus EV charging network.
It cleans 1,200 historical charging sessions, trains and evaluates a machine
learning model that predicts the charger's grid status, and serves everything
through a secure, multi-page Streamlit web portal.

| | |
|---|---|
| **Live app** | https://xuetong-ev-campus-portal.streamlit.app |
| **Repository** | https://github.com/xuetong932-hub/ev-campus-portal |
| **Author** | Xue Tong |
| **Stack** | Python 3.12 · pandas · NumPy · scikit-learn · Matplotlib · Seaborn · Streamlit |

![Sign-in page](docs/screenshots/01_sign_in.png)

---

## Contents

1. [What the project does](#1-what-the-project-does)
2. [Screenshots](#2-screenshots)
3. [Repository structure](#3-repository-structure)
4. [The dataset](#4-the-dataset)
5. [Quick start (run locally)](#5-quick-start-run-locally)
6. [Task 1 – Data pipeline](#6-task-1--eda-and-preprocessing-pipeline)
7. [Task 2 – Machine learning](#7-task-2--machine-learning-workflow)
8. [Task 3 – Streamlit web portal](#8-task-3--streamlit-web-portal)
9. [Task 4 – Deployment](#9-task-4--deployment)
10. [Testing](#10-testing)
11. [Configuration reference](#11-configuration-reference)
12. [Troubleshooting](#12-troubleshooting)
13. [Limitations and future work](#13-limitations-and-future-work)
14. [Credits](#14-credits)

Further documentation:

* [docs/USER_GUIDE.md](docs/USER_GUIDE.md) – how to use every screen of the portal
* [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) – step-by-step GitHub upload and Streamlit Cloud deployment
* [docs/TECHNICAL.md](docs/TECHNICAL.md) – architecture, module reference, data flow and design decisions

---

## 1. What the project does

| Task | Deliverable | What it does |
|---|---|---|
| **1 · EDA & preprocessing** | `data_pipeline.py` → `cleaned_ev_dataset.csv` | Profiles the raw data, removes duplicates, median-imputes missing values, engineers `Power_kW`, `Peak_Hour_Flag` and `Energy_Efficiency_Group`, and produces group-by summary tables. |
| **2 · Machine learning** | `train_ev_model.py` → `ev_model.pkl` | Follows the 7-step ML framework; compares Decision Tree, Random Forest and KNN against a baseline with 5-fold cross-validation; reports accuracy, precision, recall, F1 and Seaborn confusion matrices; saves the best pipeline. |
| **3 · Web portal** | `app.py` (+ `ui.py`, `auth.py`, `ev_core.py`) | Login-protected portal with three workspaces: an Executive KPI Dashboard, a Visual Analytics Studio and Live Machine Learning Inference with colour-coded alerts. |
| **4 · Deployment** | This repository + Streamlit Community Cloud | Clean repository with pinned `requirements.txt`, deployed as a public web app. |

Portal highlights:

* **Sign-in page** with an interactive night-sky animation (mouse-parallax stars, a glowing moon and shooting stars) over a photo of an EV charging station.
* **User accounts:** only user IDs recorded in `ev_campus_dataset.csv` can sign in; new users register first and are appended to the dataset.
* **Onboarding guide:** a five-step tour shown the first time a newly registered user signs in.
* **Official-website style navigation bar** with an account menu.
* **Dark, premium design** with glass cards and a consistent colour system across the UI and charts.

---

## 2. Screenshots

| Sign-in and registration | First-login onboarding guide |
|---|---|
| ![Register](docs/screenshots/02_register.png) | ![Guide](docs/screenshots/03_onboarding_guide.png) |

| Executive KPI Dashboard | Visual Analytics Studio |
|---|---|
| ![Dashboard](docs/screenshots/04_dashboard.png) | ![Analytics](docs/screenshots/05_analytics.png) |

| Live Machine Learning Inference | Account menu |
|---|---|
| ![Prediction](docs/screenshots/06_prediction.png) | ![Account](docs/screenshots/07_account_menu.png) |

---

## 3. Repository structure

```
ev-campus-portal/
├── app.py                            # Streamlit entry point: pages, navigation, login, onboarding
├── ui.py                             # Design system: CSS theme, top navigation, starfield animation
├── auth.py                           # Login / registration / onboarding state (backed by the CSV)
├── ev_core.py                        # Data validation, revenue estimation, model loading & inference
├── assessment1_billing_reference.py  # Assessment 1 billing rules, reused for revenue estimates
│
├── data_pipeline.py                  # TASK 1 – EDA, cleaning, feature engineering, summaries
├── train_ev_model.py                 # TASK 2 – 7-step ML workflow, evaluation, model export
├── test_app.py                       # 13 automated tests (data, model, billing, login, all pages)
│
├── ev_campus_dataset.csv             # Raw data (1,200 sessions) – also the list of user IDs
├── cleaned_ev_dataset.csv            # TASK 1 output used by the dashboard
├── summary_by_charger.csv            # TASK 1 group-by tables
├── summary_by_peak.csv
├── summary_by_charger_and_peak.csv
├── status_rate_by_charger_and_peak.csv
├── cleaning_report.json              # TASK 1 audit log (missing values, medians, thresholds)
│
├── ev_model.pkl                      # TASK 2 output: best model (preprocessing + classifier)
├── model_metadata.json               # TASK 2 metrics, confusion matrix, feature importance
├── test_predictions.csv              # TASK 2 predictions on the 240-row test set
├── reports/                          # TASK 2 figures and per-model classification reports
│   ├── confusion_matrices_all.png
│   ├── confusion_matrix_{DecisionTree,RandomForest,KNN}.png
│   ├── classification_report_{DecisionTree,RandomForest,KNN}.csv
│   ├── model_comparison.png / .csv
│   ├── feature_importance.png / .csv
│   └── decision_tree.png / decision_tree_rules.txt
│
├── requirements.txt                  # Exact package versions (needed to load ev_model.pkl)
├── .streamlit/config.toml            # Theme and server settings
├── .gitignore
└── docs/
    ├── USER_GUIDE.md
    ├── DEPLOYMENT.md
    ├── TECHNICAL.md
    └── screenshots/
```

---

## 4. The dataset

`ev_campus_dataset.csv` – 1,200 charging sessions, 9 columns.

| Column | Type | Description | Range in data |
|---|---|---|---|
| `Session_ID` | string | Unique session identifier; **also used as the login user ID** | SESS-1000 … SESS-2199 |
| `Charger_Type` | category | `AC` or `DC` | AC 784 · DC 416 |
| `User_Type` | category | `Staff`, `Student` or `Visitor` | – |
| `Start_Hour` | integer | Hour the session started | 0 – 23 |
| `Duration_Mins` | float | Plugged-in duration | 15 – 214 (25 missing) |
| `Energy_kWh` | float | Energy delivered | 3.66 – 49.64 (35 missing) |
| `Overstay_Mins` | integer | Minutes parked after charging finished | 0 – 188 |
| `Battery_Temp_C` | float | Battery temperature | 17.6 – 56.6 °C |
| `Grid_Status_Label` | target | `Normal`, `Overheated` or `Grid_Surge` | 898 / 130 / 172 |

### Differences from the assessment brief

The supplied file does not match the brief's data dictionary exactly. Each
difference is handled explicitly rather than hidden:

| Brief says | Supplied CSV | How it is handled |
|---|---|---|
| `AC_Fast` / `DC_Ultra` | `AC` / `DC` | Values kept as they are |
| `Ambient_Temp_C` column | not present; `Battery_Temp_C` exists | Battery temperature used and labelled as such everywhere |
| `Peak_Hour_Flag` column | not present; `Start_Hour` exists | Derived: `1` if `12 ≤ Start_Hour ≤ 17` |
| label `Grid Heavy` | `Grid_Surge` | Data label used |

Hour 17 is inside the peak window because the data contains Grid_Surge
sessions that start at 17:00.

---

## 5. Quick start (run locally)

Requirements: **Python 3.12** (3.13 also works) and Git or a downloaded ZIP of this repository.

```bash
# 1. Get the code
git clone https://github.com/xuetong932-hub/ev-campus-portal.git
cd ev-campus-portal

# 2. Create an isolated environment
python -m venv .venv
.venv\Scripts\activate              # Windows
# source .venv/bin/activate         # macOS / Linux

# 3. Install the exact package versions
pip install -r requirements.txt

# 4. Start the portal
streamlit run app.py
```

The browser opens at **http://localhost:8501**. Sign in with any existing ID,
for example `SESS-1000`, or register a new ID.

Optional – rebuild every artefact from the raw data:

```bash
python data_pipeline.py      # Task 1 → cleaned_ev_dataset.csv, summaries, cleaning_report.json
python train_ev_model.py     # Task 2 → ev_model.pkl, model_metadata.json, reports/
python test_app.py           # run the 13 automated tests
```

Both scripts accept `--input` and `--output-dir`, for example
`python data_pipeline.py --input ev_campus_dataset.csv --output-dir out/`.

---

## 6. Task 1 – EDA and preprocessing pipeline

`data_pipeline.py` runs five functions in order and prints a labelled section
for each, so the console output doubles as an audit log.

| Step | Function | What happens |
|---|---|---|
| 1 | `load_data`, `explore` | Checks required columns; prints `info()`, `describe()`, missing values and the class distribution |
| 2 | `clean` | Trims text; drops rows without an ID or valid label; removes exact and Session_ID duplicates; sets out-of-range values to NaN; **median-imputes** numeric columns; restores integer types |
| 3 | `engineer_features` | `Peak_Hour_Flag`, `Power_kW`, `Energy_Efficiency_Group` |
| 4 | `summarise` | Group-by tables by charger type, peak flag and both, plus status rates |
| 5 | `main` | Quality gates (`assert` no missing values / duplicate IDs), writes all outputs |

**Cleaning results**

| Item | Result |
|---|---|
| Rows in → out | 1,200 → 1,200 |
| Duplicates removed | 0 exact, 0 repeated Session_IDs |
| `Duration_Mins` imputed | 25 values with median 97.0 min |
| `Energy_kWh` imputed | 35 values with median 13.28 kWh |
| Missing values after cleaning | **0** |

**Engineered features**

* `Power_kW = Energy_kWh / (Duration_Mins / 60)` – average charging power.
* `Peak_Hour_Flag` – 1 when `12 ≤ Start_Hour ≤ 17` (442 sessions, 36.8 %).
* `Energy_Efficiency_Group` – Low / Medium / High power **tertiles computed within each charger type**.
  AC and DC work on very different power scales (≈ 6 kW vs ≈ 29 kW), so one global
  cut-off would label every DC session High.

| Charger | Low / Medium cut | Medium / High cut |
|---|---:|---:|
| AC | 5.57 kW | 6.28 kW |
| DC | 27.79 kW | 31.86 kW |

**Key findings from the summaries**

| | AC | DC |
|---|---:|---:|
| Sessions | 784 | 416 |
| Avg energy (kWh) | 11.79 | 22.56 |
| Avg battery temp (°C) | 31.94 | 40.78 |
| Avg duration (min) | 118.5 | 47.1 |
| Avg power (kW) | 5.99 | 29.35 |

* AC charging outside peak hours is 99.8 % Normal.
* About 30 % of DC sessions overheat at any time of day.
* Grid_Surge **never** occurs outside the 12:00–17:00 window.

---

## 7. Task 2 – Machine learning workflow

`train_ev_model.py` follows the **7-step framework**:

| Step | Implementation |
|---|---|
| 1. Define the problem | 3-class classification of `Grid_Status_Label`. Classes are imbalanced (75 % Normal), so models are compared by **macro F1**. |
| 2. Collect data | Raw CSV; duplicates and unlabelled rows removed; `Peak_Hour_Flag` derived with the Task 1 rule. |
| 3. Prepare data | 8 features (`Session_ID` excluded); **stratified 80/20 split** (960 / 240). |
| 4. Choose models | Decision Tree, Random Forest, KNN + majority-class baseline. |
| 5. Train & tune | `GridSearchCV`, 5-fold stratified CV on the training set only. |
| 6. Evaluate | Accuracy, precision, recall, F1, Seaborn confusion matrices on the untouched test set. |
| 7. Persist | Best pipeline saved with `joblib` as `ev_model.pkl`, reloaded and verified. |

All preprocessing (median imputer, one-hot encoder, scaler for KNN) lives
**inside a scikit-learn `Pipeline`**, so it is fitted on training data only
(no leakage) and travels with the model into the web app.

**Results**

| Model | CV macro F1 | Train acc. | Test acc. | Macro precision | Macro recall | Macro F1 |
|---|---:|---:|---:|---:|---:|---:|
| **Decision Tree (saved)** | **0.826** | 82.4 % | 79.6 % | 0.800 | 0.901 | **0.806** |
| Random Forest | 0.820 | 82.2 % | 79.6 % | 0.800 | 0.901 | 0.806 |
| KNN (scaled) | 0.667 | 100 % | 80.0 % | 0.743 | 0.669 | 0.697 |
| Baseline (always Normal) | – | – | 75.0 % | 0.250 | 0.333 | 0.286 |

* The Decision Tree was chosen by cross-validated macro F1 **before** the test set was used.
* KNN overfits (100 % train vs 80 % test); the tree does not (82.4 % vs 79.6 %).
* The tree catches **33 of 34 Grid_Surge** test sessions (97 % recall) and all 26 Overheated ones.

**Why accuracy stops near 80 %.** The tree learned two rules:
`Battery_Temp_C > 43 °C → Overheated` (true for 100 % of sessions) and
`peak hour → Grid_Surge`. Inside the peak window, 222 Normal and 172 Grid_Surge
sessions have identical measurements, so **no model can exceed about 85.7 %
accuracy** with these features. The remaining error is irreducible noise in the data.

Figures are in [`reports/`](reports/): confusion matrices, model comparison,
permutation feature importance and the decision tree itself.

---

## 8. Task 3 – Streamlit web portal

### Pages

| Page | Contents |
|---|---|
| **Sign in** (public) | Animated landing page, project statistics, Log in / Register card |
| **Dashboard** | `st.metric` cards (total energy 18,630.09 kWh · avg duration 93.8 min · estimated peak revenue RM 7,393.50 · sessions), grid-status and peak cards, filterable/sortable/downloadable session table |
| **Analytics** | Energy-vs-battery-temperature scatter, peak vs non-peak bars, charger-type distribution (Matplotlib/Seaborn); each chart downloadable |
| **Live Prediction** | Sidebar `st.selectbox` / `st.slider` / `st.number_input` → `ev_model.pkl` → `st.success` (Normal) / `st.warning` (Overheated) / `st.error` (Grid_Surge), class probabilities, model performance evidence |

Sidebar filters (charger type, user type, status, tariff period, start hour,
session ID search) update every KPI, card, table and chart together.

### Login and registration

* The dataset has no separate user table, so **`Session_ID` values are the user IDs**.
  IDs are case- and space-insensitive (` sess-1000 ` works).
* Unknown IDs are refused with *"not registered. Please register first."* and a **Register this ID** button.
* Registration validates the ID (3–20 letters, digits, `-`, `_`; must be new) and
  **appends a row to `ev_campus_dataset.csv`** containing only `Session_ID` and `User_Type`.
* Registered rows have no `Grid_Status_Label`, and both Task 1 and Task 2 drop such
  rows, so registrations never change the cleaned data or the model (covered by a test).

### Onboarding

The first time a **newly registered** user signs in, a five-step guide explains
the navigation, filters, alert colours and account menu. Finishing or skipping
records the user in `onboarded_users.json` so it is not shown again; it can be
replayed from the account menu at any time.

### Revenue estimate

The CSV has no prices, so revenue is **estimated** with the Assessment 1 billing
rules (`assessment1_billing_reference.py`): tiered hourly rates (AC RM 4/6/8/12,
DC RM 10/15/20/30), duration rounded up to whole hours, caps of RM 80 / RM 150
above 6 hours, 50 % staff and 25 % student-AC discounts, RM 5 peak surcharge
(adjustable in the sidebar) and RM 15 idle fee when `Overstay_Mins > 0`.

---

## 9. Task 4 – Deployment

The full illustrated walkthrough is in **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**. Summary:

1. Upload **the contents of this folder** to the GitHub repository
   `xuetong932-hub/ev-campus-portal` (branch `main`).
2. Go to **https://share.streamlit.io** → sign in with GitHub → **Create app** →
   *Deploy a public app from GitHub*.
3. Repository `xuetong932-hub/ev-campus-portal`, branch `main`, main file `app.py`,
   App URL `xuetong-ev-campus-portal`.
4. **Advanced settings → Python 3.12** → **Deploy**.

The app is then public at **https://xuetong-ev-campus-portal.streamlit.app**.

`requirements.txt` pins every package to the version used to train the model.
Two pins matter in particular:

* `scikit-learn==1.9.1` – the pickled pipeline is loaded with the same version it was saved with.
* `starlette==1.3.1` – starlette 1.8 breaks Streamlit's handling of chart images (HTTP 500).

---

## 10. Testing

```bash
python test_app.py
```

13 tests, all passing on Python 3.12 and 3.14:

| Area | What is checked |
|---|---|
| Task 1 | No missing values or duplicate IDs; peak rule; `Power_kW` formula |
| Task 2 | Saved model reproduces the original test-set predictions; unseen categories handled; peak flag derived at inference |
| Billing | Revenue estimate matches the Assessment 1 billing function in 192 combinations |
| Login | Unknown IDs refused; case-insensitive login; logout |
| Registration | New user appended to the CSV, can then log in; duplicates and invalid IDs refused; onboarding shown once |
| Data safety | Registered rows do not change Task 1 output |
| Pages | Dashboard filters and KPIs; three analytics charts; green / yellow / red prediction banners; clear errors when files are missing |

Registration tests run on temporary copies, so the real CSV is never modified.

---

## 11. Configuration reference

`.streamlit/config.toml`

| Setting | Value | Why |
|---|---|---|
| `theme.base` | `dark` | Native widgets match the dark design |
| `theme.primaryColor` | `#4cc9f0` | Electric-blue accent |
| `client.toolbarMode` | `viewer` | Hides developer menus from visitors |
| `browser.gatherUsageStats` | `false` | No telemetry |

Design tokens (colours, radii) are defined at the top of `ui.py` in the `:root` CSS block.

---

## 12. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Cannot load the saved model … scikit-learn X is installed" | Wrong package versions. Run `pip install -r requirements.txt`; on Streamlit Cloud choose Python 3.12. |
| Charts on Analytics show as broken images | starlette 1.8 is installed. Reinstall from `requirements.txt` (pins 1.3.1). |
| Background photos missing | The photos load from Unsplash's CDN; check the internet connection or firewall. |
| Page looks unstyled after an update | Hard-refresh the browser (`Ctrl + F5`). |
| A newly registered user disappeared on Streamlit Cloud | Cloud storage resets when the app restarts or redeploys; see Limitations. |
| `streamlit` not found | Activate the virtual environment first (`.venv\Scripts\activate`). |

---

## 13. Limitations and future work

* **Login checks the user ID only.** There is nowhere in the dataset to store a password, so anyone who knows an ID can sign in. Suitable for a course demonstration, not for real accounts.
* **Registrations on Streamlit Cloud are temporary.** The cloud file system resets on restart, so new rows in `ev_campus_dataset.csv` are lost; a database (e.g. SQLite on persistent storage, Supabase or Google Sheets) would fix this.
* **Revenue is an estimate** based on Assessment 1 rules, not real invoices.
* **The model classifies finished sessions.** It uses duration, energy and temperature that are only known after charging, so it is not an early-warning system.
* **Normal and Grid_Surge sessions in peak hours cannot be separated** with the available features. Recording ambient temperature and real-time grid load would allow a better model.

---

## 14. Credits

* Background photos (Unsplash License):
  * Sign-in page – *Illuminated modern EV charging station* by **Eva Kristensen** – https://unsplash.com/photos/aBalcTjW32Q
  * Portal – *An electric vehicle charging station is illuminated* by **Ratio EV Charging** – https://unsplash.com/photos/ngatBVIgJJk
* Open-source libraries: Streamlit, pandas, NumPy, scikit-learn, Matplotlib, Seaborn, joblib.
* Dataset and assessment brief: Taylor's University, ITS72604 Principles of Programming.
