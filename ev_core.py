"""Validated data, auditable estimated billing, and saved-pipeline inference."""
from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.pipeline import Pipeline

FEATURES = ['Charger_Type', 'User_Type', 'Start_Hour', 'Peak_Hour_Flag', 'Duration_Mins',
            'Energy_kWh', 'Overstay_Mins', 'Battery_Temp_C']
NUMERIC = FEATURES[2:]
# Same peak rule as Task 1 / Task 2: 12 <= Start_Hour <= 17.
PEAK_START, PEAK_END = 12, 17
LABELS = {'Normal', 'Overheated', 'Grid_Surge'}


def validate_data(frame):
    """Reject damaged cleaned data instead of silently changing KPI denominators."""
    required = FEATURES + ['Session_ID', 'Grid_Status_Label', 'Peak_Hour_Flag']
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing dataset columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError('The dataset is empty.')
    df = frame.copy()
    for col in ['Session_ID', 'Charger_Type', 'User_Type', 'Grid_Status_Label']:
        df[col] = df[col].astype('string').str.strip()
        if df[col].isna().any() or df[col].eq('').any():
            raise ValueError(f'{col} contains missing values. Run Task 1 cleaning first.')
    if df.Session_ID.duplicated().any():
        raise ValueError('Duplicate Session_ID values found. Run Task 1 cleaning first.')
    for col in NUMERIC + ['Peak_Hour_Flag']:
        df[col] = pd.to_numeric(df[col], errors='raise')
        if not np.isfinite(df[col].to_numpy(dtype=float)).all():
            raise ValueError(f'{col} contains missing or non-finite values.')
    if (df.Duration_Mins <= 0).any() or (df[['Energy_kWh', 'Overstay_Mins']] < 0).any().any():
        raise ValueError('Duration must be positive; energy and overstay cannot be negative.')
    if (~df.Start_Hour.between(0, 23) | df.Start_Hour.mod(1).ne(0)).any():
        raise ValueError('Start_Hour must be an integer from 0 to 23.')
    for col, allowed in [('Charger_Type', {'AC', 'DC'}),
                         ('User_Type', {'Staff', 'Student', 'Visitor'}),
                         ('Grid_Status_Label', LABELS), ('Peak_Hour_Flag', {0, 1})]:
        if not set(df[col]).issubset(allowed):
            raise ValueError(f'Unsupported values in {col}: {set(df[col]) - allowed}')
    df['Period'] = df.Peak_Hour_Flag.map({0: 'Non-peak', 1: 'Peak'})
    return df


def estimated_bills(frame, peak_surcharge=5.0):
    """Assessment 1 prototype rules; unavailable waiver/pass/card flags are false."""
    if not np.isfinite(peak_surcharge) or peak_surcharge < 0:
        raise ValueError('Peak surcharge must be a finite, nonnegative amount.')
    df = frame.copy()
    hours = np.ceil(df.Duration_Mins / 60)
    gross = np.zeros(len(df))
    previous = 0
    for upper, ac, dc in [(2, 4, 10), (4, 6, 15), (6, 8, 20), (np.inf, 12, 30)]:
        tier_hours = np.minimum(np.maximum(hours - previous, 0), upper - previous)
        gross += tier_hours * np.where(df.Charger_Type.eq('AC'), ac, dc)
        previous = upper
    caps = np.where(df.Charger_Type.eq('AC'), 80, 150)
    gross = np.where(hours > 6, np.minimum(gross, caps), gross)
    discount = np.select([df.User_Type.eq('Staff'),
                          df.User_Type.eq('Student') & df.Charger_Type.eq('AC')],
                         [0.5, 0.25], default=0.0)
    df['Estimated_Base_RM'] = gross * (1 - discount)
    df['Estimated_Peak_Surcharge_RM'] = df.Peak_Hour_Flag * peak_surcharge
    df['Estimated_Idle_RM'] = np.where(df.Overstay_Mins > 0, 15.0, 0.0)
    df['Estimated_Revenue_RM'] = (df.Estimated_Base_RM +
                                df.Estimated_Peak_Surcharge_RM + df.Estimated_Idle_RM)
    return df


def load_artifacts(model_path, metadata_path):
    """Only load the bundled trusted artifact; never accept uploaded pickles."""
    metadata = json.loads(Path(metadata_path).read_text(encoding='utf-8'))
    # A patch-level difference (e.g. 1.9.0 vs 1.9.1) is safe; a different
    # major/minor release can change the pickle format, so that still fails.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', InconsistentVersionWarning)
        model = joblib.load(model_path)
    for w in caught:
        if issubclass(w.category, InconsistentVersionWarning):
            saved, current = w.message.original_sklearn_version, w.message.current_sklearn_version
            if saved.split('.')[:2] != current.split('.')[:2]:
                raise ValueError(f'ev_model.pkl was saved with scikit-learn {saved} but {current} '
                                 'is installed. Run: pip install -r requirements.txt')
    if not isinstance(model, Pipeline) or set(model.named_steps) != {'preprocess', 'classifier'}:
        raise ValueError('Expected the Task 2 preprocess/classifier Pipeline.')
    if list(model.feature_names_in_) != FEATURES or metadata.get('features') != FEATURES:
        raise ValueError('Saved model feature schema does not match the expected input fields.')
    if set(model.classes_) != LABELS:
        raise ValueError('The saved classifier must contain all three expected status labels.')
    pre = model.named_steps['preprocess']
    if list(pre.transformers_[0][2]) != NUMERIC or list(pre.transformers_[1][2]) != FEATURES[:2]:
        raise ValueError('Saved preprocessing column mapping is inconsistent.')
    categories = pre.named_transformers_['categorical'].named_steps['onehot'].categories_
    return model, metadata, dict(zip(FEATURES[:2], [list(x) for x in categories]))


def prepare_inputs(frame):
    """Mirror Task 2 fixed validation; let the saved imputers handle missing cells."""
    raw_inputs = [c for c in FEATURES if c != 'Peak_Hour_Flag']
    missing = set(raw_inputs) - set(frame.columns)
    if missing:
        raise ValueError(f'Missing inference columns: {sorted(missing)}')
    x = frame[raw_inputs].copy()
    for col in [c for c in NUMERIC if c != 'Peak_Hour_Flag']:
        x[col] = pd.to_numeric(x[col], errors='raise').replace([np.inf, -np.inf], np.nan)
        if col == 'Duration_Mins':
            x.loc[x[col] <= 0, col] = np.nan
        elif col in {'Energy_kWh', 'Overstay_Mins'}:
            x.loc[x[col] < 0, col] = np.nan
        elif col == 'Start_Hour':
            x.loc[(x[col] < 0) | (x[col] >= 24) | (x[col] % 1 != 0), col] = np.nan
    # The peak flag is always derived from Start_Hour so the user cannot
    # enter an inconsistent combination.
    x['Peak_Hour_Flag'] = x['Start_Hour'].between(PEAK_START, PEAK_END).astype(float).where(x['Start_Hour'].notna())
    x = x[FEATURES]
    for col in FEATURES[:2]:
        x[col] = x[col].astype('string').str.strip().replace('', pd.NA)
        x[col] = x[col].astype(object).where(x[col].notna(), np.nan)
    return x


def predict(model, row):
    x = prepare_inputs(pd.DataFrame([row]))
    label = str(model.predict(x)[0])
    probabilities = dict(zip(model.classes_, model.predict_proba(x)[0].tolist()))
    if label not in LABELS:
        raise ValueError(f'Unexpected prediction: {label}')
    return label, probabilities, x
