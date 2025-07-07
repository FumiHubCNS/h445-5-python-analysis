"""!
@file metis_log.py
@version 1
@author Fumitaka ENDO
@date 2025-07-07T19:56:26+09:00
@brief metis log checker
"""
import argparse
import pathlib
import sqlite3
import pandas as pd
import json
from datetime import datetime, timezone, timedelta
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import h445lib2.catm.h445_utilities as h445util2
import catmlib.util as catutil

this_file_path = pathlib.Path(__file__).parent

JST = timezone(timedelta(hours=9))

def load_db(database_path, ip_filter, module_type):
    if module_type == 'caen':
        return load_caen(database_path, ip_filter)

def load_caen(database_path, ip_filter):

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    query = """
    SELECT timestamp, json_data FROM monitor_logs
    WHERE ip_address = ?
    ORDER BY timestamp ASC
    """
    cursor.execute(query, (ip_filter,))
    rows = cursor.fetchall()

    records = []

    for timestamp, json_data in rows:
        try:
            data = json.loads(json_data)
            VMON = list(map(float, data.get("VMON", [])))
            IMON = list(map(float, data.get("IMON", [])))
            VSET = list(map(float, data.get("VSET", [])))
            ISET = list(map(float, data.get("ISET", [])))
            STAT = data.get("STAT", [])
            
            min_len = min(len(VMON), len(IMON), len(VSET), len(ISET), len(STAT))
            for i in range(min_len):
                records.append({
                    "timestamp_utc": datetime.fromtimestamp(timestamp, tz=timezone.utc),
                    "timestamp_jst": datetime.fromtimestamp(timestamp, tz=JST),
                    "CH": i,
                    "VMON": VMON[i],
                    "IMON": IMON[i],
                    "VSET": VSET[i],
                    "ISET": ISET[i],
                    "STAT": STAT[i]
                })
        except json.JSONDecodeError:
            print(f"Invalid JSON data at timestamp {timestamp}")

    df = pd.DataFrame(records)

    conn.close()

    return df

def plot_cean_log(df, ip_filter, module_type):

    dfs = [df[df["CH"] == ch] for ch in range(4)]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=(f"VMON over Time ({ip_filter}, {module_type})", f"IMON over Time ({ip_filter}, {module_type})")
    )

    for i, dfi in enumerate(dfs):
        fig.add_trace(
            go.Scatter(
                x=dfi["timestamp_jst"],
                y=dfi["VMON"],
                mode="lines+markers",
                name=f"VMON ch{i}"
            ),
            row=1, col=1
        )

    for i, dfi in enumerate(dfs):
        fig.add_trace(
            go.Scatter(
                x=dfi["timestamp_jst"],
                y=dfi["IMON"],
                mode="lines+markers",
                name=f"IMON ch{i}"
            ),
            row=2, col=1
        )

    fig.update_layout(
        height=800,
        xaxis_tickangle=45,
        xaxis2_tickangle=45,
        showlegend=True,
        legend_title="Channels"
    )

    fig.update_xaxes(title_text="Timestamp JST", row=2, col=1)
    fig.update_yaxes(title_text="VMON", row=1, col=1)
    fig.update_yaxes(title_text="IMON", row=2, col=1)

    fig.show()

def check_log(database_path, ip_filter, module_type):

    df = load_db(database_path, ip_filter, module_type)
    df["timestamp_jst"] = pd.to_datetime(df["timestamp_jst"])

    if module_type == 'caen':
        plot_cean_log(df, ip_filter, module_type)


def main():

    parameters_path = this_file_path / '../../../parameters.toml'
    print(parameters_path)

    config, base_path, homepage_path = h445util2.load_parameters_toml(parameters_path)
    print(config)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="path of database file", type=str, default="")
    parser.add_argument("-f", "--filter", help="filter information", type=str, default="mini-caen0")
    parser.add_argument("-t", "--type", help="module type", type=str, default="caen")

    args = parser.parse_args()

    database_path: str = args.input
    ip_filter: str = config["metis"]["ip-information"][args.filter]
    module_type: str = args.type

    input_with_environment_variables = f"{config["data"]["base"]}/{database_path}" if database_path != "" else f"{config["data"]["base"]}/{config["metis"]["db-path"]}"
    input_db_path = catutil.dataforming.expand_environment_variables(input_with_environment_variables)

    print(input_db_path)

    # check_log(input_db_path, ip_filter, module_type)

if __name__ == "__main__":
    main()
