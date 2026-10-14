# Regression: who is most likely to be seriously hurt?

**Question:** When someone is injured in a crash in San Diego, what raises the chance that the injury is serious or fatal?

- **Rows:** one per person in a collision, 2018–2025, whose injury level was recorded. That is 38,230 people, and 2,033 of them (5.3%) were seriously hurt or killed.
- **Y:** `serious_or_fatal`. It is 1 for a serious, severe or fatal injury and 0 for a minor injury.
- **Method:** logistic regression, the standard tool when Y is yes/no. Standard errors are clustered by police beat, because people in the same beat share the beat-level inputs.

## Run it

Build the beat inputs first (see `analysis/correlation/serious_or_fatal/README.md`), then:

```
python3 analysis/regression/serious_or_fatal/logistic_regression.py
```

## Outputs

| File | What it is |
|------|------------|
| `odds_ratios.png` | Chart of each input's odds ratio with its 95% confidence interval |
| `odds_ratios.csv` | The same numbers |
| `model_summary.txt` | Full model output, fit checks, overlap check (VIF), and the fatal-only version |

## How to read an odds ratio

- **1 means no effect.**
- **Above 1 means higher odds:** 2.0 doubles the odds of a serious/fatal injury.
- **Below 1 means lower odds:** 0.5 halves them.
- Each number holds every other input in the model constant.

## Inputs and why each is in the model

| Input | From | Why |
|-------|------|-----|
| Road-user type (driver, passenger, pedestrian, bicyclist, motorcyclist, other) | Our data | The project's main question. Drivers are the comparison group. |
| Truck or bus involved | Our data | Heavier vehicles transfer more force |
| Night (8pm–6am) | Our data | Darkness, faster driving, fatigue |
| Weekend | Our data | Different trips and more leisure driving |
| Cause: unsafe speed (VC 22350) | Our data | Speed is a known cause of severe injury |
| Cause: DUI (VC 23152/23153) | Our data | Impaired drivers crash harder |
| Hit-and-run (VC 20001/20002) | Our data | Help may arrive later |
| Year 2020 | Our data | COVID: emptier roads, faster driving |
| Population density of the beat | Census ACS | Strongest finding in the correlation step |
| Mean speed limit of the beat | SANDAG roads | A direct measure of how fast the roads are |
| Median income of the beat | Census ACS | Research links lower income to more pedestrian deaths |

These were chosen from the project question and road-safety research. The correlation step was used only to drop look-alike inputs, such as beat area and transit stops, which duplicate density.

## Results

| Input | Odds ratio | Meaning |
|-------|-----------:|---------|
| Pedestrian | **9.3** | About 9 times the odds of a driver |
| Motorcyclist | **8.6** | |
| Bicyclist | **4.9** | |
| DUI | **2.5** | |
| Night | **2.1** | |
| Truck or bus involved | **1.6** | |
| Weekend | **1.2** | |
| Population density, per +1,000 people/sq mi | **0.96** | Denser beats have slightly lower odds |
| Hit-and-run | **0.23** | See caveats |
| Passenger, other road user, unsafe speed, 2020, speed limit, income | not significant | |

- **The fatal-only model** (Y = killed) tells the same story. Pedestrians come out even higher at 12, and night rises to 3.
- **Fit:** AUC is 0.78. AUC runs from 0.5 (a coin flip) to 1 (perfect), so the model ranks who gets seriously hurt fairly well.
- **Overlap check:** every VIF is below 1.5, so the inputs don't overlap.

## Caveats

- **Hit-and-run 0.23 doesn't mean fleeing protects anyone.** 88% of the hit-and-run cases with a known injury carry code 20002, which is the property-damage hit-and-run charge, so these are mostly low-harm crashes by how they were coded.
- **Unsafe speed isn't significant.** VC 22350 is "too fast for conditions," which officers often use for rear-end crashes in slow traffic. It's not the same as high speed.
- **No age or sex.** The dataset doesn't have them, and both matter a lot for injury severity.
- **Y is "how severe, given someone was hurt."** Blank injury levels most likely mean no injury, so they're left out.
- **This shows association, not proof of cause.**
