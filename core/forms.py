from django import forms
from .models import User, Role, Location
from .models import Complaint

from django import forms
from core.models import User, Role, Location

from django import forms
from .models import User, Role, Location

from django import forms
from .models import User, Location, Role
from django.contrib.auth import get_user_model
from .models import AdminMessage, User

LOCATION_LEVEL_CHOICES = [
    ('state', 'State'),
    ('district', 'District'),
    ('block', 'Block'),
]

GENDER_CHOICES = [
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
]

class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Naya user ke liye password daalein, edit karte waqt chhod sakte hain."
    )
    
    location_level = forms.ChoiceField(
        choices=LOCATION_LEVEL_CHOICES,
        required=True,
        label="Location Level"
    )
    state_name = forms.CharField(required=False, label="State Name")
    district_name = forms.CharField(required=False, label="District Name")
    block_name = forms.CharField(required=False, label="Block Name")
    assigned_state = forms.CharField(required=False, label="Assigned State")

    class Meta:
        model = User
        fields = [
            'username',
            'full_name',
            'father_or_mother_name',
            'date_of_birth',
            'gender',
            'mobile_number',
            'alternate_mobile_number',
            'email',
            'aadhar_or_govt_id',
            'permanent_address',
            'current_address',
            'state',
            'district',
            'block_tehsil_taluka',
            'village_town_city',
            'pincode',
            'role',
            'designation',
            'area_of_responsibility',
            'political_experience_years',       # corrected
            'previous_positions',               # corrected
            'pan_card_number',
            'photo',
            'id_proof',
            'digital_signature',
            'biography',
            'assigned_state',
                       # corrected
            'assigned_districts',
            'assigned_blocks',
            'local_area_knowledge',
            'booths_handled',                  # corrected
            'volunteer_experience',
            'reference_person_name',
            'reference_person_contact',
            'address_proof',
            'is_active',
            'password',
        ]

    def __init__(self, *args, **kwargs):
        location_level = kwargs.pop('location_level', None)
        super().__init__(*args, **kwargs)

        # Agar location_level explicitly pass nahi hua to POST ya GET data se lo
        if not location_level:
            if 'location_level' in self.data:
                location_level = self.data.get('location_level')

        # Role queryset set karo based on level
        if location_level:
            self.fields['role'].queryset = Role.objects.filter(level=location_level)
        else:
            # agar location_level nahi hai toh sab roles dikhao (ya empty)
            self.fields['role'].queryset = Role.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        level = cleaned_data.get('location_level')
        assigned_state = cleaned_data.get('assigned_state')
        district = cleaned_data.get('district_name')
        block = cleaned_data.get('block_name')

        # Location validation based on level
        if level == 'state' and not assigned_state:
            self.add_error('assigned_state', 'State name is required for State level location.')
        elif level == 'district':
            if not assigned_state:
                self.add_error('assigned_state', 'State name is required for District level location.')
            if not district:
                self.add_error('district_name', 'District name is required for District level location.')
        elif level == 'block':
            if not assigned_state:
                self.add_error('assigned_state', 'State name is required for Block level location.')
            if not district:
                self.add_error('district_name', 'District name is required for Block level location.')
            if not block:
                self.add_error('block_name', 'Block name is required for Block level location.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)

        level = self.cleaned_data.get('location_level')
        state = self.cleaned_data.get('state_name') or ''
        district = self.cleaned_data.get('district_name') or ''
        block = self.cleaned_data.get('block_name') or ''

        user.assigned_state = state
        user.assigned_districts = district
        user.assigned_blocks = block
        # Agar block_tehsil_taluka empty hai aur zarurat hai, toh default set karo
        if not user.block_tehsil_taluka:
            if level == 'district':
                user.block_tehsil_taluka = ''  # Ya 'N/A' ya jo aap chaho

        # Location object get_or_create karo
        location_kwargs = {}
        if level == 'state':
            location_kwargs = {
                'state_name': state,
                'district_name': '',
                'block_name': '',
            }
        elif level == 'district':
            location_kwargs = {
                'state_name': state,
                'district_name': district,
                'block_name': '',
            }
        elif level == 'block':
            location_kwargs = {
                'state_name': state,
                'district_name': district,
                'block_name': block,
            }

        location, created = Location.objects.get_or_create(**location_kwargs)
        user.location = location

        if commit:
            user.save()
            self.save_m2m()

        return user


from django import forms
from .models import Complaint

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = [
            'name', 'father_name', 'mobile', 'gender', 'photo', 'voter_id_image',
            'address', 'state', 'district', 'block', 'panchayat', 'village', 'pincode',
            'issue_type', 'title', 'description', 'upload_photo', 'upload_video'
        ]

    def __init__(self, *args, **kwargs):
        super(ComplaintForm, self).__init__(*args, **kwargs)
        # Simple styling: sab fields mein Bootstrap 'form-control' class add karna
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class UserRegistrationForm(forms.ModelForm):
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)
    aadhar_or_govt_id = forms.CharField(required=False, label='Aadhar Number / Govt ID')
    photo = forms.ImageField(required=False, label='Profile Picture')

    class Meta:
        model = User
        fields = ['username', 'email', 'mobile_number', 'permanent_address', 'date_of_birth', 'gender', 'aadhar_or_govt_id', 'photo']


class UserLoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

class OTPLoginForm(forms.Form):
    mobile_number = forms.CharField(max_length=15, help_text="Apna mobile number daalein")
    otp_code = forms.CharField(max_length=6, help_text="OTP code daalein")

class OTPVerifyForm(forms.Form):
    mobile_number = forms.CharField(max_length=15, help_text="Apna mobile number daalein")
    otp_code = forms.CharField(max_length=6, help_text="OTP code daalein")

    def clean(self):
        cleaned_data = super().clean()
        # Yahan OTP verification ka logic add kar sakte ho agar chaho
        return cleaned_data



class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField()

    # Yahan se aapko email ke basis pe password reset link bhejna padega

class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords match nahi kar rahe.")
        return cleaned_data




User = get_user_model()

class RoleForm(forms.ModelForm):
    send_to_user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)  # 👈 Add this

    class Meta:
        model = Role
        fields = ['role_name', 'level', 'send_to_level', 'send_to_user']  # 👈 isme bhi hona chahiye



class AdminMessageForm(forms.ModelForm):
    receiver_username = forms.CharField(
        required=False,   # single user ke liye
        label="Receiver Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    group_choice = forms.ChoiceField(
        required=False,   # group ke liye
        choices=[
            ('', '--- Select Group ---'),
            ('state', 'All State Members'),
            ('district', 'All District Members'),
            ('block', 'All Block Members'),
            ('booth', 'All Booth Members'),
        ],
        label="Send to Group",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Type your message'})
    )

    class Meta:
        model = AdminMessage
        fields = ['message']   # <-- sirf model field hi rakhna


class AdminSendMessageForm(forms.ModelForm):
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Type your message'})
    )

    class Meta:
        model = AdminMessage
        fields = ['message']