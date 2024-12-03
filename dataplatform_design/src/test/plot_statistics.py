import pandas as pd
import os
import matplotlib.pyplot as plt
import pandas as pd


def plot_metrics_grid(result_paths, out_path):
    for test_result in result_paths:
        df = pd.read_csv(test_result)
        grouped = df.groupby("scenario").mean()

        grouped["total_time"] = (
            grouped["match_time"] + grouped["augment_time"] + grouped["select_time"]
        )

        grouped = grouped.sort_values("total_time", ascending=True)

        _, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
        axes = axes.ravel()

        grouped["match_time"].plot(
            kind="bar", ax=axes[0], title="Average Match Time", color="skyblue"
        )
        axes[0].set_ylabel("Time (s)")
        axes[0].set_xlabel("Scenario")
        axes[0].tick_params(axis="x", labelrotation=30)
        axes[0].set_xticks(axes[0].get_xticks())
        axes[0].set_xticklabels(axes[0].get_xticklabels(), ha="right")
        grouped["augment_time"].plot(
            kind="bar", ax=axes[1], title="Average Augment Time", color="orange"
        )
        axes[1].set_ylabel("Time (s)")
        axes[1].set_xlabel("Scenario")
        axes[1].tick_params(axis="x", labelrotation=30)
        axes[1].set_xticklabels(axes[1].get_xticklabels(), ha="right")

        grouped["select_time"].plot(
            kind="bar", ax=axes[2], title="Average Select Time", color="green"
        )
        axes[2].set_ylabel("Time (s)")
        axes[2].set_xlabel("Scenario")
        axes[2].tick_params(axis="x", labelrotation=30)
        axes[2].set_xticklabels(axes[2].get_xticklabels(), ha="right")

        grouped["total_time"].plot(
            kind="bar",
            ax=axes[3],
            title="Total Average Time (Match + Augment + Select)",
            color="purple",
        )
        axes[3].set_ylabel("Time (s)")
        axes[3].set_xlabel("Scenario")
        axes[3].tick_params(axis="x", labelrotation=30)
        axes[3].set_xticklabels(axes[3].get_xticklabels(), ha="right")

        os.makedirs(
            os.path.join(out_path, test_result.split(os.sep)[-1][:-4]), exist_ok=True
        )

        plt.savefig(
            f"{os.path.join(out_path, test_result.split(os.sep)[-1][:-4], 'grid_charts.svg')}",
            format="svg",
        )


def plot_stacked_bar_chart(result_paths, out_path):
    for test_result in result_paths:
        df = pd.read_csv(test_result)

        grouped = df.groupby("scenario").mean()

        grouped["total_time"] = (
            grouped["match_time"] + grouped["augment_time"] + grouped["select_time"]
        )

        grouped = grouped.sort_values("total_time", ascending=True)

        fig, ax = plt.subplots(figsize=(14, 8))

        ax.bar(grouped.index, grouped["match_time"], label="Match Time")
        ax.bar(
            grouped.index,
            grouped["augment_time"],
            bottom=grouped["match_time"],
            label="Augment Time",
        )
        ax.bar(
            grouped.index,
            grouped["select_time"],
            bottom=grouped["match_time"] + grouped["augment_time"],
            label="Select Time",
        )

        ax.set_title("Average Times per Scenario", fontsize=16)
        ax.set_ylabel("Time (s)", fontsize=12)
        ax.set_xlabel("Scenario", fontsize=12)
        ax.legend()

        plt.xticks(rotation=45, fontsize=10, ha="right")
        plt.tight_layout()

        os.makedirs(
            os.path.join(out_path, test_result.split(os.sep)[-1][:-4]), exist_ok=True
        )
        plt.savefig(
            f"{os.path.join(out_path, test_result.split(os.sep)[-1][:-4], 'stacked_bar_chart.svg')}",
            format="svg",
        )


result_directory = "/home/dataplatform_design/run_statistics/"
result_paths = [
    os.path.join(result_directory, file)
    for file in os.listdir(result_directory)
    if ".csv" in file
]
out_path = "/home/dataplatform_design/run_statistics/plots/"

plot_metrics_grid(result_paths, out_path)
plot_stacked_bar_chart(result_paths, out_path)
