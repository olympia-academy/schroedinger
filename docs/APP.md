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

Startsiden bruker **Utforsk**, med fire ferdige utgangspunkt:
dobbeltspalte (2D), enkeltspalte (2D), tunnelering (1D) og fri bølgepakke (2D).
For dobbeltspalten ser du bare bredde, avstand og fysisk sluttid, i tillegg
til valg av forsøk og Kjør-knappen. Hvert oppsett velger dimensjon, metode,
bølge, rutenett og øvrige grunnverdier for deg. Et nytt ferdig oppsett
erstatter redigeringsinnstillingene, men sletter ikke fullførte resultater.

1. Velg et oppsett og juster eventuelt de få synlige egenskapene.
   **Fysisk sluttid** angir hvor lenge fysikken skal utvikles. Antall steg
   beregnes automatisk. Endring av kontroller starter ingen beregning.
2. Trykk **Kjør simulering**. **Avbryt beregningen** stopper prosessen og
   beholder tidligere fullførte resultater.
3. Trykk **Spill av** for å animere de lagrede bildene. **Pause** stopper
   visningen; **Start på nytt** spiller fra første bilde. **Hastighet**
   velger 2, 4, 8, 12 eller 24 bilder per sekund (standard: 12) og endrer bare visningen.
   Flytting av **Lagret tidssteg** pauser avspillingen ved det valgte bildet.
   Den stopper automatisk ved siste bilde. Trykk Spill av igjen for å starte
   fra begynnelsen. Tittelen viser faktisk fysisk tid og sannsynlighet.
4. Velg **Sammenlikn** i sidepanelet. Velg en fullført kjøring som utgangspunkt,
   deretter én parameter og dens nye verdi. Sluttiden og andre innstillinger
   beholdes. Appen viser hva som faktisk endret seg, inkludert eventuelle
   avledede tidsverdier og endrede diskrete spalteåpninger.
5. Velg **Avansert** når du vil endre masse, ħ, metode, rutenett, boks,
   absorber eller andre parametere. Andre forsøkstyper finnes også her.
   Bytte mellom visningene beholder de redigerte grunnverdiene. Endring av
   dimensjon i Avansert laster standardverdier for den nye dimensjonen.
6. Last ned JSON-oppsett/rapport, PNG-bilde og CSV-regnskap. Den andre
   bidragsyteren kan åpne JSON-filen under **Åpne lagret oppsett → Bruk
   oppsett**; det åpnes i Avansert med samme faktiske tidsverdier.

**Beregningsdetaljer** viser faktisk dt, antall steg, rutenettavstand,
minneanslag, randtype og diskrete spalteåpninger. Disse er informasjon som
kan åpnes ved behov, i stedet for beslutninger som kreves på startsiden.

I Avansert er ønsket dt en øvre grense. Appen bruker `ceil(T/dt)` like steg
og kan redusere dt litt for å treffe T nøyaktig. Faktisk dt og antall steg
vises og eksporteres; ingen ekstra delvis tidssteg legges til i løseren.
Et endret tidssteg i Sammenlikn vil derfor også endre antall steg. Dette er
en avledet endring for å holde fysisk sluttid fast. Metoden blir ikke
automatisk nøyaktig eller stabil bare fordi sluttiden treffes.

De to siste fullførte resultatene beholdes i nettleserøkten. En ny økt eller
omstart av serveren kan miste historikken; last ned det som skal tas vare på.
JSON-filen inneholder parametere og diagnostikk, ikke alle tetthetsbilder.
PNG er ett valgt bilde; CSV inneholder tid, sannsynlighet og absorbert
sannsynlighet. Faseinformasjon lagres ikke i appresultatene. Bruk
Python-API-et med komplekse rammer når fase er nødvendig.

I Sammenlikn beholdes den valgte utgangskjøringen sammen med det nye
resultatet, også når du velger den eldste av de to. De to bildene bruker
samme 2D-fargeskala og viser nærmeste faktisk lagrede tidspunkt.

Bildene klargjøres og lastes inn én gang før knappene blir aktive. Deretter
spiller nettleseren dem av lokalt, uten Python-tegning eller servermeldinger
for hvert bilde. Knappene, tidsvelgeren og målene oppdateres i samme spiller.
Avspillingen pauses ved valg av en annen kjøring, oppdatering av resten av
appen eller skjuling av nettleserfanen. Langsommere maskiner kan hoppe over
bilder for å følge avspillingsklokken. Fysisk tid og sannsynlighet følger
alltid det faktisk viste, lagrede bildet. Ingen mellomliggende tidsbilder
beregnes eller interpoleres under avspilling.

Nye standardkjøringer lagrer 91 bilder i stedet for 37. Tidligere resultater
beholder sine opprinnelige bilder; kjør forsøket på nytt for tettere avspilling.
2D-spilleren bruker PNG med 256 Inferno-farger, felles fast fargeskala og
barriereomriss på det opprinnelige rutenettet. Dette er en visningskoding;
lagrede float32-tettheter og diagnostikk beholdes. 1D-tetthetene overføres
uten tap som float32. PNG-knappen lagrer det viste diagrammet med akser og
tittel. De statiske sammenlikningsbildene tegnes fortsatt med Matplotlib.

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
- `app_presets.py`: fixed presets, final-time fitting and controlled-change helpers.
- `app_controls.py`: simple, comparison and advanced editing, with persistent drafts.
- `app_playback.py`: cached display data and the browser component.
- `player.mjs`: local canvas rendering and playback controls, with no per-frame server calls.
- `app_jobs.py` / `app_worker.py`: subprocess lifecycle and cancellation.
- `web_app.py`: Streamlit controls and result comparison.

## Tests

```bash
python -m pip install -e ".[app,test]"
python -m pytest -q
```

Tests cover CLI/app result agreement, both 1D methods, JSON/NPZ round trips,
geometry reporting, resource limits, real worker completion/cancellation,
UI method selection, two-run comparison and cached playback without
recalculation. Additional tests cover exact final-time fitting, the three-field
default, settings surviving mode changes, preset resets, and preservation of
the selected baseline when a third comparison is run.
Python tests check pixel orientation, fixed color mapping, lossless 1D density
encoding, physical timestamps and diagnostics, with propagation forbidden during
preparation. JavaScript tests check the wall-clock advance, pause, seeking,
restart, speed changes and automatic stop:

```bash
node --test tests/player.test.mjs
```

Node is needed only for these developer tests, not to run the app.
The optional UI tests skip when Streamlit is not installed.
CI runs the app tests on Windows, macOS and Linux with Python 3.12.

Streamlit's current [installation requirements](https://docs.streamlit.io/get-started/installation/command-line)
and [AppTest documentation](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
describe the framework environment and test interface.
