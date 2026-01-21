import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class Pension():
    def __init__(self, start, retire, contributions):
        self.start = pd.to_datetime(start)
        self.retire = pd.to_datetime(retire)
        self.cont = contributions

        # Generate contribution dates (e.g., 1st of every month)
        dates = []
        current_date = self.start
        while current_date <= self.retire:
            dates.append(current_date)
            current_date += relativedelta(months=1)
        self.cont_dates = dates

    def load_data(self, data):
        """
        Uses back-filling (bfill) to ensure that if a contribution date 
        falls on a weekend/holiday, it uses the NEXT available price.
        """
        df = data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()

        # Create a continuous date range
        all_days = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')

        # REINDEX and BACK-FILL
        # This maps missing dates to the price of the NEXT available row.
        self.funds = df.reindex(all_days).bfill()

    def get_price(self, date, col):
        """
        Retrieves the price for a specific date. 
        Because of .bfill(), this date's value is effectively the 
        price of the next valid trading day.
        """
        ts_date = pd.to_datetime(date)
        try:
            price = self.funds.at[ts_date, col]
            # If still NaN (e.g., date is after the last date in your CSV), 
            # we return the last known price to prevent errors.
            if pd.isna(price):
                return self.funds[col].dropna().iloc[-1]
            return price
        except KeyError:
            # If the requested date is outside the dataframe range entirely
            return self.funds[col].dropna().iloc[-1]

    # ... [derisk_strategy and calculate_purchase_units remain the same] ...

    def derisk_strategy(self, target_weight, derisk_years):
        self.derisk_years = derisk_years
        self.derisk_target = target_weight
        self.start_derisk_date = self.retire - relativedelta(years=self.derisk_years)
        self.derisk_months = self.derisk_years * 12
        denom = self.derisk_months if self.derisk_months > 0 else 1
        self.derisk_perc_change = round((1 - self.derisk_target) / denom, 6)

    def calculate_purchase_units(self, curr_e, curr_b, price_e, price_b, contribution, target_bond_ratio):
        if price_e <= 0 or price_b <= 0:
            return 0.0, 0.0
        A = np.array([[price_e, price_b], [-target_bond_ratio, (1 - target_bond_ratio)]])
        B = np.array([contribution, target_bond_ratio * curr_e - (1 - target_bond_ratio) * curr_b])
        try:
            delta_q = np.linalg.solve(A, B)
            return round(delta_q[0], 6), round(delta_q[1], 6)
        except np.linalg.LinAlgError:
            return 0.0, 0.0

    def accumulate(self):
        # 1. Pre-calculate bond proportions for the timeline
        bond_prop = []
        for d in self.cont_dates:
            if d <= self.start_derisk_date:
                bond_prop.append(0.0)
            else:
                diff = relativedelta(d, self.start_derisk_date)
                months_passed = diff.years * 12 + diff.months
                prop = min(months_passed * self.derisk_perc_change, 1.0)
                bond_prop.append(prop)

        results = []
        ety_cumsum, bnd_cumsum = 0.0, 0.0

        # 2. Loop through contribution dates
        for i, date_ in enumerate(self.cont_dates):
            ety_price = self.get_price(date_, "ety_open_price")
            bnd_price = self.get_price(date_, "bnd_open_price")

            e_to_buy, b_to_buy = self.calculate_purchase_units(
                ety_cumsum, bnd_cumsum, ety_price, bnd_price, self.cont, bond_prop[i]
            )

            ety_cumsum += e_to_buy
            bnd_cumsum += b_to_buy

            results.append({
                "date": date_,
                "cont": self.cont,
                "ety_price": ety_price,
                "ety_purchased": e_to_buy,
                "ety_cumsum": ety_cumsum,
                "ety_target": 1 - bond_prop[i],
                "bnd_price": bnd_price,
                "bnd_purchased": b_to_buy,
                "bnd_cumsum": bnd_cumsum,
                "bnd_target": bond_prop[i]
            })
        df_accum = pd.DataFrame(results)

        # calculate total cumulative values
        df_accum["ety_cumsum_value"] = df_accum["ety_cumsum"] * df_accum["ety_price"]
        df_accum["bnd_cumsum_value"] = df_accum["bnd_cumsum"] * df_accum["bnd_price"]
        df_accum["portfolio_value"] = round(df_accum["ety_cumsum_value"] + df_accum["bnd_cumsum_value"], 2)

        return df_accum