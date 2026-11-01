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





Task timing                      n [     min,      max]      avg      dev     time         n [     min,      max]      avg      dev    dtime
                 'core':         1 [  29.95m,   29.95m]   29.95m   0.00ns   29.95m         2 [   1.11s,   49.28m]   24.65m   24.63m   49.30m
           'default_lp':         1 [  29.95m,   29.95m]   29.95m   0.00ns   29.95m         2 [   1.11s,   13.82m]    6.92m    6.90m   13.83m
     'feasibility_pump':      8169 [351.50us, 794.56ms]  24.04ms  77.74ms    3.27m      8164 [  1.61ms, 795.62ms]  17.63ms  96.13ms    2.40m
                   'fj':       589 [ 47.19ms, 134.45ms]  77.96ms  18.92ms   45.92s       589 [100.11ms, 109.05ms] 102.56ms   3.28ms    1.01m
                   'fj':       590 [ 46.97ms, 140.14ms]  74.49ms  18.64ms   43.95s       590 [100.10ms, 108.98ms] 102.11ms   3.10ms    1.00m
            'fs_random':         1 [  54.32s,   54.32s]   54.32s   0.00ns   54.32s         2 [   1.11s,   11.91s]    6.51s    5.40s   13.02s
      'fs_random_no_lp':         1 [  54.32s,   54.32s]   54.32s   0.00ns   54.32s         2 [   1.11s,   50.50s]   25.81s   24.70s   51.62s
        'graph_arc_lns':      1806 [ 71.73ms,    1.11s] 452.63ms 149.60ms   13.62m      1806 [ 10.00ns, 100.46ms]  57.63ms  45.42ms    1.73m
        'graph_cst_lns':      1538 [ 96.40ms,    1.77s] 532.58ms 292.23ms   13.65m      1538 [ 10.00ns, 100.41ms]  57.41ms  45.33ms    1.47m
        'graph_dec_lns':      1605 [114.81ms,    1.99s] 509.11ms 347.73ms   13.62m      1605 [ 10.00ns, 100.54ms]  55.24ms  46.94ms    1.48m
        'graph_var_lns':      2672 [ 66.52ms, 831.15ms] 305.73ms 115.76ms   13.62m      2672 [ 10.00ns, 100.54ms]  59.03ms  44.38ms    2.63m
                   'ls':      8169 [ 17.52ms, 120.16ms]  64.62ms  13.50ms    8.80m      8169 [864.46us, 101.40ms]  99.43ms   9.26ms   13.54m
               'ls_lin':      8169 [ 15.94ms, 120.29ms]  65.16ms  13.32ms    8.87m      8169 [561.55us, 101.11ms]  99.84ms   6.83ms   13.59m
               'max_lp':         1 [  29.96m,   29.96m]   29.96m   0.00ns   29.96m         2 [   4.26s,   43.54m]   21.81m   21.74m   43.62m
                'no_lp':         1 [  29.95m,   29.95m]   29.95m   0.00ns   29.95m         2 [   1.11s,    1.05h]   31.57m   31.56m    1.05h
         'pseudo_costs':         1 [  29.95m,   29.95m]   29.95m   0.00ns   29.95m         2 [   1.12s,   25.83m]   12.92m   12.90m   25.85m
        'quick_restart':         1 [  29.95m,   29.95m]   29.95m   0.00ns   29.95m         2 [   1.11s,   15.27m]    7.64m    7.62m   15.29m
  'quick_restart_no_lp':         1 [  29.95m,   29.95m]   29.95m   0.00ns   29.95m         2 [   1.11s,   13.59m]    6.80m    6.79m   13.61m
        'reduced_costs':         1 [  29.95m,   29.95m]   29.95m   0.00ns   29.95m         2 [   1.12s,   21.69m]   10.86m   10.84m   21.71m
            'rins/rens':      4250 [  6.55ms, 705.82ms] 192.59ms 240.38ms   13.64m      2726 [ 10.00ns, 100.08ms]  51.29ms  49.98ms    2.33m
          'rnd_cst_lns':      1432 [ 79.28ms,    1.65s] 571.70ms 302.71ms   13.64m      1428 [ 10.00ns, 100.89ms]  56.15ms  46.22ms    1.34m
          'rnd_var_lns':      1703 [ 65.56ms,    1.98s] 480.08ms 349.96ms   13.63m      1703 [ 10.00ns, 100.80ms]  55.35ms  46.66ms    1.57m

Search stats               Bools   Conflicts     Branches  Restarts  BacktrackToRoot   Backtrack     BoolPropag  IntegerPropag
                 'core':  47'848   3'921'090  160'956'687     6'140          243'895   4'247'619  2'517'558'861    726'176'504
           'default_lp':  47'668      12'360   28'631'942        75        3'856'764   6'170'788    536'186'290    285'296'070
            'fs_random':  47'668         265      822'396         2          135'744     176'802     14'515'792      7'192'135
      'fs_random_no_lp':  47'668     132'606    9'725'211       265          335'563     629'441    106'172'926     56'999'942
               'max_lp':  47'668         138      830'299         1          207'646     286'066     24'950'481     27'997'694
                'no_lp':  47'668  15'967'919   68'401'173     1'307        2'194'028  19'031'008  3'117'985'213    415'829'933
         'pseudo_costs':  47'668         728    2'542'378         6          422'449     630'259     54'049'676     62'394'873
        'quick_restart':  47'668       4'694   41'630'750       141        5'903'535   9'476'777    811'360'376    432'214'193
  'quick_restart_no_lp':  47'668     559'498  249'260'922    52'956        3'165'036   5'532'183  1'885'272'533  1'444'637'844
        'reduced_costs':  47'668       2'375    5'653'696        29          682'062   1'062'088     90'686'987    108'371'071

SAT formula               Fixed  Equiv   Total  VarLeft  BinaryClauses  PermanentClauses  TemporaryClauses
                 'core':     28      0  47'848   47'820        323'582            47'414            10'435
           'default_lp':     28      0  47'668   47'640        320'942            26'521             9'398
            'fs_random':     26      0  47'668   47'642        283'078            14'492               147
      'fs_random_no_lp':     28      0  47'668   47'640        314'274            19'931            12'110
               'max_lp':     28      0  47'668   47'640        318'958            32'823                43
                'no_lp':     28      0  47'668   47'640        317'158            24'172            10'272
         'pseudo_costs':     28      0  47'668   47'640        320'672            37'466               380
        'quick_restart':     28      0  47'668   47'640        320'938            24'880             2'542
  'quick_restart_no_lp':     28      0  47'668   47'640        320'958            33'014            13'615
        'reduced_costs':     28      0  47'668   47'640        320'710            36'128             1'654

SAT stats                 ClassicMinim   LitRemoved  LitRemovedBinary     LitLearned   LitForgotten   Subsumed
                 'core':     2'384'742  120'534'110       173'337'445  3'235'953'103  2'692'615'962    424'579
           'default_lp':         2'377       28'320           361'357      2'038'012              0      1'220
            'fs_random':            28          174             3'961          9'680              0         29
      'fs_random_no_lp':        59'854      408'823         1'173'275     41'631'383     25'832'977     28'324
               'max_lp':            16           22             1'909          4'106              0         46
                'no_lp':    12'460'120  113'809'345        81'591'198  5'177'547'150  3'440'600'354  4'622'701
         'pseudo_costs':            51          123             7'349         35'909              0        137
        'quick_restart':           346        9'185            47'374        441'572              0      1'020
  'quick_restart_no_lp':       225'835    8'228'398         9'733'722    224'396'396    199'521'362     31'692
        'reduced_costs':           312        1'086            16'551        319'988              0        413

Vivification                Clauses   Decisions  LitTrue  Subsumed  LitRemoved  DecisionReused  Conflicts
                 'core':     60'672     626'493        0     6'345     147'720          33'459         68
           'default_lp':  1'784'535  21'991'963        1    22'605     153'158       2'407'655      1'212
            'fs_random':     29'100     638'625        1       246       3'576          51'185        128
      'fs_random_no_lp':    123'330   2'243'942        1     2'785      37'281         230'171        304
               'max_lp':     65'072     608'281        0     6'704      61'516          25'690         55
                'no_lp':    996'966  14'013'738        1    16'224     139'791       1'538'616      1'086
         'pseudo_costs':    167'108   2'046'063        0     9'442      83'101         193'546        346
        'quick_restart':  2'740'891  34'047'499        0    23'972     156'782       3'835'682      1'544
  'quick_restart_no_lp':  1'433'737  17'782'677        1    42'944     442'965       1'563'120      1'093
        'reduced_costs':    280'076   3'808'280        1    11'136      93'210         398'495        478

Clause deletion           at_true  l_and_not(l)  to_binary  sub_conflict  sub_extra  sub_decisions  sub_eager  sub_vivify  sub_probing  sub_inpro  blocked  eliminated   forgotten    promoted   conflicts
                 'core':        1             0         26       404'894     31'197              1     19'685       6'345          438      4'176        0           0   3'437'500  10'159'090   3'921'090
           'default_lp':        2             0          1         1'192         86             31         28      22'605        2'272         85        0           0           0      15'730      12'360
            'fs_random':        1             0          0            28          0              6          1         246            0          0        0           0           0         332         265
      'fs_random_no_lp':        1             0          2        27'489      2'863             16        835       2'785           66          7        0           0      81'970     355'166     132'606
               'max_lp':        0             0          0            46          0              1          0       6'704        1'691        156        0           0           0          54         138
                'no_lp':        5             0          8     4'559'997    448'174            105     62'704      16'224          289        200        0           0  10'873'216  42'478'149  15'967'919
         'pseudo_costs':        3             0          0           135          1              8          2       9'442        2'290        180        0           0           0         943         728
        'quick_restart':        3             0          0         1'005          7             32         15      23'972        2'188         62        0           0           0       4'122       4'694
  'quick_restart_no_lp':        3             0         66        29'016      3'789             56      2'676      42'944          471        497        0           0     454'327     944'943     559'498
        'reduced_costs':        2             0          1           394         53              6         19      11'136        2'250        175        0           0           0       4'598       2'375

Lp stats            Component  Iterations  AddedCuts  OPTIMAL  DUAL_F.  DUAL_U.
     'default_lp':          1   1'961'620      8'688  210'468      234       34
      'fs_random':          1      32'241        280   10'270        3       17
         'max_lp':          1     483'274          0        0      480        0
   'pseudo_costs':          1   1'361'510      2'280      175    3'204       31
  'quick_restart':          1   1'252'994     27'165  137'979       80      171
  'reduced_costs':          1   1'120'611     26'735      243    9'542      114

Lp dimension               Final dimension of first component
     'default_lp':    1071 rows, 14091 columns, 18507 entries
      'fs_random':    1224 rows, 14091 columns, 25128 entries
         'max_lp':  19572 rows, 47668 columns, 474588 entries
   'pseudo_costs':   6740 rows, 47668 columns, 133243 entries
  'quick_restart':    1661 rows, 14091 columns, 29026 entries
  'reduced_costs':   8339 rows, 47668 columns, 123682 entries

Lp debug            CutPropag  CutEqPropag   Adjust  Overflow      Bad  BadScaling
     'default_lp':          0            3  203'081         0  201'739           0
      'fs_random':          0            0   10'264         0    9'413           0
         'max_lp':          0            0      480         0        0           0
   'pseudo_costs':          0            0    3'398         0   12'354           0
  'quick_restart':          0           13  137'400         0  718'569           0
  'reduced_costs':          0            0    9'837         0  411'055           0

Lp pool             Constraints  Updates  Simplif  Merged  Shortened  Split  Strengthened       Cuts/Call
     'default_lp':       19'678      273      132       0        181     30           133    8'688/14'370
      'fs_random':       11'270        2       89       0        138      0             0         280/582
         'max_lp':       19'573        0        0   1'338         65      0             0             0/0
   'pseudo_costs':       21'853       17      160   1'338        218      0             0     2'280/9'655
  'quick_restart':       20'155    1'948      135       0        184    161             0   27'165/35'704
  'reduced_costs':       29'308      189      207   1'338        222     83            79  26'735/183'407

Lp Cut           fs_random  quick_restart  default_lp  reduced_costs  pseudo_costs
         CG_FF:         26            349         500            283            31
          CG_K:          5             39          47             43             -
         CG_KL:          8             62         212              5             -
          CG_R:         24            545         445             97             2
        Clique:          -              -           -            262            32
      MIR_1_FF:          -              1           2              7             -
       MIR_1_K:          -              -           -              3             -
      MIR_1_KL:          -              -           -              6             -
       MIR_1_R:          -              1           1             14             -
     MIR_1_RLT:          -              -           -          3'110           755
      MIR_2_FF:          -              8           1          1'696           340
       MIR_2_K:          -              -           -             13             -
      MIR_2_KL:          -              -           -             30             -
       MIR_2_R:          -              2          32             40             -
      MIR_3_FF:          5             59          52          3'509           262
       MIR_3_K:          -              -           2             18             2
      MIR_3_KL:          -              6           3            120             4
       MIR_3_R:          -              1          14            250             7
      MIR_4_FF:          2             12          10          2'054            94
       MIR_4_K:          -              -           1             24             1
      MIR_4_KL:          1              5           6            376            19
       MIR_4_R:          -              1          16             89             2
      MIR_5_FF:          3             72         111          1'472            59
       MIR_5_K:          -              -           -             18             1
      MIR_5_KL:          -             11          38            145             4
       MIR_5_R:          -              -          10             54             -
      MIR_6_FF:          2             27          43            776            42
       MIR_6_K:          -              -           -             15             -
      MIR_6_KL:          1             17          15            151             8
       MIR_6_R:          -              -           5             43             1
  ZERO_HALF_FF:        169          5'191       2'986          9'230           543
   ZERO_HALF_K:          -              2           -             47             -
  ZERO_HALF_KL:          -             78          70            640            19
   ZERO_HALF_R:         34         20'676       4'066          2'095            52

LNS stats           Improv/Calls  Closed  Difficulty  TimeLimit
  'graph_arc_lns':      208/1806     50%    5.58e-01       0.10
  'graph_cst_lns':      179/1538     50%    6.42e-01       0.10
  'graph_dec_lns':      224/1605     50%    6.55e-01       0.10
  'graph_var_lns':      311/2672     50%    4.73e-01       0.10
      'rins/rens':     1482/2726     49%    4.85e-03       0.10
    'rnd_cst_lns':      195/1428     50%    6.49e-01       0.10
    'rnd_var_lns':      241/1703     50%    6.44e-01       0.10

LS stats                                    Batches  Restarts/Perturbs   LinMoves   GenMoves  CompoundMoves  Bactracks  WeightUpdates  ScoreComputed
                             'fj_restart':       62                 28  1'354'769          0              0          0         27'199      2'708'740
                    'fj_restart_compound':      163                 23          0  1'359'122        341'499    508'658            168     56'445'006
                'fj_restart_compound_obj':       37                 18          0    254'321        125'010     64'626             20     12'737'164
            'fj_restart_compound_perturb':       31                 13          0    214'859        103'678     55'497             22     11'048'357
        'fj_restart_compound_perturb_obj':       70                 30          0    491'540        225'595    132'893             42     24'923'830
                       'fj_restart_decay':       97                 29  2'335'561          0              0          0          5'457      4'650'250
              'fj_restart_decay_compound':       37                 22          0    257'520        140'698     58'348             14     12'607'402
          'fj_restart_decay_compound_obj':       83                 19          0    716'614        237'375    239'531             45     28'660'161
      'fj_restart_decay_compound_perturb':       27                 15          0    193'122         98'498     47'263             10      9'545'650
  'fj_restart_decay_compound_perturb_obj':       96                 24          0    737'805        281'798    227'876             56     34'060'073
                   'fj_restart_decay_obj':      168                 26  4'212'526          0              0          0          9'453      8'175'323
               'fj_restart_decay_perturb':       64                 24  1'506'717          0              0          0          3'686      3'020'160
           'fj_restart_decay_perturb_obj':       67                 22  1'647'690          0              0          0          3'821      3'224'843
                         'fj_restart_obj':       58                 20  1'293'458          0              0          0         28'386      2'527'233
                     'fj_restart_perturb':       28                 19    603'600          0              0          0          8'572      1'256'019
                 'fj_restart_perturb_obj':       91                 21  2'106'068          0              0          0         67'709      3'332'137
                         'ls_lin_restart':      980                569  1'950'096          0              0          0         81'733     33'800'133
                'ls_lin_restart_compound':    1'055                561          0    547'627         54'881    245'510          3'266     42'241'542
        'ls_lin_restart_compound_perturb':    1'107                565          0    567'250         48'448    258'487          3'500     45'221'546
                   'ls_lin_restart_decay':    1'057                578  1'474'590          0              0          0         18'120     35'857'751
          'ls_lin_restart_decay_compound':    1'024                565          0    543'795         60'679    240'626          3'028     41'037'081
  'ls_lin_restart_decay_compound_perturb':    1'000                588          0    516'481         45'139    234'702          3'029     40'037'683
           'ls_lin_restart_decay_perturb':      947                580  1'354'711          0              0          0         17'730     32'689'967
                 'ls_lin_restart_perturb':      999                544  1'960'363          0              0          0         78'857     34'138'830
                             'ls_restart':      955                543  1'853'176          0              0          0         76'336     32'397'000
                    'ls_restart_compound':    1'012                606          0    519'718         47'858    234'980          3'282     41'220'583
            'ls_restart_compound_perturb':      944                529          0    482'611         36'022    222'421          3'106     38'813'542
                       'ls_restart_decay':    1'064                554  1'444'479          0              0          0         17'217     35'410'247
              'ls_restart_decay_compound':    1'013                572          0    525'666         41'427    241'148          2'912     39'650'012
      'ls_restart_decay_compound_perturb':    1'065                586          0    548'455         48'519    249'020          3'031     42'240'367
               'ls_restart_decay_perturb':    1'016                566  1'394'122          0              0          0         17'557     34'398'630
                     'ls_restart_perturb':    1'100                602  2'090'920          0              0          0         84'031     36'499'346

Solutions (304)                             Num       Rank
                          'graph_arc_lns':   60   [10,299]
                          'graph_cst_lns':   10    [7,297]
                          'graph_dec_lns':   92   [11,303]
                          'graph_var_lns':  150   [12,304]
                         'ls_lin_restart':    4  [255,291]
                'ls_lin_restart_compound':    8   [36,273]
        'ls_lin_restart_compound_perturb':   10   [70,188]
                   'ls_lin_restart_decay':   10   [90,252]
          'ls_lin_restart_decay_compound':    2  [102,103]
  'ls_lin_restart_decay_compound_perturb':    6   [54,233]
           'ls_lin_restart_decay_perturb':   16   [50,241]
                 'ls_lin_restart_perturb':    4   [80,194]
                             'ls_restart':   22   [24,302]
                    'ls_restart_compound':   20   [32,296]
            'ls_restart_compound_perturb':   20   [40,262]
                       'ls_restart_decay':   16    [8,275]
              'ls_restart_decay_compound':   14   [44,239]
      'ls_restart_decay_compound_perturb':   14   [20,294]
               'ls_restart_decay_perturb':   16   [29,300]
                     'ls_restart_perturb':   24    [9,264]
                                  'no_lp':   10      [0,7]
                            'rins_lp_lns':   12  [118,246]
                            'rnd_cst_lns':    4    [13,86]
                            'rnd_var_lns':   64    [3,301]

Objective bounds     Num
      'default_lp':    6
       'fs_random':    4
  'initial_domain':    1
    'pseudo_costs':    1
   'quick_restart':    4
   'reduced_costs':   63

Solution repositories     Added  Queried  Synchro
    'alternative_path':     817    7'994      813
      'best_solutions':   4'376   18'250    2'742
   'fj solution hints':     345        0      345
        'lp solutions':  10'890    2'309    1'779
                'pump':   7'841    1'941

Improving bounds shared    Num  Sym
             'fs_random':    2    0
       'fs_random_no_lp':    6    0
                 'no_lp':    6    0
   'quick_restart_no_lp':   14    0

Clauses shared            #Exported  #Imported  #BinaryRead  #BinaryTotal
                 'core':      5'135     29'775       30'610        30'989
           'default_lp':      1'488     35'504       30'980        30'989
            'fs_random':      1'506         90        6'093        30'989
      'fs_random_no_lp':     11'768      2'014       25'421        30'989
               'max_lp':          9     26'755       29'980        30'989
                'no_lp':     16'470     14'844       29'078        30'989
         'pseudo_costs':         85     34'754       30'844        30'989
        'quick_restart':      1'083     35'691       30'979        30'989
  'quick_restart_no_lp':     36'161      9'586       30'989        30'989
        'reduced_costs':        812     34'947       30'862        30'989

LRAT_status: NA
CpSolverResponse summary:
status: FEASIBLE
objective: -145250
best_bound: -2200
integers: 19016
booleans: 47668
conflicts: 132606
branches: 9725211
propagations: 106172926
integer_propagations: 56999942
restarts: 265
lp_iterations: 0
walltime: 1800.85
usertime: 1800.85
deterministic_time: 17495.1
gap_integral: 208585
solution_fingerprint: 0x6e137511e3f0e118

Post-processing travel distance (initial league miles: 1,302,977)...

Exported master schedule to 'data\mlb_schedule.csv' and 30 team schedules to 'data/mlb_schedule_<TEAM>.csv'.
Cached 30/30 team PNG logos in 'data\logos/' for PDF rendering.
Generated 30 1-page team schedule PDFs in 'data/mlb_schedule_<TEAM>_<SEASON>.pdf'.

========================================================================
AUTOMATED SCHEDULE VALIDATION CHECKS
========================================================================
[PASS] Total regular season games == 2,430 (780 total series)
[PASS] Zero doubleheaders scheduled (no team plays twice on the same date)
[PASS] All regular series after Opening Weekend have strictly contiguous calendar dates
[PASS] All inter-series gaps outside All-Star Break are <= 2 off-days (2-off-day gaps league-wide: 0)
[PASS] All teams play < 17 consecutive days before an off-day (Max streak: 16d | Streaks 10-16d: 137 | Excess days >9: 405)
[PASS] All divisional pairs play <= 2 series in any 31-day span and never go > 3 months between series
[PASS] All 30 teams have exactly 162 games (81 Home / 81 Away)
[PASS] All 30 teams play on Memorial Day, July 4th, and Labor Day
[PASS] Core All-Star Break (2027-07-12 to 2027-07-14) has 0 games (Thursday 2027-07-15 early restart games: 8)
[PASS] All matchup quotas met (52 In-Div; 62 Same-League [6x8 + 7x2]; 48 Interleague [6x1 + 3x14])
[PASS] All road trips and homestands are <= 3 series (soft 1-series road trips: 131)

========================================================================
EXECUTION SUMMARY & OPTIMIZATION METRICS
========================================================================
Target Season Year          : 2027
Solver Status               : FEASIBLE
Phase 2 Solve Runtime       : 1802.51 seconds
Total Script Wall Runtime   : 1824.69 seconds
CP-SAT Objective Value      : -145250
Early/Late Divisional Series: 131 series
Missed April Div Pairs      : 1 / 60 (['BAL-NYY'])
Missed Sept Div Pairs       : 3 / 60 (['CWS-DET', 'LAA-SEA', 'PIT-STL'])
ASG Thursday Early Games    : 8 games
Excess Playing Days (>9d)   : 438 penalty days
Isolated 1-Series Homestands: 122 league-wide
Isolated 1-Series Road Trips: 131 league-wide
Total League Travel Distance: 1,302,977 miles

Top 3 Teams by Travel Distance:
  - LAA: 65,162 miles
  - SF: 62,645 miles
  - ATH: 57,668 miles

Bottom 3 Teams by Travel Distance:
  - BAL: 33,838 miles
  - CLE: 28,959 miles
  - CWS: 27,983 miles