from rest_framework import serializers
from .models import Product, Category, Profile
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ProductSerializer(serializers.ModelSerializer):
    # This nested serializer shows the full category info instead of just an ID
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock', 'category', 'vendor',
            'created_at', 'weight', 'material_type', 'transport_distance', 'transport_mode',
            'energy_usage', 'grid_intensity', 'co2_saved', 'co2_baseline', 'actual_co2', 'eco_score',
        ]

    def get_eco_score(self, obj):
        return obj.eco_score  # Assuming `eco_score` is a property in the Product model

    # def validate(self, data):
    #     # Check if the user is an admin
    #     user = self.context['request'].user
    #     if not user.is_staff:  # `is_staff` is True for admin accounts
    #         # Restrict admin-only fields
    #         restricted_fields = ['carbon_footprint', 'material_sustainability', 'longevity', 'energy_usage', 'grid_intensity']
    #         for field in restricted_fields:
    #             if field in data:
    #                 raise serializers.ValidationError({field: "This field can only be set by an admin."})
    #     return data

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['role', 'shop_name', 'bio']

class UserSerializer(serializers.ModelSerializer):
    # This allows us to see the profile data inside the user data
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']

class UserMeSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role')

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']