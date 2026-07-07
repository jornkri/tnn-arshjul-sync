from datetime import date

MONTH_NB = {1: "januar", 2: "februar", 3: "mars", 4: "april", 5: "mai", 6: "juni",
            7: "juli", 8: "august", 9: "september", 10: "oktober", 11: "november", 12: "desember"}
WEEKDAY_NB = {1: "Mandag", 2: "Tirsdag", 3: "Onsdag", 4: "Torsdag",
              5: "Fredag", 6: "Lørdag", 7: "Søndag"}

def format_date_label(start: date, end: date | None) -> str:
    if end is None or end == start:
        return f"{start.day}. {MONTH_NB[start.month]}"
    if start.month == end.month:
        return f"{start.day}.–{end.day}. {MONTH_NB[end.month]}"
    return f"{start.day}. {MONTH_NB[start.month]} – {end.day}. {MONTH_NB[end.month]}"
