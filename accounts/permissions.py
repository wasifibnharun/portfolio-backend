from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Public users can read, but only an authenticated superuser can write.
    """

    message = "Only the site owner can perform this action."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_superuser
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
    

class IsOwner(BasePermission):
    """
    Allow access only to an authenticated superuser.
    """

    message = "Only the site owner can access this endpoint."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_superuser
        )