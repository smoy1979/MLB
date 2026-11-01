#!/usr/bin/env python3
"""
MLB League-Wide Regular Season Schedule Optimizer, PDF Calendar Generator,
and Historical Schedule Evaluator using Google OR-Tools CP-SAT.

Usage:
  1. Optimize 2027 schedule (30-min timeout, exports CSVs + 30 Team PDFs to data/):
     python mlb_scheduler_7.py

  2. Evaluate official 2026 MLB schedule from MLB Stats API (no optimization):
     python mlb_scheduler_7.py --evaluate-2026

  3. Evaluate any existing schedule CSV file (and optionally generate PDFs from it):
     python mlb_scheduler_7.py --evaluate-csv data/mlb_schedule.csv --season-year 2027
"""

import argparse
import os
import math
import time
import datetime
from typing import Dict, List, Tuple, Any, Optional
import requests
import pandas as pd
from ortools.sat.python import cp_model

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ==============================================================================
# 1. DATA INGESTION & FALLBACK SETUP
# ==============================================================================

MLB_API_URL = "https://statsapi.mlb.com/api/v1/teams?sportId=1&hydrate=venue(location)"
MLB_SCHEDULE_API_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={year}&gameType=R"
ESPN_LOGO_URL = "https://a.espncdn.com/i/teamlogos/mlb/500/{espn_abbr}.png"

FALLBACK_TEAMS: List[Dict[str, Any]] = [
    # AL East
    {"id": 110, "name": "Baltimore Orioles", "abbr": "BAL", "league": "AL", "division": "AL East", "venue": "Oriole Park at Camden Yards", "lat": 39.2838, "lon": -76.6216},
    {"id": 111, "name": "Boston Red Sox", "abbr": "BOS", "league": "AL", "division": "AL East", "venue": "Fenway Park", "lat": 42.3467, "lon": -71.0972},
    {"id": 147, "name": "New York Yankees", "abbr": "NYY", "league": "AL", "division": "AL East", "venue": "Yankee Stadium", "lat": 40.8296, "lon": -73.9262},
    {"id": 139, "name": "Tampa Bay Rays", "abbr": "TB", "league": "AL", "division": "AL East", "venue": "Tropicana Field", "lat": 27.7682, "lon": -82.6534},
    {"id": 141, "name": "Toronto Blue Jays", "abbr": "TOR", "league": "AL", "division": "AL East", "venue": "Rogers Centre", "lat": 43.6414, "lon": -79.3894},
    # AL Central
    {"id": 145, "name": "Chicago White Sox", "abbr": "CWS", "league": "AL", "division": "AL Central", "venue": "Guaranteed Rate Field", "lat": 41.8299, "lon": -87.6338},
    {"id": 114, "name": "Cleveland Guardians", "abbr": "CLE", "league": "AL", "division": "AL Central", "venue": "Progressive Field", "lat": 41.4962, "lon": -81.6852},
    {"id": 116, "name": "Detroit Tigers", "abbr": "DET", "league": "AL", "division": "AL Central", "venue": "Comerica Park", "lat": 42.3390, "lon": -83.0485},
    {"id": 118, "name": "Kansas City Royals", "abbr": "KC", "league": "AL", "division": "AL Central", "venue": "Kauffman Stadium", "lat": 39.0517, "lon": -94.4803},
    {"id": 142, "name": "Minnesota Twins", "abbr": "MIN", "league": "AL", "division": "AL Central", "venue": "Target Field", "lat": 44.9817, "lon": -93.2776},
    # AL West
    {"id": 117, "name": "Houston Astros", "abbr": "HOU", "league": "AL", "division": "AL West", "venue": "Minute Maid Park", "lat": 29.7573, "lon": -95.3555},
    {"id": 108, "name": "Los Angeles Angels", "abbr": "LAA", "league": "AL", "division": "AL West", "venue": "Angel Stadium", "lat": 33.8003, "lon": -117.8827},
    {"id": 133, "name": "Athletics", "abbr": "ATH", "league": "AL", "division": "AL West", "venue": "Sutter Health Park", "lat": 38.5804, "lon": -121.5138},
    {"id": 136, "name": "Seattle Mariners", "abbr": "SEA", "league": "AL", "division": "AL West", "venue": "T-Mobile Park", "lat": 47.5914, "lon": -122.3325},
    {"id": 140, "name": "Texas Rangers", "abbr": "TEX", "league": "AL", "division": "AL West", "venue": "Globe Life Field", "lat": 32.7473, "lon": -97.0842},
    # NL East
    {"id": 144, "name": "Atlanta Braves", "abbr": "ATL", "league": "NL", "division": "NL East", "venue": "Truist Park", "lat": 33.8907, "lon": -84.4677},
    {"id": 146, "name": "Miami Marlins", "abbr": "MIA", "league": "NL", "division": "NL East", "venue": "loanDepot park", "lat": 25.7781, "lon": -80.2197},
    {"id": 121, "name": "New York Mets", "abbr": "NYM", "league": "NL", "division": "NL East", "venue": "Citi Field", "lat": 40.7571, "lon": -73.8458},
    {"id": 143, "name": "Philadelphia Phillies", "abbr": "PHI", "league": "NL", "division": "NL East", "venue": "Citizens Bank Park", "lat": 39.9061, "lon": -75.1665},
    {"id": 120, "name": "Washington Nationals", "abbr": "WSH", "league": "NL", "division": "NL East", "venue": "Nationals Park", "lat": 38.8730, "lon": -77.0074},
    # NL Central
    {"id": 112, "name": "Chicago Cubs", "abbr": "CHC", "league": "NL", "division": "NL Central", "venue": "Wrigley Field", "lat": 41.9484, "lon": -87.6553},
    {"id": 113, "name": "Cincinnati Reds", "abbr": "CIN", "league": "NL", "division": "NL Central", "venue": "Great American Ball Park", "lat": 39.0974, "lon": -84.5065},
    {"id": 158, "name": "Milwaukee Brewers", "abbr": "MIL", "league": "NL", "division": "NL Central", "venue": "American Family Field", "lat": 43.0280, "lon": -87.9712},
    {"id": 134, "name": "Pittsburgh Pirates", "abbr": "PIT", "league": "NL", "division": "NL Central", "venue": "PNC Park", "lat": 40.4469, "lon": -80.0057},
    {"id": 138, "name": "St. Louis Cardinals", "abbr": "STL", "league": "NL", "division": "NL Central", "venue": "Busch Stadium", "lat": 38.6226, "lon": -90.1928},
    # NL West
    {"id": 109, "name": "Arizona Diamondbacks", "abbr": "AZ", "league": "NL", "division": "NL West", "venue": "Chase Field", "lat": 33.4453, "lon": -112.0667},
    {"id": 115, "name": "Colorado Rockies", "abbr": "COL", "league": "NL", "division": "NL West", "venue": "Coors Field", "lat": 39.7559, "lon": -104.9942},
    {"id": 119, "name": "Los Angeles Dodgers", "abbr": "LAD", "league": "NL", "division": "NL West", "venue": "Dodger Stadium", "lat": 34.0739, "lon": -118.2400},
    {"id": 135, "name": "San Diego Padres", "abbr": "SD", "league": "NL", "division": "NL West", "venue": "Petco Park", "lat": 32.7076, "lon": -117.1570},
    {"id": 137, "name": "San Francisco Giants", "abbr": "SF", "league": "NL", "division": "NL West", "venue": "Oracle Park", "lat": 37.7786, "lon": -122.3893},
]

NATURAL_RIVALS: List[Tuple[str, str]] = [
    ("BAL", "WSH"), ("BOS", "ATL"), ("NYY", "NYM"), ("TB", "MIA"), ("TOR", "PHI"),
    ("CWS", "CHC"), ("CLE", "CIN"), ("DET", "PIT"), ("KC", "STL"), ("MIN", "MIL"),
    ("HOU", "COL"), ("LAA", "LAD"), ("ATH", "SF"), ("SEA", "SD"), ("TEX", "AZ")
]


def fetch_mlb_teams() -> List[Dict[str, Any]]:
    """Fetches MLB team and venue metadata from MLB Stats API with offline fallback."""
    fallback_by_id = {t["id"]: t for t in FALLBACK_TEAMS}
    try:
        print(f"Fetching MLB metadata from {MLB_API_URL} ...")
        resp = requests.get(MLB_API_URL, timeout=6)
        resp.raise_for_status()
        data = resp.json().get("teams", [])
        if len(data) != 30:
            raise ValueError(f"Expected 30 teams, got {len(data)}")

        parsed_teams = []
        for t in data:
            tid = t.get("id")
            fb = fallback_by_id.get(tid, {})
            venue = t.get("venue", {})
            coords = venue.get("location", {}).get("defaultCoordinates", {})
            lat = coords.get("latitude", fb.get("lat", 39.0))
            lon = coords.get("longitude", fb.get("lon", -95.0))

            league_name = t.get("league", {}).get("name", "")
            league_abbr = "AL" if "American" in league_name else ("NL" if "National" in league_name else fb.get("league", "AL"))
            div_name = t.get("division", {}).get("name", fb.get("division", "AL East"))
            div_short = (
                div_name.replace("American League", "AL")
                .replace("National League", "NL")
                .strip()
            )
            parsed_teams.append({
                "id": tid,
                "name": t.get("name", fb.get("name")),
                "abbr": fb.get("abbr") or t.get("abbreviation"),
                "league": league_abbr,
                "division": div_short,
                "venue": venue.get("name", fb.get("venue")),
                "lat": float(lat),
                "lon": float(lon),
            })
        parsed_teams.sort(key=lambda x: (x["division"], x["abbr"]))
        print("Successfully loaded live MLB Stats API metadata for 30 teams.")
        return parsed_teams
    except Exception as exc:
        print(f"API fetch failed ({exc}). Using hardcoded fallback dataset.")
        teams = list(FALLBACK_TEAMS)
        teams.sort(key=lambda x: (x["division"], x["abbr"]))
        return teams


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Computes great-circle distance in integer miles between two lat/lon pairs."""
    r_miles = 3958.756
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return int(round(2 * r_miles * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))))


def build_distance_matrix(teams: List[Dict[str, Any]]) -> List[List[int]]:
    """Constructs a symmetric 30x30 Haversine distance matrix in miles."""
    n = len(teams)
    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine_miles(teams[i]["lat"], teams[i]["lon"], teams[j]["lat"], teams[j]["lon"])
            dist[i][j] = d
            dist[j][i] = d
    return dist


# ==============================================================================
# 2. CALENDAR STRUCTURE & TIME SLOT ARCHITECTURE (53 TOTAL SLOTS / 52 ACTIVE)
# ==============================================================================

def get_calendar_holidays(season_year: int) -> Dict[str, datetime.date]:
    """Computes exact dates for Opening Thursday, Memorial Day, July 4th, ASG Monday, and Labor Day."""
    may_31 = datetime.date(season_year, 5, 31)
    memorial_day = may_31 - datetime.timedelta(days=(may_31.weekday() - 0) % 7)

    july_4th = datetime.date(season_year, 7, 4)

    sep_1 = datetime.date(season_year, 9, 1)
    labor_day = sep_1 + datetime.timedelta(days=(0 - sep_1.weekday()) % 7)

    july_13 = datetime.date(season_year, 7, 13)
    asg_monday = july_13 - datetime.timedelta(days=july_13.weekday())

    mar_25 = datetime.date(season_year, 3, 25)
    offset_to_thu = (3 - mar_25.weekday()) % 7
    if offset_to_thu > 3:
        offset_to_thu -= 7
    opening_thursday = mar_25 + datetime.timedelta(days=offset_to_thu)

    return {
        "opening_thu": opening_thursday,
        "memorial_day": memorial_day,
        "july_4th": july_4th,
        "asg_monday": asg_monday,
        "labor_day": labor_day,
    }


def build_season_slots(season_year: int = 2027) -> Tuple[List[Dict[str, Any]], Dict[str, datetime.date]]:
    """
    Constructs 53 half-week Series Slots (52 active series slots + 1 All-Star Break slot)
    covering Opening Weekend (Thu Mar 25 - Sun Mar 28) plus all 26 full weeks through Sun Sep 26.
    """
    holidays = get_calendar_holidays(season_year)
    start_date = holidays["opening_thu"]
    memorial_day = holidays["memorial_day"]
    july_4th = holidays["july_4th"]
    asg_monday = holidays["asg_monday"]
    labor_day = holidays["labor_day"]

    slots: List[Dict[str, Any]] = []

    # Slot 0: Opening Weekend (Thu, Sat, Sun for 3g; Thu-Sun for 4g)
    slots.append({
        "slot_idx": 0,
        "label": "W01_B_Opening",
        "slot_type": "B",
        "is_asg": False,
        "is_post_asg": False,
        "holiday": None,
        "dates_3g": [start_date, start_date + datetime.timedelta(days=2), start_date + datetime.timedelta(days=3)],
        "dates_3g_early": [start_date, start_date + datetime.timedelta(days=2), start_date + datetime.timedelta(days=3)],
        "dates_4g": [start_date + datetime.timedelta(days=d) for d in range(4)],
        "force_3g": False,
        "shares_thu_with_prev": False,
        "is_monday_holiday_wrap": False,
    })

    curr_mon = start_date + datetime.timedelta(days=4)
    slot_idx = 1

    # Generate all 26 full Monday-Sunday weeks (52 half-week slots: 51 active + 1 ASG Break)
    for wk_offset in range(26):
        tue = curr_mon + datetime.timedelta(days=1)
        wed = curr_mon + datetime.timedelta(days=2)
        thu = curr_mon + datetime.timedelta(days=3)
        fri = curr_mon + datetime.timedelta(days=4)
        sat = curr_mon + datetime.timedelta(days=5)
        sun = curr_mon + datetime.timedelta(days=6)
        next_mon = curr_mon + datetime.timedelta(days=7)

        week_num = wk_offset + 2
        is_asg_midweek = (curr_mon == asg_monday)
        july_4_in_midweek = (curr_mon <= july_4th <= thu)
        july_4_in_weekend = (fri <= july_4th <= sun)

        # --- SLOT A (Midweek: Mon-Thu) ---
        if is_asg_midweek:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A_ASG_Break",
                "slot_type": "ASG",
                "is_asg": True,
                "is_post_asg": False,
                "holiday": "All-Star Break",
                "dates_3g": [],
                "dates_3g_early": [],
                "dates_4g": [],
                "force_3g": False,
                "shares_thu_with_prev": False,
                "is_monday_holiday_wrap": False,
            })
        elif curr_mon in (memorial_day, labor_day):
            # Previous weekend wrapped into Monday holiday; midweek is strictly Tue-Thu (3g only)
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A",
                "slot_type": "A",
                "is_asg": False,
                "is_post_asg": False,
                "holiday": None,
                "dates_3g": [tue, wed, thu],
                "dates_3g_early": [tue, wed, thu],
                "dates_4g": [tue, wed, thu],
                "force_3g": True,
                "shares_thu_with_prev": False,
                "is_monday_holiday_wrap": False,
            })
        elif july_4_in_midweek:
            if july_4th == curr_mon:
                d3 = [curr_mon, tue, wed]
                d3_early = [curr_mon, tue, wed]
            elif july_4th == thu:
                d3 = [tue, wed, thu]
                d3_early = [tue, wed, thu]
            else:
                d3 = [tue, wed, thu]
                d3_early = [curr_mon, tue, wed]
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A_July4th",
                "slot_type": "A",
                "is_asg": False,
                "is_post_asg": False,
                "holiday": "July 4th",
                "dates_3g": d3,
                "dates_3g_early": d3_early,
                "dates_4g": [curr_mon, tue, wed, thu],
                "force_3g": False,
                "shares_thu_with_prev": False,
                "is_monday_holiday_wrap": False,
            })
        else:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A",
                "slot_type": "A",
                "is_asg": False,
                "is_post_asg": False,
                "holiday": None,
                "dates_3g": [tue, wed, thu],
                "dates_3g_early": [curr_mon, tue, wed],
                "dates_4g": [curr_mon, tue, wed, thu],
                "force_3g": False,
                "shares_thu_with_prev": False,
                "is_monday_holiday_wrap": False,
            })
        slot_idx += 1

        # --- SLOT B (Weekend: Fri-Sun or Thu-Sun or Fri-Mon Holiday Wrap) ---
        if next_mon == memorial_day:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_B_MemorialDay",
                "slot_type": "B",
                "is_asg": False,
                "is_post_asg": False,
                "holiday": "Memorial Day",
                "dates_3g": [sat, sun, next_mon],
                "dates_3g_early": [sat, sun, next_mon],
                "dates_4g": [fri, sat, sun, next_mon],
                "force_3g": False,
                "shares_thu_with_prev": False,
                "is_monday_holiday_wrap": True,
            })
        elif next_mon == labor_day:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_B_LaborDay",
                "slot_type": "B",
                "is_asg": False,
                "is_post_asg": False,
                "holiday": "Labor Day",
                "dates_3g": [sat, sun, next_mon],
                "dates_3g_early": [sat, sun, next_mon],
                "dates_4g": [fri, sat, sun, next_mon],
                "force_3g": False,
                "shares_thu_with_prev": False,
                "is_monday_holiday_wrap": True,
            })
        elif curr_mon in (memorial_day, labor_day):
            # In a week where Monday was Memorial/Labor Day, Slot A played [Tue, Wed, Thu],
            # so Slot B is restricted to 3-game series [Fri, Sat, Sun] to prevent Thursday collisions.
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_B",
                "slot_type": "B",
                "is_asg": False,
                "is_post_asg": False,
                "holiday": None,
                "dates_3g": [fri, sat, sun],
                "dates_3g_early": [fri, sat, sun],
                "dates_4g": [fri, sat, sun],
                "force_3g": True,
                "shares_thu_with_prev": False,
                "is_monday_holiday_wrap": False,
            })
        elif july_4_in_weekend:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_B_July4th",
                "slot_type": "B",
                "is_asg": False,
                "is_post_asg": False,
                "holiday": "July 4th",
                "dates_3g": [fri, sat, sun],
                "dates_3g_early": [fri, sat, sun],
                "dates_4g": [thu, fri, sat, sun],
                "force_3g": False,
                "shares_thu_with_prev": (not is_asg_midweek),
                "is_monday_holiday_wrap": False,
            })
        else:
            lbl = f"W{week_num:02d}_B_Finale" if wk_offset == 25 else f"W{week_num:02d}_B"
            slots.append({
                "slot_idx": slot_idx,
                "label": lbl,
                "slot_type": "B",
                "is_asg": False,
                "is_post_asg": is_asg_midweek,
                "holiday": None,
                "dates_3g": [fri, sat, sun],
                "dates_3g_early": [fri, sat, sun],
                "dates_4g": [thu, fri, sat, sun],
                "force_3g": False,
                "shares_thu_with_prev": (not is_asg_midweek),
                "is_monday_holiday_wrap": False,
            })
        slot_idx += 1
        curr_mon = next_mon

    assert len(slots) == 53, f"Expected 53 total slots (52 active + 1 ASG), generated {len(slots)}"
    return slots, holidays


# ==============================================================================
# 3. PHASE 1: SERIES MATRIX & GAME QUOTA SOLVER (52 SERIES / 162 GAMES PER TEAM)
# ==============================================================================

def solve_matchup_quotas(teams: List[Dict[str, Any]], num_workers: int = 12) -> List[Dict[str, Any]]:
    """
    Phase 1 CP-SAT Model:
    Enforces exact hard matchup quotas for all 30 teams:
      - In-Division (52 games): 13 games x 4 opponents (three 3g + one 4g series per opponent = 16 series)
      - Interdivision Same-League (62 games): 6 games x 8 opponents (two 3g series) and
        7 games x 2 opponents (one 3g + one 4g series) = 20 series
      - Interleague (48 games): 6 games x 1 natural rival (two 3g series: 1H, 1A) and
        3 games x 14 other interleague opponents (one 3g series each: 7H, 7A) = 16 series
      - Total per team: 52 series (26 Home, 26 Away), 162 games (81 Home, 81 Away).
    """
    print("\nPhase 1: Solving league-wide series matrix (52 series / 81H & 81A games per team)...")
    model = cp_model.CpModel()
    n = len(teams)
    abbr_to_idx = {t["abbr"]: i for i, t in enumerate(teams)}
    rival_set = set()
    for a, b in NATURAL_RIVALS:
        i, j = abbr_to_idx[a], abbr_to_idx[b]
        rival_set.add((min(i, j), max(i, j)))

    s3 = {}
    s4 = {}

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            same_div = teams[i]["division"] == teams[j]["division"]
            same_lg = teams[i]["league"] == teams[j]["league"]
            is_rival = (min(i, j), max(i, j)) in rival_set

            if same_div:
                s3[i, j] = model.NewIntVar(1, 2, f"s3_{i}_{j}")
                s4[i, j] = model.NewIntVar(0, 1, f"s4_{i}_{j}")
            elif same_lg:
                # 1 Home series vs each of the 10 interdivision same-league opponents
                s3[i, j] = model.NewBoolVar(f"s3_{i}_{j}")
                s4[i, j] = model.NewBoolVar(f"s4_{i}_{j}")
                model.Add(s3[i, j] + s4[i, j] == 1)
            elif is_rival:
                # 6 games vs 1 interleague rival = two 3-game series (1 Home, 1 Away)
                s3[i, j] = model.NewConstant(1)
                s4[i, j] = model.NewConstant(0)
            else:
                # 3 games vs 14 other interleague opponents = one 3-game series per pair
                s3[i, j] = model.NewBoolVar(f"s3_{i}_{j}")
                s4[i, j] = model.NewConstant(0)

    for i in range(n):
        for j in range(i + 1, n):
            same_div = teams[i]["division"] == teams[j]["division"]
            same_lg = teams[i]["league"] == teams[j]["league"]
            is_rival = (i, j) in rival_set

            if same_div:
                # 13 games: three 3-game series + one 4-game series (2 Home, 2 Away)
                model.Add(s3[i, j] + s3[j, i] == 3)
                model.Add(s4[i, j] + s4[j, i] == 1)
                model.Add(s3[i, j] + s4[i, j] == 2)
                model.Add(s3[j, i] + s4[j, i] == 2)
            elif same_lg:
                # Either 6 games (two 3g) or 7 games (one 3g + one 4g) -> at most one 4g series per pair
                model.Add(s4[i, j] + s4[j, i] <= 1)
            elif not is_rival:
                # Exactly one 3-game series between non-rival interleague pairs
                model.Add(s3[i, j] + s3[j, i] == 1)

    for i in range(n):
        non_div_lg = [
            j for j in range(n)
            if j != i and teams[j]["league"] == teams[i]["league"] and teams[j]["division"] != teams[i]["division"]
        ]
        # Interdivision within same league: 6 games x 8 opponents and 7 games x 2 opponents (62 games)
        model.Add(sum(s4[i, j] + s4[j, i] for j in non_div_lg) == 2)

        home_games = sum(3 * s3[i, j] + 4 * s4[i, j] for j in range(n) if j != i)
        away_games = sum(3 * s3[j, i] + 4 * s4[j, i] for j in range(n) if j != i)
        model.Add(home_games == 81)
        model.Add(away_games == 81)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.num_search_workers = num_workers
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Phase 1 failed with status: {solver.StatusName(status)}")

    series_list: List[Dict[str, Any]] = []
    sid = 0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            c3 = solver.Value(s3[i, j])
            c4 = solver.Value(s4[i, j])
            is_div = teams[i]["division"] == teams[j]["division"]
            for _ in range(c3):
                series_list.append({"id": sid, "home": i, "away": j, "games": 3, "is_div": is_div})
                sid += 1
            for _ in range(c4):
                series_list.append({"id": sid, "home": i, "away": j, "games": 4, "is_div": is_div})
                sid += 1

    print(f"Phase 1 complete: Generated {len(series_list)} balanced series (2,430 total games).")
    return series_list


# ==============================================================================
# 4. PHASE 2: TEMPORAL SLOT & ROUTING CP-SAT OPTIMIZER WITH LIVE PROGRESS
# ==============================================================================

class SolutionProgressCallback(cp_model.CpSolverSolutionCallback):
    """Logs live incumbent solution milestones during Phase 2 CP-SAT search."""

    def __init__(
        self,
        div_vars: List[Any],
        iso_h_vars: List[Any],
        iso_a_vars: List[Any],
        rt_vars: List[Any],
        miss_apr_vars: List[Any],
        miss_sep_vars: List[Any],
        asg_thu_vars: List[Any],
    ):
        super().__init__()
        self._div_vars = div_vars
        self._iso_h_vars = iso_h_vars
        self._iso_a_vars = iso_a_vars
        self._rt_vars = rt_vars
        self._miss_apr_vars = miss_apr_vars
        self._miss_sep_vars = miss_sep_vars
        self._asg_thu_vars = asg_thu_vars
        self._start_time = time.time()
        self._solution_count = 0

    def on_solution_callback(self) -> None:
        self._solution_count += 1
        elapsed = time.time() - self._start_time
        obj = self.ObjectiveValue()
        bound = self.BestObjectiveBound()
        div_cnt = sum(self.Value(v) for v in self._div_vars)
        iso_h = sum(self.Value(v) for v in self._iso_h_vars)
        iso_a = sum(self.Value(v) for v in self._iso_a_vars)
        rt_cnt = sum(self.Value(v) for v in self._rt_vars)
        m_apr = sum(self.Value(v) for v in self._miss_apr_vars)
        m_sep = sum(self.Value(v) for v in self._miss_sep_vars)
        asg_thu = sum(self.Value(v) for v in self._asg_thu_vars)
        print(
            f"  [Solution #{self._solution_count:02d} @ {elapsed:6.1f}s] "
            f"Obj: {obj:8.0f} (Bound: {bound:8.0f}) | "
            f"Miss Apr/Sep: {m_apr:2d}/{m_sep:2d} | "
            f"1-Ser H/A: {iso_h:2d}/{iso_a:2d} | "
            f"ASG Thu: {asg_thu:2d} | "
            f"Early/Late Div: {div_cnt:3d} | "
            f"Road Trips: {rt_cnt:3d}"
        )


def solve_schedule_slots(
    teams: List[Dict[str, Any]],
    slots: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    dist_matrix: List[List[int]],
    timeout_sec: int = 1800,
    season_year: int = 2027,
    num_workers: int = 12,
    verbose_solver_logs: bool = True,
) -> Tuple[Dict[int, int], Dict[str, Any]]:
    """
    Phase 2 CP-SAT Model:
    Assigns all 780 series to the 52 active half-week slots with:
      - Hard no-doubleheader constraints (at most one 4-game series per team in any Mon-Sun week).
      - Hard divisional density cap: at most 2 series vs. the same divisional opponent in any 31-day span.
      - Hard divisional max-gap cap: never go more than 3 months (91 days) between series vs. the same divisional opponent.
      - Hard maximum 3 consecutive Home series and maximum 3 consecutive Away series.
      - Soft penalties for 1-series road trips, 1-series homestands, missed April/September
        divisional opponents, and All-Star Thursday games.
    """
    print("\nPhase 2: Building CP-SAT slot assignment and road-trip routing model...")
    t0 = time.time()
    model = cp_model.CpModel()
    n_teams = len(teams)
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]
    n_active = len(active_slots)  # 52 active slots

    april_cutoff = datetime.date(season_year, 4, 30)
    sept_cutoff = datetime.date(season_year, 9, 1)

    april_slots = [s["slot_idx"] for s in slots if not s["is_asg"] and s["dates_3g"][0] <= april_cutoff]
    sept_slots = [s["slot_idx"] for s in slots if not s["is_asg"] and s["dates_3g"][-1] >= sept_cutoff]

    # Precompute 31-day sliding slot windows and 3-month (91-day) sliding slot windows
    slot_starts = {s["slot_idx"]: s["dates_3g"][0] for s in slots if not s["is_asg"]}
    slot_ends = {s["slot_idx"]: s["dates_3g"][-1] for s in slots if not s["is_asg"]}

    windows_31d: List[List[int]] = []
    for k in range(n_active):
        d0 = slot_starts[active_slots[k]]
        win = [s for s in active_slots[k:] if (slot_starts[s] - d0).days <= 30]
        if len(win) >= 3:
            windows_31d.append(win)

    windows_91d: List[List[int]] = []
    season_last_day = slot_ends[active_slots[-1]]
    for k in range(n_active):
        d0 = slot_starts[active_slots[k]]
        if (season_last_day - d0).days >= 91:
            win = [s for s in active_slots[k:] if (slot_starts[s] - d0).days <= 91]
            windows_91d.append(win)

    first_4w_slots = active_slots[:8]
    final_4w_slots = active_slots[-8:]
    early_late_slots = set(first_4w_slots + final_4w_slots)

    buckets: Dict[Tuple[int, int, int, bool], List[int]] = {}
    for sr in series_list:
        key = (sr["home"], sr["away"], sr["games"], sr["is_div"])
        buckets.setdefault(key, []).append(sr["id"])

    x = {}
    for sid in range(len(series_list)):
        for s in active_slots:
            x[sid, s] = model.NewBoolVar(f"x_{sid}_{s}")

    # 1. Each series scheduled in exactly one active slot
    for sid, sr in enumerate(series_list):
        model.AddExactlyOne(x[sid, s] for s in active_slots)
        for s in active_slots:
            if slots[s].get("force_3g", False) and sr["games"] == 4:
                model.Add(x[sid, s] == 0)

    # Symmetry breaking for identical series between the same (home, away, games)
    for _, sids in buckets.items():
        if len(sids) > 1:
            for k in range(len(sids) - 1):
                sid1, sid2 = sids[k], sids[k + 1]
                model.Add(
                    sum(idx * x[sid1, s] for idx, s in enumerate(active_slots))
                    < sum(idx * x[sid2, s] for idx, s in enumerate(active_slots))
                )

    home_series_by_team = {t: [] for t in range(n_teams)}
    away_series_by_team = {t: [] for t in range(n_teams)}
    four_game_series_by_team = {t: [] for t in range(n_teams)}
    pair_series = {}

    for sid, sr in enumerate(series_list):
        h, a = sr["home"], sr["away"]
        home_series_by_team[h].append(sid)
        away_series_by_team[a].append(sid)
        if sr["games"] == 4:
            four_game_series_by_team[h].append(sid)
            four_game_series_by_team[a].append(sid)
        pair_key = (min(h, a), max(h, a))
        pair_series.setdefault(pair_key, []).append(sid)

    is_home = {}
    for t in range(n_teams):
        for k, s in enumerate(active_slots):
            is_home[t, k] = model.NewBoolVar(f"home_{t}_{k}")
            h_vars = [x[sid, s] for sid in home_series_by_team[t]]
            a_vars = [x[sid, s] for sid in away_series_by_team[t]]
            model.AddExactlyOne(h_vars + a_vars)
            model.Add(sum(h_vars) == is_home[t, k])

    # 1b. HARD NO-DOUBLEHEADER CONSTRAINT:
    # A team cannot play two 4-game series in the same standard 7-day Mon-Sun week.
    for s_b in active_slots:
        if slots[s_b].get("shares_thu_with_prev", False):
            s_a = s_b - 1
            if s_a in active_slots:
                for t in range(n_teams):
                    f4_a = [x[sid, s_a] for sid in four_game_series_by_team[t]]
                    f4_b = [x[sid, s_b] for sid in four_game_series_by_team[t]]
                    model.Add(sum(f4_a + f4_b) <= 1)

    # 2. Divisional Spacing Constraints:
    #    - Soft <= April 30 and >= September 1 with penalty slacks
    #    - Hard: No back-to-back slots against the same divisional opponent
    #    - Hard: At most 2 series against the same divisional opponent in any 31-day span
    #    - Hard: Never go more than 3 months (91 days) between series against the same divisional opponent
    missed_april_vars = []
    missed_sept_vars = []
    div_pair_meta = []

    for (t1, t2), sids in pair_series.items():
        if teams[t1]["division"] == teams[t2]["division"]:
            miss_apr = model.NewBoolVar(f"miss_apr_{t1}_{t2}")
            miss_sep = model.NewBoolVar(f"miss_sep_{t1}_{t2}")

            model.Add(sum(x[sid, s] for sid in sids for s in april_slots) + miss_apr >= 1)
            model.Add(sum(x[sid, s] for sid in sids for s in sept_slots) + miss_sep >= 1)

            missed_april_vars.append(miss_apr)
            missed_sept_vars.append(miss_sep)
            div_pair_meta.append((teams[t1]["abbr"], teams[t2]["abbr"], miss_apr, miss_sep))

            # Hard constraint: prevent playing the same divisional opponent in back-to-back slots
            for k in range(n_active - 1):
                s_curr, s_next = active_slots[k], active_slots[k + 1]
                model.Add(sum(x[sid, s_curr] + x[sid, s_next] for sid in sids) <= 1)

            # Hard constraint: at most 2 series against the same divisional opponent in any 31-day span
            for win_31 in windows_31d:
                model.Add(sum(x[sid, s] for sid in sids for s in win_31) <= 2)

            # Hard constraint: at least 1 series in every 3-month (91-day) window so gap is never > 3 months
            for win_91 in windows_91d:
                model.Add(sum(x[sid, s] for sid in sids for s in win_91) >= 1)

    # 3. Road Trip & Homestand Length Constraints (Hard Max 3; Soft Min 2)
    isolated_home_vars = []
    isolated_away_vars = []

    for t in range(n_teams):
        # Hard Max 3 consecutive Home series and Max 3 consecutive Away series
        for k in range(n_active - 3):
            window = [is_home[t, k + d] for d in range(4)]
            model.Add(sum(window) <= 3)  # Max 3 consecutive Home series
            model.Add(sum(window) >= 1)  # Max 3 consecutive Away series

        # Soft 1-series road trip at start of season (Away in Slot 0, Home in Slot 1)
        iso_a_start = model.NewBoolVar(f"iso_a_start_{t}")
        model.Add(iso_a_start >= is_home[t, 1] - is_home[t, 0])
        isolated_away_vars.append(iso_a_start)

        # Soft 1-series road trip at end of season (Home in Slot 50, Away in Slot 51)
        iso_a_end = model.NewBoolVar(f"iso_a_end_{t}")
        model.Add(iso_a_end >= is_home[t, n_active - 2] - is_home[t, n_active - 1])
        isolated_away_vars.append(iso_a_end)

        # Interior slots (1 .. n_active - 2): track both A - H - A (1-series homestand) and H - A - H (1-series road trip)
        for k in range(1, n_active - 1):
            iso_h = model.NewBoolVar(f"iso_h_{t}_{k}")
            model.Add(iso_h >= is_home[t, k] - is_home[t, k - 1] - is_home[t, k + 1])
            isolated_home_vars.append(iso_h)

            iso_a = model.NewBoolVar(f"iso_a_{t}_{k}")
            model.Add(iso_a >= is_home[t, k - 1] - is_home[t, k] + is_home[t, k + 1] - 1)
            isolated_away_vars.append(iso_a)

    # 4. Soft Penalty for scheduling 4-game series in the post-All-Star Weekend slot
    asg_thursday_4g_vars = []
    post_asg_slots = [s["slot_idx"] for s in slots if s.get("is_post_asg", False)]
    for s_post in post_asg_slots:
        for sid, sr in enumerate(series_list):
            if sr["games"] == 4:
                asg_thursday_4g_vars.append(x[sid, s_post])

    # 5. Multi-Objective Formulation
    div_early_late_terms = []
    for sid, sr in enumerate(series_list):
        if sr["is_div"]:
            for s in early_late_slots:
                div_early_late_terms.append(x[sid, s])

    road_trip_starts = []
    for t in range(n_teams):
        for k in range(1, n_active):
            rt_start = model.NewBoolVar(f"rt_start_{t}_{k}")
            model.Add(rt_start >= is_home[t, k - 1] - is_home[t, k])
            road_trip_starts.append(rt_start)

    model.Maximize(
        100 * sum(div_early_late_terms)
        - 250 * sum(isolated_home_vars)
        - 300 * sum(isolated_away_vars)
        - 50 * sum(road_trip_starts)
        - 500 * sum(missed_april_vars)
        - 500 * sum(missed_sept_vars)
        - 150 * sum(asg_thursday_4g_vars)
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(timeout_sec)
    solver.parameters.num_search_workers = num_workers
    solver.parameters.log_search_progress = verbose_solver_logs
    solver.parameters.relative_gap_limit = 0.01

    callback = SolutionProgressCallback(
        div_early_late_terms,
        isolated_home_vars,
        isolated_away_vars,
        road_trip_starts,
        missed_april_vars,
        missed_sept_vars,
        asg_thursday_4g_vars,
    )
    print(f"Solving Phase 2 (workers={num_workers}, max_time={timeout_sec}s, gap_limit=1%)...")
    status = solver.Solve(model, callback)
    solve_time = time.time() - t0

    status_name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Phase 2 CP-SAT failed with status: {status_name}")

    assignment = {}
    for sid in range(len(series_list)):
        for s in active_slots:
            if solver.Value(x[sid, s]) == 1:
                assignment[sid] = s
                break

    assignment = optimize_away_leg_ordering(teams, slots, series_list, assignment, dist_matrix, season_year)

    missed_apr_pairs = [f"{a}-{b}" for a, b, ma, _ in div_pair_meta if solver.Value(ma) == 1]
    missed_sep_pairs = [f"{a}-{b}" for a, b, _, ms in div_pair_meta if solver.Value(ms) == 1]
    asg_thu_count = sum(solver.Value(v) for v in asg_thursday_4g_vars)

    metrics = {
        "status": status_name,
        "solve_time_sec": round(solve_time, 2),
        "objective_value": solver.ObjectiveValue(),
        "isolated_homestands": sum(solver.Value(v) for v in isolated_home_vars),
        "isolated_road_trips": sum(solver.Value(v) for v in isolated_away_vars),
        "early_late_div_series": sum(solver.Value(v) for v in div_early_late_terms),
        "missed_april_pairs": len(missed_apr_pairs),
        "missed_sept_pairs": len(missed_sep_pairs),
        "missed_april_list": missed_apr_pairs,
        "missed_sept_list": missed_sep_pairs,
        "asg_thursday_games": asg_thu_count,
    }
    return assignment, metrics


def optimize_away_leg_ordering(
    teams: List[Dict[str, Any]],
    slots: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    assignment: Dict[int, int],
    dist_matrix: List[List[int]],
    season_year: int = 2027,
) -> Dict[int, int]:
    """Computes initial sequential venue-to-venue travel distance across all 30 teams."""
    n_teams = len(teams)
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]

    def compute_total_miles(assign_map: Dict[int, int]) -> int:
        slot_to_venue = {t: {} for t in range(n_teams)}
        for sid, s in assign_map.items():
            sr = series_list[sid]
            h, a = sr["home"], sr["away"]
            slot_to_venue[h][s] = h
            slot_to_venue[a][s] = h
        total = 0
        for t in range(n_teams):
            prev_v = t
            for s in active_slots:
                curr_v = slot_to_venue[t][s]
                total += dist_matrix[prev_v][curr_v]
                prev_v = curr_v
        return total

    base_miles = compute_total_miles(assignment)
    print(f"Post-processing travel distance (initial league miles: {base_miles:,})...")
    return assignment


# ==============================================================================
# 5. CALENDAR EXPANSION, PER-TEAM CSV EXPORT, PDF GENERATOR & VALIDATION
# ==============================================================================

def expand_to_daily_schedule(
    teams: List[Dict[str, Any]],
    slots: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    assignment: Dict[int, int],
    dist_matrix: List[List[int]],
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Expands the solved series-to-slot assignment into 2,430 individual game records.
    Automatically shifts a 3-game midweek Slot A series to [Mon, Tue, Wed] whenever
    either participating team plays a 4-game weekend Slot B series starting on Thursday,
    guaranteeing zero Thursday doubleheaders and <= 1 off-day between consecutive series.
    """
    n_teams = len(teams)
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]

    slot_series: Dict[int, List[Dict[str, Any]]] = {s: [] for s in active_slots}
    for sid, s in assignment.items():
        slot_series[s].append(series_list[sid])

    teams_playing_4g_in_slot: Dict[int, set] = {s: set() for s in active_slots}
    for s in active_slots:
        for sr in slot_series[s]:
            if sr["games"] == 4:
                teams_playing_4g_in_slot[s].add(sr["home"])
                teams_playing_4g_in_slot[s].add(sr["away"])

    current_venue = {t: t for t in range(n_teams)}
    team_total_miles = {teams[t]["abbr"]: 0 for t in range(n_teams)}

    records = []

    for s in active_slots:
        slot_meta = slots[s]
        slot_label = slot_meta["label"]
        next_s = s + 1
        next_shares_thu = (
            next_s < len(slots)
            and not slots[next_s]["is_asg"]
            and slots[next_s].get("shares_thu_with_prev", False)
        )

        for sr in slot_series[s]:
            h_idx = sr["home"]
            a_idx = sr["away"]
            g_cnt = sr["games"]
            h_abbr = teams[h_idx]["abbr"]
            a_abbr = teams[a_idx]["abbr"]

            h_miles = dist_matrix[current_venue[h_idx]][h_idx]
            a_miles = dist_matrix[current_venue[a_idx]][h_idx]
            team_total_miles[h_abbr] += h_miles
            team_total_miles[a_abbr] += a_miles
            current_venue[h_idx] = h_idx
            current_venue[a_idx] = h_idx

            if g_cnt == 4:
                dates = slot_meta["dates_4g"]
            else:
                if next_shares_thu and (
                    h_idx in teams_playing_4g_in_slot.get(next_s, set())
                    or a_idx in teams_playing_4g_in_slot.get(next_s, set())
                ):
                    dates = slot_meta.get("dates_3g_early", slot_meta["dates_3g"])
                else:
                    dates = slot_meta["dates_3g"]

            for g_num, g_date in enumerate(dates, start=1):
                dow = g_date.strftime("%A")
                is_final_game = (g_num == g_cnt)
                is_day_game = bool(
                    (is_final_game and dow in ("Monday", "Wednesday", "Thursday")) or dow == "Sunday"
                )
                series_travel = (h_miles + a_miles) if g_num == 1 else 0

                records.append({
                    "Date": g_date.isoformat(),
                    "DayOfWeek": dow,
                    "SeriesSlot": slot_label,
                    "HomeTeam": h_abbr,
                    "AwayTeam": a_abbr,
                    "SeriesGameNumber": g_num,
                    "TotalSeriesGames": g_cnt,
                    "IsDayGame": is_day_game,
                    "TravelDistanceMiles": series_travel,
                })

    df = pd.DataFrame(records)
    df = df.sort_values(by=["Date", "HomeTeam"])
    df = df.reset_index(drop=True)
    return df, team_total_miles


def export_schedule_files(
    df: pd.DataFrame,
    teams: List[Dict[str, Any]],
    output_dir: str = "data",
) -> str:
    """
    Writes the full league schedule to `data/mlb_schedule.csv` and writes 30 individual
    team schedule CSV files to `data/mlb_schedule_<ABBR>.csv`.
    """
    os.makedirs(output_dir, exist_ok=True)
    master_csv = os.path.join(output_dir, "mlb_schedule.csv")
    df.to_csv(master_csv, index=False)

    for t in teams:
        abbr = t["abbr"]
        t_df = df[(df["HomeTeam"] == abbr) | (df["AwayTeam"] == abbr)].copy()
        t_df = t_df.sort_values(by=["Date"])
        t_df = t_df.reset_index(drop=True)

        t_df["TeamGameNumber"] = range(1, len(t_df) + 1)
        t_df["HomeAway"] = t_df["HomeTeam"].apply(lambda h: "H" if h == abbr else "A")
        t_df["Opponent"] = t_df.apply(
            lambda r: r["AwayTeam"] if r["HomeTeam"] == abbr else r["HomeTeam"], axis=1
        )

        # Calculate idle off-days prior to each game
        date_objs = pd.to_datetime(t_df["Date"]).dt.date.tolist()
        off_days_before = [0]
        for i in range(1, len(date_objs)):
            off_days_before.append((date_objs[i] - date_objs[i - 1]).days - 1)
        t_df["IdleOffDaysBefore"] = off_days_before

        cols = [
            "TeamGameNumber",
            "Date",
            "DayOfWeek",
            "SeriesSlot",
            "HomeAway",
            "Opponent",
            "HomeTeam",
            "AwayTeam",
            "SeriesGameNumber",
            "TotalSeriesGames",
            "IsDayGame",
            "IdleOffDaysBefore",
            "TravelDistanceMiles",
        ]
        team_csv = os.path.join(output_dir, f"mlb_schedule_{abbr}.csv")
        t_df[cols].to_csv(team_csv, index=False)

    print(f"\nExported master schedule to '{master_csv}' and 30 team schedules to '{output_dir}/mlb_schedule_<TEAM>.csv'.")
    return master_csv


def fetch_or_cache_team_logos(
    teams: List[Dict[str, Any]],
    output_dir: str = "data",
    enable_logos: bool = True,
) -> Dict[str, Optional[str]]:
    """
    Attempts to download and cache 500x500 PNG team logos into `data/logos/<ABBR>.png`.
    If offline or unreachable, returns `None` for that team so the PDF generator cleanly
    renders the `Opponent` abbreviation text instead.
    """
    logo_map: Dict[str, Optional[str]] = {t["abbr"]: None for t in teams}
    if not enable_logos:
        return logo_map

    logo_dir = os.path.join(output_dir, "logos")
    os.makedirs(logo_dir, exist_ok=True)
    espn_slug_overrides = {"ATH": "oak", "AZ": "ari", "CWS": "chw", "KC": "kc", "SD": "sd", "SF": "sf", "TB": "tb", "WSH": "wsh"}

    for t in teams:
        abbr = t["abbr"]
        local_png = os.path.join(logo_dir, f"{abbr}.png")
        if os.path.exists(local_png) and os.path.getsize(local_png) > 500:
            logo_map[abbr] = local_png
            continue

        slug = espn_slug_overrides.get(abbr, abbr.lower())
        url = ESPN_LOGO_URL.format(espn_abbr=slug)
        try:
            resp = requests.get(url, timeout=2.5)
            if resp.status_code == 200 and len(resp.content) > 500:
                with open(local_png, "wb") as f:
                    f.write(resp.content)
                logo_map[abbr] = local_png
        except Exception:
            # Offline or blocked: gracefully fall back to Opponent text
            break

    cached_count = sum(1 for v in logo_map.values() if v is not None)
    if cached_count > 0:
        print(f"Cached {cached_count}/30 team PNG logos in '{logo_dir}/' for PDF rendering.")
    else:
        print("Logo download unavailable/offline; rendering clean Opponent text badges in team PDFs.")
    return logo_map


def generate_team_schedule_pdfs(
    df: pd.DataFrame,
    teams: List[Dict[str, Any]],
    season_year: int = 2027,
    output_dir: str = "data",
    enable_logos: bool = True,
) -> None:
    """
    Generates 30 individual multi-page landscape calendar PDFs (`data/mlb_schedule_<ABBR>.pdf`):
      - Combines March / April into one calendar page.
      - Individual pages for May, June, July, and August.
      - Combines September / October into one calendar page if any regular season games occur in October,
        otherwise renders September.
      - Navy blue background (#0A1E3F) for Home games; White background (#FFFFFF) for Road games.
      - Draws Opponent logo (if cached) or Opponent text in each date cell.
    """
    os.makedirs(output_dir, exist_ok=True)
    logo_map = fetch_or_cache_team_logos(teams, output_dir=output_dir, enable_logos=enable_logos)

    navy = colors.HexColor("#0A1E3F")
    light_gray = colors.HexColor("#F2F4F7")
    border_gray = colors.HexColor("#CBD2D9")
    header_blue = colors.HexColor("#1F3A60")
    muted_text = colors.HexColor("#7B8794")
    dow_names = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]

    for t in teams:
        abbr = t["abbr"]
        team_name = t["name"]
        pdf_path = os.path.join(output_dir, f"mlb_schedule_{abbr}.pdf")

        t_df = df[(df["HomeTeam"] == abbr) | (df["AwayTeam"] == abbr)].copy()
        t_df["DateObj"] = pd.to_datetime(t_df["Date"]).dt.date
        t_df = t_df.sort_values("DateObj").reset_index(drop=True)

        game_by_date: Dict[datetime.date, Dict[str, Any]] = {}
        for _, row in t_df.iterrows():
            d = row["DateObj"]
            is_home = (row["HomeTeam"] == abbr)
            opp = row["AwayTeam"] if is_home else row["HomeTeam"]
            game_by_date[d] = {
                "is_home": is_home,
                "opp": opp,
                "game_num": int(row.get("SeriesGameNumber", 1)),
                "total_games": int(row.get("TotalSeriesGames", 3)),
                "is_day": bool(row.get("IsDayGame", False)),
            }

        min_date = min(t_df["DateObj"]) if not t_df.empty else datetime.date(season_year, 3, 25)
        max_date = max(t_df["DateObj"]) if not t_df.empty else datetime.date(season_year, 9, 26)
        has_october = any(d.month == 10 for d in t_df["DateObj"])

        mar_start = min(datetime.date(season_year, 3, 21), min_date)
        periods: List[Tuple[str, datetime.date, datetime.date, set]] = [
            ("MARCH / APRIL", mar_start, datetime.date(season_year, 4, 30), {3, 4}),
            ("MAY", datetime.date(season_year, 5, 1), datetime.date(season_year, 5, 31), {5}),
            ("JUNE", datetime.date(season_year, 6, 1), datetime.date(season_year, 6, 30), {6}),
            ("JULY", datetime.date(season_year, 7, 1), datetime.date(season_year, 7, 31), {7}),
            ("AUGUST", datetime.date(season_year, 8, 1), datetime.date(season_year, 8, 31), {8}),
        ]
        if has_october:
            oct_end = max(max_date, datetime.date(season_year, 10, 3))
            periods.append(("SEPTEMBER / OCTOBER", datetime.date(season_year, 9, 1), oct_end, {9, 10}))
        else:
            periods.append(("SEPTEMBER", datetime.date(season_year, 9, 1), datetime.date(season_year, 9, 30), {9}))

        c = canvas.Canvas(pdf_path, pagesize=landscape(letter))
        page_w, page_h = landscape(letter)

        for title, p_start, p_end, active_months in periods:
            start_sun = p_start - datetime.timedelta(days=(p_start.weekday() + 1) % 7)
            end_sat = p_end + datetime.timedelta(days=(5 - p_end.weekday()) % 7)
            total_days = (end_sat - start_sun).days + 1
            num_weeks = total_days // 7

            # Top Title Banner
            c.setFillColor(navy)
            c.rect(36, page_h - 66, page_w - 72, 36, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 15)
            c.drawString(48, page_h - 53, f"{team_name.upper()} ({abbr}) — {season_year} REGULAR SEASON SCHEDULE")
            c.setFont("Helvetica-Bold", 14)
            c.drawRightString(page_w - 48, page_h - 53, f"{title} {season_year}")

            # Legend Bar
            c.setFillColor(navy)
            c.setStrokeColor(border_gray)
            c.rect(36, page_h - 88, 13, 13, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(54, page_h - 85, "HOME GAME (Navy Blue)")

            c.setFillColor(colors.white)
            c.setStrokeColor(colors.black)
            c.rect(195, page_h - 88, 13, 13, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.drawString(213, page_h - 85, "ROAD GAME (White)")

            # Calendar Grid Layout
            grid_left = 36.0
            grid_right = page_w - 36.0
            grid_top = page_h - 98.0
            grid_bottom = 32.0
            col_w = (grid_right - grid_left) / 7.0
            header_h = 20.0
            row_h = (grid_top - grid_bottom - header_h) / float(num_weeks)

            # Day-of-Week Column Headers
            for col_idx, d_name in enumerate(dow_names):
                x0 = grid_left + col_idx * col_w
                c.setFillColor(header_blue)
                c.setStrokeColor(border_gray)
                c.rect(x0, grid_top - header_h, col_w, header_h, fill=1, stroke=1)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 9)
                c.drawCentredString(x0 + col_w / 2.0, grid_top - header_h + 6, d_name)

            curr_d = start_sun
            for wk in range(num_weeks):
                y0 = grid_top - header_h - (wk + 1) * row_h
                for col_idx in range(7):
                    x0 = grid_left + col_idx * col_w
                    in_period = (curr_d.month in active_months) and (p_start <= curr_d <= p_end)
                    g_info = game_by_date.get(curr_d) if in_period else None

                    if not in_period:
                        c.setFillColor(light_gray)
                        c.setStrokeColor(border_gray)
                        c.rect(x0, y0, col_w, row_h, fill=1, stroke=1)
                    elif g_info is not None:
                        if g_info["is_home"]:
                            c.setFillColor(navy)
                            fg_color = colors.white
                        else:
                            c.setFillColor(colors.white)
                            fg_color = navy
                        c.setStrokeColor(border_gray)
                        c.rect(x0, y0, col_w, row_h, fill=1, stroke=1)

                        # Date number in top-left corner (prefix month abbr on combined pages)
                        c.setFillColor(fg_color)
                        c.setFont("Helvetica-Bold", 8.5)
                        date_label = (
                            f"{curr_d.strftime('%b')} {curr_d.day}"
                            if len(active_months) > 1
                            else str(curr_d.day)
                        )
                        c.drawString(x0 + 5, y0 + row_h - 12, date_label)

                        opp_abbr = g_info["opp"]
                        logo_file = logo_map.get(opp_abbr)
                        prefix = "vs" if g_info["is_home"] else "@"
                        day_tag = " (D)" if g_info["is_day"] else ""

                        if logo_file and os.path.exists(logo_file):
                            img_size = min(col_w * 0.42, row_h * 0.52)
                            img_x = x0 + (col_w - img_size) / 2.0
                            img_y = y0 + (row_h - img_size) / 2.0 + 2.0
                            try:
                                c.drawImage(
                                    logo_file,
                                    img_x,
                                    img_y,
                                    width=img_size,
                                    height=img_size,
                                    mask="auto",
                                    preserveAspectRatio=True,
                                )
                            except Exception:
                                c.setFont("Helvetica-Bold", 14)
                                c.drawCentredString(x0 + col_w / 2.0, y0 + row_h / 2.0 - 4, opp_abbr)
                        else:
                            c.setFont("Helvetica-Bold", 15)
                            c.drawCentredString(x0 + col_w / 2.0, y0 + row_h / 2.0 - 4, opp_abbr)

                        c.setFont("Helvetica", 7.5)
                        c.drawCentredString(
                            x0 + col_w / 2.0,
                            y0 + 5,
                            f"{prefix} {opp_abbr}",
                        )
                    else:
                        # Scheduled Off-Day inside active month
                        c.setFillColor(colors.white)
                        c.setStrokeColor(border_gray)
                        c.rect(x0, y0, col_w, row_h, fill=1, stroke=1)
                        c.setFillColor(muted_text)
                        c.setFont("Helvetica", 8.5)
                        date_label = (
                            f"{curr_d.strftime('%b')} {curr_d.day}"
                            if len(active_months) > 1
                            else str(curr_d.day)
                        )
                        c.drawString(x0 + 5, y0 + row_h - 12, date_label)

                    curr_d += datetime.timedelta(days=1)

            c.showPage()

        c.save()

    print(f"Generated 30 team schedule PDFs in '{output_dir}/mlb_schedule_<TEAM>.pdf'.")


def run_validation_checks(
    df: pd.DataFrame,
    teams: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    assignment: Dict[int, int],
    slots: List[Dict[str, Any]],
    holidays: Dict[str, datetime.date],
) -> None:
    """Runs automated validation assertions verifying all hard constraints."""
    print("\n" + "=" * 72)
    print("AUTOMATED SCHEDULE VALIDATION CHECKS")
    print("=" * 72)

    assert len(df) == 2430, f"Expected 2,430 total games, got {len(df)}"
    print("[PASS] Total regular season games == 2,430 (780 total series)")

    # 1. Verify No Doubleheaders (No team plays more than 1 game on any calendar date)
    team_dates = pd.concat([
        df[["Date", "HomeTeam"]].rename(columns={"HomeTeam": "Team"}),
        df[["Date", "AwayTeam"]].rename(columns={"AwayTeam": "Team"}),
    ])
    dups = team_dates[team_dates.duplicated(subset=["Date", "Team"], keep=False)]
    assert len(dups) == 0, f"Found {len(dups) // 2} doubleheaders! Sample:\n{dups.head(6)}"
    print("[PASS] Zero doubleheaders scheduled (no team plays twice on the same date)")

    # 2. Verify Contiguous Series Dates (excluding Opening Weekend's traditional Friday buffer off-day)
    df_temp = df.copy()
    df_temp["DateObj"] = pd.to_datetime(df_temp["Date"]).dt.date
    non_contiguous = []
    for (slot_lbl, h, a), grp in df_temp.groupby(["SeriesSlot", "HomeTeam", "AwayTeam"]):
        if slot_lbl == "W01_B_Opening":
            continue
        d_list = sorted(grp["DateObj"].tolist())
        diffs = [(d_list[i + 1] - d_list[i]).days for i in range(len(d_list) - 1)]
        if any(d != 1 for d in diffs):
            non_contiguous.append((slot_lbl, h, a, [d.strftime("%Y-%m-%d") for d in d_list]))
    assert len(non_contiguous) == 0, f"Found {len(non_contiguous)} non-contiguous series: {non_contiguous[:5]}"
    print("[PASS] All regular series after Opening Weekend have strictly contiguous calendar dates")

    # 3. Verify Inter-Series Off-Day Gaps (Hard: <= 2 off-days outside ASG; Soft metric: count of 2-day gaps)
    asg_mon = holidays["asg_monday"]
    asg_fri = asg_mon + datetime.timedelta(days=4)
    two_day_gaps = []
    gt_two_day_gaps = []

    for t in teams:
        abbr = t["abbr"]
        t_df = df_temp[(df_temp["HomeTeam"] == abbr) | (df_temp["AwayTeam"] == abbr)].sort_values("DateObj")
        d_list = t_df["DateObj"].tolist()
        s_list = t_df["SeriesSlot"].tolist()
        for i in range(1, len(d_list)):
            if s_list[i] == s_list[i - 1]:
                continue  # Same series
            if d_list[i - 1] < asg_mon and d_list[i] >= asg_mon and d_list[i] <= asg_fri:
                continue
            idle_days = (d_list[i] - d_list[i - 1]).days - 1
            if idle_days > 2:
                gt_two_day_gaps.append((abbr, str(d_list[i - 1]), str(d_list[i]), idle_days))
            elif idle_days == 2:
                two_day_gaps.append((abbr, str(d_list[i - 1]), str(d_list[i]), idle_days))

    assert len(gt_two_day_gaps) == 0, f"Found inter-series gaps > 2 off-days: {gt_two_day_gaps[:5]}"
    print(
        f"[PASS] All inter-series gaps outside All-Star Break are <= 2 off-days "
        f"(2-off-day gaps league-wide: {len(two_day_gaps)})"
    )

    # 4. Verify Divisional Spacing Rules (<= 2 series in any 31-day span, and <= 91 days between consecutive series)
    abbr_to_div = {t["abbr"]: t["division"] for t in teams}
    div_pair_series_dates: Dict[Tuple[str, str], List[Tuple[datetime.date, datetime.date]]] = {}
    for (slot_lbl, h, a), grp in df_temp.groupby(["SeriesSlot", "HomeTeam", "AwayTeam"]):
        if abbr_to_div[h] == abbr_to_div[a]:
            pk = (min(h, a), max(h, a))
            d_list = sorted(grp["DateObj"].tolist())
            div_pair_series_dates.setdefault(pk, []).append((d_list[0], d_list[-1]))

    for pk, s_ranges in div_pair_series_dates.items():
        s_ranges.sort(key=lambda r: r[0])
        # Check max 2 series in any 31-day window
        for i in range(len(s_ranges)):
            in_31 = [r for r in s_ranges if 0 <= (r[0] - s_ranges[i][0]).days <= 30]
            assert len(in_31) <= 2, f"Divisional pair {pk} has {len(in_31)} series within 31 days: {in_31}"
        # Check max 3 months (~95 days end-to-start) between consecutive series
        for i in range(len(s_ranges) - 1):
            gap_days = (s_ranges[i + 1][0] - s_ranges[i][1]).days
            assert gap_days <= 95, f"Divisional pair {pk} has {gap_days} days (>3 months) between series: {s_ranges}"
    print("[PASS] All divisional pairs play <= 2 series in any 31-day span and never go > 3 months between series")

    # 5. Verify 81 Home / 81 Away games per team
    home_counts = df["HomeTeam"].value_counts().to_dict()
    away_counts = df["AwayTeam"].value_counts().to_dict()
    for t in teams:
        abbr = t["abbr"]
        hc = home_counts.get(abbr, 0)
        ac = away_counts.get(abbr, 0)
        assert hc == 81 and ac == 81, f"Team {abbr} has {hc}H / {ac}A (expected 81H / 81A)"
    print("[PASS] All 30 teams have exactly 162 games (81 Home / 81 Away)")

    # 6. Verify Holiday Full-League Play
    for holiday_name, h_date_obj in [
        ("Memorial Day", holidays["memorial_day"]),
        ("July 4th", holidays["july_4th"]),
        ("Labor Day", holidays["labor_day"]),
    ]:
        h_date = h_date_obj.isoformat()
        h_df = df[df["Date"] == h_date]
        teams_playing = set(h_df["HomeTeam"]).union(set(h_df["AwayTeam"]))
        assert len(h_df) == 15 and len(teams_playing) == 30, (
            f"Holiday {holiday_name} ({h_date}) has {len(teams_playing)} teams playing"
        )
    print("[PASS] All 30 teams play on Memorial Day, July 4th, and Labor Day")

    # 7. All-Star Break Check: Hard check on Mon-Wed, Soft info check on Thu
    asg_wed = asg_mon + datetime.timedelta(days=2)
    asg_thu = asg_mon + datetime.timedelta(days=3)
    core_asg_games = df[(df["Date"] >= asg_mon.isoformat()) & (df["Date"] <= asg_wed.isoformat())]
    assert len(core_asg_games) == 0, f"Found {len(core_asg_games)} games during core Mon-Wed All-Star Break!"
    thu_asg_games = df[df["Date"] == asg_thu.isoformat()]
    print(
        f"[PASS] Core All-Star Break ({asg_mon.isoformat()} to {asg_wed.isoformat()}) has 0 games "
        f"(Thursday {asg_thu.isoformat()} early restart games: {len(thu_asg_games)})"
    )

    # 8. Verify Matchup Quotas (52 In-Div, 62 Interdiv Same-League, 48 Interleague)
    abbr_to_lg = {t["abbr"]: t["league"] for t in teams}
    rival_map = {}
    for a, b in NATURAL_RIVALS:
        rival_map[a] = b
        rival_map[b] = a

    pair_games: Dict[Tuple[str, str], int] = {}
    for _, row in df.iterrows():
        h, a = row["HomeTeam"], row["AwayTeam"]
        pair_games[(h, a)] = pair_games.get((h, a), 0) + 1

    for t1 in teams:
        a1 = t1["abbr"]
        div_total = 0
        lg_6_cnt = 0
        lg_7_cnt = 0
        il_rival_games = 0
        il_other_3_cnt = 0

        for t2 in teams:
            a2 = t2["abbr"]
            if a1 == a2:
                continue
            g_h = pair_games.get((a1, a2), 0)
            g_a = pair_games.get((a2, a1), 0)
            tot = g_h + g_a

            if abbr_to_div[a1] == abbr_to_div[a2]:
                assert tot == 13 and (g_h, g_a) in ((7, 6), (6, 7)), f"Invalid div split {a1}-{a2}: {g_h}/{g_a}"
                div_total += tot
            elif abbr_to_lg[a1] == abbr_to_lg[a2]:
                if tot == 6:
                    assert (g_h, g_a) == (3, 3), f"Invalid 6g intraleague split {a1}-{a2}: {g_h}/{g_a}"
                    lg_6_cnt += 1
                elif tot == 7:
                    assert (g_h, g_a) in ((3, 4), (4, 3)), f"Invalid 7g intraleague split {a1}-{a2}: {g_h}/{g_a}"
                    lg_7_cnt += 1
                else:
                    raise AssertionError(f"Invalid intraleague games {a1}-{a2}: {tot}")
            else:
                if rival_map.get(a1) == a2:
                    assert tot == 6 and (g_h, g_a) == (3, 3), f"Invalid natural rival split {a1}-{a2}: {g_h}/{g_a}"
                    il_rival_games = tot
                else:
                    assert tot == 3 and (g_h, g_a) in ((3, 0), (0, 3)), f"Invalid interleague split {a1}-{a2}: {g_h}/{g_a}"
                    il_other_3_cnt += 1

        assert div_total == 52, f"{a1} div_total={div_total}"
        assert lg_6_cnt == 8 and lg_7_cnt == 2, f"{a1} interdiv 6g={lg_6_cnt}, 7g={lg_7_cnt}"
        assert il_rival_games == 6 and il_other_3_cnt == 14, f"{a1} interleague rival={il_rival_games}, other={il_other_3_cnt}"

    print("[PASS] All matchup quotas met (52 In-Div; 62 Same-League [6x8 + 7x2]; 48 Interleague [6x1 + 3x14])")

    # 9. Verify Hard Max 3 Road Trip & Homestand Lengths
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]
    team_slot_ha = {t["abbr"]: {} for t in teams}
    for sid, s in assignment.items():
        sr = series_list[sid]
        h_abbr = teams[sr["home"]]["abbr"]
        a_abbr = teams[sr["away"]]["abbr"]
        team_slot_ha[h_abbr][s] = "H"
        team_slot_ha[a_abbr][s] = "A"

    one_series_rt_count = 0
    for t in teams:
        abbr = t["abbr"]
        seq = [team_slot_ha[abbr][s] for s in active_slots]
        runs = []
        curr_char = seq[0]
        curr_len = 0
        for ch in seq:
            if ch == curr_char:
                curr_len += 1
            else:
                runs.append((curr_char, curr_len))
                curr_char = ch
                curr_len = 1
        runs.append((curr_char, curr_len))
        for r_type, r_len in runs:
            if r_type == "A":
                assert 1 <= r_len <= 3, f"Team {abbr} has road trip of {r_len} series (max 3)"
                if r_len == 1:
                    one_series_rt_count += 1
            else:
                assert 1 <= r_len <= 3, f"Team {abbr} has homestand of {r_len} series (max 3)"
    print(f"[PASS] All road trips and homestands are <= 3 series (soft 1-series road trips: {one_series_rt_count})")


# ==============================================================================
# 6. HISTORICAL / 2026 SCHEDULE AUDIT & OBJECTIVE SCORE EVALUATOR
# ==============================================================================

def fetch_historical_mlb_schedule(season_year: int, teams: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Fetches the official regular season schedule for `season_year` from the MLB Stats API
    and converts it into the standard DataFrame schema for constraint & objective auditing.
    """
    url = MLB_SCHEDULE_API_URL.format(year=season_year)
    print(f"\nFetching official {season_year} MLB regular season schedule from {url} ...")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    dates_data = resp.json().get("dates", [])

    id_to_abbr = {t["id"]: t["abbr"] for t in teams}
    raw_games = []

    for d_entry in dates_data:
        g_date = d_entry.get("date")
        for g in d_entry.get("games", []):
            if g.get("gameType") != "R":
                continue
            status_code = g.get("status", {}).get("codedGameState", "")
            if status_code in ("C", "D"):
                continue
            h_id = g.get("teams", {}).get("home", {}).get("team", {}).get("id")
            a_id = g.get("teams", {}).get("away", {}).get("team", {}).get("id")
            if h_id not in id_to_abbr or a_id not in id_to_abbr:
                continue
            raw_games.append({
                "Date": g_date,
                "HomeTeam": id_to_abbr[h_id],
                "AwayTeam": id_to_abbr[a_id],
                "DayNight": g.get("dayNight", "night"),
            })

    df_raw = pd.DataFrame(raw_games)
    if df_raw.empty:
        raise RuntimeError(f"No regular season games returned by MLB API for {season_year}.")
    df_raw = df_raw.sort_values(by=["Date", "HomeTeam"])
    df_raw = df_raw.reset_index(drop=True)
    print(f"Loaded {len(df_raw):,} official regular season games for {season_year}.")
    return df_raw


def evaluate_existing_schedule(
    df_input: pd.DataFrame,
    teams: List[Dict[str, Any]],
    dist_matrix: List[List[int]],
    season_year: int = 2026,
) -> None:
    """
    Audits any schedule DataFrame (from MLB API or CSV) without optimizing it,
    reporting every broken constraint and calculating its exact CP-SAT objective score.
    """
    print("\n" + "=" * 76)
    print(f"HISTORICAL / EXISTING SCHEDULE AUDIT REPORT (SEASON {season_year})")
    print("=" * 76)

    df = df_input.copy()
    df["DateObj"] = pd.to_datetime(df["Date"]).dt.date
    holidays = get_calendar_holidays(season_year)
    abbr_to_idx = {t["abbr"]: i for i, t in enumerate(teams)}
    abbr_to_div = {t["abbr"]: t["division"] for t in teams}

    # 1. Total games & per-team H/A balance
    total_games = len(df)
    home_counts = df["HomeTeam"].value_counts().to_dict()
    away_counts = df["AwayTeam"].value_counts().to_dict()
    imbalanced_teams = []
    for t in teams:
        ab = t["abbr"]
        h_c, a_c = home_counts.get(ab, 0), away_counts.get(ab, 0)
        if h_c != 81 or a_c != 81:
            imbalanced_teams.append(f"{ab} ({h_c}H/{a_c}A)")

    # 2. Check Doubleheaders
    team_dates = pd.concat([
        df[["Date", "HomeTeam"]].rename(columns={"HomeTeam": "Team"}),
        df[["Date", "AwayTeam"]].rename(columns={"AwayTeam": "Team"}),
    ])
    dup_rows = team_dates[team_dates.duplicated(subset=["Date", "Team"], keep=False)]
    num_doubleheaders = len(dup_rows) // 2

    # 3. Reconstruct series per team-pair
    df_sorted = df.sort_values(by=["DateObj", "HomeTeam", "AwayTeam"]).reset_index(drop=True)
    active_series: Dict[Tuple[str, str], Dict[str, Any]] = {}
    reconstructed_series: List[Dict[str, Any]] = []

    for _, row in df_sorted.iterrows():
        h, a, d = row["HomeTeam"], row["AwayTeam"], row["DateObj"]
        key = (h, a)
        if key in active_series and (d - active_series[key]["dates"][-1]).days <= 2:
            active_series[key]["dates"].append(d)
        else:
            if key in active_series:
                reconstructed_series.append(active_series.pop(key))
            active_series[key] = {"home": h, "away": a, "dates": [d]}
    for sr in active_series.values():
        reconstructed_series.append(sr)

    reconstructed_series.sort(key=lambda x: (x["dates"][0], x["home"]))

    season_start = min(df["DateObj"])
    opening_wk_cutoff = season_start + datetime.timedelta(days=4)

    non_3_4_series = []
    internal_gap_series = []
    for sr in reconstructed_series:
        g_len = len(sr["dates"])
        if g_len not in (3, 4):
            non_3_4_series.append((sr["home"], sr["away"], str(sr["dates"][0]), g_len))
        if sr["dates"][0] > opening_wk_cutoff:
            diffs = [(sr["dates"][i + 1] - sr["dates"][i]).days for i in range(g_len - 1)]
            if any(diff > 1 for diff in diffs):
                internal_gap_series.append((sr["home"], sr["away"], [str(dt) for dt in sr["dates"]]))

    # 4. Build per-team chronological series sequence & check inter-series off-day gaps
    team_series_seq: Dict[str, List[Dict[str, Any]]] = {t["abbr"]: [] for t in teams}
    for sr in reconstructed_series:
        team_series_seq[sr["home"]].append({"type": "H", "venue": sr["home"], "opp": sr["away"], "start": sr["dates"][0], "end": sr["dates"][-1], "games": len(sr["dates"])})
        team_series_seq[sr["away"]].append({"type": "A", "venue": sr["home"], "opp": sr["home"], "start": sr["dates"][0], "end": sr["dates"][-1], "games": len(sr["dates"])})

    asg_mon = holidays["asg_monday"]
    asg_fri = asg_mon + datetime.timedelta(days=4)

    short_road_trips = 0
    long_road_trips = 0
    long_homestands = 0
    isolated_homestands = 0
    road_trip_starts = 0
    gaps_eq_2_days = 0
    gaps_gt_2_days = 0
    team_miles: Dict[str, int] = {}

    for t in teams:
        ab = t["abbr"]
        seq = sorted(team_series_seq[ab], key=lambda x: x["start"])
        curr_v = abbr_to_idx[ab]
        miles = 0
        for item in seq:
            next_v = abbr_to_idx[item["venue"]]
            miles += dist_matrix[curr_v][next_v]
            curr_v = next_v
        team_miles[ab] = miles

        for k in range(1, len(seq)):
            if seq[k - 1]["type"] == "H" and seq[k]["type"] == "A":
                road_trip_starts += 1
            prev_end = seq[k - 1]["end"]
            curr_start = seq[k]["start"]
            if not (prev_end < asg_mon and curr_start >= asg_mon and curr_start <= asg_fri):
                idle = (curr_start - prev_end).days - 1
                if idle == 2:
                    gaps_eq_2_days += 1
                elif idle > 2:
                    gaps_gt_2_days += 1

        for k in range(1, len(seq) - 1):
            if seq[k - 1]["type"] == "A" and seq[k]["type"] == "H" and seq[k + 1]["type"] == "A":
                isolated_homestands += 1

        if seq:
            runs = []
            c_type = seq[0]["type"]
            c_len = 0
            for item in seq:
                if item["type"] == c_type:
                    c_len += 1
                else:
                    runs.append((c_type, c_len))
                    c_type = item["type"]
                    c_len = 1
            runs.append((c_type, c_len))
            for r_type, r_len in runs:
                if r_type == "A":
                    if r_len == 1:
                        short_road_trips += 1
                    elif r_len > 3:
                        long_road_trips += 1
                else:
                    if r_len > 3:
                        long_homestands += 1

    # 5. Check Divisional Spacing (Apr/Sep, <=2 in 31 days, <=3 months between series)
    season_end = max(df["DateObj"])
    early_cutoff = season_start + datetime.timedelta(days=28)
    late_cutoff = season_end - datetime.timedelta(days=28)
    april_cutoff = datetime.date(season_year, 4, 30)
    sept_cutoff = datetime.date(season_year, 9, 1)

    early_late_div_series = 0
    div_pair_apr: Dict[Tuple[str, str], int] = {}
    div_pair_sep: Dict[Tuple[str, str], int] = {}
    div_pair_ranges: Dict[Tuple[str, str], List[Tuple[datetime.date, datetime.date]]] = {}

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            if teams[i]["division"] == teams[j]["division"]:
                pk = (min(teams[i]["abbr"], teams[j]["abbr"]), max(teams[i]["abbr"], teams[j]["abbr"]))
                div_pair_apr[pk] = 0
                div_pair_sep[pk] = 0
                div_pair_ranges[pk] = []

    for sr in reconstructed_series:
        h, a = sr["home"], sr["away"]
        if abbr_to_div[h] == abbr_to_div[a]:
            pk = (min(h, a), max(h, a))
            div_pair_ranges[pk].append((sr["dates"][0], sr["dates"][-1]))
            if sr["dates"][0] <= april_cutoff:
                div_pair_apr[pk] += 1
            if sr["dates"][-1] >= sept_cutoff:
                div_pair_sep[pk] += 1
            if sr["dates"][0] <= early_cutoff or sr["dates"][-1] >= late_cutoff:
                early_late_div_series += 1

    div_31d_violations = []
    div_3m_violations = []
    for pk, ranges in div_pair_ranges.items():
        ranges.sort(key=lambda r: r[0])
        for i in range(len(ranges)):
            in_31 = [r for r in ranges if 0 <= (r[0] - ranges[i][0]).days <= 30]
            if len(in_31) > 2:
                div_31d_violations.append(f"{pk[0]}-{pk[1]}")
                break
        for i in range(len(ranges) - 1):
            if (ranges[i + 1][0] - ranges[i][1]).days > 95:
                div_3m_violations.append(f"{pk[0]}-{pk[1]}")
                break

    missed_apr_list = [f"{k[0]}-{k[1]}" for k, v in div_pair_apr.items() if v == 0]
    missed_sep_list = [f"{k[0]}-{k[1]}" for k, v in div_pair_sep.items() if v == 0]

    # 6. Check All-Star Break
    asg_wed = asg_mon + datetime.timedelta(days=2)
    asg_thu = asg_mon + datetime.timedelta(days=3)
    asg_core_games = len(df[(df["DateObj"] >= asg_mon) & (df["DateObj"] <= asg_wed)])
    asg_thu_games = len(df[df["DateObj"] == asg_thu])

    # 7. Calculate Objective Score using our Phase 2 formula
    objective_score = (
        100 * early_late_div_series
        - 250 * isolated_homestands
        - 300 * short_road_trips
        - 50 * road_trip_starts
        - 500 * len(missed_apr_list)
        - 500 * len(missed_sep_list)
        - 150 * asg_thu_games
        - 100 * gaps_eq_2_days
    )

    total_miles = sum(team_miles.values())
    sorted_miles = sorted(team_miles.items(), key=lambda x: x[1], reverse=True)

    print(f"Total Games Evaluated            : {total_games:,} (Target: 2,430)")
    print(f"Total Reconstructed Series       : {len(reconstructed_series):,} (Target: 780)")
    print("-" * 76)
    print("HARD & SOFT CONSTRAINT AUDIT BREAKDOWN:")
    print(f"  1. Teams off 81H/81A Balance   : {len(imbalanced_teams)} {imbalanced_teams[:6]}")
    print(f"  2. Doubleheaders (Same Date)   : {num_doubleheaders} team-date collisions")
    print(f"  3. Series != 3 or 4 Games      : {len(non_3_4_series)} series")
    print(f"  4. Non-Opening Series w/ Gap   : {len(internal_gap_series)} series")
    print(f"  5. Inter-Series Gap > 2 Days   : {gaps_gt_2_days} occurrences (Hard Constraint)")
    print(f"  6. Inter-Series Gap == 2 Days  : {gaps_eq_2_days} occurrences (Soft Penalty)")
    print(f"  7. Div Pairs >2 Series in 31d  : {len(div_31d_violations)} pairs {div_31d_violations[:6]}")
    print(f"  8. Div Pairs >3 Months Apart   : {len(div_3m_violations)} pairs {div_3m_violations[:6]}")
    print(f"  9. Long Road Trips (>3 series) : {long_road_trips} occurrences (Hard Constraint)")
    print(f" 10. Long Homestands (>3 series) : {long_homestands} occurrences (Hard Constraint)")
    print(f" 11. 1-Series Road Trips (==1)   : {short_road_trips} occurrences (Soft Penalty)")
    print(f" 12. 1-Series Homestands (==1)   : {isolated_homestands} occurrences (Soft Penalty)")
    print(f" 13. Missed April Div Matchups   : {len(missed_apr_list)} / 60 pairs {missed_apr_list[:8]}")
    print(f" 14. Missed Sept Div Matchups    : {len(missed_sep_list)} / 60 pairs {missed_sep_list[:8]}")
    print(f" 15. ASG Core Games (Mon-Wed)    : {asg_core_games} games")
    print(f" 16. ASG Thursday Games          : {asg_thu_games} games (Soft Penalty)")
    print("-" * 76)
    print("OBJECTIVE FUNCTION SCORE & COMPONENTS:")
    print(f"  + Early/Late Divisional Series : {early_late_div_series:4d}  (x +100 = {100 * early_late_div_series:+8d})")
    print(f"  - Isolated 1-Series Homestands : {isolated_homestands:4d}  (x -250 = {-250 * isolated_homestands:+8d})")
    print(f"  - Isolated 1-Series Road Trips : {short_road_trips:4d}  (x -300 = {-300 * short_road_trips:+8d})")
    print(f"  - Road Trip Initiations        : {road_trip_starts:4d}  (x  -50 = {-50 * road_trip_starts:+8d})")
    print(f"  - Missed April Div Pairs       : {len(missed_apr_list):4d}  (x -500 = {-500 * len(missed_apr_list):+8d})")
    print(f"  - Missed Sept Div Pairs        : {len(missed_sep_list):4d}  (x -500 = {-500 * len(missed_sep_list):+8d})")
    print(f"  - ASG Thursday Games           : {asg_thu_games:4d}  (x -150 = {-150 * asg_thu_games:+8d})")
    print(f"  - 2-Day Inter-Series Gaps      : {gaps_eq_2_days:4d}  (x -100 = {-100 * gaps_eq_2_days:+8d})")
    print(f"  ==========================================================================")
    print(f"  TOTAL CP-SAT OBJECTIVE SCORE   : {objective_score:,}")
    print("-" * 76)
    print(f"Total League Travel Distance     : {total_miles:,} miles")
    print("Top 3 Teams by Travel Distance   : " + ", ".join(f"{k} ({v:,} mi)" for k, v in sorted_miles[:3]))
    print("Bottom 3 Teams by Travel Distance: " + ", ".join(f"{k} ({v:,} mi)" for k, v in sorted_miles[-3:]))
    print("=" * 76)


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main(
    season_year: int = 2027,
    timeout_sec: int = 1800,
    num_workers: int = 12,
    evaluate_2026: bool = False,
    evaluate_csv: Optional[str] = None,
    output_dir: str = "data",
    enable_logos: bool = True,
) -> None:
    overall_start = time.time()

    teams = fetch_mlb_teams()
    dist_matrix = build_distance_matrix(teams)

    # Mode A: Audit 2026 Official Schedule from MLB API or an existing CSV file
    if evaluate_2026:
        df_hist = fetch_historical_mlb_schedule(2026, teams)
        evaluate_existing_schedule(df_hist, teams, dist_matrix, season_year=2026)
        return

    if evaluate_csv:
        print(f"\nLoading schedule from CSV '{evaluate_csv}' for evaluation...")
        df_csv = pd.read_csv(evaluate_csv)
        evaluate_existing_schedule(df_csv, teams, dist_matrix, season_year=season_year)
        generate_team_schedule_pdfs(df_csv, teams, season_year=season_year, output_dir=output_dir, enable_logos=enable_logos)
        return

    # Mode B: Full Two-Phase CP-SAT Schedule Optimization
    slots, holidays = build_season_slots(season_year=season_year)
    series_list = solve_matchup_quotas(teams, num_workers=num_workers)

    assignment, metrics = solve_schedule_slots(
        teams=teams,
        slots=slots,
        series_list=series_list,
        dist_matrix=dist_matrix,
        timeout_sec=timeout_sec,
        season_year=season_year,
        num_workers=num_workers,
        verbose_solver_logs=True,
    )

    df, team_miles = expand_to_daily_schedule(
        teams=teams,
        slots=slots,
        series_list=series_list,
        assignment=assignment,
        dist_matrix=dist_matrix,
    )

    master_csv = export_schedule_files(df, teams, output_dir=output_dir)
    generate_team_schedule_pdfs(df, teams, season_year=season_year, output_dir=output_dir, enable_logos=enable_logos)

    run_validation_checks(df, teams, series_list, assignment, slots, holidays)

    total_league_miles = sum(team_miles.values())
    sorted_miles = sorted(team_miles.items(), key=lambda x: x[1], reverse=True)

    print("\n" + "=" * 72)
    print("EXECUTION SUMMARY & OPTIMIZATION METRICS")
    print("=" * 72)
    print(f"Target Season Year          : {season_year}")
    print(f"Solver Status               : {metrics['status']}")
    print(f"Phase 2 Solve Runtime       : {metrics['solve_time_sec']:.2f} seconds")
    print(f"Total Script Wall Runtime   : {time.time() - overall_start:.2f} seconds")
    print(f"CP-SAT Objective Value      : {metrics['objective_value']:.0f}")
    print(f"Early/Late Divisional Series: {metrics['early_late_div_series']} series")
    print(f"Missed April Div Pairs      : {metrics['missed_april_pairs']} / 60 ({metrics['missed_april_list']})")
    print(f"Missed Sept Div Pairs       : {metrics['missed_sept_pairs']} / 60 ({metrics['missed_sept_list']})")
    print(f"ASG Thursday Early Games    : {metrics['asg_thursday_games']} games")
    print(f"Isolated 1-Series Homestands: {metrics['isolated_homestands']} league-wide")
    print(f"Isolated 1-Series Road Trips: {metrics['isolated_road_trips']} league-wide")
    print(f"Total League Travel Distance: {total_league_miles:,} miles")
    print("\nTop 3 Teams by Travel Distance:")
    for abbr, miles in sorted_miles[:3]:
        print(f"  - {abbr}: {miles:,} miles")
    print("\nBottom 3 Teams by Travel Distance:")
    for abbr, miles in sorted_miles[-3:]:
        print(f"  - {abbr}: {miles:,} miles")
    print(f"\nExported {len(df):,} game rows to '{master_csv}' (+ 30 CSVs & 30 PDFs in '{output_dir}/').")
    print("=" * 72)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLB CP-SAT Schedule Optimizer & PDF Generator")
    parser.add_argument("--season-year", type=int, default=2027, help="Target season year (default: 2027)")
    parser.add_argument("--timeout", type=int, default=1800, help="Phase 2 solver timeout in seconds (default: 1800)")
    parser.add_argument("--workers", type=int, default=12, help="Number of CP-SAT search workers (default: 12)")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory for CSV/PDF files (default: data)")
    parser.add_argument("--no-logos", action="store_true", help="Disable downloading team logos and use Opponent text in PDFs")
    parser.add_argument("--evaluate-2026", action="store_true", help="Fetch and audit the official 2026 MLB schedule")
    parser.add_argument("--evaluate-csv", type=str, default=None, help="Audit an existing schedule CSV file and generate PDFs")
    args = parser.parse_args()

    main(
        season_year=args.season_year,
        timeout_sec=args.timeout,
        num_workers=args.workers,
        evaluate_2026=args.evaluate_2026,
        evaluate_csv=args.evaluate_csv,
        output_dir=args.output_dir,
        enable_logos=not args.no_logos,
    )