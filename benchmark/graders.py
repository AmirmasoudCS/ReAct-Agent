import re
import datetime as dt

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def _numbers(text):
    out = []
    for x in re.findall(r"-?\d[\d,]*\.?\d*", text):
        try:
            out.append(float(x.replace(",", "")))
        except ValueError:
            pass
    return out


def _has_number(answer, target, tol=0.01):
    return any(abs(n - target) <= tol for n in _numbers(answer))


def _norm(text):
    t = text.lower()
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
    t = t.replace(",", " ").replace(" of ", " ")
    return re.sub(r"\s+", " ", t)


def _date_forms(d):
    full, abbr = MONTHS[d.month - 1], MONTHS[d.month - 1][:3]
    day = str(d.day)
    forms = {d.isoformat(), f"{d.day:02d}.{d.month:02d}.{d.year}", f"{day}.{d.month}.{d.year}",
             f"{d.month}/{day}/{d.year}", f"{d.month:02d}/{d.day:02d}/{d.year}",
             f"{d.day:02d}/{d.month:02d}/{d.year}"}
    for m in (full, abbr, abbr + "."):
        forms |= {f"{m} {day} {d.year}", f"{day} {m} {d.year}",
                  f"{m} {d.day:02d} {d.year}", f"{d.day:02d} {m} {d.year}"}
    return {f.lower() for f in forms}


def _next_occurrence(today, month, day):
    d = dt.date(today.year, month, day)
    return d if d >= today else dt.date(today.year + 1, month, day)


def dynamic_check(spec, answer, today=None):
    """Expected value is computed at grading time from `today`.
    NOTE: grade soon after running, or pass the run date as `today`."""
    today = today or dt.date.today()
    fn, a = spec["fn"], answer.lower()
    if fn == "weekday_plus":
        return (today + dt.timedelta(days=spec["days"])).strftime("%A").lower() in a
    if fn == "current_weekday":
        return today.strftime("%A").lower() in a
    if fn == "current_year":
        return str(today.year) in a
    if fn == "current_month":
        return MONTHS[today.month - 1] in a
    if fn == "date_plus":
        d = today + dt.timedelta(days=spec["days"])
        n = _norm(answer)
        return any(f in n for f in _date_forms(d))
    if fn == "days_until":
        n = (_next_occurrence(today, spec["month"], spec["day"]) - today).days
        return _has_number(answer, n * spec.get("factor", 1))
    if fn == "day_of_year":
        return _has_number(answer, today.timetuple().tm_yday)
    if fn == "days_since":
        return _has_number(answer, (today - dt.date(spec["year"], spec["month"], spec["day"])).days)
    if fn == "year_diff":
        return _has_number(answer, today.year - spec["base"])
    if fn == "full_years_since":
        y, m, d = spec["year"], spec["month"], spec["day"]
        yrs = today.year - y - ((today.month, today.day) < (m, d))
        return _has_number(answer, yrs)
    raise ValueError(fn)


def grade(task, answer, today=None):
    """True/False, or None if it needs human grading."""
    g, exp = task["grader"], task.get("expected")
    if g == "human":
        return None
    if not answer:
        return False
    if g == "numeric":
        return _has_number(answer, exp, task.get("tol", 1e-6))
    if g == "contains":
        return all(e.lower() in answer.lower() for e in exp)
    if g == "regex":
        return re.search(exp, answer) is not None
    if g == "dynamic":
        return dynamic_check(exp, answer, today)
    raise ValueError(g)