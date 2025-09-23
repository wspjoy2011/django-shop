from rest_framework.pagination import CursorPagination


class FavoriteItemsCursorPagination(CursorPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 120
    ordering = ('position', '-created_at', 'id')
