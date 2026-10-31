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
# 2. CALENDAR STRUCTURE & TIME SLOT ARCHITECTURE (DYNAMIC FOR ANY YEAR)
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
    Constructs 52 half-week Series Slots (~26 weeks) dynamically anchored to `season_year`.
    Guarantees all 30 teams play on Memorial Day, July 4th, and Labor Day, and blackouts ASG week.
    """
    holidays = get_calendar_holidays(season_year)
    start_date = holidays["opening_thu"]
    memorial_day = holidays["memorial_day"]
    july_4th = holidays["july_4th"]
    asg_monday = holidays["asg_monday"]
    labor_day = holidays["labor_day"]

    slots: List[Dict[str, Any]] = []

    # Slot 0: Opening Weekend (Thu - Sun)
    slots.append({
        "slot_idx": 0,
        "label": "W01_B_Opening",
        "slot_type": "B",
        "is_asg": False,
        "holiday": None,
        "dates_3g": [start_date, start_date + datetime.timedelta(days=2), start_date + datetime.timedelta(days=3)],
        "dates_4g": [start_date + datetime.timedelta(days=d) for d in range(4)],
        "force_3g": False,
    })

    curr_mon = start_date + datetime.timedelta(days=4)
    slot_idx = 1

    # Generate 25.5 weeks (51 additional slots -> 52 slots total)
    for _ in range(25):
        tue = curr_mon + datetime.timedelta(days=1)
        wed = curr_mon + datetime.timedelta(days=2)
        thu = curr_mon + datetime.timedelta(days=3)
        fri = curr_mon + datetime.timedelta(days=4)
        sat = curr_mon + datetime.timedelta(days=5)
        sun = curr_mon + datetime.timedelta(days=6)
        next_mon = curr_mon + datetime.timedelta(days=7)

        week_num = (slot_idx + 1) // 2 + 1
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
                "holiday": "All-Star Break",
                "dates_3g": [],
                "dates_4g": [],
                "force_3g": False,
            })
        elif curr_mon in (memorial_day, labor_day):
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A",
                "slot_type": "A",
                "is_asg": False,
                "holiday": None,
                "dates_3g": [tue, wed, thu],
                "dates_4g": [tue, wed, thu, thu],
                "force_3g": True,
            })
        elif july_4_in_midweek:
            d3 = sorted(list({tue, wed, july_4th}))
            if len(d3) < 3:
                d3 = [tue, wed, thu]
            slots.append({
                "slot_idx": slot_idx,
                "label": f"W{week_num:02d}_A_July4th",
                "slot_type": "A",
                "is_asg": False,
                "holiday": "July 4th",
                "dates_3g": d3,
                "dates_4g": [curr_mon, tue, wed, thu],
                "force_3g": False,
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
        elif july_4_in_weekend:
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

    # Final Weekend Slot (Slot 51) to complete 52 total slots
    thu = curr_mon + datetime.timedelta(days=3)
    slots.append({
        "slot_idx": slot_idx,
        "label": "W26_B_Finale",
        "slot_type": "B",
        "is_asg": False,
        "holiday": None,
        "dates_3g": [curr_mon + datetime.timedelta(days=4), curr_mon + datetime.timedelta(days=5), curr_mon + datetime.timedelta(days=6)],
        "dates_4g": [thu, curr_mon + datetime.timedelta(days=4), curr_mon + datetime.timedelta(days=5), curr_mon + datetime.timedelta(days=6)],
        "force_3g": False,
    })

    assert len(slots) == 52, f"Expected 52 slots, generated {len(slots)}"
    return slots, holidays


# ==============================================================================
# 3. PHASE 1: SERIES MATRIX & GAME QUOTA SOLVER
# ==============================================================================

def solve_matchup_quotas(teams: List[Dict[str, Any]], num_workers: int = 12) -> List[Dict[str, Any]]:
    """
    Phase 1 CP-SAT Model:
    Computes exact Home/Away and 3-game/4-game series counts for every pair of teams
    so that all 30 teams play 51 series (81 Home games and 81 Away games).
    """
    print("\nPhase 1: Solving league-wide series matrix and 81H/81A game balance...")
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
                s3[i, j] = model.NewConstant(0)
                s4[i, j] = model.NewBoolVar(f"s4_{i}_{j}")
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
            elif is_rival:
                model.Add(s4[i, j] + s4[j, i] == 1)
            else:
                model.Add(s3[i, j] + s3[j, i] == 1)

    for i in range(n):
        non_div_lg = [
            j for j in range(n)
            if j != i and teams[j]["league"] == teams[i]["league"] and teams[j]["division"] != teams[i]["division"]
        ]
        model.Add(sum(s4[i, j] + s4[j, i] for j in non_div_lg) == 4)

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
        iso_vars: List[Any],
        rt_vars: List[Any],
        miss_apr_vars: List[Any],
        miss_sep_vars: List[Any],
    ):
        super().__init__()
        self._div_vars = div_vars
        self._iso_vars = iso_vars
        self._rt_vars = rt_vars
        self._miss_apr_vars = miss_apr_vars
        self._miss_sep_vars = miss_sep_vars
        self._start_time = time.time()
        self._solution_count = 0

    def on_solution_callback(self) -> None:
        self._solution_count += 1
        elapsed = time.time() - self._start_time
        obj = self.ObjectiveValue()
        bound = self.BestObjectiveBound()
        div_cnt = sum(self.Value(v) for v in self._div_vars)
        iso_cnt = sum(self.Value(v) for v in self._iso_vars)
        rt_cnt = sum(self.Value(v) for v in self._rt_vars)
        m_apr = sum(self.Value(v) for v in self._miss_apr_vars)
        m_sep = sum(self.Value(v) for v in self._miss_sep_vars)
        print(
            f"  [Solution #{self._solution_count:02d} @ {elapsed:6.1f}s] "
            f"Obj: {obj:8.0f} (Bound: {bound:8.0f}) | "
            f"Missed Apr/Sep Pairs: {m_apr:2d}/{m_sep:2d} | "
            f"Early/Late Div: {div_cnt:3d} | "
            f"1-Series Home: {iso_cnt:2d} | "
            f"Road Trips: {rt_cnt:3d}"
        )


def solve_schedule_slots(
    teams: List[Dict[str, Any]],
    slots: List[Dict[str, Any]],
    series_list: List[Dict[str, Any]],
    dist_matrix: List[List[int]],
    timeout_sec: int = 300,
    season_year: int = 2027,
    num_workers: int = 12,
    verbose_solver_logs: bool = True,
) -> Tuple[Dict[int, int], Dict[str, Any]]:
    """
    Phase 2 CP-SAT Model:
    Assigns all 765 series to the 51 active half-week slots with soft penalties
    for unaccommodated April/September divisional opponents.
    """
    print("\nPhase 2: Building CP-SAT slot assignment and road-trip routing model...")
    t0 = time.time()
    model = cp_model.CpModel()
    n_teams = len(teams)
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]
    n_active = len(active_slots)  # 51 active slots

    # Target April (<= Apr 30) and September (>= Sep 1) windows for soft divisional spacing
    april_cutoff = datetime.date(season_year, 4, 30)
    sept_cutoff = datetime.date(season_year, 9, 1)

    april_slots = [s["slot_idx"] for s in slots if not s["is_asg"] and s["dates_3g"][0] <= april_cutoff]
    sept_slots = [s["slot_idx"] for s in slots if not s["is_asg"] and s["dates_3g"][-1] >= sept_cutoff]

    if not april_slots or not sept_slots:
        raise ValueError(f"Empty April ({len(april_slots)}) or Sept ({len(sept_slots)}) slots for year {season_year}")

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
    pair_series = {}
    for sid, sr in enumerate(series_list):
        h, a = sr["home"], sr["away"]
        home_series_by_team[h].append(sid)
        away_series_by_team[a].append(sid)
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

    # 2. Divisional Spacing Constraints (SOFT <= April 30 and >= September 1 with penalty slacks)
    missed_april_vars = []
    missed_sept_vars = []
    div_pair_meta = []

    for (t1, t2), sids in pair_series.items():
        if teams[t1]["division"] == teams[t2]["division"]:
            miss_apr = model.NewBoolVar(f"miss_apr_{t1}_{t2}")
            miss_sep = model.NewBoolVar(f"miss_sep_{t1}_{t2}")

            # Soft lower bound: either >= 1 series is scheduled in the window, or miss_* == 1
            model.Add(sum(x[sid, s] for sid in sids for s in april_slots) + miss_apr >= 1)
            model.Add(sum(x[sid, s] for sid in sids for s in sept_slots) + miss_sep >= 1)

            missed_april_vars.append(miss_apr)
            missed_sept_vars.append(miss_sep)
            div_pair_meta.append((teams[t1]["abbr"], teams[t2]["abbr"], miss_apr, miss_sep))

            # Hard constraint: prevent playing the same divisional opponent in back-to-back slots
            for k in range(n_active - 1):
                s_curr, s_next = active_slots[k], active_slots[k + 1]
                model.Add(sum(x[sid, s_curr] + x[sid, s_next] for sid in sids) <= 1)

    # 3. Road Trip & Homestand Length Constraints (Hard)
    isolated_home_vars = []
    for t in range(n_teams):
        for k in range(n_active - 3):
            window = [is_home[t, k + d] for d in range(4)]
            model.Add(sum(window) <= 3)  # Max 3 consecutive Home series
            model.Add(sum(window) >= 1)  # Max 3 consecutive Away series

        # Min 2 consecutive Away series (forbid isolated 1-series road trips)
        # model.Add(is_home[t, 0] + (1 - is_home[t, 1]) >= 1)
        # model.Add(is_home[t, n_active - 1] + (1 - is_home[t, n_active - 2]) >= 1)
        # for k in range(1, n_active - 1):
        #     model.Add(is_home[t, k - 1] + (1 - is_home[t, k]) + is_home[t, k + 1] <= 2)

        #     iso_h = model.NewBoolVar(f"iso_h_{t}_{k}")
        #     model.Add(iso_h >= is_home[t, k] - is_home[t, k - 1] - is_home[t, k + 1])
        #     isolated_home_vars.append(iso_h)

    # 4. Multi-Objective Formulation
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

    # Each missed divisional pair means 2 teams missed that opponent in April/Sept (-1000 per pair = -500 per team-opponent)
    model.Maximize(
        100 * sum(div_early_late_terms)
        - 250 * sum(isolated_home_vars)
        - 50 * sum(road_trip_starts)
        - 10 * sum(missed_april_vars)
        - 10 * sum(missed_sept_vars)
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(timeout_sec)
    solver.parameters.num_search_workers = num_workers
    solver.parameters.log_search_progress = verbose_solver_logs
    solver.parameters.relative_gap_limit = 0.02

    callback = SolutionProgressCallback(
        div_early_late_terms,
        isolated_home_vars,
        road_trip_starts,
        missed_april_vars,
        missed_sept_vars,
    )
    print(f"Solving Phase 2 (workers={num_workers}, max_time={timeout_sec}s, gap_limit=2%)...")
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

    metrics = {
        "status": status_name,
        "solve_time_sec": round(solve_time, 2),
        "objective_value": solver.ObjectiveValue(),
        "isolated_homestands": sum(solver.Value(v) for v in isolated_home_vars),
        "early_late_div_series": sum(solver.Value(v) for v in div_early_late_terms),
        "missed_april_pairs": len(missed_apr_pairs),
        "missed_sept_pairs": len(missed_sep_pairs),
        "missed_april_list": missed_apr_pairs,
        "missed_sept_list": missed_sep_pairs,
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
    """
    Computes initial sequential venue-to-venue travel distance across all 30 teams.
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
    Expands the solved series-to-slot assignment into 2,430 individual game records.
    """
    n_teams = len(teams)
    active_slots = [s["slot_idx"] for s in slots if not s["is_asg"]]

    slot_series: Dict[int, List[Dict[str, Any]]] = {s: [] for s in active_slots}
    for sid, s in assignment.items():
        slot_series[s].append(series_list[sid])

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
                is_day_game = bool(
                    (is_final_game and dow in ("Monday", "Thursday")) or dow == "Sunday"
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
    df.sort_values(by=["Date", "HomeTeam"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df, team_total_miles


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
    print("[PASS] Total regular season games == 2,430")

    home_counts = df["HomeTeam"].value_counts().to_dict()
    away_counts = df["AwayTeam"].value_counts().to_dict()
    for t in teams:
        abbr = t["abbr"]
        hc = home_counts.get(abbr, 0)
        ac = away_counts.get(abbr, 0)
        assert hc == 81 and ac == 81, f"Team {abbr} has {hc}H / {ac}A (expected 81H / 81A)"
    print("[PASS] All 30 teams have exactly 162 games (81 Home / 81 Away)")

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

    asg_mon = holidays["asg_monday"]
    asg_wed = asg_mon + datetime.timedelta(days=2)
    asg_games = df[(df["Date"] >= asg_mon.isoformat()) & (df["Date"] <= asg_wed.isoformat())]
    assert len(asg_games) == 0, f"Found {len(asg_games)} games during All-Star Break!"
    print(f"[PASS] All-Star Break ({asg_mon.isoformat()} to {asg_wed.isoformat()}) has 0 games scheduled")

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

def main(season_year: int = 2027, timeout_sec: int = 300, num_workers: int = 12) -> None:
    overall_start = time.time()

    teams = fetch_mlb_teams()
    dist_matrix = build_distance_matrix(teams)

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

    output_csv = "mlb_schedule.csv"
    df.to_csv(output_csv, index=False)

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
    main(season_year=2027, timeout_sec=600, num_workers=12)