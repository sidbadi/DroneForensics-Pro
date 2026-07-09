import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import json
import pydeck as pdk
import io
import math
import re
import sys
import ipaddress
import contextlib
import zipfile
import os
import tempfile
import urllib.parse
import urllib.request
import csv
from datetime import datetime, timedelta
import logging
import xml.etree.ElementTree as ET

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.cluster import DBSCAN
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except Exception:
    IsolationForest = None
    RandomForestClassifier = None
    DBSCAN = None
    TfidfVectorizer = None
    SKLEARN_AVAILABLE = False

try:
    from pymavlink import mavutil
    logging.getLogger('MAVLink').setLevel(logging.ERROR) # Suppress verbose pymavlink warnings like "bad header"
    PYMAVLINK_AVAILABLE = True
except Exception:
    mavutil = None
    PYMAVLINK_AVAILABLE = False

import hashlib

def calculate_sha256(file_bytes):
    """Calculates the SHA-256 hash of uploaded file bytes for forensic integrity."""
    hasher = hashlib.sha256()
    hasher.update(file_bytes)
    return hasher.hexdigest()

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DroneForensics Pro",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Rajdhani', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #0d1526 50%, #0a1020 100%);
        color: #c8d8e8;
    }

    .main-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
        background: linear-gradient(90deg, transparent, rgba(0,180,255,0.05), transparent);
        border-bottom: 1px solid rgba(0,180,255,0.2);
        margin-bottom: 2rem;
    }

    .main-header h1 {
        font-family: 'Orbitron', monospace;
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(90deg, #00b4ff, #00ffcc, #00b4ff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 4px;
        margin: 0;
        text-shadow: none;
        animation: shine 3s linear infinite;
    }

    @keyframes shine {
        to { background-position: 200% center; }
    }

    .main-header p {
        color: #6a8aaa;
        font-size: 1rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-top: 0.5rem;
    }

    .metric-card {
        background: linear-gradient(135deg, rgba(0,30,60,0.8), rgba(0,20,45,0.9));
        border: 1px solid rgba(0,180,255,0.25);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin: 0.4rem 0;
        box-shadow: 0 4px 20px rgba(0,100,200,0.1), inset 0 1px 0 rgba(255,255,255,0.05);
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00b4ff, transparent);
    }

    .metric-label {
        font-size: 0.72rem;
        color: #4a7a9a;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-family: 'Orbitron', monospace;
        margin-bottom: 0.3rem;
    }

    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        font-family: 'Orbitron', monospace;
        color: #00e5ff;
        line-height: 1;
    }

    .metric-unit {
        font-size: 0.8rem;
        color: #4a8aaa;
        margin-left: 4px;
    }

    .section-header {
        font-family: 'Orbitron', monospace;
        font-size: 1rem;
        color: #00b4ff;
        text-transform: uppercase;
        letter-spacing: 3px;
        padding: 0.8rem 0 0.5rem 0;
        border-bottom: 1px solid rgba(0,180,255,0.2);
        margin: 1.5rem 0 1rem 0;
    }

    .halt-card {
        background: rgba(255,80,80,0.05);
        border: 1px solid rgba(255,80,80,0.25);
        border-left: 3px solid #ff5050;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }

    .halt-card .halt-id {
        font-family: 'Orbitron', monospace;
        font-size: 0.75rem;
        color: #ff8080;
        letter-spacing: 2px;
        margin-bottom: 0.4rem;
    }

    .halt-coord {
        color: #aac8e0;
        font-size: 0.88rem;
        margin: 2px 0;
    }

    .halt-duration {
        font-family: 'Orbitron', monospace;
        font-size: 1.1rem;
        color: #ff6060;
        margin-top: 0.3rem;
    }

    .upload-area {
        border: 2px dashed rgba(0,180,255,0.3);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: rgba(0,30,60,0.3);
        margin: 1rem 0;
    }

    .stButton > button {
        background: linear-gradient(135deg, #003366, #004488);
        color: #00e5ff;
        border: 1px solid rgba(0,180,255,0.4);
        border-radius: 8px;
        font-family: 'Orbitron', monospace;
        font-size: 0.75rem;
        letter-spacing: 2px;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #004488, #0055aa);
        border-color: #00b4ff;
        box-shadow: 0 0 20px rgba(0,180,255,0.3);
    }

    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-family: 'Orbitron', monospace;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .badge-active { background: rgba(0,255,100,0.15); color: #00ff64; border: 1px solid rgba(0,255,100,0.3); }
    .badge-halt   { background: rgba(255,80,80,0.15);  color: #ff5050; border: 1px solid rgba(255,80,80,0.3); }
    .badge-info   { background: rgba(0,180,255,0.15); color: #00b4ff; border: 1px solid rgba(0,180,255,0.3); }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #060c18 0%, #080f1e 100%);
        border-right: 1px solid rgba(0,180,255,0.15);
    }

    .sidebar-logo {
        font-family: 'Orbitron', monospace;
        font-size: 1.1rem;
        color: #00b4ff;
        letter-spacing: 3px;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 1px solid rgba(0,180,255,0.2);
        margin-bottom: 1rem;
    }

    .stDataFrame { border: 1px solid rgba(0,180,255,0.2); border-radius: 8px; }

    .stAlert { border-radius: 8px; }

    .format-tag {
        display: inline-block;
        background: rgba(0,180,255,0.1);
        border: 1px solid rgba(0,180,255,0.3);
        color: #00b4ff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-family: 'Orbitron', monospace;
        margin: 2px;
    }

    .leaflet-control-attribution {
        font-size: 9px !important;
        line-height: 1.1 !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        opacity: 0.45 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🛸 DRONE FORENSICS PRO</h1>
    <p>Flight Path Analysis &amp; Intelligence System</p>
</div>
""", unsafe_allow_html=True)

# ─── Helpers ────────────────────────────────────────────────────────────────

LAT_ALIASES = [
    "lat", "latitude", "Lat", "LAT",
    "gps_lat", "GPS_lat",
    "LatDeg", "lat_deg",
    "position_lat",
    "GLOBAL_POSITION_INT.lat",
    "GPS.Lat"
]

LON_ALIASES = [
    "lon", "lng", "longitude", "Lon", "LON",
    "gps_lon", "GPS_lon",
    "LonDeg", "lon_deg",
    "position_lon",
    "GLOBAL_POSITION_INT.lon",
    "GPS.Lng"
]

ALT_ALIASES = [
    "alt", "altitude", "Alt",
    "relative_alt",
    "height",
    "GPS.Alt"
]

TIME_ALIASES = [
    "time", "timestamp", "Time",
    "datetime",
    "DateTime",
    "GPS.Time"
]

COLUMN_ALIASES = {
    'latitude': LAT_ALIASES,
    'longitude': LON_ALIASES,
    'altitude': ALT_ALIASES,
    'speed': ['speed', 'velocity', 'groundspeed', 'OSD.groundOrVerticalSpeed',
              'GPS.speed', 'VFR_HUD.groundspeed', 'Speed', 'ground_speed'],
    'time': TIME_ALIASES,
}

LOCAL_COORD_ALIASES = {
    'pos_x': ['pos_x', 'x', 'position_x', 'local_x', 'X', 'east',  'e'],
    'pos_y': ['pos_y', 'y', 'position_y', 'local_y', 'Y', 'north', 'n'],
    'pos_z': ['pos_z', 'z', 'position_z', 'local_z', 'Z', 'up',    'u'],
}

# Reference origin for converting local XY (metres) → GPS degrees
# Uses centre of India as a safe default; overridden per-session if user sets one
DEFAULT_ORIGIN_LAT = 20.5937
DEFAULT_ORIGIN_LON = 78.9629

DRONE_MODELS = [
    "Generic / Unknown",
    "DJI Mavic 3",
    "DJI Air 3",
    "DJI Mini 4 Pro",
    "DJI Phantom 4 Pro",
    "Autel EVO II Pro",
    "Parrot Anafi",
    "Skydio 2+",
    "Custom / Other",
]

MODEL_MAX_SPEED_MPS = {
    "Generic / Unknown": 25.0,
    "DJI Mavic 3": 21.0,
    "DJI Air 3": 21.0,
    "DJI Mini 4 Pro": 16.0,
    "DJI Phantom 4 Pro": 20.0,
    "Autel EVO II Pro": 20.0,
    "Parrot Anafi": 15.0,
    "Skydio 2+": 16.0,
    "Custom / Other": 25.0,
}

@st.cache_data(ttl=3600, show_spinner=False)
def detect_ip_geolocation():
    """Best-effort IP-based geolocation for initial origin defaults."""
    try:
        req = urllib.request.Request(
            "http://ip-api.com/json/",
            headers={"User-Agent": "Mozilla/5.0 DroneForensics/1.0"},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        if data.get("status") == "success":
            lat = float(data.get("lat"))
            lon = float(data.get("lon"))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
    except Exception:
        pass
    return None, None

def local_xy_to_latlon(x_m, y_m, origin_lat, origin_lon):
    """Convert local X/Y metres offsets to lat/lon degrees."""
    lat = origin_lat + (y_m / 111320.0)
    lon = origin_lon + (x_m / (111320.0 * math.cos(math.radians(origin_lat))))
    return lat, lon

def detect_local_coord_col(df, field):
    cols_lower = {c.lower(): c for c in df.columns}
    for alias in LOCAL_COORD_ALIASES[field]:
        if alias.lower() in cols_lower:
            return cols_lower[alias.lower()]
    return None

def detect_column(df, field):
    cols_lower = {c.lower(): c for c in df.columns}
    for alias in COLUMN_ALIASES[field]:
        if alias.lower() in cols_lower:
            return cols_lower[alias.lower()]
    return None

def parse_csv(file):
    content = file.read().decode('utf-8', errors='ignore')
    file.seek(0)
    sample = "\n".join(content.splitlines()[:30])

    # Try common delimiters first, then whitespace-delimited text logs.
    delimiter_candidates = [',', '\t', ';', '|']
    best_df = None
    best_score = -1

    for sep in delimiter_candidates:
        try:
            df = pd.read_csv(
                io.StringIO(content),
                sep=sep,
                low_memory=False,
                engine='python'
            )
            score = (0 if df is None else len(df.columns)) + (0 if df is None else min(len(df), 100))
            if df is not None and score > best_score and len(df.columns) >= 2:
                best_df = df
                best_score = score
        except Exception:
            continue

    # Fallback for whitespace-separated text files.
    if best_df is None:
        try:
            df_ws = pd.read_csv(
                io.StringIO(content),
                sep=r'\s+',
                low_memory=False,
                engine='python'
            )
            if df_ws is not None and len(df_ws.columns) >= 2:
                best_df = df_ws
        except Exception:
            pass

    return best_df

def parse_kml(file):
    tree = ET.parse(file)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    coords_text = ''
    for elem in root.iter():
        if 'coordinates' in elem.tag:
            coords_text = elem.text.strip()
            break
    rows = []
    for i, c in enumerate(coords_text.split()):
        parts = c.split(',')
        if len(parts) >= 2:
            try:
                row = {'longitude': float(parts[0]), 'latitude': float(parts[1]),
                       'altitude': float(parts[2]) if len(parts) > 2 else 0.0,
                       'time': i}
                rows.append(row)
            except ValueError:
                continue
    return pd.DataFrame(rows) if rows else None

def parse_kmz(file):
    with zipfile.ZipFile(file) as z:
        for name in z.namelist():
            if name.endswith(".kml"):
                with z.open(name) as f:
                    return parse_kml(f)
    return None

def parse_gpx(file):
    tree = ET.parse(file)
    root = tree.getroot()
    ns_uri = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
    rows = []
    tag_ele = f'{{{ns_uri}}}ele' if ns_uri else 'ele'
    tag_time = f'{{{ns_uri}}}time' if ns_uri else 'time'

    point_tags = []
    for tag in ('trkpt', 'rtept', 'wpt'):
        point_tags.append(f'{{{ns_uri}}}{tag}' if ns_uri else tag)

    i = 0
    for point_tag in point_tags:
        for pt in root.iter(point_tag):
            try:
                lat = float(pt.attrib.get('lat'))
                lon = float(pt.attrib.get('lon'))
            except (TypeError, ValueError):
                continue

            alt = 0.0
            alt_el = pt.find(tag_ele)
            if alt_el is not None and alt_el.text:
                try:
                    alt = float(alt_el.text)
                except ValueError:
                    alt = 0.0

            time_el = pt.find(tag_time)
            t = time_el.text if (time_el is not None and time_el.text) else str(i)
            rows.append({'latitude': lat, 'longitude': lon, 'altitude': alt, 'time': t})
            i += 1
    return pd.DataFrame(rows) if rows else None

def parse_json(file):
    data = json.load(file)
    if isinstance(data, list):
        return pd.DataFrame(data)
    elif isinstance(data, dict):
        for key in ['data', 'points', 'path', 'records', 'waypoints']:
            if key in data and isinstance(data[key], list):
                return pd.DataFrame(data[key])
        return pd.DataFrame([data])
    return None

def parse_param(file):
    params = {}

    try:
        file.seek(0)
    except Exception:
        pass

    for raw in file:
        try:
            line = raw.decode('utf-8', errors='ignore').strip()
        except Exception:
            continue
        if not line or line.startswith('#'):
            continue
        if "," in line:
            k, v = line.split(",", 1)
            params[k.strip()] = v.strip()

    return {
        "type": "param",
        "params": params,
        "telemetry": None
    } if params else None

def detect_file_type(filename):
    name = str(filename).lower()

    if name.endswith(".csv"):
        return "csv"

    if name.endswith(".gpx"):
        return "gpx"

    if name.endswith(".kml"):
        return "kml"

    if name.endswith(".kmz"):
        return "kmz"

    if name.endswith(".xml"):
        return "xml"

    if name.endswith(".param"):
        return "param"

    if name.endswith(".bin"):
        return "bin"

    if name.endswith(".log"):
        return "log"

    if name.endswith(".txt"):
        return "txt"

    return "unknown"

def _scaled_latlon(value):
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if abs(v) > 180:
        v = v / 1e7
    if -180 <= v <= 180:
        return v
    return None

def _msg_time(msg, fallback_idx):
    for key in ("TimeUS", "time_usec", "usec"):
        val = getattr(msg, key, None)
        if val is not None:
            try:
                return float(val) / 1e6
            except Exception:
                pass
    for key in ("time_boot_ms", "TimeMS", "GMS"):
        val = getattr(msg, key, None)
        if val is not None:
            try:
                return float(val) / 1e3
            except Exception:
                pass
    return float(fallback_idx)

def parse_bin(file):
    if not PYMAVLINK_AVAILABLE:
        return None, "pymavlink is not installed, cannot parse BIN files."

    data_list = []
    tmp_path = None
    mlog = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        mlog = mavutil.mavlink_connection(tmp_path, robust_decode=True)
        while True:
            try:
                msg = mlog.recv_match(type=['GPS', 'ATT', 'BARO', 'MSG'], blocking=False)
                if msg is None:
                    break
                msg_dict = msg.to_dict()
                msg_dict['msg_type'] = msg.get_type()
                data_list.append(msg_dict)
            except Exception:
                continue

        if not data_list:
            return None, "No MAVLink messages with GPS, ATT, BARO, or MSG types found."

        df = pd.DataFrame(data_list)

        # ArduPilot stores lat/lon as integers scaled by 1e7
        for col in df.columns:
            if any(k in col.lower() for k in ('lat', 'lng', 'lon')):
                numeric = pd.to_numeric(df[col], errors='coerce')
                if numeric.dropna().abs().max() > 180:
                    df[col] = numeric / 1e7

        return df, None
    except Exception as e:
        return None, f"Error processing BIN file with pymavlink: {e}"
    finally:
        if mlog is not None:
            try:
                mlog.close()
            except Exception:
                pass
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def load_csv(file):
    return parse_csv(file)

def parse_txt(file):
    return parse_csv(file)

def parse_ardupilot_log_hardened(file_content):
    data = []
    # ArduPilot logs: GPS rows with fix status and coordinates.
    for line in file_content.splitlines():
        if line.startswith('GPS,'):
            parts = line.split(',')
            try:
                # 1. Check Fix Status (must be 3 for 3D Fix)
                if int(parts[1]) >= 3:
                    lat = float(parts[6])
                    lng = float(parts[7])
                    alt = float(parts[8])

                    # 2. Handle integer scaling if applicable
                    if abs(lat) > 180:
                        lat /= 1.0e7
                    if abs(lng) > 180:
                        lng /= 1.0e7

                    # 3. Final sanity check: ignore (0,0)
                    if lat != 0 and lng != 0:
                        data.append({
                            'latitude': lat,
                            'longitude': lng,
                            'altitude': alt,
                        })
            except (ValueError, IndexError):
                continue

    df = pd.DataFrame(data)

    # 4. Smoothing: take every 5th point to reduce jitter
    if not df.empty:
        df = df.iloc[::5, :].reset_index(drop=True)
        df['time'] = range(len(df))

    return df

def parse_log(file):
    try:
        content = file.read().decode('utf-8', errors='ignore')
        file.seek(0)
    except Exception:
        return parse_csv(file)

    df_ap = parse_ardupilot_log_hardened(content)
    if df_ap is not None and len(df_ap) > 0:
        return df_ap
    return parse_csv(file)

def parse_xml(file):
    import xml.etree.ElementTree as ET

    # Try parameter-style XML first.
    try:
        tree = ET.parse(file)
        root = tree.getroot()
        data = {}
        for p in root.iter("param"):
            name = p.attrib.get("name")
            value = p.attrib.get("value")
            if name is not None:
                data[name] = value
        if data:
            return {
                "type": "xml",
                "params": data,
                "telemetry": None
            }
    except Exception:
        pass

    # Fallback for GPX/KML-like XML telemetry.
    try:
        file.seek(0)
    except Exception:
        pass
    df = parse_gpx(file)
    if df is not None:
        return df
    try:
        file.seek(0)
    except Exception:
        pass
    return parse_kml(file)

def load_file(file):
    ftype = detect_file_type(getattr(file, "name", ""))

    if ftype == "csv":
        return load_csv(file)

    if ftype == "gpx":
        return parse_gpx(file)

    if ftype == "kml":
        return parse_kml(file)

    if ftype == "kmz":
        return parse_kmz(file)

    if ftype == "xml":
        return parse_xml(file)

    if ftype == "param":
        return parse_param(file)

    if ftype == "bin":
        df, err = parse_bin(file)
        if err:
            raise RuntimeError(err)
        return df

    if ftype == "log":
        return parse_log(file)

    if ftype == "txt":
        return parse_txt(file)

    # Backward-compat for types not handled by detect_file_type helper.
    name = str(getattr(file, "name", "")).lower()
    if name.endswith((".xls", ".xlsx")):
        return pd.read_excel(file)
    if name.endswith(".json"):
        return parse_json(file)
    return None

class NamedBytesIO(io.BytesIO):
    """Bytes buffer with a file-like name attribute."""
    def __init__(self, data, name):
        super().__init__(data)
        self.name = name

def _direct_download_url(url):
    """Convert common share URLs to direct-download URLs when possible."""
    parsed = urllib.parse.urlparse(url)

    # Google Drive: /file/d/<id>/view -> uc?export=download&id=<id>
    if "drive.google.com" in parsed.netloc:
        m = re.search(r"/file/d/([^/]+)", parsed.path)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Dropbox: force dl=1
    if "dropbox.com" in parsed.netloc:
        q = urllib.parse.parse_qs(parsed.query)
        q["dl"] = ["1"]
        new_query = urllib.parse.urlencode(q, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    return url

def fetch_file_from_url(url, timeout=30, max_size_mb=100):
    """Download remote telemetry file and return a file-like object."""
    direct_url = _direct_download_url(url.strip())
    req = urllib.request.Request(
        direct_url,
        headers={"User-Agent": "Mozilla/5.0 DroneForensics/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if len(data) > max_size_mb * 1024 * 1024:
            raise ValueError(f"File is too large (>{max_size_mb} MB).")

        final_url = getattr(resp, "geturl", lambda: direct_url)()
        content_type = (resp.headers.get("Content-Type", "") or "").lower()
        filename = ""
        content_disp = resp.headers.get("Content-Disposition", "")
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^\";]+)"?', content_disp)
        if m:
            filename = urllib.parse.unquote(m.group(1))
        if not filename:
            filename = urllib.parse.unquote(
                urllib.parse.urlparse(final_url).path.split("/")[-1]
            )
        if not filename:
            filename = "remote_flight_log.csv"

    if "." not in filename:
        if "json" in content_type:
            filename += ".json"
        elif "kml" in content_type:
            filename += ".kml"
        elif "gpx" in content_type:
            filename += ".gpx"
        elif "excel" in content_type or "spreadsheet" in content_type:
            filename += ".xlsx"
        else:
            filename += ".csv"

    return NamedBytesIO(data, filename)

def _first_public_ip(candidates):
    for raw_ip in candidates:
        if not raw_ip:
            continue
        token = str(raw_ip).split(",")[0].strip().split(":")[0].strip()
        try:
            ip_obj = ipaddress.ip_address(token)
            if not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local):
                return token
        except ValueError:
            continue
    return None

def detect_origin_from_ip(timeout=4):
    """Estimate origin coordinates from IP geolocation providers."""
    header_candidates = []
    try:
        headers = dict(st.context.headers)
    except Exception:
        headers = {}

    for key in ["X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP", "Forwarded"]:
        if key in headers:
            header_candidates.append(headers.get(key))

    ip_hint = _first_public_ip(header_candidates)

    providers = []
    if ip_hint:
        providers.append((f"https://ipapi.co/{ip_hint}/json/", "ipapi.co"))
        providers.append((f"https://ipwho.is/{ip_hint}", "ipwho.is"))
    providers.append(("https://ipapi.co/json/", "ipapi.co"))
    providers.append(("https://ipwho.is/", "ipwho.is"))

    for url, provider in providers:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DroneForensics/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))

            if provider == "ipapi.co":
                lat = payload.get("latitude")
                lon = payload.get("longitude")
            else:
                if payload.get("success") is False:
                    continue
                lat = payload.get("latitude")
                lon = payload.get("longitude")

            if lat is None or lon is None:
                continue
            lat = float(lat)
            lon = float(lon)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, provider
        except Exception:
            continue

    return None, None, None

def normalise(df, origin_lat=DEFAULT_ORIGIN_LAT, origin_lon=DEFAULT_ORIGIN_LON):
    if df is None or len(df) == 0:
        return None, {}, False

    # lowercase columns
    df = df.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    LAT_ALIASES = [
        "lat", "latitude", "latdeg", "gps_lat",
        "position_lat", "y", "lat_deg"
    ]

    LON_ALIASES = [
        "lon", "lng", "longitude", "londeg", "gps_lon",
        "position_lon", "x", "lon_deg"
    ]

    ALT_ALIASES = [
        "alt", "altitude", "height", "z", "relative_alt"
    ]

    TIME_ALIASES = [
        "time", "timestamp", "datetime", "date", "timeus"
    ]

    def find_col(aliases):
        for a in aliases:
            if a in df.columns:
                return a
        return None

    lat_col = find_col(LAT_ALIASES)
    lon_col = find_col(LON_ALIASES)
    alt_col = find_col(ALT_ALIASES)
    time_col = find_col(TIME_ALIASES)
    speed_col = find_col(["speed", "velocity", "groundspeed", "gps_speed"])

    if lat_col is None or lon_col is None:
        return None, {}, False

    out = {}
    out["latitude"] = pd.to_numeric(df[lat_col], errors="coerce")
    out["longitude"] = pd.to_numeric(df[lon_col], errors="coerce")
    out["altitude"] = pd.to_numeric(df[alt_col], errors="coerce") if alt_col else 0
    out["time"] = df[time_col] if time_col else range(len(df))
    out["speed"] = pd.to_numeric(df[speed_col], errors="coerce") if speed_col else np.nan

    out_df = pd.DataFrame(out)
    out_df["altitude"] = pd.to_numeric(out_df["altitude"], errors="coerce").fillna(0)
    out_df = out_df.dropna(subset=["latitude", "longitude"])
    out_df = out_df[(out_df["latitude"].between(-90, 90)) & (out_df["longitude"].between(-180, 180))]
    out_df = out_df.reset_index(drop=True)

    col_map = {
        "latitude": lat_col,
        "longitude": lon_col,
        "altitude": alt_col or "generated",
        "time": time_col or "generated",
    }
    return out_df, col_map, False

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def compute_speed_from_coords(df):
    speeds = [0.0]
    for i in range(1, len(df)):
        d = haversine(df.iloc[i-1]['latitude'], df.iloc[i-1]['longitude'],
                      df.iloc[i]['latitude'],   df.iloc[i]['longitude'])
        speeds.append(d)  # meters per point (approx)
    return speeds

def detect_halts(df, speed_threshold=0.5, min_points=3):
    halts = []
    if 'speed' in df.columns and df['speed'].notna().sum() > 10:
        is_halt = df['speed'] < speed_threshold
    else:
        dist = compute_speed_from_coords(df)
        is_halt = pd.Series([d < 2.0 for d in dist])

    in_halt = False
    start_idx = 0
    for i, h in enumerate(is_halt):
        if h and not in_halt:
            in_halt = True
            start_idx = i
        elif not h and in_halt:
            in_halt = False
            if i - start_idx >= min_points:
                seg = df.iloc[start_idx:i]
                halts.append({
                    'start_idx': start_idx,
                    'end_idx': i,
                    'points': len(seg),
                    'lat': seg['latitude'].mean(),
                    'lon': seg['longitude'].mean(),
                    'alt': seg['altitude'].mean() if 'altitude' in seg.columns else 0,
                    'duration_pts': i - start_idx,
                })
    if in_halt and len(df) - start_idx >= min_points:
        seg = df.iloc[start_idx:]
        halts.append({
            'start_idx': start_idx, 'end_idx': len(df),
            'points': len(seg),
            'lat': seg['latitude'].mean(), 'lon': seg['longitude'].mean(),
            'alt': seg['altitude'].mean() if 'altitude' in seg.columns else 0,
            'duration_pts': len(df) - start_idx,
        })
    return halts

def turn_delta_deg(prev_bearing, next_bearing):
    """Smallest absolute turn angle between two bearings."""
    return abs((next_bearing - prev_bearing + 180) % 360 - 180)

def detect_anomalies(
    df,
    halts,
    max_expected_speed=25.0,
    altitude_jump_threshold=15.0,
    hover_min_points=15,
    sharp_turn_threshold=120.0,
    gps_jump_threshold_m=150.0,
    loop_window=20,
    loop_turn_sum_threshold=540.0,
    loop_disp_threshold_m=40.0,
):
    """Detect core flight anomalies and return grouped events plus a flat report."""
    anomalies = {
        'speed': [],
        'altitude': [],
        'hover': [],
        'direction': [],
        'gps': [],
        'loop': [],
    }

    if len(df) < 2:
        return anomalies, pd.DataFrame()

    coords = list(zip(df['latitude'].tolist(), df['longitude'].tolist()))
    point_dist_m = [0.0]
    bearings = [None]
    for i in range(1, len(df)):
        lat1, lon1 = coords[i - 1]
        lat2, lon2 = coords[i]
        point_dist_m.append(haversine(lat1, lon1, lat2, lon2))
        bearings.append(bearing_degrees(lat1, lon1, lat2, lon2))

    for i, s in enumerate(pd.to_numeric(df['speed'], errors='coerce').fillna(0)):
        if s > max_expected_speed:
            anomalies['speed'].append({
                'index': i,
                'latitude': df.iloc[i]['latitude'],
                'longitude': df.iloc[i]['longitude'],
                'details': f"Speed {s:.1f} m/s exceeds expected {max_expected_speed:.1f} m/s",
            })

    alt_series = pd.to_numeric(df['altitude'], errors='coerce').fillna(0)
    for i in range(1, len(df)):
        delta_alt = alt_series.iloc[i] - alt_series.iloc[i - 1]
        if abs(delta_alt) >= altitude_jump_threshold:
            direction = "climb" if delta_alt > 0 else "drop"
            anomalies['altitude'].append({
                'index': i,
                'latitude': df.iloc[i]['latitude'],
                'longitude': df.iloc[i]['longitude'],
                'details': f"Sudden {direction}: {delta_alt:+.1f} m between points",
            })

    for h in halts:
        if h['points'] >= hover_min_points:
            anomalies['hover'].append({
                'index': h['start_idx'],
                'latitude': h['lat'],
                'longitude': h['lon'],
                'details': f"Extended hover for {h['points']} points ({h['duration_str']})",
            })

    for i in range(2, len(df)):
        if point_dist_m[i] < 1.0 or point_dist_m[i - 1] < 1.0:
            continue
        if bearings[i] is None or bearings[i - 1] is None:
            continue
        turn = turn_delta_deg(bearings[i - 1], bearings[i])
        if turn >= sharp_turn_threshold:
            anomalies['direction'].append({
                'index': i,
                'latitude': df.iloc[i]['latitude'],
                'longitude': df.iloc[i]['longitude'],
                'details': f"Sharp turn {turn:.1f} deg exceeds {sharp_turn_threshold:.0f} deg",
            })

    for i in range(1, len(df)):
        if point_dist_m[i] >= gps_jump_threshold_m:
            anomalies['gps'].append({
                'index': i,
                'latitude': df.iloc[i]['latitude'],
                'longitude': df.iloc[i]['longitude'],
                'details': f"Coordinate jump {point_dist_m[i]:.1f} m exceeds {gps_jump_threshold_m:.1f} m",
            })

    flagged_windows = set()
    w = max(6, min(loop_window, len(df) - 1))
    for start in range(0, len(df) - w):
        end = start + w
        path_len = sum(point_dist_m[start + 1:end + 1])
        disp = haversine(df.iloc[start]['latitude'], df.iloc[start]['longitude'],
                         df.iloc[end]['latitude'], df.iloc[end]['longitude'])

        turn_sum = 0.0
        for j in range(start + 2, end + 1):
            if bearings[j] is None or bearings[j - 1] is None:
                continue
            turn_sum += turn_delta_deg(bearings[j - 1], bearings[j])

        if turn_sum >= loop_turn_sum_threshold and disp <= loop_disp_threshold_m and path_len > 3 * max(disp, 1.0):
            anchor = int((start + end) / 2)
            if anchor in flagged_windows:
                continue
            flagged_windows.add(anchor)
            anomalies['loop'].append({
                'index': anchor,
                'latitude': df.iloc[anchor]['latitude'],
                'longitude': df.iloc[anchor]['longitude'],
                'details': f"Possible circling: turn sum {turn_sum:.0f} deg, displacement {disp:.1f} m",
            })

    rows = []
    for anomaly_type, events in anomalies.items():
        for event in events:
            rows.append({
                'type': anomaly_type,
                'point_index': event['index'],
                'latitude': event['latitude'],
                'longitude': event['longitude'],
                'details': event['details'],
            })
    report_df = pd.DataFrame(rows)
    return anomalies, report_df

def build_ml_features(df):
    """Build richer features for unsupervised flight behavior modelling."""
    work = df.copy().reset_index(drop=True)
    speed = pd.to_numeric(work['speed'], errors='coerce').fillna(0.0)
    altitude = pd.to_numeric(work['altitude'], errors='coerce').fillna(0.0)
    vertical_speed = altitude.diff().fillna(0.0)
    hover_flag = (speed < 0.5).astype(int)
    acceleration = speed.diff().fillna(0.0)

    # Vectorized haversine and bearing for performance
    lats = work['latitude'].values
    lons = work['longitude'].values
    
    lat1, lon1 = lats[:-1], lons[:-1]
    lat2, lon2 = lats[1:], lons[1:]
    
    # Step distance
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlam = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2)**2
    step_dist = np.concatenate([[0.0], R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))])
    
    # Bearings
    x = np.sin(dlam) * np.cos(phi2)
    y = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlam)
    bearings = np.concatenate([[0.0], (np.degrees(np.arctan2(x, y)) + 360) % 360])

    step_dist = pd.Series(step_dist, index=work.index)
    bearings = pd.Series(bearings, index=work.index)
    turn_angle = bearings.diff().fillna(0).apply(lambda x: abs((x + 180) % 360 - 180))
    curvature = turn_angle / (step_dist + 0.001)

    # Rolling context helps model persistent patterns beyond single-point spikes.
    speed_roll_mean = speed.rolling(window=5, min_periods=1).mean()
    speed_roll_std = speed.rolling(window=5, min_periods=1).std().fillna(0.0)
    alt_roll_mean = altitude.rolling(window=5, min_periods=1).mean()
    dist_roll_sum = step_dist.rolling(window=5, min_periods=1).sum()

    features = pd.DataFrame({
        'speed': speed,
        'altitude': altitude,
        'vertical_speed': vertical_speed,
        'hover_flag': hover_flag,
        'acceleration': acceleration,
        'turn_angle': turn_angle,
        'curvature': curvature,
        'step_dist': step_dist,
        'speed_roll_mean': speed_roll_mean,
        'speed_roll_std': speed_roll_std,
        'alt_roll_mean': alt_roll_mean,
        'dist_roll_sum': dist_roll_sum,
    }).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return features

def detect_anomalies_ml(
    df,
    contamination=0.03,
    training_features=None,
    training_texts=None,
    max_train_rows=50000,
    max_text_rows=50000,
    halt_speed_threshold=0.5,
):
    """Simplified ML: IsolationForest trained on flight behavior history."""
    if (not SKLEARN_AVAILABLE) or len(df) < 20:
        return [], pd.DataFrame(), pd.DataFrame(), []

    work = df.copy().reset_index(drop=True)
    features = build_ml_features(work)
    feature_cols = list(features.columns)

    train_features = features
    if training_features is not None and len(training_features) > 0:
        hist = training_features.reindex(columns=feature_cols, fill_value=0.0)
        train_features = pd.concat([hist, features], ignore_index=True).tail(max_train_rows)

    events = []
    try:
        model = IsolationForest(n_estimators=200, contamination=float(contamination), random_state=42)
        model.fit(train_features)
        pred = model.predict(features)
        scores = -model.decision_function(features)

        for i, p in enumerate(pred):
            if p == -1:
                events.append({
                    'index': i,
                    'latitude': work.iloc[i]['latitude'],
                    'longitude': work.iloc[i]['longitude'],
                    'details': f"ML Anomaly: Deviating flight pattern (score {scores[i]:.4f})",
                })
    except Exception:
        pass

    current_texts = []  # Placeholder for future compatibility

    rows = [{
        'type': 'ml',
        'point_index': e['index'],
        'latitude': e['latitude'],
        'longitude': e['longitude'],
        'details': e['details'],
    } for e in events]
    return events, pd.DataFrame(rows), features, current_texts

def estimate_duration(halts, df, time_col_present):
    """Attach human-readable duration to each halt."""
    for h in halts:
        if time_col_present and 'time' in df.columns:
            try:
                t_start = pd.to_datetime(df.iloc[h['start_idx']]['time'], errors='coerce')
                t_end   = pd.to_datetime(df.iloc[min(h['end_idx'], len(df)-1)]['time'], errors='coerce')
                if pd.notna(t_start) and pd.notna(t_end):
                    delta = abs((t_end - t_start).total_seconds())
                    h['duration_str'] = f"{int(delta//60)}m {int(delta%60)}s"
                    h['duration_sec'] = delta
                    continue
            except Exception:
                pass
        h['duration_str'] = f"~{h['duration_pts']} data points"
        h['duration_sec'] = h['duration_pts']
    return halts

# ─── Build Map ───────────────────────────────────────────────────────────────

def bearing_degrees(lat1, lon1, lat2, lon2):
    """Calculate compass bearing from point 1 to point 2 (degrees, 0=North)."""
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def bearing_to_label(bearing):
    """Convert bearing degrees to compass direction label."""
    dirs = ['N','NE','E','SE','S','SW','W','NW','N']
    return dirs[round(bearing / 45) % 8]

def offset_latlon(lat, lon, distance_m, bearing_deg):
    """Offset lat/lon by distance (m) along a bearing (deg)."""
    d_lat = (distance_m * math.cos(math.radians(bearing_deg))) / 111320.0
    d_lon = (distance_m * math.sin(math.radians(bearing_deg))) / (
        111320.0 * max(math.cos(math.radians(lat)), 1e-6)
    )
    return lat + d_lat, lon + d_lon

def build_map(
    df, halts, anomalies,
    show_heatmap, show_path, show_halts, show_points, show_anomalies,
    show_arrows=True, arrow_density=10,
    map_zoom_level=18, spread_halt_markers=True, halt_spread_m=8
):
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        tiles=None,
        control_scale=True
    )

    # Single basemap: satellite + labels overlay
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=False
    ).add_to(m)

    # Labels overlay on top of satellite (like Google Maps)
    folium.TileLayer(
        tiles='https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Labels',
        overlay=True,
        control=True,
        opacity=1.0
    ).add_to(m)

    coords = list(zip(df['latitude'], df['longitude']))

    # Heat map
    if show_heatmap and len(coords) > 0:
        heat_data = [[r['latitude'], r['longitude']] for _, r in df.iterrows()]
        HeatMap(heat_data, radius=12, blur=10, max_zoom=1,
                gradient={0.2: 'blue', 0.5: 'cyan', 0.7: 'lime', 0.9: 'yellow', 1.0: 'red'},
                name='Heat Map').add_to(m)

    # Flight path: static polyline
    if show_path and len(coords) > 1:
        path_coords = df[['latitude', 'longitude']].values.tolist()
        folium.PolyLine(
            locations=path_coords,
            color='#00b4ff',
            weight=4,
            opacity=0.8
        ).add_to(m)

    # Direction arrows
    if show_arrows and len(coords) > 1:
        arrow_group = folium.FeatureGroup(name='Direction Arrows')
        # Place an arrow every N points, but always include the last segment
        step = max(1, len(coords) // max(arrow_density, 1))
        indices = list(range(0, len(coords) - 1, step))
        if (len(coords) - 2) not in indices:
            indices.append(len(coords) - 2)

        for idx in indices:
            lat1, lon1 = coords[idx]
            lat2, lon2 = coords[idx + 1]
            mid_lat = (lat1 + lat2) / 2
            mid_lon = (lon1 + lon2) / 2
            brng = bearing_degrees(lat1, lon1, lat2, lon2)
            compass = bearing_to_label(brng)

            # Folium DivIcon arrow — rotates with bearing
            arrow_html = f"""
            <div style="
                width:0; height:0;
                border-left: 7px solid transparent;
                border-right: 7px solid transparent;
                border-bottom: 18px solid #00ffcc;
                transform: rotate({brng}deg);
                transform-origin: center bottom;
                filter: drop-shadow(0 0 4px rgba(0,255,200,0.7));
            "></div>"""

            folium.Marker(
                location=[mid_lat, mid_lon],
                icon=folium.DivIcon(
                    html=arrow_html,
                    icon_size=(14, 18),
                    icon_anchor=(7, 9),
                ),
                tooltip=f"Bearing: {brng:.1f}° ({compass})"
            ).add_to(arrow_group)

        arrow_group.add_to(m)

    # Individual data points
    if show_points and len(df) <= 2000:
        point_group = folium.FeatureGroup(name='Data Points')
        for _, row in df.iterrows():
            spd = f"{row['speed']:.1f} m/s" if pd.notna(row.get('speed')) else "N/A"
            alt = f"{row['altitude']:.1f} m"  if pd.notna(row.get('altitude')) else "N/A"
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=3, color='#00b4ff', fill=True, fill_opacity=0.6,
                popup=folium.Popup(
                    f"<b>Lat:</b> {row['latitude']:.6f}<br>"
                    f"<b>Lon:</b> {row['longitude']:.6f}<br>"
                    f"<b>Alt:</b> {alt}<br>"
                    f"<b>Speed:</b> {spd}", max_width=200)
            ).add_to(point_group)
        point_group.add_to(m)

    # Path Numbering (0 -> End)
    # Start Point (0)
    folium.Marker(
        location=[df.iloc[0]['latitude'], df.iloc[0]['longitude']],
        icon=folium.DivIcon(html=f"""<div style="font-family:'Rajdhani',sans-serif; background:#00ff88; color:#000; border-radius:50%; width:24px; height:24px; display:flex; justify-content:center; align-items:center; font-weight:bold; border:2px solid #fff; box-shadow:0 2px 5px rgba(0,0,0,0.5);">0</div>"""),
        tooltip="Start (Point 0)"
    ).add_to(m)

    # End Point (N)
    last_idx = len(df) - 1
    folium.Marker(
        location=[df.iloc[-1]['latitude'], df.iloc[-1]['longitude']],
        icon=folium.DivIcon(html=f"""<div style="font-family:'Rajdhani',sans-serif; background:#ff0055; color:#fff; border-radius:50%; width:24px; height:24px; display:flex; justify-content:center; align-items:center; font-weight:bold; border:2px solid #fff; box-shadow:0 2px 5px rgba(0,0,0,0.5);">{last_idx}</div>"""),
        tooltip=f"End (Point {last_idx})"
    ).add_to(m)

    # Intermediate numbered markers (every ~10% of points) to track path
    if len(df) > 20:
        step = max(10, len(df) // 10)
        for i in range(step, last_idx, step):
             folium.Marker(
                location=[df.iloc[i]['latitude'], df.iloc[i]['longitude']],
                icon=folium.DivIcon(html=f"""<div style="font-family:'Rajdhani',sans-serif; background:#ffffff; color:#333; border-radius:50%; width:20px; height:20px; display:flex; justify-content:center; align-items:center; font-weight:bold; font-size:10px; border:1px solid #999; box-shadow:0 1px 3px rgba(0,0,0,0.3);">{i}</div>"""),
                tooltip=f"Point {i}"
            ).add_to(m)

    # Anomaly markers
    if show_anomalies and anomalies:
        anomaly_colors = {
            'speed': '#ff00ff',      # magenta
            'altitude': '#ff8c00',   # orange
            'hover': '#00ffff',      # cyan
            'direction': '#ffd700',  # gold
            'gps': '#ff0000',        # red
            'loop': '#7fff00',       # chartreuse
        }
        anomaly_names = {
            'speed': 'Speed',
            'altitude': 'Altitude',
            'hover': 'Hover',
            'direction': 'Direction',
            'gps': 'GPS',
            'loop': 'Looping',
        }
        anomaly_group = folium.FeatureGroup(name='Anomaly Points')
        for anomaly_type, events in anomalies.items():
            if anomaly_type == 'ml':
                continue
            for event in events:
                lat = event.get('latitude')
                lon = event.get('longitude')
                if pd.isna(lat) or pd.isna(lon):
                    continue
                label = anomaly_names.get(anomaly_type, anomaly_type.title())
                color = anomaly_colors.get(anomaly_type, '#ff00ff')
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=7,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.85,
                    weight=2,
                    tooltip=f"{label} anomaly",
                    popup=folium.Popup(
                        f"<b>{label} anomaly</b><br>"
                        f"<b>Point:</b> {event.get('index', 'N/A')}<br>"
                        f"<b>Details:</b> {event.get('details', '')}",
                        max_width=280
                    )
                ).add_to(anomaly_group)
        anomaly_group.add_to(m)

    return m

def render_3d_view(df):
    view_df = df.copy()

    # Standardize column names to lowercase for easier matching
    view_df.columns = [str(c).lower() for c in view_df.columns]
    
    # Auto-detect Latitude
    lat_col = next((c for c in view_df.columns if c in ['lat', 'latitude', 'gps.lat', 'pos_y']), None)
    # Auto-detect Longitude
    lon_col = next((c for c in view_df.columns if c in ['lon', 'lng', 'longitude', 'gps.lng', 'pos_x']), None)
    
    if lat_col and lon_col:
        # Rename them so PyDeck knows what to look for
        view_df = view_df.rename(columns={lat_col: 'latitude', lon_col: 'longitude'})
    else:
        st.error("Could not find GPS columns in your file. Please check column headers.")
        return

    # Ensure altitude exists
    if 'altitude' not in view_df.columns:
        view_df['altitude'] = 0

    # 1. Prepare data for PyDeck (Lat/Lon/Alt)
    chart_data = view_df[['latitude', 'longitude', 'altitude']].to_dict('records')

    # 2. Define the 3D Block Layer
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=chart_data,
        get_position=["longitude", "latitude"],
        get_elevation="altitude",
        elevation_scale=5,
        radius=3,
        get_fill_color=[0, 180, 255, 140], # Forensic Blue
        pickable=True,
        auto_highlight=True,
    )

    # 3. Set the Map View (Pitch is required to see 3D height)
    view_state = pdk.ViewState(
        latitude=view_df['latitude'].mean(),
        longitude=view_df['longitude'].mean(),
        zoom=15,
        pitch=45,  # Tilts the map so you can see the 'blocks'
        bearing=0
    )

    # 4. Render with a standard style (No Mapbox Token Required)
    st.pydeck_chart(pdk.Deck(
        map_style='light', # Use 'light', 'dark', or 'road'
        initial_view_state=view_state,
        layers=[column_layer],
        tooltip={"text": "Altitude: {altitude}m"},
        width="stretch"
    ))

# ─── Sample Data Generator ──────────────────────────────────────────────────

def generate_sample_data(origin_lat=DEFAULT_ORIGIN_LAT, origin_lon=DEFAULT_ORIGIN_LON):
    np.random.seed(42)
    n = 300
    t = np.linspace(0, 4*np.pi, n)
    base_lat, base_lon = origin_lat, origin_lon
    lat = base_lat + 0.005 * np.sin(t) + np.cumsum(np.random.randn(n)*0.0002)
    lon = base_lon + 0.005 * np.cos(t) + np.cumsum(np.random.randn(n)*0.0002)
    alt = 100 + 20*np.sin(t/2) + np.random.randn(n)*2
    speed = np.abs(5 + 3*np.cos(t) + np.random.randn(n)*0.5)
    # inject halts
    for halt_region in [(60,75), (150,165), (230,248)]:
        speed[halt_region[0]:halt_region[1]] = 0.1
    base_time = datetime(2024, 6, 15, 10, 0, 0)
    times = [base_time + timedelta(seconds=i*2) for i in range(n)]
    df = pd.DataFrame({
        'latitude': lat, 'longitude': lon, 'altitude': alt,
        'speed': speed, 'time': times
    })
    return df

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="sidebar-logo">🛸 DRONE FORENSICS</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">📁 Data Source</div>', unsafe_allow_html=True)

    selected_drone_model = st.selectbox(
        "Drone Model",
        options=DRONE_MODELS,
        index=0,
        help="Select the drone platform used for this flight log.",
    )
    custom_drone_model = ""
    if selected_drone_model == "Custom / Other":
        custom_drone_model = st.text_input(
            "Custom Drone Model",
            placeholder="Enter manufacturer and model",
        )
    drone_model = custom_drone_model.strip() or selected_drone_model

    if "origin_lat" not in st.session_state or "origin_lon" not in st.session_state:
        lat, lon, source = detect_origin_from_ip()
        if lat is None or lon is None:
            lat2, lon2 = detect_ip_geolocation()
            if lat2 is not None and lon2 is not None:
                lat, lon, source = lat2, lon2, "ip-api.com"

        if lat is not None and lon is not None:
            st.session_state["origin_lat"] = lat
            st.session_state["origin_lon"] = lon
            st.session_state["origin_geo_message"] = (
                f"Initial origin auto-detected from network location ({source}): {lat:.4f}, {lon:.4f}."
            )
        else:
            st.session_state["origin_lat"] = DEFAULT_ORIGIN_LAT
            st.session_state["origin_lon"] = DEFAULT_ORIGIN_LON
            st.session_state["origin_geo_message"] = (
                "Could not auto-detect location. Using default origin; update manually if needed."
            )
    if "origin_geo_message" not in st.session_state:
        st.session_state["origin_geo_message"] = ""

    use_sample = st.checkbox("Use Sample Flight Data", value=False, key="use_sample")

    if not use_sample:
        st.markdown("""
        <div style='font-size:0.78rem; color:#4a7a9a; margin-bottom:0.5rem;'>
        Supported formats:<br>
        <span class='format-tag'>CSV</span>
        <span class='format-tag'>TSV</span>
        <span class='format-tag'>XLSX</span>
        <span class='format-tag'>KML</span>
        <span class='format-tag'>KMZ</span>
        <span class='format-tag'>GPX</span>
        <span class='format-tag'>JSON</span>
        <span class='format-tag'>LOG</span>
        <span class='format-tag'>PARAM</span>
        <span class='format-tag'>BIN</span>
        </div>
        """, unsafe_allow_html=True)
        uploaded_file = st.sidebar.file_uploader(
            "Upload Drone Flight Log / Telemetry File",
            type=["csv", "txt", "xlsx", "kml", "gpx", "json", "log", "bin"]
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            file_hash = calculate_sha256(file_bytes)
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 🛡️ Forensic Chain of Custody")
            st.sidebar.text_input("File Name:", value=uploaded_file.name, disabled=True)
            st.sidebar.text_input("SHA-256 Evidence Hash:", value=file_hash, disabled=True)
            st.sidebar.caption("💡 Match this hash against your local copy to verify zero-tampering.")
            st.sidebar.markdown("---")

        uploaded = uploaded_file
        file_url = st.text_input(
            "or Paste Direct File URL",
            placeholder="https://.../flight_log.csv",
            help="Provide a direct download link (CSV/Excel/KML/GPX/JSON).",
        )
    else:
        uploaded = None
        file_url = ""

    st.markdown('<div class="section-header">📍 Local Coord Origin</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.75rem;color:#4a7a9a;margin-bottom:0.5rem;">Set only if your file uses pos_x/pos_y (metres) instead of GPS lat/lon. This is the real-world GPS location of your drone\'s takeoff/home point.</div>', unsafe_allow_html=True)
    if st.session_state["origin_geo_message"]:
        st.caption(st.session_state["origin_geo_message"])
    origin_lat = st.number_input("Origin Latitude", key="origin_lat", format="%.6f")
    origin_lon = st.number_input("Origin Longitude", key="origin_lon", format="%.6f")

    st.markdown('<div class="section-header">⚙️ Analysis Settings</div>', unsafe_allow_html=True)

    halt_threshold = st.slider("Halt Speed Threshold (m/s)", 0.0, 5.0, 0.5, 0.1,
                               help="Points below this speed are considered halts")
    min_halt_pts   = st.slider("Min Points for Halt", 2, 20, 3,
                               help="Minimum consecutive slow-points to call a halt")

    st.markdown('<div class="section-header">🗺️ Map Layers</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Anomaly Settings</div>', unsafe_allow_html=True)
    model_speed_default = MODEL_MAX_SPEED_MPS.get(selected_drone_model, 25.0)
    max_expected_speed = st.slider(
        "Expected Max Speed (m/s)",
        5.0, 50.0, float(model_speed_default), 0.5,
        help="Speed above this threshold is flagged as anomaly.",
    )
    altitude_jump_threshold = st.slider(
        "Altitude Jump Threshold (m)",
        2.0, 100.0, 15.0, 1.0,
        help="Point-to-point climb/drop above this is flagged.",
    )
    hover_min_points = st.slider(
        "Hover Anomaly Min Points",
        3, 200, 15,
        help="Halt events with at least this many points are flagged.",
    )
    sharp_turn_threshold = st.slider(
        "Sharp Turn Threshold (deg)",
        45, 180, 120, 5,
        help="Direction change above this angle is flagged.",
    )
    gps_jump_threshold_m = st.slider(
        "GPS Jump Threshold (m)",
        10.0, 2000.0, 150.0, 10.0,
        help="Consecutive coordinate jump above this is flagged.",
    )
    loop_window = st.slider(
        "Loop Window (points)",
        6, 120, 20, 1,
        help="Sliding window size used to identify circling behavior.",
    )
    ml_contamination = st.slider(
        "ML Contamination",
        0.005, 0.20, 0.03, 0.005,
        help="Estimated fraction of outliers for ML detection.",
    )
    ml_history_limit = 20000
    if not SKLEARN_AVAILABLE:
        st.warning("scikit-learn not installed. ML mode will return no results.")

    show_heatmap = st.checkbox("Heat Map",    value=True)
    show_path    = st.checkbox("Flight Path", value=True)
    show_arrows  = st.checkbox("Direction Arrows", value=True)
    arrow_density = st.slider("Arrow Density", 5, 50, 15,
                              help="Number of direction arrows shown along the path") if show_arrows else 15
    show_halts   = st.checkbox("Halt Points", value=True)
    spread_halt_markers = st.checkbox("Spread Overlapping Halt Markers", value=True)
    halt_spread_m = st.slider("Halt Marker Spread (m)", 2, 30, 8, 1) if spread_halt_markers else 0
    map_zoom_level = st.slider("Detail Zoom Level", 14, 22, 18, 1)
    show_anomalies = st.checkbox("Anomaly Points", value=True)
    show_points  = st.checkbox("Data Points (≤2000 pts)", value=False)

    # ─── Feedback Section ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">💬 Feedback</div>', unsafe_allow_html=True)
    with st.expander("Help us improve"):
        fb_name = st.text_input("Name (Optional)", key="fb_name")
        fb_rating = st.select_slider("Rating", options=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"], value="⭐⭐⭐⭐⭐")
        fb_text = st.text_area("Comments / Suggestions", placeholder="Tell us what features you'd like to see next...")
        
        if st.button("Submit Feedback", use_container_width=True):
            if fb_text.strip():
                feedback_file = "user_feedback.csv"
                file_exists = os.path.isfile(feedback_file)
                try:
                    with open(feedback_file, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Timestamp", "Name", "Rating", "Comments"])
                        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fb_name, fb_rating, fb_text])
                    st.success("Thank you! Your feedback has been saved.")
                except Exception as e:
                    st.error(f"Error saving feedback: {e}")
            else:
                st.warning("Please enter your comments before submitting.")

# ─── Main Logic ──────────────────────────────────────────────────────────────

df_raw = None
parse_error = None
source_ready = use_sample or (uploaded is not None) or bool(file_url.strip())
if use_sample:
    source_signature = f"sample:{origin_lat:.6f}:{origin_lon:.6f}"
elif uploaded is not None:
    source_signature = f"upload:{uploaded.name}:{getattr(uploaded, 'size', 0)}"
elif file_url.strip():
    source_signature = f"url:{file_url.strip()}"
else:
    source_signature = "none"

if st.session_state.get("analysis_source_signature") != source_signature:
    st.session_state["analysis_source_signature"] = source_signature
    st.session_state["analysis_started"] = False

if source_ready and not st.session_state.get("analysis_started", False):
    st.info("Source ready. Click **Start Analysis** to begin.")
    if st.button("Start Analysis", type="primary", width="stretch"):
        st.session_state["analysis_started"] = True

if source_ready and st.session_state.get("analysis_started", False) and use_sample:
    df_raw = generate_sample_data(origin_lat=origin_lat, origin_lon=origin_lon)
    st.info(f"📡 Using built-in sample flight data (anchored near {origin_lat:.4f}, {origin_lon:.4f}, 300 points)")
elif source_ready and st.session_state.get("analysis_started", False) and uploaded is not None:
    with st.spinner("Parsing flight log…"):
        try:
            df_raw = load_file(uploaded)
        except Exception as e:
            parse_error = f"Unable to parse uploaded file: {e}"
elif source_ready and st.session_state.get("analysis_started", False) and file_url.strip():
    with st.spinner("Downloading and parsing flight log from link..."):
        try:
            remote_file = fetch_file_from_url(file_url)
            df_raw = load_file(remote_file)
            st.info(f"Loaded file from URL: {remote_file.name}")
        except Exception as e:
            parse_error = f"Unable to load file from URL: {e}"

if source_ready and st.session_state.get("analysis_started", False) and df_raw is None and parse_error is None:
    if uploaded is not None and uploaded.name.lower().endswith(".gpx"):
        parse_error = (
            "This GPX file contains no GPS points (`trkpt`/`rtept`/`wpt`). "
            "Please export a GPX with track points."
        )
    elif uploaded is not None and uploaded.name.lower().endswith(".bin"):
        parse_error = (
            "Could not extract telemetry from BIN. Ensure `pymavlink` is installed, "
            "or export BIN to CSV/GPX/KML from your flight tool."
        )
    elif uploaded is not None and uploaded.name.lower().endswith(".param"):
        parse_error = (
            "PARAM files usually contain configuration only, not full flight path telemetry. "
            "Upload the corresponding log/track file (BIN/LOG/GPX/CSV/KML)."
        )
    else:
        parse_error = "No usable telemetry points were found in the selected source."

if parse_error:
    st.error(parse_error)

data = df_raw
if data is None:
    pass
elif isinstance(data, dict) and data.get("telemetry") is None:
    src_type = str(data.get("type", "data")).upper()
    st.info(f"{src_type}: No GPS telemetry, showing metadata.")
    params = data.get("params", {})
    if params:
        with st.expander(f"{src_type} Parameters"):
            st.dataframe(
                pd.DataFrame([{"param": k, "value": v} for k, v in params.items()]),
                width="stretch",
                hide_index=True
            )
    df_raw = None
else:
    df_raw = data if isinstance(data, pd.DataFrame) else data.get("telemetry")

if df_raw is not None:
    df, col_map, used_local = normalise(df_raw, origin_lat=origin_lat, origin_lon=origin_lon)

    if df is None:
        st.warning("⚠️ No GPS coordinates found — displaying available metadata instead.")

        # ── Metadata KPIs ────────────────────────────────────────────────
        st.markdown('<div class="section-header">📋 File Metadata</div>', unsafe_allow_html=True)

        total_rows = len(df_raw)
        total_cols = len(df_raw.columns)
        numeric_cols = df_raw.select_dtypes(include='number').columns.tolist()
        text_cols    = df_raw.select_dtypes(exclude='number').columns.tolist()

        mk1, mk2, mk3, mk4 = st.columns(4)
        def mkpi(col, label, value):
            col.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value" style="font-size:1.4rem">{value}</div></div>', unsafe_allow_html=True)
        mkpi(mk1, "Total Records",   f"{total_rows:,}")
        mkpi(mk2, "Total Columns",   str(total_cols))
        mkpi(mk3, "Numeric Columns", str(len(numeric_cols)))
        mkpi(mk4, "Text Columns",    str(len(text_cols)))

        # ── Column Summary ───────────────────────────────────────────────
        st.markdown('<div class="section-header">🔬 Column Analysis</div>', unsafe_allow_html=True)
        summary_rows = []
        for col in df_raw.columns:
            s = df_raw[col]
            is_num = pd.api.types.is_numeric_dtype(s)
            summary_rows.append({
                "Column":    col,
                "Type":      "Numeric" if is_num else "Text",
                "Non-Null":  int(s.notna().sum()),
                "Null":      int(s.isna().sum()),
                "Unique":    int(s.nunique()),
                "Min":       f"{s.min():.4g}" if is_num else "-",
                "Max":       f"{s.max():.4g}" if is_num else "-",
                "Mean":      f"{s.mean():.4g}" if is_num else "-",
                "Sample":    str(s.dropna().iloc[0]) if s.notna().any() else "",
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        # ── Numeric Charts ───────────────────────────────────────────────
        if numeric_cols:
            st.markdown('<div class="section-header">📈 Numeric Data Profiles</div>', unsafe_allow_html=True)
            chart_cols = numeric_cols[:6]  # cap at 6 to avoid clutter
            tabs = st.tabs(chart_cols)
            for tab, col in zip(tabs, chart_cols):
                with tab:
                    series = pd.to_numeric(df_raw[col], errors='coerce').dropna().reset_index(drop=True)
                    if len(series) > 0:
                        st.line_chart(series, height=200, use_container_width=True)
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Min",  f"{series.min():.4g}")
                        c2.metric("Max",  f"{series.max():.4g}")
                        c3.metric("Mean", f"{series.mean():.4g}")
                        c4.metric("Std",  f"{series.std():.4g}")

        # ── Raw Data Preview ─────────────────────────────────────────────
        with st.expander("🔍 Raw Data Preview (first 100 rows)"):
            st.dataframe(df_raw.head(100), use_container_width=True, height=300)

        # ── Export metadata ──────────────────────────────────────────────
        with st.expander("💾 Export Metadata"):
            st.download_button(
                "⬇ Download Full Data (CSV)",
                data=df_raw.to_csv(index=False),
                file_name="drone_metadata.csv",
                mime="text/csv"
            )

        st.info("💡 No GPS columns (lat/lon) were detected. If your file uses local coordinates like `pos_x`/`pos_y`, set the **Origin Latitude/Longitude** in the sidebar.")
    else:
        st.caption(f"Drone Model: {drone_model}")
        if used_local:
            st.warning(f"📍 **Local coordinates detected** — `pos_x`/`pos_y` converted to GPS using origin ({origin_lat:.4f}°, {origin_lon:.4f}°). Set the correct takeoff location in the sidebar for accurate map placement.")
        # Debug: show raw BIN columns if it was a BIN file
        if uploaded is not None and uploaded.name.lower().endswith('.bin'):
            with st.expander("🔍 BIN Debug: Raw columns & sample values"):
                st.write("**Raw columns:**", list(df_raw.columns))
                st.dataframe(df_raw.head(3))
        time_col_present = 'time' in col_map or 'time' in df.columns

        # Compute missing speed from coordinates
        if df['speed'].isna().all():
            dists = compute_speed_from_coords(df)
            df['speed'] = dists

        halts = detect_halts(df, speed_threshold=halt_threshold, min_points=min_halt_pts)
        halts = estimate_duration(halts, df, time_col_present)
        rule_anomalies, rule_anomaly_df = detect_anomalies(
            df, halts,
            max_expected_speed=max_expected_speed,
            altitude_jump_threshold=altitude_jump_threshold,
            hover_min_points=hover_min_points,
            sharp_turn_threshold=sharp_turn_threshold,
            gps_jump_threshold_m=gps_jump_threshold_m,
            loop_window=loop_window,
        )
        history_features = st.session_state.get("ml_feature_history", pd.DataFrame())
        history_texts = st.session_state.get("ml_text_history", [])
        ml_events, ml_anomaly_df, current_features, current_texts = detect_anomalies_ml(
            df,
            contamination=ml_contamination,
            training_features=history_features,
            training_texts=history_texts,
            max_train_rows=ml_history_limit,
            max_text_rows=ml_history_limit,
            halt_speed_threshold=halt_threshold,
        )
        if not current_features.empty:
            combined_history = pd.concat([history_features, current_features], ignore_index=True)
            st.session_state["ml_feature_history"] = combined_history.tail(ml_history_limit)
        if current_texts:
            merged_texts = (history_texts + current_texts)[-ml_history_limit:]
            st.session_state["ml_text_history"] = merged_texts

        # Fixed hybrid engine (rule + ML) for best overall coverage.
        anomalies = {k: list(v) for k, v in rule_anomalies.items()}
        anomalies['ml'] = ml_events
        anomaly_df = pd.concat([rule_anomaly_df, ml_anomaly_df], ignore_index=True)

        total_anomalies = sum(len(v) for v in anomalies.values())
        hist_rows = len(st.session_state.get("ml_feature_history", []))
        text_rows = len(st.session_state.get("ml_text_history", []))
        st.caption(f"ML backend memory: structured {hist_rows:,} rows | unstructured {text_rows:,} text rows")

        # Vectorized distance calculation for performance and stability
        lats = df['latitude'].values
        lons = df['longitude'].values
        phi1, phi2 = np.radians(lats[:-1]), np.radians(lats[1:])
        dphi, dlam = np.radians(np.diff(lats)), np.radians(np.diff(lons))
        a = np.sin(dphi/2.0)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2.0)**2
        total_dist = np.sum(6371000 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0-a)))

        # Calculate 3D Distance from Home (Point 0)
        home_lat = df.iloc[0]['latitude']
        home_lon = df.iloc[0]['longitude']
        home_alt = df.iloc[0]['altitude']
        # Approximation for performance: Haversine 2D + Alt diff
        df['dist_home_2d'] = df.apply(lambda row: haversine(home_lat, home_lon, row['latitude'], row['longitude']), axis=1)
        df['dist_home_3d'] = np.sqrt(df['dist_home_2d']**2 + (df['altitude'] - home_alt)**2)

        # ── KPI Row ──────────────────────────────────────────────────────────
        st.markdown('<div class="section-header">📊 Flight Summary</div>', unsafe_allow_html=True)
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        def kpi(col, label, value, unit=""):
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}<span class="metric-unit">{unit}</span></div>
            </div>""", unsafe_allow_html=True)

        kpi(k1, "Total Points", f"{len(df):,}")
        kpi(k2, "Halt Events",  str(len(halts)))
        kpi(k3, "Anomalies",    str(total_anomalies))
        kpi(k4, "Max Altitude", f"{df['altitude'].max():.0f}", "m")
        kpi(k5, "Max Speed",    f"{df['speed'].max():.1f}",   "m/s")
        kpi(k6, "Est. Distance",f"{total_dist/1000:.2f}",     "km")

        max_range = df['dist_home_3d'].max()
        if max_range > 500:
            st.warning(f"⚠️ Max Range from Home: {max_range:.1f} m (Potential BVLOS > 500m)")

        # ── Map ──────────────────────────────────────────────────────────────
        st.markdown('<div class="section-header">🗺️ Flight Visualization</div>', unsafe_allow_html=True)
        
        map_tab, cube_tab = st.tabs(["🗺️ 2D Map", "🧊 3D Cube View"])

        with map_tab:
            st.subheader("2D Flight Path")
            with st.spinner("Rendering map…"):
                fmap = build_map(
                    df, halts, anomalies,
                    show_heatmap, show_path, show_halts, show_points, show_anomalies,
                    show_arrows, arrow_density,
                    map_zoom_level, spread_halt_markers, halt_spread_m
                )
            st_folium(fmap, width=None, height=600, returned_objects=[])

        with cube_tab:
            st.subheader("3D Forensic View")
            render_3d_view(df)

        # ── Two-column bottom section ─────────────────────────────────────
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown('<div class="section-header">⏸ Halt Analysis</div>', unsafe_allow_html=True)
            if halts:
                for i, h in enumerate(halts):
                    st.markdown(f"""
                    <div class="halt-card">
                        <div class="halt-id">▶ HALT EVENT #{i+1}</div>
                        <div class="halt-coord">🌐 Lat: <b>{h['lat']:.6f}°</b></div>
                        <div class="halt-coord">🌐 Lon: <b>{h['lon']:.6f}°</b></div>
                        <div class="halt-coord">⬆ Alt: <b>{h['alt']:.1f} m</b></div>
                        <div class="halt-duration">⏱ {h['duration_str']}</div>
                        <div class="halt-coord" style="margin-top:4px">📍 {h['points']} data points</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No halts detected with current threshold settings.")

        with col_right:
            st.markdown('<div class="section-header">📈 Speed & Altitude Profile</div>', unsafe_allow_html=True)
            chart_df = df[['speed', 'altitude', 'dist_home_3d']].copy().reset_index()
            chart_df.columns = ['Point', 'Speed (m/s)', 'Altitude (m)', 'Range (m)']
            tab1, tab2, tab3 = st.tabs(["Speed", "Altitude", "Range from Home"])
            with tab1:
                st.line_chart(chart_df.set_index('Point')['Speed (m/s)'], height=250, width="stretch")
            with tab2:
                st.line_chart(chart_df.set_index('Point')['Altitude (m)'], height=250, width="stretch")
            with tab3:
                st.line_chart(chart_df.set_index('Point')['Range (m)'], height=250, width="stretch")

        # ── Raw Data Table ────────────────────────────────────────────────
        st.markdown('<div class="section-header">Anomaly Detection</div>', unsafe_allow_html=True)
        anomaly_labels = {
            'speed': "Speed anomaly: Drone moving faster than expected",
            'altitude': "Altitude anomaly: Sudden climb/drop",
            'hover': "Hover anomaly: Drone stays too long at one location",
            'direction': "Direction anomaly: Sudden sharp turns",
            'gps': "GPS anomaly: Impossible jump in coordinates",
            'loop': "Looping pattern: Drone circling repeatedly",
            'ml': "ML anomaly: Outlier pattern detected",
        }
        for k in ['speed', 'altitude', 'hover', 'direction', 'gps', 'loop', 'ml']:
            count = len(anomalies.get(k, []))
            if count > 0:
                st.warning(f"{anomaly_labels[k]} ({count})")
            else:
                st.info(f"{anomaly_labels[k]} (0)")

        if not anomaly_df.empty:
            with st.expander("Anomaly Event Table"):
                st.dataframe(
                    anomaly_df.head(500),
                    width="stretch",
                    height=280,
                    hide_index=True,
                )
                if len(anomaly_df) > 500:
                    st.caption(f"Showing first 500 of {len(anomaly_df):,} anomaly events.")

        with st.expander("🔍 Raw Flight Data Table"):
            display_cols = ['latitude', 'longitude', 'altitude', 'speed']
            if 'time' in df.columns:
                display_cols = ['time'] + display_cols
            st.dataframe(
                df[display_cols].round(6).head(500),
                width="stretch",
                height=300
            )
            if len(df) > 500:
                st.caption(f"Showing first 500 of {len(df):,} records.")

        # ── Export ────────────────────────────────────────────────────────
        with st.expander("💾 Export Analysis"):
            export_df = df[['latitude','longitude','altitude','speed']].copy()
            if 'time' in df.columns:
                export_df.insert(0, 'time', df['time'])
            if halts:
                halt_df = pd.DataFrame([{
                    'halt_id': i+1, 'latitude': h['lat'], 'longitude': h['lon'],
                    'altitude': h['alt'], 'duration': h['duration_str'],
                    'data_points': h['points']
                } for i, h in enumerate(halts)])
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.download_button("⬇ Download Full Log (CSV)",
                        data=export_df.to_csv(index=False),
                        file_name="drone_flight_log.csv", mime="text/csv")
                with col_e2:
                    st.download_button("⬇ Download Halt Report (CSV)",
                        data=halt_df.to_csv(index=False),
                        file_name="drone_halt_report.csv", mime="text/csv")
            else:
                st.download_button("⬇ Download Full Log (CSV)",
                    data=export_df.to_csv(index=False),
                    file_name="drone_flight_log.csv", mime="text/csv")

            if not anomaly_df.empty:
                st.download_button("Download Anomaly Report (CSV)",
                    data=anomaly_df.to_csv(index=False),
                    file_name="drone_anomaly_report.csv", mime="text/csv")

else:
    # ── Landing / Welcome Screen ─────────────────────────────────────────
    st.markdown("""
    <div style='text-align:center; padding: 3rem 1rem; color: #4a7a9a;'>
        <div style='font-size: 5rem; margin-bottom: 1rem;'>🛸</div>
        <div style='font-family: Orbitron, monospace; font-size: 1.3rem; color: #00b4ff; letter-spacing: 3px; margin-bottom: 1rem;'>
            AWAITING FLIGHT DATA
        </div>
        <div style='font-size: 1rem; max-width: 600px; margin: 0 auto; line-height: 1.8;'>
            Upload a drone flight log file or enable <b>Sample Data</b> in the sidebar to begin forensic analysis.
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, icon, title, desc in [
        (c1, "🗺️", "Heat Map Analysis", "Visualise flight density and hotspots on an interactive map"),
        (c2, "⏸", "Halt Detection",     "Automatically detect and time every hover/stop event"),
        (c3, "📊", "Speed & Altitude",   "Full telemetry charts with GPS coordinates for every point"),
    ]:
        col.markdown(f"""
        <div class="metric-card" style="text-align:center; padding: 2rem 1rem;">
            <div style="font-size:2.5rem; margin-bottom:0.8rem;">{icon}</div>
            <div style="font-family:Orbitron,monospace; font-size:0.85rem; color:#00b4ff; letter-spacing:2px; margin-bottom:0.5rem;">{title}</div>
            <div style="font-size:0.88rem; color:#5a8aaa;">{desc}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📋 Supported File Formats</div>', unsafe_allow_html=True)
    fmt_data = {
        "Format": ["CSV / TSV", "Excel (.xlsx)", "KML", "GPX", "JSON", "DJI Logs", "ArduPilot .log"],
        "Extension": [".csv / .txt", ".xlsx / .xls", ".kml", ".gpx", ".json", ".csv / .txt", ".log / .csv"],
        "Auto-detected columns": [
            "lat, lon, alt, speed, time (any naming)",
            "Same as CSV",
            "coordinates tag (lon,lat,alt)",
            "trkpt lat/lon/ele/time",
            "Any JSON array of objects",
            "OSD.latitude, OSD.longitude, GPS.*",
            "GLOBAL_POSITION_INT, VFR_HUD, GPS"
        ]
    }
    st.dataframe(pd.DataFrame(fmt_data), width="stretch", hide_index=True)
