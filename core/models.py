from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

# -------------------------------
# Role Model
# -------------------------------
from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.utils import timezone
from django.db.models.signals import post_migrate
from django.dispatch import receiver


# Role Model
# -------------------------------
class Role(models.Model):
    LEVEL_CHOICES = [
        ('state', 'State Level'),
        ('district', 'District Level'),
        ('block', 'Block Level'),
        ('core', 'Core Committee'),
        ('head_office', 'Head Office'),
        ('booth', 'Booth Level'),   # <-- Naya level add kiya

    ]

    role_name = models.CharField(max_length=100)  # e.g., State President, District Secretary
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    send_to_level = models.CharField(max_length=50, choices=LEVEL_CHOICES, blank=True, null=True)  # 👈 Ye hona chahiye agar chahiye
    send_to_user = models.ForeignKey('User', on_delete=models.CASCADE, null=True, blank=True, related_name='sent_roles')
    class Meta:
        unique_together = ('role_name', 'level')  # prevent duplicate roles per level

    def __str__(self):
        return f"{self.role_name} ({self.get_level_display()})"

# -------------------------------
# Signal to create default roles after migration
# -------------------------------
@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    if sender.name == 'core':  # Replace 'core' with your app name if different
        default_roles = {
            'state': [
                'State President',
                'State Vice President',
                'State General Secretary',
                'State Secretary',
                'State Treasurer',
                'State Spokesperson',
                'State IT/Media Cell In-charge',
                'State Youth Wing President',
                'State Mahila (Women) Wing President',
                'State SC/ST/OBC Minority Wing Head',
                'State Legal Cell Head'
            ],
            'district': [
                'District President',
                'District Vice President',
                'District General Secretary',
                'District Secretary',
                'District Treasurer',
                'District Spokesperson',
                'District Youth Wing President',
                'District Mahila Wing President',
                'District Minority Cell In-charge'
            ],
            'block': [
                'Block President',
                'Block Vice President',
                'Block General Secretary',
                'Block Secretary',
                'Block Treasurer',
                'Block Youth Wing Head',
                'Block Mahila Wing Head',
                'Block Minority Cell Head'
                
            ],
            'core': [
                'Core Member',
            ],
            'head_office': [
                'Head Office Admin',
            ],
             'booth': [   # <-- Naya booth level roles
                'Booth President',                # Head of party operations at the booth level
                'Booth Vice President',           # Assists in booth-level coordination
                'Booth Coordinator',              # Coordinates with Block-level leaders
                'Booth Youth Volunteer',          # Engages young voters and supporters
                'Booth Mahila Volunteer',         # Ensures women engagement and awareness
                'Booth Level Agent (BLA)',        # Oversees polling booth on election day
                'Booth In-charge (Voter List/Survey)',  # Maintains voter database and surveys
            ],
        }

        for level, roles in default_roles.items():
            for role_name in roles:
                Role.objects.get_or_create(role_name=role_name, level=level)
# -------------------------------
# Location Model
# -------------------------------
class Location(models.Model):
    state_name = models.CharField(max_length=100)
    district_name = models.CharField(max_length=100)
    block_name = models.CharField(max_length=100)
    panchayat_name = models.CharField(max_length=255, null=True, blank=True)  # ye hona chahiye

    pincode = models.CharField(max_length=10, null=True, blank=True)  # ✅ naya field

    def __str__(self):
        return f"{self.block_name}, {self.district_name}, {self.state_name}"


# -------------------------------
# User Manager
# -------------------------------
class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(username, password, **extra_fields)


# -------------------------------
# User Model
# -------------------------------
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group, Permission
from django.utils import timezone

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=100)
    father_or_mother_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])

    mobile_number = models.CharField(max_length=15, unique=True)
    alternate_mobile_number = models.CharField(max_length=15, null=True, blank=True)

    email = models.EmailField(unique=True)
    aadhar_or_govt_id = models.CharField(max_length=20)

    permanent_address = models.TextField()
    current_address = models.TextField(null=True, blank=True)

    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    block_tehsil_taluka = models.CharField(max_length=100)
    village_town_city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    # Foreign keys
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, related_name='users_with_this_role')
    location = models.ForeignKey('core.Location', on_delete=models.SET_NULL, null=True, blank=True)

    # Access control
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    access_start_time = models.DateTimeField(null=True, blank=True)
    access_end_time = models.DateTimeField(null=True, blank=True)

    # Role-specific fields
    designation = models.CharField(max_length=100, null=True, blank=True)
    area_of_responsibility = models.CharField(max_length=100, null=True, blank=True)
    political_experience_years = models.PositiveIntegerField(null=True, blank=True)
    previous_positions = models.TextField(null=True, blank=True)
    pan_card_number = models.CharField(max_length=20, null=True, blank=True)
    assigned_districts = models.TextField(null=True, blank=True)
    assigned_blocks = models.TextField(null=True, blank=True)
    local_area_knowledge = models.BooleanField(null=True, blank=True)
    booths_handled = models.PositiveIntegerField(null=True, blank=True)
    volunteer_experience = models.TextField(null=True, blank=True)
    reference_person_name = models.CharField(max_length=100, null=True, blank=True)
    reference_person_contact = models.CharField(max_length=15, null=True, blank=True)
    biography = models.TextField(null=True, blank=True)

    # Newly added fields
    booth_number = models.CharField(max_length=50, null=True, blank=True)
    ward_name = models.CharField(max_length=100, null=True, blank=True)
    assigned_area = models.CharField(max_length=100, null=True, blank=True)
    voter_id_number = models.CharField(max_length=50, null=True, blank=True)

    door_to_door = models.CharField(
        max_length=3,
        choices=[('Yes', 'Yes'), ('No', 'No')],
        null=True,
        blank=True
    )

    availability = models.CharField(
        max_length=10,
        choices=[('Full-Time', 'Full-Time'), ('Part-Time', 'Part-Time')],
        null=True,
        blank=True
    )

    assigned_state = models.CharField(max_length=100, null=True, blank=True)
    assigned_district = models.CharField(max_length=100, null=True, blank=True)
    assigned_block = models.CharField(max_length=100, null=True, blank=True)
    assigned_panchayat = models.CharField(max_length=255, blank=True, null=True)

    # File uploads
    photo = models.ImageField(upload_to='user_photos/', null=True, blank=True)
    id_proof = models.FileField(upload_to='id_proofs/', null=True, blank=True)
    address_proof = models.FileField(upload_to='address_proofs/', null=True, blank=True)
    digital_signature = models.FileField(upload_to='signatures/', null=True, blank=True)
    plain_password = models.CharField(max_length=128, null=True, blank=True, help_text="Temporarily stores the generated password for display in admin/manage page")

    # Permissions
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True,
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        verbose_name='user permissions',
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['full_name', 'mobile_number', 'email']

    objects = UserManager()  # Ensure your custom UserManager is properly implemented

    def __str__(self):
        return f"{self.username} ({self.full_name})"

    def has_role(self, role_name):
        if self.is_superuser and role_name == 'Head Office Admin':
            return True
        return self.role and self.role.role_name == role_name

    def has_valid_access(self):
        if not self.has_role('Core Member'):
            return True
        now = timezone.now()
        return self.access_start_time and self.access_end_time and self.access_start_time <= now <= self.access_end_time


class ComplaintFile(models.Model):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE, related_name='files')
    file_path = models.FileField(upload_to='complaint_files/')
    file_type = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.complaint.title} - {self.file_path.name}"
            

User = get_user_model()

# models.py


from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Complaint(models.Model):
    ISSUE_TYPES = [
        ('crime', 'Crime'),
        ('education', 'Education'),
        ('road', 'Road'),
        ('water_supply', 'Water Supply'),
        ('electricity', 'Electricity'),
        ('health', 'Health'),
        ('corruption', 'Corruption'),
        ('public_safety', 'Public Safety'),
        ('transportation', 'Transportation'),
        ('environment', 'Environment'),
        ('others', 'Others'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Solved', 'Solved'),
        ('Rejected', 'Rejected'),
    ]

    SEND_TO_CHOICES = [
        ('booth', 'Booth'),
        ('block', 'Block'),
        ('district', 'District'),
        ('state', 'State'),
        ('none', 'None'),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='complaints_created')

    name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=[('male','Male'),('female','Female'),('other','Other')])
    photo = models.ImageField(upload_to='complaint_photos/', null=True, blank=True)
    voter_id_image = models.ImageField(upload_to='voter_id_images/', null=True, blank=True)
    address = models.TextField()
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    block = models.CharField(max_length=100)
    panchayat = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    issue_type = models.CharField(max_length=50, choices=ISSUE_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    upload_photo = models.ImageField(upload_to='complaint_uploads/photos/', null=True, blank=True)
    upload_video = models.FileField(upload_to='complaint_uploads/videos/', null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    forward_to = models.CharField(max_length=150, blank=True, null=True)  # username
    forward_reason = models.TextField(blank=True, null=True)  # reason
    public_notice = models.TextField(blank=True, null=True)  # naya field
    notice_updated_at = models.DateTimeField(null=True, blank=True)  # ✅ NEW FIELD

    feedback = models.TextField(blank=True, null=True)
    forward_chain = models.JSONField(default=list, blank=True)
    status_updated_at = models.DateTimeField(null=True, blank=True)
    solve_image = models.ImageField(upload_to="complaint_solutions/images/", blank=True, null=True)
    solve_video = models.FileField(upload_to="complaint_solutions/videos/", blank=True, null=True)
    send_to = models.CharField(
        max_length=20,
        choices=SEND_TO_CHOICES,
        default='none'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional unique ID for complaint
    complaint_unique_id = models.CharField(max_length=20, unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
    # Complaint ID generate karna
        if not self.complaint_unique_id:
            prefix = "CMP"
            last_complaint = Complaint.objects.order_by('-id').first()
            if last_complaint and last_complaint.complaint_unique_id:
                last_num_str = last_complaint.complaint_unique_id.replace(prefix, '')
                if last_num_str.isdigit():
                    new_num = int(last_num_str) + 1
                else:
                    new_num = 1
            else:
                new_num = 1
            self.complaint_unique_id = f"{prefix}{new_num}"

        # ✅ Status update time track karna
        if self.pk:  # agar pehle se record hai
            old = Complaint.objects.get(pk=self.pk)
            if old.status != self.status:  # agar status change hua
                self.status_updated_at = timezone.now()
        else:
            # naya record ban raha hai
            self.status_updated_at = timezone.now()

        super().save(*args, **kwargs)



    def __str__(self):
        return f"{self.title} - {self.name} ({self.complaint_unique_id})"

# -------------------------------
class OtpLog(models.Model):
    mobile_number = models.CharField(max_length=15)
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

# -------------------------------
# Optional: If user needs multiple locations
# -------------------------------
class UserLocation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)

# -------------------------------
# Optional HOD Model (Separate)
# -------------------------------
class HOD(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    department = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name



class PublicUser(models.Model):
    mobile_number = models.CharField(max_length=15, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.mobile_number



class AdminMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    reply = models.TextField(blank=True, null=True)  # reply field
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    reply_seen = models.BooleanField(default=False)  # admin ne reply dekha ya nahi

    # New fields
    sender_role = models.CharField(max_length=50, blank=True)  # Booth / Block / District / State
    is_group = models.BooleanField(default=False)             # True = group message, False = single user

    def __str__(self):
        return f"Message from {self.sender.username} ({self.sender_role}) to {self.receiver.username}"

