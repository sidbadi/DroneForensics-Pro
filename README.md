# 🛸 DroneForensics Pro — Setup Guide

## Quick Start

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
streamlit run drone_forensics_app.py
```

The app will open automatically in your browser at `http://localhost:8501`

---

## Features
- **Heat Map** — Visualise flight density using Folium + OpenStreetMap (no API key needed)
- **Flight Path** — Animated ant-path showing direction of travel
- **Halt Detection** — Auto-detects hover/stop events with GPS coordinates, altitude & duration
- **Anomaly Detection** — Flags speed spikes, sudden altitude jumps, long hovers, sharp turns, GPS jumps, and looping patterns
- **Speed & Altitude Charts** — Full telemetry profile across the flight
- **Forensic Stats** — Total distance, max speed, max altitude, halt count
- **Export** — Download full log + halt report as CSV

## Supported Input Formats
| Format | Extension |
|--------|-----------|
| CSV / TSV | `.csv`, `.txt` |
| Excel | `.xlsx`, `.xls` |
| KML (Google Earth) | `.kml` |
| GPX (GPS Exchange) | `.gpx` |
| JSON | `.json` |
| DJI Logs | `.csv`, `.txt` |
| ArduPilot logs | `.log`, `.csv` |

You can load logs either by uploading a file or by pasting a direct downloadable URL in the sidebar.

## Column Auto-Detection
The app automatically detects columns named (case-insensitive):
- **Latitude**: `lat`, `latitude`, `OSD.latitude`, `GPS.lat`, `position_lat`
- **Longitude**: `lon`, `longitude`, `OSD.longitude`, `GPS.lon`
- **Altitude**: `alt`, `altitude`, `height`, `OSD.altitude`
- **Speed**: `speed`, `velocity`, `groundspeed`, `OSD.groundOrVerticalSpeed`
- **Time**: `time`, `timestamp`, `datetime`, `OSD.flyTime`

## Sidebar Controls
- **Halt Speed Threshold** — Adjust how slow counts as a "halt" (default 0.5 m/s)
- **Min Points for Halt** — How many consecutive slow points = 1 halt event
- **Map Layers** — Toggle heat map, path, halt markers, and data points independently
