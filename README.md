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




============================================================================
HISTORICAL / EXISTING SCHEDULE AUDIT REPORT (SEASON 2027)
============================================================================
Total Games Evaluated            : 2,430 (Target: 2,430)
Total Reconstructed Series       : 780 (Target: 780)
----------------------------------------------------------------------------
HARD & SOFT CONSTRAINT AUDIT BREAKDOWN:
  1. Teams off 81H/81A Balance   : 0 []
  2. Doubleheaders (Same Date)   : 4 team-date collisions             Date Team
1190  2027-06-22   SD
1191  2027-06-22   SD
1425  2027-07-10  COL
1426  2027-07-10  COL
1190  2027-06-22  CHC
1191  2027-06-22  CHC
1425  2027-07-10   SD
1426  2027-07-10   SD
  3. Series != 3 or 4 Games      : 1 series [('BAL', 'BOS', '2027-04-27', 2)]
  4. Non-Opening Series w/ Gap   : 5 series [('BOS', 'CIN', ['2027-04-01', '2027-04-03', '2027-04-04']), ('CWS', 'MIL', ['2027-04-01', '2027-04-03', '2027-04-04']), ('STL', 'KC', ['2027-04-01', '2027-04-03', '2027-04-04']), ('KC', 'BOS', ['2027-08-12', '2027-08-14', '2027-08-15']), ('TOR', 'CHC', ['2027-08-19', '2027-08-21', '2027-08-22'])]
  5. Inter-Series Gap > 2 Days   : 0 occurrences (Hard Constraint)
  6. Inter-Series Gap == 2 Days  : 1 occurrences (Soft Penalty)
  7. Playing Streaks >= 17 Days  : 10 occurrences (Hard Constraint, Max=17d) [('CWS', '2027-07-16', '2027-08-01', 17), ('KC', '2027-06-18', '2027-07-04', 17), ('BAL', '2027-05-07', '2027-05-23', 17), ('BOS', '2027-04-09', '2027-04-25', 17)]
  8. Playing Streaks 10-16 Days  : 154 streaks / 536 excess days >9 (Soft Penalty)
  9. Div Pairs >2 Series in 31d  : 0 pairs []
 10. Div Pairs >3 Months Apart   : 17 pairs ['CWS-DET', 'DET-MIN', 'KC-MIN', 'TB-TOR', 'ATH-HOU', 'ATH-SEA', 'HOU-LAA', 'SEA-TEX', 'CHC-MIL', 'CIN-PIT','PIT-STL', 'ATL-MIA', 'PHI-WSH', 'AZ-LAD', 'AZ-SD', 'COL-LAD', 'COL-SF']
 11. Long Road Trips (>3 series) : 0 occurrences (Hard Constraint)
 12. Long Homestands (>3 series) : 1 occurrences (Hard Constraint)
 13. 1-Series Road Trips (==1)   : 55 occurrences (Soft Penalty)
 14. 1-Series Homestands (==1)   : 53 occurrences (Soft Penalty)
 15. Missed April Div Matchups   : 20 / 60 pairs ['CLE-CWS', 'CWS-MIN', 'DET-KC', 'BAL-NYY', 'BOS-NYY', 'BOS-TOR', 'NYY-TB', 'ATH-HOU', 'ATH-LAA', 'LAA-SEA', 'LAA-TEX', 'CHC-CIN', 'MIL-STL', 'PIT-STL', 'ATL-PHI', 'MIA-WSH', 'NYM-PHI', 'AZ-COL', 'LAD-SF', 'SD-SF']
 16. Missed Sept Div Matchups    : 15 / 60 pairs ['CLE-CWS', 'CLE-MIN', 'DET-KC', 'KC-MIN', 'BAL-TOR', 'ATH-LAA', 'ATH-TEX', 'HOU-SEA', 'CHC-PIT', 'CHC-STL', 'CIN-MIL', 'CIN-PIT', 'ATL-NYM', 'AZ-COL', 'LAD-SF']
 17. ASG Core Games (Mon-Wed)    : 0 games
 18. ASG Thursday Games          : 0 games (Soft Penalty)
----------------------------------------------------------------------------
OBJECTIVE FUNCTION SCORE & COMPONENTS:
  + Early/Late Divisional Series :  102  (x +100 =   +10200)
  - Isolated 1-Series Homestands :   53  (x -250 =   -13250)
  - Isolated 1-Series Road Trips :   55  (x -300 =   -16500)
  - Road Trip Initiations        :  376  (x  -50 =   -18800)
  - Missed April Div Pairs       :   20  (x -500 =   -10000)
  - Missed Sept Div Pairs        :   15  (x -500 =    -7500)
  - ASG Thursday Games           :    0  (x -150 =       +0)
  - Excess Playing Days (>9d)    :  536  (x -150 =   -80400)
  - 2-Day Inter-Series Gaps      :    1  (x -100 =     -100)
  ==========================================================================
  TOTAL CP-SAT OBJECTIVE SCORE   : -136,350
----------------------------------------------------------------------------
Total League Travel Distance     : 1,052,712 miles
Top 3 Teams by Travel Distance   : ATH (49,822 mi), SEA (48,782 mi), SF (45,462 mi)
Bottom 3 Teams by Travel Distance: CWS (25,860 mi), MIL (25,617 mi), CHC (24,335 mi)
============================================================================





