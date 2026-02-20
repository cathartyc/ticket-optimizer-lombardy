from __future__ import annotations
from datetime import date, timedelta
import signal
from textwrap import dedent
from typing import TYPE_CHECKING

import mip
from mip.constants import OptimizationStatus

if TYPE_CHECKING:
    from mip import Real
    from typing import Final
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

def cost(i: int, j: int, dates: list[date], free_days: set[date]) -> float | None:
    # there are j-i days between i and j-1 included
    delta = j - i
    # destination = j-1
    j -= 1
    if all(dates[i+d] in free_days for d in range(delta)):
        return 0

    match (delta):
        case 1:
            return IVOL_DAILY_COST
        case 2:
            return IVOL_TWO_DAYS_COST
        case 3:
            return IVOL_THREE_DAYS_COST
        case 7:
            return IVOL_SEVEN_DAYS_COST
        case _:
            if delta < 7:
                return IVOL_SEVEN_DAYS_COST
            if is_last_day_of_the_month(dates[i].month, dates[j]):
                return IVOL_MONTHLY_COST
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

    E: dict[tuple[int, int], Real] = {}
    for i in range(len(dates)-1):
        for j in range(i+1, len(dates)):
            interval_cost = cost(i, j, dates, free_days)
            if interval_cost is None:
                continue
            E[(i, j)] = interval_cost

    m = mip.Model()
    m.verbose = 0

    f = {(i, j): m.add_var(var_type="B") for (i, j) in E.keys()}
    b = {i: 0 for i in range(len(dates))}
    b[0] = 1
    b[-1] = -1

    # Write flow conservation constraint
    for i in dates:
    for i in range(len(dates)):
        _ = m.add_constr(
              mip.xsum(f[i, j] for j in range(len(dates)) if (i, j) in E.keys())
            - mip.xsum(f[j, i] for j in range(len(dates)) if (j, i) in E.keys())
            == b[i]
        )
    m.objective = mip.minimize(mip.xsum(E[i, j] * f[i, j]  for (i, j) in E.keys())) # pyright: ignore[reportOperatorIssue, reportUnknownMemberType, reportUnknownArgumentType]
    m.objective = mip.minimize(mip.xsum(E[i, j] * f[i, j] for (i, j) in E.keys()))
    status = m.optimize()
    if status == OptimizationStatus.INFEASIBLE:
        print("Could not find a solution, try again or dev's skill issue.")
        exit(1)
    print(f"Da {start_date} a {end_date}")
    print(f"Il costo totale è di {m.objective_value}€.")
    for (i, j), k in f.items():
        assert k.x is not None # .x is None only when the problem is unfeasible
        if k.x > 0.5:
            if E[i, j] > 0:
                if j - i > 7:
                    title = "IOVIAGGIO monthly subscription"
                elif j - i < 4:
                    title = f"IOVIAGGIO {j - i}-days subscription"
                else:
                    title = f"IOVIAGGIO 7-days subscription"
                print(f'{i}->{j - i} {title}')
            else:
                print(f'{i}->{j - i} no cost')


if __name__ == "__main__":
    main()
