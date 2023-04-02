import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import csv
import re

# TODO: use decimal instead of float
#  https://stackoverflow.com/questions/19473770/how-to-avoid-floating-point-errors

CURRENCY = "$"
UNIT = "m"  # k, m, b

DEFAULT_COLUMN_ROW_INDEX = {
    "current_asset": 7,
    "current_liability": 10,
    "ncib_debt": 9,  # non-current interest-bearing debt
    "equity": 13,
    "ebit": 2,
    "interest_costs": 3,
    "debt_service_of_principal": 12,
    "revenue": 1,
    "profit": 4,
    "assets": 8,
    "liabilities": 11,
    "cash_flow": 15,
    "current_ratio": None,
    "dte_ratio": None,
    "dsc_ratio": None,
}


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
        (
            lambda ebit, interest_costs, debt_service_of_principal: ebit
            / (interest_costs + debt_service_of_principal)
        ),
        "ebit",
        "interest_costs",
        "debt_service_of_principal",
    ),
}



TXT_SECTION_NAME_TO_COLUMN_NAME = {
    "Revenue": "revenue",
    "Profit": "profit",
    "Assets, Liabilities and Equity": {
        "Assets": "assets",
        "Liabilities": "liabilities",
        "Equity": "equity",
    },
    "Current ratio": "current_ratio",
    "Debt-to-equity and debt service coverage": {
        "Debt-to-equity ratio": "dte_ratio",
        "Debt service coverage ratio": "dsc_ratio",
    },
    "Cash flows": "cash_flow"
}

SECTION_WITH_UNIT = ["Revenue", "Profit", "Assets, Liabilities and Equity", "Cash flows"]


FIELD_FORMATTING_FUNCTIONS = {
    "ratio": lambda x: "{:.2%}".format(x) if x else "",
    "difference": lambda x: "{:.2f}".format(x) if x else "",
    "current_year": lambda x: remove_tail_dot_zeros("{:,.2f}".format(x)) if x else "",
    "last_year": lambda x: remove_tail_dot_zeros("{:,.2f}".format(x)) if x else "",
}

COMPANY_NAME = "Wokki Company"
CURRENT_YEAR_NUMBER = 2023
LAST_YEAR_NUMBER = 2022

tail_dot_rgx = re.compile(r"(?:(\.)|(\.\d*?[1-9]\d*?))0+(?=\b|[^0-9])")


def remove_tail_dot_zeros(a):
    return tail_dot_rgx.sub(r"\2", a)


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


class Table:
    def __init__(self, row_name_index_dict=None, rows=None):
        self.rows: list[Row] = rows or []
        self.current_asset_row_index = 7
        self.current_liability_row = 10
        self.row_name_index_dict = row_name_index_dict or DEFAULT_COLUMN_ROW_INDEX

    def get_values_from_lambda_tuple(self, lambda_func, *column_names):
        current_year_res = lambda_func(
            *[
                self.get_row_by_name(column_name).current_year
                for column_name in column_names
            ]
        )
        last_year_res = lambda_func(
            *[
                self.get_row_by_name(column_name).last_year
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
                print("error while lambda_tuple:", lambda_tuple)
                self.rows.append(Row(column_name, "", ""))

            # populate the index for report
            if column_name == "Current Ratio":
                DEFAULT_COLUMN_ROW_INDEX["current_ratio"] = len(self.rows) - 1
            elif column_name == "Debt to Equity Ratio":
                DEFAULT_COLUMN_ROW_INDEX["dte_ratio"] = len(self.rows) - 1
            elif column_name == "Debt Service Coverage Ratio":
                DEFAULT_COLUMN_ROW_INDEX["dsc_ratio"] = len(self.rows) - 1

    def get_row_by_name(self, row_name: str) -> Row:
        row_index = self.row_name_index_dict[row_name]
        return self.rows[row_index]

    def add_row(self, row: Row):
        self.rows.append(row)


def generate(
    file, table: Table, structure_dict=TXT_SECTION_NAME_TO_COLUMN_NAME, inner=False, is_unit=False
):
    for index, (section_name, column_name) in enumerate(structure_dict.items()):
        prefix = "" if inner else f"{chr(index + ord('a'))}) "
        file.write(f"{prefix}{section_name} \n")
        need_unit = is_unit or section_name in SECTION_WITH_UNIT

        if isinstance(column_name, str):
            current_year_value = table.get_row_by_name(column_name).current_year
            last_year_value = table.get_row_by_name(column_name).last_year
            difference = table.get_row_by_name(column_name).difference
            ratio = table.get_row_by_name(column_name).ratio
            currency = CURRENCY if need_unit else ""
            unit = UNIT if need_unit else ""
            file.write(
                f"{COMPANY_NAME} has been {'an increase' if difference >= 0 else 'a decrease'} in {section_name.lower()} in "
                f"{LAST_YEAR_NUMBER} of {currency}{FIELD_FORMATTING_FUNCTIONS['difference'](difference)}{unit}({FIELD_FORMATTING_FUNCTIONS['ratio'](ratio)}) from "
                f"{currency}{FIELD_FORMATTING_FUNCTIONS['last_year'](last_year_value)}{unit} to {currency}{FIELD_FORMATTING_FUNCTIONS['current_year'](current_year_value)}{unit}. "
                f"The key factors driving this movement are: \n \n"
            )
            if ratio > 1:
                file.write("!!! ratio > 1.0, NEED MORE EXPLANATION")
        elif isinstance(column_name, dict):
            generate(file, table, column_name, inner=True, is_unit=need_unit)


def analyse_file(input_csv_file_name, delimiter=",", output_csv_file_name=None):
    table = Table()
    with open(input_csv_file_name, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            r = Row(*row.values())
            table.add_row(r)

    table.generate_additional_rows()

    with open(
        output_csv_file_name
        or f"result_{datetime.date.today().strftime('%m-%d-%y')}.csv",
        "w",
        newline="",
    ) as result_csv:
        fieldnames = list(r.__dict__.keys())
        writer = csv.DictWriter(result_csv, fieldnames=fieldnames)
        writer.writeheader()

        for row in table.rows:
            row_dict = {
                k: FIELD_FORMATTING_FUNCTIONS.get(k, lambda x: x)(v)
                for k, v in row.__dict__.items()
            }
            writer.writerow(row_dict)

    with open(
        f"result_{datetime.date.today().strftime('%m-%d-%y')}.txt", "w"
    ) as result_txt:
        generate(result_txt, table)


analyse_file("sample.csv")
