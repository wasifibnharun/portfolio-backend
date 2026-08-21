from django.contrib import admin

from .models import (
    ContactMessage,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "headline",
        "email",
        "location",
        "years_of_experience",
        "is_available_for_hire",
        "updated_at",
    )
    search_fields = (
        "full_name",
        "headline",
        "bio",
        "email",
        "location",
    )
    list_filter = (
        "is_available_for_hire",
        "location",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        if Profile.objects.exists():
            return False

        return super().has_add_permission(request)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "proficiency",
        "is_featured",
        "display_order",
        "updated_at",
    )
    search_fields = ("name", "icon")
    list_filter = (
        "category",
        "is_featured",
        "created_at",
        "updated_at",
    )
    list_editable = (
        "proficiency",
        "is_featured",
        "display_order",
    )
    ordering = ("display_order", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "company",
        "employment_type",
        "location",
        "start_date",
        "end_date",
        "is_current",
        "display_order",
    )
    search_fields = (
        "role",
        "company",
        "location",
        "description",
    )
    list_filter = (
        "employment_type",
        "is_current",
        "start_date",
        "created_at",
    )
    list_editable = ("display_order",)
    ordering = ("-start_date", "display_order")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = (
        "institution",
        "degree",
        "field_of_study",
        "start_year",
        "end_year",
        "grade",
        "updated_at",
    )
    search_fields = (
        "institution",
        "degree",
        "field_of_study",
        "description",
    )
    list_filter = (
        "start_year",
        "end_year",
        "created_at",
        "updated_at",
    )
    ordering = ("-start_year",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "is_featured",
        "completed_date",
        "display_order",
        "updated_at",
    )
    search_fields = (
        "title",
        "summary",
        "description",
        "tech_stack__name",
    )
    list_filter = (
        "category",
        "is_featured",
        "tech_stack",
        "completed_date",
        "created_at",
    )
    list_editable = (
        "is_featured",
        "display_order",
    )
    filter_horizontal = ("tech_stack",)
    readonly_fields = (
        "slug",
        "created_at",
        "updated_at",
    )
    ordering = ("display_order", "-completed_date")


@admin.action(description="Mark selected messages as read")
def mark_messages_read(modeladmin, request, queryset):
    queryset.update(is_read=True)


@admin.action(description="Mark selected messages as unread")
def mark_messages_unread(modeladmin, request, queryset):
    queryset.update(is_read=False)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "name",
        "email",
        "is_read",
        "created_at",
    )
    search_fields = (
        "name",
        "email",
        "subject",
        "message",
    )
    list_filter = (
        "is_read",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "name",
        "email",
        "subject",
        "message",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
    actions = (
        mark_messages_read,
        mark_messages_unread,
    )

    def has_add_permission(self, request):
        return False