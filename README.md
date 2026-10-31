C:\Users\smoy1\AppData\Local\Programs\Python\Python311\python.exe -m venv research311
research311\Scripts\activate

pip install -r requirements.txt




c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'c:\Users\smoy1\.vscode\extensions\ms-python.debugpy-2026.6.0-win32-x64\bundled\libs\debugpy\launcher' '60701' '--' 'C:\projects\MLB\mlb_scheduler.py'

c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py' '--evaluate-2026'


Loaded 2,430 official regular season games for 2026.

============================================================================
HISTORICAL / EXISTING SCHEDULE AUDIT REPORT (SEASON 2026)
============================================================================
Total Games Evaluated            : 2,430 (Target: 2,430)
Total Reconstructed Series       : 784 (Target: 765)
----------------------------------------------------------------------------
CONSTRAINT VIOLATION BREAKDOWN:
  1. Teams off 81H/81A Balance   : 4 ['BAL (81H/80A)', 'NYY (80H/81A)', 'ATL (82H/81A)', 'SF (81H/82A)']
  2. Doubleheaders (Same Date)   : 52 team-date collisions
  3. Series != 3 or 4 Games      : 20 series (e.g., 1- or 2-game series)
  4. Series w/ Internal Date Gap : 32 series
  5. 1-Series Road Trips (<2)    : 62 occurrences
  6. Long Road Trips (>3 series) : 1 occurrences
  7. Long Homestands (>3 series) : 1 occurrences
  8. Missed April Div Matchups   : 29 / 60 pairs ['CLE-CWS', 'CLE-DET', 'CLE-MIN', 'CWS-DET', 'CWS-MIN', 'BAL-NYY', 'BAL-TB', 'BAL-TOR']
  9. Missed Sept Div Matchups    : 20 / 60 pairs ['DET-KC', 'KC-MIN', 'BAL-TB', 'BOS-NYY', 'BOS-TOR', 'NYY-TOR', 'TB-TOR', 'HOU-LAA']
 10. ASG Core Games (Mon-Wed)    : 0 games
 11. ASG Thursday Games          : 1 games
----------------------------------------------------------------------------
OBJECTIVE FUNCTION SCORE & COMPONENTS:
  + Early/Late Divisional Series :   81  (x +100 =    +8100)
  - Isolated 1-Series Homestands :   45  (x -250 =   -11250)
  - Road Trip Initiations        :  377  (x  -50 =   -18850)
  - Missed April Div Pairs       :   29  (x -500 =   -14500)
  - Missed Sept Div Pairs        :   20  (x -500 =   -10000)
  - ASG Thursday Games           :    1  (x -150 =     -150)
  ==========================================================================
  TOTAL CP-SAT OBJECTIVE SCORE   : -46,650
----------------------------------------------------------------------------
Total League Travel Distance     : 1,059,788 miles
Top 3 Teams by Travel Distance   : ATH (50,415 mi), SEA (50,311 mi), SF (47,148 mi)
Bottom 3 Teams by Travel Distance: CHC (28,479 mi), STL (27,192 mi), PIT (27,166 mi)
============================================================================





========================================================================
AUTOMATED SCHEDULE VALIDATION CHECKS
========================================================================
[PASS] Total regular season games == 2,430
[PASS] Zero doubleheaders scheduled (no team plays twice on the same date)
[PASS] All regular series after Opening Weekend have strictly contiguous calendar dates
[PASS] All 30 teams have exactly 162 games (81 Home / 81 Away)
[PASS] All 30 teams play on Memorial Day, July 4th, and Labor Day
[PASS] Core All-Star Break (2027-07-12 to 2027-07-14) has 0 games (Thursday 2027-07-15 early restart games: 0)
[PASS] All divisional quotas met (13 games per opponent; 7H/6A or 6H/7A; 52 total)
[PASS] All road trips and homestands are <= 3 series (soft 1-series road trips: 125)

========================================================================
EXECUTION SUMMARY & OPTIMIZATION METRICS
========================================================================
Target Season Year          : 2027
Solver Status               : FEASIBLE
Phase 2 Solve Runtime       : 1201.25 seconds
Total Script Wall Runtime   : 1201.95 seconds
CP-SAT Objective Value      : -70150
Early/Late Divisional Series: 171 series
Missed April Div Pairs      : 0 / 60 ([])
Missed Sept Div Pairs       : 0 / 60 ([])
ASG Thursday Early Games    : 0 games
Isolated 1-Series Homestands: 122 league-wide
Isolated 1-Series Road Trips: 125 league-wide
Total League Travel Distance: 1,267,328 miles

Top 3 Teams by Travel Distance:
  - ATH: 59,177 miles
  - SEA: 58,869 miles
  - SF: 56,411 miles

Bottom 3 Teams by Travel Distance:
  - PIT: 31,579 miles
  - CHC: 30,827 miles
  - BAL: 28,251 miles

Exported 2,430 game rows to 'mlb_schedule.csv'.