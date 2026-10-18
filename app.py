"""Assessment 2 Task 3/4: Streamlit portal (local or Streamlit Community Cloud).
Run locally: streamlit run app.py"""
from pathlib import Path
import io
import logging
import threading

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from auth import (USER_TYPES, is_registered, mark_onboarded, needs_onboarding,
                  normalise_id, register, suggest_id)
from ev_core import validate_data, estimated_bills, load_artifacts, predict
from ui import (CHART_STYLE, PALETTE, apply_style, context, footer, hero, landing_features,
                landing_intro, landing_nav, logo, overview)

ROOT = Path(__file__).resolve().parent
# The raw dataset doubles as the user list: Session_ID is the login ID.
USERS_CSV = ROOT / 'ev_campus_dataset.csv'
PAGES = ['Executive KPI Dashboard', 'Visual Analytics Studio', 'Live Machine Learning Inference']
st.set_page_config(page_title='Campus EV | Operations', page_icon='⚡', layout='wide')


@st.cache_data(show_spinner=False)
def read_data(content):
    return validate_data(pd.read_csv(io.BytesIO(content), encoding='utf-8-sig'))


@st.cache_resource(show_spinner=False)
def read_model(model_stamp, metadata_stamp):
    # File signatures invalidate the cached resource when artifacts are replaced.
    return load_artifacts(ROOT / 'ev_model.pkl', ROOT / 'model_metadata.json')


@st.cache_resource
def plot_lock():
    # Matplotlib state must not be mutated concurrently across user sessions.
    return threading.RLock()


def fail(message, exc):
    logging.exception(message)
    st.error(f'{message}: {exc}')


def filtered_data(df):
    with st.sidebar:
        st.subheader('Session filters')
        chargers = st.multiselect('Charger type', sorted(df.Charger_Type.unique()),
                                 default=sorted(df.Charger_Type.unique()), key='filter_charger')
        users = st.multiselect('User type', sorted(df.User_Type.unique()),
                              default=sorted(df.User_Type.unique()), key='filter_user')
        labels = st.multiselect('Observed status', sorted(df.Grid_Status_Label.unique()),
                               default=sorted(df.Grid_Status_Label.unique()), key='filter_status')
        period = st.selectbox('Tariff period', ['All', 'Peak', 'Non-peak'], key='filter_period')
        hours = st.slider('Start hour range', 0, 23, (0, 23), key='filter_hours')
        search = st.text_input('Find session ID', key='filter_search').strip()
        st.button('Reset filters', on_click=reset_filters)
    mask = (df.Charger_Type.isin(chargers) & df.User_Type.isin(users) &
            df.Grid_Status_Label.isin(labels) & df.Start_Hour.between(*hours))
    if period != 'All':
        mask &= df.Period.eq(period)
    if search:
        mask &= df.Session_ID.str.contains(search, case=False, regex=False)
    return df.loc[mask].copy()


def reset_filters():
    for key in list(st.session_state):
        if key.startswith('filter_'):
            del st.session_state[key]


def billing_note():
    st.caption('ESTIMATED revenue · RM · Peak sessions start between 12:00 and 17:00 '
               '(12 ≤ Start_Hour ≤ 17, following Task 1). Whole session fees are attributed '
               'to the start-period flag.')
    with st.expander('Revenue calculation and assumptions'):
        st.markdown('''The CSV has no prices or payment records. Fees are estimates using the
recovered Assessment 1 billing prototype, with the Task 1 peak window.

| Billable hour tier | AC (RM/hour) | DC (RM/hour) |
|---|---:|---:|
| First 2 hours | 4 | 10 |
| Hours 3–4 | 6 | 15 |
| Hours 5–6 | 8 | 20 |
| Above 6 hours | 12 | 30 |

Duration is rounded **up** to a whole hour. If billable hours exceed 6, gross fees
are capped at RM80 (AC) / RM150 (DC). Staff receive 50% off base fees; students
receive 25% off AC base fees. Peak surcharge defaults to RM5/session.
Idle surcharge is RM15 when Overstay_Mins > 0, an explicit proxy for the prototype's
idle flag. First-time waiver, Eco-Pass and lost-card flags are unavailable and
assumed false. These assumptions can differ from actual invoices.

**Peak revenue** = sum of estimated whole-session fees for Peak_Hour_Flag = 1,
including base fees, peak surcharge and estimated idle fees. It is not only the
peak surcharge and is not a prorated fee for minutes inside the peak window.''')


def dashboard(df, total):
    hero('01', PAGES[0], 'A clear view of campus charging. Track energy, understand demand and explore every session.',
         ['Historical operations', 'Revenue marked estimated', 'Filters apply to every KPI'])
    cols = st.columns(4)
    cols[0].metric('Total energy delivered', f'{df.Energy_kWh.sum():,.2f} kWh')
    cols[1].metric('Average session duration', f'{df.Duration_Mins.mean():,.1f} min' if len(df) else '—')
    peak = df.loc[df.Peak_Hour_Flag.eq(1)]
    cols[2].metric('Peak revenue · estimated', f'RM {peak.Estimated_Revenue_RM.sum():,.2f}')
    cols[3].metric('Sessions in view', f'{len(df):,}', help=f'{total:,} sessions in the loaded dataset')
    overview(df)
    billing_note()
    st.markdown('<div class="ev-section">Explore the underlying data</div>', unsafe_allow_html=True)
    st.subheader('Session explorer')
    st.caption('All metrics and the table follow the sidebar filters. Column headers support sorting.')
    if df.empty:
        st.info('No sessions match these filters. Adjust or reset the sidebar filters.')
        return
    columns = st.multiselect('Table columns', df.columns.tolist(),
                            default=['Session_ID', 'Charger_Type', 'User_Type', 'Energy_kWh',
                                     'Duration_Mins', 'Battery_Temp_C', 'Period',
                                     'Grid_Status_Label', 'Estimated_Revenue_RM'])
    if columns:
        st.dataframe(df[columns], hide_index=True, width='stretch')
    else:
        st.info('Choose at least one table column.')
    st.download_button('Download filtered sessions (CSV)', df.to_csv(index=False).encode('utf-8-sig'),
                       'filtered_ev_sessions.csv', 'text/csv')


def show_plot(fig, name):
    try:
        st.pyplot(fig, width='stretch')
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=160, bbox_inches='tight')
        st.download_button('Download chart', buffer.getvalue(), f'{name}.png', 'image/png', key=name)
    finally:
        plt.close(fig)


def analytics(df):
    hero('02', PAGES[1], 'Turn charging records into a clearer picture of demand, temperature and charger use.',
         ['Battery temperature', 'Shared session filters', 'Export every chart'])
    if df.empty:
        st.info('No sessions match these filters. Adjust or reset the sidebar filters.')
        return
    st.info('The supplied CSV has no ambient-temperature column, so this scatter plot uses '
            'the measured battery temperature (Battery_Temp_C). No battery readings were missing; '
            'missing duration and energy values were median-imputed in Task 1.')
    with st.container(border=True):
        controls = st.columns([1, 1.3, 1], gap='medium')
        with controls[0]:
            hue = st.selectbox('Colour scatter points by', ['Charger_Type', 'Grid_Status_Label', 'User_Type'])
        with controls[1]:
            metric = st.selectbox('Peak vs Non-peak comparison', ['Total energy (kWh)', 'Average energy (kWh)', 'Session count'])
        with controls[2]:
            size = st.slider('Scatter point size', 15, 100, 40)
    # Controls rerun the embedded Matplotlib/Seaborn figures over the filtered data.
    # Status colours keep their meaning (Normal / Overheated / Grid_Surge).
    status_colours = {'Normal': PALETTE[0], 'Overheated': PALETTE[2], 'Grid_Surge': PALETTE[3]}
    levels = sorted(df[hue].unique())
    palette = ([status_colours[x] for x in levels] if hue == 'Grid_Status_Label'
               else [PALETTE[0], PALETTE[1], PALETTE[2]][:len(levels)])
    with plot_lock(), sns.axes_style('darkgrid'), plt.rc_context(CHART_STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5), layout='constrained')
        sns.scatterplot(data=df, x='Battery_Temp_C', y='Energy_kWh', hue=hue, hue_order=levels,
                        s=size, alpha=0.75, ax=ax, palette=palette, edgecolor='none')
        ax.set(title='Energy vs Battery Temperature', xlabel='Battery temperature (°C)', ylabel='Energy delivered (kWh)')
        show_plot(fig, 'energy_vs_battery_temperature')
        left, right = st.columns(2)
        with left:
            group = df.groupby('Period').Energy_kWh
            values = group.sum() if metric.startswith('Total') else group.mean() if metric.startswith('Average') else group.size()
            values = values.reindex(['Non-peak', 'Peak'])
            fig, ax = plt.subplots(figsize=(6, 4), layout='constrained')
            ax.bar(values.index, values.fillna(0), color=[PALETTE[1], PALETTE[0]], width=0.6)
            ax.set(title='Peak vs Non-peak', ylabel=metric)
            for i, value in enumerate(values):
                text = 'No sessions' if pd.isna(value) else f'{value:,.1f}'
                ax.annotate(text, (i, 0 if pd.isna(value) else value), xytext=(0, 5), textcoords='offset points', ha='center')
            ax.margins(y=0.18)
            show_plot(fig, 'peak_vs_non_peak')
        with right:
            counts = df.Charger_Type.value_counts().sort_index()
            fig, ax = plt.subplots(figsize=(6, 4), layout='constrained')
            ax.bar(counts.index, counts.values, color=[PALETTE[0], PALETTE[1]][:len(counts)], width=0.6)
            ax.set(title='Charger Type Distribution', ylabel='Session count', xlabel='Charger type')
            for i, value in enumerate(counts):
                ax.annotate(f'{value:,} ({value / len(df):.1%})', (i, value), xytext=(0, 5), textcoords='offset points', ha='center')
            ax.margins(y=0.18)
            show_plot(fig, 'charger_distribution')
    st.caption(f'Charts use {len(df):,} filtered sessions. Bars show descriptive aggregates; no causal claim is made.')


def model_performance(meta):
    """Task 2 evidence shown inside the app: comparison, confusion matrix, insight."""
    st.markdown('<div class="ev-section">Model performance (Task 2)</div>', unsafe_allow_html=True)
    table = pd.DataFrame(meta['test_metrics'])
    cols = ['model', 'cv_f1_macro', 'accuracy', 'precision_macro', 'recall_macro', 'f1_macro']
    st.dataframe(table[cols], hide_index=True, width='stretch',
                 column_config={c: st.column_config.NumberColumn(format='%.3f') for c in cols[1:]})
    ceiling = meta['ceiling_analysis']
    st.caption(f"The saved {meta['selected_model']} was chosen by cross-validated macro F1, "
               'before the test set was used.')
    tab1, tab2, tab3 = st.tabs(['Confusion matrices', 'Feature importance', 'Why not 100%?'])
    reports = ROOT / 'reports'
    with tab1:
        if (reports / 'confusion_matrices_all.png').exists():
            st.image(str(reports / 'confusion_matrices_all.png'))
    with tab2:
        if (reports / 'feature_importance.png').exists():
            st.image(str(reports / 'feature_importance.png'))
    with tab3:
        st.markdown(
            f"- Overheated matches the rule **Battery_Temp_C > 43 °C** in "
            f"{ceiling['overheated_rule_matches']:.0%} of sessions, and the model learned it.\n"
            f"- Grid_Surge only happens in peak hours (12–17): "
            f"{ceiling['grid_surge_outside_peak']} surges occurred outside that window.\n"
            f"- Inside the peak window, Normal and Grid_Surge sessions have the same measurements "
            f"({ceiling['peak_window_normal_vs_surge'].get('Normal', 0)} Normal vs "
            f"{ceiling['peak_window_normal_vs_surge'].get('Grid_Surge', 0)} Grid_Surge), "
            "so no feature can tell them apart.\n"
            f"- So the **best accuracy any model could reach is about {ceiling['max_accuracy_possible']:.1%}**, "
            f"and if every peak session is flagged, at most {ceiling['surge_precision_if_all_peak_flagged']:.0%} "
            'of the flags are real surges. The model chooses to catch almost all surges and '
            'accept some false alarms, which is the safer choice for grid protection.')


def inference():
    hero('03', PAGES[2], 'From session measurements to a grid-status prediction. Adjust the inputs and see the result immediately.',
         ['Saved preprocessing Pipeline', 'Peak flag derived from start hour', 'Colour-coded alerts'])
    try:
        paths = [ROOT / 'ev_model.pkl', ROOT / 'model_metadata.json']
        signatures = [(p.stat().st_mtime_ns, p.stat().st_size) for p in paths]
        model, meta, categories = read_model(*signatures)
    except Exception as exc:
        fail('Cannot load the saved model. Restore the bundled model/metadata and install requirements.txt', exc)
        return
    imputer = model.named_steps['preprocess'].named_transformers_['numeric'].named_steps['impute']
    medians = dict(zip(model.named_steps['preprocess'].transformers_[0][2], imputer.statistics_))
    with st.sidebar:
        st.subheader('Live session inputs')
        row = {
            'Charger_Type': st.selectbox('Charger type', categories['Charger_Type'], key='input_charger'),
            'User_Type': st.selectbox('User type', categories['User_Type'], key='input_user'),
            'Start_Hour': st.slider('Start hour', 0, 23, int(medians['Start_Hour']), key='input_hour'),
            'Duration_Mins': st.number_input('Duration (minutes)', min_value=0.1, value=float(medians['Duration_Mins']), step=1.0, key='input_duration'),
            'Energy_kWh': st.number_input('Energy delivered (kWh)', min_value=0.0, value=float(medians['Energy_kWh']), step=0.5, key='input_energy'),
            'Overstay_Mins': st.number_input('Overstay (minutes)', min_value=0.0, value=float(medians['Overstay_Mins']), step=1.0, key='input_overstay'),
            'Battery_Temp_C': st.number_input('Battery temperature (°C)', value=float(medians['Battery_Temp_C']), step=0.5, key='input_temperature'),
        }
        is_peak = 12 <= row['Start_Hour'] <= 17
        st.caption(f"Tariff period (auto-derived): **{'Peak' if is_peak else 'Non-peak'}**")
    try:
        label, probabilities, inputs = predict(model, row)
        st.markdown('<div class="ev-section">Prediction result</div>', unsafe_allow_html=True)
        if label == 'Normal':
            st.success('Normal — model predicts normal grid status for these measurements.')
        elif label == 'Overheated':
            st.warning('Overheated — review the battery temperature and charging equipment.')
        else:
            st.error('Grid_Surge — review grid load and charger operation.')
        st.subheader('Model class probabilities')
        st.dataframe(pd.DataFrame({'Status': list(probabilities), 'Probability': list(probabilities.values())}),
                     hide_index=True, width='stretch',
                     column_config={'Probability': st.column_config.ProgressColumn('Probability', min_value=0, max_value=1, format='%.3f')})
        st.caption('Probabilities are uncalibrated classifier outputs, not measured risk or certainty.')
        st.subheader('Inputs passed to the saved Pipeline')
        st.dataframe(inputs, hide_index=True, width='stretch')
        result = inputs.assign(Predicted_Grid_Status_Label=label, **{f'Probability_{k}': v for k, v in probabilities.items()})
        st.download_button('Download prediction (CSV)', result.to_csv(index=False), 'ev_prediction.csv', 'text/csv')
    except Exception as exc:
        fail('Prediction failed. Check session inputs and the saved model', exc)
        return
    st.info('Session-level classification: duration, delivered energy, overstay and battery temperature '
            'must already be available. This model has not been validated as a prospective early-warning system.')
    model_performance(meta)
    with st.expander('Model provenance and input contract'):
        st.write(f"Model: {meta['selected_model']} · training rows: {meta['train_rows']:,} · "
                 'selected by five-fold training CV macro F1.')
        st.write(f"Held-out accuracy: {meta['best_test_accuracy']:.2%} · macro F1: {meta['best_test_f1_macro']:.3f}")
        st.write('Inputs are raw measurements plus Peak_Hour_Flag, which is derived from the start hour '
                 '(12–17). The saved training medians, category modes and one-hot encoder run inside '
                 'ev_model.pkl.')
        st.json({'feature_order': list(model.feature_names_in_), 'fitted_categories': categories,
                 'training_numeric_medians': medians})


def do_login():
    user_id = normalise_id(st.session_state.get('login_id'))
    st.session_state.pop('unregistered_id', None)
    if not user_id:
        st.session_state.auth_error = 'Please enter your user ID.'
    elif is_registered(USERS_CSV, user_id):
        st.session_state.user = user_id
        # First sign-in of a newly registered user opens the onboarding guide.
        if needs_onboarding(USERS_CSV, user_id):
            st.session_state.show_guide = True
            st.session_state.guide_step = 0
    else:
        st.session_state.auth_error = f'{user_id} is not registered. Please register first.'
        st.session_state.unregistered_id = user_id


def go_to_register():
    st.session_state.auth_mode = 'Register'
    user_id = st.session_state.pop('unregistered_id', None)
    if user_id:
        st.session_state.register_id = user_id


def do_register():
    try:
        user_id = register(USERS_CSV, st.session_state.get('register_id'),
                           st.session_state.get('register_type'))
    except ValueError as exc:
        st.session_state.auth_error = str(exc)
        return
    # Send the new user back to the login form with the ID filled in.
    st.session_state.auth_mode = 'Log in'
    st.session_state.login_id = user_id
    st.session_state.pop('register_id', None)
    st.session_state.auth_notice = (f'{user_id} is registered and has been added to '
                                    'ev_campus_dataset.csv. You can now log in.')


def logout():
    for key in list(st.session_state):
        if key in ('user', 'show_guide', 'guide_step') or key.startswith(('filter_', 'input_')):
            del st.session_state[key]


def open_guide():
    st.session_state.show_guide = True
    st.session_state.guide_step = 0


GUIDE = [
    ('⚡', 'Welcome to Campus EV, {user}',
     '<p>This portal turns 1,200 recorded campus charging sessions into clear answers: how much energy '
     'is delivered, when demand peaks, and which sessions put the grid at risk.</p>'
     '<p>This short tour shows you around. It takes under a minute.</p>'),
    ('🧭', 'Move between three workspaces',
     '<p>Use the menu at the top of the page:</p><ul>'
     '<li><b>Dashboard</b>: headline KPIs and a searchable session table</li>'
     '<li><b>Analytics</b>: charts of energy, temperature and charger mix</li>'
     '<li><b>Live Prediction</b>: the machine learning model, live</li></ul>'),
    ('🎛️', 'Filter from the side panel',
     '<p>The panel on the left holds the controls for the current workspace. On Dashboard and Analytics, '
     'filter by charger type, user type, status, tariff period or start hour; every number and chart updates '
     'together. Use <b>Reset filters</b> to start over.</p>'),
    ('🚦', 'Read the prediction alerts',
     '<p>On Live Prediction, enter a session\'s measurements and the model answers immediately:</p><ul>'
     '<li><b style="color:#34d399">Green</b>: Normal</li>'
     '<li><b style="color:#f5b041">Yellow</b>: Overheated; check battery temperature and equipment</li>'
     '<li><b style="color:#f0607a">Red</b>: Grid_Surge; check grid load</li></ul>'),
    ('👤', 'Your account menu',
     '<p>The round button in the top-right corner shows who is signed in. Open it to replay this guide at '
     'any time or to log out.</p><p>You are all set. Enjoy exploring!</p>'),
]


def finish_guide():
    mark_onboarded(USERS_CSV, st.session_state.user)
    st.session_state.show_guide = False


def hide_guide():
    """Closing with the X hides the guide for now; it returns at the next sign-in."""
    st.session_state.show_guide = False


@st.dialog('Getting started', width='large', on_dismiss=hide_guide)
def onboarding_guide():
    step = st.session_state.get('guide_step', 0)
    icon, title, body = GUIDE[step]
    dots = ''.join(f'<span class="{"on" if i <= step else ""}"></span>' for i in range(len(GUIDE)))
    st.markdown(f'<div class="ev-guide"><div class="ev-guide-step">Step {step + 1} of {len(GUIDE)}</div>'
                f'<div class="ev-guide-icon">{icon}</div><h3>{title.format(user=st.session_state.user)}</h3>'
                f'{body}<div class="ev-dots">{dots}</div></div>', unsafe_allow_html=True)
    skip, _, back, nxt = st.columns([1, 2, 1, 1.3])
    if step < len(GUIDE) - 1 and skip.button('Skip tour', key='guide_skip'):
        finish_guide()
        st.rerun()
    if step > 0 and back.button('Back', key='guide_back', width='stretch'):
        st.session_state.guide_step = step - 1
        st.rerun(scope='fragment')
    last = step == len(GUIDE) - 1
    if nxt.button('Get started' if last else 'Next', key='guide_next', type='primary', width='stretch'):
        if last:
            finish_guide()
            st.rerun()
        st.session_state.guide_step = step + 1
        st.rerun(scope='fragment')


def portal_nav():
    """Fixed top navigation: logo, workspace menu and the account avatar."""
    short = {PAGES[0]: 'Dashboard', PAGES[1]: 'Analytics', PAGES[2]: 'Live Prediction'}
    with st.container(key='topnav'):
        left, mid, right = st.columns([2.2, 6, 1.6], vertical_alignment='center')
        left.markdown(logo(), unsafe_allow_html=True)
        with mid:
            page = st.radio('Workspace', PAGES, key='page', horizontal=True,
                            label_visibility='collapsed', format_func=short.get)
        with right:
            with st.popover('Account', icon=':material/person:'):
                st.markdown(f"Signed in as **{st.session_state.user}**")
                st.button('Show getting-started guide', on_click=open_guide, key='guide_open', width='stretch')
                st.button('Log out', on_click=logout, key='logout', width='stretch')
    return page


def login_page():
    landing_nav()
    try:
        suggestion = suggest_id(USERS_CSV)
    except Exception as exc:
        fail('Cannot load the user list in ev_campus_dataset.csv', exc)
        return
    intro, card = st.columns([1.35, 1], gap='large')
    with intro:
        landing_intro([('charging sessions', '1,200'), ('kWh delivered', '18.6k'),
                       ('grid states', '3'), ('model accuracy', '79.6%')])
    with card, st.container(key='authcard'):
        st.markdown('<div class="ev-auth-head" id="signin"><h3>Access the portal</h3>'
                    '<p>Sign in with your registered user ID, or create one.</p></div>', unsafe_allow_html=True)
        mode = st.radio('Account', ['Log in', 'Register'], key='auth_mode',
                        horizontal=True, label_visibility='collapsed')
        if 'auth_notice' in st.session_state:
            st.success(st.session_state.pop('auth_notice'))
        error = st.session_state.pop('auth_error', None)
        if mode == 'Log in':
            with st.form('login_form'):
                st.text_input('User ID', key='login_id', placeholder='e.g. SESS-1000')
                st.form_submit_button('Log in', type='primary', on_click=do_login)
            if error:
                st.error(error)
            if st.session_state.get('unregistered_id'):
                st.button('Register this ID', on_click=go_to_register)
        else:
            st.session_state.setdefault('register_id', suggestion)
            with st.form('register_form'):
                st.text_input('Choose a user ID', key='register_id',
                              help='3–20 characters: letters, digits, "-" or "_".')
                st.selectbox('User type', USER_TYPES, key='register_type')
                st.form_submit_button('Register', type='primary', on_click=do_register)
            if error:
                st.error(error)
            st.caption(f'Next free ID in the dataset style: {suggestion}')
    landing_features()


def main():
    if not st.session_state.get('user'):
        apply_style('login')
        login_page()
        footer()
        return
    apply_style('portal')
    page = portal_nav()
    if st.session_state.get('show_guide'):
        onboarding_guide()
    if page == PAGES[2]:
        # Inference remains usable even when the dashboard CSV is unavailable.
        inference()
        footer()
        return
    try:
        df = read_data((ROOT / 'cleaned_ev_dataset.csv').read_bytes())
    except Exception as exc:
        fail('Cannot load cleaned_ev_dataset.csv. Restore the bundled Task 1 data', exc)
        return
    with st.sidebar.expander('Estimated tariff scenario'):
        surcharge = st.number_input('Peak surcharge (RM/session)', min_value=0.0, value=5.0, step=0.5)
        st.caption('Default from recovered Assessment 1 prototype. Changing this value is a scenario estimate.')
    selected = filtered_data(estimated_bills(df, surcharge))
    context(len(selected), len(df))
    if page == PAGES[0]:
        dashboard(selected, len(df))
    else:
        analytics(selected)
    footer()


if __name__ == '__main__':
    main()
