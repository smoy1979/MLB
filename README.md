C:\Users\smoy1\AppData\Local\Programs\Python\Python311\python.exe -m venv research311
research311\Scripts\activate

pip install -r requirements.txt
c:\projects\MLB\research311\Scripts\python.exe -m pip install -r requirements.txt



c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py'

###
# generate constraint violation report for past years

c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py' '--evaluate-2026'
c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py' '--evaluate-year=2025'

c:; cd 'c:\projects\MLB'; & 'c:\projects\MLB\research311\Scripts\python.exe' 'C:\projects\MLB\mlb_scheduler.py' '--evaluate-csv=data/mlb_schedule.csv'

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
