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

Startsiden bruker **Utforsk**, med fire ferdige utgangspunkt: dobbeltspalte
(2D), enkeltspalte (2D), tunnelering (1D) og fri bølgepakke (2D). For
standardforsøket trenger du bare spaltebredde, spalteavstand og fysisk sluttid.

1. Velg et forsøk og trykk **Kjør simulering**. Ingen beregning starter ved
   endring av innstillinger. **Avbryt beregningen** stopper den aktive prosessen.
   Fremdriftslinjen viser prosent av faktisk fullførte beregningssteg.
   Oppstart og lagring av resultat vises som egne faser; prosent er ikke et
   estimat av gjenstående veggklokketid. Fremdriften oppdateres omtrent én gang
   per sekund i appen og krever ingen endring av fysikkparametere.
2. Resultatet åpnes ved siste bilde. Bruk **Spill av**, **Pause**, **Start på
   nytt** eller **Lagret tidssteg**. Hastighet velger 2/4/8/12/24 bilder/s;
   standard er 12. Søking pauser. Avspillingen stopper ved siste bilde.
3. Åpne **Visning og målinger** for lys/mørk fargeskala, fremheving av svake
   mønstre og profilens x-posisjon. Disse valgene endrer ingen fysikkparametere.
4. Velg **Sammenlikn** i sidepanelet for å kopiere en fullført kjøring og endre
   én parameter. Fysisk sluttid og valgt utgangspunkt beholdes. Faktiske
   endringer og diskrete spalteåpninger vises ved resultatet.
5. Når to resultater har samme dimensjon, er **Spill av begge sammen** på som
   standard. Én spiller styrer begge bilder og målinger. Slå av for å vise bare
   den valgte kjøringen.
6. **Avansert** viser alle fysikk- og beregningsparametere. Endrede innstillinger
   beholdes ved bytte av arbeidsmåte. Et nytt ferdig oppsett erstatter utkastet.

**Beregningsdetaljer** viser faktisk dt, antall steg, rutenettavstand,
minneanslag, randtype og diskrete spalteåpninger. Sluttiden treffes med
`ceil(T/dt)` like steg; ønsket dt er en øvre grense. Faktisk dt kan derfor
reduseres litt. Oppsett og rapport lagrer faktiske dt/steg.

### Visning og synkronisering

Alle bilder klargjøres én gang og lastes inn før avspillingsknappene aktiveres.
Nettleseren spiller dem av uten Python-tegning eller servermeldinger for hvert
bilde. Endring av visningsvalg klargjør bildene på nytt og pauser avspillingen.
Appoppdatering, valg av annen kjøring og skjuling av fanen pauser også.
Langsomme maskiner kan hoppe over visningsbilder for å følge klokken.

Nye standardkjøringer lagrer 91 bilder. Eldre resultater beholder sine bilder.
Den lyse standarden er YlGnBu med gamma 0,5, som fremhever svake tettheter.
**Fremhev svake mønstre** kan slås av for lineær visning. **Mørk** velger Inferno.
Fargelinjen oppgir faktiske tetthetsverdier med riktig invers gamma, og andelen
mettede piksler oppgis. En automatisk øvre fargegrense basert på tetthetene kan
mette de sterkeste toppene; dette gjelder bare visningen. 2D-bilder kodes med
256 farger på opprinnelig rutenett. Float32-tettheter og sannsynlighetsregnskap
endres ikke. 1D-tettheter overføres tapsfritt som float32. Potensialet har en
egen merket høyreakse, adskilt fra tetthetens akse.

Ved to kjøringer brukes samme fargeskala for begge og gjennom hele tidsforløpet.
1D-tettheter og 2D-profiler har også felles høydeakse. Felles ønsket tid går fra
0 til den korteste sluttiden. Nærmeste lagrede bilde velges i hver kjøring;
begge viser faktisk tid og tidsavvik. Ingen tettheter interpoleres i tid.
Profiler fra ulike rutenett kan ligge ved litt ulike faktiske x-koordinater;
disse oppgis. Ingen felles profilposisjon velges hvis boksene ikke overlapper.

**Last ned bildet** eksporterer det viste diagrammet/de viste diagrammene,
inkludert akser, fargelinje, faktisk tid og eventuelle 2D-profiler, som PNG.

### Målinger og faglig tolkning

Ved barrierer vises integrert sannsynlighet til venstre for, i og til høyre
for barriereområdet ved valgt tid. For 1D-barrierer velges høyre/venstre
barriere ut fra den innkommende bevegelsesmengdens fortegn. I 2D brukes
spalteveggens faktiske ytterste rutenettnoder eller den endelige barrierens
nominelle flater. Regionene deler hele rutenettet og summerer til P i boksen.

Disse andelene er **ikke automatisk refleksjons- og transmisjonskoeffisienter**:
den innkommende pakken kan fortsatt være foran barrieren, og absorpsjon,
tilbakekomst fra ytterkanten og flere kollisjoner kan endre andelene.

2D-profilen er `|ψ(x_screen,y,t)|²` i den nærmeste faktiske x-kolonnen. Den
oppdateres med avspilleren og viser tetthet langs y på felles fast høydeakse.
Den er et øyeblikksbilde, ikke et tidsintegrert detektorsignal eller en
sannsynlighetsstrøm. Tetthetsdata alene er ikke tilstrekkelige til all
fase-/strømanalyse. x, t og V bruker modellens valgte enheter.

### Lagre og gjenåpne resultater

Åpne **Lagre resultat og oppsett → Klargjør komplett resultatfil → Last ned
komplett resultat**. NPZ-filen inneholder alle lagrede float32-tettheter,
fysiske tider, oppsett og diagnostikk. Åpne den igjen via **Åpne komplett
resultat → Resultatfil (.npz) → Åpne resultat** i sidepanelet. Dette starter
ingen simulering. Det åpne resultatet kan spilles av, sammenliknes og brukes
som utgangspunkt for nye forsøk eller numeriske kontroller.

Bare de to siste resultatene beholdes i øktens minne. Serveromstart eller ny
økt kan miste dem. Lagre resultatfilene på disk for å beholde dem. Én komprimert
eksportfil mellomlagres av gangen. Det øker ikke grensen for aktive kjøringer.

JSON inneholder oppsett og rapport, ikke alle bilder; åpnes via **Åpne lagret
oppsett → Bruk oppsett** og krever en ny kjøring for å lage bilder. CSV
inneholder sannsynlighetsregnskapet. Ingen av appformatene inneholder fase.
Bruk Python-API-et med komplekse rammer når fase er nødvendig.

Resultatimport bruker `allow_pickle=False` og kontrollerer NPY-hoder,
utpakket størrelse, dimensjoner, endelige/ikke-negative tettheter, lagrede
tider og samsvar mellom integrert tetthet og rapportert sannsynlighet.
Komprimerte filer kan være høyst 160 MiB, tettheter høyst 128 MiB og metadata
høyst 1 MiB. Formatet beholder schema_version=1.

### Veiledet kontroll av numerisk nøyaktighet

Åpne **Kontroller numerisk nøyaktighet**. Velg **Halvert tidssteg** eller
**Dobbelt så fint rutenett**, les oppsettet og trykk **Kjør kontroll**. Dette
er en ny beregning som kan avbrytes. Utgangsresultatet beholdes til sammenlikning.
Fysisk sluttid holdes fast. 1D beholder boksens endepunkter og halverer dx;
2D dobler punkttallene i begge retninger. Antall lagrede bilder reduseres ved
behov for å overholde minnegrensen; ingen beregningssteg hoppes over.

Etterpå vises sluttavviket `∫|ρ₁−ρ₂| dV` og forskjellen i P i boksen. Ved ulikt
rutenett interpoleres kontrollens tetthet i rom til utgangsrutenettet. Det
er et mål på tetthetsforskjell, ikke en fasefeil eller en full feilanalyse.
Endrede diskrete randkoordinater/geometri markeres særskilt. Slike endringer
blander romdiskretiseringsfeil med endret representert geometri.

Én slik sammenlikning dokumenterer et avvik, **ikke konvergens**. Gjenta ved
behov og kontroller også boks, geometri og absorber. Se [VALIDATION.md](VALIDATION.md).

## Numerical interpretation

- The app uses the existing production propagators. Crank–Nicolson and RK4
  remain selectable for 1D, including existing stability checks.
- The default 2D demo uses the original 512x256 geometry and T=7.03125
  (180 steps). CLI defaults and numerical propagation have not been changed.
- Periodic outer boundaries can wrap waves; Dirichlet boundaries reflect
  without absorption. An absorber is not an exact transparent boundary.
  There is no independent boundary-condition selector.
- Saved density-only results do not retain phase. Norm preservation,
  stability, density agreement and full wave-function accuracy are distinct.

## Resource use and implementation

One numerical worker is allowed across tabs, with numerical threads set to one.
Each run is limited to 1,048,576 grid points, 121 frames and 128 MiB snapshots.
Working arrays, encoded displays, two active results and browser images require
additional memory. Grids allow 8–2048 points per direction; selected positive
parameters have app-specific lower bounds. Worker temporary files are removed
after collection or cancellation. Closing the browser does not stop the server.

- `app.py`: portable launcher, active interpreter and loopback binding.
- `app_model.py`: experiment settings, solver calls and validated portable files.
- `app_presets.py` / `app_controls.py`: presets, final-time fitting and controls.
- `app_analysis.py`: saved-frame selection, region/profile measurements and refinement.
- `app_results.py`: result views, complete import/export and numerical checks.
- `app_playback.py` / `player.mjs`: shared display data and browser-only playback.
- `app_jobs.py` / `app_worker.py`: one numerical subprocess and cancellation.

## Tests

```bash
python -m pip install -e ".[app,test]"
python -m pytest -q
node --test tests/player.test.mjs
```

Node is only needed for developer playback tests, not to run the app.
Tests cover CLI/app density agreement, both 1D methods, JSON/NPZ round trips,
bounded untrusted result import, geometry/resource limits, actual worker
completion/cancellation, progressive controls, baseline retention, shared
color/timing scales, profile/region integrals, refinement and density differences.
JavaScript tests check playback timing, seeking, restart, rates, stopping,
inverse gamma colorbar values and readable physical-axis ticks.
Optional Streamlit UI tests skip without the app extra. CI runs the app tests
and playback tests on Windows, macOS and Linux with Python 3.12.
