from calendar import month
import pandas as pd
import numpy as np
import datetime

pd.set_option('display.max_columns', 50)


def in_lockdown(Date):
    if pd.to_datetime("3/26/2020") <= Date <= pd.to_datetime("5/29/2020"):
        lockdown = 1
    else:
        lockdown = 0

    return lockdown


def convert_num_vehicles(Date):
    if pd.to_datetime("3/26/2020") <= Date <= pd.to_datetime("5/29/2020"):
        lockdown = 1
    else:
        lockdown = 0

    return lockdown


def find_season(month):
    # Winter (1)
    # 12, 1, 2
    # Spring (2)
    # 3, 4, 5
    # summer (3)
    # 6, 7, 8
    # Fall (4)
    # 9, 10, 11
    if 3 <= month <= 5:
        season = 2
    elif 6 <= month <= 8:
        season = 3
    elif 9 <= month <= 11:
        season = 4
    else:
        season = 1

    return season


def insert_incomes(row):
    if row["Quarter"] == 4:
        if row["Year"] == 2021:
            print()
            last_period_inc = 1438.927
            average_pct_change = 0.0215
            income = (1+average_pct_change)*last_period_inc
        else:
            income = row["Weekly_Inc"]
    else:
        income = row["Weekly_Inc"]
    return income


def convert_dates(df, original_date_column_nme, delimiter, y_loc, m_loc, d_loc):
    df["Date"] = df[original_date_column_nme]
    datelist = df["Date"].tolist()
    years = []
    months = []
    days = []

    for date in datelist:
        date = str(date)
        split = date.split(delimiter)
        years.append(split[y_loc])
        months.append(split[m_loc])
        days.append(split[d_loc])
    df["Year"] = years
    df["Month"] = months
    df["Day"] = days
    df["Date"] = df_tnp["Month"]+"/"+df_tnp["Day"]+"/"+df_tnp["Year"]
    df = df_tnp.drop(
        columns=[original_date_column_nme, "Month", "Day", "Year"])
    return df


# Connect to datasets
df_tnp = pd.read_csv("TNPDailyTrips.csv")
df_transit = pd.read_excel("TransitRidership.xlsx")

# Modify TNP dataset
df_tnp["Trip Start Timestamp"] = df_tnp["Trip Start Timestamp"].astype(
    str)
df_tnp["Trips"] = df_tnp["Trips"].apply(
    lambda x: (x.replace(",", ""))).astype(int)

# Convert TNP dates
df_tnp = convert_dates(df_tnp, "Trip Start Timestamp", "/", 2, 0, 1)

# Convert Transit dates
# df_transit = convert_dates(df_transit, "service_date", "-")
df_transit["service_date"] = pd.to_datetime(df_transit["service_date"])

# datelist = df_transit["service_date"].tolist()
# years = []
# months = []
# days = []
# for date in datelist:
#     date = str(date)
#     split = date.split("-")
#     years.append(split[0])
#     months.append(split[1])
#     days.append(split[2].split(" ")[0])
# df_transit["Year"] = years
# df_transit["Month"] = months
# df_transit["Day"] = days
# df_transit["Date"] = df_transit["Month"]+"/" + \
#     df_transit["Day"]+"/"+df_transit["Year"]
# df_transit = df_transit.drop(columns=["service_date", "Month", "Day", "Year"])


df_transit["Total Rides"] = df_transit["total_rides"]
df_transit = df_transit.drop(columns=["total_rides"])

# join datasets
df_tnp["Date"] = pd.to_datetime(df_tnp["Date"])
df = df_tnp.join(df_transit.set_index('service_date'), on='Date')
df["Date"] = df["Date"].astype(
    np.datetime64)
df["Index"] = df["Date"]
df = df.set_index("Index")

# Filter out rows without transit ridership data
df = df[df["Total Rides"] > 0]

# Add in gas price data
df_gas = pd.read_excel("GasPrices.xlsx")
df_gas = df_gas.rename(columns={
                       "Weekly Chicago Regular All Formulations Retail Gasoline Prices  (Dollars per Gallon)": "GasPrice"})
df_gas = df_gas.dropna()
df_gas["Date"] = pd.to_datetime(df_gas["Date"])

# Join gas price data into dataset
df = df.join(df_gas.set_index('Date'), on='Date')

# Filter out rows without gas price data
df = df[df["GasPrice"] > 0]

# Format dataset
df = df.rename(columns={"GasPrice": "Gas_Price", "bus": "Bus_Rides",
               "rail_boardings": "Rail_Boardings", "Trips": "TNP_Trips", "Total Rides": "Transit_Ridership"})
df = df.drop(
    columns=["day_type"])

# Generate additional variables
# Outcome variable 'ratio'
df["Ratio"] = df["Transit_Ridership"]/df["TNP_Trips"]
# Time series controls
df["Date"] = pd.to_datetime(df["Date"])
df["Month"] = df["Date"].dt.month
df["Year"] = df["Date"].dt.year
df["Quarter"] = df["Date"].dt.quarter
df["Time"] = df["Date"].apply(
    lambda x: ((abs(pd.to_datetime("2018-11-05")-x).days)/7))
df["Season"] = df["Month"].apply(lambda x: find_season(x))
df["Lockdown"] = df["Date"].apply(lambda x: in_lockdown(x))

# Connect to and format COVID case data
df_covid = pd.read_csv("ChicagoCOVID.csv")
df_covid = df_covid.rename(columns={
    "Week Start": "Date", "Cases - Weekly": "Cases"})
df_covid = df_covid[df_covid["Cases"] > 0]
df_covid["Date"] = pd.to_datetime(df_covid["Date"])
df_covid = df_covid.drop(columns=["ZIP Code", "Week Number", "Week End", "Cases - Cumulative", "Case Rate - Weekly", "Case Rate - Cumulative", "Tests - Weekly", "Tests - Cumulative", "Test Rate - Weekly", "Test Rate - Cumulative",
                         "Percent Tested Positive - Weekly", "Percent Tested Positive - Cumulative", "Deaths - Weekly", "Deaths - Cumulative", "Death Rate - Weekly", "Death Rate - Cumulative", "Population", "Row ID", "ZIP Code Location"])

# Aggregate COVID cases to be daily
df_covid = df_covid.groupby(['Date'], as_index=False)['Cases'].sum()

# Shift days to allign with other datasets
df_cases = df_covid.set_index("Date")
df_cases = df_cases.shift(freq="1D")
# Join COVID case data into dataset
df = df.join(df_cases, how="left", on='Date')
df["Cases"] = df["Cases"].replace("NaN", 0)

# Input data from ACS car ownership data
# 2021 data chosen to be the same as 2020 per this source showing it's pretty level https://www.valuepenguin.com/auto-insurance/car-ownership-statistics#state-per-capita
df_veh_own = pd.DataFrame(
    {"Year": [2018, 2019, 2020, 2021], "No_Vehicle_Pct": [26.9, 27.8, 26.8, 26.8]})
# Join vehicle ownership data into dataset
df = df.merge(df_veh_own, how='left', on='Year')

# Input FRED Chicago population data
df_population = pd.DataFrame({"Year": [2018, 2019, 2020, 2021], "Population": [
                             9513947, 9485403, 9454282, 9601605]})
# Join vehicle ownership data into dataset
df = df.merge(df_population, how='left', on='Year')

# Connect to unemployment dataset
df_emp = pd.read_excel("FREDData.xls", sheet_name="Unemployment")
df_emp = df_emp.rename(columns={
    "observation_date": "Date", "CHIC917URN": "Unemployment_Rate"})
df_emp["Date"] = pd.to_datetime(df_emp["Date"])
df_emp["Month"] = df_emp["Date"].dt.month
df_emp["Year"] = df_emp["Date"].dt.year

# Join unemployment data into larger dataframe
df = df.merge(df_emp, how="left", on=[
              "Month", "Year"], suffixes=('_left', '_right'))

# Connect to income dataset
df_inc = pd.read_excel("FREDData.xls", sheet_name="Income")
df_inc = df_inc.rename(columns={
    "observation_date": "Date", "ENUC169840510SA": "Weekly_Inc"})
df_inc["Date"] = pd.to_datetime(df_inc["Date"])
df_inc["Quarter"] = df_inc["Date"].dt.quarter
df_inc["Year"] = df_inc["Date"].dt.year

# Join income data into larger dataframe
df = df.merge(df_inc, how="left", on=["Quarter", "Year"])

# Fill in missing weekly income data with average quarterly change in weekly incomes
df["Weekly_Inc"] = df.apply(lambda x: insert_incomes(x), axis=1)

# Formatting
df = df.drop(
    columns=["Date_right", "Date"])
df = df.rename(columns={
    "Date_left": "Week_Start_Date"})

# Reorder dataframe columns
df = df[["Week_Start_Date", "Gas_Price", "Ratio", "TNP_Trips", "Transit_Ridership", "Bus_Rides", "Rail_Boardings",
         "Time", "Month", "Quarter", "Season", "Year", "Cases", "Lockdown", "Population", "Unemployment_Rate", "Weekly_Inc"]]

print(df)
# Save the dataset to CSV
try:
    df.to_csv("CapstoneData.csv", index=False)
except PermissionError:
    print("Please close the CSV file.")
