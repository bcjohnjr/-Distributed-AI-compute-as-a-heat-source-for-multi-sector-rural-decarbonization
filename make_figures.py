#!/usr/bin/env python3
"""Regenerates Figures 1–5 from jiloca_ghg_model.py. Paths are relative to this file."""
import os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import jiloca_ghg_model as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures"); os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
                     "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "pdf.fonttype": 42, "ps.fonttype": 42,
                     "axes.spines.top": False, "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans", "mathtext.it": "Liberation Sans:italic", "mathtext.bf": "Liberation Sans:bold", "axes.spines.right": False, "axes.edgecolor": "#8a8986", "axes.linewidth": 0.6,
                     "xtick.color": "#52514e", "ytick.color": "#52514e", "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b"})
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK2, MUTED, GRID, SURF = "#52514e", "#8a8986", "#e4e3df", "#fcfcfb"
MM = 1 / 25.4
v = M.evaluate()


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), dpi=450, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def panel(ax, letter):
    ax.text(-0.02, 1.04, letter, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom", ha="right")


# ---------------------------------------------------------------- Figure 1: corridor and heat cascade
def fig1():
    fig = plt.figure(figsize=(183 * MM, 92 * MM))
    ax = fig.add_axes([0.02, 0.06, 0.40, 0.88])
    lat0 = 40.68
    xs = [n[5] for n in M.NODES]; ys = [n[4] for n in M.NODES]
    ax.plot(xs, ys, color=MUTED, lw=1.0, zorder=1, solid_capstyle="round")
    for n in M.NODES:
        r = (2.2 + 2.6 * math.sqrt(n[2])) * (1.9 if n[0].startswith("Singra") else 1.0)
        star = n[0].startswith("Singra")
        ax.scatter(n[5], n[4], s=r ** 2, color=ORANGE if star else BLUE, edgecolor="white", linewidth=0.8, zorder=3, marker="*" if star else "o")
    ax.set_aspect(1 / math.cos(math.radians(lat0)))
    lab = {"Cella": (8, -2, "left"), "Villarquemado": (8, -2, "left"), "Santa Eulalia del Campo": (-8, -2, "right"),
           "Torremocha–Torrelacárcel–Alba (shared node)": (8, -3, "left"), "Singra (prototype)": (8, 0, "left"),
           "Villafranca del Campo": (-8, 0, "right"), "Monreal del Campo": (-9, 0, "right"), "Torrijo del Campo": (9, -4, "left"),
           "Caminreal": (-9, 2, "right"), "Fuentes Claras": (-8, 3, "right"), "Calamocha": (9, 0, "left")}
    for n in M.NODES:
        dx, dy, ha = lab[n[0]]
        nm = n[0].replace(" (shared node)", "").replace(" (prototype)", " (prototype)")
        ax.annotate(f"{nm}\n{n[2]:.2f} MW · {n[1]:,} res.", (n[5], n[4]), xytext=(dx, dy), textcoords="offset points",
                    ha=ha, va="center", fontsize=5.8, color="#0b0b0b")
    ax.set_xlim(-1.47, -1.13); ax.set_ylim(40.42, 40.95)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    # scale bar 10 km
    km_deg = 1 / (111.32 * math.cos(math.radians(lat0)))
    x0, y0 = -1.46, 40.435
    ax.plot([x0, x0 + 10 * km_deg], [y0, y0], color="#0b0b0b", lw=1.4)
    ax.text(x0 + 5 * km_deg, y0 + 0.006, "10 km", ha="center", fontsize=6)
    ax.annotate("N", xy=(-1.45, 40.945), xytext=(-1.45, 40.91), ha="center", fontsize=7, arrowprops=dict(arrowstyle="-|>", lw=0.8, color="#0b0b0b"))
    ax.set_title(f"{v['c_it_mw']:.2f} MW IT · {len(M.NODES)} nodes · {v['c_pop']:,.0f} residents", loc="left", fontsize=6.5, color=INK2)
    panel(ax, "a")

    # b: heat cascade, GWh/yr
    bx = fig.add_axes([0.53, 0.14, 0.45, 0.76])
    sinks = [("District heating, 4,934 homes (net of lift)", v["c_dh_useful_gwh"] - v["c_dh_lift_gwh"], BLUE),
             ("Alfalfa dehydration (leased line)", v["p_dry_alf_gwh"] - v["c_dry_alf_lift_gwh"], ORANGE),
             ("Aquaculture (RAS)", v["c_ras_heat_gwh"], AQUA),
             ("Glasshouses (42.9 ha)", v["c_glass_heat_gwh"], YELLOW),
             ("Other drying + bread proving", v["p_dry_other_gwh"] - v["c_dry_other_lift_gwh"] + v["c_proving_gwh"], MAGENTA),
             ("Rejected by dry coolers", v["c_heat_rejected_gwh"], "#c9c8c3")]
    tot = v["c_recoverable_gwh"]
    left = 0
    for nm, val, col in sinks:
        bx.barh(0, val, left=left, color=col, edgecolor="white", linewidth=1.0, height=0.5)
        left += val
    assert abs(left - tot) < 1e-6
    # legend-table with values
    for i, (nm, val, col) in enumerate(sinks):
        y = -0.75 - i * 0.33
        bx.add_patch(Rectangle((0, y - 0.1), 12, 0.2, color=col, clip_on=False))
        bx.text(18, y, nm.replace("\n", " "), va="center", fontsize=6.3)
        bx.text(tot, y, f"{val:,.1f} GWh  ({val / tot:.0%})", va="center", ha="right", fontsize=6.3)
    bx.set_ylim(-0.75 - 6 * 0.33, 0.45)
    bx.set_xlim(0, tot * 1.001)
    bx.set_yticks([]); bx.spines["left"].set_visible(False)
    bx.set_xlabel("Recoverable heat at the liquid loop (GWh yr$^{-1}$)")
    bx.set_title(f"{tot:,.0f} GWh yr$^{{-1}}$ recoverable; {v['c_heat_from_loop_gwh']:,.0f} GWh used; ERF {v['c_erf']:.1%}", loc="left", fontsize=7)
    panel(bx, "b")
    save(fig, "Figure_1_corridor_heat")


# ---------------------------------------------------------------- Figure 2: sector reference vs project
def fig2():
    rows = M.sector_table(v)
    A = [r for r in rows if r["boundary"] == "A"]; B = [r for r in rows if r["boundary"] == "B" and r["reference_t"] > 0]
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 80 * MM), gridspec_kw=dict(wspace=0.55))
    for ax, rs, title, letter, R, J in [(axes[0], A, "Boundary A — territorial", "a", "R_A", "J_A"), (axes[1], B, "Boundary B — value chain", "b", "R_B", "J_B")]:
        rs = sorted(rs, key=lambda r: r["reference_t"])
        y = range(len(rs)); h = 0.36
        ax.barh([i + h / 2 + 0.02 for i in y], [r["reference_t"] / 1000 for r in rs], height=h, color=ORANGE, label="Reference")
        ax.barh([i - h / 2 - 0.02 for i in y], [r["project_t"] / 1000 for r in rs], height=h, color=BLUE, label="Project")
        ax.set_yticks(list(y)); ax.set_yticklabels([r["sector"] for r in rs])
        mx = max(r["reference_t"] for r in rs) / 1000
        for i, r in enumerate(rs):
            pct = f"−{r['reduction_pct']:.0%}" if r["reduction_pct"] is not None and r["reduction_pct"] >= 0 else f"+{-r['reduction_pct']:.1%}"
            ax.text(max(r["reference_t"], r["project_t"]) / 1000 + mx * 0.02, i, pct, va="center", fontsize=6, color=INK2)
        ax.set_xlim(0, mx * 1.18)
        ax.set_xlabel("ktCO$_2$e yr$^{-1}$")
        ax.xaxis.grid(True, color=GRID, lw=0.5); ax.set_axisbelow(True)
        ax.set_title(f"{title}: {v[R]/1000:,.1f} → {v[J]/1000:,.1f} kt ({1 - v[J] / v[R]:.0%} lower)", loc="left")
        panel(ax, letter)
    axes[0].legend(loc="lower right", frameon=False)
    save(fig, "Figure_2_sectors")


# ---------------------------------------------------------------- Figure 3: attribution waterfall
def fig3():
    steps = [("Reference\n(A + B screen)", v["R_AB"], None),
             ("Household\nelectricity", -v["att_elec"], YELLOW),
             ("Programme\nmeasures", -v["att_prog"], AQUA),
             ("Recovered heat\ndisplacing fossil\nheat", -v["att_heatdisp"], ORANGE),
             ("Food-substitution\ncredit", -v["att_food"], MAGENTA),
             ("Compute network\npenalty", -v["att_compute"], BLUE),
             ("Project\n(A + B screen)", v["J_AB"], None)]
    fig, ax = plt.subplots(figsize=(183 * MM, 78 * MM))
    level = 0
    for i, (lab, val, col) in enumerate(steps):
        if col is None:
            ax.bar(i, val / 1000, color="#8a8986", width=0.62); top = val / 1000
            ax.text(i, top + 3, f"{val/1000:,.1f} kt", ha="center", fontsize=6.5)
            level = val / 1000
        else:
            new = level + val / 1000
            lo, hi = min(level, new), max(level, new)
            ax.bar(i, max(hi - lo, 0.4), bottom=lo, color=col, width=0.62, edgecolor="white", linewidth=0.8)
            ax.text(i, hi + 3, f"{val/1000:+,.1f}".replace("-", "−"), ha="center", fontsize=6.5)
            ax.plot([i - 0.69, i - 0.31], [level, level], color=MUTED, lw=0.5)
            level = new
    ax.plot([len(steps) - 1.69, len(steps) - 1.31], [level, level], color=MUTED, lw=0.5)
    ax.set_xticks(range(len(steps))); ax.set_xticklabels([s[0] for s in steps], fontsize=6.3)
    ax.set_ylabel("ktCO$_2$e yr$^{-1}$"); ax.yaxis.grid(True, color=GRID, lw=0.5); ax.set_axisbelow(True)
    ax.set_ylim(0, v["R_AB"] / 1000 * 1.1)
    ax.set_title(f"Only recovered-heat displacement requires distributed siting: {v['att_heatdisp']/1000:,.1f} kt yr$^{{-1}}$ ({v['c_heatdisp_kg_mwh_it']:.0f} kgCO$_2$e MWh$^{{-1}}$ IT); the network itself adds {-v['att_compute']/1000:.1f} kt", loc="left", fontsize=7)
    save(fig, "Figure_3_attribution")


# ---------------------------------------------------------------- Figure 4: joint scenarios + heat-policy metric sensitivity
def fig4():
    scen = M.scenario_bounds()
    heat = M.heat_metric_sensitivity()
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 88 * MM), gridspec_kw=dict(wspace=0.58))

    # a: joint scenario bounds
    ax=axes[0]
    labels=["Central", "Joint\nunfavourable", "Unfavourable +\nsun-cured alfalfa", "Joint\nfavourable"]
    vals=[r["reduction"]*100 for r in scen]
    ax.barh(range(len(vals)), vals, color=[BLUE,"#b8b7b3","#8a8986",AQUA], height=0.58)
    for i,x in enumerate(vals):
        ax.text(x+1.0,i,f"{x:.1f}%",va="center",fontsize=6.5)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
    ax.set_xlim(0,90); ax.set_xlabel("Integrated programme screen reduction (%)")
    ax.xaxis.grid(True,color=GRID,lw=0.5); ax.set_axisbelow(True)
    ax.set_title("Joint deterministic scenario bounds\n(not probability intervals)",loc="left")
    panel(ax,"a")

    # b: distribution-specific heat metric
    bx=axes[1]
    order=["Central","Useful household heat 9,000 kWh yr-1","Reference heating all natural gas","Reference heating all heating oil","Reference dehydrator 3.5 MJ kg-1 water","Reference dehydrator 4.5 MJ kg-1 water","Alfalfa reference sun-cured"]
    lookup={r["case"]:r for r in heat}
    labels2=["Central","Household heat\n9,000 kWh yr$^{-1}$","All-gas reference\nheating","All-oil reference\nheating","Dryer 3.5 MJ\nkg$^{-1}$ water","Dryer 4.5 MJ\nkg$^{-1}$ water","Sun-cured alfalfa\nreference"]
    vals2=[lookup[k]["kgCO2e_per_MWh_IT"] for k in order]
    cols=[ORANGE if i==0 else BLUE for i in range(len(vals2))]
    bx.barh(range(len(vals2)), vals2, color=cols, height=0.55)
    for i,x in enumerate(vals2): bx.text(x+1.3,i,f"{x:.0f}",va="center",fontsize=6.3)
    bx.set_yticks(range(len(labels2))); bx.set_yticklabels(labels2)
    bx.invert_yaxis(); bx.set_xlim(0,105)
    bx.set_xlabel("Fossil-heat displacement (kgCO$_2$e per MWh IT)")
    bx.xaxis.grid(True,color=GRID,lw=0.5); bx.set_axisbelow(True)
    bx.set_title("Sensitivity of the siting-specific policy metric",loc="left")
    panel(bx,"b")
    save(fig, "Figure_4_sensitivity")


# ---------------------------------------------------------------- Figure 5: counterfactual and accounting
def fig5():
    rows = M.accounting_variants()
    labels = ["Market-\nbased, same\nprocurement\n(headline)", "Location-\nbased, same\nown supply", "Market-\nbased,\nexcluding food\nsubstitution", "Campus on\nresidual grid\nmix, PUE 1.15", "Campus on\nresidual grid\nmix, PUE 1.45"]
    vals = [r["reduction"] * 100 for r in rows]
    cols = [BLUE, BLUE, BLUE, "#c9c8c3", "#c9c8c3"]
    fig, ax = plt.subplots(figsize=(120 * MM, 72 * MM))
    ax.bar(range(5), vals, color=cols, width=0.6, edgecolor="white")
    for i, x in enumerate(vals): ax.text(i, x + 1.2, f"{x:.1f}%", ha="center", fontsize=6.5)
    ax.set_xticks(range(5)); ax.set_xticklabels(labels, fontsize=5.8)
    ax.set_ylabel("Reduction across A + B (%)"); ax.set_ylim(0, 100)
    ax.yaxis.grid(True, color=GRID, lw=0.5); ax.set_axisbelow(True)
    ax.text(3.5, 93, "Unmatched references\n(not used for the headline)", ha="center", fontsize=6, color=INK2)
    save(fig, "Figure_5_counterfactual")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5()
    print(sorted(os.listdir(OUT)))
