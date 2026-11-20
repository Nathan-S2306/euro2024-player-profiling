import sys, importlib.util
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
spec = importlib.util.spec_from_file_location("analysis", "analysis.py")
sys.argv = ["analysis.py", sys.argv[1], sys.argv[2]]
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
df, OUT = A.df, A.OUT
print("total events:", sum(len(v) for v in A.events.values()))

LABELS = {"passes_completed_p90": "Passes completed", "pass_completion": "Pass completion %",
  "progressive_passes_p90": "Progressive passes", "progressive_carries_p90": "Progressive carries",
  "passes_into_final_third_p90": "Passes into final third", "passes_into_box_p90": "Passes into box",
  "key_passes_p90": "Key passes", "xa_p90": "xA (expected assists)", "shots_p90": "Shots",
  "npxg_p90": "Non-penalty xG", "dribbles_completed_p90": "Dribbles completed",
  "pressures_p90": "Pressures", "pressures_final_third_p90": "Pressures in final third",
  "counterpresses_p90": "Counter-presses", "tackles_interceptions_p90": "Tackles + interceptions",
  "ball_recoveries_p90": "Ball recoveries", "clearances_p90": "Clearances"}
SECTIONS = [("In possession", ["passes_completed_p90", "pass_completion", "progressive_passes_p90",
             "progressive_carries_p90", "passes_into_final_third_p90"]),
            ("Chance creation & threat", ["passes_into_box_p90", "key_passes_p90", "xa_p90",
             "dribbles_completed_p90", "shots_p90", "npxg_p90"]),
            ("Out of possession", ["pressures_p90", "pressures_final_third_p90", "counterpresses_p90",
             "tackles_interceptions_p90", "ball_recoveries_p90"])]
COLS = ["#2B6CB0", "#C05621", "#2F855A"]

def profile(player, path):
    r = df[df.player == player].iloc[0]
    fig, ax = plt.subplots(figsize=(8, 7.5))
    y, ticks, labels = 0, [], []
    for (title, ms), col in zip(SECTIONS, COLS):
        ax.text(-2, y - 0.2, title.upper(), fontsize=9, fontweight="bold", color=col, ha="left")
        y -= 1
        for m in ms:
            v = r[m + "_pct"]
            ax.barh(y, v, color=col, alpha=0.85, height=0.7)
            ax.text(v + 1.5, y, f"{v:.0f}", va="center", fontsize=9)
            ticks.append(y); labels.append(LABELS[m]); y -= 1
        y -= 0.4
    ax.set_yticks(ticks, labels, fontsize=9)
    ax.set_xlim(0, 105); ax.set_xlabel(f"Percentile vs {r['group'].lower()}s at Euro 2024 (min {A.MIN_MINUTES} mins)")
    ax.axvline(50, color="#888", lw=0.8, ls="--")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.set_title(f"{player} ({r['team']}), {r['position']}\n{r['minutes']:.0f} minutes, per-90 percentiles",
                 fontsize=12, loc="left")
    fig.text(0.01, 0.005, "Data: StatsBomb open data, UEFA Euro 2024", fontsize=7, color="#666")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)

def scatter(group, x, y, path, label_top=8):
    g = df[df.group == group]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(g[x], g[y], s=40, color="#2B6CB0", alpha=0.7)
    ax.axvline(g[x].median(), color="#999", lw=0.8, ls="--"); ax.axhline(g[y].median(), color="#999", lw=0.8, ls="--")
    lab = g.assign(s=g[x].rank() + g[y].rank()).sort_values("s", ascending=False).head(label_top)
    for _, r in lab.iterrows(): ax.annotate(r.player, (r[x], r[y]), fontsize=8, xytext=(4, 3), textcoords="offset points")
    ax.set_xlabel(LABELS[x] + " per 90"); ax.set_ylabel(LABELS[y] + " per 90")
    ax.set_title(f"{group}s at Euro 2024: {LABELS[x]} vs {LABELS[y]}", loc="left")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.text(0.01, 0.005, "Data: StatsBomb open data. Dashed lines = group median.", fontsize=7, color="#666")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)

profile("Lamine Yamal", OUT / "example_profile_lamine_yamal.png")
scatter("Full-back", "progressive_passes_p90", "xa_p90", OUT / "fullbacks_progression_vs_creation.png")
print("charts saved")
