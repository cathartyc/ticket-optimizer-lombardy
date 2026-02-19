from __future__ import annotations
from datetime import date, timedelta
import signal
from textwrap import dedent
from typing import TYPE_CHECKING

import mip
from mip.constants import OptimizationStatus

if TYPE_CHECKING:
    from typing import Final
    from mip.entities import Var
    from types import FrameType

def exit_gracefully(_sig_num: int, _stack_frame: FrameType | None):
    print('\nClosing...')
    exit(0)

# IVOL daily ticket
IVOL_DAILY_COST: Final[float] = 17.5
# IVOL 2-days ticket
IVOL_TWO_DAYS_COST: Final[float] = 29.0
# IVOL 3->days ticket
IVOL_THREE_DAYS_COST: Final[float] = 35.0
# IVOL 7-days ticket
IVOL_SEVEN_DAYS_COST: Final[float] = 46.5
# IVOL monthly subscription
IVOL_MONTHLY_COST: Final[float] = 116.0

def is_last_day_of_the_month(month: int, day: date) -> bool:
    """True if the given day is the last day of the given month."""
    return month == day.month and (day + timedelta(1)).day == 1

def cost(i: date, j: date, free_days: set[date]) -> float | None:
    delta = j - i
    j -= timedelta(1)
    if i in free_days and j in free_days:
        return None
    free_inside_interval = [i+timedelta(d) in free_days for d in range(delta.days)]
    if all(free_inside_interval):
        return 0
    start = i
    for d in range(delta.days):
        if i+timedelta(d) not in free_days:
            delta = j - start + timedelta(1)
            start = i+timedelta(d)
            break
    match (delta.days):
        case 1:
            return DAY_COST
        case 2:
            return TWO_DAYS_COST
        case 3:
            return THREE_DAYS_COST
        case 7:
            return WEEK_COST
        case _:
            if delta.days < 7:
                return WEEK_COST
            if is_last_day_of_the_month(i.month, j):
                return MONTH_COST
            return None

def read_date(prompt: str) -> date:
    while True:
        date_split = input(prompt).split()
        try:
            day, month, year = map(lambda x: int(x), date_split)
            return date(year if year > 2000 else year + 2000, month, day)
        except ValueError:
            print(f'invalid date')

def main():
    _ = signal.signal(signal.SIGINT, exit_gracefully)

    free_days: set[date] = set()

    start_date: date = read_date("insert the first day you wanna travel (day month year): ")
    end_date: date = read_date("insert the last day you wanna travel (day month year): ")
    # increment last day for computation reasons
    end_date += timedelta(1)

    while True:
        selection = input(dedent("""\
            Would you like to exclude some days?
            1: yes, exclude a single day
            2: yes, exclude a range
            q: no, proceed with the computation
            """))
        match selection:
            case "1":
                print("1: exclude a single day")
                new_date = read_date(f"insert the day to exclude (day month year): ")
                free_days.add(new_date)
            case "2":
                print("2: exclude a range")
                start_d = read_date("insert first day of the range to exclude (day month year): ")
                end_d = read_date("insert last day of the range to exclude (day month year): ")
                end_d += timedelta(1)
                while start_d != end_d:
                    free_days.add(start_d)
                    start_d += timedelta(1)
            case "q":
                break
            case _:
                print("invalid choice")

    dates: list[date] = [
            start_date + timedelta(i)
            for i in range((end_date - start_date).days + 1)
    ]

    E: dict[tuple[date,date], float] = {}
    for i in range(len(dates)-1):
        for j in range(i+1, len(dates)):
            interval_cost = cost(dates[i], dates[j], free_days)
            if interval_cost is None:
                continue
            E[(dates[i], dates[j])] = interval_cost

    m = mip.Model()
    m.verbose = 0

    f: dict[tuple[date,date], Var] = {(i, j): m.add_var(var_type="B") for (i, j) in E.keys()} # pyright: ignore[reportUnknownMemberType]
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
        print("Could not find a solution, try again or dev's skill issue.")
        exit(1)
    print(f"Da {start_date} a {end_date}")
    print(f"Il costo totale è di {m.objective_value}€.")
    for (i, j), k in f.items():
        if k.x > 0.5:   # pyright: ignore[reportOperatorIssue]
            if E[i, j] > 0:
                if (j - i).days > 7:
                    title = "IOVIAGGIO monthly subscription"
                elif (j - i).days < 4:
                    title = f"IOVIAGGIO {(j - i).days}-days subscription"
                else:
                    title = f"IOVIAGGIO 7-days subscription"
                print(f'{i}->{j - timedelta(1)} {title}')
            else:
                print(f'{i}->{j - timedelta(1)} no cost')


if __name__ == "__main__":
    main()
