import pickle
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors

plt.rcParams.update({
    "text.usetex": True,
    "font.size": 30,
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    'hatch.color': 'white'
})


def plot_bar_charts(avgs, stds, metric):
    strategies = ["SKYLINK",
                  "NC-SKYLINK",
                  "Q-learning",
                  "Random",
                  "Bent-Pipe",
                  "KSP",
                  "Dijkstra",
                  ]
    gfs = [1.0, 2.0, 5.0, 10.0]
    patterns = ["///",
                "\\\\",
                "xx",
                "++",
                "..",
                "-",
                "/",
                '']
    colors_base = [
        '#E6001A',
        '#772583',
        '#B8B184',
        '#1f78b4',
        '#E87722',
        '#658D1B',
        '#4B4B4B',
        '#1f78b4',
    ]

    if metric == "throughput":
        for gf in avgs:
            avgs[gf] = [val / 1e12 for val in avgs[gf]]
            stds[gf] = [val / 1e12 for val in stds[gf]]
        y_label = "Throughput (Tbps)"
    elif metric == "drop_rate":
        y_label = "Drop (\%)"
    elif metric == "avg_delay":
        y_label = "Delay of delivered data (ms)"
    elif metric == "avg_hops":
        y_label = "Hops"
    else:
        y_label = "Cost"

    num_strategies = len(strategies)
    num_gfs = len(gfs)
    bar_width = 0.12
    spacing_within_group = 0.03
    spacing_between_groups = 0.2
    x = np.arange(num_gfs) * (num_strategies * (bar_width + spacing_within_group) + spacing_between_groups)

    scale_factor = 0.0015875 * 8_000_000_000
    x_labels = [f"{round(gf * scale_factor / 1e6, 1):.1f}M" for gf in gfs]

    for gf in gfs:
        if gf not in avgs:
            avgs[gf] = [0] * num_strategies
        else:
            if len(avgs[gf]) < num_strategies:
                avgs[gf] += [0] * (num_strategies - len(avgs[gf]))

    fig, ax = plt.subplots(figsize=(14, 10), dpi=250)

    for i, strategy in enumerate(strategies):

        if metric == "drop_rate":
            strategy_means = [100 * avgs[gf][i] for gf in gfs]
            strategy_errors = [100 * stds[gf][i] for gf in gfs]
        else:
            strategy_means = [avgs[gf][i] for gf in gfs]
            strategy_errors = [stds[gf][i] for gf in gfs]

        base_color = colors_base[i % len(colors_base)]
        color_rgb = np.array(mcolors.to_rgb(base_color))
        lighter_color = color_rgb * 0.5 + 0.5
        hatch_pattern = patterns[i % len(patterns)]

        ax.bar(
            x + i * (bar_width + spacing_within_group),
            strategy_means,
            bar_width,
            label=strategy,
            color=lighter_color,
            edgecolor=base_color,
            hatch=hatch_pattern,
            linewidth=1,
            yerr=strategy_errors,
            capsize=5
        )

    ax.set_ylabel(y_label)
    ax.set_xticks(x + (num_strategies - 1) * (bar_width + spacing_within_group) / 2)
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Number of Users")
    ax.set_xlim(left=-0.2, right=x[-1] + num_strategies * (bar_width + spacing_within_group))

    if metric == "avg_hops":
        ax.set_ylim(0, 1.5)
        plt.yticks(np.linspace(0, 1.5, 4))
    elif metric == "throughput":
        ax.set_ylim(0, 3)
        plt.yticks(np.linspace(0, 3, 7))
    elif metric == "drop_rate":
        ax.set_ylim(0, 80)
        plt.yticks(np.linspace(0, 80, 5))
    elif metric == "avg_delay":
        ax.set_ylim(0, 20)
        plt.yticks(np.linspace(0, 20, 5))
    elif metric == "cost":
        ax.set_ylim(0, 150)
        plt.yticks(np.linspace(0, 150, 7))

    ax.legend(loc='upper center', bbox_to_anchor=(0.22, 0.98), ncol=1, frameon=True)

    ax.grid(axis='y', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.savefig(pth + name + "_" + metric + ".pdf")
    plt.show()


def get_paths(sat_failures, gs_failures, gfs):
    strategies = ["SKYLINK",
                  "NC-SKYLINK",
                  "Random",
                  "Bent-Pipe",
                  "KSP",
                  "Dijkstra",
                  "Q-learning",
                  ]
    pths = {s: [] for s in strategies}
    filenames = {}
    for gf in gfs:
        suffix = f"{sat_failures}_{gs_failures}_{gf}"
        i = 0
        for prefix in ["tile_coded_ucb_0500000_2",
                       "ucb",
                       "q_learning",
                       "random",
                       "bent-pipe",
                       "gounder",
                       "dijkstra",
                       ]:
            filenames[strategies[i]] = [f"evaluation_data_{prefix}_{suffix}_{run}.npy" for run in range(no_of_runs)]
            pths[strategies[i]] += [(pth + file, gf) for file in filenames[strategies[i]]]
            i += 1
    return pths


def calculate_improvements(avgs, metric):
    strategies = ["SKYLINK",
                  "NC-SKYLINK",
                  "Q-learning",
                  "Random",
                  "Bent-Pipe",
                  "KSP",
                  "Dijkstra",
                  ]
    skylink_index = strategies.index("SKYLINK")

    print(f"--- Improvements for {metric} ---")
    for gf, values in avgs.items():
        skylink_value = values[skylink_index]

        print(f"GF={gf}:")
        for i, strategy in enumerate(strategies):
            other_value = values[i]
            if i == skylink_index:
                print(f"  {strategy}: {skylink_value:.4f} (baseline)")
            else:
                if metric in ["cost", "drop_rate"]:
                    improvement = (1 - skylink_value / other_value) * 100
                    print(f"  {strategy}: {other_value:.4f} -> SKYLINK improves by {improvement:.1f}% (lower is better).")
                elif metric == "throughput":
                    improvement = (skylink_value / other_value - 1) * 100
                    print(f"  {strategy}: {other_value:.4f} -> SKYLINK improves by {improvement:.1f}% (higher is better).")
        print()
    print()
    print()


# Einstellungen
name = "bar_plot"
start = 0
end = int(90 * 1.82 * 60 * 4)
pth = "results/"

gf_values = [1.0, 2.0, 5.0, 10.0]
scenarios = [(0, 0)]
metrics = ["cost", "drop_rate", "throughput"]
no_of_runs = 1


for sat_f, gs_f in scenarios:
    for metric in metrics:
        avg_values = {gf: [] for gf in gf_values}
        std_values = {gf: [] for gf in gf_values}
        for gf in gf_values:
            paths = get_paths(sat_f, gs_f, [gf])
            for strategy in paths:
                r_list = []
                for r in range(no_of_runs):
                    with open(paths[strategy][r][0], 'rb') as f:
                        d_list = []
                        while True:
                            try:
                                d_list.append(pickle.load(f))
                            except EOFError:
                                break
                    metric_data = np.mean([d[metric] for d in d_list])
                    r_list.append(metric_data)
                avg_values[gf].append(np.mean(r_list))
                std_values[gf].append(np.std(r_list))
        plot_bar_charts(avg_values, std_values, metric)
        calculate_improvements(avg_values, metric)
