# Local browser app / Lokal nettapp

Schrödinger-lab is a local experiment interface for Windows, macOS and Linux.
It uses the existing package's propagators. The optional app extra requires
**Python 3.11 or newer**; the core command-line package still supports 3.10.

The browser is the interface; Python runs on each person's own computer.
No cloud account, shared server or hosted deployment is needed.

## Install and start

Run from the repository root. If `.venv` already exists with Python 3.11+,
skip the first command.

Windows PowerShell:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e ".[app]"
& '.\.venv\Scripts\python.exe' -m schroedinger.app
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[app]"
.venv/bin/python -m schroedinger.app
```

With the environment activated, either platform can use:

```bash
python -m schroedinger.app
```

Open **http://127.0.0.1:8501** if a browser does not open automatically.
Keep the terminal running; stop the server with Ctrl+C.
`python -m schroedinger.app --port 8502` chooses another port if needed.
`--no-browser` starts the server without opening a browser.

The launcher binds to 127.0.0.1. It does not expose the app on the network.
This first version is for local use, not a public multi-user service.

## Slik prøver dere appen

1. Velg 1D eller 2D og et forsøk i sidepanelet. Endring av dimensjon laster
   et nytt standardoppsett. Andre felt gjelder det valgte forsøket.
2. Juster tid, oppløsning, bølge, potensial eller boks. Trykk **Kjør
   simulering** for å bruke endringene i skjemaet. Ingen simulering starter
   når siden åpnes eller når du bare viser et resultat.
3. Appen viser at beregningen kjører. **Avbryt beregningen** stopper
   prosessen og beholder tidligere fullførte resultater.
4. Bruk **Lagret tidssteg** for å se lagrede tetthetsbilder. Tittelen viser
   faktisk fysisk tid og sannsynlighet i boksen.
5. Gi neste kjøring et eget navn, endre én parameter og kjør igjen.
   **Sammenlikn de to siste kjøringene** viser bilder og parametere ved
   nærmeste lagrede tid. 2D-bildene bruker samme fargeskala i sammenlikningen.
6. Last ned JSON-oppsett/rapport, PNG-bilde og CSV-regnskap. Den andre
   bidragsyteren kan åpne JSON-filen under **Åpne lagret oppsett → Bruk
   oppsett** og kjøre samme forsøk på sin maskin.

De to siste fullførte resultatene beholdes i nettleserøkten. En ny økt eller
omstart av serveren kan miste historikken; last ned det som skal tas vare på.
JSON-filen inneholder parametere og diagnostikk, ikke alle tetthetsbilder.
PNG er ett valgt bilde; CSV inneholder tid, sannsynlighet og absorbert
sannsynlighet. Faseinformasjon lagres ikke i appresultatene. Bruk
Python-API-et med komplekse rammer når fase er nødvendig.

## Numerical interpretation

- Both 1D time methods are selectable: Crank–Nicolson and RK4. The app uses
  the package's existing solver and its stability checks, not a separate
  implementation of the physics.
- The 2D initial app demo uses the standard 512x256 geometry but stops at
  T=7.03125 (180 steps). The CLI's longer default remains unchanged.
  Stored frames are capped separately from propagation steps.
- The app explicitly shows the outer boundary, absorber state, derived dx,
  saved times, probability budget and discrete slit opening widths between
  zero-value nodes. The full metadata include their coordinates.
- Periodic outer boundaries can wrap outgoing waves; Dirichlet boundaries
  reflect them without absorption. The absorber reduces returning waves
  but is not an exact transparent boundary. There is no independent
  boundary-condition selector.
- A changed grid can change discrete slit geometry. Comparing screenshots
  does not establish convergence. Actual saved comparison times are shown
  separately and can differ from the requested comparison time.
- Norm preservation, stability and accuracy are different requirements.
  Check spatial resolution, time step, geometry, box size and absorber
  before quantitative conclusions. See [VALIDATION.md](VALIDATION.md).

## Resource use and implementation

One worker process is allowed at a time across browser tabs. Numerical
thread environment variables are set to one. Each run is limited to
1,048,576 grid points, 121 frames and 128 MiB of density snapshots; working
arrays and the browser require additional memory. Controls restrict grids
to 8–2048 points per direction and certain positive parameters to at least
1e-6 (dt to at least 1e-8); these are app limits, not core solver limits.

The worker's temporary input/result files are removed after collection or
cancellation. If a tab is abandoned, an active worker can finish; a later
run can replace an uncollected completed job. Closing a tab does not shut
down the server. Use the terminal to stop it.

- `app.py`: portable launcher with the active interpreter and loopback binding.
- `app_model.py`: experiment settings, validation, solver calls and exports.
- `app_jobs.py` / `app_worker.py`: subprocess lifecycle and cancellation.
- `web_app.py`: Streamlit controls and result comparison.

## Tests

```bash
python -m pip install -e ".[app,test]"
python -m pytest -q
```

Tests cover CLI/app result agreement, both 1D methods, JSON/NPZ round trips,
geometry reporting, resource limits, real worker completion/cancellation,
UI method selection, two-run comparison and frame scrubbing without
recalculation. The optional UI tests skip when Streamlit is not installed.
CI runs the app tests on Windows, macOS and Linux with Python 3.12.

Streamlit's current [installation requirements](https://docs.streamlit.io/get-started/installation/command-line)
and [AppTest documentation](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
describe the framework environment and test interface.
