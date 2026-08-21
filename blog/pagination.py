from rest_framework.pagination import PageNumberPagination


class PostPagination(PageNumberPagination):
    page_size = 6
    page_query_param = "page"


class CommentPagination(PageNumberPagination):
    page_size = 10
    page_query_param = "page"