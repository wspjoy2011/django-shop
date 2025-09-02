import json

from django import forms
from django.db.models import Max

from .models import Product, ArticleType


class ProductForm(forms.ModelForm):
    master_category_display = forms.CharField(
        label="Master category",
        required=False,
        disabled=True,
    )
    sub_category_display = forms.CharField(
        label="Sub-category",
        required=False,
        disabled=True,
    )

    class Meta:
        model = Product
        fields = [
            "product_id",
            "gender",
            "year",
            "product_display_name",
            "image_url",
            "article_type",
            "base_colour",
            "season",
            "usage_type",
        ]
        labels = {
            "product_id": "External Product ID",
            "gender": "Gender",
            "year": "Year",
            "product_display_name": "Product Name",
            "image_url": "Image URL",
            "article_type": "Article Type",
            "base_colour": "Base Colour",
            "season": "Season",
            "usage_type": "Usage",
        }
        help_texts = {
            "product_id": "Unique numeric ID from the source dataset.",
            "gender": "Target audience for this item.",
            "year": "Release/collection year.",
            "product_display_name": "Public display name of the product.",
            "image_url": "Direct link to the product image.",
            "article_type": "Specific item type within its sub-category (e.g., Shirts, Casual Shoes).",
            "base_colour": "Primary colour of the product.",
            "season": "Season associated with the product.",
            "usage_type": "Intended usage (e.g., Casual, Formal, Sports).",
        }

        widgets = {
            "product_display_name": forms.TextInput(attrs={"class": "form-control"}),
            "image_url": forms.URLInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            is_bound_with_value = bool(getattr(self, "data", None)) and self.data.get("product_id")
            has_initial_value = bool(self.initial.get("product_id"))
            if not is_bound_with_value and not has_initial_value:
                max_pid = Product.objects.aggregate(mx=Max("product_id"))["mx"] or 0
                self.fields["product_id"].initial = max_pid + 1
                self.fields["product_id"].widget.attrs.setdefault("min", max(1, max_pid + 1))

        for name, field in self.fields.items():
            if name in {"master_category_display", "sub_category_display"}:
                field.widget.attrs.setdefault("class", "form-control")
                continue
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

        article_map = {}
        for at in ArticleType.objects.select_related("sub_category__master_category").all():
            article_map[str(at.pk)] = {
                "sub": at.sub_category.name,
                "master": at.sub_category.master_category.name,
            }

        self.fields["article_type"].widget.attrs["data-article-map"] = json.dumps(article_map)

        at_obj = None
        if "article_type" in self.data and self.data.get("article_type"):
            try:
                at_obj = ArticleType.objects.select_related("sub_category__master_category").get(
                    pk=self.data.get("article_type")
                )
            except ArticleType.DoesNotExist:
                at_obj = None
        elif self.instance and self.instance.pk:
            at_obj = (
                ArticleType.objects.select_related("sub_category__master_category")
                .filter(pk=self.instance.article_type_id)
                .first()
            )

        if at_obj:
            self.fields["sub_category_display"].initial = at_obj.sub_category.name
            self.fields["master_category_display"].initial = at_obj.sub_category.master_category.name
