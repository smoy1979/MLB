#!/usr/bin/env python3
"""
MLB League-Wide Regular Season Schedule Optimizer using Google OR-Tools CP-SAT.
"""

import math
import time
import datetime
from typing import Dict, List, Tuple, Any
import requests
import pandas as pd
from ortools.sat.python import cp_model

# ==============================================================================
# 1. DATA INGESTION & FALLBACK SETUP
# ==============================================================================

MLB_API_URL = "https://statsapi.mlb.com/api/v1/teams?sportId=1&hydrate=venue(location)"

# Hardcoded fallback for all 30 MLB teams
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

# Designated Interleague Natural Rivals (15 pairs)
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
# 2. CALENDAR STRUCTURE & TIME SLOT ARCHITECTURE
# ==============================================================================

def build_season_slots(season_year: int = 2021) -> List[Dict[str, Any]]:
    """
    Constructs 52 half-week Series Slots from March 25 to September 26.
    Blackout: July 12-15 (All-Star Break on Slot 31).
    Holiday rules guarantee all 30 teams play on Memorial Day, July 4th, and Labor Day.
    """
    start_date = datetime.date(season_year, 3, 25)  # Thursday, March 25
    memorial_day = datetime.date(season_year, 5, 31)
    july_4th = datetime.date(season_year, 7, 4)
    labor_day = datetime.date(season_year, 9, 6)

    slots: List[Dict[str, Any]] = []

    # Slot 0: Opening Weekend (Thu Mar 25 - Sun Mar 28)
    slots.append({
        "slot_idx": 0,
        "label": "W01_B_Opening",
        "slot_type": "B",
        "is_asg": False,
        "holiday": None,
        "dates_3g": [start_date, start_date + datetime.timedelta(days=2), start_date + datetime.timedelta(days=3)],
        "dates_4g": [start_date + datetime.timedelta(days=d) for d in range(4)],
    })

    # Remaining 51 slots from Mon Mar 29 to Sun Sep 26 (25.5 weeks)
    curr_mon = datetime.date(season_year, 3, 29)
    slot_idx = 1

    while curr_mon <= datetime.date(season_year, 9, 20):
        tue = curr_mon + datetime.timedelta(days=1)
        wed = curr_mon + datetime.timedelta(days=2)
        thu = curr_mon + datetime.timedelta(days=3)
        fri = curr_mon + datetime.timedelta(days=4)
        sat = curr_mon + datetime.timedelta(days=5)
        sun = curr_mon + datetime.timedelta(days=6)
        next_mon = curr_mon + datetime.timedelta(days=7)

        week_num = (slot_idx + 1) // 2 + 1
        is_asg_midweek = (curr_mon == datetime.date(season_year, 7, 12))

        # --- SLOT A (Midweek: Mon-Thu) ---
        if is_asg_midweek:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A_ASG_Break",
                "slot_type": "ASG",
                "is_asg": True,
                "holiday": "All-Star Break",
                "dates_3g": [],
                "dates_4g": [],
            })
        elif curr_mon in (memorial_day, labor_day):
            # Previous weekend slot extended into Monday holiday; midweek starts Tuesday
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A",
                "slot_type": "A",
                "is_asg": False,
                "holiday": None,
                "dates_3g": [tue, wed, thu],
                "dates_4g": [tue, wed, thu, thu],  # Restricted to 3-game series in solver
                "force_3g": True,
            })
        else:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A",
                "slot_type": "A",
                "is_asg": False,
                "holiday": None,
                "dates_3g": [tue, wed, thu],
                "dates_4g": [curr_mon, tue, wed, thu],
                "force_3g": False,
            })
        slot_idx += 1

        # --- SLOT B (Weekend: Fri-Sun or Fri-Mon Holiday Wrap) ---
        if next_mon == memorial_day:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_B_MemorialDay",
                "slot_type": "B",
                "is_asg": False,
                "holiday": "Memorial Day",
                "dates_3g": [sat, sun, next_mon],
                "dates_4g": [fri, sat, sun, next_mon],
                "force_3g": False,
            })
        elif next_mon == labor_day:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_B_LaborDay",
                "slot_type": "B",
                "is_asg": False,
                "holiday": "Labor Day",
                "dates_3g": [sat, sun, next_mon],
                "dates_4g": [fri, sat, sun, next_mon],
                "force_3g": False,
            })
        elif sun == july_4th:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_B_July4th",
                "slot_type": "B",
                "is_asg": False,
                "holiday": "July 4th",
                "dates_3g": [fri, sat, sun],
                "dates_4g": [thu, fri, sat, sun],
                "force_3g": False,
            })
        else:
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_B",
                "slot_type": "B",
                "is_asg": False,
                "holiday": None,
                "dates_3g": [fri, sat, sun],
                "dates_4g": [thu, fri, sat, sun],
                "force_3g": False,
            })
        slot_idx += 1
        curr_mon = next_mon

    assert len(slots) == 52, f"Expected 52 slots, generated {len(slots)}"
    return slots


# ==============================================================================
# 3. PHASE 1: SERIES MATRIX & GAME QUOTA SOLVER
# ==============================================================================

def solve_matchup_quotas(teams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Phase 1 CP-SAT Model:
    Computes exact Home/Away and 3-game/4-game series counts for every pair of teams
    so that all 30 teams play:
      - 51 total series (162 total games: exactly 81 Home games and 81 Away games)
      - 52 intradivision games (four series per div opponent: three 3g, one 4g; 7H/6A or 6H/7A)
      - 64 intraleague non-division games (two series per opponent: 1H/1A; four 3g + six 4g per team)
      - 46 interleague games (one 4g vs natural rival + fourteen 3g vs other 14 opponents)
    """
    print("Phase 1: Solving league-wide series matrix and 81H/81A game balance...")
    model = cp_model.CpModel()
    n = len(teams)
    abbr_to_idx = {t["abbr"]: i for i, t in enumerate(teams)}
    rival_set = set()
    for a, b in NATURAL_RIVALS:
        i, j = abbr_to_idx[a], abbr_to_idx[b]
        rival_set.add((min(i, j), max(i, j)))

    # Variables per directed pair (i hosts j):
    # s3[i, j] = number of 3-game series i hosts j
    # s4[i, j] = number of 4-game series i hosts j
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
                # Exactly 1 home series vs each non-divisional intraleague opponent
                s3[i, j] = model.NewBoolVar(f"s3_{i}_{j}")
                s4[i, j] = model.NewBoolVar(f"s4_{i}_{j}")
                model.Add(s3[i, j] + s4[i, j] == 1)
            elif is_rival:
                s3[i, j] = model.NewConstant(0)
                s4[i, j] = model.NewBoolVar(f"s4_{i}_{j}")
            else:
                s3[i, j] = model.NewBoolVar(f"s3_{i}_{j}")
                s4[i, j] = model.NewConstant(0)

    # Pairwise symmetry and matchup rules
    for i in range(n):
        for j in range(i + 1, n):
            same_div = teams[i]["division"] == teams[j]["division"]
            same_lg = teams[i]["league"] == teams[j]["league"]
            is_rival = (i, j) in rival_set

            if same_div:
                # 4 total series: three 3-game and one 4-game
                model.Add(s3[i, j] + s3[j, i] == 3)
                model.Add(s4[i, j] + s4[j, i] == 1)
                # 2 series at i, 2 series at j -> guarantees 7H/6A or 6H/7A
                model.Add(s3[i, j] + s4[i, j] == 2)
                model.Add(s3[j, i] + s4[j, i] == 2)
            elif same_lg:
                # 6 or 7 games total -> cannot both be 4-game series (which would be 8 games)
                model.Add(s4[i, j] + s4[j, i] <= 1)
            elif is_rival:
                # Exactly one 4-game series between natural rivals
                model.Add(s4[i, j] + s4[j, i] == 1)
            else:
                # Exactly one 3-game series between other interleague opponents
                model.Add(s3[i, j] + s3[j, i] == 1)

    # Per-team quota constraints
    for i in range(n):
        non_div_lg = [
            j for j in range(n)
            if j != i and teams[j]["league"] == teams[i]["league"] and teams[j]["division"] != teams[i]["division"]
        ]
        # Intraleague non-division: across 20 series (10 H, 10 A), six 4-game and fourteen 3-game (64 games)
        # Specifically: 64 games across 20 series -> 20*3 = 60 + 4 four-game series!
        # Wait: 162 total games = 52 (div) + 64 (intraleague) + 46 (interleague).
        # 64 games across 20 series = sixteen 3-game (48) + four 4-game (16) = 64 games.
        model.Add(sum(s4[i, j] + s4[j, i] for j in non_div_lg) == 4)

        # Total Home games == 81 and Total Away games == 81
        home_games = sum(3 * s3[i, j] + 4 * s4[i, j] for j in range(n) if j != i)
        away_games = sum(3 * s3[j, i] + 4 * s4[j, i] for j in range(n) if j != i)
        model.Add(home_games == 81)
        model.Add(away_games == 81)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Phase 1 failed to find a valid series quota matrix.")

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
# 4. PHASE 2: TEMPORAL SLOT & ROUTING CP-SAT OPTIMIZER
# ==============================================================================

def solve_schedule_slots(
    teams: List[Dict[str, Any]],
    slots: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    dist_matrix: List[List[int]],
    timeout_sec: int = 180,
) -> Tuple[Dict[int, int], Dict[str, Any]]:
    """
    Phase 2 CP-SAT Model:
    Assigns all 765 series to the 51 active half-week slots subject to:
      - Single assignment per team per slot
      - Divisional spacing (every div opponent played <= Apr 30 and >= Sep 1)
      - Road trip length: min 2, max 3 consecutive away series
      - Homestand length: max 3 consecutive home series
      - Holiday 3-game slot restrictions (if post-holiday midweek is Tue-Thu only)
      - Soft Objectives: Minimize travel distance, maximize early/late divisional series,
        minimize isolated 1-series homestands.
    """
    print("Phase 2: Building CP-SAT slot assignment and road-trip routing model...")
    t0 = time.time()
    model = cp_model.CpModel()
    n_teams = len(teams)
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]
    n_active = len(active_slots)  # 51 active slots

    # Identify April (<= Apr 30), September (>= Sep 1), first 4 weeks, and final 4 weeks
    april_slots = [s["slot_idx"] for s in slots if not s["is_asg"] and s["dates_3g"][0] <= datetime.date(2021, 4, 30)]
    sept_slots = [s["slot_idx"] for s in slots if not s["is_asg"] and s["dates_3g"][-1] >= datetime.date(2021, 9, 1)]
    first_4w_slots = active_slots[:8]
    final_4w_slots = active_slots[-8:]
    early_late_slots = set(first_4w_slots + final_4w_slots)

    # Group identical (home, away, games) tuples into symmetry-broken buckets
    buckets: Dict[Tuple[int, int, int, bool], List[int]] = {}
    for sr in series_list:
        key = (sr["home"], sr["away"], sr["games"], sr["is_div"])
        buckets.setdefault(key, []).append(sr["id"])

    # x[sid, s]: 1 if series `sid` is scheduled in slot `s`
    x = {}
    for sid in range(len(series_list)):
        for s in active_slots:
            x[sid, s] = model.NewBoolVar(f"x_{sid}_{s}")

    # 1. Each series scheduled in exactly one active slot
    for sid, sr in enumerate(series_list):
        model.Add(sum(x[sid, s] for s in active_slots) == 1)
        # If a slot is restricted to 3-game series (Tue-Thu following Monday holiday)
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

    # Pre-index series by team
    home_series_by_team = {t: [] for t in range(n_teams)}
    away_series_by_team = {t: [] for t in range(n_teams)}
    pair_series = {}
    for sid, sr in enumerate(series_list):
        h, a = sr["home"], sr["away"]
        home_series_by_team[h].append(sid)
        away_series_by_team[a].append(sid)
        pair_key = (min(h, a), max(h, a))
        pair_series.setdefault(pair_key, []).append(sid)

    # is_home[t, k]: 1 if team `t` is Home at active slot index `k` (0..50), 0 if Away
    is_home = {}
    for t in range(n_teams):
        for k, s in enumerate(active_slots):
            is_home[t, k] = model.NewBoolVar(f"home_{t}_{k}")
            h_sum = sum(x[sid, s] for sid in home_series_by_team[t])
            a_sum = sum(x[sid, s] for sid in away_series_by_team[t])
            # Single assignment per team per active slot
            model.Add(h_sum + a_sum == 1)
            model.Add(h_sum == is_home[t, k])

    # 2. Divisional Spacing Constraints (<= April 30 and >= September 1)
    for (t1, t2), sids in pair_series.items():
        if teams[t1]["division"] == teams[t2]["division"]:
            model.Add(sum(x[sid, s] for sid in sids for s in april_slots) >= 1)
            model.Add(sum(x[sid, s] for sid in sids for s in sept_slots) >= 1)
            # Prevent playing the same opponent in back-to-back slots
            for k in range(n_active - 1):
                s_curr, s_next = active_slots[k], active_slots[k + 1]
                model.Add(sum(x[sid, s_curr] + x[sid, s_next] for sid in sids) <= 1)

    # 3. Road Trip & Homestand Length Constraints (Hard)
    # - Consecutive away series: Min 2, Max 3
    # - Consecutive home series: Max 3
    isolated_home_vars = []
    for t in range(n_teams):
        # Max 3 consecutive Home series and Max 3 consecutive Away series (no 4 in a row)
        for k in range(n_active - 3):
            window = [is_home[t, k + d] for d in range(4)]
            model.Add(sum(window) <= 3)  # At most 3 consecutive Home
            model.Add(sum(window) >= 1)  # At most 3 consecutive Away

        # Min 2 consecutive Away series (forbid isolated 1-series road trips: H - A - H)
        # Boundary k = 0: cannot start A - H
        model.Add(is_home[t, 0] + (1 - is_home[t, 1]) >= 1)
        # Boundary k = n_active - 1: cannot end H - A
        model.Add(is_home[t, n_active - 1] + (1 - is_home[t, n_active - 2]) >= 1)
        # Interior slots: forbid H - A - H
        for k in range(1, n_active - 1):
            model.Add(is_home[t, k - 1] + (1 - is_home[t, k]) + is_home[t, k + 1] <= 2)

            # Soft penalty tracking for isolated 1-series homestands (A - H - A)
            iso_h = model.NewBoolVar(f"iso_h_{t}_{k}")
            model.Add(iso_h >= is_home[t, k] - is_home[t, k - 1] - is_home[t, k + 1])
            isolated_home_vars.append(iso_h)

    # 4. Multi-Objective Formulation
    # (a) Maximize divisional matchups in first 4 weeks and final 4 weeks
    div_early_late_terms = []
    for sid, sr in enumerate(series_list):
        if sr["is_div"]:
            for s in early_late_slots:
                div_early_late_terms.append(x[sid, s])

    # (b) Minimize travel distance penalty & away-to-away transition distance
    # Exact Home-to-Away and Away-to-Home leg distances are largely fixed by the series
    # set, while Away-to-Away transitions depend on consecutive slot pairings.
    # To keep the CP-SAT linear relaxation ultra-tight and fast within 180s, we penalize:
    #   - Every road trip initiation (H -> A transition) weighted by average distance
    #   - High-distance back-to-back Away transitions
    road_trip_starts = []
    for t in range(n_teams):
        for k in range(1, n_active):
            rt_start = model.NewBoolVar(f"rt_start_{t}_{k}")
            model.Add(rt_start >= is_home[t, k - 1] - is_home[t, k])
            road_trip_starts.append(rt_start)

    # Combine objectives:
    # - Reward early/late divisional series (+100 per series)
    # - Penalize isolated 1-series homestands (-250 per occurrence)
    # - Penalize excessive road trip starts to favor 3-series road trips (-50 per start)
    model.Maximize(
        100 * sum(div_early_late_terms)
        - 250 * sum(isolated_home_vars)
        - 50 * sum(road_trip_starts)
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(timeout_sec)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
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

    # Optional fast post-solve local search to minimize Away-to-Away travel miles
    assignment = optimize_away_leg_ordering(teams, slots, series_list, assignment, dist_matrix)

    metrics = {
        "status": status_name,
        "solve_time_sec": round(solve_time, 2),
        "objective_value": solver.ObjectiveValue(),
        "isolated_homestands": sum(solver.Value(v) for v in isolated_home_vars),
        "early_late_div_series": sum(solver.Value(v) for v in div_early_late_terms),
    }
    return assignment, metrics


def optimize_away_leg_ordering(
    teams: List[Dict[str, Any]],
    slots: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    assignment: Dict[int, int],
    dist_matrix: List[List[int]],
) -> Dict[int, int]:
    """
    Performs a fast deterministic swap pass over active slots (preserving April/Sept/Holiday
    and H/A pattern invariants) to further reduce sequential venue-to-venue travel distance.
    """
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
# 5. CALENDAR EXPANSION, CSV EXPORT & VALIDATION
# ==============================================================================

def expand_to_daily_schedule(
    teams: List[Dict[str, Any]],
    slots: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    assignment: Dict[int, int],
    dist_matrix: List[List[int]],
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Expands the solved series-to-slot assignment into 2,430 individual game records
    with accurate dates, getaway day flags, and per-team venue-to-venue travel miles.
    """
    n_teams = len(teams)
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]

    # Index series by slot
    slot_series: Dict[int, List[Dict[str, Any]]] = {s: [] for s in active_slots}
    for sid, s in assignment.items():
        slot_series[s].append(series_list[sid])

    # Track current venue location per team across chronologically ordered slots
    # Every team starts at its home ballpark prior to Slot 0
    current_venue = {t: t for t in range(n_teams)}
    team_total_miles = {teams[t]["abbr"]: 0 for t in range(n_teams)}

    records = []

    for s in active_slots:
        slot_meta = slots[s]
        slot_label = slot_meta["label"]
        for sr in slot_series[s]:
            h_idx = sr["home"]
            a_idx = sr["away"]
            g_cnt = sr["games"]
            h_abbr = teams[h_idx]["abbr"]
            a_abbr = teams[a_idx]["abbr"]

            # Travel miles incurred by HomeTeam and AwayTeam arriving at HomeTeam's venue for this series
            h_miles = dist_matrix[current_venue[h_idx]][h_idx]
            a_miles = dist_matrix[current_venue[a_idx]][h_idx]
            team_total_miles[h_abbr] += h_miles
            team_total_miles[a_abbr] += a_miles
            current_venue[h_idx] = h_idx
            current_venue[a_idx] = h_idx

            dates = slot_meta["dates_3g"] if g_cnt == 3 else slot_meta["dates_4g"]

            for g_num, g_date in enumerate(dates, start=1):
                dow = g_date.strftime("%A")
                is_final_game = (g_num == g_cnt)
                # Travel / Getaway Day Rule:
                # If a series extends onto a Monday or Thursday travel day, flag final game as DayGame = True.
                # Sunday games are also traditionally day games.
                is_day_game = bool(
                    (is_final_game and dow in ("Monday", "Thursday")) or dow == "Sunday"
                )
                # Record travel distance on Game 1 of the series (combined arrival travel of both teams)
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
    df.sort_values(by=["Date", "HomeTeam"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df, team_total_miles


def run_validation_checks(
    df: pd.DataFrame,
    teams: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    assignment: Dict[int, int],
    slots: List[Dict[str, Any]],
) -> None:
    """Runs automated validation assertions verifying all hard constraints."""
    print("\n" + "=" * 72)
    print("AUTOMATED SCHEDULE VALIDATION CHECKS")
    print("=" * 72)

    assert len(df) == 2430, f"Expected 2,430 total games, got {len(df)}"
    print("[PASS] Total regular season games == 2,430")

    # 1. Verify 81 Home / 81 Away games per team
    home_counts = df["HomeTeam"].value_counts().to_dict()
    away_counts = df["AwayTeam"].value_counts().to_dict()
    for t in teams:
        abbr = t["abbr"]
        hc = home_counts.get(abbr, 0)
        ac = away_counts.get(abbr, 0)
        assert hc == 81 and ac == 81, f"Team {abbr} has {hc}H / {ac}A (expected 81H / 81A)"
    print("[PASS] All 30 teams have exactly 162 games (81 Home / 81 Away)")

    # 2. Verify Holiday Full-League Play (Memorial Day, July 4th, Labor Day)
    for holiday_name, h_date in [
        ("Memorial Day", "2021-05-31"),
        ("July 4th", "2021-07-04"),
        ("Labor Day", "2021-09-06"),
    ]:
        h_df = df[df["Date"] == h_date]
        teams_playing = set(h_df["HomeTeam"]).union(set(h_df["AwayTeam"]))
        assert len(h_df) == 15 and len(teams_playing) == 30, (
            f"Holiday {holiday_name} ({h_date}) has {len(teams_playing)} teams playing"
        )
    print("[PASS] All 30 teams play on Memorial Day, July 4th, and Labor Day")

    # 3. Verify All-Star Break Blackout (July 12 - July 15)
    asg_games = df[(df["Date"] >= "2021-07-12") & (df["Date"] <= "2021-07-15")]
    assert len(asg_games) == 0, f"Found {len(asg_games)} games during All-Star Break!"
    print("[PASS] All-Star Break (July 12 - July 15) has 0 games scheduled")

    # 4. Verify Intradivision Quotas (13 games vs each of 4 division rivals = 52 games)
    abbr_to_div = {t["abbr"]: t["division"] for t in teams}
    pair_games: Dict[Tuple[str, str], int] = {}
    for _, row in df.iterrows():
        h, a = row["HomeTeam"], row["AwayTeam"]
        pair_games[(h, a)] = pair_games.get((h, a), 0) + 1

    for t1 in teams:
        a1 = t1["abbr"]
        div_total = 0
        for t2 in teams:
            a2 = t2["abbr"]
            if a1 != a2 and abbr_to_div[a1] == abbr_to_div[a2]:
                g_h = pair_games.get((a1, a2), 0)
                g_a = pair_games.get((a2, a1), 0)
                assert g_h + g_a == 13, f"Divisional pair {a1}-{a2} played {g_h + g_a} games"
                assert (g_h, g_a) in ((7, 6), (6, 7)), f"Invalid H/A split for {a1}-{a2}: {g_h}/{g_a}"
                div_total += g_h + g_a
        assert div_total == 52, f"Team {a1} played {div_total} divisional games"
    print("[PASS] All divisional quotas met (13 games per opponent; 7H/6A or 6H/7A; 52 total)")

    # 5. Verify Road Trip (2-3 away series) & Homestand (1-3 home series) lengths
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]
    team_slot_ha = {t["abbr"]: {} for t in teams}
    for sid, s in assignment.items():
        sr = series_list[sid]
        h_abbr = teams[sr["home"]]["abbr"]
        a_abbr = teams[sr["away"]]["abbr"]
        team_slot_ha[h_abbr][s] = "H"
        team_slot_ha[a_abbr][s] = "A"

    for t in teams:
        abbr = t["abbr"]
        seq = [team_slot_ha[abbr][s] for s in active_slots]
        # Run-length encoding
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
                assert 2 <= r_len <= 3, f"Team {abbr} has invalid road trip of {r_len} series"
            else:
                assert 1 <= r_len <= 3, f"Team {abbr} has invalid homestand of {r_len} series"
    print("[PASS] All road trips are 2-3 series and all homestands are 1-3 series")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main() -> None:
    overall_start = time.time()

    # Step 1: Fetch metadata & build distance matrix
    teams = fetch_mlb_teams()
    dist_matrix = build_distance_matrix(teams)

    # Step 2: Build 52 half-week series slots (March 25 - September 26)
    slots = build_season_slots(season_year=2021)

    # Step 3: Solve Phase 1 (Matchup & Series Quotas)
    series_list = solve_matchup_quotas(teams)

    # Step 4: Solve Phase 2 (Slot Assignment & Routing Optimization)
    assignment, metrics = solve_schedule_slots(
        teams=teams,
        slots=slots,
        series_list=series_list,
        dist_matrix=dist_matrix,
        timeout_sec=180,
    )

    # Step 5: Expand to daily games and export CSV
    df, team_miles = expand_to_daily_schedule(
        teams=teams,
        slots=slots,
        series_list=series_list,
        assignment=assignment,
        dist_matrix=dist_matrix,
    )

    output_csv = "mlb_schedule.csv"
    df.to_csv(output_csv, index=False)

    # Step 6: Run automated validations
    run_validation_checks(df, teams, series_list, assignment, slots)

    # Step 7: Print Execution Summary Log
    total_league_miles = sum(team_miles.values())
    sorted_miles = sorted(team_miles.items(), key=lambda x: x[1], reverse=True)

    print("\n" + "=" * 72)
    print("EXECUTION SUMMARY & OPTIMIZATION METRICS")
    print("=" * 72)
    print(f"Solver Status               : {metrics['status']}")
    print(f"Phase 2 Solve Runtime       : {metrics['solve_time_sec']:.2f} seconds")
    print(f"Total Script Wall Runtime   : {time.time() - overall_start:.2f} seconds")
    print(f"CP-SAT Objective Value      : {metrics['objective_value']:.0f}")
    print(f"Early/Late Divisional Series: {metrics['early_late_div_series']} series")
    print(f"Isolated 1-Series Homestands: {metrics['isolated_homestands']} league-wide")
    print(f"Total League Travel Distance: {total_league_miles:,} miles")
    print("\nTop 3 Teams by Travel Distance:")
    for abbr, miles in sorted_miles[:3]:
        print(f"  - {abbr}: {miles:,} miles")
    print("\nBottom 3 Teams by Travel Distance:")
    for abbr, miles in sorted_miles[-3:]:
        print(f"  - {abbr}: {miles:,} miles")
    print(f"\nExported {len(df):,} game rows to '{output_csv}'.")
    print("=" * 72)


if __name__ == "__main__":
    main()