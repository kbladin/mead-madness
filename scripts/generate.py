# Copyright (c) 2024 Kalle Bladin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import collections
from collections import Counter
import matplotlib.backends.backend_pdf as backend_pdf


class IdNameMapper(collections.abc.Mapping):
    def __init__(self, id_name_map):
        self._id_name_map = id_name_map

    def __getitem__(self, key):
        return "({}) ".format(key) + self._id_name_map[key]

    def __iter__(self):
        return self._id_name_map.__iter__()

    def __len__(self):
        return self._id_name_map.__len__()


def clean_split(string):
    """Example input "hej;  Hej; haj"
    Example output: ["hej", "Hej", "haj"]
    """
    if not type(string) is str:
        return []
    return [" ".join(x.split()) for x in string.split(";")]


def write_counter(x, y, title, c: Counter):
    x_pos = x
    y_pos = y
    plt.figtext(x_pos, y_pos, title, fontsize=14)
    for text in c:
        y_pos -= 0.04
        plt.figtext(
            x_pos,
            y_pos,
            "({}) {}".format(c[text], text),
            fontsize=10,
        )
    y_pos -= 0.06
    return (x_pos, y_pos)


def write_list(x, y, title, l: list):
    x_pos = x
    y_pos = y
    plt.figtext(x_pos, y_pos, title, fontsize=14)
    for text in l:
        y_pos -= 0.04
        plt.figtext(
            x_pos,
            y_pos,
            text,
            fontsize=10,
        )
    y_pos -= 0.06
    return (x_pos, y_pos)


def plot_mead_info(df: pd.DataFrame, id: str, id_name_map: IdNameMapper):
    this_df = df.query("Id == {}".format(id))
    filtered_df = this_df.filter(["Sötma", "Syrlighet", "Fyllighet"])
    notes = Counter(
        this_df.filter(["Smaknoter"])
        .transform({"Smaknoter": clean_split})
        .sum()
        .to_dict()["Smaknoter"]
    )
    off_flavors = Counter(
        this_df.filter(["Bismaker"])
        .transform({"Bismaker": clean_split})
        .sum()
        .to_dict()["Bismaker"]
    )
    other = (
        this_df.filter(["Övrigt"])
        .transform({"Övrigt": clean_split})
        .sum()
        .to_dict()["Övrigt"]
    )

    plt.figure()
    sns.pointplot(data=filtered_df, errorbar="sd", linestyles=" ", markers="o")
    plt.gca().set_ylim([1, 9])
    plt.suptitle(id_name_map[id], fontsize=16, y=0.95)
    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)

    x_pos, y_pos = 0.72, 0.85

    if len(notes) > 0:
        plt.subplots_adjust(left=0.1, right=0.7, top=0.9, bottom=0.1)
        x_pos, y_pos = write_counter(x_pos, y_pos, "Smaknoter", notes)
    if len(off_flavors) > 0:
        plt.subplots_adjust(left=0.1, right=0.7, top=0.9, bottom=0.1)
        x_pos, y_pos = write_counter(x_pos, y_pos, "Bismaker", off_flavors)
    if len(other) > 0:
        plt.subplots_adjust(left=0.1, right=0.7, top=0.9, bottom=0.1)
        x_pos, y_pos = write_list(x_pos, y_pos, "Övrigt", other)

    # plt.show()


def plot_category(df: pd.DataFrame, category: str, id_name_map: IdNameMapper):
    filtered_df = pd.DataFrame(
        df.filter(["Id"] + [category]).groupby("Id")[category].apply(list).to_dict()
    ).rename(mapper=id_name_map, axis=1)

    plt.figure()
    sns.pointplot(data=filtered_df, errorbar="sd", linestyles=" ", markers="o")
    plt.gca().set_ylim([1, 9])
    plt.title(category)

    # plt.show()


def main():
    instances_dir = "data/instances"
    instance_folders = (
        x
        for x in os.listdir(instances_dir)
        if os.path.isdir(os.path.join(instances_dir, x))
    )
    for instance_folder in instance_folders:
        # Paths
        instance_dir = os.path.join(instances_dir, instance_folder)
        id_name_map_filepath = os.path.join(instance_dir, "id_name_map.csv")
        mead_data_filepath = os.path.join(instance_dir, instance_folder + ".csv")

        # Read
        df_id_name_map = pd.read_csv(
            id_name_map_filepath, sep=r"\s*,\s*", engine="python"
        )
        id_name_map = IdNameMapper(df_id_name_map.set_index("Id").to_dict()["Namn"])
        df = pd.read_csv(mead_data_filepath, skipinitialspace=True)

        plt.style.use("Solarize_Light2")

        # Title page
        plt.figure()
        plt.figtext(
            0.5, 0.5, instance_folder, fontsize=24, horizontalalignment="center"
        )

        # Mead info
        for id in set(sorted(df.get("Id"))):
            plot_mead_info(df, id, id_name_map)

        # Categories
        for category in ["Sötma", "Syrlighet", "Fyllighet", "Helhetsbetyg"]:
            plot_category(df, category, id_name_map)

        # Save pdf
        pdf = backend_pdf.PdfPages(instance_folder + ".pdf")
        for n in plt.get_fignums():
            fig = plt.figure(n)
            fig.set_size_inches(1920.0 / fig.dpi, 1080.0 / fig.dpi)
            pdf.savefig(n)
        pdf.close()


if __name__ == "__main__":
    main()
