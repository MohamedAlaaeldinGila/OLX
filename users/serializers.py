from rest_framework import serializers
from .models import UserProfile, Notification , NotificationType
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile

User = get_user_model()
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = UserProfile
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'password', 'password2')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'user_type': {'default': 'customer'},
        }
    
    def validate(self, attrs):
        print("🔍 DEBUG: Starting validation")
        print(f"🔍 DEBUG: Received data - {attrs}")
        
        username = attrs.get('username')
        if username and UserProfile.objects.filter(username=username).exists():
            print(f"❌ DEBUG: Username '{username}' already exists")
            raise serializers.ValidationError({"username": "This username is already taken."})
        else:
            print(f"✅ DEBUG: Username '{username}' is available")

        email = attrs.get('email')
        if email and UserProfile.objects.filter(email=email).exists():
            print(f"❌ DEBUG: Email '{email}' already exists")
            raise serializers.ValidationError({"email": "This email is already registered."})
        else:
            print(f"✅ DEBUG: Email '{email}' is available")

        

        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        print("✅ DEBUG: All validations passed")
        return attrs
    
    def create(self, validated_data):
        print("🔍 DEBUG: Starting user creation")
        print(f"🔍 DEBUG: Validated data - {validated_data}")

        validated_data.pop('password2')
        password = validated_data.pop('password')
        print(f"🔍 DEBUG: Creating user with - {validated_data}")

        if 'user_type' not in validated_data:
            validated_data['user_type'] = 'customer'

        try:
            user = UserProfile.objects.create_user(**validated_data)
            user.set_password(password)
            user.is_active = True
            user.save()
            print(f"✅ DEBUG: User '{user.username}' created successfully")
        except Exception as e:
            print(f"❌ DEBUG: Error creating user - {e}")
            raise serializers.ValidationError({"error": "Failed to create user."})
            
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class UserProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'date_of_birth', 
            'address'
        ]
        read_only_fields = ['created_at', 'updated_at']

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'email', 'phone', 'address')

    def update(self, instance, validated_data):
        user = instance
        user.first_name = validated_data.get('first_name', user.first_name)
        user.last_name = validated_data.get('last_name', user.last_name)
        user.email = validated_data.get('email', user.email)
        user.phone = validated_data.get('phone', user.phone)
        user.address = validated_data.get('address', user.address)
        user.save()
        return user

"""class UserProfileUpdateSerializer(serializers.ModelSerializer):
    user = UserUpdateSerializer()
    
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name','phone','address']
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        
        # Update User model
        if user_data:
            #user = instance.user
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            #user.email = user_data.get('email', user.email)
            user.phone = user_data.get('phone', user.phone)
            user.address = user_data.get('address', user.address)
            user.save()
        
        # Update UserProfile model
        return super().update(instance, validated_data)"""

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

class NotificationSerializer(serializers.ModelSerializer):

    notification_type_name = serializers.CharField(source = 'notification_type.name', read_only = True)

    class Meta():
        model = Notification
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'read_at']


