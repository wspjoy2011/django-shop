from pathlib import Path
from typing import Tuple, Union

import pandas as pd

from etl.dto import (
    MasterCategoryDTO,
    SubCategoryDTO,
    ArticleTypeDTO,
    BaseColourDTO,
    SeasonDTO,
    UsageTypeDTO,
    ProductDTO,
    ImageDTO,
    CatalogResultDTO,
)


class CatalogCSVExtractTransformer:
    """Extract & Transform pipeline for products and images CSV files."""

    def __init__(self, styles_path: Union[str, Path], images_path: Union[str, Path]) -> None:
        self._styles_path = Path(styles_path)
        self._images_path = Path(images_path)

    def execute(self) -> CatalogResultDTO:
        """Run extract + transform and return a CatalogResultDTO."""
        styles_dataframe, images_dataframe = self._extract()
        return self._transform(styles_dataframe, images_dataframe)

    def _extract(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Read raw CSV files."""
        styles_dataframe = pd.read_csv(
            self._styles_path,
            skipinitialspace=True,
            dtype={
                "product_id": "Int64",
                "year": "Int64",
            },
            keep_default_na=True,
        )
        images_dataframe = pd.read_csv(
            self._images_path,
            skipinitialspace=True,
            dtype={"filename": "string", "link": "string"},
            keep_default_na=True,
        )
        return styles_dataframe, images_dataframe

    @staticmethod
    def _none_if_nan(value):
        """Convert NaN/NA/empty strings to None."""
        if isinstance(value, str):
            return value if value.strip() != "" else None
        return None if pd.isna(value) else value

    def _transform(
        self, styles_dataframe: pd.DataFrame, images_dataframe: pd.DataFrame
    ) -> CatalogResultDTO:
        """Normalize data and build DTO collections."""

        master_categories = [
            MasterCategoryDTO(name=name)
            for name in sorted(styles_dataframe["master_category"].dropna().unique())
        ]

        sub_categories = [
            SubCategoryDTO(master_category=row.master_category, name=row.sub_category)
            for row in (
                styles_dataframe[["master_category", "sub_category"]]
                .dropna()
                .drop_duplicates()
                .itertuples(index=False)
            )
        ]

        article_types = [
            ArticleTypeDTO(sub_category=row.sub_category, name=row.article_type)
            for row in (
                styles_dataframe[["sub_category", "article_type"]]
                .dropna()
                .drop_duplicates()
                .itertuples(index=False)
            )
        ]

        base_colours = [
            BaseColourDTO(name=name)
            for name in sorted(styles_dataframe["base_colour"].dropna().unique())
        ]

        seasons = [
            SeasonDTO(name=name)
            for name in sorted(styles_dataframe["season"].dropna().unique())
        ]

        usage_types = [
            UsageTypeDTO(name=name)
            for name in sorted(styles_dataframe["usage"].dropna().unique())
        ]

        products = []
        for row in styles_dataframe.itertuples(index=False):
            products.append(
                ProductDTO(
                    product_id=int(row.product_id),
                    gender=str(row.gender),
                    year=int(row.year) if pd.notna(row.year) else None,
                    product_display_name=self._none_if_nan(getattr(row, "product_display_name", None)),
                    article_type=str(row.article_type),
                    base_colour=self._none_if_nan(getattr(row, "base_colour", None)),
                    season=self._none_if_nan(getattr(row, "season", None)),
                    usage=self._none_if_nan(getattr(row, "usage", None)),
                )
            )

        images_dataframe = images_dataframe.copy()
        images_dataframe["product_id"] = (
            images_dataframe["filename"]
            .str.split(".")
            .str[0]
            .astype("Int64")
        )

        images = [
            ImageDTO(product_id=int(row.product_id), image_url=str(row.link))
            for row in images_dataframe[["product_id", "link"]].dropna().itertuples(index=False)
        ]

        return CatalogResultDTO(
            master_categories=master_categories,
            sub_categories=sub_categories,
            article_types=article_types,
            base_colours=base_colours,
            seasons=seasons,
            usage_types=usage_types,
            products=products,
            images=images,
        )
