import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pickle


def load_metric_data_from_file(filepath, metric):
    """Load metric data from the given filepath and calculate the mean over all time steps."""
    data_list = []
    try:
        with open(filepath, 'rb') as f:
            while True:
                try:
                    data = pickle.load(f)
                    data_list.append(data[metric])
                except EOFError:
                    break
    except (FileNotFoundError, pickle.UnpicklingError) as e:
        print(f"Error loading {filepath}: {e}")
    return np.mean(data_list) if data_list else np.nan


# Define parameter ranges
distance_precisions = [2e4, 5e4, 1e5, 2e5, 5e5, 1e6, 2e6]  # Distance precision values
grid_sizes = [1, 2, 3, 4, 5, 6]  # Grid sizes
metric = 'cost'  # Define the metric to plot
context = '[\'distance\']'  # Specify the context


def plot_single_heatmap(path, gf):
    print(f"Generating heatmap for metric '{metric}'")

    avg_values = np.array([
        [
            load_metric_data_from_file(
                os.path.join(
                    path,
                    f"evaluation_data_tile_coded_ucb_{int(dist_prec):07d}_{int(grids)}_0_0_{gf}_0.npy"
                ),
                metric
            )
            for dist_prec in distance_precisions
        ]
        for grids in grid_sizes
    ])

    print("Shape of avg_values:", avg_values.shape)

    plt.rcParams.update({
        "text.usetex": True,
        "font.family": "serif",
        "font.size": 20,
        "font.serif": ["Times New Roman"]
    })

    plt.figure(figsize=(10, 8), dpi=250)
    sns.heatmap(
        avg_values,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        xticklabels=[str(int(d/1000)) + " km" for d in distance_precisions],
        cbar=False,
        yticklabels=grid_sizes
    )

    plt.xlabel(r"Distance Precision")
    plt.ylabel(r"Number of Grids")
    plt.tight_layout()
    plt.savefig(path + metric + "_" + str(gf) + "_heatmap.pdf")
    plt.show()


plot_single_heatmap("results/", 2.0)
