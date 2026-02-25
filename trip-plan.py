#!/usr/bin/env python3
import os
import pandas as pd
import googlemaps
from datetime import datetime, timedelta
from urllib.parse import quote

# --- CONFIGURATION ---
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
INPUT_FILE = 'trip-destinations.csv'
TXT_OUTPUT = 'trip-itinerary.txt'
HTML_OUTPUT = 'index.html'
TRIP_START_TIME = datetime(2026, 2, 26, 22, 0)

def parse_stay(stay_str):
    try:
        if pd.isna(stay_str) or stay_str == "": return timedelta(hours=1)
        h, m = map(int, str(stay_str).split(':'))
        return timedelta(hours=h, minutes=m)
    except: return timedelta(hours=1)

def format_stay_string(td):
    total_seconds = int(td.total_seconds())
    return f"{total_seconds // 3600} hour(s) {(total_seconds % 3600) // 60} minutes"

def get_pin_link(lat, lng):
    return f"http://maps.google.com/?q={lat},{lng}"

#def get_daily_route_link(stops):
#    if not stops: return ""
#    base_url = "https://www.google.com/maps/dir/?api=1"
#    origin = "origin=My+Location"
#    destination = f"destination={stops[-1]['lat']},{stops[-1]['lng']}"
#    waypoints = quote("|".join([f"{s['lat']},{s['lng']}" for s in stops]))
#    return f"{base_url}&{origin}&{destination}&waypoints={waypoints}&travelmode=driving"

def get_daily_route_link(stops):
    if not stops: return ""
    # We use the /dir/ (Directions) format which is better for many stops
    base_url = "https://www.google.com/maps/dir/"
    
    # Create a list of "lat,lng" strings for every stop
    path_segments = [f"{s['lat']},{s['lng']}" for s in stops]
    
    # Join them with slashes: /lat,lng/lat,lng/lat,lng
    return base_url + "/".join(path_segments)    

def main():
    if not API_KEY:
        print("❌ Error: GOOGLE_MAPS_API_KEY not set.")
        return

    gmaps = googlemaps.Client(key=API_KEY)
    
    try:
        df = pd.read_csv(INPUT_FILE, comment='#')
    except FileNotFoundError:
        print(f"❌ Error: {INPUT_FILE} not found.")
        return

    current_time = TRIP_START_TIME
    itinerary = []

    print("🚀 Calculating route data via Google Maps API...")

    for i in range(len(df)):
        row = df.iloc[i]
        stay_td = parse_stay(row['stay'])
        arrival = current_time
        departure = arrival + stay_td
        
        drive_time = "-"
        drive_seconds = 0 
        
        if i < len(df) - 1:
            next_row = df.iloc[i+1]
            if (row['lat'], row['lng']) == (next_row['lat'], next_row['lng']):
                drive_time = "0 min (Same location)"
                drive_seconds = 0
            else:
                try:
                    res = gmaps.distance_matrix((row['lat'], row['lng']), (next_row['lat'], next_row['lng']), mode="driving")
                    element = res['rows'][0]['elements'][0]
                    status = element.get('status')
                    if status == 'OK':
                        drive_time = element['duration']['text'].replace("hours", "hrs").replace("mins", "min")
                        drive_seconds = element['duration']['value']
                    else:
                        drive_time = f"0 min ({status})"
                        drive_seconds = 0
                except:
                    drive_time = "0 min (API Error)"
                    drive_seconds = 0

        itinerary.append({
            "name": row['name'], "lat": row['lat'], "lng": row['lng'],
            "stay_str": format_stay_string(stay_td), "arrival": arrival, "departure": departure,
            "drive_to_next": drive_time, "comments": str(row['comments']),
            "pin": get_pin_link(row['lat'], row['lng'])
        })
        current_time = departure + timedelta(seconds=drive_seconds)

    days = {}
    for s in itinerary:
        d = s['arrival'].strftime("%A, %B %d")
        if d not in days: days[d] = []
        days[d].append(s)

    # --- GENERATE TXT ---
    with open(TXT_OUTPUT, "w", encoding="utf-8") as f:
        for d, stops in days.items():
            f.write(f"----------------------------------------\n>>> {d.upper()} <<<\n----------------------------------------\n\n")
            f.write(f"🗺️ FULL DAY ROUTE MAP: {get_daily_route_link(stops)}\n\n")
            for s in stops:
                f.write(f"📍 {s['name']}\n   🕒 Arrive:  {s['arrival'].strftime('%-I:%M %p')}\n   ⌛ Stay:    {s['stay_str']}\n   🛫 Depart:  {s['departure'].strftime('%-I:%M %p')}\n")
                if s['drive_to_next'] != "-": f.write(f"   🚗 Drive:   {s['drive_to_next']} to next destination\n")
                f.write(f"   🔗 Pin:      {s['pin']}\n")
                if s['comments'].lower() != "no comments": f.write(f"   💬 Info:    {s['comments']}\n")
                f.write("\n")

    # --- GENERATE HTML ---
    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>")
        f.write("body{font-family:sans-serif; background:#f4f4f9; padding:10px; line-height:1.5; color: #333;}")
        f.write(".day-box{background:#fff; border-radius:10px; padding:15px; margin-bottom:25px; box-shadow:0 2px 5px rgba(0,0,0,0.1);}")
        f.write("h2{color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:5px; margin-top: 0;}")
        f.write(".map-btn{display:block; background:#3498db; color:#fff; text-align:center; padding:12px; border-radius:5px; text-decoration:none; margin:10px 0 20px 0; font-weight:bold;}")
        f.write(".stop{border-left:4px solid #e74c3c; padding-left:15px; margin-bottom:20px;}")
        f.write(".stop-name{font-weight:bold; font-size:1.1em; color:#e74c3c; margin-bottom: 5px;}")
        f.write(".details{font-size: 0.95em; color: #555;}")
        f.write(".pin-link{display: inline-block; margin-top: 8px; color:#3498db; text-decoration:none; font-weight: bold;}")
        f.write(".comment-box{margin-top: 5px; margin-bottom: 10px; padding: 8px; background: #fff9c4; border-radius: 4px; font-size: 0.9em; color: #444; border-left: 3px solid #fbc02d;}")
        f.write("</style></head><body><h1 style='text-align:center;'>Trip Itinerary</h1>")
        
        for d, stops in days.items():
            f.write(f"<div class='day-box'><h2>{d}</h2>")
            f.write(f"<a class='map-btn' href='{get_daily_route_link(stops)}'>View Map For Entire Day's Route!</a>")
            for s in stops:
                f.write(f"<div class='stop'><div class='stop-name'>📍 {s['name']}</div>")
                
                # --- COMMENT BOX MOVED HERE ---
                if s['comments'].lower() != "no comments" and s['comments'].strip() != "":
                    f.write(f"<div class='comment-box'>💬 <b>Info:</b> {s['comments']}</div>")
                
                f.write("<div class='details'>")
                f.write(f"🕒 <b>Arrive:</b> {s['arrival'].strftime('%-I:%M %p')}<br>")
                f.write(f"⌛ <b>Stay:</b> {s['stay_str']}<br>")
                f.write(f"🛫 <b>Depart:</b> {s['departure'].strftime('%-I:%M %p')}<br>")
                if s['drive_to_next'] != "-": 
                    f.write(f"🚗 <b>Drive:</b> {s['drive_to_next']} to next destination<br>")
                f.write(f"<a class='pin-link' href='{s['pin']}'>🔗 View Map Pin</a>")
                f.write("</div></div>")
            f.write("</div>")
        f.write("</body></html>")

    print(f"✅ Success! Generated:\n   - {TXT_OUTPUT}\n   - {HTML_OUTPUT}")

if __name__ == "__main__":
    main()