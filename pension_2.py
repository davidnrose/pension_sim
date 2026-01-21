# import libraries
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


# create pension class
class Pension():

    def __init__(self, start, retire, contributions):
        self.start = start
        self.retire = retire
        self.cont = contributions

        # create all dates on which contributions will be made
        dates = []
        current_date = self.start

        while current_date <= self.retire:
            dates.append(current_date)
            current_date += relativedelta(months=1)

        self.cont_dates = dates

    # load fund data to an object for calculations
    def load_data(self, data):
        for col in data:
            data[col] = data[col].fillna(0.0)
        self.funds = data

    # return the price of an equity or bond on a given date
    def get_price(self, date, col):
        # allow for the fact that not al days have prices
        try:
            price = self.funds[self.funds["date"] == date][col].item()
        except:
            # iterate until finding the next day when there is a price
            while (len(self.funds[self.funds["date"] == date]) == 0) or (
                    self.funds[self.funds["date"] == date][col].item() == 0):
                date = date + timedelta(days=1)
            price = self.funds[self.funds["date"] == date][col].item()

        return price

    # calcualte the amount by which to decrease equities and increase proportion of bonds to retirement date
    def derisk_strategy(self, target_weight, derisk_years):
        self.derisk_years = derisk_years
        self.derisk_target = target_weight
        self.start_derisk_date = self.retire - relativedelta(years=self.derisk_years)
        self.derisk_months = self.derisk_years * 12
        self.derisk_perc_change = round((1 - self.derisk_target) / self.derisk_months, 6)

    # use algebra to calculate purchase units
    def calculate_purchase_units(self, curr_e, curr_b, price_e, price_b, contribution, target_bond_ratio):
        A = np.array([
            [price_e, price_b],
            [-target_bond_ratio, (1 - target_bond_ratio)]
        ])

        B = np.array([
            contribution,
            target_bond_ratio * curr_e - (1 - target_bond_ratio) * curr_b
        ])

        try:
            delta_q = np.linalg.solve(A, B)
            units_e = round(delta_q[0], 6)
            units_b = round(delta_q[1], 6)
            return units_e, units_b
        except np.linalg.LinAlgError:
            return None

    # accumulate the pension, including hitting the derisk threshold and then balance the funds accordingly
    def accumulate(self):

        # create all dates on which contributions will be made
        dates = []
        current_date = self.start
        i = 1
        while current_date <= self.retire:
            dates.append(current_date)
            current_date += relativedelta(months=1)

        # generate the bond proportions for the corresponding date
        current_date = self.start
        bond_prop = list()
        while current_date <= self.start_derisk_date:
            bond_prop.append(0)
            current_date += relativedelta(months=1)
        for m in range(self.derisk_months):
            bond_prop.append(m * self.derisk_perc_change)

        # initialise lists to store results of accumulation
        date_ls = list()
        cont_ls = list()
        ety_price_ls = list()
        ety_purchased_ls = list()
        ety_cumsum_ls = list()
        ety_target_ls = list()
        bnd_price_ls = list()
        bnd_purchased_ls = list()
        bnd_cumsum_ls = list()
        bnd_target_ls = list()

        # iterate through all the dates and purchase funds
        ety_cumsum = 0
        bnd_cumsum = 0
        for i, date_ in enumerate(dates):
            # return fund prices
            ety_price = self.get_price(date_, "ety_open_price")
            bnd_price = self.get_price(date_, "bnd_open_price")

            # calculate the amount of each fund to purchase
            e_to_buy, b_to_buy = self.calculate_purchase_units(ety_cumsum, bnd_cumsum, ety_price, bnd_price, self.cont,
                                                               bond_prop[i])

            # add on the quantity purchased
            ety_cumsum += e_to_buy
            bnd_cumsum += b_to_buy

            # append results to list
            date_ls.append(date_)
            cont_ls.append(self.cont)
            ety_price_ls.append(ety_price)
            ety_purchased_ls.append(e_to_buy)
            ety_cumsum_ls.append(ety_cumsum)
            ety_target_ls.append(1 - bond_prop[i])
            bnd_price_ls.append(bnd_price)
            bnd_purchased_ls.append(b_to_buy)
            bnd_cumsum_ls.append(bnd_cumsum)
            bnd_target_ls.append(bond_prop[i])



        # compile into dataframe
        data = {
            "date": date_ls,
            "cont": cont_ls,
            "ety_price": ety_price_ls,
            "ety_purchased": ety_purchased_ls,
            "ety_cumsum": ety_cumsum_ls,
            "ety_target": ety_target_ls,
            "bnd_price": bnd_price_ls,
            "bnd_purchased": bnd_purchased_ls,
            "bnd_cumsum": bnd_cumsum_ls,
            "bnd_target": bnd_target_ls
        }
        df_accum = pd.DataFrame(data)

        # calculate total cumulative values
        df_accum["ety_cumsum_value"] = df_accum["ety_cumsum"] * df_accum["ety_price"]
        df_accum["bnd_cumsum_value"] = df_accum["bnd_cumsum"] * df_accum["bnd_price"]
        df_accum["portfolio_value"] = round(df_accum["ety_cumsum_value"] + df_accum["bnd_cumsum_value"], 2)

        return df_accum