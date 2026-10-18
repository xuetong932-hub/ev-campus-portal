"""Visual system for the Campus EV portal: night-sky theme, top navigation,
glass cards and the interactive starfield used on the sign-in page.

Background photos are free Unsplash images loaded from Unsplash's CDN:
  * Login:  "Illuminated modern EV charging station" by Eva Kristensen
            https://unsplash.com/photos/aBalcTjW32Q
  * Portal: "An electric vehicle charging station is illuminated" by Ratio EV Charging
            https://unsplash.com/photos/ngatBVIgJJk
"""
from html import escape
import streamlit as st

LOGIN_PHOTO = 'https://images.unsplash.com/photo-1783413154353-50531d4244e5?auto=format&fit=crop&w=2400&q=80'
PORTAL_PHOTO = 'https://images.unsplash.com/photo-1751553822264-47ef77e3495f?auto=format&fit=crop&w=2400&q=80'
CREDITS = ('Photos: <a href="https://unsplash.com/photos/aBalcTjW32Q" target="_blank" rel="noopener">Eva Kristensen</a> · '
           '<a href="https://unsplash.com/photos/ngatBVIgJJk" target="_blank" rel="noopener">Ratio EV Charging</a> on Unsplash')

# Chart colours shared with app.py (accent, secondary, warning, critical).
PALETTE = ['#4cc9f0', '#3f7cf5', '#f5b041', '#f0607a']
CHART_STYLE = {
    'figure.facecolor': '#0c1322', 'axes.facecolor': '#0c1322', 'savefig.facecolor': '#0c1322',
    'axes.edgecolor': '#24324a', 'grid.color': '#1a2538', 'axes.labelcolor': '#aab8cc',
    'text.color': '#e8eef7', 'xtick.color': '#8fa1b8', 'ytick.color': '#8fa1b8',
    'legend.facecolor': '#0c1322', 'legend.edgecolor': '#24324a',
    'axes.titleweight': 'bold', 'axes.titlepad': 16, 'axes.titlesize': 13,
    'axes.spines.top': False, 'axes.spines.right': False,
}

STYLE = '''<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {--bg:#05080f;--surface:rgba(12,19,34,.72);--surface-2:rgba(18,28,48,.78);--line:rgba(148,178,214,.14);
--line-2:rgba(148,178,214,.24);--text:#e8eef7;--muted:#93a4ba;--accent:#4cc9f0;--accent-2:#3f7cf5;
--amber:#f5b041;--rose:#f0607a;--ok:#34d399;--radius:18px;--nav:68px;--ease:cubic-bezier(.22,1,.36,1);}
/* Photo on the root element (body has no height in Streamlit). */
html {background:BACKGROUND;background-attachment:fixed;min-height:100%;}
body {background:transparent!important;}
[data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"] {background:transparent!important;}
[data-testid="stApp"] {font-family:'Inter',system-ui,sans-serif;color:var(--text);}
[data-testid="stHeader"] {background:transparent!important;top:var(--nav);height:2.5rem;z-index:999989;}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none!important;}
.block-container {max-width:1360px;padding:calc(var(--nav) + 40px) 40px 40px;}
h1,h2,h3,h4 {color:var(--text)!important;font-family:'Inter',sans-serif!important;letter-spacing:-.025em;}
h2 {font-size:1.45rem!important;} h3 {font-size:1.1rem!important;}
[data-testid="stMarkdownContainer"] p, [data-testid="stWidgetLabel"] p {color:var(--text);}
[data-testid="stCaptionContainer"] p {color:var(--muted)!important;line-height:1.6;}
a {color:var(--accent);}

/* ---------- Top navigation (fixed, full width, like an official site) ---------- */
.st-key-topnav {position:fixed;top:0;left:0;right:0;z-index:999991;height:var(--nav);padding:0 36px;
  display:flex;flex-direction:column;justify-content:center;gap:0!important;
  background:linear-gradient(180deg,rgba(4,7,14,.92),rgba(4,7,14,.70));
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border-bottom:1px solid rgba(255,255,255,.06);}
.st-key-topnav>div {width:100%;}
.st-key-topnav [data-testid="stHorizontalBlock"] {align-items:center;flex-wrap:nowrap;gap:24px;}
.ev-logo {display:flex;align-items:center;gap:12px;white-space:nowrap;text-decoration:none;}
.ev-logo-mark {width:38px;height:38px;border-radius:50%;display:grid;place-items:center;
  border:2px solid #e8eef7;color:#e8eef7;font-size:18px;font-weight:700;box-shadow:0 0 18px rgba(76,201,240,.35);}
.ev-logo-text strong {display:block;font-size:19px;font-weight:700;color:#fff;letter-spacing:.02em;line-height:1.1;}
.ev-logo-text small {display:block;font-size:9.5px;letter-spacing:.28em;color:var(--muted);margin-top:3px;}
/* Workspace radio styled as text menu with an underline on the active item. */
.st-key-topnav [role="radiogroup"] {gap:44px!important;flex-wrap:nowrap;}
.st-key-topnav [role="radiogroup"] label {padding:8px 0!important;margin:0!important;position:relative;cursor:pointer;background:none!important;}
.st-key-topnav [role="radiogroup"] label>div:first-child {display:none!important;}
.st-key-topnav [role="radiogroup"] label p {color:#8d9aad!important;font-size:15px;font-weight:600;letter-spacing:.04em;
  white-space:nowrap;transition:color 250ms var(--ease);}
.st-key-topnav [role="radiogroup"] label:hover p {color:#dfe7f2!important;}
.st-key-topnav [role="radiogroup"] label:has(input:checked) p {color:#fff!important;}
.st-key-topnav [role="radiogroup"] label::after {content:"";position:absolute;left:50%;bottom:-6px;width:0;height:2px;
  background:#fff;border-radius:2px;transform:translateX(-50%);transition:width 300ms var(--ease);}
.st-key-topnav [role="radiogroup"] label:has(input:checked)::after {width:24px;}
.ev-nav-links {display:flex;gap:44px;align-items:center;}
.ev-nav-links a {color:#8d9aad;font-size:15px;font-weight:600;letter-spacing:.04em;text-decoration:none;position:relative;padding:8px 0;white-space:nowrap;}
.ev-nav-links a:hover, .ev-nav-links a.active {color:#fff;}
.ev-nav-links a.active::after {content:"";position:absolute;left:50%;bottom:-6px;width:24px;height:2px;background:#fff;transform:translateX(-50%);border-radius:2px;}
/* Round avatar button that opens the account menu. */
.st-key-topnav [data-testid="stPopover"] {display:flex;justify-content:flex-end;}
.st-key-topnav [data-testid="stPopoverButton"] {width:44px;height:44px;min-height:44px;border-radius:50%!important;padding:0!important;
  background:rgba(255,255,255,.08)!important;border:1px solid rgba(255,255,255,.22)!important;color:#fff!important;}
.st-key-topnav [data-testid="stPopoverButton"]:hover {background:rgba(76,201,240,.18)!important;border-color:var(--accent)!important;}
.st-key-topnav [data-testid="stPopoverButton"] p {display:none;}
.st-key-topnav [data-testid="stPopoverButton"] [data-testid="stIconMaterial"] {margin:0!important;font-size:24px;}
.st-key-topnav [data-testid="stPopoverButton"] svg:last-child {display:none;}
.ev-nav-cta {display:flex;justify-content:flex-end;}
.ev-nav-cta a {display:inline-flex;align-items:center;gap:8px;padding:9px 18px;border-radius:99px;font-size:13px;font-weight:600;
  color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.06);}
.ev-nav-cta a:hover {border-color:var(--accent);background:rgba(76,201,240,.14);}

/* ---------- Sidebar sits below the navigation bar ---------- */
[data-testid="stSidebar"] {top:var(--nav)!important;height:calc(100vh - var(--nav))!important;
  background:rgba(6,10,19,.82)!important;backdrop-filter:blur(18px);border-right:1px solid var(--line);}
[data-testid="stSidebar"] h3 {font-size:.8rem!important;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)!important;}

/* ---------- Form controls ---------- */
[data-baseweb="select"]>div, [data-baseweb="input"], [data-baseweb="base-input"], [data-testid="stNumberInputContainer"] {
  background:rgba(255,255,255,.04)!important;border-color:var(--line-2)!important;border-radius:10px!important;}
[data-baseweb="select"]>div:hover, [data-baseweb="input"]:hover {border-color:rgba(76,201,240,.55)!important;}
/* Dropdowns: no text cursor and no outline box inside the select; the whole
   control glows instead so keyboard focus is still visible. */
[data-baseweb="select"] input {caret-color:transparent!important;outline:none!important;box-shadow:none!important;cursor:pointer;}
[data-baseweb="select"] input:focus, [data-baseweb="select"] input:focus-visible {outline:none!important;box-shadow:none!important;}
[data-baseweb="select"]:focus-within>div {border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(76,201,240,.18)!important;}
[data-baseweb="input"]:focus-within, [data-testid="stNumberInputContainer"]:focus-within {border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(76,201,240,.18)!important;}
input:focus-visible {outline:none!important;}
[data-baseweb="popover"] [role="listbox"] {background:#0d1525!important;border:1px solid var(--line-2);border-radius:12px;}
[role="option"]:hover, [role="option"][aria-selected="true"] {background:rgba(76,201,240,.12)!important;}
.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {border-radius:10px;font-weight:600;
  transition:transform 200ms var(--ease),box-shadow 200ms var(--ease),background 200ms;}
.stButton button[kind="secondary"], .stDownloadButton button {background:rgba(255,255,255,.05);border:1px solid var(--line-2);color:var(--text);}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {
  background:linear-gradient(135deg,#4cc9f0,#3f7cf5)!important;border:0!important;color:#04101d!important;box-shadow:0 8px 24px rgba(63,124,245,.35);}
.stButton button:hover, .stDownloadButton button:hover, [data-testid="stFormSubmitButton"] button:hover {transform:translateY(-1px);}
button:focus-visible, a:focus-visible {outline:2px solid var(--accent)!important;outline-offset:3px;}

/* ---------- Glass surfaces ---------- */
[data-testid="stMetric"] {background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:22px;
  backdrop-filter:blur(16px);min-height:132px;transition:transform 400ms var(--ease),border-color 400ms var(--ease);}
[data-testid="stMetric"]:hover {transform:translateY(-3px);border-color:rgba(76,201,240,.45);}
[data-testid="stMetricLabel"] p {font-size:12px;color:var(--muted)!important;font-weight:500;letter-spacing:.04em;text-transform:uppercase;}
[data-testid="stMetricValue"] {color:#fff;font-size:clamp(1.2rem,1.75vw,1.75rem);font-weight:600;letter-spacing:-.03em;}
[data-testid="stMetricValue"] div {overflow:visible!important;white-space:nowrap;}
/* Hide Streamlit's automatic link icon next to headings. */
[data-testid="stHeaderActionElements"], .ev-hero h1 a, .ev-landing h1 a, .ev-guide h3 a {display:none!important;}
/* Multiselect chips: tinted instead of solid bright blue. */
[data-baseweb="tag"] {background:rgba(76,201,240,.14)!important;border:1px solid rgba(76,201,240,.35)!important;}
[data-baseweb="tag"] span, [data-baseweb="tag"] svg {color:#bfeefd!important;fill:#bfeefd!important;}
[data-testid="stVerticalBlockBorderWrapper"]>div, [data-testid="stExpander"] details, [data-testid="stForm"] {
  background:var(--surface)!important;border:1px solid var(--line)!important;border-radius:var(--radius)!important;backdrop-filter:blur(16px);}
[data-testid="stDataFrame"], [data-testid="stImage"] img, [data-testid="stPyplot"] img {border-radius:14px;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:8px;}
[data-testid="stAlert"] {border-radius:14px;backdrop-filter:blur(12px);}

/* ---------- Page header ---------- */
.ev-hero {position:relative;overflow:hidden;border-radius:24px;padding:40px 44px;margin:0 0 28px;
  background:linear-gradient(120deg,rgba(9,16,30,.86),rgba(9,16,30,.55));border:1px solid var(--line);backdrop-filter:blur(14px);}
.ev-hero::before {content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(600px 220px at 90% -10%,rgba(76,201,240,.22),transparent 70%),
  radial-gradient(400px 200px at 0% 120%,rgba(63,124,245,.18),transparent 70%);}
.ev-eyebrow {font-size:11px;font-weight:600;letter-spacing:.24em;text-transform:uppercase;color:var(--accent);}
.ev-hero h1 {color:#fff!important;font-size:clamp(1.8rem,3.4vw,2.9rem)!important;line-height:1.1;font-weight:700;padding:14px 0 12px!important;margin:0;}
.ev-hero p {color:#b8c5d6!important;max-width:760px;line-height:1.7;margin:0;font-size:15px;}
.ev-hero-foot {display:flex;gap:10px;flex-wrap:wrap;margin-top:22px;}
.ev-pill {border:1px solid var(--line-2);background:rgba(255,255,255,.04);border-radius:99px;padding:6px 13px;font-size:11.5px;color:#cfdbea;}
.ev-context {display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:0 0 14px;letter-spacing:.06em;}
.ev-context b {color:var(--accent);font-weight:600;}
.ev-section {margin:22px 0 6px;font-size:11px;font-weight:600;letter-spacing:.2em;color:var(--accent);text-transform:uppercase;}

/* ---------- Summary cards ---------- */
.ev-card {background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:26px;min-height:250px;
  margin:12px 0 20px;backdrop-filter:blur(16px);}
.ev-card h2 {font-size:18px!important;padding:0 0 4px!important;margin:0;}
.ev-card p {font-size:12.5px;line-height:1.6;color:var(--muted)!important;margin:0 0 18px;}
.ev-status-row {display:grid;grid-template-columns:100px minmax(24px,1fr) 96px;gap:12px;align-items:center;margin:16px 0;font-size:12.5px;}
.ev-track {height:6px;background:rgba(255,255,255,.07);border-radius:9px;overflow:hidden;}
.ev-fill {height:100%;border-radius:9px;background:linear-gradient(90deg,#3f7cf5,#4cc9f0);}
.ev-fill.attention {background:linear-gradient(90deg,#c98a1c,#f5b041);} .ev-fill.critical {background:linear-gradient(90deg,#c2384f,#f0607a);}
.ev-status-row strong {text-align:right;font-weight:500;font-variant-numeric:tabular-nums;}
.ev-share {font-size:44px;line-height:1.15;letter-spacing:-.04em;font-weight:700;
  background:linear-gradient(135deg,#fff,#4cc9f0);-webkit-background-clip:text;background-clip:text;color:transparent;}
.ev-split {display:flex;gap:28px;flex-wrap:wrap;margin-top:18px;}
.ev-split span {display:block;color:var(--muted);font-size:12px;margin-top:6px;}
.ev-split strong {font-size:20px;font-weight:600;}
.ev-footer {border-top:1px solid var(--line);padding-top:20px;margin-top:40px;display:flex;justify-content:space-between;
  flex-wrap:wrap;gap:12px;color:var(--muted);font-size:11.5px;}
.ev-footer a {color:#b8c5d6;}

/* ---------- Sign-in landing page ---------- */
.st-key-fx {position:absolute!important;height:0!important;overflow:hidden;}
.ev-landing {padding:56px 0 0;}
.ev-landing .ev-eyebrow {display:inline-flex;align-items:center;gap:10px;}
.ev-landing .ev-eyebrow::before {content:"";width:28px;height:1px;background:var(--accent);}
.ev-landing h1 {font-size:clamp(2.4rem,5vw,4.4rem)!important;line-height:1.04!important;font-weight:700!important;color:#fff!important;
  margin:18px 0 20px!important;padding:0!important;letter-spacing:-.04em;}
.ev-landing h1 span {background:linear-gradient(120deg,#4cc9f0 10%,#9ad8ff 50%,#3f7cf5 90%);-webkit-background-clip:text;background-clip:text;color:transparent;}
.ev-landing p.lead {font-size:17px;line-height:1.7;color:#c3cfdf!important;max-width:560px;}
.ev-stats {display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:44px 0 0;max-width:640px;}
.ev-stat {border-left:1px solid var(--line-2);padding:4px 0 4px 16px;}
.ev-stat strong {display:block;font-size:26px;font-weight:700;color:#fff;letter-spacing:-.03em;}
.ev-stat span {font-size:11.5px;color:var(--muted);letter-spacing:.04em;}
.st-key-authcard {margin-top:40px;padding:30px 30px 22px;border-radius:24px;background:rgba(8,13,25,.66);
  border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(22px) saturate(140%);-webkit-backdrop-filter:blur(22px) saturate(140%);
  box-shadow:0 30px 80px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.06);animation:ev-rise 900ms var(--ease) both 150ms;}
.st-key-authcard [data-testid="stForm"] {background:transparent!important;border:0!important;padding:0!important;backdrop-filter:none;}
.st-key-authcard [data-testid="stRadio"], .st-key-authcard [data-testid="stRadio"]>div {width:100%;}
.st-key-authcard [role="radiogroup"] {background:rgba(255,255,255,.05);border-radius:12px;padding:4px;gap:0!important;
  display:grid!important;grid-template-columns:1fr 1fr;width:100%;}
.st-key-authcard [role="radiogroup"] label {justify-content:center;border-radius:9px;padding:8px!important;margin:0!important;transition:background 250ms;}
.st-key-authcard [role="radiogroup"] label>div:first-child {display:none!important;}
.st-key-authcard [role="radiogroup"] label:has(input:checked) {background:rgba(76,201,240,.16);}
.st-key-authcard [role="radiogroup"] label p {font-weight:600;color:#c3cfdf!important;}
.st-key-authcard [data-testid="stFormSubmitButton"] button {width:100%;height:46px;}
.ev-auth-head h3 {margin:0 0 4px!important;font-size:1.35rem!important;}
.ev-auth-head p {color:var(--muted)!important;font-size:13px;margin:0 0 16px;}
.ev-features {display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:72px 0 0;}
.ev-feature {background:rgba(8,13,25,.58);border:1px solid var(--line);border-radius:18px;padding:22px;backdrop-filter:blur(14px);
  transition:transform 400ms var(--ease),border-color 400ms;}
.ev-feature:hover {transform:translateY(-4px);border-color:rgba(76,201,240,.45);}
.ev-feature b {display:block;font-size:15px;color:#fff;margin:10px 0 6px;}
.ev-feature span {font-size:13px;color:var(--muted);line-height:1.6;}
.ev-feature i {font-style:normal;font-size:12px;letter-spacing:.2em;color:var(--accent);}
.ev-landing>*, .ev-features {animation:ev-rise 900ms var(--ease) both;}
@keyframes ev-rise {from {opacity:0;transform:translateY(18px);} to {opacity:1;transform:none;}}

/* ---------- Onboarding dialog ---------- */
[data-testid="stDialog"] [role="dialog"] {background:rgba(10,16,30,.94)!important;border:1px solid var(--line-2);border-radius:22px;backdrop-filter:blur(20px);}
.ev-guide-step {font-size:11px;letter-spacing:.22em;color:var(--accent);text-transform:uppercase;font-weight:600;}
.ev-guide-icon {width:56px;height:56px;border-radius:16px;display:grid;place-items:center;font-size:26px;margin:16px 0 14px;
  background:linear-gradient(135deg,rgba(76,201,240,.22),rgba(63,124,245,.22));border:1px solid rgba(76,201,240,.35);}
.ev-guide h3 {margin:0 0 8px!important;font-size:1.4rem!important;}
.ev-guide p {color:#c3cfdf!important;line-height:1.7;font-size:14.5px;}
.ev-guide ul {color:#c3cfdf;line-height:1.8;font-size:14px;padding-left:18px;margin:6px 0 0;}
.ev-dots {display:flex;gap:6px;margin:18px 0 6px;}
.ev-dots span {width:22px;height:4px;border-radius:4px;background:rgba(255,255,255,.14);}
.ev-dots span.on {background:var(--accent);}

@media (max-width:1100px) {.st-key-topnav [role="radiogroup"], .ev-nav-links {gap:22px!important;}
  .ev-features {grid-template-columns:1fr;} .ev-stats {grid-template-columns:repeat(2,1fr);}}
@media (max-width:768px) {.block-container {padding:calc(var(--nav) + 24px) 18px 28px;} .st-key-topnav {padding:0 14px;}
  .ev-logo-text small, .ev-nav-links {display:none;} .ev-hero {padding:28px 22px;}
  .st-key-topnav [role="radiogroup"] label p {font-size:13px;}}
@media (prefers-reduced-motion:reduce) {*,*::before,*::after {animation:none!important;transition:none!important;}}
</style>'''

# Interactive starfield for the sign-in page: depth layers that follow the
# mouse, twinkling stars, a softly glowing moon and occasional shooting stars.
STARFIELD = '''<script>
(() => {
  const doc = window.document;
  if (doc.getElementById('ev-stars')) return;
  const c = doc.createElement('canvas');
  c.id = 'ev-stars';
  c.setAttribute('aria-hidden', 'true');
  // z-index -1: above the page background photo, below all app content.
  c.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;z-index:-1;pointer-events:none;';
  doc.body.prepend(c);
  const ctx = c.getContext('2d');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let W, H, dpr, stars = [], shooting = [], mx = 0, my = 0, tx = 0, ty = 0, t = 0;
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = c.width = innerWidth * dpr; H = c.height = innerHeight * dpr;
    const n = Math.round(innerWidth * innerHeight / 3200);
    stars = Array.from({length: n}, () => ({
      x: Math.random() * W, y: Math.random() * H * 0.78, z: Math.random() * 0.9 + 0.1,
      r: (Math.random() * 1.2 + 0.25) * dpr, p: Math.random() * Math.PI * 2, s: Math.random() * 0.02 + 0.004}));
  }
  addEventListener('resize', resize); resize();
  addEventListener('mousemove', e => { tx = (e.clientX / innerWidth - .5); ty = (e.clientY / innerHeight - .5); });
  function shoot() {
    if (reduce) return;
    shooting.push({x: Math.random() * W * .7 + W * .2, y: Math.random() * H * .3, vx: -(6 + Math.random() * 5) * dpr,
                   vy: (2.2 + Math.random() * 2) * dpr, life: 1});
    setTimeout(shoot, 2600 + Math.random() * 4200);
  }
  setTimeout(shoot, 1500);
  function frame() {
    if (!doc.getElementById('ev-stars')) return;   // removed after login
    t += 1; mx += (tx - mx) * .05; my += (ty - my) * .05;
    ctx.clearRect(0, 0, W, H);
    // Moon with a soft halo; drifts slightly against the mouse.
    const R = Math.min(W, H) * .04, cx = W * .62 - mx * 30 * dpr, cy = H * .14 - my * 20 * dpr;
    let g = ctx.createRadialGradient(cx, cy, R * .4, cx, cy, R * 5.5);
    g.addColorStop(0, 'rgba(210,228,255,.22)'); g.addColorStop(1, 'rgba(210,228,255,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R * 5.5, 0, 7); ctx.fill();
    g = ctx.createRadialGradient(cx - R * .3, cy - R * .3, R * .1, cx, cy, R);
    g.addColorStop(0, '#f4f7fb'); g.addColorStop(.7, '#cdd6e2'); g.addColorStop(1, '#9aa8bb');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.fill();
    ctx.fillStyle = 'rgba(120,135,160,.22)';
    [[-.3,-.2,.18],[.25,.15,.13],[-.05,.38,.1],[.35,-.3,.08]].forEach(([a,b,s]) => {
      ctx.beginPath(); ctx.arc(cx + a * R, cy + b * R, s * R, 0, 7); ctx.fill(); });
    // Stars: nearer stars (bigger z) move more with the mouse.
    for (const s of stars) {
      const tw = reduce ? .8 : .55 + .45 * Math.sin(s.p + t * s.s);
      const x = s.x - mx * 60 * s.z * dpr, y = s.y - my * 40 * s.z * dpr;
      ctx.globalAlpha = tw * (.35 + s.z * .65);
      ctx.fillStyle = s.z > .8 ? '#bfe9ff' : '#ffffff';
      ctx.beginPath(); ctx.arc(x, y, s.r * (.6 + s.z * .6), 0, 7); ctx.fill();
    }
    ctx.globalAlpha = 1;
    shooting = shooting.filter(m => m.life > 0);
    for (const m of shooting) {
      const grad = ctx.createLinearGradient(m.x, m.y, m.x - m.vx * 14, m.y - m.vy * 14);
      grad.addColorStop(0, `rgba(255,255,255,${m.life})`); grad.addColorStop(1, 'rgba(76,201,240,0)');
      ctx.strokeStyle = grad; ctx.lineWidth = 1.6 * dpr; ctx.beginPath();
      ctx.moveTo(m.x, m.y); ctx.lineTo(m.x - m.vx * 14, m.y - m.vy * 14); ctx.stroke();
      m.x += m.vx; m.y += m.vy; m.life -= .012;
    }
    requestAnimationFrame(frame);
  }
  frame();
})();
</script>'''

REMOVE_STARFIELD = "<script>document.getElementById('ev-stars')?.remove();</script>"


def apply_style(page):
    """page = 'login' or 'portal'; each uses its own background photo."""
    if page == 'login':
        # Dark on the left (headline) and at the top (sky for the stars); the
        # lit charging canopy shows through on the right.
        background = ('linear-gradient(90deg,rgba(3,5,10,.95) 0%,rgba(3,5,10,.86) 32%,rgba(3,5,10,.45) 62%,rgba(3,5,10,.30) 100%),'
                      'linear-gradient(180deg,rgba(3,5,10,.85) 0%,rgba(3,5,10,.35) 30%,rgba(3,5,10,.25) 65%,rgba(3,5,10,.92) 100%),'
                      f'url("{LOGIN_PHOTO}") center 70%/cover no-repeat fixed, #05080f')
    else:
        background = ('linear-gradient(110deg,rgba(4,7,14,.97) 0%,rgba(4,7,14,.93) 50%,rgba(4,7,14,.80) 100%),'
                      f'url("{PORTAL_PHOTO}") right center/cover no-repeat fixed, #05080f')
    st.markdown(STYLE.replace('BACKGROUND', background), unsafe_allow_html=True)
    with st.container(key='fx'):
        st.html(STARFIELD if page == 'login' else REMOVE_STARFIELD, unsafe_allow_javascript=True)


def logo():
    return ('<div class="ev-logo"><div class="ev-logo-mark" aria-hidden="true">ϟ</div>'
            '<div class="ev-logo-text"><strong>Campus EV</strong><small>CHARGING RESEARCH</small></div></div>')


def landing_nav():
    """Navigation bar shown before sign-in (anchor links within the page)."""
    with st.container(key='topnav'):
        left, mid, right = st.columns([2.2, 6, 1.6], vertical_alignment='center')
        left.markdown(logo(), unsafe_allow_html=True)
        mid.markdown('<nav class="ev-nav-links" aria-label="Main"><a class="active" href="#home">Home</a>'
                     '<a href="#research">Research</a><a href="#platform">Platform</a>'
                     '<a href="#signin">Sign in</a></nav>', unsafe_allow_html=True)
        right.markdown('<div class="ev-nav-cta"><a href="#signin">Access portal →</a></div>', unsafe_allow_html=True)


def landing_intro(stats):
    items = ''.join(f'<div class="ev-stat"><strong>{escape(v)}</strong><span>{escape(k)}</span></div>' for k, v in stats)
    st.markdown(
        '<section class="ev-landing" id="home">'
        '<div class="ev-eyebrow">Taylor\'s Smart Campus · EV charging research</div>'
        '<h1>Powering the campus,<br><span>one charge at a time.</span></h1>'
        '<p class="lead">Explore 1,200 recorded charging sessions, see how energy, temperature and peak demand '
        'interact, and predict charger grid status in real time.</p>'
        f'<div class="ev-stats" id="research">{items}</div></section>', unsafe_allow_html=True)


def landing_features():
    cards = [('01', 'Executive KPI Dashboard', 'Energy delivered, session duration and estimated peak revenue, filtered your way.'),
             ('02', 'Visual Analytics Studio', 'Temperature, demand and charger-mix charts built with Matplotlib and Seaborn.'),
             ('03', 'Live ML Inference', 'A cross-validated Decision Tree flags Normal, Overheated or Grid_Surge sessions.')]
    st.markdown('<section class="ev-features" id="platform">' + ''.join(
        f'<div class="ev-feature"><i>{n}</i><b>{escape(a)}</b><span>{escape(b)}</span></div>' for n, a, b in cards)
        + '</section>', unsafe_allow_html=True)


def hero(number, title, description, tags):
    pills = ''.join(f'<span class="ev-pill">{escape(tag)}</span>' for tag in tags)
    st.markdown(f'<section class="ev-hero" aria-label="{escape(title)}">'
                f'<div class="ev-eyebrow">Campus EV / Workspace {number}</div>'
                f'<h1>{escape(title)}</h1><p>{escape(description)}</p>'
                f'<div class="ev-hero-foot">{pills}</div></section>', unsafe_allow_html=True)


def context(selected, total):
    st.markdown(f'<div class="ev-context"><span>OPERATIONS / HISTORICAL SESSIONS</span>'
                f'<span><b>{selected:,}</b> of {total:,} sessions selected · Task 1 cleaned data</span></div>',
                unsafe_allow_html=True)


def overview(df):
    if df.empty:
        return
    n = len(df)
    rows = []
    for label, style in [('Normal', ''), ('Overheated', 'attention'), ('Grid_Surge', 'critical')]:
        count = int(df.Grid_Status_Label.eq(label).sum())
        share = count / n * 100
        rows.append(f'<div class="ev-status-row"><span>{label}</span>'
                    f'<div class="ev-track" aria-hidden="true"><div class="ev-fill {style}" style="width:{share:.2f}%"></div></div>'
                    f'<strong>{count:,} · {share:.1f}%</strong></div>')
    left, right = st.columns([1.4, 1], gap='medium')
    with left:
        st.markdown('<section class="ev-card"><h2>Observed grid status</h2>'
                    '<p>Historical labels across the sessions in view.</p>' + ''.join(rows) + '</section>', unsafe_allow_html=True)
    with right:
        peak = df.loc[df.Peak_Hour_Flag.eq(1)]
        share = len(peak) / n * 100
        st.markdown('<section class="ev-card"><h2>Peak-period activity</h2>'
                    '<p>Sessions starting between 12:00 and 17:00 (hours 12–17).</p>'
                    f'<div class="ev-share">{share:.1f}%</div>'
                    f'<div class="ev-split"><div><strong>{len(peak):,}</strong><span>peak-start sessions</span></div>'
                    f'<div><strong>{peak.Energy_kWh.sum():,.1f} kWh</strong><span>energy in peak-start sessions</span></div></div></section>',
                    unsafe_allow_html=True)


def footer():
    st.markdown('<footer class="ev-footer"><span>Campus EV · ITS72604 Assessment 2</span>'
                f'<span>{CREDITS}</span></footer>', unsafe_allow_html=True)
