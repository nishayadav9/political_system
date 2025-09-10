from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import ComplaintForm  
from .forms import UserRegistrationForm
from .models import Role
from .forms import OTPLoginForm
import random
from .models import OtpLog
from django.utils import timezone
from datetime import timedelta  
from .forms import OTPVerifyForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.apps import apps
from django.contrib.auth.decorators import user_passes_test
import secrets
import string
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_POST
from core.models import Role
from .models import Complaint, ComplaintFile  
from .forms import UserForm
from core.models import Location
from django.db.models import Q
from datetime import datetime
from .forms import UserRegistrationForm
from django.contrib.auth import get_user_model
import os
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Count
import requests
from .models import PublicUser, OtpLog
from django.core.exceptions import ObjectDoesNotExist
User = get_user_model()
from .models import Role, Location, PublicUser, Complaint, User
from django.http import HttpResponseForbidden
from django.contrib.auth.hashers import make_password

from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .forms import AdminMessageForm
from .models import AdminMessage
from django.utils import translation
from django.utils.translation import gettext as _
from .forms import AdminSendMessageForm

LANGUAGE_SESSION_KEY = 'django_language'  # direct string use

User = get_user_model()  # 


def superuser_required(view_func):
    decorated_view_func = user_passes_test(lambda user: user.is_superuser, login_url='/admin-login/')(view_func)
    return decorated_view_func

# views.py ke top me ya kisi helpers file me
def is_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

def is_state_admin(user):
    return user.is_authenticated and user.role and user.role.role_name == 'State Committee'


def home(request):
    # LocaleMiddleware khud session/cookie se language read karega
    return render(request, "core/home.html")

def set_language(request):
    if request.method == "POST":
        lang_code = request.POST.get("language")
        if lang_code in dict(settings.LANGUAGES):
            response = redirect(request.META.get("HTTP_REFERER", "/"))
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
            return response
    return redirect(request.META.get("HTTP_REFERER", "/"))

    
def crime_view(request):
    return render(request, 'core/crime.html')

def road(request):
    return render(request, 'core/road_complaint.html')

def about(request):
    return render(request, 'core/about.html')

def water(request):
    return render(request, 'core/water.html')

def electricity_page(request):
    return render(request, 'core/electricity.html')

def health_page(request):
    return render(request, 'core/health_page.html')

def education_view(request):
    return render(request, 'core/education.html')
   
def corruption_page(request):
    return render(request, 'core/corruption.html')

def public_safety_page(request):
    return render(request, 'core/public_safety.html')

def transportation_view(request):
    return render(request, 'core/transportation.html')

def environment_page(request):
    return render(request, 'core/environment.html')

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('public_otp_login')  # Redirect to OTP login page
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
        
    return render(request, 'core/register.html', {'form': form})




from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages

def send_otp_to_mobile(mobile):
    mobile = mobile[-10:]   # ensure last 10 digits only
    otp = str(random.randint(100000, 999999))
    expiry = timezone.now() + timedelta(minutes=5)

    # Save in DB
    OtpLog.objects.create(
        mobile_number=mobile,
        otp_code=otp,
        expires_at=expiry
    )

    # Debug print
    print(f"Generated OTP for {mobile}: {otp}")

    try:
        url = f"https://api.authkey.io/request?authkey=28d7629dee12e54c&mobile={mobile}&country_code=91&sid=7326&name=StreetLearning&otp={otp}"
        response = requests.get(url, timeout=10)

        print("===== OTP API Debug =====")
        print("URL:", url)
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)
        print("=========================")

        if response.status_code == 200 and "SUCCESS" in response.text.upper():
            return True
    except Exception as e:
        print("OTP send failed:", e)

    return False



# public OTP login view
def public_otp_login_view(request):
    mobile = request.session.get('public_mobile', '')

    if request.method == 'POST':
        entered_mobile = request.POST.get('mobile')
        if not entered_mobile:   # agar form me mobile nahi dala gaya
            entered_mobile = request.session.get('public_mobile', '')
        entered_mobile = entered_mobile[-10:]
        otp = request.POST.get('otp')

        # agar OTP enter kiya hai to verify karo
        if otp:
            try:
                otp_obj = OtpLog.objects.filter(
                    mobile_number=entered_mobile,
                    otp_code=otp,
                    is_used=False,
                    expires_at__gte=timezone.now()
                ).latest('created_at')

                # ✅ OTP correct
                otp_obj.is_used = True
                otp_obj.save()

                public_user, created = PublicUser.objects.get_or_create(mobile_number=entered_mobile)
                request.session['public_user_id'] = public_user.id
                request.session['otp_verified'] = True   # ✅ Mark OTP verified

                # Agar pending complaint hai to ab save karna allow karo
                if request.session.get('pending_complaint'):
                    messages.success(request, "OTP verified successfully. Your complaint is being submitted.")
                    return redirect('complaint_form')

                messages.success(request, "OTP verified successfully. You can now submit your complaint.")
                return redirect('complaint_form')

            except OtpLog.DoesNotExist:
                messages.error(request, "Invalid or expired OTP. Please try again.")

        else:
            # agar sirf mobile diya hai -> OTP bhejna hai
            if send_otp_to_mobile(entered_mobile):
                request.session['public_mobile'] = entered_mobile
                request.session['otp_verified'] = False   # ✅ reset flag
                messages.success(request, f"OTP has been sent to {entered_mobile}.")
            else:
                messages.error(request, "There was a problem sending the OTP, please try again.")

    context = {'mobile': mobile}
    return render(request, 'core/public_otp_login.html', context)




# complaint form view
def complaint_form_view(request):
    user = request.user if request.user.is_authenticated else None
    public_user_id = request.session.get('public_user_id')
    otp_verified = request.session.get('otp_verified', False)

    # ✅ Bihar locations: district + block names
    bihar_locations = [
        {"district_name": "Araria", "block_name": "Araria, Bhargama, Forbesganj, Jokihat, Kursakatta, Narpatganj, Palasi, Raniganj, Sikti"},
        {
        "district_name": "Arwal",
        "block_name": "Arwal, Kaler, Karpi, Kurtha"
        },
        {"district_name": "Aurangabad", "block_name": "Aurangabad, Barun, Deo, Goh, Haspura, Kutumba, Madanpur, Nabinagar, Obra, Rafiganj"},
        {
        "district_name": "Banka",
        "block_name": "Amarpur, Banka, Barahat, Belhar, Bausi, Bihat,  Chandan, Dhuraiya, Katoria, Rajauli, Shambhuganj, Sultanganj, Tola, Udwantnagar"
        },
        {
        "district_name": "Begusarai",
        "block_name": "Bachhwara, Bakhri, Balia, Barauni, Begusarai, Bhagwanpur, Birpur, Cheria Bariyarpur, Dandari, Garhpura, Khodawandpur, Mansurchak, Matihani, Naokothi, Sahebpur Kamal, Teghra, Bihat"
        },
        {"district_name": "Bhagalpur", "block_name": "Bihpur, Colgong, Goradih, Ismailpur, Jagdishpur, Kahalgaon, Kharik, Nathnagar, Naugachhia, Pirpainty, Rangra Chowk, Sabour, Sanhaula, Shahkund, Sultanganj"},
        {"district_name": "Bhojpur", "block_name": "Agiaon, Arrah, Barhara, Behea, Charpokhari, Garhani, Jagdishpur, Koilwar, Piro, Sahar, Sandesh, Shahpur, Tarari, Udwantnagar"},
        {"district_name": "Buxar", "block_name": "Buxar, Itarhi, Chausa, Rajpur, Dumraon, Nawanagar, Brahampur, Kesath, Chakki, Chougain, Simri"},
        {
        "district_name": "Darbhanga",
        "block_name": "Alinagar, Benipur, Biraul, Baheri, Bahadurpur, Darbhanga Sadar, Ghanshyampur, Hayaghat, Jale, Keotirunway, Kusheshwar Asthan, Manigachhi, Kiratpur, Khutauna, Muraul, Purnahiya, Rajnagar, Shivnagar, Singhwara, Tardih, Wazirganj, Gaurabauram, Khamhria"
        },

        {
        "district_name": "Gaya",
        "block_name": "Gaya Sadar, Belaganj, Wazirganj, Manpur, Bodhgaya, Tekari, Konch, Guraru, Paraiya, Neemchak Bathani, Khizarsarai, Atri, Bathani, Mohra, Sherghati, Gurua, Amas, Banke Bazar, Imamganj, Dumariya, Dobhi, Mohanpur, Barachatti, Fatehpur"
        },
        {
        "district_name": "Gopalganj",
        "block_name": "Gopalganj, Thawe, Kuchaikote, Manjha, Sidhwaliya, Hathua, Baikunthpur, Barauli, Kateya, Phulwariya, Panchdewari, Uchkagaon, Vijayipur, Bhorey"
        },
        {"district_name": "Jamui", "block_name": "Jamui, Sikandra, Khaira, Chakai, Sono, Laxmipur, Jhajha, Barhat, Gidhour, Islamnagar Aliganj"},
        {"district_name": "Jehanabad", "block_name": "Jehanabad, Makhdumpur, Ghosi, Hulasganj, Ratni Faridpur, Modanganj, Kako"},
        {"district_name": "Kaimur", "block_name": "Adhaura, Bhabua, Bhagwanpur, Chainpur, Chand, Rampur, Durgawati, Kudra, Mohania, Nuaon, Ramgarh"},
        {"district_name": "Katihar", "block_name": "Katihar, Barsoi, Manihari, Falka, Kadwa, Kursela, Hasanganj, Sameli, Pranpur, Korha"},
        {"district_name": "Khagaria", "block_name": "Khagaria, Beldaur, Parbatta, Hasanpur, Chautham, Mansi, Gogri, Simri Bakhtiyarpur"},
        {"district_name": "Kishanganj", "block_name": "Kishanganj, Bahadurganj, Dighalbank, Thakurganj, Goalpokhar, Islampur"},
        {
        "district_name": "Lakhisarai",
        "block_name": "Lakhisarai, Ramgarh Chowk, Surajgarha, Barahiya, Chanan"
        },
        {"district_name": "Madhepura", "block_name": "Madhepura, Kumargram, Singheshwar, Murliganj, Gopalpur, Udaipur, Alamnagar, Shankarpur, Madhepura Sadar"},
        {"district_name": "Madhubani", "block_name":  "Andhratharhi, Babubarhi, Basopatti, Benipatti, Bisfi, Ghoghardiha, Harlakhi, Jhanjharpur, Kaluahi, Khajauli, Ladania, Laukahi, Madhepur, Madhwapur, Pandaul, Phulparas, Rajnagar, Sakri, Shankarpur, Tardih, Lakhnaur"},
        {
        "district_name": "Munger",
        "block_name": "Munger Sadar, Bariyarpur, Chandan, Sangrampur, Tarapur, Jamalpur, Kharagpur, Hathidah"
        },
        {"district_name": "Muzaffarpur", "block_name": "Muzaffarpur Sadar, Musahari, Marwan, Bochahan, Katra, Saraiya, Paroo, Sakra, Gorhara, Motipur, Barahiya, Minapur, Meenapur, Aurai, Piprahi, Aurai, Saraiya, Bochahan"},
        {"district_name": "Nalanda", "block_name": "Bihar Sharif, Rajgir, Harnaut, Islampur, Hilsa, Noorsarai, Ekangarsarai, Asthawan, Katri, Silao, Nalanda Sadar"},
        {"district_name": "Nawada", "block_name": "Nawada Sadar, Akbarpur, Narhat, Pakribarawan, Hisua, Warisaliganj, Kawakol, Roh, Rajauli"},
        {"district_name": "Patna", "block_name": "Patna Sadar, Daniyaw, Bakhtiyarpur, Fatuha, Paliganj, Danapur, Maner, Naubatpur, Sampatchak, Masaurhi, Khusrupur, Bihta, Punpun, Barh, Phulwari, Dhanarua"},
        {"district_name": "Purnia", "block_name": "Purnia Sadar, Banmankhi, Dhamdaha, Rupauli, Baisi, Kasba, Bhawanipur, Barhara Kothi, Sukhasan, Amour, Krityanand Nagar, Jalalgarh, Bhagalpur, Purnia City"},
        {"district_name": "Rohtas", "block_name": "Rohtas Sadar, Sasaram, Nokha, Dehri, Akbarpur, Nauhatta, Rajpur, Chenari, Tilouthu, Rohtas, Dumraon"},
        {"district_name": "Saharsa", "block_name": "Saharsa Sadar, Mahishi, Simri Bakhtiyarpur, Sonbarsa, Madhepur, Pipra, Salkhua, Patarghat, Alamnagar"},
        {"district_name": "Samastipur", "block_name": "Samastipur Sadar, Ujiarpur, Morwa, Sarairanjan, Warisnagar, Kalyanpur, Dalsinghsarai, Hasanpur, Patori, Vidyapati Nagar, Tajpur, Makhdumpur, Musrigharari, Shivajinagar, Goriakothi"},
        {"district_name": "Saran", "block_name": "Chapra Sadar, Marhaura, Dighwara, Parsa, Sonpur, Garkha, Amnour, Dariapur, Taraiya, Manjhi, Sonepur, Masrakh, Parsauni"},
        {"district_name": "Sheikhpura", "block_name": "Sheikhpura Sadar, Chewara, Ariari, Barbigha, Hasanpur, Pirpainti, Sheikhpura, Nathnagar"},
        {"district_name": "Sheohar", "block_name": "Sheohar Sadar, Purnahiya, Dumri Katsari, Piprarhi, Mehsi"},
        {"district_name": "Sitamarhi", "block_name": "Sitamarhi Sadar, Belsand, Bajpatti, Choraut, Bathnaha, Suppi, Riga, Runnisaidpur, Pupri, Sursand, Bairgania, Nanpur"},
        {"district_name": "Siwan", "block_name": "Siwan Sadar, Barharia, Bhagwanpur Hat, Daraundha, Goriakothi, Guthani, Hussainganj, Lakri Nabiganj, Maharajganj, Nautan, Pachrukhi, Raghunathpur, Mairwa"},
        {"district_name": "Vaishali", "block_name": "Hajipur, Lalganj, Mahua, Mahnar, Patepur, Rajapakar, Bidupur, Chehrakala, Desari, Goraul, Jandaha, Sahdei Buzurg"},
        {
        "district_name": "Forbesganj",
        "block_name": "Forbesganj, Araria, Bhargama, Raniganj, Palasi, Sikti, Jokihat, Kursakatta, Narpatganj"
        },
        {"district_name": "Mokama", "block_name": "Mokama, Ghoswari, Pandarak, Barh, Daniyawan, Bikramganj, Kharagpur"},
        {"district_name": "Bettiah", "block_name": "Bettiah Sadar, Nautan, Chanpatia, Sikta, Majhauli, Dumra, Shikarpur, Ramnagar"}
                # ... add all remaining districts & blocks
    ]


    # District list for dropdown
    districts = [loc['district_name'] for loc in bihar_locations]

    # OTP ke baad pending complaint handle
    if otp_verified and request.session.get('pending_complaint_id'):
        try:
            temp_complaint_id = request.session.pop('pending_complaint_id')
            complaint = Complaint.objects.get(id=temp_complaint_id)
            complaint.user = user if user else None
            complaint.save()
            request.session['otp_verified'] = False
            messages.success(request, f"Complaint submitted successfully! ID: {complaint.complaint_unique_id}")
            return render(request, 'core/complaint_success.html', {'complaint': complaint})
        except Complaint.DoesNotExist:
            messages.error(request, "Something went wrong. Please try again.")
            return redirect('complaint_form')

    # Normal complaint form handling
    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            mobile = form.cleaned_data.get('mobile')

            # User login nahi hai aur public OTP bhi verify nahi hua
            if not user and not public_user_id:
                temp_complaint = form.save(commit=False)
                temp_complaint.save()  # temporary save
                request.session['pending_complaint_id'] = temp_complaint.id
                request.session['public_mobile'] = mobile
                request.session['otp_verified'] = False
                messages.info(request, "Please verify OTP before submitting your complaint.")
                return redirect('public_otp_login')

            # Agar OTP verified hai ya user login hai
            if otp_verified or user:
                complaint = form.save(commit=False)
                complaint.user = user if user else None
                

                if public_user_id and not user:
                    try:
                        public_user = PublicUser.objects.get(id=public_user_id)
                        complaint.description += f"\n\nPublic User Mobile: {public_user.mobile_number}"
                    except PublicUser.DoesNotExist:
                        pass
                complaint.save()
                request.session['otp_verified'] = False
                messages.success(request, f"Complaint submitted successfully! ID: {complaint.complaint_unique_id}")
                return render(request, 'core/complaint_success.html', {'complaint': complaint})

        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ComplaintForm()

    # Context me districts & locations
    context = {
        'form': form,
        'districts': districts,
        'locations': bihar_locations
    }
    return render(request, 'core/complaint_form.html', context)

def track_complaint(request):
    complaint = None
    complaint_unique_id = request.GET.get('complaint_id')
    notices = []

    if complaint_unique_id:
        try:
            complaint = Complaint.objects.get(complaint_unique_id=complaint_unique_id)
            if complaint.public_notice:
                # Split notices by --- and remove empty lines
                notices = [n.strip() for n in complaint.public_notice.split('---') if n.strip()]
        except Complaint.DoesNotExist:
            messages.warning(request, f'No complaint found with ID {complaint_unique_id}')
            complaint = None

    return render(request, 'core/track_complaint.html', {
        'complaint': complaint,
        'complaint_id': complaint_unique_id,
        'notices': notices,
    })


def booth_complaints_public_notice(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == "POST":
        public_notice = request.POST.get('public_notice')
        complaint.public_notice = public_notice
        complaint.save()
        messages.success(request, "Public notice saved successfully.")
    return redirect('booth_complaints')


from django.utils import timezone
import pytz

def update_public_notice(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == 'POST':
        new_notice = request.POST.get('public_notice', '').strip()
        if new_notice:
            # ✅ India timezone ke hisaab se current time
            india_tz = pytz.timezone('Asia/Kolkata')
            current_time = timezone.now().astimezone(india_tz)
            timestamp = current_time.strftime("%d-%m-%Y %H:%M")
            notice_with_time = f"[{timestamp}] {new_notice}"  # ✅ timestamp hamesha add

            # ✅ Append ya naya notice
            if complaint.public_notice:
                complaint.public_notice += f"\n---\n{notice_with_time}"
            else:
                complaint.public_notice = notice_with_time
            
            complaint.notice_updated_at = timezone.now()
            complaint.save()
            messages.success(request, "Public notice added successfully!")
        else:
            messages.warning(request, "Notice cannot be empty.")

        return redirect('block_complaints_forward', complaint_id=complaint.pk)

    return redirect('block_complaints_forward', complaint_id=complaint.pk)

def district_update_public_notice(request, pk):
    """
    District Admin: Update public notice for a complaint.
    Each notice gets timestamp in IST and appended to existing notices.
    """
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == 'POST':
        new_notice = request.POST.get('public_notice', '').strip()

        if new_notice:
            # ✅ India timezone ke hisaab se timestamp
            india_tz = pytz.timezone('Asia/Kolkata')
            current_time = timezone.now().astimezone(india_tz)
            timestamp = current_time.strftime("%d-%m-%Y %H:%M")
            notice_with_time = f"[{timestamp}] {new_notice}"

            # ✅ Append existing notice ya naya add kare
            if complaint.public_notice:
                complaint.public_notice += f"\n---\n{notice_with_time}"
            else:
                complaint.public_notice = notice_with_time

            # Optional field for last update time
            complaint.notice_updated_at = timezone.now()
            complaint.save()

            messages.success(request, "Public notice updated successfully!")
        else:
            messages.warning(request, "Notice cannot be empty.")

        return redirect('district_admin_complaints')  # redirect to district complaints page

    # Agar GET request ho
    return redirect('district_complaints')
    
@login_required
def complaint_list_view(request):
    user = request.user
    complaints = Complaint.objects.none()  # Default empty queryset

    if hasattr(user, 'role') and user.role:
        role_level = user.role.level.lower()  # 'state', 'district', 'block', 'booth'

        if role_level == 'state':
            complaints = Complaint.objects.filter(state=user.state)

        elif role_level == 'district':
            complaints = Complaint.objects.filter(state=user.state, district=user.district)

        elif role_level == 'block':
            complaints = Complaint.objects.filter(state=user.state, district=user.district, block=user.block)

        elif role_level == 'booth':
            complaints = Complaint.objects.filter(state=user.state, district=user.district, block=user.block, panchayat=user.assigned_panchayat)

    return render(request, 'core/complaint_list.html', {
        'complaints': complaints,
        'selected_role': user.role.role_name if hasattr(user, 'role') else None
    })


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)



def submit_feedback(request, complaint_id):
    complaint = get_object_or_404(Complaint, pk=complaint_id)

    if request.method == 'POST':
        feedback_text = request.POST.get('feedback')
        if feedback_text:
            complaint.feedback = feedback_text
            complaint.save()
            messages.success(request, "Feedback submitted successfully.")
        else:
            messages.error(request, "Please enter feedback before submitting.")
        return redirect('track_complaint')  # ya same page pe redirect

    return render(request, 'core/feedback_form.html', {'complaint': complaint})







def add_forward_chain(complaint, to_user, from_panel):
    # Append new step to the chain
    complaint.forward_chain.append({
        "from": from_panel,
        "to": to_user,
        "date": str(datetime.now())
    })
    complaint.forward_to = to_user
    complaint.forwarded_from = from_panel
    complaint.save()




@login_required
def send_admin_message(request):
    if request.method == "POST":
        form = AdminMessageForm(request.POST)
        if form.is_valid():
            receiver_username = form.cleaned_data.get("receiver_username")  # custom field
            group_choice = form.cleaned_data.get("group_choice")            # custom field
            message_text = form.cleaned_data.get("message")                # model field

            users = []

            # Single user case
            if receiver_username:
                try:
                    receiver = User.objects.get(username=receiver_username)
                    users = [receiver]
                except User.DoesNotExist:
                    messages.error(request, f"User '{receiver_username}' does not exist!")
                    return redirect("send_admin_message")

            # Group case
            if group_choice == "state":
                users = User.objects.filter(state__isnull=False).exclude(assigned_district__isnull=False)
            elif group_choice == "district":
                users = User.objects.filter(assigned_district__isnull=False).exclude(assigned_block__isnull=False)
            elif group_choice == "block":
                users = User.objects.filter(assigned_block__isnull=False).exclude(booth_number__isnull=False)
            elif group_choice == "booth":
                users = User.objects.filter(booth_number__isnull=False)

            else:
                    users = []

            # Agar koi receiver hai
            if users:
                for u in users:
                    AdminMessage.objects.create(
                        sender=request.user,
                        receiver=u,
                        message=message_text
                    )
                messages.success(
                    request, 
                    f"Message sent to {len(users)} user(s) successfully!"
                )
            else:
                messages.error(request, "Enter a username or select a group.")

            return redirect("send_admin_message")

    else:
        form = AdminMessageForm()

    sent_msgs = AdminMessage.objects.filter(sender=request.user).order_by("-created_at")
    return render(
        request, 
        "core/admin/send_admin_message.html", 
        {"form": form, "sent_msgs": sent_msgs}
    )


@login_required
def hod_receive_messages(request):
    # Sirf booth se bheje messages jinke reply blank hai
    received_msgs = AdminMessage.objects.filter(
        receiver=request.user,
        sender_role__icontains='Booth'
    ).filter(
        Q(reply__isnull=True) | Q(reply__exact='')
    ).order_by('-created_at')

    return render(request, "core/admin/receive_message.html", {"received_msgs": received_msgs})

login_required
def admin_reply_message(request):
    if request.method == 'POST':
        msg_id = request.POST.get('msg_id')
        reply_text = request.POST.get('reply')

        if msg_id and reply_text:
            msg = get_object_or_404(AdminMessage, id=msg_id)
            msg.reply = reply_text
            msg.save()
            messages.success(request, "Reply sent successfully!")

    return redirect('core:hod_receive_messages')  # redirect to HOD message list

@login_required
def message_reply(request, msg_id):
    msg = get_object_or_404(AdminMessage, id=msg_id)

    # Ensure only receiver can reply
    if request.user != msg.receiver:
        messages.error(request, "You are not authorized to reply to this message.")
        return redirect('send_admin_message')

    if request.method == 'POST':
        reply_text = request.POST.get('reply')
        if reply_text:
            msg.reply = reply_text
            msg.save()
            messages.success(request, f"Reply sent to {msg.sender.username}")
        else:
            messages.error(request, "Reply cannot be empty.")

    return redirect('send_admin_message')


@login_required
def receive_messages(request):
    """
    Ek hi page me:
    1. Received messages (reply possible)
    2. Sent messages
    3. Send new message
    """
    # ----------- Handle reply ---------
    if request.method == "POST" and request.POST.get("msg_id"):
        msg_id = request.POST.get("msg_id")
        reply_text = request.POST.get("reply")

        if msg_id and reply_text:
            msg = get_object_or_404(AdminMessage, id=msg_id, receiver=request.user)
            msg.reply = reply_text
            msg.save()
            messages.success(request, f"Reply sent to {msg.sender.username}")
        return redirect("messages_view")  # reload page

    # ----------- Handle new message ---------
    if request.method == "POST" and request.POST.get("receiver_username"):
        form = AdminMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.save()
            messages.success(request, f"Message sent to {msg.receiver.username}")
            return redirect("messages_view")
    else:
        form = AdminMessageForm()

    # ----------- Data for template ---------
    received_msgs = AdminMessage.objects.filter(receiver=request.user).order_by('-created_at')
    sent_msgs = AdminMessage.objects.filter(sender=request.user).order_by('-created_at')

    context = {
        "form": form,
        "received_msgs": received_msgs,
        "sent_msgs": sent_msgs,
    }

    return render(request, 'core/state_admin/receive_messages.html',context)

@login_required
def send_message(request):
    if request.method == 'POST':
        form = AdminMessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.save()
            return redirect('send_message')
    else:
        form = AdminMessageForm()
    sent_msgs = AdminMessage.objects.filter(sender=request.user).order_by('-created_at')
    return render(request, 'core/state_admin/send_message.html', {'form': form, 'sent_msgs': sent_msgs})

# --------------------- EDIT MESSAGE ----------------------
@login_required
def message_edit(request, msg_id):
    msg = get_object_or_404(AdminMessage, id=msg_id, sender=request.user)

    if request.method == "POST":
        form = AdminMessageForm(request.POST, instance=msg)
        if form.is_valid():
            form.save()
            messages.success(request, "Message updated successfully.")
            return redirect("send_admin_message")
    else:
        form = AdminMessageForm(instance=msg)

    return render(request, "core/admin/message_edit.html", {"form": form})


# --------------------- DELETE MESSAGE ----------------------
@login_required
def message_delete(request, msg_id):
    msg = get_object_or_404(AdminMessage, id=msg_id, sender=request.user)

    if request.method == "POST":
        msg.delete()
        messages.success(request, "Message deleted successfully.")
        return redirect("send_admin_message")
    return redirect("send_admin_message")


@login_required
def district_receive_messages(request):
    """
    District admin ke liye received messages aur replies handle
    """
    if request.method == 'POST':
        msg_id = request.POST.get('msg_id')
        reply_text = request.POST.get('reply')

        if msg_id and reply_text:
            msg = get_object_or_404(AdminMessage, id=msg_id)
            # Ensure only receiver can reply
            if request.user == msg.receiver:
                msg.reply = reply_text
                msg.save()
                messages.success(request, f"Reply sent to {msg.sender.username}")
            else:
                messages.error(request, "You are not authorized to reply to this message.")
        return redirect('district_receive_messages')

    # GET request -> show received messages
    msgs = AdminMessage.objects.filter(receiver=request.user).order_by('-created_at')
    return render(request, 'core/district_admin/receive_messages.html', {'msgs': msgs})

@login_required
def district_send_message(request):
    if request.method == 'POST':
        receiver_username = request.POST.get('receiver')
        message_text = request.POST.get('message')

        try:
            receiver_user = User.objects.get(username=receiver_username)  # <-- User model se fetch
        except User.DoesNotExist:
            messages.error(request, "Receiver username not found.")
            return redirect('district_receive_messages')

        AdminMessage.objects.create(
            sender=request.user,
            receiver=receiver_user,
            message=message_text
        )
        messages.success(request, f"Message sent to {receiver_username}")
        return redirect('district_receive_messages')
    return redirect('district_receive_messages')

@login_required
def block_receive_messages(request):
    """
    Block admin ke liye received messages aur replies handle
    """
    if request.method == 'POST':
        msg_id = request.POST.get('msg_id')
        reply_text = request.POST.get('reply')

        if msg_id and reply_text:
            msg = get_object_or_404(AdminMessage, id=msg_id)
            if request.user == msg.receiver:
                msg.reply = reply_text
                msg.save()
                messages.success(request, f"Reply sent to {msg.sender.username}")
            else:
                messages.error(request, "You are not authorized to reply to this message.")
        return redirect('block_receive_messages')

    # GET request -> show received messages
    msgs = AdminMessage.objects.filter(receiver=request.user).order_by('-created_at')
    return render(request, 'core/block_admin/receive_messages.html', {'msgs': msgs})


@login_required
def block_send_message(request):
    """
    Block admin ke liye send message
    """
    if request.method == 'POST':
        receiver_username = request.POST.get('receiver')
        message_text = request.POST.get('message')

        try:
            receiver_user = ZeUser.objects.get(username=receiver_username)
        except ZeUser.DoesNotExist:
            messages.error(request, "Receiver username not found.")
            return redirect('block_receive_messages')

        AdminMessage.objects.create(
            sender=request.user,
            receiver=receiver_user,
            message=message_text
        )
        messages.success(request, f"Message sent to {receiver_username}")
        return redirect('block_receive_messages')
    return redirect('block_receive_messages')


@login_required
def booth_receive_messages(request):
    # Inbox messages for booth
    msgs = AdminMessage.objects.filter(receiver=request.user).order_by('-created_at')
    sent_msgs = AdminMessage.objects.filter(sender=request.user).order_by('-created_at')

    if request.method == 'POST':
        msg_id = request.POST.get('msg_id')
        reply_text = request.POST.get('message')

        if msg_id and reply_text:
            msg = get_object_or_404(AdminMessage, id=msg_id)
            # Ensure only receiver can reply
            if request.user == msg.receiver:
                msg.reply = reply_text
                msg.save()
                messages.success(request, f"Reply sent to {msg.sender.username}")
            else:
                messages.error(request, "You cannot reply to this message.")

        return redirect('booth_receive_messages')

    return render(request, 'core/booth_admin/receive_messages.html', {'msgs': msgs, 'sent_msgs': sent_msgs})



#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
User = get_user_model()

from django.db.models import Count

from django.db.models import Count, Q

@login_required
@user_passes_test(lambda u: u.is_superuser)
def hod_dashboard(request):
    # -------- Party Members Count --------
    state_member_count = User.objects.filter(role__role_name__icontains='State').count()
    state_member_active_count = User.objects.filter(role__role_name__icontains='State', is_active=True).count()
    state_member_inactive_count = User.objects.filter(role__role_name__icontains='State', is_active=False).count()

    district_member_count = User.objects.filter(role__role_name__icontains='District').count()
    district_member_active_count = User.objects.filter(role__role_name__icontains='District', is_active=True).count()
    district_member_inactive_count = User.objects.filter(role__role_name__icontains='District', is_active=False).count()

    block_member_count = User.objects.filter(role__role_name__icontains='Block').count()
    block_member_active_count = User.objects.filter(role__role_name__icontains='Block', is_active=True).count()
    block_member_inactive_count = User.objects.filter(role__role_name__icontains='Block', is_active=False).count()

    booth_member_count = User.objects.filter(role__role_name__icontains='Booth').count()
    booth_member_active_count = User.objects.filter(role__role_name__icontains='Booth', is_active=True).count()
    booth_member_inactive_count = User.objects.filter(role__role_name__icontains='Booth', is_active=False).count()

    # -------- Complaint Stats --------
    state_complaints = get_complaint_stats('state')
    district_complaints = get_complaint_stats('district')
    block_complaints = get_complaint_stats('block')
    booth_complaints = get_complaint_stats('booth')

    # -------- Complaint Grouping with Accepted/Rejected/Solved --------
    district_wise_complaints = (
        Complaint.objects
        .values("district")
        .annotate(
            total=Count("id"),
            accepted=Count("id", filter=Q(status="Accepted")),
            rejected=Count("id", filter=Q(status="Rejected")),
            solved=Count("id", filter=Q(status="Solved"))
        )
        .order_by("district")
    )

    block_wise_complaints = (
        Complaint.objects
        .values("district", "block")
        .annotate(
            total=Count("id"),
            accepted=Count("id", filter=Q(status="Accepted")),
            rejected=Count("id", filter=Q(status="Rejected")),
            solved=Count("id", filter=Q(status="Solved"))
        )
        .order_by("district", "block")
    )

    panchayat_wise_complaints = (
        Complaint.objects
        .values("district", "block", "panchayat")
        .annotate(
            total=Count("id"),
            accepted=Count("id", filter=Q(status="Accepted")),
            rejected=Count("id", filter=Q(status="Rejected")),
            solved=Count("id", filter=Q(status="Solved"))
        )
        .order_by("district", "block", "panchayat")
    )

    # -------- Notifications --------
    unread_messages_count = AdminMessage.objects.filter(receiver=request.user, is_read=False).count()
    replied_messages_count = AdminMessage.objects.filter(receiver=request.user).exclude(reply__isnull=True).count()
    new_replies_count = request.user.received_messages.filter(reply__isnull=False, reply_seen=False).count()

    context = {
        # Party Members
        'state_member_count': state_member_count,
        'state_member_active_count': state_member_active_count,
        'state_member_inactive_count': state_member_inactive_count,

        'district_member_count': district_member_count,
        'district_member_active_count': district_member_active_count,
        'district_member_inactive_count': district_member_inactive_count,

        'block_member_count': block_member_count,
        'block_member_active_count': block_member_active_count,
        'block_member_inactive_count': block_member_inactive_count,

        'booth_member_count': booth_member_count,
        'booth_member_active_count': booth_member_active_count,
        'booth_member_inactive_count': booth_member_inactive_count,

        # Complaint Stats
        'state_complaints': state_complaints,
        'district_complaints': district_complaints,
        'block_complaints': block_complaints,
        'booth_complaints': booth_complaints,

        # Complaint Grouping
        'district_wise_complaints': district_wise_complaints,
        'block_wise_complaints': block_wise_complaints,
        'panchayat_wise_complaints': panchayat_wise_complaints,

        # Notifications
        'unread_messages_count': unread_messages_count,
        'replied_messages_count': replied_messages_count,
        'new_replies_count': new_replies_count,
    }
    return render(request, 'core/admin/dashboard.html', context)

def get_complaint_stats(level):
    # Level ke hisaab se filter lagao fields pe (state, district, block)
    if level == 'state':
        complaints = Complaint.objects.filter(state__isnull=False)
    elif level == 'district':
        complaints = Complaint.objects.filter(district__isnull=False)
    elif level == 'block':
        complaints = Complaint.objects.filter(block__isnull=False)
    else:
        complaints = Complaint.objects.all()

    return {
        'total': complaints.count(),
        'accepted': complaints.filter(status='Accepted').count(),
        'solved': complaints.filter(status='Solved').count(),
        'rejected': complaints.filter(status='Rejected').count(),
    }


# Bihar ke 38 districts aur unke blocks mapping (example, sab add karein)
DISTRICT_BLOCKS = [
        {"district_name": "Araria", "block_name": "Araria, Bhargama, Forbesganj, Jokihat, Kursakatta, Narpatganj, Palasi, Raniganj, Sikti"},
        {
        "district_name": "Arwal",
        "block_name": "Arwal, Kaler, Karpi, Kurtha"
        },
        {"district_name": "Aurangabad", "block_name": "Aurangabad, Barun, Deo, Goh, Haspura, Kutumba, Madanpur, Nabinagar, Obra, Rafiganj"},
        {
        "district_name": "Banka",
        "block_name": "Amarpur, Banka, Barahat, Belhar, Bausi, Bihat,  Chandan, Dhuraiya, Katoria, Rajauli, Shambhuganj, Sultanganj, Tola, Udwantnagar"
        },
        {
        "district_name": "Begusarai",
        "block_name": "Bachhwara, Bakhri, Balia, Barauni, Begusarai, Bhagwanpur, Birpur, Cheria Bariyarpur, Dandari, Garhpura, Khodawandpur, Mansurchak, Matihani, Naokothi, Sahebpur Kamal, Teghra, Bihat"
        },
        {"district_name": "Bhagalpur", "block_name": "Bihpur, Colgong, Goradih, Ismailpur, Jagdishpur, Kahalgaon, Kharik, Nathnagar, Naugachhia, Pirpainty, Rangra Chowk, Sabour, Sanhaula, Shahkund, Sultanganj"},
        {"district_name": "Bhojpur", "block_name": "Agiaon, Arrah, Barhara, Behea, Charpokhari, Garhani, Jagdishpur, Koilwar, Piro, Sahar, Sandesh, Shahpur, Tarari, Udwantnagar"},
        {"district_name": "Buxar", "block_name": "Buxar, Itarhi, Chausa, Rajpur, Dumraon, Nawanagar, Brahampur, Kesath, Chakki, Chougain, Simri"},
        {
        "district_name": "Darbhanga",
        "block_name": "Alinagar, Benipur, Biraul, Baheri, Bahadurpur, Darbhanga Sadar, Ghanshyampur, Hayaghat, Jale, Keotirunway, Kusheshwar Asthan, Manigachhi, Kiratpur, Khutauna, Muraul, Purnahiya, Rajnagar, Shivnagar, Singhwara, Tardih, Wazirganj, Gaurabauram, Khamhria"
        },

        {
        "district_name": "Gaya",
        "block_name": "Gaya Sadar, Belaganj, Wazirganj, Manpur, Bodhgaya, Tekari, Konch, Guraru, Paraiya, Neemchak Bathani, Khizarsarai, Atri, Bathani, Mohra, Sherghati, Gurua, Amas, Banke Bazar, Imamganj, Dumariya, Dobhi, Mohanpur, Barachatti, Fatehpur"
        },
        {
        "district_name": "Gopalganj",
        "block_name": "Gopalganj, Thawe, Kuchaikote, Manjha, Sidhwaliya, Hathua, Baikunthpur, Barauli, Kateya, Phulwariya, Panchdewari, Uchkagaon, Vijayipur, Bhorey"
        },
        {"district_name": "Jamui", "block_name": "Jamui, Sikandra, Khaira, Chakai, Sono, Laxmipur, Jhajha, Barhat, Gidhour, Islamnagar Aliganj"},
        {"district_name": "Jehanabad", "block_name": "Jehanabad, Makhdumpur, Ghosi, Hulasganj, Ratni Faridpur, Modanganj, Kako"},
        {"district_name": "Kaimur", "block_name": "Adhaura, Bhabua, Bhagwanpur, Chainpur, Chand, Rampur, Durgawati, Kudra, Mohania, Nuaon, Ramgarh"},
        {"district_name": "Katihar", "block_name": "Katihar, Barsoi, Manihari, Falka, Kadwa, Kursela, Hasanganj, Sameli, Pranpur, Korha"},
        {"district_name": "Khagaria", "block_name": "Khagaria, Beldaur, Parbatta, Hasanpur, Chautham, Mansi, Gogri, Simri Bakhtiyarpur"},
        {"district_name": "Kishanganj", "block_name": "Kishanganj, Bahadurganj, Dighalbank, Thakurganj, Goalpokhar, Islampur"},
        {
        "district_name": "Lakhisarai",
        "block_name": "Lakhisarai, Ramgarh Chowk, Surajgarha, Barahiya, Chanan"
        },
        {"district_name": "Madhepura", "block_name": "Madhepura, Kumargram, Singheshwar, Murliganj, Gopalpur, Udaipur, Alamnagar, Shankarpur, Madhepura Sadar"},
        {"district_name": "Madhubani", "block_name":  "Andhratharhi, Babubarhi, Basopatti, Benipatti, Bisfi, Ghoghardiha, Harlakhi, Jhanjharpur, Kaluahi, Khajauli, Ladania, Laukahi, Madhepur, Madhwapur, Pandaul, Phulparas, Rajnagar, Sakri, Shankarpur, Tardih, Lakhnaur"},
        {
        "district_name": "Munger",
        "block_name": "Munger Sadar, Bariyarpur, Chandan, Sangrampur, Tarapur, Jamalpur, Kharagpur, Hathidah"
        },
        {"district_name": "Muzaffarpur", "block_name": "Muzaffarpur Sadar, Musahari, Marwan, Bochahan, Katra, Saraiya, Paroo, Sakra, Gorhara, Motipur, Barahiya, Minapur, Meenapur, Aurai, Piprahi, Aurai, Saraiya, Bochahan"},
        {"district_name": "Nalanda", "block_name": "Bihar Sharif, Rajgir, Harnaut, Islampur, Hilsa, Noorsarai, Ekangarsarai, Asthawan, Katri, Silao, Nalanda Sadar"},
        {"district_name": "Nawada", "block_name": "Nawada Sadar, Akbarpur, Narhat, Pakribarawan, Hisua, Warisaliganj, Kawakol, Roh, Rajauli"},
        {"district_name": "Patna", "block_name": "Patna Sadar, Daniyaw, Bakhtiyarpur, Fatuha, Paliganj, Danapur, Maner, Naubatpur, Sampatchak, Masaurhi, Khusrupur, Bihta, Punpun, Barh, Phulwari, Dhanarua"},
        {"district_name": "Purnia", "block_name": "Purnia Sadar, Banmankhi, Dhamdaha, Rupauli, Baisi, Kasba, Bhawanipur, Barhara Kothi, Sukhasan, Amour, Krityanand Nagar, Jalalgarh, Bhagalpur, Purnia City"},
        {"district_name": "Rohtas", "block_name": "Rohtas Sadar, Sasaram, Nokha, Dehri, Akbarpur, Nauhatta, Rajpur, Chenari, Tilouthu, Rohtas, Dumraon"},
        {"district_name": "Saharsa", "block_name": "Saharsa Sadar, Mahishi, Simri Bakhtiyarpur, Sonbarsa, Madhepur, Pipra, Salkhua, Patarghat, Alamnagar"},
        {"district_name": "Samastipur", "block_name": "Samastipur Sadar, Ujiarpur, Morwa, Sarairanjan, Warisnagar, Kalyanpur, Dalsinghsarai, Hasanpur, Patori, Vidyapati Nagar, Tajpur, Makhdumpur, Musrigharari, Shivajinagar, Goriakothi"},
        {"district_name": "Saran", "block_name": "Chapra Sadar, Marhaura, Dighwara, Parsa, Sonpur, Garkha, Amnour, Dariapur, Taraiya, Manjhi, Sonepur, Masrakh, Parsauni"},
        {"district_name": "Sheikhpura", "block_name": "Sheikhpura Sadar, Chewara, Ariari, Barbigha, Hasanpur, Pirpainti, Sheikhpura, Nathnagar"},
        {"district_name": "Sheohar", "block_name": "Sheohar Sadar, Purnahiya, Dumri Katsari, Piprarhi, Mehsi"},
        {"district_name": "Sitamarhi", "block_name": "Sitamarhi Sadar, Belsand, Bajpatti, Choraut, Bathnaha, Suppi, Riga, Runnisaidpur, Pupri, Sursand, Bairgania, Nanpur"},
        {"district_name": "Siwan", "block_name": "Siwan Sadar, Barharia, Bhagwanpur Hat, Daraundha, Goriakothi, Guthani, Hussainganj, Lakri Nabiganj, Maharajganj, Nautan, Pachrukhi, Raghunathpur, Mairwa"},
        {"district_name": "Vaishali", "block_name": "Hajipur, Lalganj, Mahua, Mahnar, Patepur, Rajapakar, Bidupur, Chehrakala, Desari, Goraul, Jandaha, Sahdei Buzurg"},
        {
        "district_name": "Forbesganj",
        "block_name": "Forbesganj, Araria, Bhargama, Raniganj, Palasi, Sikti, Jokihat, Kursakatta, Narpatganj"
        },
        {"district_name": "Mokama", "block_name": "Mokama, Ghoswari, Pandarak, Barh, Daniyawan, Bikramganj, Kharagpur"},
        {"district_name": "Bettiah", "block_name": "Bettiah Sadar, Nautan, Chanpatia, Sikta, Majhauli, Dumra, Shikarpur, Ramnagar"}
]


@login_required
def view_complaints(request):
    user = request.user
    complaints = Complaint.objects.all().order_by('-created_at')

    # ✅ Role ke hisaab se restrict karo
    if user.has_role('Head Office Admin'):
        complaints = complaints  # sab dekh sakta hai

    elif user.has_role('State Committee'):
        complaints = complaints.filter(send_to='state')

    elif user.has_role('District Committee'):
        complaints = complaints.filter(send_to='district')

    elif user.has_role('Block Committee'):
        complaints = complaints.filter(send_to='block')

    else:
        return redirect('unauthorized')

    # ✅ Filter parameters from GET
    state = "Bihar"  # fixed
    district = request.GET.get('district')
    block = request.GET.get('block')
    panchayat = request.GET.get('panchayat')

    complaints = complaints.filter(state=state)

    if district:
        complaints = complaints.filter(district=district)
    if block:
        complaints = complaints.filter(block=block)
    if panchayat:
        complaints = complaints.filter(panchayat__icontains=panchayat)

    context = {
        'complaints': complaints,
        'districts': [d['district_name'] for d in DISTRICT_BLOCKS],  # ✅ ye list of district names bana dega
        'district_blocks': DISTRICT_BLOCKS,         # JS ke liye dynamic block 
        'panchayats': User.objects.all(),   # booth → panchayat
    }
    return render(request, 'core/admin/view_complaints.html', context)


def complaint_edit(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)

    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            form.save()
            return redirect('complaints_list')  # jahan aap complaint list dikhate ho
    else:
        form = ComplaintForm(instance=complaint)

    return render(request, 'core/admin/complaint_edit.html', {'form': form, 'complaint': complaint})



def complaint_delete(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)

    if request.method == 'POST':
        complaint.delete()
        messages.success(request, "Complaint deleted successfully.")
        return redirect('view_complaints')
    else:
        # GET request pe sirf redirect kar do
        messages.warning(request, "Please use the delete button to remove complaints.")
        return redirect('view_complaints')


from django.contrib.auth.decorators import login_required, user_passes_test

def is_state_committee(user):
    return hasattr(user, 'role') and user.role.role_name == 'State Committee'

@login_required
@user_passes_test(is_state_committee)
def state_dashboard(request):
    return render(request, 'core/state_dashboard/dashboard.html')


@login_required
def state_profile(request):
    return render(request, 'core/state_dashboard/state_profile.html')




@login_required
@user_passes_test(lambda u: is_in_group(u, 'Core Member') or hasattr(u, 'coremember'))
def core_member_dashboard(request):
    return render(request, 'core/core_member/dashboard.html')


# -------------------------------------------
# STATE LEVEL PARTY MEMBER CRUD
# -------------------------------------------
from django.contrib.auth.models import Group

def superuser_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_superuser)(view_func)
    return decorated_view_func

def generate_random_password(length=10):
    chars = string.ascii_letters + string.digits + "@#$!"
    return ''.join(secrets.choice(chars) for _ in range(length))

import json
from django.core.serializers.json import DjangoJSONEncoder

@superuser_required
def add_state_member(request):
    random_password = None

    # -----------------------
    # Bihar districts + blocks
    # -----------------------
    bihar_locations = [
        {"district_name": "Araria", "block_name": "Araria, Bhargama, Forbesganj, Jokihat, Kursakatta, Narpatganj, Palasi, Raniganj, Sikti"},
        {
        "district_name": "Arwal",
        "block_name": "Arwal, Kaler, Karpi, Kurtha"
        },
        {"district_name": "Aurangabad", "block_name": "Aurangabad, Barun, Deo, Goh, Haspura, Kutumba, Madanpur, Nabinagar, Obra, Rafiganj"},
        {
        "district_name": "Banka",
        "block_name": "Amarpur, Banka, Barahat, Belhar, Bausi, Bihat,  Chandan, Dhuraiya, Katoria, Rajauli, Shambhuganj, Sultanganj, Tola, Udwantnagar"
        },
        {
        "district_name": "Begusarai",
        "block_name": "Bachhwara, Bakhri, Balia, Barauni, Begusarai, Bhagwanpur, Birpur, Cheria Bariyarpur, Dandari, Garhpura, Khodawandpur, Mansurchak, Matihani, Naokothi, Sahebpur Kamal, Teghra, Bihat"
        },
        {"district_name": "Bhagalpur", "block_name": "Bihpur, Colgong, Goradih, Ismailpur, Jagdishpur, Kahalgaon, Kharik, Nathnagar, Naugachhia, Pirpainty, Rangra Chowk, Sabour, Sanhaula, Shahkund, Sultanganj"},
        {"district_name": "Bhojpur", "block_name": "Agiaon, Arrah, Barhara, Behea, Charpokhari, Garhani, Jagdishpur, Koilwar, Piro, Sahar, Sandesh, Shahpur, Tarari, Udwantnagar"},
        {"district_name": "Buxar", "block_name": "Buxar, Itarhi, Chausa, Rajpur, Dumraon, Nawanagar, Brahampur, Kesath, Chakki, Chougain, Simri"},
        {
        "district_name": "Darbhanga",
        "block_name": "Alinagar, Benipur, Biraul, Baheri, Bahadurpur, Darbhanga Sadar, Ghanshyampur, Hayaghat, Jale, Keotirunway, Kusheshwar Asthan, Manigachhi, Kiratpur, Khutauna, Muraul, Purnahiya, Rajnagar, Shivnagar, Singhwara, Tardih, Wazirganj, Gaurabauram, Khamhria"
        },

        {
        "district_name": "Gaya",
        "block_name": "Gaya Sadar, Belaganj, Wazirganj, Manpur, Bodhgaya, Tekari, Konch, Guraru, Paraiya, Neemchak Bathani, Khizarsarai, Atri, Bathani, Mohra, Sherghati, Gurua, Amas, Banke Bazar, Imamganj, Dumariya, Dobhi, Mohanpur, Barachatti, Fatehpur"
        },
        {
        "district_name": "Gopalganj",
        "block_name": "Gopalganj, Thawe, Kuchaikote, Manjha, Sidhwaliya, Hathua, Baikunthpur, Barauli, Kateya, Phulwariya, Panchdewari, Uchkagaon, Vijayipur, Bhorey"
        },
        {"district_name": "Jamui", "block_name": "Jamui, Sikandra, Khaira, Chakai, Sono, Laxmipur, Jhajha, Barhat, Gidhour, Islamnagar Aliganj"},
        {"district_name": "Jehanabad", "block_name": "Jehanabad, Makhdumpur, Ghosi, Hulasganj, Ratni Faridpur, Modanganj, Kako"},
        {"district_name": "Kaimur", "block_name": "Adhaura, Bhabua, Bhagwanpur, Chainpur, Chand, Rampur, Durgawati, Kudra, Mohania, Nuaon, Ramgarh"},
        {"district_name": "Katihar", "block_name": "Katihar, Barsoi, Manihari, Falka, Kadwa, Kursela, Hasanganj, Sameli, Pranpur, Korha"},
        {"district_name": "Khagaria", "block_name": "Khagaria, Beldaur, Parbatta, Hasanpur, Chautham, Mansi, Gogri, Simri Bakhtiyarpur"},
        {"district_name": "Kishanganj", "block_name": "Kishanganj, Bahadurganj, Dighalbank, Thakurganj, Goalpokhar, Islampur"},
        {
        "district_name": "Lakhisarai",
        "block_name": "Lakhisarai, Ramgarh Chowk, Surajgarha, Barahiya, Chanan"
        },
        {"district_name": "Madhepura", "block_name": "Madhepura, Kumargram, Singheshwar, Murliganj, Gopalpur, Udaipur, Alamnagar, Shankarpur, Madhepura Sadar"},
        {"district_name": "Madhubani", "block_name":  "Andhratharhi, Babubarhi, Basopatti, Benipatti, Bisfi, Ghoghardiha, Harlakhi, Jhanjharpur, Kaluahi, Khajauli, Ladania, Laukahi, Madhepur, Madhwapur, Pandaul, Phulparas, Rajnagar, Sakri, Shankarpur, Tardih, Lakhnaur"},
        {
        "district_name": "Munger",
        "block_name": "Munger Sadar, Bariyarpur, Chandan, Sangrampur, Tarapur, Jamalpur, Kharagpur, Hathidah"
        },
        {"district_name": "Muzaffarpur", "block_name": "Muzaffarpur Sadar, Musahari, Marwan, Bochahan, Katra, Saraiya, Paroo, Sakra, Gorhara, Motipur, Barahiya, Minapur, Meenapur, Aurai, Piprahi, Aurai, Saraiya, Bochahan"},
        {"district_name": "Nalanda", "block_name": "Bihar Sharif, Rajgir, Harnaut, Islampur, Hilsa, Noorsarai, Ekangarsarai, Asthawan, Katri, Silao, Nalanda Sadar"},
        {"district_name": "Nawada", "block_name": "Nawada Sadar, Akbarpur, Narhat, Pakribarawan, Hisua, Warisaliganj, Kawakol, Roh, Rajauli"},
        {"district_name": "Patna", "block_name": "Patna Sadar, Daniyaw, Bakhtiyarpur, Fatuha, Paliganj, Danapur, Maner, Naubatpur, Sampatchak, Masaurhi, Khusrupur, Bihta, Punpun, Barh, Phulwari, Dhanarua"},
        {"district_name": "Purnia", "block_name": "Purnia Sadar, Banmankhi, Dhamdaha, Rupauli, Baisi, Kasba, Bhawanipur, Barhara Kothi, Sukhasan, Amour, Krityanand Nagar, Jalalgarh, Bhagalpur, Purnia City"},
        {"district_name": "Rohtas", "block_name": "Rohtas Sadar, Sasaram, Nokha, Dehri, Akbarpur, Nauhatta, Rajpur, Chenari, Tilouthu, Rohtas, Dumraon"},
        {"district_name": "Saharsa", "block_name": "Saharsa Sadar, Mahishi, Simri Bakhtiyarpur, Sonbarsa, Madhepur, Pipra, Salkhua, Patarghat, Alamnagar"},
        {"district_name": "Samastipur", "block_name": "Samastipur Sadar, Ujiarpur, Morwa, Sarairanjan, Warisnagar, Kalyanpur, Dalsinghsarai, Hasanpur, Patori, Vidyapati Nagar, Tajpur, Makhdumpur, Musrigharari, Shivajinagar, Goriakothi"},
        {"district_name": "Saran", "block_name": "Chapra Sadar, Marhaura, Dighwara, Parsa, Sonpur, Garkha, Amnour, Dariapur, Taraiya, Manjhi, Sonepur, Masrakh, Parsauni"},
        {"district_name": "Sheikhpura", "block_name": "Sheikhpura Sadar, Chewara, Ariari, Barbigha, Hasanpur, Pirpainti, Sheikhpura, Nathnagar"},
        {"district_name": "Sheohar", "block_name": "Sheohar Sadar, Purnahiya, Dumri Katsari, Piprarhi, Mehsi"},
        {"district_name": "Sitamarhi", "block_name": "Sitamarhi Sadar, Belsand, Bajpatti, Choraut, Bathnaha, Suppi, Riga, Runnisaidpur, Pupri, Sursand, Bairgania, Nanpur"},
        {"district_name": "Siwan", "block_name": "Siwan Sadar, Barharia, Bhagwanpur Hat, Daraundha, Goriakothi, Guthani, Hussainganj, Lakri Nabiganj, Maharajganj, Nautan, Pachrukhi, Raghunathpur, Mairwa"},
        {"district_name": "Vaishali", "block_name": "Hajipur, Lalganj, Mahua, Mahnar, Patepur, Rajapakar, Bidupur, Chehrakala, Desari, Goraul, Jandaha, Sahdei Buzurg"},
        {
        "district_name": "Forbesganj",
        "block_name": "Forbesganj, Araria, Bhargama, Raniganj, Palasi, Sikti, Jokihat, Kursakatta, Narpatganj"
        },
        {"district_name": "Mokama", "block_name": "Mokama, Ghoswari, Pandarak, Barh, Daniyawan, Bikramganj, Kharagpur"},
        {"district_name": "Bettiah", "block_name": "Bettiah Sadar, Nautan, Chanpatia, Sikta, Majhauli, Dumra, Shikarpur, Ramnagar"}
                # ... add all remaining districts & blocks
    ]


    # Districts list for dropdown
    districts = [loc['district_name'] for loc in bihar_locations]

    if request.method == 'POST':
        location_level = request.POST.get('location_level')
        form = UserForm(request.POST, request.FILES, location_level=location_level)

        if form.is_valid():
            member = form.save(commit=False)
            password = form.cleaned_data.get('password')

            # Password generate if empty
            if not password:
                password = generate_random_password()
                messages.success(request, f"Member added. Auto-generated password: {password}")
            else:
                messages.success(request, "Member added successfully.")

            member.set_password(password)

            # Role assign
            role = form.cleaned_data.get('role')
            if not role:
                try:
                    role = Role.objects.get(role_name='State President')
                except Role.DoesNotExist:
                    messages.error(request, "Role 'State President' does not exist. Please create it first.")
                    return redirect('add_state_member')
            member.role = role

            # Location assign
            try:
                state_name = form.cleaned_data.get('state_name')
                district_name = form.cleaned_data.get('district_name')
                block_name = form.cleaned_data.get('block_name')

                if location_level == 'state':
                    location = Location.objects.get(state_name=state_name, district_name='', block_name='')
                elif location_level == 'district':
                    location = Location.objects.get(state_name=state_name, district_name=district_name, block_name='')
                elif location_level == 'block':
                    location = Location.objects.get(state_name=state_name, district_name=district_name, block_name=block_name)
                else:
                    raise ValueError("Invalid location level selected.")

                member.location = location

            except Location.DoesNotExist:
                messages.error(request, "Specified location does not exist. Please create it first.")
                return render(request, 'core/admin/add_state_member.html', {'form': form, 'districts': districts, 'locations': bihar_locations})
            except ValueError as e:
                messages.error(request, str(e))
                return render(request, 'core/admin/add_state_member.html', {'form': form, 'districts': districts, 'locations': bihar_locations})

            member.save()
            form.save_m2m()

            # Add to 'State Admin' group
            try:
                state_admin_group = Group.objects.get(name='State Admin')
                member.groups.add(state_admin_group)
            except Group.DoesNotExist:
                messages.error(request, "Group 'State Admin' does not exist. Please create it first.")

            return redirect('manage_state_member')

        else:
            messages.error(request, "Form validation failed. Please check the details.")

    else:
        random_password = generate_random_password()
        form = UserForm(initial={'password': random_password})

    return render(request, 'core/admin/add_state_member.html', {
        'form': form,
        'generated_password': random_password if request.method == 'GET' else None,
        'districts': districts,
        'locations': bihar_locations
    })


@superuser_required
def manage_state_member(request):
    state_roles = Role.objects.filter(role_name__startswith='State')

    # unique states list User table se nikal lenge
    states = User.objects.filter(role__in=state_roles).values_list('state', flat=True).distinct()

    query = request.GET.get('q', '')
    selected_state = request.GET.get('state', '')

    members = User.objects.filter(role__in=state_roles)

    # ✅ Search filter
    if query:
        members = members.filter(
            Q(username__icontains=query) | Q(full_name__icontains=query)
        )

    # ✅ State filter
    if selected_state:
        members = members.filter(state__iexact=selected_state.strip())

    # Debugging print
    for m in members:
        print(f"Username: {m.username}, State: {m.state}")

    context = {
        'members': members,
        'states': states,
        'selected_state': selected_state,
        'query': query
    }
    return render(request, 'core/admin/manage_state_member.html', context)


@superuser_required
def edit_state_member(request, member_id):
    member = get_object_or_404(User, id=member_id)

    if request.method == "POST":
        email = request.POST.get('email')
        
        # Check duplicate email (excluding this member)
        if User.objects.filter(email=email).exclude(id=member_id).exists():
            messages.error(request, "Email already exists!")
            return render(request, 'core/admin/edit_state_member.html', {'member': member})

        # Update fields
        member.full_name = request.POST.get('full_name')
        member.email = email
        member.state = request.POST.get('state')
        member.permanent_address = request.POST.get('permanent_address', '')
        member.current_address = request.POST.get('current_address', '')
        member.save()

        messages.success(request, "State member updated successfully.")
        return redirect('manage_state_member')

    return render(request, 'core/admin/edit_state_member.html', {'member': member})


@superuser_required
def delete_state_member(request, member_id):
    member = get_object_or_404(User, id=member_id)
    if request.method == 'POST':
        member.delete()
        messages.success(request, "State level member deleted successfully.")
        return redirect('manage_state_member')
    return render(request, 'core/admin/confirm_delete.html', {'member': member})


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.models import Complaint  # Update this import based on your actual model location



# views.py ke top me (ya constants.py me and then import)
STATE_LEVEL_ROLES = [
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
]

DISTRICT_LEVEL_ROLES = [
    'District President',
    'District Vice President',
    'District General Secretary',
    'District Secretary',
    'District Treasurer',
    'District Spokesperson',
    'District Youth Wing President',
    'District Mahila Wing President',
    'District Minority Cell In-charge'
]

BLOCK_LEVEL_ROLES = [
    'Block President',
    'Block Vice President',
    'Block General Secretary',
    'Block Secretary',
    'Block Treasurer',
    'Block Youth Wing Head',
    'Block Mahila Wing Head',
    'Block Minority Cell Head'
]


@login_required(login_url='admin_login')
def state_admin_dashboard(request):
    user = request.user
    print("---- DEBUG INFO ----")
    print("Username:", user.username)
    print("Is Authenticated:", user.is_authenticated)
    print("User Role:", getattr(user, 'role', None))
    print("Role Name:", getattr(user.role, 'role_name', 'N/A') if user.role else 'No Role')
    print("Role level:", getattr(user.role, 'level', 'N/A') if user.role else 'No Role')
    print("User Location:", getattr(user, 'location', None))
    print("--------------------")

    if not user.role:
        messages.error(request, "Role not assigned to user.")
        return redirect('state_admin_logout')

    role_name = user.role.role_name
    role_level = user.role.level
    location = user.location

    if role_name == 'Core Member' and role_level == 'state':
        if location:
            if location.block_name != 'NA':
                return redirect('block_admin_dashboard')
            elif location.district_name != 'NA':
                return redirect('district_admin_dashboard')
            elif location.state_name != 'NA':
                complaints = Complaint.objects.filter(send_to='state')

                total_count = complaints.count()
                solved_count = complaints.filter(status='Resolved').count()
                pending_count = complaints.exclude(status='Resolved').count()
                accepted_count = complaints.filter(status='Accepted').count()
                rejected_count = complaints.filter(status='Rejected').count()

                return render(request, 'core/state_admin/dashboard.html', {
                    'complaints': complaints,
                    'total_complaints': total_count,
                    'solved_count': solved_count,
                    'pending_count': pending_count,
                    'accepted_count': accepted_count,
                    'rejected_count': rejected_count,
                })
            else:
                messages.error(request, "Core Member ka location level properly set nahi hai.")
                return redirect('admin_login')
        else:
            messages.error(request, "Core Member ke liye location assign nahi hai.")
            return redirect('admin_login')

    elif role_name in STATE_LEVEL_ROLES and role_level == 'state':
        complaints = Complaint.objects.filter(send_to='state')
        return render(request, 'core/state_admin/dashboard.html', {
            'complaints': complaints,
            'total_complaints': complaints.count(),
            'solved_count': complaints.filter(status='Resolved').count(),
            'pending_count': complaints.exclude(status='Resolved').count(),
            'accepted_count': complaints.filter(status='Accepted').count(),
            'rejected_count': complaints.filter(status='Rejected').count(),
        })

    elif role_name in DISTRICT_LEVEL_ROLES and role_level == 'district':
        return redirect('district_admin_dashboard')

    elif role_name in BLOCK_LEVEL_ROLES and role_level == 'block':
        return redirect('block_admin_dashboard')

    messages.error(request, "Aapko access nahi hai.")
    return redirect('logout')


@login_required(login_url='admin_login')
def state_admin_forwarded_complaints(request):
    # yahan tum apne forwarded complaints ka queryset le sakte ho
    forwarded_complaints = Complaint.objects.filter(status='Forwarded', send_to='state')
    
    context = {
        'forwarded_complaints': forwarded_complaints,
    }
    return render(request, 'core/state_admin/forwarded_complaints.html', context)



@login_required
def state_admin_profile(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Prevents logout after password change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('state_admin_profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'core/state_admin/profile.html', {'form': form})


@login_required
def state_admin_complaints(request):
    assigned_state = getattr(request.user, 'assigned_state', None)
    
    if not assigned_state:
        complaints = Complaint.objects.none()
    else:
        # State panel me saari complaints show karni hain
        # Chahe wo booth, block, district ke liye bhi ho
        complaints = Complaint.objects.filter(
            Q(state__iexact=assigned_state.strip())
        ).order_by('-created_at')

    total = complaints.count()
    accepted = complaints.filter(status='Accepted').count()
    solved = complaints.filter(status='Solved').count()
    rejected = complaints.filter(status='Rejected').count()

    context = {
        'complaints': complaints,
        'total_complaints': total,
        'accepted_complaints': accepted,
        'solved_complaints': solved,
        'rejected_complaints': rejected,
    }

    return render(request, 'core/state_admin/complaints.html', context)

@login_required
def state_complaints_edit(request, pk):
    from django.shortcuts import get_object_or_404, redirect, render

    user = request.user

    # Sirf apne state ka complaint hi fetch hoga
    complaint = get_object_or_404(Complaint, pk=pk, state=user.state, send_to='state')

    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            form.save()
            messages.success(request, "Complaint updated successfully!")
            return redirect('state_admin_complaints')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ComplaintForm(instance=complaint)

    return render(request, 'core/state_admin/state_edit_complaint.html', {'form': form})

@login_required
def state_complaints_delete(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, state=request.user.state, send_to='state')
    complaint.delete()
    messages.success(request, 'Complaint deleted successfully!')
    return redirect('state_admin_complaints')


@login_required
def state_complaints_accept(request, pk):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, pk=pk, state=request.user.state, send_to='state')
        complaint.status = 'Accepted'
        complaint.backend_response = 'Accepted'
        complaint.save()
        messages.success(request, 'Complaint accepted successfully.')
    return redirect('state_admin_complaints')


@login_required
def state_complaints_reject(request, pk):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, pk=pk, state=request.user.state, send_to='state')
        complaint.status = 'Rejected'
        complaint.backend_response = 'Rejected'
        complaint.save()
        messages.success(request, 'Complaint rejected.')
    return redirect('state_admin_complaints')


@login_required
def state_complaints_solve(request, pk):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, pk=pk, state=request.user.state, send_to='state')
        complaint.resolved_at = timezone.now()
        complaint.status = 'Solved'
        complaint.save()
        messages.success(request, 'Complaint marked as solved.')
    return redirect('state_admin_complaints')

@login_required
def state_admin_logout(request):
    logout(request)
    return redirect('home')  # Or your login url name

@login_required
def district_admin_logout(request):
    logout(request)
    return redirect('home') 


@login_required
def block_admin_logout(request):
    logout(request)
    return redirect('home')


@login_required
def hod_logout(request):
    logout(request)
    return redirect('home')


@login_required
def state_admin_change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # session logout na ho
            messages.success(request, 'Password changed successfully.')
            return redirect('state_admin_profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/state_admin/change_password.html', {'form': form})




# -------------------------------------------
# DISTRICT LEVEL PARTY MEMBER CRUD
# -------------------------------------------

from django.core.serializers.json import DjangoJSONEncoder
import json

import string, secrets

def generate_random_password(length=10):
    chars = string.ascii_letters + string.digits + "@#$!"
    return ''.join(secrets.choice(chars) for _ in range(length))


@superuser_required
def add_district_member(request):
    roles = Role.objects.all()

    # Roles JSON for JS dropdown
    roles_json = json.dumps([
        {'id': role.id, 'name': role.role_name, 'level': role.level}
        for role in roles
    ])

    # -----------------------
    # Bihar districts & blocks
    # -----------------------
    bihar_locations = [
        {"district_name": "Araria", "block_name": "Araria, Bhargama, Forbesganj, Jokihat, Kursakatta, Narpatganj, Palasi, Raniganj, Sikti"},
        {
        "district_name": "Arwal",
        "block_name": "Arwal, Kaler, Karpi, Kurtha"
        },
        {"district_name": "Aurangabad", "block_name": "Aurangabad, Barun, Deo, Goh, Haspura, Kutumba, Madanpur, Nabinagar, Obra, Rafiganj"},
        {
        "district_name": "Banka",
        "block_name": "Amarpur, Banka, Barahat, Belhar, Bausi, Bihat,  Chandan, Dhuraiya, Katoria, Rajauli, Shambhuganj, Sultanganj, Tola, Udwantnagar"
        },
        {
        "district_name": "Begusarai",
        "block_name": "Bachhwara, Bakhri, Balia, Barauni, Begusarai, Bhagwanpur, Birpur, Cheria Bariyarpur, Dandari, Garhpura, Khodawandpur, Mansurchak, Matihani, Naokothi, Sahebpur Kamal, Teghra, Bihat"
        },
        {"district_name": "Bhagalpur", "block_name": "Bihpur, Colgong, Goradih, Ismailpur, Jagdishpur, Kahalgaon, Kharik, Nathnagar, Naugachhia, Pirpainty, Rangra Chowk, Sabour, Sanhaula, Shahkund, Sultanganj"},
        {"district_name": "Bhojpur", "block_name": "Agiaon, Arrah, Barhara, Behea, Charpokhari, Garhani, Jagdishpur, Koilwar, Piro, Sahar, Sandesh, Shahpur, Tarari, Udwantnagar"},
        {"district_name": "Buxar", "block_name": "Buxar, Itarhi, Chausa, Rajpur, Dumraon, Nawanagar, Brahampur, Kesath, Chakki, Chougain, Simri"},
        {
        "district_name": "Darbhanga",
        "block_name": "Alinagar, Benipur, Biraul, Baheri, Bahadurpur, Darbhanga Sadar, Ghanshyampur, Hayaghat, Jale, Keotirunway, Kusheshwar Asthan, Manigachhi, Kiratpur, Khutauna, Muraul, Purnahiya, Rajnagar, Shivnagar, Singhwara, Tardih, Wazirganj, Gaurabauram, Khamhria"
        },

        {
        "district_name": "Gaya",
        "block_name": "Gaya Sadar, Belaganj, Wazirganj, Manpur, Bodhgaya, Tekari, Konch, Guraru, Paraiya, Neemchak Bathani, Khizarsarai, Atri, Bathani, Mohra, Sherghati, Gurua, Amas, Banke Bazar, Imamganj, Dumariya, Dobhi, Mohanpur, Barachatti, Fatehpur"
        },
        {
        "district_name": "Gopalganj",
        "block_name": "Gopalganj, Thawe, Kuchaikote, Manjha, Sidhwaliya, Hathua, Baikunthpur, Barauli, Kateya, Phulwariya, Panchdewari, Uchkagaon, Vijayipur, Bhorey"
        },
        {"district_name": "Jamui", "block_name": "Jamui, Sikandra, Khaira, Chakai, Sono, Laxmipur, Jhajha, Barhat, Gidhour, Islamnagar Aliganj"},
        {"district_name": "Jehanabad", "block_name": "Jehanabad, Makhdumpur, Ghosi, Hulasganj, Ratni Faridpur, Modanganj, Kako"},
        {"district_name": "Kaimur", "block_name": "Adhaura, Bhabua, Bhagwanpur, Chainpur, Chand, Rampur, Durgawati, Kudra, Mohania, Nuaon, Ramgarh"},
        {"district_name": "Katihar", "block_name": "Katihar, Barsoi, Manihari, Falka, Kadwa, Kursela, Hasanganj, Sameli, Pranpur, Korha"},
        {"district_name": "Khagaria", "block_name": "Khagaria, Beldaur, Parbatta, Hasanpur, Chautham, Mansi, Gogri, Simri Bakhtiyarpur"},
        {"district_name": "Kishanganj", "block_name": "Kishanganj, Bahadurganj, Dighalbank, Thakurganj, Goalpokhar, Islampur"},
        {
        "district_name": "Lakhisarai",
        "block_name": "Lakhisarai, Ramgarh Chowk, Surajgarha, Barahiya, Chanan"
        },
        {"district_name": "Madhepura", "block_name": "Madhepura, Kumargram, Singheshwar, Murliganj, Gopalpur, Udaipur, Alamnagar, Shankarpur, Madhepura Sadar"},
        {"district_name": "Madhubani", "block_name":  "Andhratharhi, Babubarhi, Basopatti, Benipatti, Bisfi, Ghoghardiha, Harlakhi, Jhanjharpur, Kaluahi, Khajauli, Ladania, Laukahi, Madhepur, Madhwapur, Pandaul, Phulparas, Rajnagar, Sakri, Shankarpur, Tardih, Lakhnaur"},
        {
        "district_name": "Munger",
        "block_name": "Munger Sadar, Bariyarpur, Chandan, Sangrampur, Tarapur, Jamalpur, Kharagpur, Hathidah"
        },
        {"district_name": "Muzaffarpur", "block_name": "Muzaffarpur Sadar, Musahari, Marwan, Bochahan, Katra, Saraiya, Paroo, Sakra, Gorhara, Motipur, Barahiya, Minapur, Meenapur, Aurai, Piprahi, Aurai, Saraiya, Bochahan"},
        {"district_name": "Nalanda", "block_name": "Bihar Sharif, Rajgir, Harnaut, Islampur, Hilsa, Noorsarai, Ekangarsarai, Asthawan, Katri, Silao, Nalanda Sadar"},
        {"district_name": "Nawada", "block_name": "Nawada Sadar, Akbarpur, Narhat, Pakribarawan, Hisua, Warisaliganj, Kawakol, Roh, Rajauli"},
        {"district_name": "Patna", "block_name": "Patna Sadar, Daniyaw, Bakhtiyarpur, Fatuha, Paliganj, Danapur, Maner, Naubatpur, Sampatchak, Masaurhi, Khusrupur, Bihta, Punpun, Barh, Phulwari, Dhanarua"},
        {"district_name": "Purnia", "block_name": "Purnia Sadar, Banmankhi, Dhamdaha, Rupauli, Baisi, Kasba, Bhawanipur, Barhara Kothi, Sukhasan, Amour, Krityanand Nagar, Jalalgarh, Bhagalpur, Purnia City"},
        {"district_name": "Rohtas", "block_name": "Rohtas Sadar, Sasaram, Nokha, Dehri, Akbarpur, Nauhatta, Rajpur, Chenari, Tilouthu, Rohtas, Dumraon"},
        {"district_name": "Saharsa", "block_name": "Saharsa Sadar, Mahishi, Simri Bakhtiyarpur, Sonbarsa, Madhepur, Pipra, Salkhua, Patarghat, Alamnagar"},
        {"district_name": "Samastipur", "block_name": "Samastipur Sadar, Ujiarpur, Morwa, Sarairanjan, Warisnagar, Kalyanpur, Dalsinghsarai, Hasanpur, Patori, Vidyapati Nagar, Tajpur, Makhdumpur, Musrigharari, Shivajinagar, Goriakothi"},
        {"district_name": "Saran", "block_name": "Chapra Sadar, Marhaura, Dighwara, Parsa, Sonpur, Garkha, Amnour, Dariapur, Taraiya, Manjhi, Sonepur, Masrakh, Parsauni"},
        {"district_name": "Sheikhpura", "block_name": "Sheikhpura Sadar, Chewara, Ariari, Barbigha, Hasanpur, Pirpainti, Sheikhpura, Nathnagar"},
        {"district_name": "Sheohar", "block_name": "Sheohar Sadar, Purnahiya, Dumri Katsari, Piprarhi, Mehsi"},
        {"district_name": "Sitamarhi", "block_name": "Sitamarhi Sadar, Belsand, Bajpatti, Choraut, Bathnaha, Suppi, Riga, Runnisaidpur, Pupri, Sursand, Bairgania, Nanpur"},
        {"district_name": "Siwan", "block_name": "Siwan Sadar, Barharia, Bhagwanpur Hat, Daraundha, Goriakothi, Guthani, Hussainganj, Lakri Nabiganj, Maharajganj, Nautan, Pachrukhi, Raghunathpur, Mairwa"},
        {"district_name": "Vaishali", "block_name": "Hajipur, Lalganj, Mahua, Mahnar, Patepur, Rajapakar, Bidupur, Chehrakala, Desari, Goraul, Jandaha, Sahdei Buzurg"},
        {
        "district_name": "Forbesganj",
        "block_name": "Forbesganj, Araria, Bhargama, Raniganj, Palasi, Sikti, Jokihat, Kursakatta, Narpatganj"
        },
        {"district_name": "Mokama", "block_name": "Mokama, Ghoswari, Pandarak, Barh, Daniyawan, Bikramganj, Kharagpur"},
        {"district_name": "Bettiah", "block_name": "Bettiah Sadar, Nautan, Chanpatia, Sikta, Majhauli, Dumra, Shikarpur, Ramnagar"}
                # ... add all remaining districts & blocks
    ]

    # Insert locations if not exists
    for loc in bihar_locations:
        if not Location.objects.filter(state_name="Bihar", district_name=loc["district_name"], block_name=loc["block_name"]).exists():
            Location.objects.create(state_name="Bihar", **loc)

    # GET distinct districts & blocks
    districts = list(Location.objects.filter(state_name="Bihar").values_list('district_name', flat=True).distinct())
    blocks = []  # Initially empty, will populate via AJAX

    if request.method == "POST":
        email = request.POST['email']

        # Email duplicate check
        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, 'core/admin/add_district_member.html', {
                'roles': roles, 'roles_json': roles_json, 'districts': districts, 'blocks': blocks,
                'generated_password': request.POST.get('password', ''),
                'state_name': 'Bihar'
            })

        # Role fetch
        role_id = request.POST.get('role')
        role = None
        if role_id:
            try:
                role = Role.objects.get(id=role_id)
            except ObjectDoesNotExist:
                messages.error(request, "Selected role does not exist.")
                return render(request, 'core/admin/add_district_member.html', {
                    'roles': roles, 'roles_json': roles_json, 'districts': districts, 'blocks': blocks,
                    'generated_password': request.POST.get('password', ''),
                    'state_name': 'Bihar'
                })

        district_name = request.POST.get('district')
        if not district_name:
            messages.error(request, "Please provide the district name.")
            return render(request, 'core/admin/add_district_member.html', {
                'roles': roles, 'roles_json': roles_json, 'districts': districts, 'blocks': blocks,
                'generated_password': request.POST.get('password', ''),
                'state_name': 'Bihar'
            })

        block_name = request.POST.get('block') or "N/A"
        state_name = "Bihar"

        # Location fetch/create
        location, _ = Location.objects.get_or_create(
            state_name=state_name,
            district_name=district_name,
            block_name=block_name
        )

        # Password generate
        password = request.POST.get('password') or generate_random_password()

        # Create member
        member = User(
            username=request.POST['username'],
            full_name=request.POST['full_name'],
            father_or_mother_name=request.POST['father_or_mother_name'],
            date_of_birth=request.POST.get('date_of_birth'),
            gender=request.POST.get('gender'),
            mobile_number=request.POST['mobile_number'],
            alternate_mobile_number=request.POST.get('alternate_mobile_number', ''),
            email=email,
            aadhar_or_govt_id=request.POST.get('aadhar_or_govt_id'),
            permanent_address=request.POST.get('permanent_address'),
            current_address=request.POST.get('current_address'),
            state=state_name,
            district=district_name,
            block_tehsil_taluka=block_name,
            pincode=request.POST.get('pincode'),
            role=role,
            location=location,
            assigned_state=state_name,
            assigned_district=request.POST.get('assigned_district'),
            assigned_blocks=request.POST.get('assigned_block'),  # instead of assigned_block_text
            local_area_knowledge=request.POST.get('local_area_knowledge') == 'Yes',
            political_experience_years=request.POST.get('political_experience_years'),
            is_active='is_active' in request.POST
        )

        # Handle uploaded files
        member.photo = request.FILES.get('photo')
        member.id_proof = request.FILES.get('id_proof')

        member.set_password(password)
        member.save()

        messages.success(request, f"District member added successfully. Generated password: {password}")
        return redirect('manage_district_member')

    # GET request
    generated_password = generate_random_password()
    return render(request, 'core/admin/add_district_member.html', {
        'roles': roles,
        'roles_json': roles_json,
        'districts': districts,
        'blocks': blocks,
        'generated_password': generated_password,
        'state_name': 'Bihar'
    })


# -----------------------
# AJAX endpoints
# -----------------------
def get_districts_by_state(request):
    state = request.GET.get('state')
    districts = (
        list(
            Location.objects.filter(state_name=state)
            .order_by('district_name')   # ✅ Alphabetical order
            .values_list('district_name', flat=True)
            .distinct()
        )
        if state else []
    )
    return JsonResponse({'districts': districts})
def get_blocks_by_district(request):
    district = request.GET.get('district')
    blocks = []
    if district:
        block_strings = Location.objects.filter(
            state_name="Bihar", district_name=district
        ).values_list('block_name', flat=True)

        for b_str in block_strings:
            # yaha split karke clean kar lenge
            blocks.extend([b.strip() for b in b_str.split(',') if b.strip()])

        blocks = list(set(blocks))  # duplicate hatao

    return JsonResponse({'blocks': blocks})


def get_pincode_by_block(request):
    block = request.GET.get('block')
    pincode = Location.objects.filter(block_name=block).values_list('pincode', flat=True).first() or ''
    return JsonResponse({'pincode': pincode})




@superuser_required
def manage_district_member(request):
    # All locations jinke district_name filled ho
    district_location_ids = Location.objects.exclude(district_name='').values_list('id', flat=True)
    members = User.objects.filter(location_id__in=district_location_ids)

    # Simple search
    query = request.GET.get('q')
    if query:
        members = members.filter(assigned_district__icontains=query)

    # Advanced search
    username = request.GET.get('username')
    district = request.GET.get('district')

    if username:
        members = members.filter(username__icontains=username)
    if district:
        members = members.filter(assigned_district__icontains=district)

    districts = [
        "Araria","Arwal","Aurangabad","Banka","Begusarai","Bhagalpur","Bhojpur",
        "Buxar","Darbhanga","Gaya","Gopalganj","Jamui","Jehanabad","Kaimur",
        "Katihar","Khagaria","Kishanganj","Lakhisarai","Madhepura","Madhubani",
        "Munger","Muzaffarpur","Nalanda","Nawada","Patna","Purnia","Rohtas",
        "Saharsa","Samastipur","Saran","Sheikhpura","Sheohar","Sitamarhi","Siwan",
        "Vaishali","Forbesganj","Mokama","Bettiah"
    ]

    return render(request, 'core/admin/manage_district_member.html', {
        'members': members,
        'query': query or "",
        'username': username or "",
        'district': district or "",
        'districts': districts
    })



@superuser_required
def edit_district_member(request, member_id):
    member = get_object_or_404(User, id=member_id)
    roles = Role.objects.all()

    if request.method == "POST":
        email = request.POST['email']
        if DistrictLevelPartyMember.objects.filter(email=email).exclude(id=member_id).exists():
            messages.error(request, "Email already exists.")
            return render(request, 'core/admin/edit_district_member.html', {'member': member, 'roles': roles})

        role_id = request.POST.get('role')
        role = None
        if role_id:
            try:
                role = Role.objects.get(id=role_id)
            except ObjectDoesNotExist:
                messages.error(request, "Selected role does not exist.")
                return render(request, 'core/admin/edit_district_member.html', {'member': member, 'roles': roles})

        member.username = request.POST['username']
        member.email = email
        member.district = request.POST['district']
        member.address = request.POST['address']
        member.role = role
        member.save()

        messages.success(request, "District member updated successfully.")
        return redirect('manage_district_member')

    return render(request, 'core/admin/edit_district_member.html', {'member': member, 'roles': roles})


@superuser_required
def delete_district_member(request, member_id):
    member = get_object_or_404(User, id=member_id)
    if request.method == "POST":
        member.delete()
        messages.success(request, "District member deleted successfully.")
        return redirect('manage_district_member')
    return render(request, 'core/admin/confirm_delete.html', {'member': member})


# -------------------------------------------
# BLOCK LEVEL PARTY MEMBER CRUD
# -------------------------------------------


@superuser_required
def add_block_member(request):
    from .models import Role, Location, User
    from django.contrib import messages
    from django.shortcuts import render, redirect
    import string, secrets

    level_map = {
        'state': 'state',
        'district': 'district',
        'block': 'block',
    }


    blocks_by_district = {
        # ... your full blocks_by_district dictionary ...
    }

    districts = list(blocks_by_district.keys())

    # -----------------------
    # Bihar locations (districts + blocks)
    # -----------------------
    bihar_locations = [
        {"district_name": "Araria", "block_name": "Araria, Bhargama, Forbesganj, Jokihat, Kursakatta, Narpatganj, Palasi, Raniganj, Sikti"},
        {
        "district_name": "Arwal",
        "block_name": "Arwal, Kaler, Karpi, Kurtha"
        },
        {"district_name": "Aurangabad", "block_name": "Aurangabad, Barun, Deo, Goh, Haspura, Kutumba, Madanpur, Nabinagar, Obra, Rafiganj"},
        {
        "district_name": "Banka",
        "block_name": "Amarpur, Banka, Barahat, Belhar, Bausi, Bihat,  Chandan, Dhuraiya, Katoria, Rajauli, Shambhuganj, Sultanganj, Tola, Udwantnagar"
        },
        {
        "district_name": "Begusarai",
        "block_name": "Bachhwara, Bakhri, Balia, Barauni, Begusarai, Bhagwanpur, Birpur, Cheria Bariyarpur, Dandari, Garhpura, Khodawandpur, Mansurchak, Matihani, Naokothi, Sahebpur Kamal, Teghra, Bihat"
        },
        {"district_name": "Bhagalpur", "block_name": "Bihpur, Colgong, Goradih, Ismailpur, Jagdishpur, Kahalgaon, Kharik, Nathnagar, Naugachhia, Pirpainty, Rangra Chowk, Sabour, Sanhaula, Shahkund, Sultanganj"},
        {"district_name": "Bhojpur", "block_name": "Agiaon, Arrah, Barhara, Behea, Charpokhari, Garhani, Jagdishpur, Koilwar, Piro, Sahar, Sandesh, Shahpur, Tarari, Udwantnagar"},
        {"district_name": "Buxar", "block_name": "Buxar, Itarhi, Chausa, Rajpur, Dumraon, Nawanagar, Brahampur, Kesath, Chakki, Chougain, Simri"},
        {
        "district_name": "Darbhanga",
        "block_name": "Alinagar, Benipur, Biraul, Baheri, Bahadurpur, Darbhanga Sadar, Ghanshyampur, Hayaghat, Jale, Keotirunway, Kusheshwar Asthan, Manigachhi, Kiratpur, Khutauna, Muraul, Purnahiya, Rajnagar, Shivnagar, Singhwara, Tardih, Wazirganj, Gaurabauram, Khamhria"
        },

        {
        "district_name": "Gaya",
        "block_name": "Gaya Sadar, Belaganj, Wazirganj, Manpur, Bodhgaya, Tekari, Konch, Guraru, Paraiya, Neemchak Bathani, Khizarsarai, Atri, Bathani, Mohra, Sherghati, Gurua, Amas, Banke Bazar, Imamganj, Dumariya, Dobhi, Mohanpur, Barachatti, Fatehpur"
        },
        {
        "district_name": "Gopalganj",
        "block_name": "Gopalganj, Thawe, Kuchaikote, Manjha, Sidhwaliya, Hathua, Baikunthpur, Barauli, Kateya, Phulwariya, Panchdewari, Uchkagaon, Vijayipur, Bhorey"
        },
        {"district_name": "Jamui", "block_name": "Jamui, Sikandra, Khaira, Chakai, Sono, Laxmipur, Jhajha, Barhat, Gidhour, Islamnagar Aliganj"},
        {"district_name": "Jehanabad", "block_name": "Jehanabad, Makhdumpur, Ghosi, Hulasganj, Ratni Faridpur, Modanganj, Kako"},
        {"district_name": "Kaimur", "block_name": "Adhaura, Bhabua, Bhagwanpur, Chainpur, Chand, Rampur, Durgawati, Kudra, Mohania, Nuaon, Ramgarh"},
        {"district_name": "Katihar", "block_name": "Katihar, Barsoi, Manihari, Falka, Kadwa, Kursela, Hasanganj, Sameli, Pranpur, Korha"},
        {"district_name": "Khagaria", "block_name": "Khagaria, Beldaur, Parbatta, Hasanpur, Chautham, Mansi, Gogri, Simri Bakhtiyarpur"},
        {"district_name": "Kishanganj", "block_name": "Kishanganj, Bahadurganj, Dighalbank, Thakurganj, Goalpokhar, Islampur"},
        {
        "district_name": "Lakhisarai",
        "block_name": "Lakhisarai, Ramgarh Chowk, Surajgarha, Barahiya, Chanan"
        },
        {"district_name": "Madhepura", "block_name": "Madhepura, Kumargram, Singheshwar, Murliganj, Gopalpur, Udaipur, Alamnagar, Shankarpur, Madhepura Sadar"},
        {"district_name": "Madhubani", "block_name":  "Andhratharhi, Babubarhi, Basopatti, Benipatti, Bisfi, Ghoghardiha, Harlakhi, Jhanjharpur, Kaluahi, Khajauli, Ladania, Laukahi, Madhepur, Madhwapur, Pandaul, Phulparas, Rajnagar, Sakri, Shankarpur, Tardih, Lakhnaur"},
        {
        "district_name": "Munger",
        "block_name": "Munger Sadar, Bariyarpur, Chandan, Sangrampur, Tarapur, Jamalpur, Kharagpur, Hathidah"
        },
        {"district_name": "Muzaffarpur", "block_name": "Muzaffarpur Sadar, Musahari, Marwan, Bochahan, Katra, Saraiya, Paroo, Sakra, Gorhara, Motipur, Barahiya, Minapur, Meenapur, Aurai, Piprahi, Aurai, Saraiya, Bochahan"},
        {"district_name": "Nalanda", "block_name": "Bihar Sharif, Rajgir, Harnaut, Islampur, Hilsa, Noorsarai, Ekangarsarai, Asthawan, Katri, Silao, Nalanda Sadar"},
        {"district_name": "Nawada", "block_name": "Nawada Sadar, Akbarpur, Narhat, Pakribarawan, Hisua, Warisaliganj, Kawakol, Roh, Rajauli"},
        {"district_name": "Patna", "block_name": "Patna Sadar, Daniyaw, Bakhtiyarpur, Fatuha, Paliganj, Danapur, Maner, Naubatpur, Sampatchak, Masaurhi, Khusrupur, Bihta, Punpun, Barh, Phulwari, Dhanarua"},
        {"district_name": "Purnia", "block_name": "Purnia Sadar, Banmankhi, Dhamdaha, Rupauli, Baisi, Kasba, Bhawanipur, Barhara Kothi, Sukhasan, Amour, Krityanand Nagar, Jalalgarh, Bhagalpur, Purnia City"},
        {"district_name": "Rohtas", "block_name": "Rohtas Sadar, Sasaram, Nokha, Dehri, Akbarpur, Nauhatta, Rajpur, Chenari, Tilouthu, Rohtas, Dumraon"},
        {"district_name": "Saharsa", "block_name": "Saharsa Sadar, Mahishi, Simri Bakhtiyarpur, Sonbarsa, Madhepur, Pipra, Salkhua, Patarghat, Alamnagar"},
        {"district_name": "Samastipur", "block_name": "Samastipur Sadar, Ujiarpur, Morwa, Sarairanjan, Warisnagar, Kalyanpur, Dalsinghsarai, Hasanpur, Patori, Vidyapati Nagar, Tajpur, Makhdumpur, Musrigharari, Shivajinagar, Goriakothi"},
        {"district_name": "Saran", "block_name": "Chapra Sadar, Marhaura, Dighwara, Parsa, Sonpur, Garkha, Amnour, Dariapur, Taraiya, Manjhi, Sonepur, Masrakh, Parsauni"},
        {"district_name": "Sheikhpura", "block_name": "Sheikhpura Sadar, Chewara, Ariari, Barbigha, Hasanpur, Pirpainti, Sheikhpura, Nathnagar"},
        {"district_name": "Sheohar", "block_name": "Sheohar Sadar, Purnahiya, Dumri Katsari, Piprarhi, Mehsi"},
        {"district_name": "Sitamarhi", "block_name": "Sitamarhi Sadar, Belsand, Bajpatti, Choraut, Bathnaha, Suppi, Riga, Runnisaidpur, Pupri, Sursand, Bairgania, Nanpur"},
        {"district_name": "Siwan", "block_name": "Siwan Sadar, Barharia, Bhagwanpur Hat, Daraundha, Goriakothi, Guthani, Hussainganj, Lakri Nabiganj, Maharajganj, Nautan, Pachrukhi, Raghunathpur, Mairwa"},
        {"district_name": "Vaishali", "block_name": "Hajipur, Lalganj, Mahua, Mahnar, Patepur, Rajapakar, Bidupur, Chehrakala, Desari, Goraul, Jandaha, Sahdei Buzurg"},
        {
        "district_name": "Forbesganj",
        "block_name": "Forbesganj, Araria, Bhargama, Raniganj, Palasi, Sikti, Jokihat, Kursakatta, Narpatganj"
        },
        {"district_name": "Mokama", "block_name": "Mokama, Ghoswari, Pandarak, Barh, Daniyawan, Bikramganj, Kharagpur"},
        {"district_name": "Bettiah", "block_name": "Bettiah Sadar, Nautan, Chanpatia, Sikta, Majhauli, Dumra, Shikarpur, Ramnagar"}
                # ... add all remaining districts & blocks
    ]


    # Insert into Location model if not exists
    for loc in bihar_locations:
        if not Location.objects.filter(state_name="Bihar", district_name=loc["district_name"]).exists():
            Location.objects.create(state_name="Bihar", **loc)

    districts = list(Location.objects.filter(state_name="Bihar").values_list("district_name", flat=True).distinct())

    def generate_random_password(length=10):
        chars = string.ascii_letters + string.digits + "@#$!"
        return ''.join(secrets.choice(chars) for _ in range(length))

    if request.method == "POST":
        # Basic fields
        username = request.POST.get('username')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        mobile_number = request.POST.get('mobile_number')
        location_level = request.POST.get('location_level', '').lower()

        # Location info
        state_name = request.POST.get('state_name', '').strip()
        district_name = request.POST.get('district', '').strip() or ''
        block_name = request.POST.get('block_name', '').strip() or ''

        if not state_name:
            messages.error(request, "State name is required.")
            roles = Role.objects.filter(level=level_map.get(location_level, 'block'))
            return render(request, 'core/admin/add_block_member.html', {
                'roles': roles,
                'districts': districts,
                'blocks_by_district': blocks_by_district
            })

        # Role info
        role_id = request.POST.get('role')
        password = request.POST.get('password')
        is_active = 'is_active' in request.POST

        # Additional user details
        alternate_mobile_number = request.POST.get('alternate_mobile_number')
        dob = request.POST.get('dob')
        gender = request.POST.get('gender')
        father_or_mother_name = request.POST.get('father_or_mother_name')
        aadhar_or_govt_id = request.POST.get("aadhar_or_govt_id")
        permanent_address = request.POST.get('permanent_address')
        current_address = request.POST.get('current_address')
        block_tehsil_taluka = request.POST.get('block_tehsil_taluka')
        village_town_city = request.POST.get('village_town_city')
        pincode = request.POST.get('pincode')
        designation = request.POST.get('designation')
        assigned_block = request.POST.get('assigned_block')
        booths_handled = request.POST.get('booths_handled')
        experience = request.POST.get('experience')
        reference_person_name = request.POST.get("reference_person_name")
        reference_person_contact = request.POST.get('reference_person_contact')
        assigned_state = state_name
        assigned_district = district_name

        # File fields
        photo = request.FILES.get('photo')
        address_proof = request.FILES.get('address_proof')

        level_name = level_map.get(location_level, location_level)
        roles = Role.objects.filter(level=level_name)

        if not password:
            password = generate_random_password()

        role = roles.filter(id=role_id).first()
        if not role:
            messages.error(request, "Invalid role selected for the chosen location level.")
            return render(request, 'core/admin/add_block_member.html', {
                'roles': roles,
                'districts': districts,
                'blocks_by_district': blocks_by_district,
            })

        # Location create or get
        location, created = Location.objects.get_or_create(
            state_name=state_name,
            district_name=district_name,
            block_name=block_name,
            defaults={
                'state_name': state_name,
                'district_name': district_name,
                'block_name': block_name
            }
        )

        # User create
        user = User.objects.create_user(
            username=username,
            password=password,
            full_name=full_name,
            email=email,
            mobile_number=mobile_number,
            alternate_mobile_number=alternate_mobile_number,
            date_of_birth=dob,
            gender=gender,
            father_or_mother_name=father_or_mother_name,
            aadhar_or_govt_id=aadhar_or_govt_id,
            permanent_address=permanent_address,
            current_address=current_address,
            state=assigned_state,
            district=assigned_district,
            block_tehsil_taluka=block_tehsil_taluka,
            village_town_city=village_town_city,
            pincode=pincode,
            location=location,
            role=role,
            designation=designation,
            assigned_state=assigned_state,
            assigned_district=assigned_district,
            assigned_block=assigned_block,
            booths_handled=booths_handled,
            volunteer_experience=experience,
            reference_person_name=reference_person_name,
            reference_person_contact=reference_person_contact,
            photo=photo,
            address_proof=address_proof,
            is_active=is_active
        )

        user.location_level = location_level
        user.save()

        messages.success(request, f"{location_level.capitalize()} Member added successfully with username: {username}")
        return redirect('add_block_member')

    else:
        roles = Role.objects.filter(level='block')
        return render(request, 'core/admin/add_block_member.html', {
            'roles': roles,
            'districts': districts,   # 38 districts
            'state_name': 'Bihar'
        })




@superuser_required
def manage_block_member(request):
    block_roles = Role.objects.filter(level='block')
    if not block_roles.exists():
        messages.error(request, "No roles found for 'block' level.")
        members = User.objects.none()
    else:
        members = User.objects.filter(role__in=block_roles)

    # ✅ Block-wise search
    block_query = request.GET.get('block')
    if block_query:
        members = members.filter(assigned_block__icontains=block_query)

    # ✅ Username-wise search
    username_query = request.GET.get('username')
    if username_query:
        members = members.filter(username__icontains=username_query)

    # ✅ District + Block data
    districts_blocks = {
    "Araria": ["Araria", "Bhargama", "Forbesganj", "Jokihat", "Kursakatta", "Narpatganj", "Palasi", "Raniganj", "Sikti"],
    "Arwal": ["Arwal", "Kaler", "Karpi", "Kurtha"],
    "Aurangabad": ["Aurangabad", "Barun", "Deo", "Goh", "Haspura", "Kutumba", "Madanpur", "Nabinagar", "Obra", "Rafiganj"],
    "Banka": ["Amarpur", "Banka", "Barahat", "Belhar", "Bausi", "Bihat", "Chandan", "Dhuraiya", "Katoria", "Rajauli", "Shambhuganj", "Sultanganj", "Tola", "Udwantnagar"],
    "Begusarai": ["Bachhwara", "Bakhri", "Balia", "Barauni", "Begusarai", "Bhagwanpur", "Birpur", "Cheria Bariyarpur", "Dandari", "Garhpura", "Khodawandpur", "Mansurchak", "Matihani", "Naokothi", "Sahebpur Kamal", "Teghra", "Bihat"],
    "Bhagalpur": ["Bihpur", "Colgong", "Goradih", "Ismailpur", "Jagdishpur", "Kahalgaon", "Kharik", "Nathnagar", "Naugachhia", "Pirpainty", "Rangra Chowk", "Sabour", "Sanhaula", "Shahkund", "Sultanganj"],
    "Bhojpur": ["Agiaon", "Arrah", "Barhara", "Behea", "Charpokhari", "Garhani", "Jagdishpur", "Koilwar", "Piro", "Sahar", "Sandesh", "Shahpur", "Tarari", "Udwantnagar"],
    "Buxar": ["Buxar", "Itarhi", "Chausa", "Rajpur", "Dumraon", "Nawanagar", "Brahampur", "Kesath", "Chakki", "Chougain", "Simri"],
    "Darbhanga": ["Alinagar", "Benipur", "Biraul", "Baheri", "Bahadurpur", "Darbhanga Sadar", "Ghanshyampur", "Hayaghat", "Jale", "Keotirunway", "Kusheshwar Asthan", "Manigachhi", "Kiratpur", "Khutauna", "Muraul", "Purnahiya", "Rajnagar", "Shivnagar", "Singhwara", "Tardih", "Wazirganj", "Gaurabauram", "Khamhria"],
    "Gaya": ["Gaya Sadar", "Belaganj", "Wazirganj", "Manpur", "Bodhgaya", "Tekari", "Konch", "Guraru", "Paraiya", "Neemchak Bathani", "Khizarsarai", "Atri", "Bathani", "Mohra", "Sherghati", "Gurua", "Amas", "Banke Bazar", "Imamganj", "Dumariya", "Dobhi", "Mohanpur", "Barachatti", "Fatehpur"],
    "Gopalganj": ["Gopalganj", "Thawe", "Kuchaikote", "Manjha", "Sidhwaliya", "Hathua", "Baikunthpur", "Barauli", "Kateya", "Phulwariya", "Panchdewari", "Uchkagaon", "Vijayipur", "Bhorey"],
    "Jamui": ["Jamui", "Sikandra", "Khaira", "Chakai", "Sono", "Laxmipur", "Jhajha", "Barhat", "Gidhour", "Islamnagar Aliganj"],
    "Jehanabad": ["Jehanabad", "Makhdumpur", "Ghosi", "Hulasganj", "Ratni Faridpur", "Modanganj", "Kako"],
    "Kaimur": ["Adhaura", "Bhabua", "Bhagwanpur", "Chainpur", "Chand", "Rampur", "Durgawati", "Kudra", "Mohania", "Nuaon", "Ramgarh"],
    "Katihar": ["Katihar", "Barsoi", "Manihari", "Falka", "Kadwa", "Kursela", "Hasanganj", "Sameli", "Pranpur", "Korha"],
    "Khagaria": ["Khagaria", "Beldaur", "Parbatta", "Hasanpur", "Chautham", "Mansi", "Gogri", "Simri Bakhtiyarpur"],
    "Kishanganj": ["Kishanganj", "Bahadurganj", "Dighalbank", "Thakurganj", "Goalpokhar", "Islampur"],
    "Lakhisarai": ["Lakhisarai", "Ramgarh Chowk", "Surajgarha", "Barahiya", "Chanan"],
    "Madhepura": ["Madhepura", "Kumargram", "Singheshwar", "Murliganj", "Gopalpur", "Udaipur", "Alamnagar", "Shankarpur", "Madhepura Sadar"],
    "Madhubani": ["Andhratharhi", "Babubarhi", "Basopatti", "Benipatti", "Bisfi", "Ghoghardiha", "Harlakhi", "Jhanjharpur", "Kaluahi", "Khajauli", "Ladania", "Laukahi", "Madhepur", "Madhwapur", "Pandaul", "Phulparas", "Rajnagar", "Sakri", "Shankarpur", "Tardih", "Lakhnaur"],
    "Munger": ["Munger Sadar", "Bariyarpur", "Chandan", "Sangrampur", "Tarapur", "Jamalpur", "Kharagpur", "Hathidah"],
    "Muzaffarpur": ["Muzaffarpur Sadar", "Musahari", "Marwan", "Bochahan", "Katra", "Saraiya", "Paroo", "Sakra", "Gorhara", "Motipur", "Barahiya", "Minapur", "Meenapur", "Aurai", "Piprahi", "Aurai", "Saraiya", "Bochahan"],
    "Nalanda": ["Bihar Sharif", "Rajgir", "Harnaut", "Islampur", "Hilsa", "Noorsarai", "Ekangarsarai", "Asthawan", "Katri", "Silao", "Nalanda Sadar"],
    "Nawada": ["Nawada Sadar", "Akbarpur", "Narhat", "Pakribarawan", "Hisua", "Warisaliganj", "Kawakol", "Roh", "Rajauli"],
    "Patna": ["Patna Sadar", "Daniyaw", "Bakhtiyarpur", "Fatuha", "Paliganj", "Danapur", "Maner", "Naubatpur", "Sampatchak", "Masaurhi", "Khusrupur", "Bihta", "Punpun", "Barh", "Phulwari", "Dhanarua"],
    "Purnia": ["Purnia Sadar", "Banmankhi", "Dhamdaha", "Rupauli", "Baisi", "Kasba", "Bhawanipur", "Barhara Kothi", "Sukhasan", "Amour", "Krityanand Nagar", "Jalalgarh", "Bhagalpur", "Purnia City"],
    "Rohtas": ["Rohtas Sadar", "Sasaram", "Nokha", "Dehri", "Akbarpur", "Nauhatta", "Rajpur", "Chenari", "Tilouthu", "Rohtas", "Dumraon"],
    "Saharsa": ["Saharsa Sadar", "Mahishi", "Simri Bakhtiyarpur", "Sonbarsa", "Madhepur", "Pipra", "Salkhua", "Patarghat", "Alamnagar"],
    "Samastipur": ["Samastipur Sadar", "Ujiarpur", "Morwa", "Sarairanjan", "Warisnagar", "Kalyanpur", "Dalsinghsarai", "Hasanpur", "Patori", "Vidyapati Nagar", "Tajpur", "Makhdumpur", "Musrigharari", "Shivajinagar", "Goriakothi"],
    "Saran": ["Chapra Sadar", "Marhaura", "Dighwara", "Parsa", "Sonpur", "Garkha", "Amnour", "Dariapur", "Taraiya", "Manjhi", "Sonepur", "Masrakh", "Parsauni"],
    "Sheikhpura": ["Sheikhpura Sadar", "Chewara", "Ariari", "Barbigha", "Hasanpur", "Pirpainti", "Sheikhpura", "Nathnagar"],
    "Sheohar": ["Sheohar Sadar", "Purnahiya", "Dumri Katsari", "Piprarhi", "Mehsi"],
    "Sitamarhi": ["Sitamarhi Sadar", "Belsand", "Bajpatti", "Choraut", "Bathnaha", "Suppi", "Riga", "Runnisaidpur", "Pupri", "Sursand", "Bairgania", "Nanpur"],
    "Siwan": ["Siwan Sadar", "Barharia", "Bhagwanpur Hat", "Daraundha", "Goriakothi", "Guthani", "Hussainganj", "Lakri Nabiganj", "Maharajganj", "Nautan", "Pachrukhi", "Raghunathpur", "Mairwa"],
    "Vaishali": ["Hajipur", "Lalganj", "Mahua", "Mahnar", "Patepur", "Rajapakar", "Bidupur", "Chehrakala", "Desari", "Goraul", "Jandaha", "Sahdei Buzurg"],
    "Forbesganj": ["Forbesganj", "Araria", "Bhargama", "Raniganj", "Palasi", "Sikti", "Jokihat", "Kursakatta", "Narpatganj"],
    "Mokama": ["Mokama", "Ghoswari", "Pandarak", "Barh", "Daniyawan", "Bikramganj", "Kharagpur"],
    "Bettiah": ["Bettiah Sadar", "Nautan", "Chanpatia", "Sikta", "Majhauli", "Dumra", "Shikarpur", "Ramnagar"],
}


    return render(request, 'core/admin/manage_block_member.html', {
        'members': members,
        'query': block_query or "",
        'username': username_query or "",
        'districts_blocks': districts_blocks
    })



@superuser_required
def edit_block_member(request, member_id):
    member = get_object_or_404(User, id=member_id)
    roles = Role.objects.all()

    if request.method == 'POST':
        email = request.POST['email']
        if User.objects.filter(email=email).exclude(id=member_id).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'core/admin/edit_block_member.html', {'member': member, 'roles': roles})

        member.username = request.POST['username']
        member.full_name = request.POST['full_name']
        member.email = email
        mobile_number = request.POST.get('mobile_number')  # ✅ Safe
        member.address = request.POST['address']
        member.is_active = 'is_active' in request.POST

        # Role update
        role_id = request.POST.get('role')
        if role_id:
            member.role = Role.objects.get(id=role_id)

        # Location update
        location_name = request.POST.get('block')
        try:
            member.location = Location.objects.get(block_name=location_name)
        except Location.DoesNotExist:
            messages.error(request, f"Block '{location_name}' does not exist.")
            return render(request, 'core/admin/edit_block_member.html', {'member': member, 'roles': roles})

        member.save()
        messages.success(request, 'Block member updated successfully.')
        return redirect('manage_block_member')

    return render(request, 'core/admin/edit_block_member.html', {'member': member, 'roles': roles})


@superuser_required
def delete_block_member(request, member_id):
    member = get_object_or_404(User, id=member_id)
    if request.method == 'POST':
        member.delete()
        messages.success(request, 'Block member deleted successfully.')
        return redirect('manage_block_member')
    return render(request, 'core/admin/confirm_delete.html', {'member': member})

# -------------------------------------------
# CORE MEMBER CRUD
# -------------------------------------------

@superuser_required
def add_core_member(request):
    roles = Role.objects.all()

    def generate_random_password(length=10):
        chars = string.ascii_letters + string.digits + "@#$!"
        return ''.join(secrets.choice(chars) for _ in range(length))

    if request.method == "POST":
        username = request.POST.get('username')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        mobile_number = request.POST.get('mobile_number')
        role_id = request.POST.get('role')
        location_level = request.POST.get('location_level')

        # Default state_name set kar diya agar blank ho
        state_name = request.POST.get('state_name', '').strip() or 'YourDefaultState'
        district_name = request.POST.get('district_name', '').strip()
        block_name = request.POST.get('block_name', '').strip()
        address = request.POST.get('address')
        password = request.POST.get('password')
        is_verified = 'is_verified' in request.POST
        is_active = True

        access_start_time_str = request.POST.get('access_start_time')
        access_end_time_str = request.POST.get('access_end_time')

        if not password:
            password = generate_random_password()

        role = Role.objects.filter(id=role_id).first()
        if not role:
            messages.error(request, "Invalid role selected.")
            return render(request, 'core/admin/add_core_member.html', {
                'roles': roles,
                'generated_password': password
            })

        # Location logic — ab state_name me default value aane par bhi sahi se kaam karega
        location = None
        if location_level == 'state' and state_name:
            location, _ = Location.objects.get_or_create(
                state_name=state_name, district_name='NA', block_name='NA'
            )
        elif location_level == 'district' and state_name and district_name:
            location, _ = Location.objects.get_or_create(
                state_name=state_name, district_name=district_name, block_name='NA'
            )
        elif location_level == 'block' and state_name and district_name and block_name:
            location, _ = Location.objects.get_or_create(
                state_name=state_name, district_name=district_name, block_name=block_name
            )
        else:
            messages.error(request, "Please fill all required fields for the selected location level.")
            return render(request, 'core/admin/add_core_member.html', {
                'roles': roles,
                'generated_password': password
            })

        # Duplication checks
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'core/admin/add_core_member.html', {
                'roles': roles,
                'generated_password': password
            })

        if email and User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, 'core/admin/add_core_member.html', {
                'roles': roles,
                'generated_password': password
            })

        if mobile_number and User.objects.filter(mobile_number=mobile_number).exists():
            messages.error(request, "Mobile number already exists.")
            return render(request, 'core/admin/add_core_member.html', {
                'roles': roles,
                'generated_password': password
            })

        # Parse & convert to timezone-aware
        try:
            access_start_time = datetime.strptime(access_start_time_str, '%Y-%m-%dT%H:%M') if access_start_time_str else None
            access_end_time = datetime.strptime(access_end_time_str, '%Y-%m-%dT%H:%M') if access_end_time_str else None

            if access_start_time:
                access_start_time = timezone.make_aware(access_start_time)
            if access_end_time:
                access_end_time = timezone.make_aware(access_end_time)

        except ValueError:
            messages.error(request, "Access start/end time format sahi nahi hai. Format: YYYY-MM-DDTHH:MM")
            return render(request, 'core/admin/add_core_member.html', {
                'roles': roles,
                'generated_password': password
            })

        # **User create karne se pehle aur baad me print lagao taaki debug ho sake**
        try:
            print("Creating user with:", username, full_name, email, mobile_number, role, location)
            
            user = User.objects.create_user(
                username=username,
                password=password,
                full_name=full_name,
                email=email,
                mobile_number=mobile_number,
                address=address,
                role=role,
                location=location,
                is_verified=is_verified,
                is_active=is_active,
                access_start_time=access_start_time,
                access_end_time=access_end_time,
            )
            
            print("User created successfully:", user)
        except Exception as e:
            print("Error while creating user:", e)
            messages.error(request, f"Error creating user: {e}")
            return render(request, 'core/admin/add_core_member.html', {
                'roles': roles,
                'generated_password': password
            })

        messages.success(request, f"Core member '{username}' added successfully.")
        return redirect('manage_core_member')

    generated_password = generate_random_password()
    return render(request, 'core/admin/add_core_member.html', {
        'roles': roles,
        'generated_password': generated_password
    })


@superuser_required
def manage_core_member(request):
    try:
        core_role = Role.objects.get(role_name='Core Member')
    except Role.DoesNotExist:
        messages.error(request, "Role 'Core Member' nahi mila.")
        core_role = None

    if core_role:
        query = request.GET.get('q', '')
        if query:
            members = User.objects.filter(role=core_role).filter(
                Q(username__icontains=query) | Q(full_name__icontains=query)
            )
        else:
            members = User.objects.filter(role=core_role)
    else:
        members = User.objects.none()

    return render(request, 'core/admin/manage_core_member.html', {'members': members})


@superuser_required
def edit_core_member(request, member_id):
    member = get_object_or_404(User, id=member_id)
    roles = Role.objects.all()

    if request.method == 'POST':
        email = request.POST.get('email')
        if User.objects.filter(email=email).exclude(id=member_id).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'core/admin/edit_core_member.html', {'member': member, 'roles': roles})

        member.full_name = request.POST.get('full_name')
        member.email = email
        role_id = request.POST.get('role')
        member.role = Role.objects.filter(id=role_id).first()
        member.address = request.POST.get('address')

        # Location update
        location_level = request.POST.get('location_level')
        state_name = request.POST.get('state_name')
        district_name = request.POST.get('district_name')
        block_name = request.POST.get('block_name')

        location = None
        if location_level == 'state' and state_name:
            location, _ = Location.objects.get_or_create(
                state_name=state_name, district_name='NA', block_name='NA'
            )
        elif location_level == 'district' and state_name and district_name:
            location, _ = Location.objects.get_or_create(
                state_name=state_name, district_name=district_name, block_name='NA'
            )
        elif location_level == 'block' and state_name and district_name and block_name:
            location, _ = Location.objects.get_or_create(
                state_name=state_name, district_name=district_name, block_name=block_name
            )
        member.location = location

        # Timezone-aware time parsing
        access_start_time_str = request.POST.get('access_start_time')
        access_end_time_str = request.POST.get('access_end_time')

        try:
            if access_start_time_str:
                dt = datetime.strptime(access_start_time_str, '%Y-%m-%d %H:%M')
                member.access_start_time = timezone.make_aware(dt)
            else:
                member.access_start_time = None

            if access_end_time_str:
                dt = datetime.strptime(access_end_time_str, '%Y-%m-%d %H:%M')
                member.access_end_time = timezone.make_aware(dt)
            else:
                member.access_end_time = None

        except ValueError:
            messages.error(request, "Access start/end time format sahi nahi hai. Format: YYYY-MM-DD HH:MM")
            return render(request, 'core/admin/edit_core_member.html', {'member': member, 'roles': roles})

        member.save()
        messages.success(request, 'Core member updated successfully.')
        return redirect('manage_core_member')

    return render(request, 'core/admin/edit_core_member.html', {'member': member, 'roles': roles})


@superuser_required
def delete_core_member(request, member_id):
    member = get_object_or_404(User, id=member_id)
    if request.method == 'POST':
        member.delete()
        messages.success(request, 'Core member deleted successfully.')
        return redirect('manage_core_member')
    return render(request, 'core/admin/confirm_delete.html', {'member': member})

# -------------------------------------------
# TOGGLE ACTIVE STATUS (AJAX)
# -------------------------------------------

@login_required
@csrf_exempt
def toggle_active_status(request):
    if request.method == 'POST' and request.is_ajax():
        data = json.loads(request.body)

        level = data.get('level')
        member_id = data.get('member_id')
        is_active = data.get('is_active')

        # Mapping level to model
        model_map = {
            'state': StatelevelPartyMember,
            'district': DistrictlevelPartyMember,
            'block': BlocklevelPartyMember,
            'core': CoreMember,
        }

        ModelClass = model_map.get(level)
        if not ModelClass:
            return JsonResponse({'status': 'error', 'message': 'Invalid member level.'})

        try:
            member = ModelClass.objects.get(id=member_id)
            member.is_active = is_active
            member.save()
            return JsonResponse({'status': 'success'})
        except ModelClass.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Member not found.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method or not AJAX.'})





from django.views.decorators.http import require_GET

def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

@require_GET
def generate_password_api(request):
    password = generate_random_password()
    return JsonResponse({'password': password})






# Superuser check
def is_superuser(user):
    return user.is_superuser







from django.contrib.auth.decorators import login_required, user_passes_test

def is_district_user(user):
    return (
        user.is_authenticated and
        hasattr(user, 'role') and
        user.role is not None and
        user.role.level == 'district' and
        user.role.role_name in [
            'District President',
            'District Vice President',
            'District General Secretary',
            'District Secretary',
            'District Treasurer',
            'District Spokesperson',
            'District Youth Wing President',
            'District Mahila Wing President',
            'District Minority Cell In-charge'
        ]
    )




@login_required(login_url='admin_login')
@user_passes_test(is_district_user, login_url='admin_login')
def district_dashboard(request):
    user = request.user

    # Complaints in this district
    complaints = Complaint.objects.filter(
        state=user.state,
        district=user.district
    )

    total_complaints = complaints.count()
    solved_count = complaints.filter(status='Solved').count()
    accepted_count = complaints.filter(status='Accepted').count()
    rejected_count = complaints.filter(status='Rejected').count()

    # Block-wise **forwarded complaints**
    forwarded_by_block = complaints.filter(
        # Sirf wo complaints jo block se forward hue hain
        send_to='district',  # ya jo field mark kare ki forward hua
        status='Accepted'    # ya forwarded
    ).values('block').annotate(count=Count('id'))

    return render(request, 'core/district_admin/district_dashboard.html', {
        'total_complaints': total_complaints,
        'solved_count': solved_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'forwarded_by_block': forwarded_by_block,
    })

@login_required
@user_passes_test(is_district_user, login_url='admin_login')
def forward_complaint_to_state(request, complaint_id):
    if request.method == 'POST':
        # Complaint get karo, lekin sirf usi state ka jisse user assigned hai
        complaint = get_object_or_404(
            Complaint,
            id=complaint_id,
            state=request.user.assigned_state  # filter lagaya
        )

        # State level ke admins filter karo
        state_admins = User.objects.filter(
            role__level='state',
            state=complaint.state
        )

        if state_admins.exists():
            complaint.assigned_to = state_admins.first()  # pehle admin ko assign kar rahe
            complaint.save()
            messages.success(request, "Complaint successfully forwarded to state admin.")
        else:
            messages.error(request, "No state admin found for this state.")
    else:
        messages.error(request, "Invalid request method.")

    return redirect('district_admin_complaints')  # district complaints list page



@login_required
def district_profile(request):
    return render(request, 'core/district_admin/district_profile.html')





# views.py

@login_required
def district_admin_complaints(request):
    # User ke assigned state aur district fetch karo
    assigned_state = getattr(request.user, 'assigned_state', '').strip()
    assigned_district = getattr(request.user, 'assigned_district', '').strip()

    block_filter = request.GET.get("block", "").strip()
    panchayat_filter = request.GET.get("panchayat", "").strip()

    # Agar district assigned nahi hai toh empty queryset
    if not assigned_district:
        complaints = Complaint.objects.none()
    else:
        complaints = Complaint.objects.filter(
            state__iexact=assigned_state,
            district__iexact=assigned_district
        )

        # Block filter apply
        if block_filter:
            complaints = complaints.filter(block__iexact=block_filter)

        # Panchayat filter apply
        if panchayat_filter:
            complaints = complaints.filter(panchayat__iexact=panchayat_filter)

        complaints = complaints.order_by("-created_at")

    # Unique blocks aur panchayats dropdown ke liye nikal lo
    blocks = Complaint.objects.filter(
        state__iexact=assigned_state,
        district__iexact=assigned_district
    ).values_list("block", flat=True).distinct()

    panchayats = Complaint.objects.filter(
        state__iexact=assigned_state,
        district__iexact=assigned_district
    ).values_list("panchayat", flat=True).distinct()

    return render(request, "core/district_admin/complaints.html", {
        "complaints": complaints,
        "blocks": blocks,
        "panchayats": panchayats,
        "selected_block": block_filter,
        "selected_panchayat": panchayat_filter,
    })


@login_required
def district_complaints_forward(request, complaint_id):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, id=complaint_id)

        # Agar already forwarded hai to dobara mat bhejo
        if complaint.send_to == 'state':
            messages.warning(request, "Yeh complaint already State Admin ko forward ki gayi hai.")
            return redirect('district_admin_complaints')

        # State level wale admins filter karo
        state_admins = User.objects.filter(
            role__level='state',  # Tumhare User model me role structure ke hisaab se
            state=complaint.state
        )

        if state_admins.exists():
            complaint.send_to = 'state'
            complaint.save()
            messages.success(request, "Complaint successfully forwarded to State Admin.")
        else:
            messages.error(request, "No matching State Admin found to forward this complaint.")
    else:
        messages.error(request, "Invalid request method.")

    return redirect('district_admin_complaints')










# Forwarded complaints list (ye complaint_id nahi lega)
@login_required
def district_forwarded_complaints(request):
    complaints = Complaint.objects.filter(
        send_to='district',
        district=request.user.assigned_district  # same as in district_admin_complaints
    )
    return render(request, 'core/district_admin/forwarded_complaints.html', {'complaints': complaints})





@login_required
def district_complaints_delete(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
        complaint.delete()
        messages.success(request, 'Complaint deleted successfully!')
    except Complaint.DoesNotExist:
        messages.error(request, 'Complaint not found.')

    return redirect('district_admin_complaints')


@login_required
def district_complaints_accept(request, pk):
    if request.method == 'POST':
        try:
            complaint = Complaint.objects.get(pk=pk)
            complaint.status = 'Accepted'
            complaint.backend_response = 'Accepted'
            complaint.save()
            messages.success(request, 'Complaint accepted successfully.')
        except Complaint.DoesNotExist:
            messages.error(request, 'Complaint not found.')

    return redirect('district_admin_complaints')


@login_required
def district_complaints_reject(request, pk):
    if request.method == 'POST':
        try:
            complaint = Complaint.objects.get(pk=pk)
            complaint.status = 'Rejected'
            complaint.backend_response = 'Rejected'
            complaint.save()
            messages.success(request, 'Complaint rejected successfully.')
        except Complaint.DoesNotExist:
            messages.error(request, 'Complaint not found.')

    return redirect('district_admin_complaints')


@login_required
def district_complaints_solve(request, pk):
    if request.method == 'POST':
        try:
            complaint = Complaint.objects.get(pk=pk)
            complaint.resolved_at = timezone.now()
            complaint.status = 'Solved'
            complaint.save()
            messages.success(request, 'Complaint marked as solved.')
        except Complaint.DoesNotExist:
            messages.error(request, 'Complaint not found.')
            
    return redirect('district_admin_complaints')


@login_required
def district_complaints_resolve(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
        complaint.resolved_at = timezone.now()
        complaint.status = 'Solved'  # Ya jo bhi solved status ho
        complaint.save()
        messages.success(request, "Complaint marked as resolved.")
    except Complaint.DoesNotExist:
        messages.error(request, "Complaint not found.")

    return redirect('district_admin_complaints')  # Tumhara url name


@login_required
@user_passes_test(lambda u: (
    (u.role and u.role.level == 'block') or
    (u.role and u.role.role_name == 'Core Member' and u.location and u.location.block_name != 'NA')
))









def block_dashboard(request):
    user = request.user

    # All complaints of this block
    complaints = Complaint.objects.filter(
        state=user.assigned_state,
        district=user.assigned_district,
        block=user.assigned_block
    )

    # Status-wise counts
    total_count = complaints.count()
    accepted_count = complaints.filter(status='Accepted').count()
    rejected_count = complaints.filter(status='Rejected').count()
    solved_count = complaints.filter(status='Solved').count()
    pending_count = complaints.filter(status='Pending').count()

    
    # Forwarded complaints by Panchayat (Accepted complaints)
    forwarded_panchayat_counts = complaints.filter(
        status='Accepted'
    ).values('panchayat').annotate(count=Count('id'))

    return render(request, 'core/block_admin/block_dashboard.html', {
        'complaints': complaints,
        'total_count': total_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'solved_count': solved_count,
        'pending_count': pending_count,
        'forwarded_panchayat_counts': forwarded_panchayat_counts,
    })



@login_required
def block_admin_complaints(request):
    user = request.user

    # Safely get admin locations, agar None ho to empty string use karo
    user_block = user.assigned_block or ''
    user_district = user.assigned_district or ''
    user_state = user.assigned_state or ''

    # Public dwara submit kiye gaye complaints jinka state, district, block admin se match karta ho
    complaints = Complaint.objects.filter(
        state__iexact=user_state.strip(),
        district__iexact=user_district.strip(),
        block__iexact=user_block.strip()
    ).order_by('-created_at')

    # Count complaints by status
    status_counts = complaints.values('status').annotate(count=Count('id'))
    counts = {item['status']: item['count'] for item in status_counts}

    context = {
        'complaints': complaints,
        'total_complaints': complaints.count(),
        'solved_count': counts.get('Solved', 0),
        'rejected_count': counts.get('Rejected', 0),
        'accepted_count': counts.get('Accepted', 0),
        'pending_count': counts.get('Pending', 0),
    }

    return render(request, 'core/block_admin/complaints.html', context)

@login_required
def forward_complaint_to_district(request, complaint_id):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, id=complaint_id)

        # Agar already forwarded h to dobara na bheje
        if complaint.send_to == 'district':
            messages.warning(request, "This complaint has already been forwarded to the district.")
            return redirect('block_admin_complaints')

        # District level wale admins filter karo
        district_admins = User.objects.filter(
            role__level='district',
            district=complaint.district,
            state=complaint.state
        )

        if district_admins.exists():
            # 🔹 Forward chain me append karna
            complaint.forward_chain.append({
                "from": "block",
                "to": "district_admin",
                "level": "district",
                "reason": "Forwarded by block",  # agar reason chahiye to form se le sakte ho
                "date": datetime.now().strftime("%Y-%m-%d")  # <-- string format
            })

            complaint.send_to = 'district'
            complaint.save()
            messages.success(request, "Complaint successfully forwarded to district admin.")
        else:
            messages.error(request, "No matching district admin found to forward this complaint.")
    else:
        messages.error(request, "Invalid request method.")

    return redirect('block_admin_complaints')



# Same logic har delete, accept, reject, solve me apply karna hoga:
@login_required
def block_complaints_delete(request, pk):
    # Sirf primary key ke basis pe complaint get karo
    complaint = get_object_or_404(Complaint, pk=pk)
    
    # Complaint delete karo
    complaint.delete()
    
    # Success message
    messages.success(request, 'Complaint deleted successfully!')
    
    # Redirect back to block complaints page
    return redirect('block_admin_complaints')
    
# Accept
@login_required
def block_complaints_accept(request, pk):
    complaint = get_object_or_404(
        Complaint,
        pk=pk,
        block=request.user.block_tehsil_taluka,
        district=request.user.district,
        state=request.user.state,
        send_to='block'
    )
    complaint.status = 'Accepted'
    complaint.backend_response = 'Accepted'
    complaint.save()
    messages.success(request, 'Complaint accepted successfully.')
    return redirect('block_admin_complaints')

# Reject
@login_required
def block_complaints_reject(request, pk):
    complaint = get_object_or_404(
        Complaint,
        pk=pk,
        block=request.user.block_tehsil_taluka,
        district=request.user.district,
        state=request.user.state,
        send_to='block'
    )
    complaint.status = 'Rejected'
    complaint.backend_response = 'Rejected'
    complaint.save()
    messages.success(request, 'Complaint rejected.')
    return redirect('block_admin_complaints')

# Solve
@login_required
def block_complaints_solve(request, pk):
    complaint = get_object_or_404(
        Complaint,
        pk=pk,
        block=request.user.block_tehsil_taluka,
        district=request.user.district,
        state=request.user.state,
        send_to='block'
    )
    complaint.resolved_at = timezone.now()
    complaint.status = 'Solved'
    complaint.save()
    messages.success(request, 'Complaint marked as solved.')
    return redirect('block_admin_complaints')



@login_required
def block_profile(request):
    return render(request, 'core/block_admin/profile.html')



def logout_admin(request):
    logout(request)
    return redirect('home')













from django.contrib import messages

   
ROLE_DASHBOARD_MAPPING = {
    # Head Office Level
    ('head_office', 'Head Office Admin'): 'hod_dashboard',

    # State Level
    ('state', 'State President'): 'state_admin_dashboard',
    ('state', 'State Vice President'): 'state_admin_dashboard',
    ('state', 'State General Secretary'): 'state_admin_dashboard',
    ('state', 'State Secretary'): 'state_admin_dashboard',
    ('state', 'State Treasurer'): 'state_admin_dashboard',
    ('state', 'State Spokesperson'): 'state_admin_dashboard',
    ('state', 'State IT/Media Cell In-charge'): 'state_admin_dashboard',
    ('state', 'State Youth Wing President'): 'state_admin_dashboard',
    ('state', 'State Mahila (Women) Wing President'): 'state_admin_dashboard',
    ('state', 'State SC/ST/OBC Minority Wing Head'): 'state_admin_dashboard',
    ('state', 'State Legal Cell Head'): 'state_admin_dashboard',

    # District Level
    ('district', 'District President'): 'district_dashboard',
    ('district', 'District Vice President'): 'district_dashboard',
    ('district', 'District General Secretary'): 'district_dashboard',
    ('district', 'District Secretary'): 'district_dashboard',
    ('district', 'District Treasurer'): 'district_dashboard',
    ('district', 'District Spokesperson'): 'district_dashboard',
    ('district', 'District Youth Wing President'): 'district_dashboard',
    ('district', 'District Mahila Wing President'): 'district_dashboard',
    ('district', 'District Minority Cell In-charge'): 'district_dashboard',

    # Block Level
    ('block', 'Block President'): 'block_dashboard',
    ('block', 'Block Vice President'): 'block_dashboard',
    ('block', 'Block General Secretary'): 'block_dashboard',
    ('block', 'Block Secretary'): 'block_dashboard',
    ('block', 'Block Treasurer'): 'block_dashboard',
    ('block', 'Block Youth Wing Head'): 'block_dashboard',
    ('block', 'Block Mahila Wing Head'): 'block_dashboard',
    ('block', 'Block Minority Cell Head'): 'block_dashboard',

    # Booth Level ✅
    ('booth', 'Booth President'): 'booth_dashboard',
    ('booth', 'Booth Vice President'): 'booth_dashboard',
    ('booth', 'Booth Coordinator'): 'booth_dashboard',
    ('booth', 'Booth Youth Volunteer'): 'booth_dashboard',
    ('booth', 'Booth Mahila Volunteer'): 'booth_dashboard',
    ('booth', 'Booth Level Agent (BLA)'): 'booth_dashboard',
    ('booth', 'Booth In-charge (Voter List/Survey)'): 'booth_dashboard',

    # Core Level
    ('core', 'Core Member'): 'core_dashboard',
}

# -------------------------------
# Admin Login View
# -------------------------------
def admin_login(request):
    panel = request.GET.get('panel', 'hod')  # default HOD
    PANEL_LEVEL_MAPPING = {
        'hod': 'head_office',
        'state': 'state',
        'district': 'district',
        'block': 'block',
        'booth': 'booth',
    }
    panel_level = PANEL_LEVEL_MAPPING.get(panel, 'head_office')

    allowed_panels = [
        ('head_office', 'Head Office'),
        ('state', 'State'),
        ('district', 'District'),
        ('block', 'Block'),
        ('booth', 'Booth'),
    ]

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        selected_level = request.POST.get('user_type')  # dropdown se aayega level

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Your account is inactive.")
                return redirect(f'/admin-login/?panel={panel}')

            # ---- Superuser panel validation ----
            if user.is_superuser:
                if selected_level != 'head_office':
                    messages.error(request, "Superuser can only login via Head Office panel.")
                    return redirect(f'/admin-login/?panel={panel}')
                login(request, user)
                return redirect('hod_dashboard')  # superuser dashboard

            role = getattr(user, 'role', None)
            if not role:
                messages.error(request, "Role not assigned to user.")
                return redirect(f'/admin-login/?panel={panel}')

            # Selected level must match user's role level
            if role.level != selected_level:
                messages.error(request, "You selected an incorrect panel.")
                return redirect(f'/admin-login/?panel={panel}')

            login(request, user)

            # Redirect based on role level
            if role.level == 'head_office':
                return redirect('hod_dashboard')
            elif role.level == 'state':
                return redirect('state_admin_dashboard')
            elif role.level == 'district':
                return redirect('district_dashboard')
            elif role.level == 'block':
                return redirect('block_dashboard')
            elif role.level == 'booth':
                return redirect('booth_dashboard')

        else:
            messages.error(request, "Invalid username or password.")
            return redirect(f'/admin-login/?panel={panel}')

    return render(request, 'core/admin_login.html', {
        'allowed_panels': allowed_panels,
        'panel': panel,
    })

MODEL_MAP = {
    'hod': 'core.HOD',
    'state': 'core.StatelevelPartyMember',
    'district': 'core.DistrictlevelPartyMember',
    'block': 'core.BlocklevelPartyMember',
    'core': 'core.CoreMember',
}

@superuser_required
@csrf_exempt
def toggle_active(request, model_name, object_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            active_status = data.get('active', None)

            model_path = MODEL_MAP.get(model_name)
            if model_path is None:
                return JsonResponse({'success': False, 'error': 'Invalid model name'})

            app_label, model_class_name = model_path.split('.')
            Model = apps.get_model(app_label, model_class_name)  # ✅ Fix 2

            obj = Model.objects.get(id=object_id)

            if active_status is not None:
                obj.active = active_status
                obj.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid data'})
        
        except Model.DoesNotExist:
            return JsonResponse({'success': False, 'error': f'{model_name} not found'})

        except Exception as e:
            print(f"[toggle_active] ERROR: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})



@property
def is_expired(self):
    return self.valid_until is not None and timezone.now() > self.valid_until







@login_required
def location_based_complaints(request):
    user = request.user
    complaints = Complaint.objects.none()
    location_level = None

    if hasattr(user, 'location') and user.location:
        location = user.location

        if location.block_name and location.block_name != 'NA':
            complaints = Complaint.objects.filter(level='Block', location__block_name=location.block_name)
            location_level = 'Block'

        elif location.district_name and location.district_name != 'NA':
            complaints = Complaint.objects.filter(level='District', location__district_name=location.district_name)
            location_level = 'District'

        elif location.state_name and location.state_name != 'NA':
            complaints = Complaint.objects.filter(level='State', location__state_name=location.state_name)
            location_level = 'State'

    context = {
        'complaints': complaints,
        'location_level': location_level,
    }
    return render(request, 'core/complaints/location_based_complaints.html', context)



@login_required
def submit_complaint(request):
    if request.method == 'POST':
        # ----- Get form data -----
        complaint_data = {
            'name': request.POST.get('name', '').strip(),
            'mobile': request.POST.get('mobile', '').strip(),
            'address': request.POST.get('address', '').strip(),
            'state': request.POST.get('state', '').strip(),
            'district': request.POST.get('district', '').strip(),
            'block': request.POST.get('block', '').strip(),
            'panchayat': request.POST.get('panchayat', '').strip(),
            'village': request.POST.get('village', '').strip(),
            'pincode': request.POST.get('pincode', '').strip(),
            'issue_type': request.POST.get('issue_type', '').strip(),
            'title': request.POST.get('title', '').strip(),
            'description': request.POST.get('description', '').strip(),
        }

        photo = request.FILES.get('photo')
        upload_photo = request.FILES.get('upload_photo')
        upload_video = request.FILES.get('upload_video')

        # ----- Decide send_to based on hierarchy -----
        if complaint_data['panchayat']:
            send_to = 'booth'
        elif complaint_data['block']:
            send_to = 'block'
        elif complaint_data['district']:
            send_to = 'district'
        elif complaint_data['state']:
            send_to = 'state'
        else:
            send_to = 'none'

        # ✅ Save files path separately
        request.session['complaint_files'] = {
            'photo': photo.name if photo else None,
            'upload_photo': upload_photo.name if upload_photo else None,
            'upload_video': upload_video.name if upload_video else None,
        }

        # ✅ Save complaint data into session temporarily (not DB yet)
        request.session['pending_complaint'] = complaint_data
        request.session['pending_send_to'] = send_to

        mobile = complaint_data['mobile']

        # ✅ Send OTP to this mobile
        otp_sent = send_otp_to_mobile(mobile)
        if otp_sent:
            messages.info(request, f"OTP sent to {mobile}. Please verify to submit your complaint.")
            return redirect('verify_otp')  # redirect to OTP page
        else:
            messages.error(request, "Failed to send OTP. Try again.")
            return redirect('submit_complaint')

    return render(request, 'core/complaints/submit_complaint.html')


def logout_view(request):
    logout(request)
    return redirect('home') 





   

User = get_user_model()


def ajax_load_users(request):
    level = request.GET.get('level')
    users = User.objects.filter(role__level=level)
    
    data = [
        {
            'id': user.id,
            'full_name': user.get_full_name()  # ya user.name
        }
        for user in users
    ]
    
    return JsonResponse(data, safe=False)






def get_roles(request):
    level = request.GET.get('level')
    roles = Role.objects.filter(level=level).values(
        'id',
        name=F('role_name')  # 👈 alias banaya "name"
    )
    return JsonResponse({'roles': list(roles)})









@login_required
def district_complaints_list(request):
    user_state = request.user.state  # login user ka state le lo
    complaints = Complaint.objects.filter(state=user_state)
    return render(request, 'core/district_admin/complaints.html', {'complaints': complaints})

@login_required
def forwarded_complaints_list(request):
    user = request.user
    print("Logged in user:", user)
    print("User role level:", user.role.level)
    print("User state:", user.state)
    
    complaints = Complaint.objects.filter(assigned_to=user, send_to='state')
    print("Complaints count:", complaints.count())
    for c in complaints:
        print(c.id, c.title, c.assigned_to, c.send_to)

    return render(request, 'core/state_admin/forwarded_complaints.html', {'complaints': complaints})
















from django.utils.dateparse import parse_date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.dateparse import parse_date
from core.models import User, Role, Location

@superuser_required
def add_booth_member(request):
    # -----------------------
    # Bihar districts + blocks
    # -----------------------
    bihar_locations = [
        {"district_name": "Araria", "block_name": "Araria, Bhargama, Forbesganj, Jokihat, Kursakatta, Narpatganj, Palasi, Raniganj, Sikti"},
        {
        "district_name": "Arwal",
        "block_name": "Arwal, Kaler, Karpi, Kurtha"
        },
        {"district_name": "Aurangabad", "block_name": "Aurangabad, Barun, Deo, Goh, Haspura, Kutumba, Madanpur, Nabinagar, Obra, Rafiganj"},
        {
        "district_name": "Banka",
        "block_name": "Amarpur, Banka, Barahat, Belhar, Bausi, Bihat,  Chandan, Dhuraiya, Katoria, Rajauli, Shambhuganj, Sultanganj, Tola, Udwantnagar"
        },
        {
        "district_name": "Begusarai",
        "block_name": "Bachhwara, Bakhri, Balia, Barauni, Begusarai, Bhagwanpur, Birpur, Cheria Bariyarpur, Dandari, Garhpura, Khodawandpur, Mansurchak, Matihani, Naokothi, Sahebpur Kamal, Teghra, Bihat"
        },
        {"district_name": "Bhagalpur", "block_name": "Bihpur, Colgong, Goradih, Ismailpur, Jagdishpur, Kahalgaon, Kharik, Nathnagar, Naugachhia, Pirpainty, Rangra Chowk, Sabour, Sanhaula, Shahkund, Sultanganj"},
        {"district_name": "Bhojpur", "block_name": "Agiaon, Arrah, Barhara, Behea, Charpokhari, Garhani, Jagdishpur, Koilwar, Piro, Sahar, Sandesh, Shahpur, Tarari, Udwantnagar"},
        {"district_name": "Buxar", "block_name": "Buxar, Itarhi, Chausa, Rajpur, Dumraon, Nawanagar, Brahampur, Kesath, Chakki, Chougain, Simri"},
        {
        "district_name": "Darbhanga",
        "block_name": "Alinagar, Benipur, Biraul, Baheri, Bahadurpur, Darbhanga Sadar, Ghanshyampur, Hayaghat, Jale, Keotirunway, Kusheshwar Asthan, Manigachhi, Kiratpur, Khutauna, Muraul, Purnahiya, Rajnagar, Shivnagar, Singhwara, Tardih, Wazirganj, Gaurabauram, Khamhria"
        },

        {
        "district_name": "Gaya",
        "block_name": "Gaya Sadar, Belaganj, Wazirganj, Manpur, Bodhgaya, Tekari, Konch, Guraru, Paraiya, Neemchak Bathani, Khizarsarai, Atri, Bathani, Mohra, Sherghati, Gurua, Amas, Banke Bazar, Imamganj, Dumariya, Dobhi, Mohanpur, Barachatti, Fatehpur"
        },
        {
        "district_name": "Gopalganj",
        "block_name": "Gopalganj, Thawe, Kuchaikote, Manjha, Sidhwaliya, Hathua, Baikunthpur, Barauli, Kateya, Phulwariya, Panchdewari, Uchkagaon, Vijayipur, Bhorey"
        },
        {"district_name": "Jamui", "block_name": "Jamui, Sikandra, Khaira, Chakai, Sono, Laxmipur, Jhajha, Barhat, Gidhour, Islamnagar Aliganj"},
        {"district_name": "Jehanabad", "block_name": "Jehanabad, Makhdumpur, Ghosi, Hulasganj, Ratni Faridpur, Modanganj, Kako"},
        {"district_name": "Kaimur", "block_name": "Adhaura, Bhabua, Bhagwanpur, Chainpur, Chand, Rampur, Durgawati, Kudra, Mohania, Nuaon, Ramgarh"},
        {"district_name": "Katihar", "block_name": "Katihar, Barsoi, Manihari, Falka, Kadwa, Kursela, Hasanganj, Sameli, Pranpur, Korha"},
        {"district_name": "Khagaria", "block_name": "Khagaria, Beldaur, Parbatta, Hasanpur, Chautham, Mansi, Gogri, Simri Bakhtiyarpur"},
        {"district_name": "Kishanganj", "block_name": "Kishanganj, Bahadurganj, Dighalbank, Thakurganj, Goalpokhar, Islampur"},
        {
        "district_name": "Lakhisarai",
        "block_name": "Lakhisarai, Ramgarh Chowk, Surajgarha, Barahiya, Chanan"
        },
        {"district_name": "Madhepura", "block_name": "Madhepura, Kumargram, Singheshwar, Murliganj, Gopalpur, Udaipur, Alamnagar, Shankarpur, Madhepura Sadar"},
        {"district_name": "Madhubani", "block_name":  "Andhratharhi, Babubarhi, Basopatti, Benipatti, Bisfi, Ghoghardiha, Harlakhi, Jhanjharpur, Kaluahi, Khajauli, Ladania, Laukahi, Madhepur, Madhwapur, Pandaul, Phulparas, Rajnagar, Sakri, Shankarpur, Tardih, Lakhnaur"},
        {
        "district_name": "Munger",
        "block_name": "Munger Sadar, Bariyarpur, Chandan, Sangrampur, Tarapur, Jamalpur, Kharagpur, Hathidah"
        },
        {"district_name": "Muzaffarpur", "block_name": "Muzaffarpur Sadar, Musahari, Marwan, Bochahan, Katra, Saraiya, Paroo, Sakra, Gorhara, Motipur, Barahiya, Minapur, Meenapur, Aurai, Piprahi, Aurai, Saraiya, Bochahan"},
        {"district_name": "Nalanda", "block_name": "Bihar Sharif, Rajgir, Harnaut, Islampur, Hilsa, Noorsarai, Ekangarsarai, Asthawan, Katri, Silao, Nalanda Sadar"},
        {"district_name": "Nawada", "block_name": "Nawada Sadar, Akbarpur, Narhat, Pakribarawan, Hisua, Warisaliganj, Kawakol, Roh, Rajauli"},
        {"district_name": "Patna", "block_name": "Patna Sadar, Daniyaw, Bakhtiyarpur, Fatuha, Paliganj, Danapur, Maner, Naubatpur, Sampatchak, Masaurhi, Khusrupur, Bihta, Punpun, Barh, Phulwari, Dhanarua"},
        {"district_name": "Purnia", "block_name": "Purnia Sadar, Banmankhi, Dhamdaha, Rupauli, Baisi, Kasba, Bhawanipur, Barhara Kothi, Sukhasan, Amour, Krityanand Nagar, Jalalgarh, Bhagalpur, Purnia City"},
        {"district_name": "Rohtas", "block_name": "Rohtas Sadar, Sasaram, Nokha, Dehri, Akbarpur, Nauhatta, Rajpur, Chenari, Tilouthu, Rohtas, Dumraon"},
        {"district_name": "Saharsa", "block_name": "Saharsa Sadar, Mahishi, Simri Bakhtiyarpur, Sonbarsa, Madhepur, Pipra, Salkhua, Patarghat, Alamnagar"},
        {"district_name": "Samastipur", "block_name": "Samastipur Sadar, Ujiarpur, Morwa, Sarairanjan, Warisnagar, Kalyanpur, Dalsinghsarai, Hasanpur, Patori, Vidyapati Nagar, Tajpur, Makhdumpur, Musrigharari, Shivajinagar, Goriakothi"},
        {"district_name": "Saran", "block_name": "Chapra Sadar, Marhaura, Dighwara, Parsa, Sonpur, Garkha, Amnour, Dariapur, Taraiya, Manjhi, Sonepur, Masrakh, Parsauni"},
        {"district_name": "Sheikhpura", "block_name": "Sheikhpura Sadar, Chewara, Ariari, Barbigha, Hasanpur, Pirpainti, Sheikhpura, Nathnagar"},
        {"district_name": "Sheohar", "block_name": "Sheohar Sadar, Purnahiya, Dumri Katsari, Piprarhi, Mehsi"},
        {"district_name": "Sitamarhi", "block_name": "Sitamarhi Sadar, Belsand, Bajpatti, Choraut, Bathnaha, Suppi, Riga, Runnisaidpur, Pupri, Sursand, Bairgania, Nanpur"},
        {"district_name": "Siwan", "block_name": "Siwan Sadar, Barharia, Bhagwanpur Hat, Daraundha, Goriakothi, Guthani, Hussainganj, Lakri Nabiganj, Maharajganj, Nautan, Pachrukhi, Raghunathpur, Mairwa"},
        {"district_name": "Vaishali", "block_name": "Hajipur, Lalganj, Mahua, Mahnar, Patepur, Rajapakar, Bidupur, Chehrakala, Desari, Goraul, Jandaha, Sahdei Buzurg"},
        {
        "district_name": "Forbesganj",
        "block_name": "Forbesganj, Araria, Bhargama, Raniganj, Palasi, Sikti, Jokihat, Kursakatta, Narpatganj"
        },
        {"district_name": "Mokama", "block_name": "Mokama, Ghoswari, Pandarak, Barh, Daniyawan, Bikramganj, Kharagpur"},
        {"district_name": "Bettiah", "block_name": "Bettiah Sadar, Nautan, Chanpatia, Sikta, Majhauli, Dumra, Shikarpur, Ramnagar"}
    ]


    for loc in bihar_locations:
        if not Location.objects.filter(state_name="Bihar", district_name=loc["district_name"]).exists():
            Location.objects.create(state_name="Bihar", district_name=loc["district_name"], block_name=loc["block_name"])

    # Get all Bihar districts
    districts = list(Location.objects.filter(state_name="Bihar").values_list("district_name", flat=True).distinct())

    # Password generator
    def generate_password(length=10):
        chars = string.ascii_letters + string.digits + "@#$!"
        return ''.join(secrets.choice(chars) for _ in range(length))

    if request.method == 'POST':
        username = request.POST.get('username')

        # Username check
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please choose another.")
            return redirect('add_booth_member')

        full_name = request.POST.get('full_name')
        father_or_mother_name = request.POST.get('father_or_mother_name')
        dob_str = request.POST.get('date_of_birth')
        date_of_birth = parse_date(dob_str) if dob_str else None

        gender = request.POST.get('gender')
        mobile_number = request.POST.get('mobile_number')
        alternate_mobile_number = request.POST.get('alternate_mobile_number') or None
        email = request.POST.get('email')
        aadhar_or_govt_id = request.POST.get('aadhar_or_govt_id')
        permanent_address = request.POST.get('permanent_address')
        current_address = request.POST.get('current_address') or None

        # Auto-filled Bihar info
        state = 'Bihar'
        district = request.POST.get('district')
        block_tehsil_taluka = request.POST.get('block_tehsil_taluka')
        village_town_city = request.POST.get('village_town_city')
        pincode = request.POST.get('pincode')

        booth_number = request.POST.get('booth_number') or None
        ward_name = request.POST.get('ward_name') or None
        assigned_area = request.POST.get('assigned_area') or None
        voter_id_number = request.POST.get('voter_id_number') or None
        door_to_door = request.POST.get('door_to_door') or None
        availability = request.POST.get('availability') or None

        # Assigned fields auto-fill
        assigned_state = state
        assigned_district = district
        assigned_block = block_tehsil_taluka
        assigned_panchayat = request.POST.get('assigned_panchayat') or None

        photo = request.FILES.get('photo')
        id_proof = request.FILES.get('id_proof')
        address_proof = request.FILES.get('address_proof')
        digital_signature = request.FILES.get('digital_signature')

        role_id = request.POST.get('designation')
        role_instance = get_object_or_404(Role, id=role_id) if role_id else None

        location_id = request.POST.get('location')
        location_instance = get_object_or_404(Location, id=location_id) if location_id else None

        designation = role_instance.role_name if role_instance else None

        # Password from form (generated in template)
        password = request.POST.get('password') or generate_password()

        # Create user
        user = User(
            username=username,
            full_name=full_name,
            father_or_mother_name=father_or_mother_name,
            date_of_birth=date_of_birth,
            gender=gender,
            mobile_number=mobile_number,
            alternate_mobile_number=alternate_mobile_number,
            email=email,
            aadhar_or_govt_id=aadhar_or_govt_id,
            permanent_address=permanent_address,
            current_address=current_address,
            state=state,
            district=district,
            block_tehsil_taluka=block_tehsil_taluka,
            village_town_city=village_town_city,
            pincode=pincode,
            booth_number=booth_number,
            ward_name=ward_name,
            assigned_area=assigned_area,
            voter_id_number=voter_id_number,
            door_to_door=door_to_door,
            availability=availability,
            assigned_state=assigned_state,
            assigned_district=assigned_district,
            assigned_block=assigned_block,
            assigned_panchayat=assigned_panchayat,
            designation=designation,
            role=role_instance,
            location=location_instance,
            photo=photo,
            id_proof=id_proof,
            address_proof=address_proof,
            digital_signature=digital_signature,
            is_active=True,
        )
        user.set_password(password)
        user.save()

        messages.success(request, f"Booth Member successfully created. Password: {password}")
        return redirect('manage_booth_member')

    # GET request → send districts for dropdown
    return render(request, 'core/admin/add_booth_member.html', {
        'booth_roles': Role.objects.filter(level='booth'),
        'locations': Location.objects.all(),
        'districts': districts,  # Bihar ke 38 districts
        'state_name': 'Bihar'
    })

def manage_booth_member(request):
    # Get all booth-level members
    booth_members = User.objects.filter(role__level='booth').order_by('full_name')

    # ✅ Assigned Panchayat wise search
    panchayat_query = request.GET.get('panchayat')
    if panchayat_query:
        booth_members = booth_members.filter(assigned_panchayat__icontains=panchayat_query)

    return render(request, 'core/admin/manage_booth_member.html', {
        'booth_members': booth_members,
        'panchayat_query': panchayat_query or ""
    })


def edit_booth_member(request, id):
    member = get_object_or_404(User, id=id)
    booth_roles = Role.objects.all()

    if request.method == 'POST':
        try:
            # Basic fields
            member.full_name = request.POST.get('full_name', '').strip()
            member.parent_name = request.POST.get('parent_name', '').strip()
            member.dob = request.POST.get('dob') or None
            member.gender = request.POST.get('gender', '')
            member.mobile = request.POST.get('mobile', '').strip()
            member.alt_mobile = request.POST.get('alt_mobile', '').strip()
            member.email = request.POST.get('email', '').strip()
            member.govt_id = request.POST.get('govt_id', '').strip()
            member.permanent_address = request.POST.get('permanent_address', '').strip()
            member.current_address = request.POST.get('current_address', '').strip()
            member.state = request.POST.get('state', '').strip()
            member.district = request.POST.get('district', '').strip()
            member.block = request.POST.get('block', '').strip()
            member.village = request.POST.get('village', '').strip()
            member.pincode = request.POST.get('pincode', '').strip()

            # New booth-related fields
            member.booth_number = request.POST.get('booth_number', '').strip()
            member.ward_name = request.POST.get('ward_name', '').strip()
            member.assigned_area = request.POST.get('assigned_area', '').strip()
            member.assigned_panchayat = request.POST.get('assigned_panchayat', '').strip()  # ✅ new field
            member.voter_id_number = request.POST.get('voter_id_number', '').strip()
            member.door_to_door = request.POST.get('door_to_door', '').strip()
            member.availability = request.POST.get('availability', '').strip()
            member.assigned_state = request.POST.get('assigned_state', '').strip()
            member.assigned_district = request.POST.get('assigned_district', '').strip()
            member.assigned_block = request.POST.get('assigned_block', '').strip()

            # Role / designation update
            designation_id = request.POST.get('designation')
            if designation_id:
                role_instance = get_object_or_404(Role, id=designation_id)
                member.designation = role_instance.role_name  # CharField
                member.role = role_instance                   # ForeignKey

            # File uploads
            if request.FILES.get('photo'):
                member.photo = request.FILES['photo']
            if request.FILES.get('id_proof'):
                member.id_proof = request.FILES['id_proof']
            if request.FILES.get('address_proof'):
                member.address_proof = request.FILES['address_proof']  # ✅ new field
            if request.FILES.get('digital_signature'):
                member.digital_signature = request.FILES['digital_signature']  # ✅ new field

            # Save updated member
            member.save()
            messages.success(request, "✅ Booth Member updated successfully.")
            return redirect('manage_booth_member')

        except Exception as e:
            messages.error(request, f"❌ Error updating booth member: {e}")

    context = {
        'member': member,
        'booth_roles': booth_roles,
    }
    return render(request, 'core/admin/edit_booth_member.html', context)


def delete_booth_member(request, id):
    member = get_object_or_404(User, id=id)
    member.delete()
    messages.success(request, "Booth member deleted successfully.")
    return redirect('manage_booth_member')  # Aapka manage page ka URL name




@login_required
def booth_dashboard(request):
    # Assigned area for booth admin
    user = request.user
    assigned_state = getattr(user, 'assigned_state', None)
    assigned_district = getattr(user, 'assigned_district', None)
    assigned_block = getattr(user, 'assigned_block', None)
    assigned_panchayat = getattr(user, 'assigned_panchayat', None)

    complaints = Complaint.objects.all()

    # Filter by assigned area
    if assigned_state:
        complaints = complaints.filter(state__iexact=assigned_state)
    if assigned_district:
        complaints = complaints.filter(district__iexact=assigned_district)
    if assigned_block:
        complaints = complaints.filter(block__iexact=assigned_block)
    if assigned_panchayat:
        complaints = complaints.filter(panchayat__iexact=assigned_panchayat)

    total_complaints = complaints.count()
    accept_count = complaints.filter(status='Accepted').count()
    reject_count = complaints.filter(status='Rejected').count()
    solve_count = complaints.filter(status='Solved').count()

    # Panchayat-wise forwarded complaints
    panchayat_forward = complaints.values('panchayat').annotate(total=Count('id')).order_by('-total')

    return render(request, 'core/booth_admin/booth_dashboard.html', {
        'total_complaints': total_complaints,
        'accept_count': accept_count,
        'reject_count': reject_count,
        'solve_count': solve_count,
        'panchayat_forward': panchayat_forward
    })







def booth_forward_complaints(request):
    return render(request, 'core/booth_admin/forward_complaints.html')




from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from core.models import Complaint


@login_required
def booth_complaints(request):
    # Debugging: user ke location fields
    assigned_state = getattr(request.user, 'assigned_state', '').strip()
    assigned_district = getattr(request.user, 'assigned_district', '').strip()
    assigned_block = getattr(request.user, 'assigned_block', '').strip()
    assigned_panchayat = getattr(request.user, 'assigned_panchayat', '').strip()

    print("DEBUG USER FIELDS:", 
          request.user.id,
          assigned_state,
          assigned_district,
          assigned_block,
          assigned_panchayat)

    if not assigned_panchayat:
        complaints = Complaint.objects.none()
    else:
        # Filter complaints based on exact location match (case-insensitive)
        complaints = Complaint.objects.filter(
        state__iexact=assigned_state,
        district__iexact=assigned_district,
        block__iexact=assigned_block,
        panchayat__iexact=assigned_panchayat,
    ).order_by('-created_at')


    print("COMPLAINT COUNT:", complaints.count())
    return render(request, 'core/booth_admin/complaints.html', {'complaints': complaints})



@login_required
def booth_complaints_edit(request, pk):
    user = request.user
    complaint = get_object_or_404(
        Complaint,
        pk=pk,
        send_to='booth',
        state=user.assigned_state,
        district=user.assigned_district,
        block=user.assigned_block,
        panchayat=user.assigned_panchayat
    )

    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            form.save()
            messages.success(request, 'Complaint updated successfully!')
            return redirect('booth_complaints')
    else:
        form = ComplaintForm(instance=complaint)

    return render(request, 'core/booth_admin/booth_edit_complaint.html', {'form': form, 'complaint': complaint})


@login_required
def booth_complaints_delete(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
        complaint.delete()
        messages.success(request, 'Complaint deleted successfully!')
    except Complaint.DoesNotExist:
        messages.error(request, 'Complaint not found.')
        
    return redirect('booth_complaints')


@login_required
def booth_complaints_accept(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
        complaint.status = 'Accepted'
        complaint.save(update_fields=['status'])
        messages.success(request, 'Complaint accepted successfully.')
    except Complaint.DoesNotExist:
        messages.error(request, "Complaint not found.")
    
    return redirect('booth_complaints')

@login_required
def booth_complaints_reject(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
        complaint.status = 'Rejected'
        complaint.save(update_fields=['status'])
        messages.success(request, 'Complaint rejected successfully.')
    except Complaint.DoesNotExist:
        messages.error(request, "Complaint not found.")
    
    return redirect('booth_complaints')


@login_required
def booth_complaints_solve(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
        complaint.status = 'Solved'
        complaint.resolved_at = timezone.now()
        complaint.save(update_fields=['status', 'resolved_at'])
        messages.success(request, 'Complaint marked as solved.')
    except Complaint.DoesNotExist:
        messages.error(request, 'Complaint not found.')
    
    return redirect('booth_complaints')


from datetime import datetime
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

@login_required
def booth_complaints_forward(request, complaint_id):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, id=complaint_id)

        print("=== Forward View Called ===")
        print("Complaint ID:", complaint.id)
        print("Complaint Block:", complaint.block)
        print("Complaint District:", complaint.district)
        print("Complaint State:", complaint.state)
        print("Complaint Status:", complaint.status)

        if complaint.status == 'Forwarded':
            messages.warning(request, "This complaint has already been forwarded.")
            return redirect('booth_complaints')

        username = request.POST.get("username")   # 🆕 form se input
        reason = request.POST.get("reason")  

        # 1. Try Block Level User
        users = User.objects.filter(
            assigned_block__iexact=complaint.block.strip(),
            assigned_district__iexact=complaint.district.strip(),
            assigned_state__iexact=complaint.state.strip()
        )

        level = "block"

        # 2. Agar block level user na mile, district level check karo
        if not users.exists():
            users = User.objects.filter(
                assigned_district__iexact=complaint.district.strip(),
                assigned_state__iexact=complaint.state.strip()
            )
            level = "district"

        # 3. Agar district level user bhi na mile, state level check karo
        if not users.exists():
            users = User.objects.filter(
                assigned_state__iexact=complaint.state.strip()
            )
            level = "state"

        if users.exists():
        # 🔹 Forward chain me append karna
            complaint.forward_chain.append({
                "from": "booth",
                "to":" block",
                "level": level,
                "reason": reason,
                "date": datetime.now().strftime("%Y-%m-%d")  # sirf date store ho rahi
                # agar time bhi chahiye to "%Y-%m-%d %H:%M:%S" use karo
            })

            # 🔹 Existing forward fields update
            complaint.send_to = level
            complaint.status = 'Forwarded'
            complaint.forward_to = username   # ✅ save username
            complaint.forward_reason = reason  # ✅ save reason
            complaint.save()

            messages.success(request, f"Complaint successfully forwarded to {level} level admin.")
        else:
            messages.error(request, "No matching user found at Block/District/State level.")
    else:
        messages.error(request, "Invalid request method.")

    return redirect('booth_complaints')





@login_required
def block_forward_complaints(request):
    complaints = Complaint.objects.filter(
        state=request.user.assigned_state,
        district=request.user.assigned_district,
        block=request.user.assigned_block,
        send_to="block"   # 👈 sirf block ko forward kiye complaints
    ).order_by("-created_at")

    return render(
        request,
        "core/block_admin/forward_complaints.html",
        {"complaints": complaints}
    )



@login_required
def block_complaint_delete(request, pk):
    complaint = get_object_or_404(Complaint, id=pk)
    complaint.delete()
    messages.success(request, "Complaint deleted successfully.")
    return redirect('block_admin_complaints')


def block_complaint_pending(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    complaint.status = "Pending"
    complaint.save()
    messages.info(request, "Complaint marked as Pending.")
    return redirect("block_admin_complaints")


@login_required
def block_complaints_accept(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
        complaint.status = "Accepted"
        complaint.save(update_fields=['status'])
    except Complaint.DoesNotExist:
        pass  # Agar complaint exist nahi karti, silently ignore
    return redirect("block_admin_complaints")  # Ya aapka redirect URL

@login_required
def block_complaints_reject(request, pk):
    # Complaint fetch karo, agar exist na kare to silently ignore
    complaint = Complaint.objects.filter(pk=pk).first()
    if complaint:
        complaint.status = "Rejected"
        complaint.save(update_fields=['status'])
    # Redirect silently, koi message nahi
    return redirect("block_admin_complaints")  # Ya aapka redirect URL

@login_required
def block_complaints_solve(request, pk):
    try:
        complaint = Complaint.objects.get(pk=pk)
        complaint.status = "Solved"
        complaint.resolved_at = timezone.now()
        complaint.save(update_fields=['status'])
    except Complaint.DoesNotExist:
        pass
    return redirect("block_admin_complaints")







from django.db.models import Q

def get_complaints_for_user(user):
    qs = Complaint.objects.all()

    # Booth level
    if user.assigned_panchayat:
        qs = qs.filter(
            state=user.assigned_state,
            district=user.assigned_district,
            block=user.assigned_block,
            panchayat=user.assigned_panchayat
        )
    
    # Block level
    elif user.assigned_block:
        qs = qs.filter(
            state=user.assigned_state,
            district=user.assigned_district,
            block=user.assigned_block
        )
    
    # District level
    elif user.assigned_district:
        qs = qs.filter(
            state=user.assigned_state,
            district=user.assigned_district
        )

    return qs



@login_required
def complaint_list(request):
    user = request.user
    complaints = Complaint.objects.all()

    if user.role == "district":
        complaints = complaints.filter(
            state=user.assigned_state,
            district=user.assigned_district
        )

    elif user.role == "block":
        complaints = complaints.filter(
            state=user.assigned_state,
            district=user.assigned_district,
            block=user.assigned_block
        )

    elif user.role == "booth":
        complaints = complaints.filter(
            state=user.assigned_state,
            district=user.assigned_district,
            block=user.assigned_block,
            panchayat=user.assigned_panchayat
        )

    elif user.role == "state":
        complaints = complaints.filter(
            state=user.assigned_state
        )

    return render(request, "complaints/list.html", {"complaints": complaints})



@login_required
def location_based_complaints(request):
    user = request.user
    complaints = Complaint.objects.all()

    if user.role.level == 'state':
        complaints = complaints.filter(state=user.assigned_state, send_to='state')

    elif user.role.level == 'district':
        complaints = complaints.filter(
            state=user.assigned_state,
            district=user.assigned_district,
            send_to='district'
        )

    elif user.role.level == 'block':
        complaints = complaints.filter(
            state=user.assigned_state,
            district=user.assigned_district,
            block=user.assigned_block,
            send_to='block'
        )

    elif user.role.level == 'booth':
        complaints = complaints.filter(
            state=user.assigned_state,
            district=user.assigned_district,
            block=user.assigned_block,
            panchayat=user.assigned_panchayat,
            send_to='booth'
        )

    return render(request, 'core/complaints/location_based.html', {
        'complaints': complaints
    })


@login_required
def admin_complaints(request):
    user = request.user
    complaints = Complaint.objects.all()

    # ----- Filter complaints based on user role and assigned location -----
    if user.role:
        if user.role.level == 'state':
            complaints = complaints.filter(
                state=user.assigned_state,
                send_to='state'
            )

        elif user.role.level == 'district':
            complaints = complaints.filter(
                state=user.assigned_state,
                district=user.assigned_district,
                send_to='district'
            )

        elif user.role.level == 'block':
            complaints = complaints.filter(
                state=user.assigned_state,
                district=user.assigned_district,
                block=user.assigned_block,
                send_to='block'
            )

        elif user.role.level == 'booth':
            complaints = complaints.filter(
                state=user.assigned_state,
                district=user.assigned_district,
                block=user.assigned_block,
                panchayat=user.assigned_panchayat,
                send_to='booth'
            )

    # ----- Order by latest first -----
    complaints = complaints.order_by('-created_at')

    return render(request, 'core/complaints/location_based.html', {
        'complaints': complaints
    })