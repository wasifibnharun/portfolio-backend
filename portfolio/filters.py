import django_filters

from .models import Project


class ProjectFilter(django_filters.FilterSet):
    tech = django_filters.CharFilter(
        method="filter_by_tech",
    )

    class Meta:
        model = Project
        fields = (
            "category",
            "is_featured",
            "tech",
        )

    def filter_by_tech(self, queryset, name, value):
        value = value.strip()

        if not value:
            return queryset

        if value.isdigit():
            return queryset.filter(
                tech_stack__id=int(value)
            ).distinct()

        return queryset.filter(
            tech_stack__name__iexact=value
        ).distinct()