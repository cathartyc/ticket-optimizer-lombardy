# Ticket optimizer - Lombardy
A somewhat useful interactive tool to find the least expensive choice of IVOL
(_Io Viaggio Ovunque in Lombardia_, I Travel Everywhere in Lombardy)
[tickets](https://www.regione.lombardia.it/wps/portal/istituzionale/HP/DettaglioServizio/servizi-e-informazioni/Cittadini/Muoversi-in-Lombardia/biglietti-e-agevolazioni/Io-viaggio/01-io-viaggio-ovunque-in-lombardia-biglietti-giornaliero-settimanale/01-io-viaggio-ovunque-in-lombardia-biglietti-giornaliero-settimanale)
and
[subscriptions](https://www.regione.lombardia.it/wps/portal/istituzionale/HP/DettaglioServizio/servizi-e-informazioni/Cittadini/Muoversi-in-Lombardia/biglietti-e-agevolazioni/Io-viaggio/io-viaggio-ovunque-in-lombardia-abbonamento/io-viaggio-ovunque-in-lombardia-abbonamento),
(other kind of tickets are WIP), given a range of days. It also allows
to specify days within the range to be ignored.

## Installation
Just use [uv](https://docs.astral.sh/uv):
```bash
$ # assuming you already cloned the project and cd-ed inside it, just run:
$ uv run main.py
```
In alternative, you could use python >=3.12 and install
[python-mip](https://github.com/coin-or/python-mip) in a virtual environment:
```bash
$ # in the project directory:
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install mip
$ python3 main.py
```
I could not install `mip` for python >3.12, so YMMV.

I plan to upgrade the project to the latest python version as soon as I am able
to make it work with that.

## Concept
The problem of finding the least expensive choice of tickets and subscriptions
is modeled as a [_minimum-cost flow
problem_](https://en.wikipedia.org/wiki/Minimum-cost_flow_problem), which can
be solved by linear programming: `mip` indeed provides a set of linear solvers.

## License
TODO
