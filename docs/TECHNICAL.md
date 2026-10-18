# Technical reference

Architecture, module reference, data flow and the reasoning behind the main
design decisions.

---

## 1. Architecture

```
                 ┌─────────────────────────┐
 raw CSV ───────►│ data_pipeline.py (Task1)│──► cleaned_ev_dataset.csv, summaries, cleaning_report.json
   │             └─────────────────────────┘                │
   │             ┌─────────────────────────┐                │
   ├────────────►│ train_ev_model.py (T2)  │──► ev_model.pkl, model_metadata.json, reports/
   │             └─────────────────────────┘                │                │
   │                                                        ▼                ▼
   │             ┌──────────────────────────────────────────────────────────────┐
   └────────────►│ app.py  (Streamlit, Task 3)                                  │
   user list     │   ├─ auth.py     login, registration, onboarding state       │
   + new users   │   ├─ ev_core.py  validation, revenue estimate, inference     │
                 │   └─ ui.py       theme, navigation, starfield animation      │
                 └──────────────────────────────────────────────────────────────┘
```

* The **raw CSV** feeds both offline scripts and doubles as the **user list** for the portal.
* Task 2 deliberately trains from the **raw** file, not the Task 1 output, so the
  median imputation is learned from training rows only (no test-set leakage).
* The portal never retrains; it loads the saved pipeline and the cleaned data.

---

## 2. Module reference

### `data_pipeline.py` (Task 1)

| Function | Purpose |
|---|---|
| `load_data(path)` | Read CSV (`utf-8-sig`), check required columns, reject empty files |
| `explore(df)` | Print shape, `info()`, `describe()`, missing values, target distribution |
| `clean(df, report)` | Trim text, drop invalid rows, de-duplicate, range-check, median-impute, restore integer types; records every action in `report` |
| `engineer_features(df, report)` | `Peak_Hour_Flag`, `Power_kW`, `Energy_Efficiency_Group` (per-charger tertiles) |
| `summarise(df)` | Four group-by tables using named aggregation |
| `main()` | CLI (`--input`, `--output-dir`), quality-gate assertions, write outputs |

Constants: `NUMERIC_COLS`, `CATEGORICAL_COLS`, `VALID_RANGES`, `PEAK_START = 12`, `PEAK_END = 17`.

### `train_ev_model.py` (Task 2)

| Function | Purpose |
|---|---|
| `add_peak_flag(frame)` | Same deterministic peak rule as Task 1 (uses no statistics → no leakage) |
| `build_pipeline(classifier, scale=False)` | `ColumnTransformer` (median imputer [+ scaler] for numeric; most-frequent imputer + one-hot for categorical) + classifier |
| `metric_row(name, y_true, y_pred)` | Accuracy and macro/weighted precision, recall, F1 |
| `plot_confusion(ax, …)` | Seaborn heatmap confusion matrix |
| `main()` | The 7 steps: load → split → grid search with 5-fold CV → evaluate → figures → ceiling analysis → save & verify |

Hyper-parameter grids:

| Model | Grid |
|---|---|
| Decision Tree | `max_depth` 3/4/6/None · `min_samples_leaf` 1/5 · `class_weight` None/balanced |
| Random Forest (300 trees) | `max_depth` 4/8/None · `min_samples_leaf` 1/5 · `class_weight` None/balanced |
| KNN | `n_neighbors` 3/5/9/15 · `weights` uniform/distance |

### `ev_core.py`

| Function | Purpose |
|---|---|
| `validate_data(frame)` | Strict schema and value checks on the cleaned data; adds a `Period` column |
| `estimated_bills(frame, peak_surcharge=5.0)` | Vectorised Assessment 1 billing rules → `Estimated_Revenue_RM` |
| `load_artifacts(model_path, metadata_path)` | Load the pickle with version checks (patch differences allowed, minor differences refused), verify pipeline structure, features and classes |
| `prepare_inputs(frame)` | Turn raw inputs into the model's feature frame; invalid numbers become NaN for the saved imputer; derives `Peak_Hour_Flag` |
| `predict(model, row)` | Returns `(label, probabilities, inputs)` |

### `auth.py`

| Function | Purpose |
|---|---|
| `normalise_id(user_id)` | Strip spaces, upper-case |
| `load_user_ids(path)` | Set of `Session_ID` values, read fresh on every call |
| `is_registered(path, user_id)` | Membership check |
| `validate_new_id(user_id)` | Regex `^[A-Z0-9][A-Z0-9_-]{2,19}$` – also guarantees the ID cannot break the CSV |
| `suggest_id(path)` | Next free `SESS-####` |
| `register(path, user_id, user_type)` | Validate, re-check inside a lock, append one CSV row (`csv.DictWriter`) |
| `needs_onboarding(path, user_id)` | True for portal-registered users (blank label) not yet in `onboarded_users.json` |
| `mark_onboarded(path, user_id)` | Record that the guide was finished or skipped |

A module-level `threading.Lock` serialises writes, because Streamlit serves
every visitor from the same process.

### `ui.py`

| Item | Purpose |
|---|---|
| `STYLE` | The complete CSS design system (tokens in `:root`) |
| `STARFIELD` | Canvas animation script injected with `st.html(..., unsafe_allow_javascript=True)` |
| `apply_style(page)` | `'login'` or `'portal'`: injects CSS with the matching background photo; starts or removes the starfield |
| `logo()`, `landing_nav()`, `landing_intro()`, `landing_features()` | Sign-in page building blocks |
| `hero()`, `context()`, `overview()`, `footer()` | Portal page building blocks |
| `PALETTE`, `CHART_STYLE` | Shared chart colours and Matplotlib `rcParams` |

### `app.py`

| Function | Purpose |
|---|---|
| `main()` | Router: sign-in page if no user, otherwise navigation + selected workspace |
| `login_page()` | Landing layout and the Log in / Register card |
| `do_login`, `go_to_register`, `do_register`, `logout` | Widget callbacks (run before the next render, so they can change widget state) |
| `portal_nav()` | Fixed top bar: logo, workspace radio styled as a menu, account popover |
| `onboarding_guide()` | `@st.dialog` five-step tour; steps rerun only the dialog (`st.rerun(scope='fragment')`) |
| `dashboard`, `analytics`, `inference`, `model_performance` | The three workspaces |
| `filtered_data()` | Sidebar filters applied to the data |
| `read_data`, `read_model` | Cached loaders (`st.cache_data`, `st.cache_resource`) |

---

## 3. Design decisions

| Decision | Reason |
|---|---|
| Select models by **macro F1** | 75 % of sessions are Normal; accuracy rewards ignoring faults |
| Preprocessing inside the `Pipeline` | No leakage; identical transformations at inference time |
| Choose the model on **CV score before testing** | The test score stays an unbiased estimate |
| Per-charger efficiency tertiles | AC and DC power scales differ about five-fold |
| Peak window 12–17 inclusive | Grid_Surge sessions start at 17:00 in the data |
| `Session_ID` as user ID | The dataset has no other identifier; the brief requires using the table |
| Registered rows have blank labels | Task 1 and Task 2 already drop unlabelled rows, so the analysis is unchanged |
| Pinned `requirements.txt` | Pickled scikit-learn models must load with the version that saved them |
| `starlette==1.3.1` | starlette 1.8 + Streamlit 1.58 return HTTP 500 for chart images |
| Photos hot-linked from Unsplash CDN | Allowed by the Unsplash License/guidelines; keeps the repository small |
| Starfield removed after sign-in | Keeps the portal pages calm and saves CPU |
| `prefers-reduced-motion` respected | Animations stop for users who disable motion in their OS |

---

## 4. Security notes

* **ID-only login** – there is no password field because the dataset has no place
  to store one. Do not reuse this pattern for real accounts.
* **Input validation** – registration IDs are restricted by regex, so they cannot
  inject CSV delimiters or quotes. All HTML built from data is escaped with `html.escape`.
* **Model loading** – only the bundled `ev_model.pkl` is loaded; the app never
  unpickles user-supplied files.
* **Concurrency** – writes to the CSV and onboarding file happen under a lock, and
  duplicate IDs are re-checked inside the lock.

---

## 5. Re-generating artefacts

```bash
python data_pipeline.py     # ~1 s
python train_ev_model.py    # ~20 s (grid search, 5-fold CV, 300-tree forest)
python test_app.py          # ~10 s
```

Results are deterministic (`random_state=42`): the Decision Tree reaches
79.6 % test accuracy and 0.806 macro F1 on every run.
