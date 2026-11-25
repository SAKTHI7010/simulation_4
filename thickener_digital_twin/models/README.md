# Models Directory

This project is **physics-first**, implementing the process engineering equations from Project 4 (§5.6 and §5.8):
1. Richardson-Zaki hindered settling (`backend/settling_velocity.py`)
2. Solids flux & limiting flux (`backend/flux_model.py`)
3. Thickener area sizing (`backend/thickener_area.py`)
4. Bounded flocculant dose-response (`backend/flocculant_model.py`)
5. Dynamic solids inventory & bed-level ODE (`backend/bed_dynamics.py`)
6. Synthetic rheology & pumpability pressure balance (`backend/rheology_model.py`, `backend/pumpability.py`)
7. Monte Carlo uncertainty propagation (`backend/monte_carlo.py`)

Optional ML surrogates (e.g., for fast calibration against measured batch-settling tables) should be saved here once real plant data are added to `data/raw/`.
