from datetime import date, timedelta
from textwrap import dedent
from typing import TYPE_CHECKING, Final

import mip
from mip.constants import OptimizationStatus
if TYPE_CHECKING:
    from mip.entities import Var

m = mip.Model()
m.verbose = 1

"""
IOVIAGGIO mensile  116.00€
IOVIAGGIO 7 giorni  46.50€
IOVIAGGIO 3 giorni  35.00€
IOVIAGGIO 2 giorni  29.00€
IOVIAGGIO 1 giorno  17.50€
"""
day_cost: Final[float] = 17.5
two_days_cost: Final[float] = 29.0
three_days_cost: Final[float] = 35.0
week_cost: Final[float] = 46.5
month_cost: Final[float] = 116.0

def is_last_day_of_the_month(month: int, day: date) -> bool:
    """True if the given day is the last day of the given month."""
    return month == day.month and (day + timedelta(1)).day == 1

    delta = j - i
    free_inside_interval = [i+timedelta(d) in free_days for d in range(delta.days)]
    if all(free_inside_interval):
        return 0
    start = i
    for d in range(delta.days):
        if i+timedelta(d) not in free_days:
            start = i+timedelta(d)
            break
    delta = j - start
    match (delta.days):
        case 1:
            return day_cost
        case 2:
            return two_days_cost
        case 3:
            return three_days_cost
        case 7:
            return week_cost
        case _:
            if j == end_date and delta.days < 7:
                return week_cost
            return None

def parse_date(date_: str) -> date:
    date_split = date_.split()
    day, month, year = map(lambda x: int(x), date_split)
    return date(year if year > 2000 else year + 2000, month, day)

def main():
    free_days: list[date] = []

    start_date: date = parse_date(input("inserire giorno, mese e anno di partenza: "))
    end_date: date = parse_date(input("inserire giorno, mese e anno di arrivo (escluso): "))

    #
    while True:
        selection = input(dedent("""\
            selezionare modalità di inserimento giorni liberi:
            1: giorni singoli
            2: intervalli
            q: procedi con il calcolo
            """))
        match selection:
            case "1":
                free_day = input("inserire giorno mese (i weekend sono già esclusi):\n")
                new_date = parse_date(f"{free_day} {start_date.year}")
                free_days.append(new_date)
            case "2":
                start = input("inserire giorno mese di partenza:\n")
                start_d = parse_date(f"{start} {start_date.year}")
                end = input("inserire giorno mese di arrivo (escluso):\n")
                end_d = parse_date(f"{end} {start_date.year}")
                while start_d != end_d:
                    free_days.append(start_d)
                    start_d += timedelta(1)
            case "q":
                break
            case _:
                print("selezione non valida")

    dates: list[date] = [start_date + timedelta(i) for i in range((end_date - start_date).days + 1)]

    E: dict[tuple[date,date], float] = {}
    for i in range(len(dates)-1):
        for j in range(i+1, len(dates)):
            interval_cost = cost(dates[i], dates[j], end_date, free_days)
            if interval_cost is None:
                continue
            E[(dates[i], dates[j])] = interval_cost

    f: dict[tuple[date,date], Var] = {(i, j): m.add_var() for (i, j) in E.keys()} # pyright: ignore[reportUnknownMemberType]
    b = {i: 0 for i in dates}
    b[start_date] = 1
    b[end_date] = -1

    # Write flow conservation constraint
    for i in dates:
        m.add_constr(                                                # pyright: ignore[reportUnknownMemberType]
              mip.xsum(f[i, j] for j in dates if (i, j) in E.keys()) # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            - mip.xsum(f[j, i] for j in dates if (j, i) in E.keys()) # pyright: ignore[reportUnknownMemberType]
            == b[i]
        )
    m.objective = mip.minimize(mip.xsum(E[i, j] * f[i, j]  for (i, j) in E.keys())) # pyright: ignore[reportOperatorIssue, reportUnknownMemberType, reportUnknownArgumentType]
    status = m.optimize()
    if status == OptimizationStatus.INFEASIBLE:
        print("Errore nel trovare una soluzione, skill issue del dev.")
        quit(1)
    print(f"Da {start_date} a {end_date}")
    print(f"Il costo totale è di {m.objective_value}€.")
    for (i, j), k in f.items():
        if k.x > 0.5:   # pyright: ignore[reportOperatorIssue]
            if E[i, j] > 0:
                if (j - i).days > 7:
                    title = "IOVIAGGIO mensile"
                else:
                    title = f"IOVIAGGIO da {(j - i).days} giorni"
                print(f'{i}->{j - timedelta(1)} {title}')

if __name__ == "__main__":
    main()
"""
devo coprire una settimana lavorativa e due giorni
"""
