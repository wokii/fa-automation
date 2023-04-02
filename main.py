import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import csv

# TODO: use decimal instead of float
#  https://stackoverflow.com/questions/19473770/how-to-avoid-floating-point-errors


@dataclass
class Row:
    name: str  # first column
    current_year: float  # second column
    last_year: float  # third column
    difference: float = field(init=False)
    ratio: Optional[str] = field(init=False)

    def __post_init__(self):
        try:
            if not isinstance(self.current_year, float):
                self.current_year = float(self.current_year)
            if not isinstance(self.last_year, float):
                self.last_year = float(self.last_year)

            self.difference = self.current_year - self.last_year
            self.ratio = self.calculate_ratio(
                self.difference, self.last_year, self.current_year, self.last_year
            )
        except Exception as e:
            print(f"failed to parse row {self.__dict__} because of empty fields")
            self.difference = None
            self.ratio = None

    @staticmethod
    def calculate_ratio(difference, base, current_year, last_year):
        if current_year * last_year < 0:
            return None
        ratio = difference / base
        return ratio


class Year(Enum):
    CURRENT_YEAR = 1
    LAST_YEAR = 2


ADDITIONAL_ROWS = {
    "Current Ratio": (
        (lambda current_asset, current_liability: current_asset / current_liability),
        "current_asset",
        "current_liability",
    ),
    "Debt to Equity Ratio": (
        (lambda ncib_debt, equity: ncib_debt / equity),
        "ncib_debt",
        "equity",
    ),
    "Debt Service Coverage Ratio": (
        (lambda ebit, interest_costs, ncib_debt: ebit / (interest_costs + ncib_debt)),
        "ebit",
        "interest_costs",
        "ncib_debt",
    ),
}


class Table:
    def __init__(self, row_name_index_dict=None, rows=None):
        self.rows: list[Row] = rows or []
        self.current_asset_row_index = 7
        self.current_liability_row = 10
        self.row_name_index_dict = {
            "current_asset": 7,
            "current_liability": 10,
            "ncib_debt": 9,  # non-current interest-bearing debt
            "equity": 12,
            "ebit": 2,
            "interest_costs": 3,
        }

    def get_values_from_lambda_tuple(self, lambda_func, *column_names):
        current_year_res = lambda_func(
            *[
                self.get_row_value_by_name(column_name, Year.CURRENT_YEAR)
                for column_name in column_names
            ]
        )
        last_year_res = lambda_func(
            *[
                self.get_row_value_by_name(column_name, Year.LAST_YEAR)
                for column_name in column_names
            ]
        )

        return current_year_res, last_year_res

    def generate_additional_rows(self):
        for column_name, lambda_tuple in ADDITIONAL_ROWS.items():
            try:
                current_year_value, last_year_value = self.get_values_from_lambda_tuple(
                    *lambda_tuple
                )
                self.rows.append(Row(column_name, current_year_value, last_year_value))
            except Exception as e:
                print(f"error while generate_additional_rows {column_name}, e {e}")
                self.rows.append(Row(column_name, "", ""))

    def get_row_value_by_name(self, row_name: str, year: Year):
        row_index = self.row_name_index_dict[row_name]

        if year is Year.LAST_YEAR:
            return self.rows[row_index].last_year
        elif year is Year.CURRENT_YEAR:
            return self.rows[row_index].current_year
        else:
            raise Exception("unsupported year type in get_row_value_by_name")

    def add_row(self, row: Row):
        self.rows.append(row)

    # def add_current_ratio_row(self):
    #     row_name = "Current Ratio"
    #     try:
    #         current_year_asset = self.get_row_value_by_name("current_asset", Year.CURRENT_YEAR)
    #         current_year_liability = self.get_row_value_by_name("current_liability", Year.CURRENT_YEAR)
    #
    #         last_year_asset = self.get_row_value_by_name("current_asset", Year.LAST_YEAR)
    #         last_year_liability = self.get_row_value_by_name("current_liability", Year.LAST_YEAR)
    #         print(f"current_year_asset {current_year_asset} \n current_year_liability {current_year_liability} \n,"
    #               f"last_year_asset {last_year_asset}, \n last_year_liability{last_year_liability}" )
    #
    #
    #         self.rows.append(
    #             Row(
    #                 row_name,
    #                 current_year_asset / current_year_liability,
    #                 last_year_asset / last_year_liability,
    #             )
    #         )
    #     except Exception as e:
    #         print(f"failed to produce add_current_ratio_row, error: {e}")
    #         print(f"self length {len(self.rows)}")


def analyse_file(input_csv_file_name, delimiter=",", output_csv_file_name=None):
    field_formatting_functions = {
        "ratio": lambda x: "{:.2%}".format(x) if x else "",
        "difference": lambda x: "{:.2f}".format(x) if x else "",
    }
    table = Table()
    with open(input_csv_file_name, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        # print(list(spamreader))
        for row in reader:
            print("reading, row", row)
            r = Row(*row.values())
            print("*row.values()", *row.values())
            print("processed row", r)
            table.add_row(r)
            # print(r)
            # print(r.__dict__)

    table.generate_additional_rows()

    print("fieldanmes: ", list(r.__dict__.keys()))
    with open(
        output_csv_file_name
        or f"result_{datetime.date.today().strftime('%m-%d-%y')}.csv",
        "w",
        newline="",
    ) as result_csv, open(
        f"result_{datetime.date.today().strftime('%m-%d-%y')}.csv", "w"
    ) as result_txt:
        fieldnames = list(r.__dict__.keys())
        writer = csv.DictWriter(result_csv, fieldnames=fieldnames)
        writer.writeheader()

        for row in table.rows:
            row_dict = {
                k: field_formatting_functions.get(k, lambda x: x)(v)
                for k, v in row.__dict__.items()
            }
            writer.writerow(row_dict)


analyse_file("sample.csv")

# def test_row():
#     row_0 = Row("total_asset", 200, 50)
#     print(row_0)
#
#
# test_row()
