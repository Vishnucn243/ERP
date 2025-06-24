from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, LeaveRequest
from django.db import transaction, connection
from django.core.management import call_command
from django.core.cache import cache
from django.db import reset_queries
import logging

logger = logging.getLogger(__name__)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['role']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'profile']
        read_only_fields = ['id']

    def _refresh_database(self):
        """Force database refresh and clear caches"""
        try:
            cache.clear()
            reset_queries()
            logger.info("Database caches cleared in serializer")
        except Exception as e:
            logger.error(f"Error refreshing database: {e}")

    @transaction.atomic
    def create(self, validated_data):
        print("--- Creating User ---")
        print(f"Validated data: {validated_data}")
        
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)

        try:
            user = User.objects.create_user(**validated_data)
            if password:
                user.set_password(password)
                user.save()

            Profile.objects.create(user=user, **profile_data)
            
            # Force database refresh
            self._refresh_database()
            
            # Reload user from database to ensure we have fresh data
            user.refresh_from_db()
            
            print(f"--- User {user.username} created successfully ---")
            return user
        except Exception as e:
            print(f"--- Error creating user: {e} ---")
            raise e

    @transaction.atomic
    def update(self, instance, validated_data):
        print(f"--- Updating User: {instance.username} ---")
        print(f"Validated data: {validated_data}")

        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)

        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            if password:
                instance.set_password(password)

            instance.save()

            profile, created = Profile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

            # Force database refresh
            self._refresh_database()
            
            # Reload instance from database to ensure we have fresh data
            instance.refresh_from_db()
            
            print(f"--- User {instance.username} updated successfully ---")
            return instance
        except Exception as e:
            print(f"--- Error updating user: {e} ---")
            raise e

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'}, label='Confirm Password')
    role = serializers.ChoiceField(
        choices=[('Admin', 'Admin'), ('Manager', 'Manager'), ('Employee', 'Employee')],
        write_only=True,
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'role']
        extra_kwargs = {
            'email': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        role = validated_data.pop('role')
        password = validated_data.pop('password')

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        Profile.objects.create(user=user, role=role)
        return user

class LeaveRequestSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = LeaveRequest
        fields = ['id', 'user', 'start_date', 'end_date', 'reason', 'status', 'requested_at']
        read_only_fields = ['id', 'user', 'status', 'requested_at']
