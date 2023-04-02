import datetime
from dataclasses import dataclass, field
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
        if not isinstance(self.current_year, float):
            self.current_year = float(self.current_year)
        if not isinstance(self.last_year, float):
            self.last_year = float(self.last_year)

        self.difference = self.current_year - self.last_year
        self.ratio = self.calculate_ratio(
            self.difference, self.last_year, self.current_year, self.last_year
        )

    @staticmethod
    def calculate_ratio(difference, base, current_year, last_year):
        if current_year * last_year < 0:
            return None
        ratio = difference / base
        return ratio


class Table:
    def __init__(self, rows=None, current_asset_row_index=1, current_liability_row=3):
        self.rows: list[Row] = rows or []
        self.current_asset_row_index = current_asset_row_index
        self.current_liability_row = current_liability_row

    def add_row(self, row: Row):
        self.rows.append(row)

    def add_current_ratio_row(self):
        row_name = "current_ratio"
        try:
            current_year_asset = self.rows[self.current_asset_row_index].current_year
            current_year_liability = self.rows[self.current_liability_row].current_year

            last_year_asset = self.rows[self.current_asset_row_index].last_year
            last_year_liability = self.rows[self.current_liability_row].last_year

            self.rows.append(
                Row(
                    row_name,
                    current_year_asset / current_year_liability,
                    last_year_asset / last_year_liability,
                )
            )
        except Exception as e:
            print(f"failed to produce add_current_ratio_row, error: {e}")
            print(f"self length {len(self.rows)}")


def analyse_file(input_csv_file_name, delimiter=",", output_csv_file_name=None):
    field_formatting_functions = {
        "ratio": lambda x: "{:.2%}".format(x) if x else "N/A",
        "difference": lambda x: "{:.2f}".format(x),
    }
    table = Table()
    with open(input_csv_file_name, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        # print(list(spamreader))
        for row in reader:
            r = Row(*row.values())
            table.add_row(r)
            print(r)
            print(r.__dict__)

    table.add_current_ratio_row()

    print("fieldanmes: ", list(r.__dict__.keys()))
    with open(
        output_csv_file_name
        or f"result_{datetime.date.today().strftime('%m-%d-%y')}.csv",
        "w",
        newline="",
    ) as result:
        fieldnames = list(r.__dict__.keys())
        writer = csv.DictWriter(result, fieldnames=fieldnames)
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
