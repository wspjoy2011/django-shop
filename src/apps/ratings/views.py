from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.db import transaction

from apps.catalog.models import Product
from .models import Like, Dislike, Rating


class LikeToggleView(LoginRequiredMixin, View):

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            existing_like = Like.objects.filter(user=user, product=product).first()

            if existing_like:
                existing_like.delete()
                action = 'unliked'
            else:
                Dislike.objects.filter(user=user, product=product).delete()

                Like.objects.create(user=user, product=product)
                action = 'liked'

        likes_count = Like.objects.filter(product=product).count()
        dislikes_count = Dislike.objects.filter(product=product).count()

        return JsonResponse({
            'action': action,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count,
        })


class DislikeToggleView(LoginRequiredMixin, View):

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            existing_dislike = Dislike.objects.filter(user=user, product=product).first()

            if existing_dislike:
                existing_dislike.delete()
                action = 'undisliked'
            else:
                Like.objects.filter(user=user, product=product).delete()

                Dislike.objects.create(user=user, product=product)
                action = 'disliked'

        likes_count = Like.objects.filter(product=product).count()
        dislikes_count = Dislike.objects.filter(product=product).count()

        return JsonResponse({
            'action': action,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count,
        })


class RatingCreateUpdateView(LoginRequiredMixin, View):

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        try:
            score = int(request.POST.get('score', 0))
            if score < 1 or score > 5:
                return JsonResponse({'error': 'Score must be between 1 and 5'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid score value'}, status=400)

        with transaction.atomic():
            rating, created = Rating.objects.update_or_create(
                user=user,
                product=product,
                defaults={'score': score}
            )

            action = 'rated' if created else 'updated'

        ratings = Rating.objects.filter(product=product)
        ratings_count = ratings.count()
        avg_rating = sum(r.score for r in ratings) / ratings_count if ratings_count > 0 else 0.0

        return JsonResponse({
            'action': action,
            'score': score,
            'avg_rating': round(avg_rating, 1),
            'ratings_count': ratings_count,
        })


class RatingDeleteView(LoginRequiredMixin, View):

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        user = request.user

        with transaction.atomic():
            try:
                rating = Rating.objects.get(user=user, product=product)
                rating.delete()
                action = 'removed'
            except Rating.DoesNotExist:
                return JsonResponse({'error': 'Rating not found'}, status=404)

        ratings = Rating.objects.filter(product=product)
        ratings_count = ratings.count()
        avg_rating = sum(r.score for r in ratings) / ratings_count if ratings_count > 0 else 0.0

        return JsonResponse({
            'action': action,
            'avg_rating': round(avg_rating, 1),
            'ratings_count': ratings_count,
        })
