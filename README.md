# Euro 2024 Player Profiling

**What a coach would ask:** for each position, which players stand out at the jobs that position does? And if we lose a player, who has a similar profile?

This project uses event data from all 51 matches of UEFA Euro 2024 to answer both questions. That's about 188,000 events, each with a pitch location.

## What it does
1. **Minutes and positions:** works out each player's minutes from line-up position spells. Each player gets one main position, which places him in one of five groups: centre-back, full-back, midfielder, winger or striker.
2. **Action counts:** counts 17 actions per 90 minutes, covering passing, progression, chance creation, shooting, pressing and defending. Only open-play passes are counted.
3. **Percentiles:** ranks every player only against his own position group, and only players with at least 270 minutes are included.
4. **Role scores:** combines related percentiles into role scores, such as Deep playmaker, Ball winner, Creator and Presser.
5. **Similar players:** finds similar players with cosine similarity on z-scores.
6. **Outputs:** exports Power BI-ready tables and draws player profile and comparison charts.

## Key definitions
| Metric | Definition |
|---|---|
| Progressive pass/carry | Ends at least 25% closer to the centre of the opponent's goal. Carries must also gain at least 5 units. |
| xA | xG of the shot a pass created, credited to the passer |
| npxG | Expected goals excluding penalties |
| Passes into box | Completed passes ending in the penalty area that started outside it |

## Setup
```
pip install -r requirements.txt
jupyter notebook euro2024_player_profiling.ipynb
```

## Files
- `euro2024_player_profiling.ipynb` is the explained walkthrough. Start here. The first cell downloads the data.
- `analysis.py` is the same analysis as a script: `python analysis.py data outputs`.
- `charts.py` draws the profile and scatter charts.
- `outputs/players_per90.csv` is one row per player, with every metric and percentile.
- `outputs/role_scores.csv` is one row per player per role, in long format for Power BI slicers.

## Limitations
- **Small sample:** one tournament, with at most 7 matches per player.
- **No adjustments:** there's no adjustment for opponent strength or game state.
- **Coarse percentiles:** small groups (16 strikers, 20 wingers) move in big steps.
- **Off-ball work isn't captured:** event data misses positioning and runs.
- **Judgement calls:** the role definitions are my own choices, made to be discussed with coaches.

## Data
Data provided by [StatsBomb](https://github.com/statsbomb/open-data) (Hudl StatsBomb open data), used under their free data licence with attribution.
