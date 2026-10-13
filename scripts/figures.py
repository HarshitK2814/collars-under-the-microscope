"""Figures for the write-up, from results/ files only (never recomputes a result).

    python scripts/figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from collars.config import RESULTS  # noqa: E402

FIG, TAB, RUNS = RESULTS / "figures", RESULTS / "tables", RESULTS / "runs"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "font.size": 10,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "legend.frameon": False,
})


def fan(period: str = "test") -> None:
    navs = pd.read_parquet(RUNS / f"{period}_navs_fixed.parquet")
    navs.columns = navs.columns.astype(int)
    lad = pd.DataFrame({phi: navs[[phi, phi + 21, phi + 42]].mean(axis=1) for phi in range(21)})
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(navs.index, navs.values, color="#b9b8b2", lw=0.6, alpha=0.7)
    ax.fill_between(lad.index, lad.min(axis=1), lad.max(axis=1), color=ORANGE, alpha=0.35, lw=0,
                    label="Range of the 21 three-tranche ladders")
    ax.plot(navs.index, navs[0], color=BLUE, lw=2, label="Fund's calendar (phase 0)")
    ax.plot([], [], color="#b9b8b2", lw=1, label="63 single-tranche reset phases")
    ax.set_title(f"Same rule, different reset day: growth of $1, {period} period 2020–2023")
    ax.set_ylabel("Growth of $1")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / f"fan_{period}.png", dpi=160)
    plt.close(fig)


def by_phase(period: str = "test") -> None:
    t = pd.read_csv(TAB / f"{period}_phases_fixed.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    colors = [BLUE if i == 0 else "#9fb9dc" for i in t.index]
    ax.bar(t.index, t["ann_return"] * 100, color=colors, width=0.8)
    ax.axhline(t["ann_return"].mean() * 100, color=INK2, lw=1, ls="--")
    ax.annotate("phase 0 = fund's quarter-end calendar", (0, t.loc[0, "ann_return"] * 100),
                xytext=(6, t["ann_return"].max() * 100 + 0.3), color=INK2, fontsize=9,
                arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.8})
    ax.set_xlabel("Reset phase (trading days after quarter-end)")
    ax.set_ylabel("Annualised return, %")
    ax.set_title("Annualised return of the collar by reset day, 2020–2023")
    ax.set_ylim(0, t["ann_return"].max() * 100 + 1.5)
    fig.tight_layout()
    fig.savefig(FIG / f"by_phase_{period}.png", dpi=160)
    plt.close(fig)


def dispersion() -> None:
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for k, per in enumerate(("development", "validation", "test")):
        s = pd.read_csv(TAB / f"{per}_phases_fixed.csv", index_col=0)["ann_return"] * 100
        l = pd.read_csv(TAB / f"{per}_ladders.csv", index_col=0)["ann_return"] * 100
        ax.scatter([k - 0.15] * len(s), s, color=BLUE, s=12, alpha=0.6, label="Single tranche (63 phases)" if k == 0 else None)
        ax.scatter([k + 0.15] * len(l), l, color=ORANGE, s=12, alpha=0.8, label="Three-tranche ladder (21)" if k == 0 else None)
    ax.set_xticks([0, 1, 2], ["Development\n2011–16", "Validation\n2017–19", "Test\n2020–23"])
    ax.set_ylabel("Annualised return, %")
    ax.set_title("Timing-luck dispersion: single tranche vs ladder")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "dispersion.png", dpi=160)
    plt.close(fig)


def nport_caps() -> None:
    frames = [pd.read_csv(TAB / f"nport_strikes_{p}.csv") for p in ("development_validation", "test", "recent")
              if (TAB / f"nport_strikes_{p}.csv").exists()]
    t = pd.concat(frames)
    t["period"] = pd.to_datetime(t["period"])
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(t["period"], t["cap"] * 100, color=BLUE, lw=2, marker="o", ms=5, label="Fund's actual cap (N-PORT)")
    ax.plot(t["period"], t["model_cap"] * 100, color=ORANGE, lw=2, marker="s", ms=5, label="Model (free-data surface)")
    ax.axhspan(3.5, 5.5, color=GRID, alpha=0.6, lw=0, label="Cap band in the 2025 prospectus")
    ax.set_ylabel("Call strike above index, %")
    ax.set_title("Upside cap per quarter: model vs the fund's reported strikes")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "nport_caps.png", dpi=160)
    plt.close(fig)


def attribution(period: str = "test") -> None:
    a = pd.read_csv(TAB / f"{period}_attribution_phase0.csv", index_col=0).drop("all_legs")
    cols = {"delta": "Delta", "gamma_theta_vrp": "Gamma + theta (VRP)", "vega": "Vega"}
    names = {"long_put": "Long 95% put", "short_put": "Short 80% put", "short_call": "Short call"}
    a = a.loc[list(names)]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    w = 0.25
    for j, (c, lab) in enumerate(cols.items()):
        ax.bar([i + (j - 1) * w for i in range(3)], a[c], width=w - 0.02, color=[BLUE, ORANGE, AQUA][j], label=lab)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(range(3), [names[i] for i in a.index])
    ax.set_ylabel("% of index per year")
    ax.set_title("Where the collar's option P&L comes from, 2020–2023 (phase 0)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / f"attribution_{period}.png", dpi=160)
    plt.close(fig)


def fund_tracking(period: str = "test") -> None:
    b = pd.read_parquet(RUNS / f"{period}_benchmark_navs.parquet")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for col, c, lab in (("collar_phase0", BLUE, "Reconstructed collar (phase 0)"),
                        ("JHEQX_nav", ORANGE, "Fund NAV, total return (JHEQX)"),
                        ("spx_tr", "#8a8984", "S&P 500 total return")):
        if col in b:
            ax.plot(b.index, b[col], color=c, lw=2 if col != "spx_tr" else 1.2, label=lab)
    ax.set_ylabel("Growth of $1")
    ax.set_title("The reconstruction vs the real fund, 2020–2023")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / f"fund_tracking_{period}.png", dpi=160)
    plt.close(fig)


def real_chain() -> None:
    import json
    t = pd.read_csv(TAB / "posthoc_real_chain_iv.csv")
    meta = json.loads((RUNS / "posthoc_real_chain.json").read_text())
    fig, ax = plt.subplots(figsize=(8, 4.0))
    ax.scatter(t["mny"] * 100, t["iv_real"] * 100, color=BLUE, s=14, alpha=0.7, label="Real Cboe SPX chain")
    ax.scatter(t["mny"] * 100, t["iv_model"] * 100, color=ORANGE, s=10, alpha=0.7, label="Free-data surface (frozen 2011–16)")
    ax.set_xlabel("Strike ÷ spot, %")
    ax.set_ylabel("Implied volatility, %")
    ax.set_title(f"Free surface vs a real option chain, {meta['days']}-day SPX, {meta['as_of']}")
    ax.annotate(f"{meta['n_strikes_compared']} strikes · mean error {meta['iv_mae_volpts']} vol pts",
                (0.02, 0.04), xycoords="axes fraction", color=INK2, fontsize=9)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG / "real_chain_smile.png", dpi=160)
    plt.close(fig)


def sister_navs() -> None:
    f = RUNS / "posthoc_sister_navs.parquet"
    if not f.exists():
        return
    b = pd.read_parquet(f)
    names = {"HE1": "Fund (Dec/Mar/Jun/Sep)", "HE2": "Fund 2 (Jan/Apr/Jul/Oct)", "HE3": "Fund 3 (Feb/May/Aug/Nov)"}
    cols = [BLUE, ORANGE, AQUA]
    fig, ax = plt.subplots(figsize=(8, 4.0))
    for k, (f_, lab) in enumerate(names.items()):
        ax.plot(b.index, b[f"{f_}_nav"], color=cols[k], lw=2, label=lab + " — NAV")
        ax.plot(b.index, b[f"{f_}_model"], color=cols[k], lw=1, ls="--", alpha=0.7)
    ax.plot([], [], color=INK2, lw=1, ls="--", label="our reconstruction (dashed)")
    ax.set_ylabel("Growth of $1")
    ax.set_title("The fund family's own ladder: three funds, three reset calendars")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "sister_funds.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (fan, by_phase, dispersion, nport_caps, attribution, fund_tracking, real_chain, sister_navs):
        try:
            f()
            print("ok", f.__name__)
        except FileNotFoundError as e:
            print("skip", f.__name__, e)
