class RatingActionChoices:
    LIKED = 'liked'
    UNLIKED = 'unliked'

    DISLIKED = 'disliked'
    UNDISLIKED = 'undisliked'

    RATED = 'rated'
    UPDATED = 'updated'
    REMOVED = 'removed'

    ALL_CHOICES = [
        LIKED, UNLIKED, DISLIKED, UNDISLIKED,
        RATED, UPDATED, REMOVED
    ]

    LIKE_CHOICES = [LIKED, UNLIKED]
    DISLIKE_CHOICES = [DISLIKED, UNDISLIKED]
    RATING_CHOICES = [RATED, UPDATED, REMOVED]


class FavoriteActionChoices:
    ADDED = 'added'
    REMOVED = 'removed'

    CREATED = 'created'
    SET_DEFAULT = 'set_default'

    ALL_CHOICES = [ADDED, REMOVED, CREATED, SET_DEFAULT]

    TOGGLE_CHOICES = [ADDED, REMOVED]
    COLLECTION_CHOICES = [CREATED, SET_DEFAULT]
