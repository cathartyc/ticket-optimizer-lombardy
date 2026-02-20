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

ONE_DAY: Final[timedelta] = timedelta(1)

def is_last_day_of_the_month(month: int, day: date) -> bool:
    """True if the given day is the last day of the given month."""
    return month == day.month and (day + ONE_DAY).day == 1


def cost(i: int, j: int, dates: list[date], free_days: set[date]) -> float | None:
    # there are j-i days between i and j-1 included
    delta = j - i
    # destination = j-1
    j -= 1
    if all(dates[i+d] in free_days for d in range(delta)):
        # if this range is contained in a bigger free range, ignore it
        if (i > 0 and dates[i-1] in free_days) or (j < len(dates)-1 and dates[j+1] in free_days):
            return None
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
            if dates[i].month == dates[j].month:
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

def get_free_days(start_date: date, end_date: date) -> set[date]:
    """Asks the user for free days as single days or range of days.

    :return: a set containing the user-defined free days
    """
    free_days: set[date] = set()

    # ask for weekends
    while True:
        ignore_weekends = input("Do you want to ignore weekends? [Y/n]: ")
        match ignore_weekends:
            case ('Y' | 'y' | ''):
                # add weekends to set
                free_days.update(
                        start_date + ONE_DAY*i
                        for i in range((end_date - start_date).days + 1)
                        if (start_date + ONE_DAY*i).weekday() >= 5
                )
                break
            case ('N' | 'n'):
                # don't count weekends as free days, break
                break
            case _:
                # repeat prompt
                pass

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
                end_d += ONE_DAY
                while start_d != end_d:
                    free_days.add(start_d)
                    start_d += ONE_DAY
            case "q":
                break
            case _:
                print("invalid choice")
    return free_days


def main():
    # capture ^C
    _ = signal.signal(signal.SIGINT, exit_gracefully)

    start_date: date = read_date("insert the first day you wanna travel (day month year): ")
    end_date: date = read_date("insert the last day you wanna travel (day month year): ")

    free_days = get_free_days(start_date, end_date)

    # adjust start_date and end_date to consider eventual leading and trailing
    # free days
    effective_start_date = start_date
    while effective_start_date in free_days:
        effective_start_date += ONE_DAY
    effective_end_date = end_date
    while effective_end_date in free_days:
        effective_end_date -= ONE_DAY

    # end-start+1, +1 again to account for the extra day (see `cost()`)
    num_dates = (effective_end_date - effective_start_date).days + 2
    # dates within the range
    dates: list[date] = [
            effective_start_date + ONE_DAY*i
            for i in range(num_dates)
    ]

    E: dict[tuple[int, int], Real] = {}
    for i in range(num_dates - 1):
        for j in range(i + 1, num_dates):
            interval_cost = cost(i, j, dates, free_days)
            if interval_cost is None:
                continue
            E[(i, j)] = interval_cost

    m = mip.Model()
    m.verbose = 0

    f = {(i, j): m.add_var(var_type="B") for (i, j) in E.keys()}
    b = [0] * num_dates
    b[0] = 1
    b[-1] = -1

    # Write flow conservation constraint
    for i in dates:
    for i in range(num_dates):
        _ = m.add_constr(
              mip.xsum(f[i, j] for j in range(num_dates) if (i, j) in E.keys())
            - mip.xsum(f[j, i] for j in range(num_dates) if (j, i) in E.keys())
            == b[i]
        )

    # objective function here is (E+1)*f, where the + 1 is meant to reduce the
    # amount of tickets in cases where you could spend the same amount in e.g.
    # one tickets instead of two
    m.objective = mip.minimize(mip.xsum((E[i, j] + 1) * f[i, j] for (i, j) in E.keys()))

    status = m.optimize()
    if status == OptimizationStatus.INFEASIBLE:
        print("Could not find a solution, try again or dev's skill issue.")
        exit(1)
    assert m.objective_value is not None
    result = m.objective_value - sum(int(k.x) for k in f.values() if k.x is not None)
    print(f"\nTotal cost is {result}€:")

    if effective_start_date != start_date:
        print(f'{start_date}->{effective_start_date-ONE_DAY} no cost')

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
                print(f'{dates[i]}->{dates[j-1]} {title}')
            else:
                print(f'{dates[i]}->{dates[j-1]} no cost')

    if effective_end_date != end_date:
        print(f'{effective_end_date}->{end_date} no cost')


if __name__ == "__main__":
    main()
