import json

from django import forms
from django.db.models import Max

from .mixins import CategoryFormMixin
from .models import Product, ArticleType, SubCategory, MasterCategory


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
        self._set_initial_product_id()
        self._set_field_styles()
        self._set_category_fields()

    def _set_initial_product_id(self):
        is_new_product = not self.instance.pk
        is_form_unbound = not hasattr(self, "data") or self.data.get("product_id") is None

        if is_new_product and is_form_unbound and not self.initial.get("product_id"):
            max_pid = Product.objects.aggregate(mx=Max("product_id"))["mx"] or 0
            self.fields["product_id"].initial = max_pid + 1
            self.fields["product_id"].widget.attrs["min"] = max(1, max_pid + 1)

    def _set_field_styles(self):
        for name, field in self.fields.items():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css_class)

    def _set_category_fields(self):
        article_types = ArticleType.objects.select_related("sub_category__master_category").all()
        article_map = {
            str(article_type.pk): {
                "sub": article_type.sub_category.name,
                "master": article_type.sub_category.master_category.name,
            }
            for article_type in article_types
        }
        self.fields["article_type"].widget.attrs["data-article-map"] = json.dumps(article_map)

        article_type_id = None
        if self.is_bound and self.data.get("article_type"):
            article_type_id = self.data["article_type"]
        elif self.instance.pk:
            article_type_id = self.instance.article_type_id

        if article_type_id and str(article_type_id) in article_map:
            categories = article_map[str(article_type_id)]
            self.fields["sub_category_display"].initial = categories["sub"]
            self.fields["master_category_display"].initial = categories["master"]


class MasterCategoryForm(CategoryFormMixin, forms.ModelForm):
    class Meta:
        model = MasterCategory
        fields = ['name']
        labels = {
            'name': 'Master Category Name',
        }
        help_texts = {
            'name': 'Enter master category name (e.g., "Clothing", "Footwear")',
        }


class SubCategoryForm(CategoryFormMixin, forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ['master_category', 'name']
        labels = {
            'master_category': 'Master Category',
            'name': 'Subcategory Name',
        }
        help_texts = {
            'master_category': 'Select master category',
            'name': 'Enter subcategory name (e.g., "Shirts", "Sneakers")',
        }

    def __init__(self, *args, **kwargs):
        master_category_id = kwargs.pop('master_category_id', None)
        super().__init__(*args, **kwargs)

        if master_category_id:
            self.fields['master_category'].initial = master_category_id
            self.fields['master_category'].queryset = MasterCategory.objects.filter(id=master_category_id)
            self.fields['master_category'].widget.attrs['readonly'] = True


class ArticleTypeForm(CategoryFormMixin, forms.ModelForm):
    class Meta:
        model = ArticleType
        fields = ['sub_category', 'name']
        labels = {
            'sub_category': 'Subcategory',
            'name': 'Article Type Name',
        }
        help_texts = {
            'sub_category': 'Select subcategory',
            'name': 'Enter article type name (e.g., "Casual Shirts", "Running Shoes")',
        }

    def __init__(self, *args, **kwargs):
        sub_category_id = kwargs.pop('sub_category_id', None)
        super().__init__(*args, **kwargs)

        if sub_category_id:
            self.fields['sub_category'].initial = sub_category_id
            self.fields['sub_category'].queryset = SubCategory.objects.filter(id=sub_category_id)
            self.fields['sub_category'].widget.attrs['readonly'] = True
