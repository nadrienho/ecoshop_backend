from rest_framework import permissions

class IsVendorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow vendors to edit or create objects.
    Everyone can see the list (Read Only).
    """
    def has_permission(self, request, view):
        # 1. Allow any safe method (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # 2. For POST, PUT, DELETE, check if user is logged in AND is a vendor
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.profile.role == 'vendor'
        )