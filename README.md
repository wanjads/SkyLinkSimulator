# SkyLinkSimulator

A fast simulator for a LEO satellite network with ISLs/GSLs, buffer/queueing model, and routing strategies

## Prerequisites

- Python 3.11 or later
- (Recommended) a virtual environment
- Install dependencies from requirements.txt

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts ctivate
pip install -r requirements.txt
```

## Data

By default, `main.py` expects precomputed data under `data/`.

Generate data:

- Positions: `src/calculators/position_calculator.py`
- Visibilities: `src/calculators/neighbour_calculator.py`, `src/calculators/gs_neighbour_calculator.py`
- Traffic: `src/calculators/data_calculator.py`
- Atmosphere/Radio: `src/calculators/atmospheric_attenuation.py`, `src/calculators/rician.py`

The calculator scripts use `CosmicBeats` (included in the repo at `src/calculators/CosmicBeats/`); the configuration is referenced in the
scripts (e.g., `CosmicBeats/configs/oneweb/config.json`).

## Quickstart (Simulation)

```bash
python main.py   --growth_factor 2   --gsl_failures False   --isl_failures False   --max_time_steps 240   --logging False   --seed 0   --repetitions 1
```

### CLI arguments

- `--growth_factor` (float): Scales the data generation rate
- `--gsl_failures` (bool): Simulates GSL failures
- `--isl_failures` (bool): Simulates ISL failures
- `--max_time_steps` (int): Number of time steps
- `--logging` (bool): CSV logging in `logging/` and `results/`
- `--seed` (int): Reproducibility
- `--repetitions` (int): Multiple runs per strategy

## Results & Visualization

- Logs/CSV: `logging/`, `results/`
- Plots: `src/visualisation/` (`time_plot.py`, `parameter_plot.py`, `growth_factors_multiple_runs.py`)
