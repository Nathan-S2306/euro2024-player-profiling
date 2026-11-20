"""Euro 2024 player profiling: core analysis (also used to build the notebook)."""
import json, math, os, sys
from pathlib import Path
import numpy as np, pandas as pd

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("outputs")
OUT.mkdir(exist_ok=True)

# ---------- 1. load ----------
matches = json.load(open(DATA / "matches/55/282.json"))
def mmss(s):
    m, sec = s.split(":"); return int(m) + int(sec) / 60

events, lineups = {}, {}
for m in matches:
    mid = m["match_id"]
    events[mid] = json.load(open(DATA / f"events/{mid}.json"))
    lineups[mid] = json.load(open(DATA / f"lineups/{mid}.json"))

# ---------- 2. minutes and main position ----------
rows = []
for mid, teams in lineups.items():
    end_min = max(e["minute"] + e["second"] / 60 for e in events[mid])
    for team in teams:
        for p in team["lineup"]:
            for pos in p["positions"]:
                start = mmss(pos["from"])
                stop = mmss(pos["to"]) if pos["to"] else end_min
                rows.append({"match_id": mid, "player_id": p["player_id"],
                             "player": p.get("player_nickname") or p["player_name"],
                             "team": team["team_name"], "position": pos["position"],
                             "minutes": max(stop - start, 0)})
stints = pd.DataFrame(rows)
mins = stints.groupby(["player_id", "player", "team"], as_index=False)["minutes"].sum()
main_pos = (stints.groupby(["player_id", "position"])["minutes"].sum()
            .reset_index().sort_values("minutes", ascending=False)
            .drop_duplicates("player_id")[["player_id", "position"]])
players = mins.merge(main_pos, on="player_id")

GROUPS = {
    "Centre-back": ["Center Back", "Left Center Back", "Right Center Back"],
    "Full-back": ["Left Back", "Right Back", "Left Wing Back", "Right Wing Back"],
    "Midfielder": ["Center Defensive Midfield", "Left Defensive Midfield", "Right Defensive Midfield",
                   "Center Midfield", "Left Center Midfield", "Right Center Midfield",
                   "Center Attacking Midfield", "Left Attacking Midfield", "Right Attacking Midfield"],
    "Winger": ["Left Wing", "Right Wing", "Left Midfield", "Right Midfield"],
    "Striker": ["Center Forward", "Left Center Forward", "Right Center Forward", "Secondary Striker"],
}
pos_to_group = {p: g for g, ps in GROUPS.items() for p in ps}
players["group"] = players["position"].map(pos_to_group)  # goalkeepers become NaN

# ---------- 3. per-player event counts ----------
GOAL = (120, 40)
def dist(loc): return math.hypot(GOAL[0] - loc[0], GOAL[1] - loc[1])
def progressive(start, end):
    """Moves the ball at least 25% closer to the centre of the opponent's goal."""
    return dist(end) <= 0.75 * dist(start)
def in_box(loc): return loc[0] >= 102 and 18 <= loc[1] <= 62

stats = {}
def add(pid, key, val=1):
    stats.setdefault(pid, {}); stats[pid][key] = stats[pid].get(key, 0) + val

for mid, evs in events.items():
    by_id = {e["id"]: e for e in evs}
    for e in evs:
        if "player" not in e: continue
        pid, t = e["player"]["id"], e["type"]["name"]
        loc = e.get("location")
        if t == "Pass":
            pa = e["pass"]
            if pa.get("type", {}).get("name") in ("Throw-in", "Corner", "Free Kick", "Kick Off", "Goal Kick"):
                continue  # open-play passes only
            add(pid, "passes_attempted")
            if "outcome" not in pa:  # no outcome = completed
                add(pid, "passes_completed")
                end = pa["end_location"]
                if progressive(loc, end): add(pid, "progressive_passes")
                if loc[0] < 80 <= end[0]: add(pid, "passes_into_final_third")
                if in_box(end) and not in_box(loc): add(pid, "passes_into_box")
            if pa.get("shot_assist") or pa.get("goal_assist"): add(pid, "key_passes")
        elif t == "Carry":
            end = e["carry"]["end_location"]
            if progressive(loc, end) and dist(loc) - dist(end) >= 5: add(pid, "progressive_carries")
        elif t == "Shot":
            sh = e["shot"]
            if sh["type"]["name"] == "Penalty": continue
            add(pid, "shots"); add(pid, "npxg", sh["statsbomb_xg"])
            if sh["outcome"]["name"] == "Goal": add(pid, "np_goals")
            kp = sh.get("key_pass_id")
            if kp and kp in by_id and "player" in by_id[kp]:
                add(by_id[kp]["player"]["id"], "xa", sh["statsbomb_xg"])
        elif t == "Dribble":
            if e["dribble"]["outcome"]["name"] == "Complete": add(pid, "dribbles_completed")
        elif t == "Pressure":
            add(pid, "pressures")
            if loc and loc[0] >= 80: add(pid, "pressures_final_third")
            if e.get("counterpress"): add(pid, "counterpresses")
        elif t == "Duel" and e["duel"]["type"]["name"] == "Tackle":
            if e["duel"].get("outcome", {}).get("name") in ("Won", "Success", "Success In Play", "Success Out"):
                add(pid, "tackles_won")
        elif t == "Interception":
            if e["interception"]["outcome"]["name"] in ("Won", "Success", "Success In Play", "Success Out"):
                add(pid, "interceptions")
        elif t == "Ball Recovery":
            if not e.get("ball_recovery", {}).get("recovery_failure"): add(pid, "ball_recoveries")
        elif t == "Clearance":
            add(pid, "clearances")

counts = pd.DataFrame.from_dict(stats, orient="index").fillna(0)
counts.index.name = "player_id"
df = players.merge(counts.reset_index(), on="player_id", how="left")
df[list(counts.columns)] = df[list(counts.columns)].fillna(0)

# ---------- 4. per 90 and filter ----------
MIN_MINUTES = 270  # three full matches
COUNT_COLS = [c for c in counts.columns if c != "passes_attempted"]
df = df[(df["minutes"] >= MIN_MINUTES) & df["group"].notna()].copy()
df["pass_completion"] = df["passes_completed"] / df["passes_attempted"].replace(0, np.nan)
for c in COUNT_COLS:
    df[c + "_p90"] = df[c] / df["minutes"] * 90
df["tackles_interceptions_p90"] = df["tackles_won_p90"] + df["interceptions_p90"]

METRICS = ["passes_completed_p90", "pass_completion", "progressive_passes_p90", "progressive_carries_p90",
           "passes_into_final_third_p90", "passes_into_box_p90", "key_passes_p90", "xa_p90",
           "shots_p90", "npxg_p90", "dribbles_completed_p90", "pressures_p90", "pressures_final_third_p90",
           "counterpresses_p90", "tackles_interceptions_p90", "ball_recoveries_p90", "clearances_p90"]

# ---------- 5. percentiles within position group ----------
for m in METRICS:
    df[m + "_pct"] = df.groupby("group")[m].rank(pct=True) * 100

ROLES = {
    "Centre-back": {"Ball-playing": ["progressive_passes_p90", "passes_completed_p90", "pass_completion"],
                    "Defending": ["tackles_interceptions_p90", "clearances_p90", "ball_recoveries_p90"]},
    "Full-back": {"Progressor": ["progressive_passes_p90", "progressive_carries_p90", "passes_into_final_third_p90"],
                  "Attacking": ["key_passes_p90", "xa_p90", "passes_into_box_p90"],
                  "Defending": ["tackles_interceptions_p90", "pressures_p90", "ball_recoveries_p90"]},
    "Midfielder": {"Deep playmaker": ["passes_completed_p90", "progressive_passes_p90", "pass_completion"],
                   "Ball winner": ["tackles_interceptions_p90", "pressures_p90", "ball_recoveries_p90"],
                   "Attacking": ["key_passes_p90", "xa_p90", "npxg_p90", "progressive_carries_p90"]},
    "Winger": {"Creator": ["key_passes_p90", "xa_p90", "passes_into_box_p90"],
               "Carrier": ["progressive_carries_p90", "dribbles_completed_p90"],
               "Goal threat": ["npxg_p90", "shots_p90"],
               "Presser": ["pressures_final_third_p90", "counterpresses_p90"]},
    "Striker": {"Goal threat": ["npxg_p90", "shots_p90"],
                "Link-up": ["key_passes_p90", "xa_p90", "passes_completed_p90"],
                "Presser": ["pressures_final_third_p90", "counterpresses_p90"]},
}
role_rows = []
for _, r in df.iterrows():
    for role, ms in ROLES[r["group"]].items():
        role_rows.append({"player": r["player"], "team": r["team"], "group": r["group"], "role": role,
                          "score": np.mean([r[m + "_pct"] for m in ms])})
roles = pd.DataFrame(role_rows)

# ---------- 6. similar players (cosine similarity on z-scores within group) ----------
def similar(player, n=5):
    row = df[df["player"] == player].iloc[0]
    g = df[df["group"] == row["group"]]
    z = (g[METRICS] - g[METRICS].mean()) / g[METRICS].std(ddof=0)
    z = z.fillna(0)
    v = z.loc[row.name].values
    sims = z.values @ v / (np.linalg.norm(z.values, axis=1) * np.linalg.norm(v) + 1e-9)
    out = g.assign(similarity=sims)[["player", "team", "position", "minutes", "similarity"]]
    return out[out["player"] != player].sort_values("similarity", ascending=False).head(n)

if __name__ == "__main__":
    df.round(3).to_csv(OUT / "players_per90.csv", index=False)
    roles.round(1).to_csv(OUT / "role_scores.csv", index=False)
    print("players kept:", len(df)); print(df["group"].value_counts().to_dict())
    for g in ROLES:
        top = roles[roles.group == g].sort_values("score", ascending=False).groupby("role").head(3)
        print("\n", g); print(top.sort_values(["role", "score"], ascending=[True, False]).to_string(index=False))
    print("\nSimilar to Rodri:"); print(similar("Rodri").to_string(index=False))
