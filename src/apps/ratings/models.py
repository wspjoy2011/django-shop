from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q, UniqueConstraint, CheckConstraint

User = get_user_model()


class Rating(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ratings",
        db_index=True
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="ratings",
        db_index=True
    )
    score = models.PositiveSmallIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=('user', 'product'), name='uniq_user_product_rating'),
            CheckConstraint(check=Q(score__gte=1) & Q(score__lte=5), name='score_between_1_and_5'),
        ]

        indexes = [
            models.Index(fields=['product', 'score'], name='idx_rating_product_score'),
            models.Index(fields=['product'], name='idx_rating_product'),
            models.Index(fields=['product', '-score'], name='idx_rating_product_score_desc'),
        ]

    def __str__(self):
        return f"{self.user} rated {self.product} as {self.score}"


class Like(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="likes",
        db_index=True
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="likes",
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=('user', 'product'), name='uniq_user_product_like'),
        ]
        indexes = [
            models.Index(fields=['product'], name='idx_like_product'),
            models.Index(fields=['product', 'user'], name='idx_like_product_user'),
            models.Index(fields=['product', '-created_at'], name='idx_like_product_created_desc'),
        ]

    def __str__(self):
        return f"{self.user} liked {self.product}"


class Dislike(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dislikes",
        db_index=True
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="dislikes",
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=('user', 'product'), name='uniq_user_product_dislike'),
        ]
        indexes = [
            models.Index(fields=['product'], name='idx_dislike_product'),
            models.Index(fields=['product', 'user'], name='idx_dislike_prod_user'),
            models.Index(fields=['product', '-created_at'], name='idx_dislike_prod_created'),
        ]

    def __str__(self):
        return f"{self.user} disliked {self.product}"
