import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── AED formatting helpers ─────────────────────────────────────────────────────
def format_aed(value):
    digits = re.sub(r"[^\d]", "", str(value))
    return f"{int(digits):,}" if digits else ""

def parse_aed(value):
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else 0

GOOGLE_CREDS_JSON  = os.getenv("GOOGLE_CREDS_JSON", "google_creds.json")
GOOGLE_SHEET_NAME  = os.getenv("GOOGLE_SHEET_NAME", "Dubai Calculator Leads")
GMAIL_SENDER       = os.getenv("GMAIL_SENDER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_NOTIFY       = os.getenv("GMAIL_NOTIFY", "")
RAPIDAPI_KEY       = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST      = "uae-real-estate3.p.rapidapi.com"

st.set_page_config(
    page_title="Dubai Rent vs Buy Calculator 2026",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { background-color: #0a0f1e; color: #e8e0d0; }
    .main .block-container { padding: 2rem 3rem; max-width: 1100px; }
    #MainMenu, footer, header { visibility: hidden; }
    .hero { text-align: center; padding: 2.5rem 0 1.5rem; }
    .hero-title { font-size: 2.4rem; font-weight: 700; color: #C9A84C; margin: 0 0 0.5rem; }
    .hero-sub { font-size: 1rem; color: #8a9bb5; margin: 0 0 0.3rem; }
    .hero-badge {
        display: inline-block; background: rgba(201,168,76,0.12);
        border: 1px solid rgba(201,168,76,0.3); color: #C9A84C;
        font-size: 0.75rem; padding: 4px 14px; border-radius: 20px; margin-top: 0.5rem;
    }
    .card-title {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em;
        color: #C9A84C; text-transform: uppercase; margin-bottom: 1rem;
        border-bottom: 1px solid rgba(201,168,76,0.2); padding-bottom: 0.5rem;
    }
    .hint { font-size: 0.75rem; color: #4a6080; margin-top: -10px; margin-bottom: 10px; }
    .live-badge { display: inline-block; background: rgba(45,158,95,0.15); border: 1px solid rgba(45,158,95,0.4); color: #2d9e5f; font-size: 0.7rem; padding: 2px 8px; border-radius: 20px; }
    .static-badge { display: inline-block; background: rgba(201,168,76,0.1); border: 1px solid rgba(201,168,76,0.3); color: #C9A84C; font-size: 0.7rem; padding: 2px 8px; border-radius: 20px; }
    .stNumberInput input, .stTextInput input {
        background: #1a2235 !important; border: 1px solid rgba(201,168,76,0.25) !important;
        color: #e8e0d0 !important; border-radius: 8px !important;
    }
    .stNumberInput button { background: #1a2235 !important; border-color: rgba(201,168,76,0.25) !important; color: #C9A84C !important; }
    .stNumberInput button:hover { background: rgba(201,168,76,0.15) !important; }
    label, .stSelectbox label, .stNumberInput label { color: #8a9bb5 !important; font-size: 0.82rem !important; }
    .stSelectbox [data-baseweb="select"] > div { background: #1a2235 !important; border: 1px solid rgba(201,168,76,0.25) !important; border-radius: 8px !important; color: #e8e0d0 !important; }
    .stSelectbox [data-baseweb="select"] span { color: #e8e0d0 !important; }
    .stSelectbox [data-baseweb="select"] svg { fill: #C9A84C !important; }
    [data-baseweb="popover"] li { background: #1a2235 !important; color: #e8e0d0 !important; }
    [data-baseweb="popover"] li:hover { background: rgba(201,168,76,0.15) !important; }
    .verdict-buy { background: #0d2b1e; border: 1px solid #2d9e5f; border-radius: 12px; padding: 1.5rem; text-align: center; }
    .verdict-rent { background: #2b0d0d; border: 1px solid #9e2d2d; border-radius: 12px; padding: 1.5rem; text-align: center; }
    .verdict-title { font-size: 1.5rem; font-weight: 700; margin: 0 0 0.3rem; }
    .verdict-sub { font-size: 0.88rem; color: #8a9bb5; margin: 0; }
    .kpi-grid { display: flex; gap: 12px; margin: 1rem 0; flex-wrap: wrap; }
    .kpi-card { flex: 1; min-width: 120px; background: #1a2235; border: 1px solid rgba(201,168,76,0.15); border-radius: 10px; padding: 1rem; text-align: center; }
    .kpi-val { font-size: 1.1rem; font-weight: 700; color: #C9A84C; }
    .kpi-lbl { font-size: 0.7rem; color: #8a9bb5; margin-top: 4px; }
    .bar-section { background: #111827; border: 1px solid rgba(201,168,76,0.1); border-radius: 10px; padding: 1.25rem; margin: 1rem 0; }
    .bar-title { font-size: 0.7rem; color: #C9A84C; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1rem; font-weight: 600; }
    .bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
    .bar-label { font-size: 0.78rem; color: #8a9bb5; width: 160px; flex-shrink: 0; }
    .bar-track { flex: 1; height: 10px; background: rgba(255,255,255,0.06); border-radius: 5px; overflow: hidden; }
    .bar-fill-buy  { height: 100%; background: linear-gradient(90deg, #1a6e45, #2d9e5f); border-radius: 5px; }
    .bar-fill-rent { height: 100%; background: linear-gradient(90deg, #6e1a1a, #9e2d2d); border-radius: 5px; }
    .bar-val { font-size: 0.82rem; font-weight: 600; color: #e8e0d0; width: 120px; text-align: right; }
    .bar-note { font-size: 0.72rem; color: #4a6080; margin-top: 6px; }
    .lead-box { background: #111827; border: 1px solid rgba(201,168,76,0.4); border-radius: 14px; padding: 2rem; text-align: center; margin-top: 1.5rem; }
    .lead-title { font-size: 1.2rem; font-weight: 700; color: #C9A84C; margin-bottom: 0.3rem; }
    .lead-sub { font-size: 0.85rem; color: #8a9bb5; }
    .disclaimer { background: rgba(201,168,76,0.04); border: 1px solid rgba(201,168,76,0.12); border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.73rem; color: #4a6080; margin: 0.5rem 0; }
    .stButton > button,
    .stFormSubmitButton > button,
    button[kind="primaryFormSubmit"],
    button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        background: #C9A84C !important;
        color: #0a0f1e !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        font-size: 1rem !important;
        width: 100% !important;
    }
    .stButton > button:hover,
    .stFormSubmitButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: #b8963e !important;
        color: #0a0f1e !important;
    }
    hr { border-color: rgba(201,168,76,0.15) !important; }
</style>
""", unsafe_allow_html=True)

# ── Community data — corrected against Bayut 2026 report ──────────────────────
# Annual rents verified against: Bayut Dubai Rental Report 2025, Sands of Wealth 2026,
# DLD Rental Index. Studios: AED 45K–130K citywide. 1BR: AED 55K–130K. 2BR: AED 85K–220K.
COMMUNITIES = {
    # ── Luxury / Waterfront ──────────────────────────────────────────────────
    "Palm Jumeirah":              {"psf": 3500, "studio": 110000, "1br": 160000, "2br": 230000, "3br": 330000, "4br": 460000},
    "Bluewaters Island":          {"psf": 3200, "studio": 105000, "1br": 148000, "2br": 210000, "3br": 300000, "4br": 410000},
    "Emaar Beachfront":           {"psf": 2800, "studio": 95000,  "1br": 135000, "2br": 195000, "3br": 280000, "4br": 375000},
    "Dubai Harbour":              {"psf": 2500, "studio": 88000,  "1br": 125000, "2br": 178000, "3br": 250000, "4br": 335000},
    "City Walk":                  {"psf": 2900, "studio": 95000,  "1br": 138000, "2br": 200000, "3br": 285000, "4br": 375000},
    "Emirates Hills":             {"psf": 2800, "studio": 95000,  "1br": 138000, "2br": 200000, "3br": 295000, "4br": 420000},
    # ── Premium ─────────────────────────────────────────────────────────────
    "Downtown Dubai":             {"psf": 2800, "studio": 82000,  "1br": 115000, "2br": 168000, "3br": 245000, "4br": 330000},
    "DIFC":                       {"psf": 2600, "studio": 88000,  "1br": 125000, "2br": 180000, "3br": 258000, "4br": 345000},
    "Dubai Marina":               {"psf": 2100, "studio": 68000,  "1br": 98000,  "2br": 140000, "3br": 192000, "4br": 258000},
    "JBR (Jumeirah Beach)":       {"psf": 2300, "studio": 75000,  "1br": 108000, "2br": 155000, "3br": 210000, "4br": 280000},
    "Jumeirah":                   {"psf": 2200, "studio": 72000,  "1br": 105000, "2br": 150000, "3br": 208000, "4br": 288000},
    "Sobha Hartland":             {"psf": 2000, "studio": 65000,  "1br": 95000,  "2br": 138000, "3br": 192000, "4br": 258000},
    "Creek Harbour":              {"psf": 2200, "studio": 72000,  "1br": 105000, "2br": 150000, "3br": 208000, "4br": 278000},
    # ── Mid-market ──────────────────────────────────────────────────────────
    "Business Bay":               {"psf": 1900, "studio": 62000,  "1br": 88000,  "2br": 125000, "3br": 175000, "4br": 230000},
    "Dubai Hills Estate":         {"psf": 1800, "studio": 58000,  "1br": 88000,  "2br": 132000, "3br": 180000, "4br": 240000},
    "MBR City":                   {"psf": 1900, "studio": 62000,  "1br": 90000,  "2br": 128000, "3br": 180000, "4br": 238000},
    "Meydan":                     {"psf": 1700, "studio": 56000,  "1br": 82000,  "2br": 118000, "3br": 165000, "4br": 218000},
    "Jumeirah Lake Towers":       {"psf": 1400, "studio": 48000,  "1br": 70000,  "2br": 98000,  "3br": 132000, "4br": 172000},
    "Jumeirah Golf Estates":      {"psf": 1600, "studio": 52000,  "1br": 78000,  "2br": 115000, "3br": 160000, "4br": 218000},
    "Jumeirah Islands":           {"psf": 2000, "studio": 65000,  "1br": 98000,  "2br": 142000, "3br": 198000, "4br": 268000},
    "Trade Centre":               {"psf": 1800, "studio": 58000,  "1br": 82000,  "2br": 118000, "3br": 165000, "4br": 218000},
    "Tilal Al Ghaf":              {"psf": 1700, "studio": 55000,  "1br": 82000,  "2br": 118000, "3br": 165000, "4br": 222000},
    "The Springs":                {"psf": 1450, "studio": 48000,  "1br": 70000,  "2br": 100000, "3br": 138000, "4br": 182000},
    "The Meadows":                {"psf": 1550, "studio": 50000,  "1br": 75000,  "2br": 108000, "3br": 150000, "4br": 198000},
    "The Lakes":                  {"psf": 1600, "studio": 52000,  "1br": 78000,  "2br": 112000, "3br": 155000, "4br": 205000},
    "The Greens":                 {"psf": 1500, "studio": 50000,  "1br": 72000,  "2br": 102000, "3br": 142000, "4br": 188000},
    "The Views":                  {"psf": 1550, "studio": 50000,  "1br": 74000,  "2br": 106000, "3br": 148000, "4br": 195000},
    "Emirates Living":            {"psf": 1700, "studio": 55000,  "1br": 82000,  "2br": 118000, "3br": 165000, "4br": 218000},
    "Arabian Ranches":            {"psf": 1600, "studio": 52000,  "1br": 82000,  "2br": 122000, "3br": 165000, "4br": 210000},
    "Arabian Ranches 2":          {"psf": 1500, "studio": 50000,  "1br": 78000,  "2br": 112000, "3br": 155000, "4br": 200000},
    "Arabian Ranches 3":          {"psf": 1400, "studio": 46000,  "1br": 72000,  "2br": 102000, "3br": 142000, "4br": 188000},
    "DAMAC Hills":                {"psf": 1350, "studio": 45000,  "1br": 68000,  "2br": 98000,  "3br": 135000, "4br": 178000},
    "Mudon":                      {"psf": 1300, "studio": 42000,  "1br": 65000,  "2br": 92000,  "3br": 125000, "4br": 165000},
    "Victory Heights":            {"psf": 1200, "studio": 40000,  "1br": 60000,  "2br": 85000,  "3br": 115000, "4br": 150000},
    "Al Barsha":                  {"psf": 1100, "studio": 38000,  "1br": 55000,  "2br": 78000,  "3br": 105000, "4br": 138000},
    "Al Furjan":                  {"psf": 1150, "studio": 40000,  "1br": 58000,  "2br": 82000,  "3br": 112000, "4br": 148000},
    # ── Affordable ──────────────────────────────────────────────────────────
    "JVC (Jumeirah Village Circle)": {"psf": 1200, "studio": 45000, "1br": 65000, "2br": 88000, "3br": 118000, "4br": 155000},
    "JVT (Jumeirah Village Triangle)": {"psf": 1100, "studio": 42000, "1br": 60000, "2br": 82000, "3br": 110000, "4br": 145000},
    "Dubai Sports City":          {"psf": 1000, "studio": 38000,  "1br": 55000,  "2br": 78000,  "3br": 105000, "4br": 138000},
    "Motor City":                 {"psf": 1000, "studio": 38000,  "1br": 55000,  "2br": 78000,  "3br": 105000, "4br": 138000},
    "Dubai Silicon Oasis":        {"psf":  900, "studio": 35000,  "1br": 50000,  "2br": 70000,  "3br": 95000,  "4br": 125000},
    "Dubailand":                  {"psf":  950, "studio": 36000,  "1br": 52000,  "2br": 72000,  "3br": 98000,  "4br": 128000},
    "Town Square":                {"psf":  950, "studio": 36000,  "1br": 52000,  "2br": 72000,  "3br": 98000,  "4br": 128000},
    "DAMAC Hills 2":              {"psf":  950, "studio": 36000,  "1br": 52000,  "2br": 72000,  "3br": 98000,  "4br": 128000},
    "Akoya Oxygen":               {"psf":  950, "studio": 36000,  "1br": 52000,  "2br": 72000,  "3br": 98000,  "4br": 128000},
    "Discovery Gardens":          {"psf":  800, "studio": 30000,  "1br": 45000,  "2br": 65000,  "3br": 88000,  "4br": 115000},
    "International City":         {"psf":  650, "studio": 26000,  "1br": 38000,  "2br": 55000,  "3br": 75000,  "4br": 98000},
    "Mirdif":                     {"psf":  900, "studio": 34000,  "1br": 50000,  "2br": 72000,  "3br": 98000,  "4br": 128000},
    "Al Nahda":                   {"psf":  800, "studio": 28000,  "1br": 42000,  "2br": 60000,  "3br": 82000,  "4br": 108000},
    "Deira":                      {"psf":  800, "studio": 28000,  "1br": 42000,  "2br": 60000,  "3br": 82000,  "4br": 108000},
    "Bur Dubai":                  {"psf":  850, "studio": 30000,  "1br": 45000,  "2br": 65000,  "3br": 88000,  "4br": 115000},
    "Al Quoz":                    {"psf":  950, "studio": 34000,  "1br": 50000,  "2br": 70000,  "3br": 95000,  "4br": 125000},
    "Oud Metha":                  {"psf": 1000, "studio": 36000,  "1br": 52000,  "2br": 74000,  "3br": 100000, "4br": 132000},
}

BED_KEY = {"Studio": "studio", "1 BR": "1br", "2 BR": "2br", "3 BR": "3br", "4+ BR": "4br"}

# ── Bayut live rent fetch ──────────────────────────────────────────────────────
def get_bayut_headers():
    return {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}

@st.cache_data(ttl=3600)
def fetch_live_rent(community, beds_key):
    if not RAPIDAPI_KEY:
        return None, False
    try:
        r1   = requests.get(f"https://{RAPIDAPI_HOST}/autocomplete",
                            headers=get_bayut_headers(),
                            params={"query": community.split("(")[0].strip()}, timeout=8)
        locs = r1.json().get("data", {}).get("locations", [])
        if not locs:
            return None, False
        loc_id   = locs[0]["externalID"]
        beds_num = {"studio":"0","1br":"1","2br":"2","3br":"3","4br":"4"}
        params   = {"purpose":"for-rent","locationExternalIDs":loc_id,"hitsPerPage":"50","page":"1"}
        if beds_key in beds_num:
            params["beds"] = beds_num[beds_key]
        r2   = requests.get(f"https://{RAPIDAPI_HOST}/transactions",
                            headers=get_bayut_headers(), params=params, timeout=8)
        hits = r2.json().get("data", {}).get("hits", [])
        if not hits:
            return None, False
        rents = []
        for h in hits:
            amt = h.get("contract_monthly_amount") or h.get("transaction_amount")
            if amt:
                try:
                    v = float(amt)
                    annual = v * 12 if v < 100000 else v
                    if 20000 < annual < 2000000:
                        rents.append(annual)
                except Exception:
                    pass
        if len(rents) < 3:
            return None, False
        return int(sum(rents) / len(rents)), True
    except Exception:
        return None, False

# ── Google Sheets ──────────────────────────────────────────────────────────────
def get_sheet():
    try:
        scopes = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
        creds  = Credentials.from_service_account_file(GOOGLE_CREDS_JSON, scopes=scopes)
        client = gspread.authorize(creds)
        sheet  = client.open(GOOGLE_SHEET_NAME).sheet1
        if sheet.row_count == 0 or sheet.cell(1,1).value != "Timestamp":
            sheet.append_row(["Timestamp","Name","Email","Phone","Community","Beds",
                               "Size (sqft)","Purchase Price","Annual Rent",
                               "Verdict","Break-even Year","Monthly Mortgage"])
        return sheet
    except Exception:
        return None

def save_lead(row):
    try:
        sheet = get_sheet()
        if sheet:
            sheet.append_row(row)
            return True
    except Exception:
        pass
    return False

def send_email(lead):
    if not all([GMAIL_SENDER, GMAIL_APP_PASSWORD, GMAIL_NOTIFY]):
        return False
    try:
        msg            = MIMEMultipart("alternative")
        msg["Subject"] = f"New Lead: {lead['name']} — {lead['community']} {lead['beds']}"
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = GMAIL_NOTIFY
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:580px;margin:0 auto;">
          <div style="background:#C9A84C;padding:20px 30px;border-radius:10px 10px 0 0;">
            <h2 style="color:#0a0f1e;margin:0;">New Property Lead 🏙️</h2>
            <p style="color:#0a0f1e;margin:4px 0 0;opacity:0.75;font-size:13px;">Dubai Rent vs Buy Calculator · {lead['timestamp']}</p>
          </div>
          <div style="background:#111827;padding:25px 30px;border-radius:0 0 10px 10px;">
            <table style="width:100%;border-collapse:collapse;font-size:14px;color:#e8e0d0;">
              <tr><td style="padding:7px 0;color:#8a9bb5;width:45%;">Name</td><td style="color:#C9A84C;font-weight:bold;">{lead['name']}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Email</td><td>{lead['email']}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">WhatsApp</td><td>{lead['phone']}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Community</td><td>{lead['community']}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Bedrooms</td><td>{lead['beds']}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Size</td><td>{lead['size_sqft']:,} sqft</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Purchase Price</td><td>AED {lead['price']:,}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Annual Rent</td><td>AED {lead['annual_rent']:,}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Verdict</td><td style="color:{'#2d9e5f' if 'beats' in lead['verdict'] else '#9e2d2d'};font-weight:bold;">{lead['verdict']}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Break-even</td><td>{lead['breakeven']}</td></tr>
              <tr><td style="padding:7px 0;color:#8a9bb5;">Monthly Mortgage</td><td>AED {lead['mortgage']:,}</td></tr>
            </table>
          </div>
        </div>"""
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_SENDER, GMAIL_NOTIFY, msg.as_string())
        return True
    except Exception:
        return False

# ── Calculation engine (fixed) ─────────────────────────────────────────────────
def calculate(price, annual_rent, dp_pct, rate_pct, term_yrs, appr_pct, ri_pct, sc_psf, size_sqft, years=10):
    loan         = price * (1 - dp_pct / 100)
    monthly_rate = (rate_pct / 100) / 12
    n_months     = term_yrs * 12
    mortgage     = loan * (monthly_rate * (1 + monthly_rate)**n_months) / ((1 + monthly_rate)**n_months - 1) if monthly_rate > 0 else loan / n_months

    dld_fee   = price * 0.04
    agent_fee = price * 0.02
    upfront   = price * (dp_pct / 100) + dld_fee + agent_fee + 4200

    # Buy total starts at upfront (cash already spent on day 1)
    buy_cumulative  = upfront
    rent_cumulative = 0
    cur_rent        = annual_rent
    balance         = loan
    prop_val        = price
    be_year         = None
    yearly          = []

    for y in range(1, years + 1):
        ann_mortgage   = mortgage * 12
        service_charge = sc_psf * size_sqft      # annual service charge (AED/sqft × sqft)
        buy_cumulative  += ann_mortgage + service_charge
        rent_cumulative += cur_rent

        # Pay down loan
        interest  = balance * (rate_pct / 100)
        principal = ann_mortgage - interest
        balance   = max(0, balance - principal)
        prop_val *= (1 + appr_pct / 100)
        cur_rent *= (1 + ri_pct / 100)

        # Net buy cost = total spent MINUS appreciation gained
        net_buy_cost = buy_cumulative - (prop_val - price)
        if be_year is None and net_buy_cost < rent_cumulative:
            be_year = y

        yearly.append({
            "Year":                    y,
            "Cumulative Buy Cost":     f"AED {round(buy_cumulative):,}",
            "Cumulative Rent Cost":    f"AED {round(rent_cumulative):,}",
            "Net Buy Cost (adj.)":     f"AED {round(net_buy_cost):,}",
            "Property Value":          f"AED {round(prop_val):,}",
            "Remaining Loan":          f"AED {round(balance):,}",
        })

    equity = prop_val - balance - upfront

    # Option B: extra costs only (no property price, no down payment)
    # = DLD fee + agent + registration + total mortgage interest paid + total service charges
    total_interest     = (mortgage * 12 * 10) - (loan - balance)   # interest portion only
    total_service      = round(sc_psf * size_sqft * 10)
    ownership_cost     = round(dld_fee + agent_fee + 4200 + total_interest + total_service)

    return {
        "mortgage":          round(mortgage),
        "upfront":           round(upfront),
        "buy_cumulative":    round(buy_cumulative),
        "ownership_cost":    ownership_cost,
        "rent_cumulative":   round(rent_cumulative),
        "equity":            round(equity),
        "prop_val":          round(prop_val),
        "dld_fee":           round(dld_fee),
        "agent_fee":         round(agent_fee),
        "loan":              round(loan),
        "be_year":           be_year,
        "yearly":            yearly,
        "service_charge":    round(sc_psf * size_sqft),
        "total_interest":    round(total_interest),
        "total_service":     total_service,
    }

def fmt(n):
    n = round(n)
    if abs(n) >= 1_000_000: return f"AED {n/1_000_000:.2f}M"
    if abs(n) >= 1_000:     return f"AED {n:,.0f}"
    return f"AED {n}"

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <div class="hero-title">Dubai Rent vs Buy Calculator</div>
  <div class="hero-sub">Make smarter property decisions with real Dubai market data</div>
  <div class="hero-badge">2026 Edition · 50+ Communities · Live Bayut Pricing</div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

col_left, col_right = st.columns(2, gap="large")

with col_left:
    st.markdown('<div class="card-title">Property Details</div>', unsafe_allow_html=True)
    community = st.selectbox("Community", sorted(COMMUNITIES.keys()))
    beds      = st.selectbox("Bedrooms", list(BED_KEY.keys()))
    mkt       = COMMUNITIES[community]
    mkt_psf   = mkt["psf"]
    beds_key  = BED_KEY[beds]

    with st.spinner("Fetching live rent from Bayut..."):
        live_rent, is_live = fetch_live_rent(community, beds_key)

    fallback_rent = mkt[beds_key]
    default_rent  = live_rent if is_live and live_rent else fallback_rent
    rent_source   = "live" if is_live and live_rent else "static"

    size_sqft = st.number_input("Property Size (sqft)", min_value=200, max_value=20000, value=1000, step=50)
    suggested_price = mkt_psf * size_sqft

    # ── Price input with auto comma formatting ─────────────────────────────
    if "price_input" not in st.session_state or        abs(parse_aed(st.session_state.get("price_input","0")) - int(suggested_price)) > 500000:
        st.session_state.price_input = f"{int(suggested_price):,}"

    def update_price():
        st.session_state.price_input = format_aed(st.session_state.price_input)

    st.text_input("Purchase Price (AED)", key="price_input", on_change=update_price)
    price = max(300000, min(50000000, parse_aed(st.session_state.price_input) or int(suggested_price)))
    st.markdown(
        f'<div class="hint">Market avg: AED {mkt_psf:,}/sqft · '
        f'Suggested: AED {suggested_price:,} · '
        f'Your price: AED {round(price/size_sqft):,}/sqft</div>',
        unsafe_allow_html=True
    )

    # ── Rent input with auto comma formatting ──────────────────────────────
    if "rent_input" not in st.session_state:
        st.session_state.rent_input = f"{int(default_rent):,}"

    def update_rent():
        st.session_state.rent_input = format_aed(st.session_state.rent_input)

    st.text_input("Annual Rent (AED)", key="rent_input", on_change=update_rent)
    annual_rent = max(20000, min(2000000, parse_aed(st.session_state.rent_input) or default_rent))
    if rent_source == "live":
        st.markdown(
            f'<div class="hint"><span class="live-badge">Live Bayut</span> '
            f'Avg {beds} rent in {community.split("(")[0].strip()}: '
            f'AED {live_rent:,}/yr · AED {round(live_rent/12):,}/mo</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="hint"><span class="static-badge">Market avg</span> '
            f'{beds} in {community.split("(")[0].strip()}: '
            f'AED {fallback_rent:,}/yr · AED {round(fallback_rent/12):,}/mo · '
            f'Adjust above if needed</div>',
            unsafe_allow_html=True
        )

with col_right:
    st.markdown('<div class="card-title">Financial Assumptions</div>', unsafe_allow_html=True)

    dp_pct = st.number_input("Down Payment (%)", min_value=15, max_value=80, value=25, step=5)
    st.markdown('<div class="hint">UAE minimum: 20% expats · 15% UAE nationals · Off-plan varies</div>', unsafe_allow_html=True)

    rate_pct = st.number_input("Mortgage Interest Rate (%)", min_value=1.0, max_value=12.0, value=4.5, step=0.1)
    st.markdown('<div class="hint">Current UAE fixed: 3.99%–5.5% · Variable: 4.0%–6.0%</div>', unsafe_allow_html=True)

    term_yrs = st.number_input("Mortgage Term (Years)", min_value=5, max_value=25, value=25, step=1)
    st.markdown('<div class="hint">Max term in UAE: 25 years · Must complete before age 70</div>', unsafe_allow_html=True)

    appr_pct = st.number_input("Annual Price Appreciation (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.5)
    st.markdown('<div class="hint">Dubai 5-yr avg: 4–7% · Conservative: 3% · Optimistic: 8–10%</div>', unsafe_allow_html=True)

    ri_pct = st.number_input("Annual Rent Increase (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.5)
    st.markdown('<div class="hint">Dubai RERA cap: 0–20% depending on gap vs market · Avg: 5–10%</div>', unsafe_allow_html=True)

    sc_psf = st.number_input("Service Charge (AED per sqft per year)", min_value=8, max_value=30, value=15, step=1)
    st.markdown('<div class="hint">Affordable (JVC, Motor City): AED 8–12 · Mid-market (Business Bay, JLT): AED 12–18 · Premium (Marina, Downtown): AED 18–25 · Luxury (Palm, DIFC): AED 25–30</div>', unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer">
  <b>Data sources:</b> Purchase price benchmarks from DLD historical transaction data.
  Rental prices pulled live from Bayut API where available, otherwise Q1 2026 market averages
  verified against Bayut Dubai Rental Report 2025 and DLD Rental Index.
  All figures are indicative — actual prices vary by building, floor, and furnishing.
  Adjust any value manually. This tool does not constitute financial or investment advice.
</div>
""", unsafe_allow_html=True)

# ── Calculate ──────────────────────────────────────────────────────────────────
r = calculate(price, annual_rent, dp_pct, rate_pct, term_yrs, appr_pct, ri_pct, sc_psf, size_sqft)
st.markdown("---")

# ── Yield sanity check ─────────────────────────────────────────────────────────
gross_yield = (annual_rent / price) * 100
if gross_yield < 3:
    st.warning(
        f"⚠️ **Low yield alert:** At AED {annual_rent:,}/yr rent on a AED {price:,} property, "
        f"the gross yield is only {gross_yield:.1f}%. Dubai market average is 5–7%. "
        f"Consider adjusting the rent or purchase price — this may skew the break-even result."
    )

# ── Verdict ────────────────────────────────────────────────────────────────────
if r["be_year"]:
    verdict_str   = f"Buying beats renting in {r['be_year']} year{'s' if r['be_year'] > 1 else ''}"
    verdict_sub   = f"After year {r['be_year']}, owning in {community.split('(')[0].strip()} costs less than renting — and you build equity."
    verdict_class = "verdict-buy"
    verdict_color = "#2d9e5f"
else:
    verdict_str   = "Renting is more cost-effective over 10 years"
    verdict_sub   = "At current prices and rates, renting is financially better over a 10-year horizon — but you build no equity."
    verdict_class = "verdict-rent"
    verdict_color = "#9e2d2d"

st.markdown(f"""
<div class="{verdict_class}">
  <div class="verdict-title" style="color:{verdict_color};">{verdict_str}</div>
  <div class="verdict-sub">{verdict_sub}</div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ───────────────────────────────────────────────────────────────────────
gv = "Yes ✓" if price >= 2_000_000 else "No ✗"
st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card"><div class="kpi-val">{fmt(r['mortgage'])}/mo</div><div class="kpi-lbl">Monthly mortgage</div></div>
  <div class="kpi-card"><div class="kpi-val">{fmt(r['upfront'])}</div><div class="kpi-lbl">Upfront cost (incl. DLD fees)</div></div>
  <div class="kpi-card"><div class="kpi-val">{gross_yield:.1f}%</div><div class="kpi-lbl">Gross rental yield</div></div>
  <div class="kpi-card"><div class="kpi-val">{fmt(r['equity'])}</div><div class="kpi-lbl">Est. equity after 10 yrs</div></div>
  <div class="kpi-card"><div class="kpi-val">{fmt(r['prop_val'])}</div><div class="kpi-lbl">Est. property value 10 yrs</div></div>
  <div class="kpi-card"><div class="kpi-val">{gv}</div><div class="kpi-lbl">Golden Visa eligible</div></div>
</div>
""", unsafe_allow_html=True)

# ── Cost bars ──────────────────────────────────────────────────────────────────
mx       = max(r["ownership_cost"], r["rent_cumulative"])
buy_pct  = int(r["ownership_cost"]  / mx * 100)
rent_pct = int(r["rent_cumulative"] / mx * 100)

st.markdown(f"""
<div class="bar-section">
  <div class="bar-title">10-Year Cost of Ownership vs Renting</div>
  <div class="bar-note" style="margin-bottom:14px; color:#8a9bb5;">
    Buying bar = extra costs only (what you pay beyond the property price itself).
    Property price and down payment are NOT included — you own the asset at the end.
  </div>

  <div class="bar-row">
    <div class="bar-label">🟢 Cost of buying</div>
    <div class="bar-track"><div class="bar-fill-buy" style="width:{buy_pct}%"></div></div>
    <div class="bar-val">{fmt(r["ownership_cost"])}</div>
  </div>
  <div class="bar-note" style="margin-bottom:14px; margin-left:172px;">
    DLD fee {fmt(r["dld_fee"])}
    + Agent {fmt(r["agent_fee"])}
    + Reg AED 4,200
    + 10-yr mortgage interest {fmt(r["total_interest"])}
    + 10-yr service charge {fmt(r["total_service"])}
  </div>

  <div class="bar-row">
    <div class="bar-label">🔴 Cost of renting</div>
    <div class="bar-track"><div class="bar-fill-rent" style="width:{rent_pct}%"></div></div>
    <div class="bar-val">{fmt(r["rent_cumulative"])}</div>
  </div>
  <div class="bar-note" style="margin-left:172px;">
    10 years of rent · starts AED {annual_rent:,}/yr · increases {ri_pct}% annually · nothing owned at the end
  </div>

  <div class="bar-note" style="margin-top:14px; padding-top:12px; border-top:1px solid rgba(201,168,76,0.15); color:#C9A84C;">
    After 10 years: buyer owns a property worth {fmt(r["prop_val"])} with {fmt(r["equity"])} in equity.
    Renter owns nothing.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Full breakdown ─────────────────────────────────────────────────────────────
with st.expander("📊 Full cost breakdown & 10-year projection"):
    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown("**Upfront buying costs**")
        st.write(f"Down payment ({dp_pct}%): AED {round(price * dp_pct/100):,}")
        st.write(f"DLD transfer fee (4%): AED {r['dld_fee']:,}")
        st.write(f"Agent commission (2%): AED {r['agent_fee']:,}")
        st.write(f"Registration fee: AED 4,200")
        st.write(f"**Total upfront: AED {r['upfront']:,}**")
        st.markdown("---")
        st.write(f"Monthly mortgage: AED {r['mortgage']:,}")
        st.write(f"Annual service charge: AED {r['service_charge']:,}")
        st.write(f"Gross rental yield: {gross_yield:.1f}%")
    with bc2:
        st.markdown("**Year-by-year projection**")
        st.dataframe(
            pd.DataFrame(r["yearly"]).set_index("Year"),
            use_container_width=True
        )

st.markdown("---")

# ── Lead capture ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="lead-box">
  <div class="lead-title">Get Your Free Personalised Property Report</div>
  <div class="lead-sub">
    Based on your inputs, I'll send you a detailed analysis with DLD comparables,
    area market data, and my personal recommendation as a Dubai real estate expert.
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

with st.form("lead_form", clear_on_submit=True):
    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        lead_name  = st.text_input("Your Name *",         placeholder="Ahmed Al Mansouri")
    with lc2:
        lead_email = st.text_input("Email Address *",     placeholder="ahmed@email.com")
    with lc3:
        lead_phone = st.text_input("WhatsApp / Phone *",  placeholder="+971 50 123 4567")

    submitted = st.form_submit_button("Get My Free Property Report")
    if submitted:
        if not lead_name or not lead_email or not lead_phone:
            st.error("Please fill in all three fields.")
        else:
            ts      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            be_text = f"Year {r['be_year']}" if r["be_year"] else "No break-even in 10 yrs"
            lead    = {
                "name": lead_name, "email": lead_email, "phone": lead_phone,
                "community": community, "beds": beds, "size_sqft": size_sqft,
                "price": price, "annual_rent": annual_rent, "verdict": verdict_str,
                "breakeven": be_text, "mortgage": r["mortgage"], "timestamp": ts,
            }
            save_lead([ts, lead_name, lead_email, lead_phone, community, beds,
                       size_sqft, price, annual_rent, verdict_str, be_text, r["mortgage"]])
            send_email(lead)
            st.success(
                f"Thank you {lead_name.split()[0]}! Your request is received. "
                f"Rahul will contact you within 24 hours on {lead_phone}."
            )

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#2a3548;font-size:0.75rem;'>"
    "Built by Rahul Verma · Dubai Real Estate Agent & Python Developer · "
    "Data: DLD transactions + Bayut API + DLD Rental Index 2026</p>",
    unsafe_allow_html=True
)