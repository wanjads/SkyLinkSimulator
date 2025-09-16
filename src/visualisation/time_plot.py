import _pickle
import pickle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams.update({
    "text.usetex": True,
    "font.size": 32,
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    'hatch.color': 'white'
})


colors = [
    '#1f78b4',
    '#E87722',
    '#4B4B4B',
    '#658D1B',
    '#B8B184',
    '#772583',
    '#E6001A',
    '#1B4332',
]

labels = [
    "Random",
    "Bent-Pipe",
    "Dijkstra",
    "KSP",
    "Q-Learning",
    "NC-SKYLINK",
    "SKYLINK",
]

markers = ['d',
           's',
           'o',
           '^',
           '>',
           'v',
           'x',
           '<',
           ]

def sliding_window_mean(data, ws):
    return np.convolve(data, np.ones(ws) / ws, mode='valid')

def draw_generation_rate_box(x_upper, generation_rate_smooth, label='Generation Rate'):
    x_pos = 0.75 * x_upper
    y_pos = 1.185 * np.mean(generation_rate_smooth)

    box_width = 0.23 * x_upper
    box_height = 0.037 * np.mean(generation_rate_smooth)

    plt.gca().add_patch(Rectangle(
        (x_pos, y_pos - box_height), box_width, box_height,
        edgecolor='black', facecolor='white', linewidth=1, zorder=10
    ))

    plt.text(x_pos + 0.07 * x_upper, y_pos - box_height/2, label, fontsize=20, verticalalignment='center', zorder=11)

    plt.plot([x_pos + 0.01 * x_upper, x_pos + 0.055 * x_upper], [y_pos - box_height/2, y_pos - box_height/2],
             linestyle='--', color='black', linewidth=2, zorder=12)


def plot_evaluation_data(
    filenames, metric, y_label, y_lower, y_upper, y_tics, gsl_failures, isl_failures, gf,
    orbital_rounds=False,
    fig_size=(15.5, 10), dpi=250,
    legend_ncol=3, legend_y=1.35, top_margin=0.78
):

    fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
    fig.subplots_adjust(top=top_margin)   # Platz am oberen Rand für die Legendebox

    print(metric)
    x_upper = 0
    x_lower = 0
    orbital_period_time_steps = 1.82 * 60 * 4
    generation_rate = None
    x_data = None

    extra_artists = []

    for file_no in range(len(filenames)):
        filename = filenames[file_no]

        data = []
        try:
            d_list = []
            with open(filename, 'rb') as f:
                while True:
                    try:
                        d_list.append(pickle.load(f))
                    except EOFError:
                        break
            data += [d_list]
        except EOFError:
            print(f"File corrupted: {filename}")
            continue
        except _pickle.UnpicklingError:
            print(f"File corrupted: {filename}")
            continue
        except FileNotFoundError:
            print(f"File not found: {filename}")
            continue

        metric_data = np.array([[d[metric] for d in run][start:end] for run in data])
        metric_data_mean = np.mean(metric_data, axis=0)

        if metric == "cost":
            delay_metric_data = np.array([[d["avg_delay"] for d in run][start:end] for run in data])
            drop_metric_data = np.array([[d["drop_rate"] for d in run][start:end] for run in data])
            metric_data = (np.ones([len(drop_metric_data), len(drop_metric_data[0])]) - drop_metric_data) \
                          * delay_metric_data + 200 * drop_metric_data
            metric_data = np.mean(metric_data, axis=0)
        elif metric == "drop_rate":
            metric_data = 100 * metric_data_mean
        elif metric == "throughput":
            metric_data = metric_data_mean / 1e9
            if generation_rate is None:
                generation_rate = np.mean([[d["generation_rate"] for d in run][start:end] for run in data],
                                          axis=0) / 1e9
        elif metric == "main_link_out":
            metric_data = (metric_data_mean *
                           np.mean(np.array([[d["throughput"] for d in run][:end] for run in data]), axis=0) / 1e9)
        else:
            metric_data = metric_data_mean

        print(labels[file_no] + " (avg)", np.nanmean(metric_data))
        print(labels[file_no] + " (std)", np.nanstd(metric_data))
        print()

        metric_data_smooth = sliding_window_mean(metric_data, window_size)

        if orbital_rounds:
            x_lower = window_size / orbital_period_time_steps
            x_data = np.linspace(x_lower, len(metric_data_smooth) + x_lower, len(metric_data_smooth))
            x_upper = len(metric_data_smooth) / orbital_period_time_steps + x_lower
            x_label = 'Orbital Rounds'
        else:
            days = len(metric_data_smooth) / ( 24 * 60 * 4)
            x_lower = window_size / (24 * 60 * 4)
            x_data = np.linspace(x_lower, days + x_lower, len(metric_data_smooth))
            x_upper = days + x_lower
            x_label = 'Days'

        label = labels[file_no]
        ax.plot(
            x_data, metric_data_smooth,
            label=label, color=colors[file_no], marker=markers[file_no],
            markevery=int(10 * 1.82 * 60 * 4), markersize=15,
            linewidth=2 if label == "SKYLINK" else 1
        )

    if metric == "throughput" and generation_rate is not None:
        generation_rate_smooth = sliding_window_mean(generation_rate, window_size)
        ax.plot(x_data, generation_rate_smooth, linestyle='--', color='black', linewidth=2)
        draw_generation_rate_box(x_upper, generation_rate_smooth)

    if gsl_failures or isl_failures:
        failure_start = 2 * 24 * 60 * 4
        failure_end = 4 * 24 * 60 * 4

        failure_start /= (24 * 60 * 4)
        failure_end /= (24 * 60 * 4)

        ax.axvline(x=failure_start, color='red', linestyle='--', linewidth=1.5)
        t1 = ax.text(
            failure_start - 0.8,
            y_upper - (y_upper - y_lower) * 0.05,
            'GSL Failures' if gsl_failures else 'ISL Failures',
            color='red', fontsize=20
        )
        extra_artists.append(t1)

        ax.axvline(x=failure_end, color='green', linestyle='--', linewidth=1.5)
        t2 = ax.text(
            failure_end - 0.8,
            y_upper - (y_upper - y_lower) * 0.05,
            'GSL Recovery' if gsl_failures else 'ISL Recovery',
            color='green', fontsize=20
        )
        extra_artists.append(t2)

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_xlim(x_lower, x_upper)
    ax.set_ylim(y_lower, y_upper)
    ax.set_yticks(np.linspace(y_lower, y_upper, y_tics))
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    leg = ax.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, legend_y),
        fancybox=True,
        ncol=legend_ncol
    )
    extra_artists.append(leg)

    out_path = pth + name + "_" + metric + "_" + str(gsl_failures) + "_" + str(isl_failures) + "_" + str(gf) + ".pdf"
    fig.savefig(out_path, bbox_inches="tight", bbox_extra_artists=extra_artists)
    plt.show()
    plt.close(fig)


def get_pths(gsl_failures, isl_failures, gf):

    suffix = str(int(gsl_failures)) + "_" + str(int(isl_failures)) + "_" + str(gf) + "_0"

    filenames = ([
        "evaluation_data_random_" + suffix + ".npy",
        "evaluation_data_bent-pipe_" + suffix + ".npy",
        "evaluation_data_dijkstra_" + suffix + ".npy",
        "evaluation_data_gounder_" + suffix + ".npy",
        "evaluation_data_q_learning_" + suffix + ".npy",
        "evaluation_data_ucb_" + suffix + ".npy",
        "evaluation_data_tile_coded_ucb_0500000_2_" + suffix + ".npy",
    ])

    return [pth + filename for filename in filenames]


name = "time_plot"
window_size = 4 * 60 * 12
start = 0
end = 4 * 60 * 24 * 10
pth = "results"
g = 2.0
gsl_f = 1
isl_f = 0
no_of_runs = 10
pths = get_pths(gsl_f,isl_f, g)

if gsl_f == isl_f == 0:
    plot_evaluation_data(pths, 'fairness', "Jain's Fairness Index", 0.75, 1, 6, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'cost', 'Cost', 0, 50, 6, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'drop_rate', 'Drop (\%)', 0, 40, 5, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'avg_delay', 'Delay (ms)', 3, 8, 6, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'throughput', 'Throughput (Gbps)', 0, 3500, 8, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'avg_hops', 'Hops', 0.99, 1.05, 7, gsl_f, isl_f, g)

elif isl_f == 1:
    plot_evaluation_data(pths, 'cost', 'Cost', 0, 25, 6, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'drop_rate', 'Drop (\%)', 0, 50, 6, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'avg_delay', 'Delay (ms)', 3, 7, 5, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'throughput', 'Throughput (Gbps)', 350, 700, 8, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'avg_hops', 'Hops', 0.99, 1.15, 9, gsl_f, isl_f, g)

elif gsl_f == 1:
    plot_evaluation_data(pths, 'cost', 'Cost', 0, 20, 6, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'drop_rate', 'Drop (\%)', 0, 12, 7, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'avg_delay', 'Delay (ms)', 3, 7, 5, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'throughput', 'Throughput (Gbps)', 350, 700, 8, gsl_f, isl_f, g)
    plot_evaluation_data(pths, 'avg_hops', 'Hops', 0.96, 1.16, 6, gsl_f, isl_f, g)
