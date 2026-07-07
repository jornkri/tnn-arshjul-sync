from datetime import date
from tnn_sync.labels import format_date_label, WEEKDAY_NB

def test_single_day():
    assert format_date_label(date(2026, 6, 7), None) == "7. juni"

def test_single_day_when_end_same_date():
    assert format_date_label(date(2026, 6, 7), date(2026, 6, 7)) == "7. juni"

def test_range_same_month():
    assert format_date_label(date(2026, 7, 1), date(2026, 7, 4)) == "1.–4. juli"

def test_range_across_months():
    assert format_date_label(date(2026, 7, 27), date(2026, 8, 2)) == "27. juli – 2. august"

def test_weekday_names():
    assert WEEKDAY_NB[2] == "Tirsdag" and WEEKDAY_NB[6] == "Lørdag"
