C:\Users\smoy1\AppData\Local\Programs\Python\Python311\python.exe -m venv research311
research311\Scripts\activate

pip install -r requirements.txt
c:\projects\MLB\research311\Scripts\python.exe -m pip install -r requirements.txt



c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py'

###
# generate constraint violation report for past years

c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py' '--evaluate-year=2025'
c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py' '--evaluate-year=2026'
c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py' '--evaluate-year=2027'

c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py' --evaluate-csv=data/mlb_schedule.csv --season-year=2027

###
# Equivalent parameters for the launch.json
,
            "args": [
                "--evaluate-csv=data/mlb_schedule.csv"
            ]

,
            "args": [
                "--evaluate-year=2025"
            ]


###
# examples

============================================================================
HISTORICAL / EXISTING SCHEDULE AUDIT REPORT (SEASON 2026)
============================================================================
Total Games Evaluated            : 2,430 (Target: 2,430)
Total Reconstructed Series       : 784 (Target: 780)
----------------------------------------------------------------------------
HARD & SOFT CONSTRAINT AUDIT BREAKDOWN:
  1. Teams off 81H/81A Balance   : 4 ['BAL (81H/80A)', 'NYY (80H/81A)', 'ATL (82H/81A)', 'SF (81H/82A)']
  2. Doubleheaders (Same Date)   : 52 team-date collisions
  3. Series != 3 or 4 Games      : 20 series
  4. Non-Opening Series w/ Gap   : 24 series
  5. Inter-Series Gap > 2 Days   : 2 occurrences (Hard Constraint)
  6. Inter-Series Gap == 2 Days  : 4 occurrences (Soft Penalty)
  7. Playing Streaks > 14 Days   : 28 occurrences (Hard Constraint, Max=20d) [('CWS', '2026-08-11', '2026-08-26', 16), ('MIN', '2026-04-01', '2026-04-15', 15), ('MIN', '2026-05-22', '2026-06-07', 17), ('BAL', '2026-08-25', '2026-09-09', 16)]
  8. Playing Streaks 10-14 Days  : 133 streaks / 555 excess days >9 (Soft Penalty)
  9. Div Pairs >2 Series in 31d  : 1 pairs ['NYM-PHI']
 10. Div Pairs >3 Months Apart   : 10 pairs ['CLE-KC', 'BAL-NYY', 'BAL-TOR', 'ATH-SEA', 'ATH-TEX', 'SEA-TEX']
 11. Long Road Trips (>3 series) : 1 occurrences (Hard Constraint)
 12. Long Homestands (>3 series) : 1 occurrences (Hard Constraint)
 13. 1-Series Road Trips (==1)   : 62 occurrences (Soft Penalty)
 14. 1-Series Homestands (==1)   : 45 occurrences (Soft Penalty)
 15. Missed April Div Matchups   : 29 / 60 pairs ['CLE-CWS', 'CLE-DET', 'CLE-MIN', 'CWS-DET', 'CWS-MIN', 'BAL-NYY', 'BAL-TB', 'BAL-TOR']
 16. Missed Sept Div Matchups    : 20 / 60 pairs ['DET-KC', 'KC-MIN', 'BAL-TB', 'BOS-NYY', 'BOS-TOR', 'NYY-TOR', 'TB-TOR', 'HOU-LAA']
 17. ASG Core Games (Mon-Wed)    : 0 games
 18. ASG Thursday Games          : 1 games (Soft Penalty)
----------------------------------------------------------------------------
OBJECTIVE FUNCTION SCORE & COMPONENTS:
  + Early/Late Divisional Series :   81  (x +100 =    +8100)
  - Isolated 1-Series Homestands :   45  (x -250 =   -11250)
  - Isolated 1-Series Road Trips :   62  (x -300 =   -18600)
  - Road Trip Initiations        :  377  (x  -50 =   -18850)
  - Missed April Div Pairs       :   29  (x -500 =   -14500)
  - Missed Sept Div Pairs        :   20  (x -500 =   -10000)
  - ASG Thursday Games           :    1  (x -150 =     -150)
  - Excess Playing Days (>9d)    :  555  (x -150 =   -83250)
  - 2-Day Inter-Series Gaps      :    4  (x -100 =     -400)
  ==========================================================================
  TOTAL CP-SAT OBJECTIVE SCORE   : -148,900
----------------------------------------------------------------------------
Total League Travel Distance     : 1,059,788 miles
Top 3 Teams by Travel Distance   : ATH (50,415 mi), SEA (50,311 mi), SF (47,148 mi)
Bottom 3 Teams by Travel Distance: CHC (28,479 mi), STL (27,192 mi), PIT (27,166 mi)
============================================================================