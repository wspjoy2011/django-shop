from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MasterCategoryDTO:
    name: str


@dataclass
class SubCategoryDTO:
    master_category: str
    name: str


@dataclass
class ArticleTypeDTO:
    sub_category: str
    name: str


@dataclass
class BaseColourDTO:
    name: str


@dataclass
class SeasonDTO:
    name: str


@dataclass
class UsageTypeDTO:
    name: str


@dataclass
class ProductDTO:
    product_id: int
    gender: str
    year: Optional[int] = None
    product_display_name: Optional[str] = None
    article_type: str = ""
    base_colour: Optional[str] = None
    season: Optional[str] = None
    usage: Optional[str] = None


@dataclass
class ImageDTO:
    product_id: int
    image_url: str


@dataclass
class CatalogResultDTO:
    master_categories: List[MasterCategoryDTO] = field(default_factory=list)
    sub_categories: List[SubCategoryDTO] = field(default_factory=list)
    article_types: List[ArticleTypeDTO] = field(default_factory=list)
    base_colours: List[BaseColourDTO] = field(default_factory=list)
    seasons: List[SeasonDTO] = field(default_factory=list)
    usage_types: List[UsageTypeDTO] = field(default_factory=list)
    products: List[ProductDTO] = field(default_factory=list)
    images: List[ImageDTO] = field(default_factory=list)
