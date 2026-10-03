"""Figure: life expectancy at birth and at age 65, men vs. women."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to file, no screen needed
import matplotlib.pyplot as plt
import pandas as pd

COLORS = {"Men": "#2a78d6", "Women": "#eb6834"}
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

PANELS = [(0, "At birth"), (65, "At age 65")]


def plot_life_expectancy(df: pd.DataFrame, out_path: Path, source_note: str) -> Path:
    first, last = df["year"].min(), df["year"].max()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), facecolor=SURFACE)

    for ax, (age, title) in zip(axes, PANELS):
        ax.set_facecolor(SURFACE)
        panel = df[df["age"] == age]

        for sex, color in COLORS.items():
            series = panel[panel["sex"] == sex]
            ax.plot(series["year"], series["life_expectancy"], color=color,
                    linewidth=2, label=sex)
            # Direct label at the end of each line
            end = series.iloc[-1]
            ax.annotate(f"{sex} {end['life_expectancy']:.1f}",
                        xy=(end["year"], end["life_expectancy"]),
                        xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=9, color=TEXT_PRIMARY)

        ax.set_title(title, loc="left", fontsize=11, color=TEXT_PRIMARY, pad=8)
        ax.set_ylabel("Remaining years", fontsize=9, color=TEXT_SECONDARY)
        ax.set_xlim(first, last + 7)  # room for end labels
        ax.set_xticks([y for y in range(1990, last + 1, 10)])
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.tick_params(colors=TEXT_SECONDARY, labelsize=9, length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)

    axes[0].legend(frameon=False, fontsize=9, loc="upper left", labelcolor=TEXT_SECONDARY)

    fig.suptitle(f"Life expectancy in Norway, {first}–{last}",
                 x=0.06, y=0.97, ha="left", fontsize=14, color=TEXT_PRIMARY, fontweight="bold")
    fig.text(0.06, 0.02, source_note, fontsize=8, color=TEXT_SECONDARY)
    fig.tight_layout(rect=(0.03, 0.05, 1, 0.93))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path
