# Schrödinger — Akademie Olympia

[Norsk bokmål](README.nb.md) | [English](README.md)

Numeriske kvantesimuleringer for fysikk, forskning og undervisning.

## Installer på Windows

Kjør fra prosjektmappen i PowerShell:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e ".[test]"
& '.\.venv\Scripts\python.exe' -m schroedinger
```

Miljøet trenger ikke aktiveres. På Linux/macOS brukes vanlig venv-aktivering
og `python -m pip install -e ".[test]"`.

## Prøv ulike forsøk

```powershell
# Dobbeltspalte:
& '.\.venv\Scripts\python.exe' -m schroedinger

# Enkeltspalte:
& '.\.venv\Scripts\python.exe' -m schroedinger --scenario single_slit

# Fri gaussisk bølgepakke:
& '.\.venv\Scripts\python.exe' -m schroedinger --scenario free --wave gaussian_packet

# Endelig barriere:
& '.\.venv\Scripts\python.exe' -m schroedinger --scenario wall --wave gaussian_packet

# Én dimensjon:
& '.\.venv\Scripts\python.exe' -m schroedinger --dimension 1

# Vis alle parameterne:
& '.\.venv\Scripts\python.exe' -m schroedinger --help
```

Bruk Pause/Play, Restart og glidebryteren for bilder i animasjonen. Tittelen
viser fysisk tid og samlet sannsynlighet som er igjen i simuleringsområdet.
Lukk vinduet for å avslutte.

Parametere kan endres i kommandoen, for eksempel `--slit-width 0.8`,
`--px 15`, `--dt 0.01` og `--nx 1024`. Kildekoden trenger ikke endres.

## Lagre resultat og kjør tester

```powershell
& '.\.venv\Scripts\python.exe' -m schroedinger --headless --output outputs/forsok.png
& '.\.venv\Scripts\python.exe' -m pytest -q
```

Eksporten skriver en PNG og en JSON med konfigurasjon, tidsverdier,
sannsynlighet, absorbert sannsynlighet, metode og minnebruk for bildene.

## Hva er rettet?

- Ugennomtrengelige 2D-vegger inngår i utbredelsesoperatoren. Bølgen slettes
  ikke ved hvert tidssteg. Lukket vegg bevarer sannsynligheten og slipper
  ikke bølgen gjennom.
- Kantabsorpsjon bruker en rate per tidsenhet. Den kan slås av med
  `--no-absorber`, og sannsynligheten den fjerner måles separat.
- 1D bruker som standard normbevarende Crank–Nicolson. RK4 finnes fortsatt
  med `--method rk4`, men har stabilitetskontroll og renormaliseres ikke
  skjult etter hvert steg.
- Bevegelsesmengdens fase inkluderer hbar. Forventningsverdier bruker riktig
  integrasjonselement og korrekt operatormultiplikasjon.
- Rutenettavstander beregnes fra grensene og antall punkter. Automatisk dt
  følger rutenettet; en eksplisitt dt beholdes.
- 2D-demoen lagrer sannsynlighetstetthet som float32 og bruker en firedel av
  minnet til de tidligere komplekse bildene.

Standardverdiene er demonstrasjonsinnstillinger. For kvantitative resultater
må både rutenett og tidssteg undersøkes for konvergens. Sammenlikn ved samme
fysiske sluttid: Hvis dt halveres, dobles antall steg. En gaussisk bølgepakke
har en energifordeling, så transmisjon gjennom en endelig vegg kan omfatte
både tunnelering og komponenter med energi over barrieren.

Gaussbredden beholder den opprinnelige definisjonen:
psi er proporsjonal med exp(-((x-x0)/sigma)^2). Standardavviket i posisjon
er derfor sigma/2.

Se [den engelske dokumentasjonen](README.md) for metoder, randbetingelser,
Python-API og flere presiseringer. Se [valideringen](docs/VALIDATION.md) for
testgrunnlaget og sammenlikningen med originalversjonen.
