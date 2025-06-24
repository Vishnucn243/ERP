from rest_framework import permissions
from .models import Profile

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            try:
                profile = Profile.objects.get(user=request.user)
                return profile.role == 'Admin'
            except Profile.DoesNotExist:
                return False
        return False

class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            try:
                profile = Profile.objects.get(user=request.user)
                return profile.role in ['Admin', 'Manager']
            except Profile.DoesNotExist:
                return False
        return False

class CanEditEmployee(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        try:
            requester_profile = Profile.objects.get(user=request.user)
            target_profile = Profile.objects.get(user=obj)
            if requester_profile.role == 'Manager' and target_profile.role == 'Employee':
                return True
            if requester_profile.role == 'Admin':
                return True
            return False
        except Profile.DoesNotExist:
            return False

class CanEditOrDeleteUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow users to edit their own profile
        if request.user == obj:
            return True
            
        try:
            profile = Profile.objects.get(user=request.user)
            target_profile = Profile.objects.get(user=obj)
        except Profile.DoesNotExist:
            return False
            
        # Admin can edit/delete Managers and Employees, but not other Admins
        if profile.role == 'Admin':
            return target_profile.role in ['Manager', 'Employee']
        # Manager can only edit/delete Employees
        elif profile.role == 'Manager':
            return target_profile.role == 'Employee'
        # Employees can't edit/delete anyone else
        return False