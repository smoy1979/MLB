#!/usr/bin/env python3
"""
MLB League-Wide Regular Season Schedule Optimizer, 1-Page Portrait PDF Calendar Generator,
and Historical Schedule Evaluator using Google OR-Tools CP-SAT.

Usage:
  1. Optimize 2027 schedule (30-min timeout, exports CSVs + 30 1-Page Team PDFs to data/):
     python mlb_scheduler_9.py

  2. Evaluate official 2026 MLB schedule from MLB Stats API (no optimization):
     python mlb_scheduler_9.py --evaluate-year=2026

  3. Evaluate any existing schedule CSV file (and generate 1-page PDFs from it):
     python mlb_scheduler_9.py --evaluate-csv=data/mlb_schedule.csv --season-year=2027
"""

import argparse
import os
import math
import time
import datetime
from typing import Dict, List, Tuple, Any, Optional
import itertools
import requests
import pandas as pd
from ortools.sat.python import cp_model

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas


from dataclasses import dataclass

@dataclass
class ScheduleConfig:
    """
    Single source of truth for all CP-SAT hard constraints and soft objective weights.
    """
    name: str = "custom"

    # --- Hard Constraint Toggles & Thresholds ---
    max_consec_play_days_hard: int = 16
    soft_streak_threshold: int = 9
    max_homestand_roadtrip_hard: int = 4
    enforce_no_b2b_div_hard: bool = True
    force_no_asg_thursday_hard: bool = False
    max_isolated_series_per_team: int = 2

    # --- Soft Objective Weights ---
    w_early_late_div: int = 150
    w_isolated_home: int = -250
    w_isolated_away: int = -400
    w_long_home: int = -650
    w_long_away: int = -650
    w_road_trip_start: int = -50
    w_missed_april_div: int = -1500
    w_missed_sept_div: int = -1500
    w_div_31d_excess: int = -300
    w_div_91d_gap: int = -300
    w_asg_thursday_game: int = -1000
    w_streak_over_threshold: int = -150
    w_consec_dow_off: int = -150
    w_tz_shift_ge2: int = -250
    w_tz_abs_hour: int = -125
    w_gap_2d: int = -100
    w_regional_road_pair: int = 150   # Bonus per road trip pairing host venues <= 350 mi


def get_schedule_config(profile: str = "custom") -> ScheduleConfig:
    """Returns the centralized ScheduleConfig for the requested optimization profile."""
    if profile == "mlb_mimic":
        return ScheduleConfig(
            name="mlb_mimic",
            max_consec_play_days_hard=20,     # Proven fast search space (no hard-cap deadlocks)
            soft_streak_threshold=12,         # Penalize streaks > 12 days
            max_homestand_roadtrip_hard=4,    # Keep at 4 hard so LNS can freely swap series
            enforce_no_b2b_div_hard=False,    # Keep off so divisional series don't block road swings
            force_no_asg_thursday_hard=False, # Handled via -2500 soft weight
            max_isolated_series_per_team=0,   # Handled via soft weights

            w_early_late_div=0,
            w_isolated_home=-950,             # Up from -650 to compress IsoH
            w_isolated_away=-1150,            # Up from -850 to compress IsoA
            w_long_home=-1500,                # Up from -800 so 4-series stands are rarely used
            w_long_away=-1500,                # Up from -800 so 4-series trips are rarely used
            w_road_trip_start=-250,           # Up from -120 to penalize excess H->A transitions
            w_missed_april_div=0,
            w_missed_sept_div=-200,
            w_div_31d_excess=0,
            w_div_91d_gap=0,
            w_asg_thursday_game=-2500,
            w_streak_over_threshold=-60,
            w_consec_dow_off=-75,
            w_tz_shift_ge2=-750,
            w_tz_abs_hour=-300,
            w_gap_2d=0,
            w_regional_road_pair=350,         # Strong bonus for chaining close away venues
        )
    return ScheduleConfig(name="custom")


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

# Venue UTC-relative time zone offsets for regular season (EDT=0, CDT=-1, MDT/MST=-2, PDT=-3)
TEAM_TIMEZONES: Dict[str, int] = {
    # Eastern (0)
    "BAL": 0, "BOS": 0, "NYY": 0, "TB": 0, "TOR": 0,
    "CLE": 0, "DET": 0, "ATL": 0, "MIA": 0, "NYM": 0,
    "PHI": 0, "WSH": 0, "CIN": 0, "PIT": 0,
    # Central (-1)
    "CWS": -1, "KC": -1, "MIN": -1, "HOU": -1, "TEX": -1,
    "CHC": -1, "MIL": -1, "STL": -1,
    # Mountain / Arizona (-2)
    "COL": -2, "AZ": -2,
    # Pacific (-3)
    "LAA": -3, "ATH": -3, "SEA": -3, "LAD": -3, "SD": -3, "SF": -3,
}

NATURAL_RIVALS: List[Tuple[str, str]] = [
    ("BAL", "WSH"), ("BOS", "ATL"), ("NYY", "NYM"), ("TB", "MIA"), ("TOR", "PHI"),
    ("CWS", "CHC"), ("CLE", "CIN"), ("DET", "PIT"), ("KC", "STL"), ("MIN", "MIL"),
    ("HOU", "COL"), ("LAA", "LAD"), ("ATH", "SF"), ("SEA", "SD"), ("TEX", "AZ")
]


def build_timezone_matrix(teams: List[Dict[str, Any]]) -> List[List[int]]:
    """Returns a 30x30 matrix where entry (i, j) is the absolute hour difference between venues."""
    n = len(teams)
    tz_diff = [[0] * n for _ in range(n)]
    for i in range(n):
        tz_i = TEAM_TIMEZONES.get(teams[i]["abbr"], 0)
        for j in range(n):
            tz_j = TEAM_TIMEZONES.get(teams[j]["abbr"], 0)
            tz_diff[i][j] = abs(tz_i - tz_j)
    return tz_diff


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


def optimize_away_leg_ordering(
    teams: List[Dict[str, Any]],
    slots: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    assignment: Dict[int, int],
    dist_matrix: List[List[int]],
    season_year: int = 2027,
) -> Dict[int, int]:
    """
    Post-optimization TSP optimizer:
    Identifies multi-series road trips for each team and evaluates valid slot permutations
    of those away series to minimize sequential venue-to-venue Haversine travel distance,
    without altering home dates, series lengths, or rest constraints.
    """
    n_teams = len(teams)
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]
    slot_to_series = {s: [] for s in active_slots}
    for sid, s in assignment.items():
        slot_to_series[s].append(sid)

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
            total += dist_matrix[prev_v][t]  # return home
        return total

    initial_miles = compute_total_miles(assignment)
    print(f"\nPost-processing travel routing (Initial league travel: {initial_miles:,} miles)...")

    improved_assignment = dict(assignment)

    # For each team, identify consecutive road series runs (length 2 or 3)
    team_away_slots: Dict[int, List[int]] = {t: [] for t in range(n_teams)}
    for sid, s in improved_assignment.items():
        a = series_list[sid]["away"]
        team_away_slots[a].append(s)

    swaps_made = 0
    for t in range(n_teams):
        a_slots = sorted(team_away_slots[t])
        # Find runs of consecutive active slots where team t is away
        runs = []
        curr_run = []
        for s in a_slots:
            if not curr_run or active_slots.index(s) == active_slots.index(curr_run[-1]) + 1:
                curr_run.append(s)
            else:
                if len(curr_run) in (2, 3):
                    runs.append(list(curr_run))
                curr_run = [s]
        if len(curr_run) in (2, 3):
            runs.append(list(curr_run))

        for run in runs:
            # Series played by team t in this road trip
            run_sids = [sid for s in run for sid in slot_to_series[s] if series_list[sid]["away"] == t]
            if len(run_sids) != len(run):
                continue

            # Prior venue (before road trip) and next venue (after road trip)
            k_first = active_slots.index(run[0])
            k_last = active_slots.index(run[-1])
            prev_v = t if k_first == 0 else [
                series_list[sid]["home"] for sid in slot_to_series[active_slots[k_first - 1]]
                if series_list[sid]["home"] == t or series_list[sid]["away"] == t
            ][0]
            next_v = t if k_last == len(active_slots) - 1 else [
                series_list[sid]["home"] for sid in slot_to_series[active_slots[k_last + 1]]
                if series_list[sid]["home"] == t or series_list[sid]["away"] == t
            ][0]

            best_order = run_sids
            best_cost = None

            for perm in itertools.permutations(run_sids):
                # Verify 4-game / 3-game compatibility with slots in run
                valid = True
                for slot_idx, cand_sid in zip(run, perm):
                    cand_sr = series_list[cand_sid]
                    if slots[slot_idx].get("force_3g", False) and cand_sr["games"] == 4:
                        valid = False
                        break
                    # Verify opponent does not have a conflict in that slot
                    opp = cand_sr["home"]
                    opp_sids_in_slot = [sid for sid in slot_to_series[slot_idx] if sid != cand_sid]
                    if any(series_list[sid]["home"] == opp or series_list[sid]["away"] == opp for sid in opp_sids_in_slot):
                        valid = False
                        break
                if not valid:
                    continue

                # Compute distance for this candidate ordering: prev_v -> h1 -> h2 (-> h3) -> next_v
                venues = [series_list[sid]["home"] for sid in perm]
                cost = dist_matrix[prev_v][venues[0]]
                for i in range(len(venues) - 1):
                    cost += dist_matrix[venues[i]][venues[i + 1]]
                cost += dist_matrix[venues[-1]][next_v]

                if best_cost is None or cost < best_cost:
                    best_cost = cost
                    best_order = perm

            if best_order != run_sids:
                # Apply the swap
                for slot_idx, new_sid, old_sid in zip(run, best_order, run_sids):
                    improved_assignment[new_sid] = slot_idx
                    slot_to_series[slot_idx].remove(old_sid)
                    slot_to_series[slot_idx].append(new_sid)
                swaps_made += 1

    final_miles = compute_total_miles(improved_assignment)
    print(f"Post-processing complete: Made {swaps_made} road-trip route swaps. New total travel: {final_miles:,} miles.")
    return improved_assignment


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

def solve_matchup_quotas(
    teams: List[Dict[str, Any]],
    dist_matrix: List[List[int]],
    num_workers: int = 12,
) -> List[Dict[str, Any]]:
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
                s3[i, j] = model.NewBoolVar(f"s3_{i}_{j}")
                s4[i, j] = model.NewBoolVar(f"s4_{i}_{j}")
                model.Add(s3[i, j] + s4[i, j] == 1)
            elif is_rival:
                s3[i, j] = model.NewConstant(1)
                s4[i, j] = model.NewConstant(0)
            else:
                s3[i, j] = model.NewBoolVar(f"s3_{i}_{j}")
                s4[i, j] = model.NewConstant(0)

    for i in range(n):
        for j in range(i + 1, n):
            same_div = teams[i]["division"] == teams[j]["division"]
            same_lg = teams[i]["league"] == teams[j]["league"]
            is_rival = (i, j) in rival_set

            if same_div:
                model.Add(s3[i, j] + s3[j, i] == 3)
                model.Add(s4[i, j] + s4[j, i] == 1)
                model.Add(s3[i, j] + s4[i, j] == 2)
                model.Add(s3[j, i] + s4[j, i] == 2)
            elif same_lg:
                model.Add(s4[i, j] + s4[j, i] <= 1)
            elif not is_rival:
                model.Add(s3[i, j] + s3[j, i] == 1)

    for i in range(n):
        non_div_lg = [
            j for j in range(n)
            if j != i and teams[j]["league"] == teams[i]["league"] and teams[j]["division"] != teams[i]["division"]
        ]
        model.Add(sum(s4[i, j] + s4[j, i] for j in non_div_lg) == 2)

        home_games = sum(3 * s3[i, j] + 4 * s4[i, j] for j in range(n) if j != i)
        away_games = sum(3 * s3[j, i] + 4 * s4[j, i] for j in range(n) if j != i)
        model.Add(home_games == 81)
        model.Add(away_games == 81)

    # Phase 1 Geographic Pairing Objective:
    # Ensure each team's away interleague opponents are geographically clustered (<= 350 miles)
    # so Phase 2 can chain them into low-mileage multi-series road trips.
    pair_bonuses = []
    for i in range(n):
        il_opps = [j for j in range(n) if teams[j]["league"] != teams[i]["league"]]
        for idx1 in range(len(il_opps)):
            j1 = il_opps[idx1]
            for idx2 in range(idx1 + 1, len(il_opps)):
                j2 = il_opps[idx2]
                if dist_matrix[j1][j2] <= 350:
                    both_away = model.NewBoolVar(f"p1_cl_{i}_{j1}_{j2}")
                    model.Add(both_away <= s3[j1, i])
                    model.Add(both_away <= s3[j2, i])
                    pair_bonuses.append(both_away)

    model.Maximize(sum(pair_bonuses))

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
        streak_gt9_vars: List[Any],
        consec_dow_vars: List[Any],
    ):
        super().__init__()
        self._div_vars = div_vars
        self._iso_h_vars = iso_h_vars
        self._iso_a_vars = iso_a_vars
        self._rt_vars = rt_vars
        self._miss_apr_vars = miss_apr_vars
        self._miss_sep_vars = miss_sep_vars
        self._asg_thu_vars = asg_thu_vars
        self._streak_gt9_vars = streak_gt9_vars
        self._consec_dow_vars = consec_dow_vars
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
        strk_9 = sum(self.Value(v) for v in self._streak_gt9_vars)
        dow_pen = sum(self.Value(v) for v in self._consec_dow_vars)
        print(
            f"  [Solution #{self._solution_count:02d} @ {elapsed:6.1f}s] "
            f"Obj: {obj:8.0f} (Bound: {bound:8.0f}) | "
            f"Miss Apr/Sep: {m_apr:2d}/{m_sep:2d} | "
            f"1-Ser H/A: {iso_h:2d}/{iso_a:2d} | "
            f">9d Streak: {strk_9:3d} | "
            f"Mon/Thu Off Pen: {dow_pen:2d} | "
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
    cfg: ScheduleConfig = ScheduleConfig(),
) -> Tuple[Dict[int, int], Dict[str, Any]]:
    """
    Phase 2 CP-SAT Model:
    Assigns all 780 series to the 52 active half-week slots.
    Enforces <= 16 consecutive playing days (hard), <= 3 consecutive weeks with Monday
    or Thursday off-days (hard), and soft penalties for playing streaks > 9 days.
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

    # REQUIRED: Every series must be assigned to exactly one active slot
    for sid, sr in enumerate(series_list):
        model.AddExactlyOne(x[sid, s] for s in active_slots)
        for s in active_slots:
            if slots[s].get("force_3g", False) and sr["games"] == 4:
                model.Add(x[sid, s] == 0)

    # Optional Hard No-ASG-Thursday Rule
    if cfg.force_no_asg_thursday_hard:
        for s_post in [s["slot_idx"] for s in slots if s.get("is_post_asg", False)]:
            for sid, sr in enumerate(series_list):
                if sr["games"] == 4:
                    model.Add(x[sid, s_post] == 0)

    # Break symmetry between identical series in the same matchup bucket
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
    is_4g = {}
    for t in range(n_teams):
        for k, s in enumerate(active_slots):
            is_home[t, k] = model.NewBoolVar(f"home_{t}_{k}")
            h_vars = [x[sid, s] for sid in home_series_by_team[t]]
            a_vars = [x[sid, s] for sid in away_series_by_team[t]]
            model.AddExactlyOne(h_vars + a_vars)
            model.Add(sum(h_vars) == is_home[t, k])

            f4_vars = [x[sid, s] for sid in four_game_series_by_team[t]]
            if slots[s].get("force_3g", False) or not f4_vars:
                is_4g[t, s] = 0
            else:
                b4 = model.NewBoolVar(f"is4g_{t}_{s}")
                model.Add(sum(f4_vars) == b4)
                is_4g[t, s] = b4

    # Hard No-Doubleheader Constraint
    for s_b in active_slots:
        if slots[s_b].get("shares_thu_with_prev", False):
            s_a = s_b - 1
            if s_a in active_slots:
                for t in range(n_teams):
                    model.Add(is_4g[t, s_a] + is_4g[t, s_b] <= 1)

    # --------------------------------------------------------------------------
    # SOFT PENALTY: > 3 Consecutive Weeks with Monday or Thursday Off-Days
    # --------------------------------------------------------------------------
    weeks_meta = []
    curr_s = 1
    while curr_s < len(slots) - 1:
        s_a = curr_s
        s_b = curr_s + 1
        if not slots[s_a]["is_asg"] and not slots[s_b]["is_asg"]:
            weeks_meta.append((s_a, s_b))
        curr_s += 2

    consec_dow_off_penalties = []

    for t in range(n_teams):
        mon_off_vars = []
        thu_off_vars = []

        for w_idx, (s_a, s_b) in enumerate(weeks_meta):
            prev_s_b = weeks_meta[w_idx - 1][1] if w_idx > 0 else 0
            prev_wrap = slots[prev_s_b].get("is_monday_holiday_wrap", False)

            if prev_wrap or slots[s_a].get("holiday") == "July 4th":
                mon_off = model.NewConstant(0)
            else:
                mon_off = model.NewBoolVar(f"mon_off_{t}_{w_idx}")
                model.Add(mon_off == 1 - is_4g[t, s_a])
            mon_off_vars.append(mon_off)

            if slots[s_b].get("shares_thu_with_prev", False):
                thu_off = model.NewBoolVar(f"thu_off_{t}_{w_idx}")
                model.Add(thu_off == 1 - is_4g[t, s_b])
            else:
                thu_off = model.NewConstant(0)
            thu_off_vars.append(thu_off)

        # Soft penalties: trigger when a team has 4 consecutive weeks with Monday or Thursday off
        for i in range(len(mon_off_vars) - 3):
            mon_pen = model.NewBoolVar(f"mon_pen_{t}_{i}")
            model.Add(sum(mon_off_vars[i:i + 4]) - 3 <= mon_pen)
            consec_dow_off_penalties.append(mon_pen)

        for i in range(len(thu_off_vars) - 3):
            thu_pen = model.NewBoolVar(f"thu_pen_{t}_{i}")
            model.Add(sum(thu_off_vars[i:i + 4]) - 3 <= thu_pen)
            consec_dow_off_penalties.append(thu_pen)

    # --------------------------------------------------------------------------
    # CONSECUTIVE PLAYING DAYS: Hard < 17 Days (<= 16 days), Soft Penalty > 9 Days
    # --------------------------------------------------------------------------
    season_start_date = slots[0]["dates_4g"][0]
    season_end_date = slots[-1]["dates_4g"][-1]
    total_cal_days = (season_end_date - season_start_date).days + 1
    cal_dates = [season_start_date + datetime.timedelta(days=d) for d in range(total_cal_days)]

    slot_by_idx = {s["slot_idx"]: s for s in slots}
    streak_over_9_vars = []

    for t in range(n_teams):
        play_day: Dict[datetime.date, Any] = {d: 0 for d in cal_dates}

        for s in active_slots:
            s_meta = slot_by_idx[s]
            d3 = set(s_meta["dates_3g"])
            d4 = set(s_meta["dates_4g"])
            for d in d3.intersection(d4):
                play_day[d] = 1
            for d in (d4 - d3):
                play_day[d] = play_day[d] + is_4g[t, s]

        if cfg.max_consec_play_days_hard > 0:
            win_len = cfg.max_consec_play_days_hard + 1
            for d_idx in range(total_cal_days - cfg.max_consec_play_days_hard):
                win_hard = [play_day[cal_dates[d_idx + k]] for k in range(win_len)]
                model.Add(sum(win_hard) <= cfg.max_consec_play_days_hard)

        if cfg.w_streak_over_threshold != 0:
            s_win_len = cfg.soft_streak_threshold + 1
            for d_idx in range(total_cal_days - cfg.soft_streak_threshold):
                win_soft = [play_day[cal_dates[d_idx + k]] for k in range(s_win_len)]
                if any(isinstance(v, int) and v == 0 for v in win_soft):
                    continue
                ov_strk = model.NewBoolVar(f"strk_gt_{t}_{d_idx}")
                model.Add(ov_strk >= sum(win_soft) - cfg.soft_streak_threshold)
                streak_over_9_vars.append(ov_strk)

    missed_april_vars = []
    missed_sept_vars = []
    div_pair_meta = []
    div_31d_pen_vars = []
    div_91d_pen_vars = []

    for (t1, t2), sids in pair_series.items():
        if teams[t1]["division"] == teams[t2]["division"]:
            if cfg.w_missed_april_div != 0:
                miss_apr = model.NewBoolVar(f"miss_apr_{t1}_{t2}")
                model.Add(sum(x[sid, s] for sid in sids for s in april_slots) + miss_apr >= 1)
                missed_april_vars.append(miss_apr)
            else:
                miss_apr = model.NewConstant(0)

            if cfg.w_missed_sept_div != 0:
                miss_sep = model.NewBoolVar(f"miss_sep_{t1}_{t2}")
                model.Add(sum(x[sid, s] for sid in sids for s in sept_slots) + miss_sep >= 1)
                missed_sept_vars.append(miss_sep)
            else:
                miss_sep = model.NewConstant(0)

            div_pair_meta.append((teams[t1]["abbr"], teams[t2]["abbr"], miss_apr, miss_sep))

            if cfg.enforce_no_b2b_div_hard:
                for k in range(n_active - 1):
                    s_curr, s_next = active_slots[k], active_slots[k + 1]
                    model.Add(sum(x[sid, s_curr] + x[sid, s_next] for sid in sids) <= 1)

            if cfg.w_div_31d_excess != 0:
                for w_idx, win_31 in enumerate(windows_31d):
                    ov_31 = model.NewBoolVar(f"div31_{t1}_{t2}_{w_idx}")
                    model.Add(sum(x[sid, s] for sid in sids for s in win_31) - 2 <= ov_31)
                    model.Add(sum(x[sid, s] for sid in sids for s in win_31) <= 3)
                    div_31d_pen_vars.append(ov_31)

            if cfg.w_div_91d_gap != 0:
                for w_idx, win_91 in enumerate(windows_91d):
                    miss_91 = model.NewBoolVar(f"div91_{t1}_{t2}_{w_idx}")
                    model.Add(sum(x[sid, s] for sid in sids for s in win_91) + miss_91 >= 1)
                    div_91d_pen_vars.append(miss_91)

    isolated_home_vars = []
    isolated_away_vars = []
    long_home_vars = []
    long_away_vars = []

    for t in range(n_teams):
        # Hard cap homestands and road trips to <= max_homestand_roadtrip_hard (e.g. 3 or 4 series)
        if cfg.max_homestand_roadtrip_hard > 0:
            hard_w = cfg.max_homestand_roadtrip_hard + 1
            for k in range(n_active - cfg.max_homestand_roadtrip_hard):
                win_h = [is_home[t, k + d] for d in range(hard_w)]
                model.Add(sum(win_h) <= cfg.max_homestand_roadtrip_hard)
                model.Add(sum(win_h) >= 1)

        # Soft penalty for 4 consecutive Home or Away series when hard cap is > 3
        if cfg.max_homestand_roadtrip_hard > 3 and (cfg.w_long_home != 0 or cfg.w_long_away != 0):
            for k in range(n_active - 3):
                window = [is_home[t, k + d] for d in range(4)]
                if cfg.w_long_home != 0:
                    lh = model.NewBoolVar(f"long_h_{t}_{k}")
                    model.Add(sum(window) - 3 <= lh)
                    long_home_vars.append(lh)
                if cfg.w_long_away != 0:
                    la = model.NewBoolVar(f"long_a_{t}_{k}")
                    model.Add(1 - sum(window) <= la)
                    long_away_vars.append(la)

        # Track single-series homestands (A -> H -> A) and single-series road trips (H -> A -> H)
        iso_h_start = model.NewBoolVar(f"iso_h_start_{t}")
        model.Add(iso_h_start >= is_home[t, 0] - is_home[t, 1])
        isolated_home_vars.append(iso_h_start)

        iso_h_end = model.NewBoolVar(f"iso_h_end_{t}")
        model.Add(iso_h_end >= is_home[t, n_active - 1] - is_home[t, n_active - 2])
        isolated_home_vars.append(iso_h_end)

        iso_a_start = model.NewBoolVar(f"iso_a_start_{t}")
        model.Add(iso_a_start >= is_home[t, 1] - is_home[t, 0])
        isolated_away_vars.append(iso_a_start)

        iso_a_end = model.NewBoolVar(f"iso_a_end_{t}")
        model.Add(iso_a_end >= is_home[t, n_active - 2] - is_home[t, n_active - 1])
        isolated_away_vars.append(iso_a_end)

        team_iso_h = [iso_h_start, iso_h_end]
        team_iso_a = [iso_a_start, iso_a_end]

        for k in range(1, n_active - 1):
            iso_h = model.NewBoolVar(f"iso_h_{t}_{k}")
            model.Add(iso_h >= is_home[t, k] - is_home[t, k - 1] - is_home[t, k + 1])
            isolated_home_vars.append(iso_h)
            team_iso_h.append(iso_h)

            iso_a = model.NewBoolVar(f"iso_a_{t}_{k}")
            model.Add(iso_a >= is_home[t, k - 1] - is_home[t, k] + is_home[t, k + 1] - 1)
            isolated_away_vars.append(iso_a)
            team_iso_a.append(iso_a)

        # Enforce MLB homestand/roadtrip rhythm: cap isolated series per team to <= max_isolated_series_per_team
        if cfg.max_isolated_series_per_team > 0:
            model.Add(sum(team_iso_h) <= cfg.max_isolated_series_per_team)
            model.Add(sum(team_iso_a) <= cfg.max_isolated_series_per_team)

    asg_thursday_4g_vars = []
    post_asg_slots = [s["slot_idx"] for s in slots if s.get("is_post_asg", False)]
    for s_post in post_asg_slots:
        for sid, sr in enumerate(series_list):
            if sr["games"] == 4:
                asg_thursday_4g_vars.append(x[sid, s_post])

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

    # --------------------------------------------------------------------------
    # TIME ZONE SHIFTS (All 1h+ shifts & >= 2h jumps)
    # --------------------------------------------------------------------------
    venue_tz_val = [abs(TEAM_TIMEZONES.get(teams[h]["abbr"], 0)) for h in range(n_teams)]

    tz_shifts_ge2_vars = []
    tz_abs_vars = []
    for t in range(n_teams):
        t_sids = home_series_by_team[t] + away_series_by_team[t]

        for k in range(n_active - 1):
            s_curr, s_next = active_slots[k], active_slots[k + 1]
            if (s_next - s_curr) > 1:
                continue

            tz_curr = sum(venue_tz_val[series_list[sid]["home"]] * x[sid, s_curr] for sid in t_sids)
            tz_next = sum(venue_tz_val[series_list[sid]["home"]] * x[sid, s_next] for sid in t_sids)

            tz_diff = model.NewIntVar(-3, 3, f"tz_diff_{t}_{k}")
            model.Add(tz_diff == tz_next - tz_curr)
            tz_abs = model.NewIntVar(0, 3, f"tz_abs_{t}_{k}")
            model.AddAbsEquality(tz_abs, tz_diff)
            tz_abs_vars.append(tz_abs)

            tz_ge2 = model.NewBoolVar(f"tz_ge2_{t}_{k}")
            model.Add(tz_abs - 1 <= 2 * tz_ge2)
            tz_shifts_ge2_vars.append(tz_ge2)

    # --------------------------------------------------------------------------
    # DIRECT LINEAR HOME <-> AWAY FLIGHT MILEAGE & REGIONAL ROAD PAIRING
    # --------------------------------------------------------------------------
    # 1. Penalize flying from Home -> Away (start of road trip) and Away -> Home (end of road trip)
    #    scaled by distance // 10. This requires ONLY 1 boolean per (away_series, slot) —
    #    ZERO quadratic series pairs! It strongly penalizes 1-series cross-country trips
    #    and forces West/East teams to stay on the road for 2-3 series once they fly out.
    ha_flight_10mi_terms = []
    for t in range(n_teams):
        for sid in away_series_by_team[t]:
            h_venue = series_list[sid]["home"]
            d_10 = dist_matrix[t][h_venue] // 10
            if d_10 <= 0:
                continue

            for k in range(n_active - 1):
                s_curr, s_next = active_slots[k], active_slots[k + 1]
                if (s_next - s_curr) > 1:
                    continue

                # Outbound flight: Home in k -> Away(sid) in k+1
                # Linear inequality: fly_out >= is_home[t, k] + x[sid, s_next] - 1
                fly_out = model.NewBoolVar(f"fo_{t}_{k}_{sid}")
                model.Add(fly_out >= is_home[t, k] + x[sid, s_next] - 1)
                ha_flight_10mi_terms.append(d_10 * fly_out)

                # Inbound flight: Away(sid) in k -> Home in k+1
                # Linear inequality: fly_in >= x[sid, s_curr] + is_home[t, k+1] - 1
                fly_in = model.NewBoolVar(f"fi_{t}_{k}_{sid}")
                model.Add(fly_in >= x[sid, s_curr] + is_home[t, k + 1] - 1)
                ha_flight_10mi_terms.append(d_10 * fly_in)

    # 2. Tight Regional Road Pairing Bonus (<= 350 miles between consecutive away hosts)
    regional_road_pairs = []
    if cfg.w_regional_road_pair != 0:
        for t in range(n_teams):
            a_sids = away_series_by_team[t]
            for k in range(n_active - 1):
                s_curr, s_next = active_slots[k], active_slots[k + 1]
                if (s_next - s_curr) > 1:
                    continue

                slot_c_vars = []
                for sid1 in a_sids:
                    h1 = series_list[sid1]["home"]
                    for sid2 in a_sids:
                        h2 = series_list[sid2]["home"]
                        if h1 != h2 and dist_matrix[h1][h2] <= 350:
                            c_var = model.NewBoolVar(f"cl_{t}_{k}_{sid1}_{sid2}")
                            model.Add(c_var <= x[sid1, s_curr])
                            model.Add(c_var <= x[sid2, s_next])
                            regional_road_pairs.append(c_var)
                            slot_c_vars.append(c_var)
                if slot_c_vars:
                    model.Add(sum(slot_c_vars) <= 1 - is_home[t, k])
                    model.Add(sum(slot_c_vars) <= 1 - is_home[t, k + 1])

    # --------------------------------------------------------------------------
    # 2-DAY OFF-DAY GAPS (Inter-series gaps == 2 days)
    # --------------------------------------------------------------------------
    gaps_2d_vars = []
    for t in range(n_teams):
        for k in range(n_active - 1):
            s1, s2 = active_slots[k], active_slots[k + 1]
            if (s2 - s1) > 1:
                continue

            if slots[s1]["slot_type"] == "A" and slots[s2]["slot_type"] == "B":
                g2 = model.NewBoolVar(f"g2_{t}_{k}")
                model.Add(g2 >= 1 - is_4g[t, s1] - is_4g[t, s2])
                gaps_2d_vars.append(g2)
            elif slots[s1]["slot_type"] == "B" and slots[s2]["slot_type"] == "A":
                if not slots[s1].get("is_monday_holiday_wrap", False) and slots[s2].get("holiday") != "July 4th":
                    g2 = model.NewBoolVar(f"g2_{t}_{k}")
                    model.Add(g2 >= 1 - is_4g[t, s1] - is_4g[t, s2])
                    gaps_2d_vars.append(g2)

    # Phase 2 Objective
    model.Maximize(
        cfg.w_early_late_div * sum(div_early_late_terms)
        + cfg.w_isolated_home * sum(isolated_home_vars)
        + cfg.w_isolated_away * sum(isolated_away_vars)
        + cfg.w_long_home * sum(long_home_vars)
        + cfg.w_long_away * sum(long_away_vars)
        + cfg.w_div_31d_excess * sum(div_31d_pen_vars)
        + cfg.w_div_91d_gap * sum(div_91d_pen_vars)
        + cfg.w_road_trip_start * sum(road_trip_starts)
        + cfg.w_missed_april_div * sum(missed_april_vars)
        + cfg.w_missed_sept_div * sum(missed_sept_vars)
        + cfg.w_asg_thursday_game * sum(asg_thursday_4g_vars)
        + cfg.w_streak_over_threshold * sum(streak_over_9_vars)
        + cfg.w_consec_dow_off * sum(consec_dow_off_penalties)
        + cfg.w_tz_shift_ge2 * sum(tz_shifts_ge2_vars)
        + cfg.w_tz_abs_hour * sum(tz_abs_vars)
        + cfg.w_gap_2d * sum(gaps_2d_vars)
        + cfg.w_regional_road_pair * sum(regional_road_pairs)
        - 2 * sum(ha_flight_10mi_terms)
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
        streak_over_9_vars,
        consec_dow_off_penalties,
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
    streak_gt9_pen_count = sum(solver.Value(v) for v in streak_over_9_vars)
    dow_pen_count = sum(solver.Value(v) for v in consec_dow_off_penalties)

    metrics = {
        "status": status_name,
        "solve_time_sec": round(solve_time, 2),
        "objective_value": solver.ObjectiveValue(),
        "isolated_homestands": sum(solver.Value(v) for v in isolated_home_vars),
        "isolated_road_trips": sum(solver.Value(v) for v in isolated_away_vars),
        "long_homestands": sum(solver.Value(v) for v in long_home_vars),
        "long_road_trips": sum(solver.Value(v) for v in long_away_vars),
        "div_31d_penalties": sum(solver.Value(v) for v in div_31d_pen_vars),
        "div_91d_penalties": sum(solver.Value(v) for v in div_91d_pen_vars),
        "early_late_div_series": sum(solver.Value(v) for v in div_early_late_terms),
        "missed_april_pairs": len(missed_apr_pairs),
        "missed_sept_pairs": len(missed_sep_pairs),
        "missed_april_list": missed_apr_pairs,
        "missed_sept_list": missed_sep_pairs,
        "asg_thursday_games": asg_thu_count,
        "streak_gt9_penalty_days": streak_gt9_pen_count,
        "consec_dow_off_penalties": dow_pen_count,
        "tz_shifts_ge2": sum(solver.Value(v) for v in tz_shifts_ge2_vars),
        "tz_abs_hours": sum(solver.Value(v) for v in tz_abs_vars),
        "gaps_2d": sum(solver.Value(v) for v in gaps_2d_vars),
        "clust_rt_pairs": sum(solver.Value(v) for v in regional_road_pairs)
    }
    return assignment, metrics


# ==============================================================================
# 5. CALENDAR EXPANSION, PER-TEAM CSV EXPORT, 1-PAGE PDF GENERATOR & VALIDATION
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
    1. Automatically shifts a 3-game midweek Slot A series to [Mon, Tue, Wed] whenever
       either participating team plays a 4-game weekend Slot B series starting on Thursday.
    2. Actively chooses [Mon, Tue, Wed] vs [Tue, Wed, Thu] for optional 3-game midweek
       series to balance Monday vs Thursday off-days (preventing >3 consecutive weeks
       with Monday off) while respecting playing streak limits.
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

    # Track consecutive Monday off-days and current playing streak per team
    consec_mon_off = {t: 0 for t in range(n_teams)}
    consec_thu_off = {t: 0 for t in range(n_teams)}
    team_play_dates: Dict[int, set] = {t: set() for t in range(n_teams)}

    records = []

    for k_idx, s in enumerate(active_slots):
        slot_meta = slots[s]
        slot_label = slot_meta["label"]
        next_s = s + 1
        next_shares_thu = (
            next_s < len(slots)
            and not slots[next_s]["is_asg"]
            and slots[next_s].get("shares_thu_with_prev", False)
        )
        prev_s = active_slots[k_idx - 1] if k_idx > 0 else None
        prev_was_mon_wrap = (
            prev_s is not None and slots[prev_s].get("is_monday_holiday_wrap", False)
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
                must_shift_early = next_shares_thu and (
                    h_idx in teams_playing_4g_in_slot.get(next_s, set())
                    or a_idx in teams_playing_4g_in_slot.get(next_s, set())
                )
                can_shift_early = (
                    slot_meta["slot_type"] == "A"
                    and not slot_meta.get("force_3g", False)
                    and not prev_was_mon_wrap
                    and slot_meta.get("dates_3g_early", slot_meta["dates_3g"]) != slot_meta["dates_3g"]
                )

                if must_shift_early:
                    dates = slot_meta.get("dates_3g_early", slot_meta["dates_3g"])
                elif can_shift_early:
                    # Check if shifting to [Mon, Tue, Wed] helps break a Monday off-day run (>= 2 weeks)
                    # without pushing either team's consecutive playing streak past 9 days
                    early_dates = slot_meta["dates_3g_early"]
                    mon_d = early_dates[0]

                    # Count how many consecutive days each team has played leading into Monday
                    def prior_streak(t_id: int, ref_date: datetime.date) -> int:
                        cnt = 0
                        cur = ref_date - datetime.timedelta(days=1)
                        while cur in team_play_dates[t_id]:
                            cnt += 1
                            cur -= datetime.timedelta(days=1)
                        return cnt

                    h_prior = prior_streak(h_idx, mon_d)
                    a_prior = prior_streak(a_idx, mon_d)

                    # Shifting to [Mon, Tue, Wed] adds 3 days to the prior weekend streak, then gives Thu off!
                    streak_safe = (h_prior + 3 <= 9) and (a_prior + 3 <= 9)
                    thu_safe = (consec_thu_off[h_idx] < 2) and (consec_thu_off[a_idx] < 2)
                    needs_mon_play = (consec_mon_off[h_idx] >= 2) or (consec_mon_off[a_idx] >= 2)

                    if streak_safe and thu_safe and needs_mon_play:
                        dates = early_dates
                    else:
                        dates = slot_meta["dates_3g"]
                else:
                    dates = slot_meta["dates_3g"]

            # Update play dates and Monday/Thursday off-day streak counters for midweek Slot A
            for d in dates:
                team_play_dates[h_idx].add(d)
                team_play_dates[a_idx].add(d)

            if slot_meta["slot_type"] == "A" and not slot_meta["is_asg"] and slot_meta["dates_4g"]:
                mon_date = slot_meta["dates_4g"][0]
                if mon_date.weekday() == 0:
                    for tid in (h_idx, a_idx):
                        if mon_date in team_play_dates[tid]:
                            consec_mon_off[tid] = 0
                        else:
                            consec_mon_off[tid] += 1

            if slot_meta["slot_type"] == "B" and slot_meta["dates_4g"]:
                # Check Thursday of this week
                thu_cand = slot_meta["dates_4g"][0]
                if thu_cand.weekday() == 3:
                    for tid in (h_idx, a_idx):
                        if thu_cand in team_play_dates[tid]:
                            consec_thu_off[tid] = 0
                        else:
                            consec_thu_off[tid] += 1

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
    renders the Opponent abbreviation text instead.
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
    subtitle: str = "",
) -> None:
    """
    Generates 30 individual ONE-PAGE Portrait PDF calendars (`data/mlb_schedule_<ABBR>_<YEAR>.pdf`):
      - 1 single page per team (Letter Portrait: 612 x 792 pt).
      - 2 columns x 3 rows grid of month blocks (left-to-right, then top-to-bottom):
          Row 0: March / April (combined) | May
          Row 1: June                     | July
          Row 2: August                   | September (or September / October if games in Oct)
      - White background for regular games; Yellow background (#FEF08A) for Doubleheaders.
      - Inset thick navy blue border (#0A1E3F, 3.0 pt) for Home games; thin border for Road games.
      - Tuesday All-Star Game (ASG) highlighted with a true gold badge; Mon/Wed/Thu ASG Break shaded.
      - Clean date number in top-left; Opponent logo/text badge in center.
    """
    output_dir = f"{output_dir}/{subtitle} {season_year}"
    os.makedirs(output_dir, exist_ok=True)
    logo_map = fetch_or_cache_team_logos(teams, output_dir=output_dir, enable_logos=enable_logos)

    navy = colors.HexColor("#0A1E3F")
    header_blue = colors.HexColor("#1F3A60")
    light_gray = colors.HexColor("#F2F4F7")
    border_gray = colors.HexColor("#CBD2D9")
    muted_text = colors.HexColor("#7B8794")
    gold_bg = colors.HexColor("#F5C518")             # True bright gold for ASG
    gold_border = colors.HexColor("#D4AF37")         # Metallic gold border for ASG
    asg_break_bg = colors.HexColor("#FEF9C3")        # Soft cream for ASG Break
    asg_break_text = colors.HexColor("#854D0E")
    doubleheader_bg = colors.HexColor("#FEF08A")     # Warm yellow for scheduled doubleheaders
    dow_letters = ["S", "M", "T", "W", "T", "F", "S"]

    page_w, page_h = letter  # 612 x 792 pt portrait

    asg_date = datetime.date(season_year, 7, 13)
    asg_mon = asg_date - datetime.timedelta(days=asg_date.weekday())
    asg_wed = asg_mon + datetime.timedelta(days=2)
    asg_thu = asg_mon + datetime.timedelta(days=3)
    asg_break_days = {asg_mon, asg_wed}

    home_border_w = 3.0
    half_hb = home_border_w / 2.0

    for t in teams:
        abbr = t["abbr"]
        team_name = t["name"]
        pdf_path = os.path.join(output_dir, f"mlb_schedule_{abbr}_{season_year}_{subtitle}.pdf")

        t_df = df[(df["HomeTeam"] == abbr) | (df["AwayTeam"] == abbr)].copy()
        t_df["DateObj"] = pd.to_datetime(t_df["Date"]).dt.date
        t_df = t_df.sort_values("DateObj").reset_index(drop=True)

        # Support multiple games on the same calendar date (e.g., official doubleheaders)
        game_by_date: Dict[datetime.date, List[Dict[str, Any]]] = {}
        for _, row in t_df.iterrows():
            d = row["DateObj"]
            is_home = (row["HomeTeam"] == abbr)
            opp = row["AwayTeam"] if is_home else row["HomeTeam"]
            game_by_date.setdefault(d, []).append({
                "is_home": is_home,
                "opp": opp,
            })

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

        c = canvas.Canvas(pdf_path, pagesize=letter)

        # Top Banner
        c.setFillColor(navy)
        c.rect(20, page_h - 44, page_w - 40, 32, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(30, page_h - 33, f"{team_name.upper()} ({abbr}) — {season_year} SCHEDULE - {subtitle}")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(page_w - 30, page_h - 33, "REGULAR SEASON CALENDAR")

        # Compact Legend Bar: Thick navy border for Home, Thin border for Road, Yellow for DH, Gold for ASG
        legend_y = page_h - 58
        c.setFillColor(colors.white)
        c.setStrokeColor(navy)
        c.setLineWidth(2.2)
        c.rect(20, legend_y, 11, 11, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(34, legend_y + 2, "HOME (Navy Border)")

        c.setFillColor(colors.white)
        c.setStrokeColor(border_gray)
        c.setLineWidth(0.5)
        c.rect(130, legend_y, 11, 11, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(144, legend_y + 2, "ROAD (Thin)")

        c.setFillColor(doubleheader_bg)
        c.setStrokeColor(border_gray)
        c.setLineWidth(0.5)
        c.rect(202, legend_y, 11, 11, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(216, legend_y + 2, "DOUBLEHEADER (Yellow)")

        c.setFillColor(gold_bg)
        c.setStrokeColor(gold_border)
        c.setLineWidth(0.8)
        c.rect(328, legend_y, 11, 11, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.drawString(342, legend_y + 2, "ALL-STAR GAME (Gold)")

        # 2 Columns x 3 Rows Geometry (Left-to-right, then top-to-bottom)
        margin_x = 20.0
        gap_x = 12.0
        col_w = (page_w - 2 * margin_x - gap_x) / 2.0  # ~280 pt

        top_y = page_h - 68.0
        bottom_y = 16.0
        gap_y = 10.0
        block_h = (top_y - bottom_y - 2 * gap_y) / 3.0  # ~229 pt

        for idx, (title, p_start, p_end, active_months) in enumerate(periods):
            col = idx % 2
            row = idx // 2
            bx = margin_x + col * (col_w + gap_x)
            by = top_y - (row + 1) * block_h - row * gap_y

            # Month Block Header
            title_h = 16.0
            c.setFillColor(header_blue)
            c.rect(bx, by + block_h - title_h, col_w, title_h, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawCentredString(bx + col_w / 2.0, by + block_h - title_h + 4.5, title)

            # Day-of-week header row (S M T W T F S)
            dow_h = 13.0
            c.setFillColor(light_gray)
            c.rect(bx, by + block_h - title_h - dow_h, col_w, dow_h, fill=1, stroke=0)
            c.setFillColor(navy)
            c.setFont("Helvetica-Bold", 7.5)
            cell_w = col_w / 7.0

            for d_idx, d_char in enumerate(dow_letters):
                cx = bx + d_idx * cell_w
                c.drawCentredString(cx + cell_w / 2.0, by + block_h - title_h - dow_h + 3.5, d_char)

            # Weeks & Days Grid
            start_sun = p_start - datetime.timedelta(days=(p_start.weekday() + 1) % 7)
            end_sat = p_end + datetime.timedelta(days=(5 - p_end.weekday()) % 7)
            total_days = (end_sat - start_sun).days + 1
            num_weeks = total_days // 7
            cell_h = (block_h - title_h - dow_h) / float(num_weeks)

            curr_d = start_sun
            for w in range(num_weeks):
                wy = by + block_h - title_h - dow_h - (w + 1) * cell_h
                for d_idx in range(7):
                    cx = bx + d_idx * cell_w
                    in_period = (curr_d.month in active_months) and (p_start <= curr_d <= p_end)
                    games_today = game_by_date.get(curr_d, []) if in_period else []

                    if not in_period:
                        c.setFillColor(light_gray)
                        c.setStrokeColor(border_gray)
                        c.setLineWidth(0.5)
                        c.rect(cx, wy, cell_w, cell_h, fill=1, stroke=1)
                    elif games_today:
                        is_dh = len(games_today) >= 2
                        has_home = any(g["is_home"] for g in games_today)

                        # Yellow background for doubleheaders; clean white for single games
                        c.setFillColor(doubleheader_bg if is_dh else colors.white)
                        c.setStrokeColor(border_gray)
                        c.setLineWidth(0.5)
                        c.rect(cx, wy, cell_w, cell_h, fill=1, stroke=1)

                        # Inset thick navy border if at least one game is at home
                        if has_home:
                            c.setStrokeColor(navy)
                            c.setLineWidth(home_border_w)
                            c.rect(
                                cx + half_hb,
                                wy + half_hb,
                                cell_w - home_border_w,
                                cell_h - home_border_w,
                                fill=0,
                                stroke=1,
                            )

                        # Date number in top-left
                        c.setFillColor(navy if has_home else colors.HexColor("#243B53"))
                        c.setFont("Helvetica-Bold", 6.5)
                        date_lbl = (
                            f"{curr_d.strftime('%b')[:1]}{curr_d.day}"
                            if len(active_months) > 1 and curr_d.day == 1
                            else str(curr_d.day)
                        )
                        text_pad_x = 3.5 if has_home else 2.5
                        text_pad_y = 8.5 if has_home else 7.5
                        c.drawString(cx + text_pad_x, wy + cell_h - text_pad_y, date_lbl)

                        if is_dh:
                            # DH indicator tag in top-right corner
                            c.setFillColor(colors.HexColor("#854D0E"))
                            c.setFont("Helvetica-Bold", 5.5)
                            c.drawRightString(cx + cell_w - (3.5 if has_home else 2.5), wy + cell_h - text_pad_y, "DH")

                            # Render stacked double-header opponents
                            opp1 = games_today[0]["opp"]
                            opp2 = games_today[1]["opp"]
                            c.setFillColor(navy)
                            c.setFont("Helvetica-Bold", 6.5)
                            c.drawCentredString(cx + cell_w / 2.0, wy + cell_h / 2.0 + 1.0, f"G1: {opp1}")
                            c.drawCentredString(cx + cell_w / 2.0, wy + cell_h / 2.0 - 6.5, f"G2: {opp2}")
                        else:
                            # Standard single game: Logo or bold text in center
                            opp_abbr = games_today[0]["opp"]
                            logo_file = logo_map.get(opp_abbr)

                            if logo_file and os.path.exists(logo_file):
                                img_size = min(cell_w * 0.56, cell_h * 0.62)
                                img_x = cx + (cell_w - img_size) / 2.0
                                img_y = wy + (cell_h - img_size) / 2.0 - 1.5
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
                                    c.setFillColor(navy)
                                    c.setFont("Helvetica-Bold", 8.5)
                                    c.drawCentredString(cx + cell_w / 2.0, wy + cell_h / 2.0 - 4.0, opp_abbr)
                            else:
                                c.setFillColor(navy)
                                c.setFont("Helvetica-Bold", 8.5)
                                c.drawCentredString(cx + cell_w / 2.0, wy + cell_h / 2.0 - 4.0, opp_abbr)
                    elif curr_d == asg_date:
                        # All-Star Game Tuesday: highlighted in true gold with navy ASG text
                        c.setFillColor(gold_bg)
                        c.setStrokeColor(gold_border)
                        c.setLineWidth(0.8)
                        c.rect(cx, wy, cell_w, cell_h, fill=1, stroke=1)

                        c.setFillColor(navy)
                        c.setFont("Helvetica-Bold", 6.5)
                        c.drawString(cx + 2.5, wy + cell_h - 7.5, str(curr_d.day))

                        c.setFont("Helvetica-Bold", 8.0)
                        c.drawCentredString(cx + cell_w / 2.0, wy + cell_h / 2.0 - 3.5, "ASG")
                    elif curr_d in asg_break_days or (curr_d == asg_thu and not games_today):
                        # Core All-Star Break days: soft warm cream with Break label
                        c.setFillColor(asg_break_bg)
                        c.setStrokeColor(border_gray)
                        c.setLineWidth(0.5)
                        c.rect(cx, wy, cell_w, cell_h, fill=1, stroke=1)

                        c.setFillColor(asg_break_text)
                        c.setFont("Helvetica-Bold", 6.5)
                        c.drawString(cx + 2.5, wy + cell_h - 7.5, str(curr_d.day))

                        c.setFont("Helvetica-Bold", 6.0)
                        c.drawCentredString(cx + cell_w / 2.0, wy + cell_h / 2.0 - 2.5, "BREAK")
                    else:
                        # Standard Scheduled Off-Day
                        c.setFillColor(colors.white)
                        c.setStrokeColor(border_gray)
                        c.setLineWidth(0.5)
                        c.rect(cx, wy, cell_w, cell_h, fill=1, stroke=1)
                        c.setFillColor(muted_text)
                        c.setFont("Helvetica", 6.5)
                        date_lbl = (
                            f"{curr_d.strftime('%b')[:1]}{curr_d.day}"
                            if len(active_months) > 1 and curr_d.day == 1
                            else str(curr_d.day)
                        )
                        c.drawString(cx + 2.5, wy + cell_h - 7.5, date_lbl)

                    curr_d += datetime.timedelta(days=1)

        c.showPage()
        c.save()

    print(f"Generated 30 1-page team schedule PDFs in '{output_dir}/mlb_schedule_<TEAM>_<SEASON>.pdf'.")


def compute_team_playing_streaks(
    df: pd.DataFrame,
    teams: List[Dict[str, Any]],
) -> Tuple[int, List[Tuple[str, str, str, int]], List[Tuple[str, str, str, int]], int]:
    """
    Computes consecutive playing day streaks for all 30 teams from a daily schedule DataFrame.
    Returns:
      - max_streak: longest streak of consecutive days played by any team
      - streaks_ge_17: list of (team, start_date, end_date, length) for streaks >= 17 days
      - streaks_10_to_16: list of (team, start_date, end_date, length) for streaks of 10..16 days
      - excess_days_over_9: sum of (length - 9) across all streaks > 9 days
    """
    df_temp = df.copy()
    df_temp["DateObj"] = pd.to_datetime(df_temp["Date"]).dt.date

    max_streak = 0
    streaks_ge_17: List[Tuple[str, str, str, int]] = []
    streaks_10_to_16: List[Tuple[str, str, str, int]] = []
    excess_days_over_9 = 0

    for t in teams:
        abbr = t["abbr"]
        t_dates = sorted(
            set(df_temp[(df_temp["HomeTeam"] == abbr) | (df_temp["AwayTeam"] == abbr)]["DateObj"].tolist())
        )
        if not t_dates:
            continue

        s_start = t_dates[0]
        s_prev = t_dates[0]
        s_len = 1

        for d in t_dates[1:]:
            if (d - s_prev).days == 1:
                s_len += 1
                s_prev = d
            else:
                if s_len > max_streak:
                    max_streak = s_len
                if s_len > 9:
                    excess_days_over_9 += (s_len - 9)
                    if s_len >= 17:
                        streaks_ge_17.append((abbr, s_start.isoformat(), s_prev.isoformat(), s_len))
                    else:
                        streaks_10_to_16.append((abbr, s_start.isoformat(), s_prev.isoformat(), s_len))
                s_start = d
                s_prev = d
                s_len = 1

        if s_len > max_streak:
            max_streak = s_len
        if s_len > 9:
            excess_days_over_9 += (s_len - 9)
            if s_len >= 17:
                streaks_ge_17.append((abbr, s_start.isoformat(), s_prev.isoformat(), s_len))
            else:
                streaks_10_to_16.append((abbr, s_start.isoformat(), s_prev.isoformat(), s_len))

    return max_streak, streaks_ge_17, streaks_10_to_16, excess_days_over_9


def compute_timezone_shifts_ge_2h(df: pd.DataFrame, teams: List[Dict[str, Any]]) -> int:
    """Counts the total occurrences of teams traveling across >= 2 timezone boundaries between consecutive series."""
    df_temp = df.copy()
    df_temp["DateObj"] = pd.to_datetime(df_temp["Date"]).dt.date
    tz_map = {t["abbr"]: TEAM_TIMEZONES.get(t["abbr"], 0) for t in teams}
    total_shifts_ge_2h = 0

    for t in teams:
        ab = t["abbr"]
        t_games = df_temp[(df_temp["HomeTeam"] == ab) | (df_temp["AwayTeam"] == ab)].sort_values("DateObj")
        # Identify consecutive series venues
        series_venues = []
        last_slot = None
        for _, row in t_games.iterrows():
            slot = row.get("SeriesSlot")
            if slot != last_slot:
                series_venues.append(row["HomeTeam"])
                last_slot = slot

        for k in range(1, len(series_venues)):
            v_prev = series_venues[k - 1]
            v_curr = series_venues[k]
            if abs(tz_map[v_prev] - tz_map[v_curr]) >= 2:
                total_shifts_ge_2h += 1

    return total_shifts_ge_2h


def compute_consecutive_dow_offdays(df: pd.DataFrame, teams: List[Dict[str, Any]], dow_target: str) -> List[Tuple[str, int]]:
    """Checks for teams with > 3 consecutive weeks where `dow_target` (e.g. 'Monday', 'Thursday') is an off-day."""
    df_temp = df.copy()
    df_temp["DateObj"] = pd.to_datetime(df_temp["Date"]).dt.date
    violations = []

    for t in teams:
        ab = t["abbr"]
        t_games = df_temp[(df_temp["HomeTeam"] == ab) | (df_temp["AwayTeam"] == ab)]
        play_dates = set(t_games["DateObj"].tolist())

        # Group by full calendar weeks (Monday through Sunday)
        min_date = min(df_temp["DateObj"])
        start_mon = min_date - datetime.timedelta(days=min_date.weekday())
        max_date = max(df_temp["DateObj"])
        curr_mon = start_mon

        consec_off = 0
        max_consec = 0

        while curr_mon <= max_date:
            target_date = curr_mon if dow_target == "Monday" else curr_mon + datetime.timedelta(days=3)
            if target_date not in play_dates:
                consec_off += 1
                if consec_off > max_consec:
                    max_consec = consec_off
            else:
                consec_off = 0
            curr_mon += datetime.timedelta(days=7)

        if max_consec > 3:
            violations.append((ab, max_consec))

    return violations


def run_validation_checks(
    df: pd.DataFrame,
    teams: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    assignment: Dict[int, int],
    slots: List[Dict[str, Any]],
    holidays: Dict[str, datetime.date],
    cfg: ScheduleConfig = ScheduleConfig(),
) -> None:
    """Runs automated validation assertions verifying all hard constraints."""
    print("\n" + "=" * 72)
    print("AUTOMATED SCHEDULE VALIDATION CHECKS")
    print("=" * 72)

    assert len(df) == 2430, f"Expected 2,430 total games, got {len(df)}"
    print("[PASS] Total regular season games == 2,430 (780 total series)")

    # 1. Verify No Doubleheaders
    team_dates = pd.concat([
        df[["Date", "HomeTeam"]].rename(columns={"HomeTeam": "Team"}),
        df[["Date", "AwayTeam"]].rename(columns={"AwayTeam": "Team"}),
    ])
    dups = team_dates[team_dates.duplicated(subset=["Date", "Team"], keep=False)]
    assert len(dups) == 0, f"Found {len(dups) // 2} doubleheaders! Sample:\n{dups.head(6)}"
    print("[PASS] Zero doubleheaders scheduled (no team plays twice on the same date)")

    # 2. Verify Contiguous Series Dates
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

    # 3. Verify Inter-Series Off-Day Gaps
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
                continue
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

    # 3b. Verify Consecutive Playing Days
    max_streak, streaks_ge_17, streaks_10_to_16, excess_days_over_9 = compute_team_playing_streaks(df, teams)
    hard_play_limit = cfg.max_consec_play_days_hard if cfg.max_consec_play_days_hard > 0 else 20
    if max_streak > hard_play_limit:
        print(f"Found team with {max_streak} consecutive playing days (hard cap: {hard_play_limit})")
    else:
        print(
            f"[PASS] All teams play <= {hard_play_limit} consecutive days before an off-day "
            f"(Max streak: {max_streak}d | Streaks 10-16d: {len(streaks_10_to_16)} | Excess days >9: {excess_days_over_9})"
        )

    # 3c. Check Monday & Thursday Off-Day Spacing (Soft Metric: > 3 consecutive weeks)
    mon_viols = compute_consecutive_dow_offdays(df, teams, "Monday")
    thu_viols = compute_consecutive_dow_offdays(df, teams, "Thursday")
    print(
        f"[INFO] Monday off-days >3 wks in a row: {len(mon_viols)} teams {mon_viols} | "
        f"Thursday off-days >3 wks in a row: {len(thu_viols)} teams {thu_viols}"
    )

    # 3d. Check Timezone Shifts (>= 2 hours)
    tz_shifts = compute_timezone_shifts_ge_2h(df, teams)
    print(f"[INFO] League-wide timezone shifts (>= 2 hours): {tz_shifts}")

    # 4. Check Divisional Spacing Rules (Soft Metrics: >2 series in 31d, >3 months apart)
    abbr_to_div = {t["abbr"]: t["division"] for t in teams}
    div_pair_series_dates: Dict[Tuple[str, str], List[Tuple[datetime.date, datetime.date]]] = {}
    for (slot_lbl, h, a), grp in df_temp.groupby(["SeriesSlot", "HomeTeam", "AwayTeam"]):
        if abbr_to_div[h] == abbr_to_div[a]:
            pk = (min(h, a), max(h, a))
            d_list = sorted(grp["DateObj"].tolist())
            div_pair_series_dates.setdefault(pk, []).append((d_list[0], d_list[-1]))

    div_31d_viols = []
    div_95d_viols = []
    for pk, s_ranges in div_pair_series_dates.items():
        s_ranges.sort(key=lambda r: r[0])
        for i in range(len(s_ranges)):
            in_31 = [r for r in s_ranges if 0 <= (r[0] - s_ranges[i][0]).days <= 30]
            if len(in_31) > 2:
                div_31d_viols.append(f"{pk[0]}-{pk[1]}")
                break
        for i in range(len(s_ranges) - 1):
            gap_days = (s_ranges[i + 1][0] - s_ranges[i][1]).days
            if gap_days > 95:
                div_95d_viols.append(f"{pk[0]}-{pk[1]} ({gap_days}d)")
                break
    print(
        f"[INFO] Divisional spacing soft metrics: >2 series in 31d={len(div_31d_viols)} {div_31d_viols} | "
        f">3 months apart={len(div_95d_viols)} {div_95d_viols}"
    )

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

    # 7. All-Star Break Check
    asg_wed = asg_mon + datetime.timedelta(days=2)
    asg_thu = asg_mon + datetime.timedelta(days=3)
    core_asg_games = df[(df["Date"] >= asg_mon.isoformat()) & (df["Date"] <= asg_wed.isoformat())]
    assert len(core_asg_games) == 0, f"Found {len(core_asg_games)} games during core Mon-Wed All-Star Break!"
    thu_asg_games = df[df["Date"] == asg_thu.isoformat()]
    print(
        f"[PASS] Core All-Star Break ({asg_mon.isoformat()} to {asg_wed.isoformat()}) has 0 games "
        f"(Thursday {asg_thu.isoformat()} early restart games: {len(thu_asg_games)})"
    )

    # 8. Verify Matchup Quotas
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

    # 9. Check Road Trip & Homestand Lengths
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]
    team_slot_ha = {t["abbr"]: {} for t in teams}
    for sid, s in assignment.items():
        sr = series_list[sid]
        h_abbr = teams[sr["home"]]["abbr"]
        a_abbr = teams[sr["away"]]["abbr"]
        team_slot_ha[h_abbr][s] = "H"
        team_slot_ha[a_abbr][s] = "A"

    one_series_rt_count = 0
    long_rt_count = 0
    long_hs_count = 0
    hard_series_limit = cfg.max_homestand_roadtrip_hard if cfg.max_homestand_roadtrip_hard > 0 else 4

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
                assert 1 <= r_len <= hard_series_limit, (
                    f"Team {abbr} has road trip of {r_len} series (hard max {hard_series_limit})"
                )
                if r_len == 1:
                    one_series_rt_count += 1
                elif r_len > 3:
                    long_rt_count += (r_len - 3)
            else:
                assert 1 <= r_len <= hard_series_limit, (
                    f"Team {abbr} has homestand of {r_len} series (hard max {hard_series_limit})"
                )
                if r_len > 3:
                    long_hs_count += (r_len - 3)
    print(
        f"[PASS] All road trips and homestands are <= {hard_series_limit} series "
        f"(Soft >3 series: {long_rt_count}A / {long_hs_count}H | 1-series RT: {one_series_rt_count})"
    )

    # 9b. Verify Isolated Series Cap per Team
    if cfg.max_isolated_series_per_team > 0:
        for t in teams:
            abbr = t["abbr"]
            seq = [team_slot_ha[abbr][s] for s in active_slots]
            h_runs = [len(list(g)) for k, g in itertools.groupby(seq) if k == "H"]
            a_runs = [len(list(g)) for k, g in itertools.groupby(seq) if k == "A"]
            iso_h_cnt = sum(1 for r in h_runs if r == 1)
            iso_a_cnt = sum(1 for r in a_runs if r == 1)
            assert iso_h_cnt <= cfg.max_isolated_series_per_team, (
                f"Team {abbr} has {iso_h_cnt} isolated homestands (max: {cfg.max_isolated_series_per_team})"
            )
            assert iso_a_cnt <= cfg.max_isolated_series_per_team, (
                f"Team {abbr} has {iso_a_cnt} isolated road trips (max: {cfg.max_isolated_series_per_team})"
            )
        print(f"[PASS] All teams have <= {cfg.max_isolated_series_per_team} isolated homestands & road trips")

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
    cfg: ScheduleConfig = ScheduleConfig()
) -> None:
    """
    Audits any schedule DataFrame (from MLB API or CSV) without optimizing it,
    reporting every broken constraint, printing an itemized leaderboard of CP-SAT
    objective scores per team in a pandas DataFrame, and calculating the league score.
    """
    print("\n" + "=" * 76)
    print(f"HISTORICAL / EXISTING SCHEDULE AUDIT REPORT (SEASON {season_year})")
    print("=" * 76)

    df = df_input.copy()
    df["DateObj"] = pd.to_datetime(df["Date"]).dt.date
    holidays = get_calendar_holidays(season_year)
    abbr_to_idx = {t["abbr"]: i for i, t in enumerate(teams)}
    abbr_to_div = {t["abbr"]: t["division"] for t in teams}
    tz_map = {t["abbr"]: TEAM_TIMEZONES.get(t["abbr"], 0) for t in teams}

    total_games = len(df)
    home_counts = df["HomeTeam"].value_counts().to_dict()
    away_counts = df["AwayTeam"].value_counts().to_dict()
    imbalanced_teams = []
    for t in teams:
        ab = t["abbr"]
        h_c, a_c = home_counts.get(ab, 0), away_counts.get(ab, 0)
        if h_c != 81 or a_c != 81:
            imbalanced_teams.append(f"{ab} ({h_c}H/{a_c}A)")

    team_dates = pd.concat([
        df[["Date", "HomeTeam"]].rename(columns={"HomeTeam": "Team"}),
        df[["Date", "AwayTeam"]].rename(columns={"AwayTeam": "Team"}),
    ])
    dup_rows = team_dates[team_dates.duplicated(subset=["Date", "Team"], keep=False)]
    num_doubleheaders = len(dup_rows) // 2

    max_streak, streaks_ge_17, streaks_10_to_16, excess_days_over_9 = compute_team_playing_streaks(df, teams)

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

    team_series_seq: Dict[str, List[Dict[str, Any]]] = {t["abbr"]: [] for t in teams}
    for sr in reconstructed_series:
        team_series_seq[sr["home"]].append({"type": "H", "venue": sr["home"], "opp": sr["away"], "start": sr["dates"][0], "end": sr["dates"][-1], "games": len(sr["dates"])})
        team_series_seq[sr["away"]].append({"type": "A", "venue": sr["home"], "opp": sr["home"], "start": sr["dates"][0], "end": sr["dates"][-1], "games": len(sr["dates"])})

    asg_mon = holidays["asg_monday"]
    asg_fri = asg_mon + datetime.timedelta(days=4)

    team_metrics: Dict[str, Dict[str, int]] = {
        t["abbr"]: {
            "early_late_div": 0,
            "iso_h": 0,
            "iso_a": 0,
            "long_h": 0,
            "long_a": 0,
            "rt_starts": 0,
            "asg_thu": 0,
            "streak_gt9": 0,
            "tz_shifts_ge2": 0,
            "tz_abs": 0,
            "mon_off_pen": 0,
            "thu_off_pen": 0,
            "gaps_2d": 0,
            "clust_rt": 0,
            "miles": 0,
        }
        for t in teams
    }

    short_road_trips = 0
    long_road_trips = 0
    long_homestands = 0
    isolated_homestands = 0
    road_trip_starts = 0
    gaps_eq_2_days = 0
    gaps_gt_2_days = 0

    for t in teams:
        ab = t["abbr"]
        seq = sorted(team_series_seq[ab], key=lambda x: x["start"])
        curr_v = abbr_to_idx[ab]
        miles = 0
        for item in seq:
            next_v = abbr_to_idx[item["venue"]]
            miles += dist_matrix[curr_v][next_v]
            curr_v = next_v
        team_metrics[ab]["miles"] = miles

        for k in range(1, len(seq)):
            v_prev = seq[k - 1]["venue"]
            v_curr = seq[k]["venue"]
            diff_h = abs(tz_map[v_prev] - tz_map[v_curr])
            team_metrics[ab]["tz_abs"] += diff_h
            if diff_h >= 2:
                team_metrics[ab]["tz_shifts_ge2"] += 1

        # Check consecutive away venues on road trips for regional clustering (<= 450 mi)
        for k in range(1, len(seq)):
            if seq[k - 1]["type"] == "A" and seq[k]["type"] == "A":
                v_prev = abbr_to_idx[seq[k - 1]["venue"]]
                v_curr = abbr_to_idx[seq[k]["venue"]]
                if v_prev != v_curr and dist_matrix[v_prev][v_curr] <= 450:
                    team_metrics[ab]["clust_rt"] += 1

        for k in range(1, len(seq)):
            if seq[k - 1]["type"] == "H" and seq[k]["type"] == "A":
                road_trip_starts += 1
                team_metrics[ab]["rt_starts"] += 1
            prev_end = seq[k - 1]["end"]
            curr_start = seq[k]["start"]
            if not (prev_end < asg_mon and curr_start >= asg_mon and curr_start <= asg_fri):
                idle = (curr_start - prev_end).days - 1
                if idle == 2:
                    gaps_eq_2_days += 1
                    team_metrics[ab]["gaps_2d"] += 1
                elif idle > 2:
                    gaps_gt_2_days += 1

        for k in range(1, len(seq) - 1):
            if seq[k - 1]["type"] == "A" and seq[k]["type"] == "H" and seq[k + 1]["type"] == "A":
                isolated_homestands += 1
                team_metrics[ab]["iso_h"] += 1

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
                        team_metrics[ab]["iso_a"] += 1
                    elif r_len > 3:
                        long_road_trips += (r_len - 3)
                        team_metrics[ab]["long_a"] += (r_len - 3)
                else:
                    if r_len > 3:
                        long_homestands += (r_len - 3)
                        team_metrics[ab]["long_h"] += (r_len - 3)

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
                team_metrics[h]["early_late_div"] += 1
                team_metrics[a]["early_late_div"] += 1

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

    asg_wed = asg_mon + datetime.timedelta(days=2)
    asg_thu = asg_mon + datetime.timedelta(days=3)
    asg_core_games = len(df[(df["DateObj"] >= asg_mon) & (df["DateObj"] <= asg_wed)])
    asg_thu_df = df[df["DateObj"] == asg_thu]
    asg_thu_games = len(asg_thu_df)
    for _, row in asg_thu_df.iterrows():
        team_metrics[row["HomeTeam"]]["asg_thu"] += 1
        team_metrics[row["AwayTeam"]]["asg_thu"] += 1

    # Team playing streaks > 9 days
    for t in teams:
        ab = t["abbr"]
        t_dates = sorted(set(df[(df["HomeTeam"] == ab) | (df["AwayTeam"] == ab)]["DateObj"].tolist()))
        if not t_dates:
            continue
        s_len = 1
        s_prev = t_dates[0]
        for d in t_dates[1:]:
            if (d - s_prev).days == 1:
                s_len += 1
            else:
                if s_len > 9:
                    team_metrics[ab]["streak_gt9"] += (s_len - 9)
                s_len = 1
            s_prev = d
        if s_len > 9:
            team_metrics[ab]["streak_gt9"] += (s_len - 9)

    mon_viols = compute_consecutive_dow_offdays(df, teams, "Monday")
    thu_viols = compute_consecutive_dow_offdays(df, teams, "Thursday")
    for ab, c_len in mon_viols:
        team_metrics[ab]["mon_off_pen"] += max(0, c_len - 3)
    for ab, c_len in thu_viols:
        team_metrics[ab]["thu_off_pen"] += max(0, c_len - 3)

    tz_shifts_ge_2h = sum(tm["tz_shifts_ge2"] for tm in team_metrics.values())
    total_excess_dow = sum(tm["mon_off_pen"] + tm["thu_off_pen"] for tm in team_metrics.values())

    # Build per-team leaderboard DataFrame
    # Build per-team leaderboard DataFrame using centralized ScheduleConfig weights
    team_rows = []
    for t in teams:
        ab = t["abbr"]
        m = team_metrics[ab]
        score = (
            cfg.w_early_late_div * m["early_late_div"]
            + cfg.w_isolated_home * m["iso_h"]
            + cfg.w_isolated_away * m["iso_a"]
            + cfg.w_long_home * m["long_h"]
            + cfg.w_long_away * m["long_a"]
            + cfg.w_road_trip_start * m["rt_starts"]
            + cfg.w_asg_thursday_game * m["asg_thu"]
            + cfg.w_streak_over_threshold * m["streak_gt9"]
            + cfg.w_consec_dow_off * (m["mon_off_pen"] + m["thu_off_pen"])
            + cfg.w_tz_shift_ge2 * m["tz_shifts_ge2"]
            + cfg.w_tz_abs_hour * m["tz_abs"]
            + cfg.w_gap_2d * m["gaps_2d"]
            + cfg.w_regional_road_pair * m["clust_rt"]
        )
        team_rows.append({
            "Team": ab,
            "Div": t["division"],
            "Score": score,
            "EarlyLateDiv": m["early_late_div"],
            "IsoH": m["iso_h"],
            "IsoA": m["iso_a"],
            "LongH/A": m["long_h"] + m["long_a"],
            "RTStarts": m["rt_starts"],
            ">9dPlay": m["streak_gt9"],
            "TZ>=2h": m["tz_shifts_ge2"],
            "TZ_Hours": m["tz_abs"],
            "M/T_Off": m["mon_off_pen"] + m["thu_off_pen"],
            "ASGThu": m["asg_thu"],
            "ClustRT": m["clust_rt"],
            "Miles": m["miles"],
        })

    team_summary_df = pd.DataFrame(team_rows).sort_values(by="Score", ascending=False).reset_index(drop=True)
    team_summary_df.index = team_summary_df.index + 1

    print("\n" + "=" * 76)
    print("INDIVIDUAL TEAM SCHEDULE SCORE LEADERBOARD (Sorted by Objective Score):")
    print("=" * 76)
    pd.set_option("display.max_columns", 15)
    pd.set_option("display.width", 110)
    print(team_summary_df.to_csv(sep="|", index=False))

    total_miles = sum(tm["miles"] for tm in team_metrics.values())
    sorted_miles = sorted(team_metrics.items(), key=lambda x: x[1]["miles"], reverse=True)
    total_clust_rt = sum(tm["clust_rt"] for tm in team_metrics.values())
    total_tz_abs = sum(tm["tz_abs"] for tm in team_metrics.values())

    objective_score = (
        cfg.w_early_late_div * early_late_div_series
        + cfg.w_isolated_home * isolated_homestands
        + cfg.w_isolated_away * short_road_trips
        + cfg.w_long_home * long_homestands
        + cfg.w_long_away * long_road_trips
        + cfg.w_div_31d_excess * len(div_31d_violations)
        + cfg.w_div_91d_gap * len(div_3m_violations)
        + cfg.w_road_trip_start * road_trip_starts
        + cfg.w_missed_april_div * len(missed_apr_list)
        + cfg.w_missed_sept_div * len(missed_sep_list)
        + cfg.w_asg_thursday_game * asg_thu_games
        + cfg.w_streak_over_threshold * excess_days_over_9
        + cfg.w_consec_dow_off * total_excess_dow
        + cfg.w_tz_shift_ge2 * tz_shifts_ge_2h
        + cfg.w_tz_abs_hour * total_tz_abs
        + cfg.w_gap_2d * gaps_eq_2_days
        + cfg.w_regional_road_pair * total_clust_rt
    )

    print("\n" + "=" * 76)
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
    print(f"  7. Playing Streaks >= 17 Days  : {len(streaks_ge_17)} occurrences (Hard Constraint, Max={max_streak}d) {streaks_ge_17[:4]}")
    print(f"  8. Playing Streaks 10-16 Days  : {len(streaks_10_to_16)} streaks / {excess_days_over_9} excess days >9 (Soft Penalty)")
    print(f"  9. Monday Off-Days > 3 wks     : {len(mon_viols)} teams {mon_viols} (Soft Penalty)")
    print(f" 10. Thursday Off-Days > 3 wks   : {len(thu_viols)} teams {thu_viols} (Soft Penalty)")
    print(f" 11. Timezone Shifts >= 2 Hours  : {tz_shifts_ge_2h} occurrences (Soft Penalty)")
    print(f" 12. Div Pairs >2 Series in 31d  : {len(div_31d_violations)} pairs {div_31d_violations[:6]}")
    print(f" 13. Div Pairs >3 Months Apart   : {len(div_3m_violations)} pairs {div_3m_violations[:6]}")
    print(f" 14. Long Road Trips (>3 series) : {long_road_trips} occurrences (Hard Constraint)")
    print(f" 15. Long Homestands (>3 series) : {long_homestands} occurrences (Hard Constraint)")
    print(f" 16. 1-Series Road Trips (==1)   : {short_road_trips} occurrences (Soft Penalty)")
    print(f" 17. 1-Series Homestands (==1)   : {isolated_homestands} occurrences (Soft Penalty)")
    print(f" 18. Missed April Div Matchups   : {len(missed_apr_list)} / 60 pairs {missed_apr_list[:8]}")
    print(f" 19. Missed Sept Div Matchups    : {len(missed_sep_list)} / 60 pairs {missed_sep_list[:8]}")
    print(f" 20. ASG Core Games (Mon-Wed)    : {asg_core_games} games")
    print(f" 21. ASG Thursday Games          : {asg_thu_games} games (Soft Penalty)")
    print("-" * 76)
    print("OBJECTIVE FUNCTION SCORE & COMPONENTS:")
    print(f"  + Early/Late Divisional Series : {early_late_div_series:4d}  (x {cfg.w_early_late_div:+5d} = {cfg.w_early_late_div * early_late_div_series:+8d})")
    print(f"  - Isolated 1-Series Homestands : {isolated_homestands:4d}  (x {cfg.w_isolated_home:+5d} = {cfg.w_isolated_home * isolated_homestands:+8d})")
    print(f"  - Isolated 1-Series Road Trips : {short_road_trips:4d}  (x {cfg.w_isolated_away:+5d} = {cfg.w_isolated_away * short_road_trips:+8d})")
    print(f"  - Long Homestands (>3 series)  : {long_homestands:4d}  (x {cfg.w_long_home:+5d} = {cfg.w_long_home * long_homestands:+8d})")
    print(f"  - Long Road Trips (>3 series)  : {long_road_trips:4d}  (x {cfg.w_long_away:+5d} = {cfg.w_long_away * long_road_trips:+8d})")
    print(f"  - Div Pairs >2 Series in 31d   : {len(div_31d_violations):4d}  (x {cfg.w_div_31d_excess:+5d} = {cfg.w_div_31d_excess * len(div_31d_violations):+8d})")
    print(f"  - Div Pairs >3 Months Apart    : {len(div_3m_violations):4d}  (x {cfg.w_div_91d_gap:+5d} = {cfg.w_div_91d_gap * len(div_3m_violations):+8d})")
    print(f"  - Road Trip Initiations        : {road_trip_starts:4d}  (x {cfg.w_road_trip_start:+5d} = {cfg.w_road_trip_start * road_trip_starts:+8d})")
    print(f"  - Missed April Div Pairs       : {len(missed_apr_list):4d}  (x {cfg.w_missed_april_div:+5d} = {cfg.w_missed_april_div * len(missed_apr_list):+8d})")
    print(f"  - Missed Sept Div Pairs        : {len(missed_sep_list):4d}  (x {cfg.w_missed_sept_div:+5d} = {cfg.w_missed_sept_div * len(missed_sep_list):+8d})")
    print(f"  - ASG Thursday Games           : {asg_thu_games:4d}  (x {cfg.w_asg_thursday_game:+5d} = {cfg.w_asg_thursday_game * asg_thu_games:+8d})")
    print(f"  - Excess Playing Days (>9d)    : {excess_days_over_9:4d}  (x {cfg.w_streak_over_threshold:+5d} = {cfg.w_streak_over_threshold * excess_days_over_9:+8d})")
    print(f"  - Consec M/T Off-Day Weeks     : {total_excess_dow:4d}  (x {cfg.w_consec_dow_off:+5d} = {cfg.w_consec_dow_off * total_excess_dow:+8d})")
    print(f"  - Timezone Shifts >= 2 Hours   : {tz_shifts_ge_2h:4d}  (x {cfg.w_tz_shift_ge2:+5d} = {cfg.w_tz_shift_ge2 * tz_shifts_ge_2h:+8d})")
    print(f"  - 2-Day Inter-Series Gaps      : {gaps_eq_2_days:4d}  (x {cfg.w_gap_2d:+5d} = {cfg.w_gap_2d * gaps_eq_2_days:+8d})")
    print(f"  + Regional Road Trip Pairs     : {total_clust_rt:4d}  (x {cfg.w_regional_road_pair:+5d} = {cfg.w_regional_road_pair * total_clust_rt:+8d})")
    print(f"  ==========================================================================")
    print(f"  TOTAL CP-SAT OBJECTIVE SCORE   : {objective_score:,}")
    print("-" * 76)
    print(f"Total League Travel Distance     : {total_miles:,} miles")
    print("Top 3 Teams by Travel Distance   : " + ", ".join(f"{k} ({v['miles']:,} mi)" for k, v in sorted_miles[:3]))
    print("Bottom 3 Teams by Travel Distance: " + ", ".join(f"{k} ({v['miles']:,} mi)" for k, v in sorted_miles[-3:]))
    print("=" * 76)

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main(
    season_year: int = 2027,
    timeout_sec: int = 1800,
    num_workers: int = 12,
    evaluate_year: int = 0,
    evaluate_csv: Optional[str] = None,
    output_dir: str = "data",
    enable_logos: bool = True,
    profile = "custom"
) -> None:
    overall_start = time.time()

    cfg = get_schedule_config(profile)
    teams = fetch_mlb_teams()
    dist_matrix = build_distance_matrix(teams)

    # Mode A: Audit 2026 Official Schedule from MLB API or an existing CSV file
    if evaluate_year:
        df_hist = fetch_historical_mlb_schedule(evaluate_year, teams)
        evaluate_existing_schedule(df_hist, teams, dist_matrix, season_year=evaluate_year, cfg=cfg)
        # generate_team_schedule_pdfs(df_hist, teams, season_year=evaluate_year, output_dir=output_dir, enable_logos=enable_logos, subtitle="official")
        return

    if evaluate_csv:
        print(f"\nLoading schedule from CSV '{evaluate_csv}' for evaluation...")
        df_csv = pd.read_csv(evaluate_csv)
        evaluate_existing_schedule(df_csv, teams, dist_matrix, season_year=season_year, cfg=cfg)
        # generate_team_schedule_pdfs(df_csv, teams, season_year=season_year, output_dir=output_dir, enable_logos=enable_logos, subtitle="proposed")
        return

    # Mode B: Full Two-Phase CP-SAT Schedule Optimization
    slots, holidays = build_season_slots(season_year=season_year)
    series_list = solve_matchup_quotas(teams, dist_matrix, num_workers=num_workers)

    assignment, metrics = solve_schedule_slots(
        teams=teams,
        slots=slots,
        series_list=series_list,
        dist_matrix=dist_matrix,
        timeout_sec=timeout_sec,
        season_year=season_year,
        num_workers=num_workers,
        verbose_solver_logs=True,
        cfg=cfg
    )

    df, team_miles = expand_to_daily_schedule(
        teams=teams,
        slots=slots,
        series_list=series_list,
        assignment=assignment,
        dist_matrix=dist_matrix,
    )

    master_csv = export_schedule_files(df, teams, output_dir=output_dir)
    generate_team_schedule_pdfs(df, teams, season_year=season_year, output_dir=output_dir, enable_logos=enable_logos, subtitle="proposed")

    run_validation_checks(df, teams, series_list, assignment, slots, holidays, cfg=cfg)

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
    print(f"Excess Playing Days (>9d)   : {metrics['streak_gt9_penalty_days']} penalty days")
    print(f"Isolated 1-Series Homestands: {metrics['isolated_homestands']} league-wide")
    print(f"Isolated 1-Series Road Trips: {metrics['isolated_road_trips']} league-wide")
    print(f"Total League Travel Distance: {total_league_miles:,} miles")
    print("\nTop 3 Teams by Travel Distance:")
    for abbr, miles in sorted_miles[:3]:
        print(f"  - {abbr}: {miles:,} miles")
    print("\nBottom 3 Teams by Travel Distance:")
    for abbr, miles in sorted_miles[-3:]:
        print(f"  - {abbr}: {miles:,} miles")
    print(f"\nExported {len(df):,} game rows to '{master_csv}' (+ 30 CSVs & 30 1-Page PDFs in '{output_dir}/').")
    print("=" * 72)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLB CP-SAT Schedule Optimizer & 1-Page PDF Generator")
    parser.add_argument("--season-year", type=int, default=2027, help="Target season year (default: 2027)")
    parser.add_argument("--timeout", type=int, default=1800, help="Phase 2 solver timeout in seconds (default: 1800)")
    parser.add_argument("--workers", type=int, default=12, help="Number of CP-SAT search workers (default: 12)")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory for CSV/PDF files (default: data)")
    parser.add_argument("--no-logos", action="store_true", help="Disable downloading team logos and use Opponent text in PDFs")
    parser.add_argument("--evaluate-year", type=int, default=0, help="Fetch and audit the official MLB schedule from the specified year")
    parser.add_argument("--evaluate-csv", type=str, default=None, help="Audit an existing schedule CSV file and generate PDFs")
    parser.add_argument(
        "--profile",
        type=str,
        default="custom",
        choices=["custom", "mlb_mimic"],
        help="Optimization weight profile: 'custom' or 'mlb_mimic' (default: custom)",
    )
    args = parser.parse_args()

    main(
        season_year=args.season_year,
        timeout_sec=args.timeout,
        num_workers=args.workers,
        evaluate_year=args.evaluate_year,
        evaluate_csv=args.evaluate_csv,
        output_dir=args.output_dir,
        enable_logos=not args.no_logos,
        profile=args.profile
    )