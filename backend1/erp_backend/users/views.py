from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Profile, LeaveRequest
from .serializers import UserSerializer, RegisterSerializer, LeaveRequestSerializer
from .permissions import IsAdminOrManager, IsAdmin, CanEditOrDeleteUser
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.db import transaction, connection
from django.core.cache import cache
from django.db import reset_queries
import logging
from rest_framework.decorators import action

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    """
    Allows Admins and Managers to manage users.
    - Admin: full access (create, update, delete)
    - Manager: read-only
    - Employee: only sees self
    """
    queryset = User.objects.all().select_related('profile')
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return User.objects.none()

        try:
            profile = user.profile
            if profile.role in ['Admin', 'Manager']:
                # Force fresh query from database
                return User.objects.all().select_related('profile').order_by('id')
            else:
                return User.objects.filter(id=user.id)
        except Profile.DoesNotExist:
            return User.objects.none()

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            permission_classes = [IsAdminOrManager]
        elif self.action == 'create':
            permission_classes = [IsAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, CanEditOrDeleteUser]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def _clear_all_caches(self):
        """Clear all caches and force database refresh"""
        try:
            # Clear Django cache
            cache.clear()
            # Clear query cache
            reset_queries()
            logger.info("All caches cleared in viewset")
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        print("--- Creating user in viewset ---")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Clear all caches and force refresh
            self._clear_all_caches()
            print(f"--- User {user.username} created successfully in viewset ---")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print(f"--- User creation failed: {serializer.errors} ---")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        print("--- Updating user in viewset ---")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            user = serializer.save()
            # Clear all caches and force refresh
            self._clear_all_caches()
            print(f"--- User {user.username} updated successfully in viewset ---")
            return Response(serializer.data)
        print(f"--- User update failed: {serializer.errors} ---")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        print("--- Deleting user in viewset ---")
        instance = self.get_object()
        username = instance.username
        instance.delete()
        # Clear all caches and force refresh
        self._clear_all_caches()
        print(f"--- User {username} deleted successfully in viewset ---")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        """Override list to ensure fresh data"""
        print("--- Listing users in viewset ---")
        # Force fresh query
        self.queryset = User.objects.all().select_related('profile').order_by('id')
        return super().list(request, *args, **kwargs)

class RegisterView(generics.CreateAPIView):
    """
    Public API for user registration (not used for admin-managed user creation).
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

class ProfileView(APIView):
    """
    Returns the current user's profile (used in frontend for auth context).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)

class RefreshUsersView(APIView):
    """
    Force refresh the user list by clearing caches and returning fresh data.
    """
    permission_classes = [IsAdminOrManager]

    def get(self, request):
        try:
            # Clear all caches
            cache.clear()
            reset_queries()
            
            # Force fresh query
            users = User.objects.all().select_related('profile').order_by('id')
            serializer = UserSerializer(users, many=True)
            
            logger.info("User list refreshed successfully")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error refreshing user list: {e}")
            return Response(
                {"error": "Failed to refresh user list"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all().select_related('user')
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.profile.role == 'Admin':
            return LeaveRequest.objects.all().select_related('user')
        else:
            return LeaveRequest.objects.filter(user=user).select_related('user')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        leave = self.get_object()
        if request.user.profile.role == 'Admin':
            leave.status = 'Approved'
            leave.save()
            return Response({'status': 'Leave approved'})
        return Response({'error': 'Not authorized'}, status=403)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        leave = self.get_object()
        if request.user.profile.role == 'Admin':
            leave.status = 'Rejected'
            leave.save()
            return Response({'status': 'Leave rejected'})
        return Response({'error': 'Not authorized'}, status=403)
