from typing import Any, Optional
import pandas as pd

from pydantic import BaseModel, Field

# from llama_index.program.evaporate.df
class DataFrameRow(BaseModel):
    """Row in a DataFrame."""

    row_values: list[Any] = Field(
        ...,
        description="list of row values, where each value corresponds to a row key.",
    )


class DataFrameColumn(BaseModel):
    """Column in a DataFrame."""

    column_name: str = Field(..., description="Column name.")
    column_desc: Optional[str] = Field(..., description="Column description.")


class DataFrame(BaseModel):
    """Data-frame class.

    Consists of a `rows` field which is a list of dictionaries,
    as well as a `columns` field which is a list of column names.

    """

    description: Optional[str] = None

    columns: list[DataFrameColumn] = Field(..., description="list of column names.")
    rows: list[DataFrameRow] = Field(
        ...,
        description="""list of DataFrameRow objects. Each DataFrameRow contains \
        valuesin order of the data frame column.""",
    )

    def to_df(self) -> pd.DataFrame:
        """To dataframe."""
        return pd.DataFrame(
            [row.row_values for row in self.rows],
            columns=[col.column_name for col in self.columns],
        )


class DataFrameRowsOnly(BaseModel):
    """Data-frame with rows. Assume column names are already known beforehand."""

    rows: list[DataFrameRow] = Field(..., description="""list of row objects.""")

    def to_df(self, existing_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """To dataframe."""
        if existing_df is None:
            return pd.DataFrame([row.row_values for row in self.rows])
        else:
            new_df = pd.DataFrame([row.row_values for row in self.rows])
            new_df.columns = existing_df.columns
            # assume row values are in order of column names
            return pd.concat([existing_df, new_df], ignore_index=True)

