# Fra likning til simulering

Denne veiledningen forklarer modellvalg, randbetingelser og kode for
undervisning. Den historiske koden finnes uendret under
[`original`](https://github.com/olympia-academy/schroedinger/tree/original).
Dagens versjon er en videreutvikling, ikke en numerisk identisk gjengivelse.

## Hva er bevart, og hva er endret?

Vi løser fortsatt den tidsavhengige Schrödinger-likningen

```text
i hbar dpsi/dt = H psi
H = -hbar²/(2m) Laplace + V
```

Gausskonvensjonen er bevart: `psi ~ exp(-((x-x0)/sigma)²)`. Standardavviket
til posisjonsfordelingen er derfor `sigma/2`. Spalteforsøkene, bølgepakkene
og forfatterskapet er videreført. Men beregningsmetodene er endret:

- 1D bruker Crank–Nicolson som standard, med RK4 som alternativ.
- Harde 2D-vegger inngår i den kinetiske utbredelsen. Originalen utviklet
  først bølgen med FFT og slettet så amplituden inne i veggen. Det kunne
  fjerne sannsynlighet som fysisk skulle blitt reflektert.
- Kantabsorpsjon er nå en rate per tidsenhet, ikke en fast faktor per steg.
- 2D-spalter har nå Dirichlet-ytterkanter i stedet for periodiske ytterkanter.

Siste punkt er en endring av den endelige beregningsboksen, ikke bare en
optimalisering. Bilder fra de to versjonene trenger derfor ikke være like.
`--method rk4` alene gjenskaper heller ikke hele originalens 1D-algoritme:
den skjulte renormaliseringen etter hvert steg er fjernet.

Originalens 1D-startfil satte dessuten barrierehøyden til `1.2*p²/(2*m)`.
Dagens kommandolinje bruker 24 som standard, som gir samme høyde for
standardens p=20 og m=10. Endrer du p eller m, følger ikke barrierehøyden
automatisk med; sett `--potential-strength` eksplisitt hvis du vil bevare
det samme forholdet mellom høyde og kinetisk energi.

## To forskjellige grenser: spalteveggen og ytterkanten

Spalteveggen er en **intern grense** inne i boksen. Ytterkantene av boksen
ligger lenger ute. At spalteveggen skal være ugjennomtrengelig, bestemmer
ikke automatisk hvordan de ytre kantene bør behandles.

| Valg i dagens kode | Hvor brukes det? | Hva skjer med utgående bølger? |
|---|---|---|
| Periodisk ytterkant | 2D fri partikkel og endelig potensial, med FFT | Bølgen kan gå ut på én side og komme inn på motsatt side. |
| Null Dirichlet, psi = 0 | 1D og 2D-spalteløseren | Uten absorber oppfører ytterkanten seg som en reflekterende boksvegg. |
| Absorberende lag innenfor ytterkanten | Valgfritt i begge dimensjoner | Bølgen dempes før den når ytterkanten; litt refleksjon og restamplitude kan fortsatt forekomme. |

En bølge som kommer tilbake fra kanten, kan interferere med bølgene vi
ønsker å studere. Et pent interferensbilde kan derfor inneholde både
spaltefysikk og bidrag fra den endelige boksen. Stor nok boks, egnet absorber
og måling ved passende tid må undersøkes sammen.

Absorberen erstatter ikke den underliggende randbetingelsen med en eksakt
åpen grense. `--no-absorber` fjerner bare dempingen. Det gjør **ikke** en
Dirichlet-boks periodisk eller en periodisk boks reflekterende.

Metoden velges automatisk fra dimensjon og veggtype. Det finnes foreløpig
ikke et fritt `--boundary`-valg. Neumann- og Robin-betingelser, eksakte
transparente grenser og PML er ikke implementert.

## Hvor ligger veggen på rutenettet?

Rutenettpunktene er prøvepunkter, ikke kontinuerlige flater. I 1D brukes
endelige differanser; nullverdiene ligger ved de to nabopunktene utenfor
de lagrede punktene. Med N punkter blir avstanden mellom nullgrensene
`(N+1)*dx`, ikke `(N-1)*dx`.

2D bruker punkter uten høyre endepunkt: `x_j = x_min + j*dx`.
For et helt tillatt intervall ligger sinusløserens ytre nullpunkter derfor
ved `x_min-dx` og `x_max`. Inne ved veggen ligger nullpunktene i de nærmeste
utelukkede veggpunktene. Tilsvarende gjelder y-retningen.
Dette følger DST-I-konvensjonen i
[SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.fft.dst.html).

Vegger og spalter tegnes på dette rutenettet. En nominell spaltebredde på
0,6 blir derfor ikke nødvendigvis nøyaktig 0,6 i den diskrete modellen.
Antall åpne punkter ganger dy er et mål på rasteret; avstanden mellom
sinusmetodens nullpunkter er et annet. Når rutenettet endres, endres også
den representerte geometrien litt. Begge deler må vurderes ved konvergens.

## Hva måler sannsynlighetsregnskapet?

```text
P(t) = sum |psi|² * dx             (1D)
P(t) = sum |psi|² * dx * dy        (2D)
```

Den initiale bølgen normaliseres. Hvis den overlapper en hard vegg,
projiseres den bort fra veggpunktene og normaliseres én gang før t=0.
Dette tapet rapporteres separat som `initial_projection_loss`.

Uten absorber skal de unitære metodene bevare P opp til avrundingsfeil.
Med absorber undersøker vi `P(t) + absorbert(t) ≈ P(0)`. RK4 kan i tillegg
ha numerisk normdrift. Ingen av metodene renormaliserer bølgen inne i løkken.
Et godt sannsynlighetsregnskap beviser ikke at fase, spaltebredde eller
interferensmønster er konvergert.

## Crank–Nicolson og RK4: begge kan velges i 1D

Fra repoets rot:

```powershell
# Standardmetoden, valgt eksplisitt:
& '.\.venv\Scripts\python.exe' -m schroedinger --dimension 1 --method crank_nicolson

# Alternativet som ligger nærmere originalens tidsmetode:
& '.\.venv\Scripts\python.exe' -m schroedinger --dimension 1 --method rk4
```

`--method auto` velger Crank–Nicolson i 1D. Metodevalgene ovenfor gjelder
ikke 2D, der vi bruker Fourier- eller sinusbasert Strang-splitting.

| Egenskap | Crank–Nicolson | Klassisk RK4 |
|---|---|---|
| Prinsipp | Implisitt: løser et lineært system for neste tilstand. | Eksplisitt: beregner fire helninger per steg. |
| Global tidsorden | Andre orden for glatt løsning og fast romdiskretisering. | Fjerde orden under tilsvarende forutsetninger. |
| Norm uten absorber | Bevares opp til avrunding for den hermitiske Hamilton-operatoren her. | Ikke eksakt bevart; drift kan oppstå også innenfor stabilitetsområdet. |
| Stabilitet her | Ingen RK4-lignende øvre stabilitetsgrense for dt i det lukkede lineære problemet. | dt må ligge innenfor stabilitetsområdet. Koden bruker en konservativ spektralgrense. |
| Kostnad | Tridiagonalt system; produksjonskoden faktoriserer én gang for statisk potensial. | Fire evalueringer av høyresiden; ingen lineær systemløsning. |
| Viktig begrensning | Stor dt kan gi betydelig fasefeil selv om normen er perfekt. | Høyere tidsorden fjerner ikke romfeil, randfeil eller stabilitetsgrensen. |

Begge bruker samme tredelte endelige differanse for den andrederiverte i
rommet. Det gir andre ordens romtilnærming for glatte løsninger.
RK4 er derfor ikke automatisk «mest nøyaktig», og Crank–Nicolson er ikke
automatisk «riktig» fordi den bevarer normen. Sammenlikn ved samme fysiske
sluttid og samme rutenett, og varier deretter dt og dx hver for seg.

Crank–Nicolson kan skrives

```text
(I + i*dt*H/(2*hbar)) psi_ny = (I - i*dt*H/(2*hbar)) psi
```

RK4 anvendes på `f(psi) = -i*H*psi/hbar` med

```text
k1 = f(psi)
k2 = f(psi + dt*k1/2)
k3 = f(psi + dt*k2/2)
k4 = f(psi + dt*k3)
psi_ny = psi + dt*(k1 + 2*k2 + 2*k3 + k4)/6
```

For en energimodus er RK4s stabilitetskrav `|E*dt/hbar| <= sqrt(8)`.
Implementasjonen bruker en øvre grense på energienes absoluttverdier;
en avvisning er dermed et konservativt sikkerhetskriterium.
Se [forelesningsnotater fra University of Illinois](https://research.physics.illinois.edu/ElectronicStructure/498CQM/lnotes/lec5.html)
om unitær Schrödinger-utvikling og Crank–Nicolson, og
[Utrecht-notater om RK-stabilitet](https://webspace.science.uu.nl/~frank011/Classes/numwisk/ch10.pdf).

## Et lite eksempel man kan lese fra start til slutt

[`examples/compare_1d_methods.py`](../examples/compare_1d_methods.py) viser
initialtilstand, Hamilton-operator, begge tidsmetoder og måling i én fil.
Det er selvstendig undervisningskode med norske kommentarer, uten den
generelle konfigurasjonen og GUI-et. Det endrer ikke produksjonsløseren.

```powershell
& '.\.venv\Scripts\python.exe' examples/compare_1d_methods.py --method both
```

Eksemplet bruker hbar=m=1, p=2, x0=-3 og T=1. Kontinuumløsningen har
`<x>(T)=-1`. Begge metoder bruker samme rutenett og sluttid. PNG og JSON
lagres i `outputs/teaching/`, uten at et vindu åpnes. Prøv `--dt 0.001` og
sammenlikn med standardens 0.002. Romfeilen kan dominere når dt er liten.

En lokal kjøring ga `<x>(1)=-1.023249` med Crank–Nicolson og `-1.023215`
med RK4. Ved halvert dt ble verdiene `-1.023224` og `-1.023215`.
At begge blir liggende nær -1.0232 i stedet for kontinuumverdien -1 viser
at mindre tidssteg alene ikke fjerner romfeilen i dette lille eksemplet.

## Finn frem i produksjonskoden

| Fil | Spørsmål den besvarer |
|---|---|
| `states.py` | Hvordan bygges og normaliseres initialbølgen? |
| `potentials.py` | Hvor ligger potensialet og de utelukkede veggpunktene? |
| `solvers.py` | Hvordan utvikles bølgen, og hvordan måles absorberens tap? |
| `dirichlet.py` | Hvordan deles en rutenettlinje ved vegger og utvikles med sinus? |
| `diagnostics.py` | Hvordan regnes sannsynlighet og forventningsverdier? |
| `config.py` | Hvilke parametere, avledede størrelser og gyldighetskrav brukes? |
| `cli.py` | Hvordan blir kommandolinjevalg til et forsøk og en eksport? |
| `visualization.py` | Hvordan vises lagrede resultater? |

Filene ligger i `src/schroedinger/`. Begynn gjerne med undervisningseksemplet,
deretter `states.py`, `potentials.py` og hovedløkken i `solvers.py`.
De gamle `1d/`- og `2d/`-mappene er kompatibilitetslag rundt denne pakken.

## Undersøk standardens dobbeltspalte

[`examples/double_slit_sensitivity.py`](../examples/double_slit_sensitivity.py)
varierer dt, rutenett, boksstørrelse og absorber ved samme fysiske tid.
Koden beholder bare initial- og sluttbildet og kjører ett forsøk om gangen.
Hele undersøkelsen tar lengre tid enn én demonstrasjon.

```powershell
& '.\.venv\Scripts\python.exe' examples/double_slit_sensitivity.py
# Et mindre utvalg:
& '.\.venv\Scripts\python.exe' examples/double_slit_sensitivity.py --cases baseline dt_half
```

Se [måleoppsett, resultater og begrensninger](SENSITIVITY.md).
Undersøkelsen gjelder et tidlig øyeblikksbilde, ikke alle senere tider eller
andre bølgepakker. Testene erstatter ikke en slik følsomhetsundersøkelse.

[Oppfølgingsforsøkene](GRID_DIFFERENCE.md) viser hvorfor det opprinnelige
profilavviket var så stort: rutenettene representerte ulike spalteåpninger.
På samme finere rutenett gir de to geometriene omtrent 19,9% forskjell.
Med samme interne randkoordinater er de undersøkte forskjellene rundt
1–3%. Det er derfor viktig å skille romoppløsning fra endret geometri.
