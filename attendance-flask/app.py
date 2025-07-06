from flask import Flask, render_template, request
import math
from datetime import date, timedelta
from collections import defaultdict, Counter

app = Flask(__name__)

START_DATE = date(2025, 7, 14)
END_DATE = date(2025, 10, 30)
TODAY = date.today()

WEEKLY_TIMETABLE = {
    "Monday": ["Math", "Physics"],
    "Tuesday": ["English", "English"],
    "Wednesday": ["Math", "Math", "CS"],
    "Thursday": ["Physics"],
    "Friday": ["Math", "CS"],
    "Saturday": []
}

HOLIDAY_RANGES = [
    (date(2025, 8, 15), date(2025, 8, 16)),
    (date(2025, 8, 20), date(2025, 8, 22)),
    (date(2025, 8, 27), date(2025, 8, 27)),
    (date(2025, 9, 4), date(2025, 9, 10)),
    (date(2025, 9, 29), date(2025, 9, 30)),
    (date(2025, 10, 1), date(2025, 10, 2)),
    (date(2025, 10, 16), date(2025, 10, 20)),
]

def expand_holidays(ranges):
    holidays = set()
    for start, end in ranges:
        for offset in range((end - start).days + 1):
            holidays.add(start + timedelta(days=offset))
    return holidays

def get_working_days(start, end, holidays):
    return [
        d for d in (start + timedelta(days=i) for i in range((end - start).days + 1))
        if d.weekday() != 6 and d not in holidays
    ]

def build_class_schedule(working_days, timetable):
    weekday_map = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    all_classes = []
    for day in working_days:
        weekday_name = weekday_map[day.weekday()]
        subjects = timetable.get(weekday_name, [])
        all_classes.append((day, subjects))
    return all_classes

def count_subjects_per_period(class_schedule):
    past_counts = Counter()
    future_counts = Counter()
    future_dates = defaultdict(list)
    for day, subjects in class_schedule:
        for subj in subjects:
            if day <= TODAY:
                past_counts[subj] += 1
            else:
                future_counts[subj] += 1
                future_dates[subj].append(day)
    return past_counts, future_counts, future_dates

def max_bunks(attended, held, future):
    total = held + future
    return max(0, math.floor(attended + future - 0.75 * total))

def find_earliest_75(attended, held, future_dates):
    total = held
    present = attended
    for i, day in enumerate(future_dates):
        present += 1
        total += 1
        if (present / total) * 100 >= 75:
            return i + 1, day
    return None, None

@app.route("/", methods=["GET", "POST"])
def index():
    holidays = expand_holidays(HOLIDAY_RANGES)
    working_days = get_working_days(START_DATE, END_DATE, holidays)
    class_schedule = build_class_schedule(working_days, WEEKLY_TIMETABLE)
    past_counts, future_counts, future_dates = count_subjects_per_period(class_schedule)
    subjects = sorted(set(past_counts) | set(future_counts))

    report = None

    if request.method == "POST":
        attendance_data = {}
        for subject in subjects:
            input_type = request.form.get(f"{subject}_type")
            if input_type == "percent":
                percent = float(request.form.get(f"{subject}_percent", 0))
                attended = math.floor((percent / 100) * past_counts[subject])
            else:
                attended = int(request.form.get(f"{subject}_attended", 0))
            attendance_data[subject] = attended

        report = []
        for subject in subjects:
            T = past_counts[subject]
            F = future_counts[subject]
            A = attendance_data[subject]
            current_percent = (A / T * 100) if T else 0
            required_total = 0.75 * (T + F)
            needed = max(0, math.ceil(required_total - A))
            can_reach = needed <= F

            data = {
                "subject": subject,
                "held": T,
                "attended": A,
                "percent": round(current_percent, 2),
                "future": F,
                "needed": needed,
                "can_reach": can_reach,
            }

            if current_percent >= 75:
                data["bunks"] = max_bunks(A, T, F)
            elif can_reach:
                classes_needed, by_date = find_earliest_75(A, T, future_dates[subject])
                data["reach_date"] = by_date.strftime("%A, %d %B %Y") if by_date else None
                data["reach_count"] = classes_needed
            else:
                data["unreachable"] = True

            report.append(data)

    return render_template("index.html", subjects=subjects, report=report)

if __name__ == "__main__":
    app.run(debug=True)
