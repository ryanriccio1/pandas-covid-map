# Author:   Ryan Riccio
# Program:  COVID Visualization Project
# Date:     November 14th, 2022

from matplotlib import image as mpimg
from matplotlib import pyplot as plt
from datetime import datetime
from urllib import request
import pandas as pd
import argparse
import time
import os


def get_data():
    """
    Get CA COVID death data from the JHU GitHub and return as DataFrame.

    :return: DataFrame of CA COVID deaths.
    """
    url = "https://github.com/CSSEGISandData/COVID-19/raw/master/csse_covid_19_data/csse_covid_19_time_series" \
          "/time_series_covid19_deaths_US.csv "
    filename = "death_data.csv"

    # see if the data is locally store, if it is, make sure its newer than 12 hours old, otherwise download
    if not os.path.exists(filename) or time.time() - os.path.getmtime(filename) > (60 * 60 * 12):
        request.urlretrieve(url, filename)

    # dataframe preprocessing
    df = pd.read_csv(filename)
    df = df.rename(columns={"Admin2": "County", "Province_State": "State"})
    df = df[df["State"] == "California"]
    unused_columns = ["UID", "iso2", "iso3", "code3", "FIPS", "Long_", "Lat", "Population",
                      "Country_Region", "Combined_Key", "State"]
    df = df.drop(columns=unused_columns)
    df = df.set_index("County")
    return df


def get_stats():
    """
    Get info on CA counties from file.

    :return: DataFrame of CA county stats.
    """
    # get the lon and lat of CA counties from file
    ca_stats_df = pd.read_csv("california_county_stats.txt")
    ca_stats_df = ca_stats_df.set_index("County")
    unused_columns = ["Population", "Area"]
    ca_stats_df = ca_stats_df.drop(columns=unused_columns)
    return ca_stats_df


def convert_to_daily(df):
    """
    Convert stats to daily readings rather than cumulative.

    :param df: DataFrame to perform conversion on.
    :return: Processed DataFrame and Series of total deaths per county.
    """
    first_column = df.columns.get_loc("1/22/20")
    last_column = df.shape[1] - 1
    total_deaths = df.iloc[:, -1:].copy()

    # convert cumulative data to daily data by subtracting last item iteratively
    for column in range(last_column, first_column, -1):
        df.iloc[:, column] = df.iloc[:, column] - df.iloc[:, column - 1]

    return df, total_deaths


def get_county(df, county):
    """
    Return a specific county from the CA dataframe.

    :param df: DataFrame to search.
    :param county: County name to search for.
    :return: Series of county info.
    """
    return df.loc[county]


def n_day_average(df, n):
    """
    Calculate the n-day average of daily statistics.

    :param df: DataFrame to process.
    :param n: Number of days to average.
    :return: Averaged DataFrame.
    """
    avg = df.copy()
    first_column = df.columns.get_loc("1/22/20")
    last_column = df.shape[1] - 1

    # average n days in a row
    for column in range(first_column + n, last_column):
        avg.iloc[:, column] = avg.iloc[:, column:column + n].mean(axis=1)

    # average the first n days to keep from bad data
    for column in range(first_column, n):
        avg.iloc[:, column] = avg.iloc[:, first_column:column + 1].mean(axis=1)
    return avg


def plot_map(total_deaths, stats_df, subplot):
    """
    Plot COVID Data per county on map of CA.

    :param total_deaths: Series of deaths indexed by county.
    :param stats_df: DataFrame of CA county info.
    :param subplot: Plot to plot data onto.
    :rtype: None
    """
    # plot image and make it a square, use lanczos interpolation because sometimes its sharper than antialiasing
    california = mpimg.imread('california.png')
    subplot.imshow(california, interpolation='lanczos', aspect='auto', extent=[-124.55, -113.80, 32.45, 42.05])
    total_deaths = total_deaths.rename(columns={total_deaths.iloc[:, -1].name: "Total Deaths"})
    # combine deaths and locations of counties to plot onto image
    info = stats_df.join(total_deaths)

    # plot onto image
    subplot.scatter(info["Lon"], info["Lat"], s=info["Total Deaths"], color="orangered", alpha=0.3)
    subplot.set_xlabel("Longitude", labelpad=10, fontsize=14)
    subplot.set_ylabel("Latitude", labelpad=10, fontsize=14)
    subplot.set_title("COVID-19 Deaths by County", pad=15, fontsize=16)


def plot_daily(ca, county, total_deaths, subplot):
    """
    Plot graph of daily deaths in CA county compared to CA overall.

    :param ca: CA death info.
    :param county: County death info.
    :param total_deaths: Total deaths indexed by county.
    :param subplot: Plot to plot data onto.
    :rtype: None
    """
    # get the total average of all counties
    ca_avg = ca.sum()

    # get all the data from DF
    ca_x_vals = ca_avg[:].index
    ca_y_vals = ca_avg[:]
    ca_x_vals = [datetime.strptime(day, '%m/%d/%y') for day in ca_x_vals]

    county_x_vals = county[:].index
    county_y_vals = county[:]
    county_x_vals = [datetime.strptime(day, '%m/%d/%y') for day in county_x_vals]

    # plot a grid
    subplot.yaxis.grid()

    # plot CA total
    subplot.plot(ca_x_vals, ca_y_vals, "-", color="lightsteelblue")
    subplot.fill_between(ca_x_vals, ca_y_vals, color="lightsteelblue", alpha=0.4)

    # plot county total
    subplot.plot(county_x_vals, county_y_vals, "-", color="orangered")
    subplot.fill_between(county_x_vals, county_y_vals, color="orangered", alpha=0.4)

    # set label and title
    subplot.set_xlabel("Date", labelpad=10, fontsize=14)
    subplot.set_ylabel("Deaths", labelpad=10, fontsize=14)
    subplot.set_title(f"COVID-19 Deaths in {county.name} County", fontsize=16, pad=15)

    # set 'legend' that shows total numbers
    subplot.text(ca_x_vals[0], 500, f'CA Total = {total_deaths.sum().iloc[0]:,.0f}', fontsize=12,
                 bbox=dict(linestyle="", facecolor='lightsteelblue', boxstyle='round, pad=1'))
    subplot.text(ca_x_vals[0], 450, f'{county.name} Total = {round(county.sum(), 0):,.0f}', fontsize=12,
                 bbox=dict(edgecolor='orangered', fill=False, boxstyle='round, pad=1'))


def county_in_df(val, df):
    """
    Check if county is in a DataFrame.

    :param val: County to check for.
    :param df: DataFrame to search.
    :return: True if found, False if not.
    """
    if val in df.index:
        return True
    return False


def run_program(county):
    """
    Main loop for COVID visualization.

    :param county: County to plot.
    :rtype: None
    """
    # get data from file
    ca_stats_df = get_stats()
    ca_covid_df = get_data()

    # check to see if our county is valid
    county = county.title()
    if not county_in_df(county, ca_stats_df):
        raise ValueError("That is an invalid county.")

    # covert to daily stats, get total deaths
    ca_covid_df, total_deaths = convert_to_daily(ca_covid_df)

    # average data and pick out selected county
    ca_avg_df = n_day_average(ca_covid_df, 7)
    county_avg_df = get_county(ca_avg_df, county)

    # setup matplotlib figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))
    fig.subplots_adjust(left=0.045, right=0.965, bottom=0.08, top=0.945, wspace=0.15, hspace=0)

    # plot subplots
    plot_daily(ca_avg_df, county_avg_df, total_deaths, ax2)
    plot_map(total_deaths, ca_stats_df, ax1)
    plt.show()


if __name__ == "__main__":
    # get county data from argparse
    parser = argparse.ArgumentParser("COVID Visualization", description="Display COVID data given a county in CA.")
    parser.add_argument("county", type=str, help="name of county in CA")
    args = parser.parse_args()

    # run main program loop
    run_program(args.county)
