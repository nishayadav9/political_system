from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role

class UserAdmin(BaseUserAdmin):
    list_display = ('full_name', 'mobile_number', 'role', 'is_staff', 'is_superuser')
    
    fieldsets = (
    (None, {'fields': ('mobile_number', 'password')}),
    ('Personal info', {'fields': (
        'full_name', 'email', 'permanent_address', 'current_address', 'role',
        'assigned_state', 'assigned_district', 'assigned_block', 'assigned_panchayat'
    )}),


        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'mobile_number', 'full_name', 'role', 'password1', 'password2',
                'assigned_state', 'assigned_district', 'assigned_block', 'assigned_panchayat'  # ✅ Add these
            ),
        }),
    )
    
    search_fields = ('mobile_number', 'full_name')
    ordering = ('mobile_number',)

admin.site.register(User, UserAdmin)
admin.site.register(Role)
