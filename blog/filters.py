import django_filters

from .models import Post


class PostFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="category__slug",
        lookup_expr="iexact",
    )
    tag = django_filters.CharFilter(
        field_name="tags__slug",
        lookup_expr="iexact",
    )

    class Meta:
        model = Post
        fields = (
            "category",
            "tag",
            "is_featured",
        )