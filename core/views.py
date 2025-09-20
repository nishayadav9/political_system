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
        {
            "district_name": "Araria",
            "block_name": "Araria",
            "panchayats": [
            "Araria Basti", "Azamnagar Kusiyar Gawon", "Azmatpur Basantpur", "Bahgi Pokharia",
            "Bairgachhi Belwa", "Bangawan Bangama", "Bansbari Bansbari", "Barakamatchistipur Haria",
            "Basantpur Basantpur", "Baturbari Baturbari", "Belbari Araria Basti", "Belsandi Araria Basti",
            "Belwa Araria Basti", "Bhadwar Araria Basti", "Bhairoganj Araria Basti", "Bhanghi Araria Basti",
            "Bhawanipur Araria Basti", "Bhorhar Araria Basti", "Chakorwa Araria Basti", "Dahrahra Araria Basti",
            "Damiya Araria Basti", "Dargahiganj Araria Basti", "Dombana Araria Basti", "Dumari Araria Basti",
            "Fatehpur Araria Basti", "Gadhgawan Araria Basti", "Gandhi Araria Basti", "Gangauli Araria Basti",
            "Ganj Araria Basti", "Gogri Araria Basti", "Gopalpur Araria Basti"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Forbesganj",
            "panchayats": [
            "Forbesganj", "Araria", "Bhargama", "Raniganj", "Sikti", "Palasi",
            "Jokihat", "Kursakatta", "Narpatganj", "Hanskosa", "Hardia", "Haripur",
            "Hasanpur Khurd", "Hathwa", "Gadaha", "Ganj Bhag", "Ghiwba", "Ghoraghat",
            "Gogi", "Gopalpur", "Gurmahi", "Halhalia", "Halhalia Jagir"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Jokihat",
            "panchayats": [
            "Jokihat", "Artia Simaria", "Bagdahara", "Bagesari", "Bagmara", "Bagnagar",
            "Baharbari", "Bairgachhi", "Bankora", "Bara Istamrar", "Bardenga", "Barhuwa",
            "Bazidpur", "Beldanga", "Bela", "Belsandi", "Belwa", "Bhatkuri", "Bharwara",
            "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri", "Dundbahadur Chakla", "Gamharia"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Kursakatta",
            "panchayats": [
            "Kursakatta", "Kamaldaha", "Kuari", "Lailokhar", "Sikti", "Singhwara", "Sukhasan", "Bairgachhi"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Narpatganj",
            "panchayats": [
            "Narpatganj", "Ajitnagar", "Amrori", "Anchraand Hanuman Nagar", "Baghua Dibiganj",
            "Bardaha", "Barhara", "Barhepara", "Bariarpur", "Barmotra Arazi", "Basmatiya", "Bela",
            "Belsandi", "Belwa"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Palasi",
            "panchayats": [
            "Palasi", "Bakainia", "Balua", "Bangawan", "Baradbata", "Baraili", "Bargaon",
            "Barkumba", "Behari", "Belbari", "Belsari", "Beni", "Beni Pakri"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Raniganj",
            "panchayats": [
            "Raniganj", "Asabhag", "Asura Kalan Khola", "Bakhri Milik", "Balchanda", "Banmali",
            "Batraha", "Bhag Parasi", "Bhagtira", "Bhaloa", "Bhimpur Khar", "Bhishunpur",
            "Bhorha", "Bhutahi", "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri",
            "Dundbahadur Chakla", "Gamharia", "Gamharia Milik"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Sikti",
            "panchayats": [
            "Sikti", "Asabhag", "Asura Kalan Khola", "Bakhri Milik", "Balchanda", "Banmali",
            "Batraha", "Bhag Parasi", "Bhagtira", "Bhaloa", "Bhimpur Khar", "Bhishunpur",
            "Bhorha", "Bhutahi", "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri",
            "Dundbahadur Chakla", "Gamharia", "Gamharia Milik"
            ]
        },
            
        {
            "district_name": "Arwal",
            "block_name": "Arwal",
            "panchayats": ["Abgila", "Amara", "Arwal Sipah", "Basilpur", "Bhadasi", "Fakharpur", "Khamaini", "Makhdumpur", "Muradpur Hujara", "Parasi", "Payarechak", "Rampur Baina"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Kaler",
            "panchayats": ["Sakri Khurd", "Balidad", "Belawan", "Belsar", "Injor", "Ismailpur Koyal", "Jaipur", "Kaler", "Kamta", "Mainpura", "North Kaler", "Pahleja"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Karpi",
            "panchayats": ["Khajuri", "Kochahasa", "Aiyara", "Bambhi", "Belkhara", "Chauhar", "Dorra", "Kapri", "Karpi", "Keyal", "Kinjar", "Murarhi"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Kurtha",
            "panchayats": ["Ahmadpur Harna", "Alawalpur", "Bahbalpur", "Baid Bigha", "Bara", "Barahiya", "Basatpur", "Benipur", "Bishunpur", "Chhatoi", "Dakra", "Darheta", "Dhamaul", "Dhondar", "Gangapur", "Gangea", "Gauhara", "Gokhulpur", "Harpur", "Helalpur", "Ibrahimpur", "Jagdispur", "Khaira", "Khemkaran Saray", "Kimdar Chak", "Kod marai", "Koni", "Kothiya", "Kubri", "Kurkuri", "Kurthadih", "Lari", "Lodipur", "Madarpur", "Mahmadpur", "Makhdumpur", "Manikpur", "Manikpur", "Milki", "Mobarakpur", "Molna Chak", "Motipur", "Musarhi", "Nadaura", "Narhi", "Nezampur", "Nighwan"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Sonbhadra Banshi Suryapur",
            "panchayats": ["Sonbhadra", "Banshi", "Suryapur"]
        },
         {
            "district_name": "Aurangabad",
            "block_name": "Aurangabad",
            "panchayats": ["Aurangabad Sadar", "Barun", "Karmabad", "Bachra", "Bhawanipur", "Chakibazar", "Dhanauti", "Jaitpur", "Khurampur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Barun",
            "panchayats": ["Barun", "Bhagwanpur", "Kundahar", "Laxmanpur", "Rampur", "Sasaram", "Senga", "Tandwa"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Deo",
            "panchayats": ["Deo", "Bakar", "Chakand", "Gopalpur", "Jamalpur", "Kachhahi", "Kekri", "Manjhi"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Goh",
            "panchayats": ["Goh", "Kachhawa", "Kanchanpur", "Khirpai", "Makhdumpur", "Rajnagar", "Rampur", "Sarwa"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Haspura",
            "panchayats": ["Haspura", "Barauli", "Belwar", "Bichkoi", "Chandi", "Khapri", "Mahmoodpur", "Nuaon"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Kutumba",
            "panchayats": ["Kutumba", "Brajpura", "Chak Mukundpur", "Daharpur", "Gopalpur", "Jhunjhunu", "Rampur", "Sahar"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Madanpur",
            "panchayats": ["Madanpur", "Amra", "Bajidpur", "Barachatti", "Chakiya", "Dhanpur", "Kachhawa", "Rampur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Nabinagar",
            "panchayats": ["Nabinagar", "Alipur", "Chhatauni", "Deohra", "Jafarpur", "Rampur", "Shivpur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Obra",
            "panchayats": ["Obra", "Biharichak", "Chhata", "Harikala", "Kandua", "Rampur", "Sakra"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Rafiganj",
            "panchayats": ["Rafiganj", "Barauni", "Bhagwanpur", "Chakuli", "Deoghar", "Mohanpur", "Rampur", "Sikta"]
        },
        


        {
            "district_name": "Banka",
            "block_name": "Amarpur",
            "panchayats": ["Amarpur", "Chouka", "Dhamua", "Gopalpur", "Haripur", "Jagdishpur", "Kharagpur", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Banka",
            "panchayats": ["Banka Sadar", "Barhampur", "Chandipur", "Dumaria", "Kharik", "Maheshpur", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Barahat",
            "panchayats": ["Barahat", "Chakpura", "Durgapur", "Jagdishpur", "Kudra", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Belhar",
            "panchayats": ["Belhar", "Chakbhabani", "Durgapur", "Maheshpur", "Rampur", "Sahapur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Bausi",
            "panchayats": ["Bausi", "Chakla", "Dhanpur", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Bihat",
            "panchayats": ["Bihat", "Chakra", "Durgapur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Chandan",
            "panchayats": ["Chandan", "Gopalpur", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Dhuraiya",
            "panchayats": ["Dhuraiya", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Katoria",
            "panchayats": ["Katoria", "Rampur", "Chakla", "Maheshpur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Rajauli",
            "panchayats": ["Rajauli", "Chakbhabani", "Rampur", "Durgapur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Shambhuganj",
            "panchayats": ["Shambhuganj", "Rampur", "Chakla", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Sultanganj",
            "panchayats": ["Sultanganj", "Rampur", "Chakbhabani", "Durgapur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Tola",
            "panchayats": ["Tola", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Udwantnagar",
            "panchayats": ["Udwantnagar", "Rampur", "Chakla", "Durgapur", "Maheshpur"]
        },
        

            
        {
            "district_name": "Begusarai",
            "block_name": "Bachhwara",
            "panchayats": ["Bachhwara", "Chowki", "Kachhwa", "Mahamadpur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bakhri",
            "panchayats": ["Bakhri", "Chakla", "Dhanpur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Balia",
            "panchayats": ["Balia", "Chakbhabani", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Barauni",
            "panchayats": ["Barauni", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Begusarai",
            "panchayats": ["Begusarai Sadar", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bhagwanpur",
            "panchayats": ["Bhagwanpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Birpur",
            "panchayats": ["Birpur", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Cheria Bariyarpur",
            "panchayats": ["Cheria Bariyarpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Dandari",
            "panchayats": ["Dandari", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Garhpura",
            "panchayats": ["Garhpura", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Khodawandpur",
            "panchayats": ["Khodawandpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Mansurchak",
            "panchayats": ["Mansurchak", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Matihani",
            "panchayats": ["Matihani", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Naokothi",
            "panchayats": ["Naokothi", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Sahebpur Kamal",
            "panchayats": ["Sahebpur Kamal", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Teghra",
            "panchayats": ["Teghra", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bihat",
            "panchayats": ["Bihat", "Chakla", "Rampur", "Sahpur"]
        },
        

        
        {
            "district_name": "Bhagalpur",
            "block_name": "Bihpur",
            "panchayats": ["Bihpur", "Rampur", "Chakla", "Sundarpur", "Maheshpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Colgong",
            "panchayats": ["Colgong", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Goradih",
            "panchayats": ["Goradih", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Ismailpur",
            "panchayats": ["Ismailpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Jagdishpur",
            "panchayats": ["Jagdishpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Kahalgaon",
            "panchayats": ["Kahalgaon", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Kharik",
            "panchayats": ["Kharik", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Nathnagar",
            "panchayats": ["Nathnagar", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Naugachhia",
            "panchayats": ["Naugachhia", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Pirpainty",
            "panchayats": ["Pirpainty", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Rangra Chowk",
            "panchayats": ["Rangra Chowk", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sabour",
            "panchayats": ["Sabour", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sanhaula",
            "panchayats": ["Sanhaula", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Shahkund",
            "panchayats": ["Shahkund", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sultanganj",
            "panchayats": ["Sultanganj", "Chakla", "Rampur", "Sahpur"]
        },
        
        
        {
            "district_name": "Bhojpur",
            "block_name": "Agiaon",
            "panchayats": ["Agiaon", "Sahpur", "Rampur", "Chakla"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Arrah",
            "panchayats": ["Arrah", "Barhara", "Chakla", "Rampur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Barhara",
            "panchayats": ["Barhara", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Behea",
            "panchayats": ["Behea", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Charpokhari",
            "panchayats": ["Charpokhari", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Garhani",
            "panchayats": ["Garhani", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Jagdishpur",
            "panchayats": ["Jagdishpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Koilwar",
            "panchayats": ["Koilwar", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Piro",
            "panchayats": ["Piro", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Sahar",
            "panchayats": ["Sahar", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Sandesh",
            "panchayats": ["Sandesh", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Shahpur",
            "panchayats": ["Shahpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Tarari",
            "panchayats": ["Tarari", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Udwantnagar",
            "panchayats": ["Udwantnagar", "Rampur", "Chakla", "Sahpur"]
        },
        
        
        {
            "district_name": "Buxar",
            "block_name": "Buxar",
            "panchayats": ["Buxar", "Chaugain", "Parashpur", "Kaharpur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Itarhi",
            "panchayats": ["Itarhi", "Srikhand", "Lohna", "Nagar Panchayat Itarhi"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chausa",
            "panchayats": ["Chausa", "Rajpur", "Mahuli", "Khawaspur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Rajpur",
            "panchayats": ["Rajpur", "Chausa", "Brahmapur", "Kesath"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Dumraon",
            "panchayats": ["Dumraon", "Bharathar", "Chakand", "Rajpur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Nawanagar",
            "panchayats": ["Nawanagar", "Kesath", "Chauki"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Brahampur",
            "panchayats": ["Brahampur", "Simri", "Chakki"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Kesath",
            "panchayats": ["Kesath", "Chakki", "Brahampur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chakki",
            "panchayats": ["Chakki", "Kesath", "Simri"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chougain",
            "panchayats": ["Chougain", "Rajpur", "Buxar"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Simri",
            "panchayats": ["Simri", "Brahampur", "Chakki"]
        },
        
                
        {
            "district_name": "Darbhanga",
            "block_name": "Alinagar",
            "panchayats": ["Alinagar", "Bhuapur", "Chakmiyan", "Mahadevpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Benipur",
            "panchayats": ["Benipur", "Biraul", "Bahadurpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Biraul",
            "panchayats": ["Biraul", "Kalyanpur", "Bheja"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Baheri",
            "panchayats": ["Baheri", "Chandih", "Sarsar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Bahadurpur",
            "panchayats": ["Bahadurpur", "Biraul", "Maheshpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Darbhanga Sadar",
            "panchayats": ["Darbhanga Sadar", "Bachhwara", "Madhopur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Ghanshyampur",
            "panchayats": ["Ghanshyampur", "Chhatauni", "Dhunra"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Hayaghat",
            "panchayats": ["Hayaghat", "Biraul", "Maheshpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Jale",
            "panchayats": ["Jale", "Bhagwanpur", "Chhatauni"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Keotirunway",
            "panchayats": ["Keotirunway", "Muraul", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Kusheshwar Asthan",
            "panchayats": ["Kusheshwar Asthan", "Bahadurpur", "Rajpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Manigachhi",
            "panchayats": ["Manigachhi", "Mahishi", "Chhatauni"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Kiratpur",
            "panchayats": ["Kiratpur", "Chhatauni", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Khutauna",
            "panchayats": ["Khutauna", "Rajnagar", "Tardih"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Muraul",
            "panchayats": ["Muraul", "Singhwara", "Purnahiya"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Purnahiya",
            "panchayats": ["Purnahiya", "Gaurabauram", "Khamhria"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Rajnagar",
            "panchayats": ["Rajnagar", "Shivnagar", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Shivnagar",
            "panchayats": ["Shivnagar", "Tardih", "Wazirganj"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Singhwara",
            "panchayats": ["Singhwara", "Muraul", "Rajnagar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Tardih",
            "panchayats": ["Tardih", "Khutauna", "Shivnagar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Wazirganj",
            "panchayats": ["Wazirganj", "Gaurabauram", "Khamhria"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Gaurabauram",
            "panchayats": ["Gaurabauram", "Khamhria", "Purnahiya"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Khamhria",
            "panchayats": ["Khamhria", "Gaurabauram", "Wazirganj"]
        },
        

                
        {
            "district_name": "Gaya",
            "block_name": "Gaya Sadar",
            "panchayats": ["Gaya Sadar", "Kumahar", "Chandauti", "Barkachha"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Belaganj",
            "panchayats": ["Belaganj", "Araj", "Belsand", "Sariya"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Wazirganj",
            "panchayats": ["Wazirganj", "Madhuban", "Bhurpur", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Manpur",
            "panchayats": ["Manpur", "Kabra", "Chandpura", "Balki"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Bodhgaya",
            "panchayats": ["Bodhgaya", "Gorawan", "Barachatti", "Ratanpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Tekari",
            "panchayats": ["Tekari", "Kharar", "Chakpar", "Barhi"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Konch",
            "panchayats": ["Konch", "Rampur", "Barhampur", "Chhatauni"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Guraru",
            "panchayats": ["Guraru", "Chakbar", "Sikandarpur", "Mohanpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Paraiya",
            "panchayats": ["Paraiya", "Dumariya", "Belsand", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Neemchak Bathani",
            "panchayats": ["Neemchak Bathani", "Sikandarpur", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Khizarsarai",
            "panchayats": ["Khizarsarai", "Chakpar", "Balki"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Atri",
            "panchayats": ["Atri", "Barachatti", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Bathani",
            "panchayats": ["Bathani", "Barachatti", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Mohra",
            "panchayats": ["Mohra", "Rampur", "Guraru"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Sherghati",
            "panchayats": ["Sherghati", "Belsand", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Gurua",
            "panchayats": ["Gurua", "Bodhgaya", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Amas",
            "panchayats": ["Amas", "Sikandarpur", "Chakpar"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Banke Bazar",
            "panchayats": ["Banke Bazar", "Rampur", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Imamganj",
            "panchayats": ["Imamganj", "Belsand", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Dumariya",
            "panchayats": ["Dumariya", "Rampur", "Guraru"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Dobhi",
            "panchayats": ["Dobhi", "Bodhgaya", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Mohanpur",
            "panchayats": ["Mohanpur", "Belsand", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Barachatti",
            "panchayats": ["Barachatti", "Rampur", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Fatehpur",
            "panchayats": ["Fatehpur", "Chakpar", "Gurua"]
        },
        

                
        {
            "district_name": "Gopalganj",
            "block_name": "Gopalganj",
            "panchayats": ["Gopalganj", "Narkatiaganj", "Bairia", "Chapra", "Fatehpur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Thawe",
            "panchayats": ["Thawe", "Parsa", "Bamahi", "Chhaprauli"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Kuchaikote",
            "panchayats": ["Kuchaikote", "Kalyanpur", "Sikati", "Belsand"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Manjha",
            "panchayats": ["Manjha", "Babhnauli", "Rampur", "Chhapra"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Sidhwaliya",
            "panchayats": ["Sidhwaliya", "Belha", "Parmanpur", "Rampur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Hathua",
            "panchayats": ["Hathua", "Bhanpura", "Ramnagar", "Chakpar"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Baikunthpur",
            "panchayats": ["Baikunthpur", "Rampur", "Belsand", "Sikandarpur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Barauli",
            "panchayats": ["Barauli", "Rampur", "Chakpar", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Kateya",
            "panchayats": ["Kateya", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Phulwariya",
            "panchayats": ["Phulwariya", "Rampur", "Chakpar", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Panchdewari",
            "panchayats": ["Panchdewari", "Rampur", "Belsand", "Chakpar"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Uchkagaon",
            "panchayats": ["Uchkagaon", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Vijayipur",
            "panchayats": ["Vijayipur", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Bhorey",
            "panchayats": ["Bhorey", "Rampur", "Belsand", "Chakpar"]
        },
        

        
        {
            "district_name": "Jamui",
            "block_name": "Jamui",
            "panchayats": ["Jamui", "Chakai", "Barhampur", "Dumri", "Sikandra"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Sikandra",
            "panchayats": ["Sikandra", "Bharwaliya", "Khaira", "Chakai", "Sono"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Khaira",
            "panchayats": ["Khaira", "Chakai", "Jamui", "Gidhour"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Chakai",
            "panchayats": ["Chakai", "Khaira", "Jamui", "Barhat"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Sono",
            "panchayats": ["Sono", "Laxmipur", "Jhajha", "Gidhour"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Laxmipur",
            "panchayats": ["Laxmipur", "Barhat", "Jhajha", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Jhajha",
            "panchayats": ["Jhajha", "Barhat", "Gidhour", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Barhat",
            "panchayats": ["Barhat", "Jhajha", "Gidhour", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Gidhour",
            "panchayats": ["Gidhour", "Jhajha", "Barhat", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Islamnagar Aliganj",
            "panchayats": ["Islamnagar Aliganj", "Gidhour", "Barhat", "Jhajha"]
        },
        
        
        {
            "district_name": "Jehanabad",
            "block_name": "Jehanabad",
            "panchayats": ["Jehanabad", "Kachhiyar", "Barkagaon", "Fatuha", "Sukhi"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Makhdumpur",
            "panchayats": ["Makhdumpur", "Daukar", "Gopalpur", "Arajpura"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Ghosi",
            "panchayats": ["Ghosi", "Nawada", "Sukhpura", "Barhampur"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Hulasganj",
            "panchayats": ["Hulasganj", "Barharwa", "Saraiya", "Rampur"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Ratni Faridpur",
            "panchayats": ["Ratni", "Faridpur", "Kamlapur", "Sultanganj"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Modanganj",
            "panchayats": ["Modanganj", "Bhagwanpur", "Bachhwara", "Barai"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Kako",
            "panchayats": ["Kako", "Belwa", "Chakbhabani", "Naugarh"]
        },
        
        
        {
            "district_name": "Kaimur",
            "block_name": "Adhaura",
            "panchayats": ["Adhaura", "Katahariya", "Chakari", "Rampur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Bhabua",
            "panchayats": ["Bhabua", "Kalyanpur", "Gahmar", "Rajpur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Bhagwanpur",
            "panchayats": ["Bhagwanpur", "Chauki", "Chakradharpur", "Sukari"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Chainpur",
            "panchayats": ["Chainpur", "Nautan", "Chakaria", "Belwa"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Chand",
            "panchayats": ["Chand", "Rampur", "Maharajganj", "Sukahi"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Rampur",
            "panchayats": ["Rampur", "Karhi", "Bhagwanpur", "Beldar"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Durgawati",
            "panchayats": ["Durgawati", "Chainpur", "Bhelwara", "Rampur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Kudra",
            "panchayats": ["Kudra", "Patna", "Chakari", "Barauli"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Mohania",
            "panchayats": ["Mohania", "Gamharia", "Rampur", "Barauli"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Nuaon",
            "panchayats": ["Nuaon", "Chak", "Rampur", "Belwa"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Ramgarh",
            "panchayats": ["Ramgarh", "Rampur", "Chakra", "Sukahi"]
        },
        
        
        {
            "district_name": "Katihar",
            "block_name": "Katihar",
            "panchayats": ["Katihar Sadar", "Chhota Gamharia", "Puraini", "Sundarpur", "Balua", "Kharhara", "Rajpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Barsoi",
            "panchayats": ["Barsoi", "Sahibganj", "Bhurkunda", "Baksara", "Jamalpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Manihari",
            "panchayats": ["Manihari", "Sikandarpur", "Gopi Bigha", "Rampur", "Chakuli"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Falka",
            "panchayats": ["Falka", "Bhurkunda", "Dhamdaha", "Beldaur", "Jalalpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Kadwa",
            "panchayats": ["Kadwa", "Chakki", "Rampur", "Sikandarpur", "Mahadeopur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Kursela",
            "panchayats": ["Kursela", "Baksara", "Chhapra", "Belwa", "Gajha"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Hasanganj",
            "panchayats": ["Hasanganj", "Rampur", "Chakuli", "Puraini", "Sikandarpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Sameli",
            "panchayats": ["Sameli", "Chhapra", "Rampur", "Beldaur", "Bhagwanpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Pranpur",
            "panchayats": ["Pranpur", "Rampur", "Chakuli", "Baksara", "Belwa"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Korha",
            "panchayats": ["Korha", "Rampur", "Belwa", "Chakuli", "Sameli"]
        },
        
        
        {
            "district_name": "Khagaria",
            "block_name": "Khagaria",
            "panchayats": ["Khagaria Sadar", "Pachkuli", "Bhagwanpur", "Kothia", "Rampur"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Beldaur",
            "panchayats": ["Beldaur", "Chakparan", "Bariarpur", "Rajpur", "Gopalpur"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Parbatta",
            "panchayats": ["Parbatta", "Barhampur", "Chakua", "Rampur", "Kothi"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Bariyarpur", "Rampur", "Chakuli", "Belwa"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Chautham",
            "panchayats": ["Chautham", "Rampur", "Bhagwanpur", "Baksara", "Belwa"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Mansi",
            "panchayats": ["Mansi", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Gogri",
            "panchayats": ["Gogri", "Rampur", "Chakuli", "Belwa", "Sameli"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Simri Bakhtiyarpur",
            "panchayats": ["Simri Bakhtiyarpur", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        
        
        {
            "district_name": "Kishanganj",
            "block_name": "Kishanganj",
            "panchayats": ["Kishanganj Sadar", "Jagdishpur", "Haripur", "Rampur", "Belwa"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Bahadurganj",
            "panchayats": ["Bahadurganj", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Dighalbank",
            "panchayats": ["Dighalbank", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Thakurganj",
            "panchayats": ["Thakurganj", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Goalpokhar",
            "panchayats": ["Goalpokhar", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Islampur",
            "panchayats": ["Islampur", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        
            
        {
            "district_name": "Lakhisarai",
            "block_name": "Lakhisarai",
            "panchayats": ["Lakhisarai Sadar", "Bhatpur", "Rampur", "Chhatwan", "Nawanagar"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Ramgarh Chowk",
            "panchayats": ["Ramgarh Chowk", "Siyalchak", "Chakbahadur", "Kumhar", "Bhagwanpur"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Surajgarha",
            "panchayats": ["Surajgarha", "Chakmohammad", "Mohanpur", "Rampur", "Ghoramara"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Barahiya",
            "panchayats": ["Barahiya", "Chandan", "Kailashganj", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Chanan",
            "panchayats": ["Chanan", "Rampur", "Chakbahadur", "Siyalchak", "Bhagwanpur"]
        },
        

        {
        
            "district_name": "Madhepura",
            "block_name": "Madhepura",
            "panchayats": ["Madhepura Sadar", "Bhawanipur", "Rampur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Kumargram",
            "panchayats": ["Kumargram", "Chakdah", "Rampur", "Bhawanipur", "Chhatarpur"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Singheshwar",
            "panchayats": ["Singheshwar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Murliganj",
            "panchayats": ["Murliganj", "Rampur", "Chakbahadur", "Bhawanipur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Gopalpur",
            "panchayats": ["Gopalpur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Udaipur",
            "panchayats": ["Udaipur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Alamnagar",
            "panchayats": ["Alamnagar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Shankarpur",
            "panchayats": ["Shankarpur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Madhepura Sadar",
            "panchayats": ["Madhepura Sadar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        
        
        {
            "district_name": "Madhubani",
            "block_name": "Andhratharhi",
            "panchayats": ["Andhratharhi", "Chhota Babhani", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Babubarhi",
            "panchayats": ["Babubarhi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Basopatti",
            "panchayats": ["Basopatti", "Rampur", "Bhawanipur", "Chakbahadur"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Benipatti",
            "panchayats": ["Benipatti", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Bisfi",
            "panchayats": ["Bisfi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Ghoghardiha",
            "panchayats": ["Ghoghardiha", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Harlakhi",
            "panchayats": ["Harlakhi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Jhanjharpur",
            "panchayats": ["Jhanjharpur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Kaluahi",
            "panchayats": ["Kaluahi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Khajauli",
            "panchayats": ["Khajauli", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Ladania",
            "panchayats": ["Ladania", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Laukahi",
            "panchayats": ["Laukahi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Madhepur",
            "panchayats": ["Madhepur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Madhwapur",
            "panchayats": ["Madhwapur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Pandaul",
            "panchayats": ["Pandaul", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Phulparas",
            "panchayats": ["Phulparas", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Rajnagar",
            "panchayats": ["Rajnagar", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Sakri",
            "panchayats": ["Sakri", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Shankarpur",
            "panchayats": ["Shankarpur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Tardih",
            "panchayats": ["Tardih", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Lakhnaur",
            "panchayats": ["Lakhnaur", "Rampur", "Bhawanipur", "Chhata"]
        },
        
                
        {
            "district_name": "Munger",
            "block_name": "Munger Sadar",
            "panchayats": ["Munger Sadar", "Gunjaria", "Jorhat", "Chakmoh"]
        },
        {
            "district_name": "Munger",
            "block_name": "Bariyarpur",
            "panchayats": ["Bariyarpur", "Chakla", "Parsa", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Chandan",
            "panchayats": ["Chandan", "Sikta", "Barauli", "Gajni"]
        },
        {
            "district_name": "Munger",
            "block_name": "Sangrampur",
            "panchayats": ["Sangrampur", "Bhagwanpur", "Chhitauni", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Tarapur",
            "panchayats": ["Tarapur", "Paharpur", "Chakbigha", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Jamalpur",
            "panchayats": ["Jamalpur", "Chakgawan", "Bhawanipur", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Kharagpur",
            "panchayats": ["Kharagpur", "Chakra", "Rampur", "Barauli"]
        },
        {
            "district_name": "Munger",
            "block_name": "Hathidah",
            "panchayats": ["Hathidah", "Chakmoh", "Rampur", "Bhawanipur"]
        },
        

        
        {
            "district_name": "Muzaffarpur",
            "block_name": "Muzaffarpur Sadar",
            "panchayats": ["Muzaffarpur Sadar", "Kohra", "Sahibganj", "Barauli", "Bhagwanpur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Musahari",
            "panchayats": ["Musahari", "Chakna", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Marwan",
            "panchayats": ["Marwan", "Barauli", "Chakla", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Bochahan",
            "panchayats": ["Bochahan", "Bhawanipur", "Chakmoh", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Katra",
            "panchayats": ["Katra", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Saraiya",
            "panchayats": ["Saraiya", "Rampur", "Chakmoh", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Paroo",
            "panchayats": ["Paroo", "Chakra", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Sakra",
            "panchayats": ["Sakra", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Gorhara",
            "panchayats": ["Gorhara", "Rampur", "Bhawanipur", "Chakmoh"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Motipur",
            "panchayats": ["Motipur", "Chakra", "Barauli", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Barahiya",
            "panchayats": ["Barahiya", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Minapur",
            "panchayats": ["Minapur", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Meenapur",
            "panchayats": ["Meenapur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Aurai",
            "panchayats": ["Aurai", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Piprahi",
            "panchayats": ["Piprahi", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        
        
        {
            "district_name": "Nalanda",
            "block_name": "Bihar Sharif",
            "panchayats": ["Bihar Sharif", "Rampur", "Barhampur", "Chakla", "Sultanpur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Rajgir",
            "panchayats": ["Rajgir", "Bhawanipur", "Rampur", "Chakmoh"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Harnaut",
            "panchayats": ["Harnaut", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Islampur",
            "panchayats": ["Islampur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Hilsa",
            "panchayats": ["Hilsa", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Noorsarai",
            "panchayats": ["Noorsarai", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Ekangarsarai",
            "panchayats": ["Ekangarsarai", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Asthawan",
            "panchayats": ["Asthawan", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Katri",
            "panchayats": ["Katri", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Silao",
            "panchayats": ["Silao", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Nalanda Sadar",
            "panchayats": ["Nalanda Sadar", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Nawada",
            "block_name": "Nawada Sadar",
            "panchayats": ["Nawada Sadar", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Akbarpur",
            "panchayats": ["Akbarpur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Narhat",
            "panchayats": ["Narhat", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Pakribarawan",
            "panchayats": ["Pakribarawan", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Hisua",
            "panchayats": ["Hisua", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Warisaliganj",
            "panchayats": ["Warisaliganj", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Kawakol",
            "panchayats": ["Kawakol", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Roh",
            "panchayats": ["Roh", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Rajauli",
            "panchayats": ["Rajauli", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Patna",
            "block_name": "Patna Sadar",
            "panchayats": ["Patna Sadar", "Rampur", "Chakmoh", "Khalilpur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Daniyaw",
            "panchayats": ["Daniyaw", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Bakhtiyarpur",
            "panchayats": ["Bakhtiyarpur", "Rampur", "Chakmoh", "Saraiya"]
        },
        {
            "district_name": "Patna",
            "block_name": "Fatuha",
            "panchayats": ["Fatuha", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Paliganj",
            "panchayats": ["Paliganj", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Danapur",
            "panchayats": ["Danapur", "Rampur", "Chakla", "Kharika"]
        },
        {
            "district_name": "Patna",
            "block_name": "Maner",
            "panchayats": ["Maner", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Naubatpur",
            "panchayats": ["Naubatpur", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Sampatchak",
            "panchayats": ["Sampatchak", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Masaurhi",
            "panchayats": ["Masaurhi", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Khusrupur",
            "panchayats": ["Khusrupur", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Bihta",
            "panchayats": ["Bihta", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Punpun",
            "panchayats": ["Punpun", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Barh",
            "panchayats": ["Barh", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Phulwari",
            "panchayats": ["Phulwari", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Dhanarua",
            "panchayats": ["Dhanarua", "Rampur", "Chakla", "Barauli"]
        },
        
        
        {
            "district_name": "Purnia",
            "block_name": "Purnia Sadar",
            "panchayats": ["Purnia Sadar", "Rampur", "Chakla", "Murliganj", "Banmankhi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Banmankhi",
            "panchayats": ["Banmankhi", "Rampur", "Chakla", "Baisi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Dhamdaha",
            "panchayats": ["Dhamdaha", "Rampur", "Chakla", "Rupauli"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Rupauli",
            "panchayats": ["Rupauli", "Rampur", "Chakla", "Baisi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Baisi",
            "panchayats": ["Baisi", "Rampur", "Chakla", "Banmankhi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Kasba",
            "panchayats": ["Kasba", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Bhawanipur",
            "panchayats": ["Bhawanipur", "Rampur", "Chakla", "Barhara Kothi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Barhara Kothi",
            "panchayats": ["Barhara Kothi", "Rampur", "Chakla", "Sukhasan"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Sukhasan",
            "panchayats": ["Sukhasan", "Rampur", "Chakla", "Amour"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Amour",
            "panchayats": ["Amour", "Rampur", "Chakla", "Krityanand Nagar"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Krityanand Nagar",
            "panchayats": ["Krityanand Nagar", "Rampur", "Chakla", "Jalalgarh"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Jalalgarh",
            "panchayats": ["Jalalgarh", "Rampur", "Chakla", "Bhagalpur"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Bhagalpur",
            "panchayats": ["Bhagalpur", "Rampur", "Chakla", "Purnia City"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Purnia City",
            "panchayats": ["Purnia City", "Rampur", "Chakla", "Purnia Sadar"]
        },
        
        
        {
            "district_name": "Rohtas",
            "block_name": "Rohtas Sadar",
            "panchayats": ["Rohtas Sadar", "Barauli", "Chandpur", "Bikramganj", "Dehri"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Sasaram",
            "panchayats": ["Sasaram", "Kashwan", "Chitbara Gaon", "Karbasawan"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Nokha",
            "panchayats": ["Nokha", "Dumri", "Khirkiya", "Chakia"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Dehri",
            "panchayats": ["Dehri", "Chakai", "Akrua", "Dumari"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Akbarpur",
            "panchayats": ["Akbarpur", "Rajpur", "Chunarughat", "Tilouthu"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Nauhatta",
            "panchayats": ["Nauhatta", "Chakla", "Rajpur", "Dumraon"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Rajpur",
            "panchayats": ["Rajpur", "Tilouthu", "Chand", "Sasaram"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Chenari",
            "panchayats": ["Chenari", "Karbasawan", "Bhabhua", "Chakia"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Tilouthu",
            "panchayats": ["Tilouthu", "Rajpur", "Akbarpur", "Rohtas Sadar"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Dumraon",
            "panchayats": ["Dumraon", "Nokha", "Sasaram", "Chakla"]
        },
        
        
        {
            "district_name": "Saharsa",
            "block_name": "Saharsa Sadar",
            "panchayats": ["Saharsa Sadar", "Bachhwara", "Kothia", "Bajitpur", "Gamhariya"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Mahishi",
            "panchayats": ["Mahishi", "Banwaria", "Barari", "Mahisar"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Simri Bakhtiyarpur",
            "panchayats": ["Simri Bakhtiyarpur", "Nagar", "Parsauni", "Bapudih"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Sonbarsa",
            "panchayats": ["Sonbarsa", "Belha", "Rampur", "Chandwara"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Madhepur",
            "panchayats": ["Madhepur", "Sakra", "Kothia", "Bachhwara"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Pipra",
            "panchayats": ["Pipra", "Kosi", "Bajitpur", "Narayanpur"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Salkhua",
            "panchayats": ["Salkhua", "Rampur", "Chakla", "Bapudih"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Patarghat",
            "panchayats": ["Patarghat", "Belha", "Mahisham", "Rampur"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Alamnagar",
            "panchayats": ["Alamnagar", "Kothia", "Banwaria", "Rampur"]
        },
        
        
        {
            "district_name": "Samastipur",
            "block_name": "Samastipur Sadar",
            "panchayats": ["Samastipur Sadar", "Dighalbank", "Kachharauli", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Ujiarpur",
            "panchayats": ["Ujiarpur", "Barauli", "Bhawanipur", "Chakuli"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Morwa",
            "panchayats": ["Morwa", "Mahishi", "Rampur", "Sakra"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Sarairanjan",
            "panchayats": ["Sarairanjan", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Warisnagar",
            "panchayats": ["Warisnagar", "Barauli", "Maheshpur", "Rampur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Kalyanpur",
            "panchayats": ["Kalyanpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Dalsinghsarai",
            "panchayats": ["Dalsinghsarai", "Barauli", "Rampur", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Patori",
            "panchayats": ["Patori", "Barauli", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Vidyapati Nagar",
            "panchayats": ["Vidyapati Nagar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Tajpur",
            "panchayats": ["Tajpur", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Makhdumpur",
            "panchayats": ["Makhdumpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Musrigharari",
            "panchayats": ["Musrigharari", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Shivajinagar",
            "panchayats": ["Shivajinagar", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Goriakothi",
            "panchayats": ["Goriakothi", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Saran",
            "block_name": "Chapra Sadar",
            "panchayats": ["Chapra Sadar", "Chhapra Bazar", "Rampur", "Belha"]
        },
        {
            "district_name": "Saran",
            "block_name": "Marhaura",
            "panchayats": ["Marhaura", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Dighwara",
            "panchayats": ["Dighwara", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Parsa",
            "panchayats": ["Parsa", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Sonpur",
            "panchayats": ["Sonpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Saran",
            "block_name": "Garkha",
            "panchayats": ["Garkha", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Amnour",
            "panchayats": ["Amnour", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Dariapur",
            "panchayats": ["Dariapur", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Taraiya",
            "panchayats": ["Taraiya", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Manjhi",
            "panchayats": ["Manjhi", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Sonepur",
            "panchayats": ["Sonepur", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Masrakh",
            "panchayats": ["Masrakh", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Parsauni",
            "panchayats": ["Parsauni", "Rampur", "Belha", "Chakla"]
        },
        
        
        {
            "district_name": "Sheikhpura",
            "block_name": "Sheikhpura Sadar",
            "panchayats": ["Sheikhpura Sadar", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Chewara",
            "panchayats": ["Chewara", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Ariari",
            "panchayats": ["Ariari", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Barbigha",
            "panchayats": ["Barbigha", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Pirpainti",
            "panchayats": ["Pirpainti", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Sheikhpura",
            "panchayats": ["Sheikhpura", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Nathnagar",
            "panchayats": ["Nathnagar", "Rampur", "Belha", "Chakla"]
        },
        
        
        {
            "district_name": "Sheohar",
            "block_name": "Sheohar Sadar",
            "panchayats": ["Sheohar Sadar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Purnahiya",
            "panchayats": ["Purnahiya", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Dumri Katsari",
            "panchayats": ["Dumri Katsari", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Piprarhi",
            "panchayats": ["Piprarhi", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Mehsi",
            "panchayats": ["Mehsi", "Chakla", "Rampur", "Belha"]
        },
        
        
        {
            "district_name": "Sitamarhi",
            "block_name": "Sitamarhi Sadar",
            "panchayats": ["Sitamarhi Sadar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Belsand",
            "panchayats": ["Belsand", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bajpatti",
            "panchayats": ["Bajpatti", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Choraut",
            "panchayats": ["Choraut", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bathnaha",
            "panchayats": ["Bathnaha", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Suppi",
            "panchayats": ["Suppi", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Riga",
            "panchayats": ["Riga", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Runnisaidpur",
            "panchayats": ["Runnisaidpur", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Pupri",
            "panchayats": ["Pupri", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Sursand",
            "panchayats": ["Sursand", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bairgania",
            "panchayats": ["Bairgania", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Nanpur",
            "panchayats": ["Nanpur", "Chakla", "Rampur", "Belha"]
        },
        
        
        {
            "district_name": "Siwan",
            "block_name": "Siwan Sadar",
            "panchayats": ["Siwan Sadar", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Barharia",
            "panchayats": ["Barharia", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Bhagwanpur Hat",
            "panchayats": ["Bhagwanpur Hat", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Daraundha",
            "panchayats": ["Daraundha", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Goriakothi",
            "panchayats": ["Goriakothi", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Guthani",
            "panchayats": ["Guthani", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Hussainganj",
            "panchayats": ["Hussainganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Lakri Nabiganj",
            "panchayats": ["Lakri Nabiganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Maharajganj",
            "panchayats": ["Maharajganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Nautan",
            "panchayats": ["Nautan", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Pachrukhi",
            "panchayats": ["Pachrukhi", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Raghunathpur",
            "panchayats": ["Raghunathpur", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Mairwa",
            "panchayats": ["Mairwa", "Chakari", "Rampur", "Maheshpur"]
        },
        
        
        {
            "district_name": "Vaishali",
            "block_name": "Hajipur",
            "panchayats": ["Hajipur", "Chaksikandar", "Bidupur", "Mahua"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Lalganj",
            "panchayats": ["Lalganj", "Saraiya", "Bigha", "Raghunathpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Mahua",
            "panchayats": ["Mahua", "Mahammadpur", "Khesraha", "Sikandarpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Mahnar",
            "panchayats": ["Mahnar", "Barauli", "Chakhandi", "Bharawan"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Patepur",
            "panchayats": ["Patepur", "Chaksikandar", "Gokulpur", "Basantpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Rajapakar",
            "panchayats": ["Rajapakar", "Chakandarpur", "Katauli", "Kanchanpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Bidupur",
            "panchayats": ["Bidupur", "Mahua", "Chaksikandar", "Paterpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Chehrakala",
            "panchayats": ["Chehrakala", "Dighari", "Mahmoodpur", "Barauli"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Desari",
            "panchayats": ["Desari", "Barauli", "Chakandarpur", "Katauli"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Goraul",
            "panchayats": ["Goraul", "Basantpur", "Chaksikandar", "Mahua"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Jandaha",
            "panchayats": ["Jandaha", "Mahnar", "Barauli", "Chakhandi"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Sahdei Buzurg",
            "panchayats": ["Sahdei Buzurg", "Chaksikandar", "Mahammadpur", "Raghunathpur"]
        },
        
                
        {
            "district_name": "Forbesganj",
            "block_name": "Forbesganj",
            "panchayats": ["Forbesganj", "Araria Basti", "Bahgi Pokharia", "Belbari Araria Basti", "Bansbari Bansbari", "Barakamatchistipur Haria"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Araria",
            "panchayats": ["Araria Basti", "Azamnagar Kusiyar Gawon", "Azmatpur Basantpur", "Bahgi Pokharia", "Bairgachhi Belwa"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Bhargama",
            "panchayats": ["Bhargama", "Bairgachhi", "Bangawan", "Belsandi", "Belwa"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Raniganj",
            "panchayats": ["Raniganj", "Chakorwa", "Dahrahra", "Damiya", "Dargahiganj"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Palasi",
            "panchayats": ["Palasi", "Fatehpur", "Gadhgawan", "Gandhi", "Gangauli"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Sikti",
            "panchayats": ["Sikti", "Ganj", "Gogri", "Gopalpur", "Baturbari"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Jokihat",
            "panchayats": ["Jokihat", "Bhadwar", "Bhairoganj", "Bhawanipur", "Bhanghi"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Kursakatta",
            "panchayats": ["Kursakatta", "Dombana", "Dumari", "Fatehpur", "Gadhgawan"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Narpatganj",
            "panchayats": ["Narpatganj", "Nabinagar", "Obra", "Rafiganj", "Haspura"]
        }
        
        

        
        
        
        
                      # ... add all remaining districts & blocks
    ]


    jharkhand_locations = [
        {
            "district_name": "Bokaro",
            "block_name": "Bermo",
            "panchayats": ["Bermo", "Tetulmari", "Barmasia", "Jaridih", "Karo"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chas",
            "panchayats": ["Chas", "Chandrapura", "Bandhgora", "Bermo", "Tetulmari"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chandankiyari",
            "panchayats": ["Chandankiyari", "Kundri", "Jhalda", "Panchbaria", "Nawadih"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chandrapura",
            "panchayats": ["Chandrapura", "Gomia", "Bermo", "Chas", "Tetulmari"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Gomia",
            "panchayats": ["Gomia", "Chandrapura", "Bermo", "Kasmar", "Nawadih"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Jaridih",
            "panchayats": ["Jaridih", "Bermo", "Chas", "Tetulmari", "Barmasia"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Kasmar",
            "panchayats": ["Kasmar", "Gomia", "Chandankiyari", "Bermo", "Petarwar"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Nawadih",
            "panchayats": ["Nawadih", "Chandankiyari", "Gomia", "Kasmar", "Bermo"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Petarwar",
            "panchayats": ["Petarwar", "Kasmar", "Gomia", "Nawadih", "Chandankiyari"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Chatra",
            "panchayats": ["Chatra", "Chhatarpur", "Bhaupur", "Patratu", "Bhaluadih"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Hunterganj",
            "panchayats": ["Hunterganj", "Dhauraiya", "Pipra", "Chandwa", "Kalyanpur"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Itkhori",
            "panchayats": ["Itkhori", "Kundru", "Lohardaga", "Bagodar", "Sadar Itkhori"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Kunda",
            "panchayats": ["Kunda", "Chirgaon", "Bhelwadih", "Kundru", "Barachatti"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Lawalong",
            "panchayats": ["Lawalong", "Birsanagar", "Chakradih", "Barauli", "Simaria"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Mayurhand",
            "panchayats": ["Mayurhand", "Ratanpur", "Pipra", "Sundarpur", "Harhar"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Pathalgora",
            "panchayats": ["Pathalgora", "Sadar Pathalgora", "Kumradih", "Kumra", "Badiya"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Pratappur",
            "panchayats": ["Pratappur", "Mugma", "Bokaro", "Sadar Pratappur", "Chhota Pratappur"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Simaria",
            "panchayats": ["Simaria", "Bara Simaria", "Chhota Simaria", "Bagha", "Paharpur"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Tandwa",
            "panchayats": ["Tandwa", "Chhota Tandwa", "Bara Tandwa", "Kumardih", "Bari Tandwa"]
        },
        
        
        {
            "district_name": "Deoghar",
            "block_name": "Deoghar",
            "panchayats": ["Deoghar Sadar", "Bardih", "Bangaon", "Barhara", "Kundahit", "Bagodar"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Devipur",
            "panchayats": ["Devipur", "Kushma", "Kheria", "Bara Devipur", "Chhota Devipur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Madhupur",
            "panchayats": ["Madhupur Sadar", "Sakri", "Radhanagar", "Chhota Madhupur", "Bara Madhupur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Mohanpur",
            "panchayats": ["Mohanpur", "Bara Mohanpur", "Chhota Mohanpur", "Tilhar", "Paharpur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Palojori",
            "panchayats": ["Palojori", "Bara Palojori", "Chhota Palojori", "Rampur", "Bhurkunda"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Sarath",
            "panchayats": ["Sarath", "Bara Sarath", "Chhota Sarath", "Bagodar", "Rasikpur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Sonaraithari",
            "panchayats": ["Sonaraithari", "Bara Sonaraithari", "Chhota Sonaraithari", "Rampur", "Chakla"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Margomunda",
            "panchayats": ["Margomunda", "Bara Margomunda", "Chhota Margomunda", "Paharpur", "Sundarpur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Karon",
            "panchayats": ["Karon", "Bara Karon", "Chhota Karon", "Rampur", "Baghar"]
        },
        
       
    

        {
            "district_name": "Dumka",
            "block_name": "Dumka",
            "panchayats": ["Dumka Sadar", "Sanjhariya", "Ramnagar", "Chopadih", "Bhaluadih"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Jarmundi",
            "panchayats": ["Jarmundi", "Tilma", "Chilla", "Karmatanr", "Saraiya"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Jama",
            "panchayats": ["Jama", "Barahat", "Nandni", "Sahibganj", "Bishunpur"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Kathikund",
            "panchayats": ["Kathikund", "Rampur", "Karia", "Chandrapur", "Sundarpur"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Masalia",
            "panchayats": ["Masalia", "Bara Masalia", "Chhota Masalia", "Ramnagar", "Baghar"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Ramgarh",
            "panchayats": ["Ramgarh", "Bara Ramgarh", "Chhota Ramgarh", "Chopadih", "Saraiya"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Ranishwar",
            "panchayats": ["Ranishwar", "Bara Ranishwar", "Chhota Ranishwar", "Rampur", "Bhaluadih"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Saraiyahat",
            "panchayats": ["Saraiyahat", "Bara Saraiyahat", "Chhota Saraiyahat", "Ramnagar", "Baghar"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Shikaripara",
            "panchayats": ["Shikaripara", "Bara Shikaripara", "Chhota Shikaripara", "Rampur", "Chopadih"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Gopikandar",
            "panchayats": ["Gopikandar", "Bara Gopikandar", "Chhota Gopikandar", "Ramnagar", "Baghar"]
        },
        
        {
            "district_name": "East Singhbhum",
            "block_name": "Baharagora",
            "panchayats": ["Baharagora Sadar", "Barabazar", "Chandpur", "Patratu", "Bhaupur"]
        },
        {
            "district_name": "East Singhbhum",
            "block_name": "Chakulia",
            "panchayats": ["Chakulia", "Kumardubi", "Hiramunda", "Barakar", "Jamshedpur"]
        },
        {
            "district_name": "East Singhbhum",
            "block_name": "Dhalbhumgarh",
            "panchayats": ["Dhalbhumgarh", "Barabazar", "Gopinathpur", "Rampur", "Baghar"]
        },
        {
            "district_name": "East Singhbhum",
            "block_name": "Dumaria",
            "panchayats": ["Dumaria", "Bara Dumaria", "Chhota Dumaria", "Rampur", "Baghar"]
        },
        {
            "district_name": "East Singhbhum",
            "block_name": "Ghatshila",
            "panchayats": ["Ghatshila", "Bara Ghatshila", "Chhota Ghatshila", "Rampur", "Baghar"]
        },
        {
            "district_name": "East Singhbhum",
            "block_name": "Golmuri-cum-Jugsalai",
            "panchayats": ["Golmuri", "Jugsalai", "Bari Golmuri", "Chhota Jugsalai", "Rampur"]
        },
        {
            "district_name": "East Singhbhum",
            "block_name": "Musabani",
            "panchayats": ["Musabani", "Bara Musabani", "Chhota Musabani", "Rampur", "Baghar"]
        },
        {
            "district_name": "East Singhbhum",
            "block_name": "Patamda",
            "panchayats": ["Patamda", "Bara Patamda", "Chhota Patamda", "Rampur", "Baghar"]
        },
        {
            "district_name": "East Singhbhum",
            "block_name": "Potka",
            "panchayats": ["Potka", "Bara Potka", "Chhota Potka", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Bhandaria",
            "panchayats": ["Bhandaria Sadar", "Bara Bhandaria", "Chhota Bhandaria", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Bishunpura",
            "panchayats": ["Bishunpura Sadar", "Bara Bishunpura", "Chhota Bishunpura", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Bhawnathpur",
            "panchayats": ["Bhawnathpur Sadar", "Bara Bhawnathpur", "Chhota Bhawnathpur", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Danda",
            "panchayats": ["Danda Sadar", "Bara Danda", "Chhota Danda", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Dhurki",
            "panchayats": ["Dhurki Sadar", "Bara Dhurki", "Chhota Dhurki", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Garhwa",
            "panchayats": ["Garhwa Sadar", "Bara Garhwa", "Chhota Garhwa", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Ketar",
            "panchayats": ["Ketar Sadar", "Bara Ketar", "Chhota Ketar", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Kandi",
            "panchayats": ["Kandi Sadar", "Bara Kandi", "Chhota Kandi", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Majhiaon",
            "panchayats": ["Majhiaon Sadar", "Bara Majhiaon", "Chhota Majhiaon", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Meral",
            "panchayats": ["Meral Sadar", "Bara Meral", "Chhota Meral", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Nagar Untari",
            "panchayats": ["Nagar Untari Sadar", "Bara Nagar Untari", "Chhota Nagar Untari", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Ramkanda",
            "panchayats": ["Ramkanda Sadar", "Bara Ramkanda", "Chhota Ramkanda", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Ranka",
            "panchayats": ["Ranka Sadar", "Bara Ranka", "Chhota Ranka", "Rampur", "Baghar"]
        },
        {
            "district_name": "Garhwa",
            "block_name": "Sagma",
            "panchayats": ["Sagma Sadar", "Bara Sagma", "Chhota Sagma", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Bagodar",
            "panchayats": ["Bagodar Sadar", "Bara Bagodar", "Chhota Bagodar", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Bengabad",
            "panchayats": ["Bengabad Sadar", "Bara Bengabad", "Chhota Bengabad", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Birni",
            "panchayats": ["Birni Sadar", "Bara Birni", "Chhota Birni", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Deori",
            "panchayats": ["Deori Sadar", "Bara Deori", "Chhota Deori", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Dhanwar",
            "panchayats": ["Dhanwar Sadar", "Bara Dhanwar", "Chhota Dhanwar", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Dumri",
            "panchayats": ["Dumri Sadar", "Bara Dumri", "Chhota Dumri", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Gandey",
            "panchayats": ["Gandey Sadar", "Bara Gandey", "Chhota Gandey", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Giridih",
            "panchayats": ["Giridih Sadar", "Bara Giridih", "Chhota Giridih", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Jamua",
            "panchayats": ["Jamua Sadar", "Bara Jamua", "Chhota Jamua", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Pirtand",
            "panchayats": ["Pirtand Sadar", "Bara Pirtand", "Chhota Pirtand", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Sariya",
            "panchayats": ["Sariya Sadar", "Bara Sariya", "Chhota Sariya", "Rampur", "Baghar"]
        },
        {
            "district_name": "Giridih",
            "block_name": "Tisri",
            "panchayats": ["Tisri Sadar", "Bara Tisri", "Chhota Tisri", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Bashant Rai",
            "panchayats": ["Bashant Rai Sadar", "Bara Bashant Rai", "Chhota Bashant Rai", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Boarijor",
            "panchayats": ["Boarijor Sadar", "Bara Boarijor", "Chhota Boarijor", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Godda",
            "panchayats": ["Godda Sadar", "Bara Godda", "Chhota Godda", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Mahagama",
            "panchayats": ["Mahagama Sadar", "Bara Mahagama", "Chhota Mahagama", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Meherma",
            "panchayats": ["Meherma Sadar", "Bara Meherma", "Chhota Meherma", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Pathargama",
            "panchayats": ["Pathargama Sadar", "Bara Pathargama", "Chhota Pathargama", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Poraiyahat",
            "panchayats": ["Poraiyahat Sadar", "Bara Poraiyahat", "Chhota Poraiyahat", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Sunderpahari",
            "panchayats": ["Sunderpahari Sadar", "Bara Sunderpahari", "Chhota Sunderpahari", "Rampur", "Baghar"]
        },
        {
            "district_name": "Godda",
            "block_name": "Thakurgangti",
            "panchayats": ["Thakurgangti Sadar", "Bara Thakurgangti", "Chhota Thakurgangti", "Rampur", "Baghar"]
        },
        {
        "district_name": "Gumla",
        "block_name": "Albert Ekka",
        "panchayats": ["Govindpur", "Jarda", "Meral", "Sikari", "Sisi Karamtoli"]
        },
        {
        "district_name": "Gumla",
        "block_name": "Bishunpur",
        "panchayats": ["Amtipani", "Banari", "Bishunpur", "Chirodih", "Gautam Nagar", "Joriya", "Kilmila", "Koenjra", "Mahur", "Nawatoli"]
        },
        {
        "district_name": "Gumla",
        "block_name": "Chainpur",
        "panchayats": ["Bamda", "Bardih", "Barwenagar", "Bendora", "Chainpur", "Chhichhwani", "Janawal", "Kating", "Malam", "Rampur"]
        },
        {
        "district_name": "Gumla",
        "block_name": "Dumri",
        "panchayats": ["Aakasi", "Bhikhampur", "Jairagi", "Jurmu", "Karni", "Khetli", "Majhgaon", "Nawadih", "Udni"]
        },
        {
        "district_name": "Gumla",
        "block_name": "Ghaghra",
        "panchayats": ["Adar", "Arangi", "Badri", "Belagara", "Bimarla", "Chapka", "Chundari", "Dewaki", "Dirgaon", "Duko", "Ghaghra", "Kugaon", "Kuhipath", "Nawdiha", "Ruki", "Sarango", "Sehal", "Shivrajpur"]
        },
        {
        "district_name": "Gumla",
        "block_name": "Gumla",
        "panchayats": ["Anjan", "Amboa", "Armai", "Asni", "Basua", "Brinda", "Dumerdih", "Fasia", "Fori", "Ghatgaon", "Kaliga", "Karaundi", "Kaseera", "Katri", "Kharka", "Khora", "Kotam", "Kulabira", "Kumharia", "Murkunda", "Nawadih", "Puggu", "Silafari", "Telgaon", "Toto"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Barkagaon",
        "panchayats": ["Barkagaon", "Bendi", "Bhadwar", "Bhelwatand", "Birchand", "Chorhat", "Danua", "Gaidu", "Hesatu", "Joral", "Kakora", "Keredari East", "Keredari West", "Kesaria", "Kharika", "Khedia", "Kupgawan", "Manatu", "Pandu", "Qadam", "Rajrappa", "Urimari"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Bishnugarh",
        "panchayats": ["Bansalong", "Barkitanr", "Bekobar", "Bisariya", "Bishnugarh", "Bishunpur", "Chikni", "Chokahatu", "Dharampur", "Gadokhar", "Jaridih", "Jhari", "Kandul", "Karmali", "Kharika", "Khilan", "Kusumbha", "Lathiya", "Masaria", "Murgadih", "Narkopi", "Pardheya", "Pipra", "Sampathua"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Churchu",
        "panchayats": ["Alauna", "Bundu", "Chundri", "Churchu", "Harsinghpur", "Laducha", "Ratia", "Tandwa"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Daru",
        "panchayats": ["Amrampur", "Barahi", "Bariatu", "Bariyath", "Bhelwatanr", "Daru", "Imel", "Kadma", "Khelari"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Hazaribagh",
        "panchayats": ["Bahera", "Bankheta", "Bariyath", "Barora", "Bhaipur", "Chano", "Chaura", "Daparkha", "Gerhwa", "Guniyadih", "Hazaribagh", "Indrapuri", "Jatka", "Krishnapur", "Lalotand", "Masipirhi", "Morangi", "Okni", "Pabra", "Pelawal", "Pimpalgaon", "Pithoriya", "Purnadih", "Sadar", "Silwar"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Ichak",
        "panchayats": ["Amjhar", "Bahera", "Bansba", "Barh", "Barwa", "Basaria", "Bherwadih", "Bijurka", "Bikrampur", "Chainpur", "Chitkari", "Ichak", "Jaradhi", "Kundru", "Kurumba", "Makraso", "Palhe", "Sariya", "Sindur", "Tandwa"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Katkamsandi",
        "panchayats": ["Amari", "Aswa", "Baghmani", "Bangrakala", "Barh", "Chainpur", "Chhota Bhakur", "Deori", "Durgapur", "Kakari", "Katkamsandi", "Logka", "Madhuban", "Mahuadanr", "Ramgarh", "Singi"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Katkamdag",
        "panchayats": ["Aswa", "Barkakana", "Barora", "Barwadih", "Bichna", "Chandwar", "Chiapara", "Dumardaha", "Jarwa", "Katkamdag", "Kharkhari", "Masratu", "Sindi"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Keredari",
        "panchayats": ["Adina", "Bhanwar", "Chakuliya", "Chandwara", "Charhi", "Dondla", "Jari", "Keredari", "Khapia", "Kutmu", "Manatu", "Masaratu", "Nichi", "Patrahatu", "Salaiya", "Sambhupur"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Chauparan",
        "panchayats": ["Amba", "Bhunwa", "Chainpur", "Chauparan", "Dadhi", "Dumri", "Fatehpur", "Jamu", "Kandwa", "Karminiya", "Karma", "Keral", "Kherwa", "Kukurha", "Kumhari", "Lakhisarai", "Latra", "Mahuar", "Mangura", "Pandu", "Patra", "Pratappur", "Salaiya", "Shivnagar", "Siyana", "Tandwa", "Udent"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Padma",
        "panchayats": ["Bakaspura", "Barga", "Chano", "Chirka", "Kadma", "Khalari", "Padma", "Patra"]
        },
        {
        "district_name": "Hazaribagh",
        "block_name": "Tati Jhariya",
        "panchayats": ["Aalhe", "Baliganj", "Baraand", "Batam", "Dumar", "Kariasol", "Tati Jhariya", "Tatijharia"]
        },
        {
        "district_name": "Jamtara",
        "block_name": "Jamtara",
        "panchayats": ["Barjora", "Bewa", "Chalna", "Chandradipa", "Chengaidh", "Dakhinbahal", "Duladi", "Garainala", "Gobindpur", "Jamuniabad", "Jargudi", "Kaladabar", "Karmatanr", "Lokdi", "Pipla", "Rajpur", "Saharpur", "Sekraydi"]
        },
        {
        "district_name": "Jamtara",
        "block_name": "Kundhit",
        "panchayats": ["Amba", "Aunha", "Baghmara", "Basdiha", "Bongari", "Chakdih", "Chandrapara", "Dularpur", "Guria", "Harati", "Jalbari", "Karma", "Kundhit", "Majhgaon", "Nala", "Pathardih", "Rampur", "Tati"]
        },
        {
        "district_name": "Jamtara",
        "block_name": "Nala",
        "panchayats": ["Afjalpur", "Bandardiha", "Bara Rampur", "Chaknayapara", "Dalbar", "Dhobna", "Jain Basna", "Kantur", "Kukru", "Nala", "Narayanpur", "Pakuria", "Panjunia", "Roopdih", "Tesjoriya"]
        },
        {
        "district_name": "Jamtara",
        "block_name": "Narayanpur",
        "panchayats": ["Bandarchuan", "Bankudih", "Bidwa", "Borwa", "Budhudi", "Butberiya", "Chadadhi Lakhanpur", "Chakwa", "Daltengan", "Jarmundi", "Mahurkela", "Narkopi", "Narayanpur", "Narodih", "Pabiya", "Posta", "Sahepur"]
        },
        {
        "district_name": "Jamtara",
        "block_name": "Fatehpur",
        "panchayats": ["Agaiyasarmundi", "Asanberia", "Bamandiha", "Bandarnacha", "Banudih", "Bindapathar", "Chapuriya", "Dumariya", "Jorbhitha", "Masaria", "Pipla", "Supaidi"]
        },
        {
        "district_name": "Jamtara",
        "block_name": "Karmatanr",
        "panchayats": ["Alagchuan", "Bagber", "Baradaha", "Barmundi", "Birajpur", "Dumariya", "Karmatarnr"]
        },
        {
        "district_name": "Khunti",
        "block_name": "Khunti",
        "panchayats": ["Bhandra", "Bichna", "Chikor", "Ganeor", "Govindpur", "Hesel", "Jilinga", "Kamu", "Karra", "Khunti", "Maranghada", "Tiril"]
        },
        {
        "district_name": "Khunti",
        "block_name": "Murhu",
        "panchayats": ["Amreya", "Banki", "Barudih", "Dadi", "Hesadih", "Hesapiri", "Karra", "Kheran", "Kuda", "Manda", "Murhu", "Nawadih", "Oina", "Purnadih", "Reladih", "Serengdih"]
        },
        {
        "district_name": "Khunti",
        "block_name": "Rania",
        "panchayats": ["Barka", "Bendora", "Chikor", "Darang", "Gobindpur", "Kanya", "Kotbera"]
        },
        {
        "district_name": "Khunti",
        "block_name": "Torpa",
        "panchayats": ["Baruhatu", "Bendon", "Bistumpur", "Gaidghat", "Hurhuru", "Japud", "Koru", "Kundang", "Kurunga", "Kutchuru", "Lota", "Lotwa", "Naditoli", "Sarwakala", "Tontang", "Torpa"]
        },
        {
        "district_name": "Khunti",
        "block_name": "Erki",
        "panchayats": ["Amru", "Bolli", "Dawatoli", "Dumargarha", "Erki", "Gobindpur", "Iragutu", "Kullu", "Kupgu", "Lang", "Leru", "Lohardaga", "Mungu", "Nawadih", "Sarwa", "Sobo"]
        },
        {
        "district_name": "Khunti",
        "block_name": "Karra",
        "panchayats": ["Barwadih", "Birbanki", "Buchangutu", "Chelgi", "Chichdih", "Doko", "Hesadih", "Hesal", "Jaltanga", "Karra", "Kedikidih", "Lodhma", "Midda", "Mogda", "Palak", "Purnadih", "Reladih", "Simra", "Teshobera"]
        },
        {
        "district_name": "Koderma",
        "block_name": "Chandwara",
        "panchayats": ["Aragaro", "Badkidhamrai", "Birsodih", "Chandwara East", "Chandwara West"]
        },
        {
        "district_name": "Koderma",
        "block_name": "Domchanch",
        "panchayats": ["Bachhedih", "Dhargawan", "Dhodhakola", "Koldiha"]
        },
        {
        "district_name": "Koderma",
        "block_name": "Jainagar",
        "panchayats": ["Bhaidih", "Chhatra", "Dumardih", "Govie", "Jainagar"]
        },
        {
        "district_name": "Koderma",
        "block_name": "Koderma",
        "panchayats": ["Bekobar North", "Bekobar South", "Charadih", "Dumardiha"]
        },
        {
        "district_name": "Koderma",
        "block_name": "Markacho",
        "panchayats": ["Baradih", "Chakardih", "Dupadih", "Gamharia", "Markacho"]
        },
        {
        "district_name": "Koderma",
        "block_name": "Satgawan",
        "panchayats": ["Bagodar", "Chowka", "Dumar", "Gamharia", "Satgawan"]
        },
        {
        "district_name": "Latehar",
        "block_name": "Balumath",
        "panchayats": ["Adharmunda", "Amma", "Basariya", "Balumath", "Bhojudih", "Dhurhi", "Hudedih", "Kansa", "Lohandih", "Patratu", "Sowdih"]
        },
        {
        "district_name": "Latehar",
        "block_name": "Barwadih",
        "panchayats": ["Akti", "Asawa", "Barwadih", "Barwadih West", "Bhaderiya", "Chandwa", "Durgapur", "Jalhana", "Kachhwa", "Mahuwadih", "Rampur"]
        },
        {
        "district_name": "Latehar",
        "block_name": "Chandwa",
        "panchayats": ["Arcanga", "Belsara", "Chandwa", "Danda", "Dari", "Hesla", "Kamdha", "Kumsipathar", "Lakma", "Rampur", "Sirdih"]
        },
        {
        "district_name": "Latehar",
        "block_name": "Garu",
        "panchayats": ["Barwadih", "Dimra", "Garu", "Jamuni", "Karkata", "Khamam", "Sirmot"]
        },
        {
        "district_name": "Latehar",
        "block_name": "Herhanj",
        "panchayats": ["Basanwa", "Herhanj", "Kulberya", "Pahariya", "Pipra"]
        },
        {
        "district_name": "Latehar",
        "block_name": "Latehar",
        "panchayats": ["Amma", "Balumath", "Chandu", "Hawadih", "Jogidih", "Latehar Sadar", "Maduadih", "Rampur"]
        },
        {
        "district_name": "Latehar",
        "block_name": "Mahuadanr",
        "panchayats": ["Ashakol", "Bardia", "Baridih", "Damodarpur", "Dinabandh", "Garia", "Jhumri", "Mahuwadih", "Rampur"]
        },
        {
        "district_name": "Latehar",
        "block_name": "Manika",
        "panchayats": ["Bamamadih", "Bhaderiya", "Bhatgaon", "Chhotoam","Haludih","Jamkunda","Kanudih","Manika","Patratu"]
        },
        {
        "district_name": "Lohardaga",
        "block_name": "Bhandra",
        "panchayats": ["Gram Panchayat 1", "Gram Panchayat 2", "Gram Panchayat 3", "Gram Panchayat 4", "Gram Panchayat 5", "Gram Panchayat 6", "Gram Panchayat 7", "Gram Panchayat 8", "Gram Panchayat 9"]
        },
        {
        "district_name": "Lohardaga",
        "block_name": "Kisko",
        "panchayats": ["Gram Panchayat 1", "Gram Panchayat 2", "Gram Panchayat 3", "Gram Panchayat 4", "Gram Panchayat 5", "Gram Panchayat 6", "Gram Panchayat 7", "Gram Panchayat 8", "Gram Panchayat 9"]
        },
        {
        "district_name": "Lohardaga",
        "block_name": "Kuru",
        "panchayats": ["Gram Panchayat 1", "Gram Panchayat 2", "Gram Panchayat 3", "Gram Panchayat 4", "Gram Panchayat 5", "Gram Panchayat 6", "Gram Panchayat 7", "Gram Panchayat 8", "Gram Panchayat 9", "Gram Panchayat 10", "Gram Panchayat 11", "Gram Panchayat 12", "Gram Panchayat 13", "Gram Panchayat 14"]
        },
        {
        "district_name": "Lohardaga",
        "block_name": "Lohardaga",
        "panchayats": ["Gram Panchayat 1", "Gram Panchayat 2", "Gram Panchayat 3", "Gram Panchayat 4", "Gram Panchayat 5", "Gram Panchayat 6", "Gram Panchayat 7", "Gram Panchayat 8", "Gram Panchayat 9", "Gram Panchayat 10", "Gram Panchayat 11", "Gram Panchayat 12"]
        },
        {
        "district_name": "Lohardaga",
        "block_name": "Peshrar",
        "panchayats": ["Gram Panchayat 1", "Gram Panchayat 2", "Gram Panchayat 3", "Gram Panchayat 4", "Gram Panchayat 5"]
        },
        {
        "district_name": "Lohardaga",
        "block_name": "Senha",
        "panchayats": ["Gram Panchayat 1", "Gram Panchayat 2", "Gram Panchayat 3", "Gram Panchayat 4", "Gram Panchayat 5", "Gram Panchayat 6", "Gram Panchayat 7", "Gram Panchayat 8", "Gram Panchayat 9", "Gram Panchayat 10", "Gram Panchayat 11"]
        },
        {
        "district_name": "Pakur",
        "block_name": "Amrapara",
        "panchayats": ["Alubeda", "Baluadih", "Gurdarag", "Jharapara", "Kumarpur", "Masidih", "Pukrim", "Sikindih", "Tandih", "Tamang"]
        },
        {
        "district_name": "Pakur",
        "block_name": "Hiranpur",
        "panchayats": ["Baidih", "Bhagalchak", "Charwa", "Hiranpur", "Hirapur", "Ichak", "Paharpur", "Palgada", "Pipradih", "Rampur"]
        },
        {
        "district_name": "Pakur",
        "block_name": "Littipara",
        "panchayats": ["Balaidih", "Chakdih", "Domra", "Gudha", "Halidih", "Jhari", "Kaphan Diha", "Mahuwadih", "Morwa", "Pachowka"]
        },
        {
        "district_name": "Pakur",
        "block_name": "Maheshpur",
        "panchayats": ["Badanoo", "Banabira", "Chilchila", "Dumardih", "Hesretand", "Jhunjhunia", "Maheshpur", "Parasi", "Sundari"]
        },
        {
        "district_name": "Pakur",
        "block_name": "Pakur",
        "panchayats": ["Ambabadih", "Bansbera", "Guaidih", "Kamisma", "Kharwan", "Pakur", "Pakuria", "Rampur Daltonganj"]
        },
        {
        "district_name": "Pakur",
        "block_name": "Pakuria",
        "panchayats": ["Baharpur", "Bengabari", "Dainkat", "Dumsara", "Kantapahari", "Pakuria"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Bishrampur",
        "panchayats": ["Babhani", "Banai", "Chandwa", "Dumar", "Kariyabahal", "Khapari", "Lohra", "Manatu", "Pandwa", "Sarchar", "Sundri"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Chhatarpur",
        "panchayats": ["Amarpur", "Bahera", "Chhatarpur - I", "Chhatarpur - II", "Dandesahi", "Dari", "Jalpura", "Kesaria", "Kundru", "Makwar"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Chhatarpur-II",
        "panchayats": ["Amarpur", "Bahera", "Chhatarpur - II", "Kesari", "Kundru", "Makwar"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Chainpur",
        "panchayats": ["Belsara", "Bhatoli", "Chainpur", "Dulmi", "Jarmundi", "Khori", "Mandanpur", "Pasrighat"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Hussainabad",
        "panchayats": ["Amka", "Bairiya", "Barkajori", "Chhotetara", "Daltonganj", "Hussainabad", "Kundhit", "Patratu"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Lesliganj",
        "panchayats": ["Baghmara", "Balarampur", "Bunari", "Charwatand", "Doladih", "Kharhara", "Seori", "Sikraur"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Manatu",
        "panchayats": ["Burmu", "Chechra", "Curmi", "Hesli", "Kanchi", "Lodhra", "Manatu", "Nokha", "Sodmi"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Medininagar",
        "panchayats": ["Belsara", "Garhua", "Gaura", "Hesal", "Jamua", "Kund", "Lohra", "Medininagar", "Nawadih"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Mohammadganj",
        "panchayats": ["Badkaga", "Baruindih", "Chand", "Daltonganj", "Kharari", "Mohammadganj", "Rampur"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Nawagarh",
        "panchayats": ["Ahdagi", "Barkhatu", "Hesela", "Jamtoli", "Nawagarh", "Tati"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Pandu",
        "panchayats": ["Dumariya", "Kandaha", "Lohra", "Pandu", "Patra", "Pipra"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Patan",
        "panchayats": ["Amthua", "Bahura", "Chowka", "Kamaru", "Lohra", "Patan"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Panki",
        "panchayats": ["Bhadri", "Daltonganj North", "Daltonganj South", "Lohra", "Panki"]
        },
        {
        "district_name": "Palamu",
        "block_name": "Satbarwa",
        "panchayats": ["Badabra", "Bagra", "Kandar", "Lohra", "Satbarwa"]
        },
        {
        "district_name": "Ramgarh",
        "block_name": "Chitarpur",
        "panchayats": ["Barkipona", "Bhuchungdih", "Borobing", "Chitarpur East", "Chitarpur North", "Chitarpur South", "Chitarpur West", "Larikalan", "Marang Marcha", "Mayal", "Sewai North", "Sewai South", "Sukrigarha"]
        },
        {
        "district_name": "Ramgarh",
        "block_name": "Dulmi",
        "panchayats": ["Dulmi", "Honhe", "Ichatu", "Jamira", "Kulhi", "Patamdaga", "Sikni", "Siru", "Soso", "Usra"]
        },
        {
        "district_name": "Ramgarh",
        "block_name": "Gola",
        "panchayats": ["Banda", "Bariatu", "Barlanga", "Betulkala", "Chadi", "Bariatu Chokad", "Goal", "Hesapoda", "Huppu", "Korambe", "Kumhardaga", "Maganpur", "Nawadih", "Purabdih", "Rakua", "Sadam", "Sangrampur", "Saragdih", "Sosokalan", "Sutri", "Uparbarga"]
        },
        {
        "district_name": "Ramgarh",
        "block_name": "Mandu",
        "panchayats": ["Ara North", "Ara South", "Badgaon", "Barka Chumba", "Barughutu East", "Barughutu Middle", "Barughutu North", "Barughutu West", "Basantpur", "Bumri", "Chhotidundi", "Hesagarha", "Ichakdih", "Karma North", "Karma South", "Kedla Middle", "Kedla North", "Kedla South", "Kimo", "Kuju East", "Kuju South", "Kuju West", "Laiyo North", "Laiyo South", "Manduchati", "Mandudih", "Manjhla Chumba", "Nawadih", "Orla", "Pindra", "Pundi", "Ratwe", "Sarubera", "Sondiha", "Taping", "Topa"]
        },
        {
        "district_name": "Ramgarh",
        "block_name": "Patratu",
        "panchayats": ["Block Panchayats of Patratu Block (Details to be provided as per available data)"]
        },
        {
        "district_name": "Ramgarh",
        "block_name": "Ramgarh",
        "panchayats": ["Block Panchayats of Ramgarh Block (Details to be provided as per available data)"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Angara",
        "panchayats": ["Bari", "Bhala", "Chitik Behar", "Dadathahi", "Golu", "Idgora", "Kantadih", "Kursi", "Nagri", "Santaldih", "Saruberu"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Bero",
        "panchayats": ["Bero", "Chandpur", "Gundi", "Hupkar", "Imelda", "Kadra", "Lamnda", "Lath", "Ripbul"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Burmu",
        "panchayats": ["Aamno", "Amtar", "Birkamara", "Burmu", "Dumdari", "Ganwadih", "Hateya", "Kakri", "Khuntitoli", "Pendari"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Chanho",
        "panchayats": ["Bhadra", "Chandil", "Gamharia", "Gara", "Jama", "Karma", "Kudti", "Mandi", "Nawadih"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Itki",
        "panchayats": ["Andha", "Badwa", "Burighat", "Itki", "Jalbari", "Kadma", "Karma", "Koel", "Kumardih"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Kanke",
        "panchayats": ["Bariatu", "Chikuti", "Dhurda", "Gundri", "Hatgamharia", "Kanke Sadar", "Latiya", "Namkum", "Pali"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Khelari",
        "panchayats": ["Abad", "Bagodi", "Dumari", "Gundi", "Itkhori", "Khelari", "Kuju", "Nimka", "Phulwari"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Lapung",
        "panchayats": ["Bagbera", "Bari", "Garga", "Joriya", "Lohra", "Manatu", "Nagri", "Pundru", "Suga"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Mandar",
        "panchayats": ["Banu", "Chaintia", "Dumri", "Gamharia", "Kardahawa", "Mandar", "Pahariya", "Sundari", "Tingi"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Namkum",
        "panchayats": ["Amupur", "Bandadih", "Bariatu", "Barkakana", "Bero", "Gamharia", "Kumardih", "Namkum", "Patamda"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Ormanjhi",
        "panchayats": ["Andhari", "Bamundih", "Derang", "Gola", "Hesal", "Ormanjhi", "Sundar"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Ratu",
        "panchayats": ["Ammudih", "Barsi", "Dalmi", "Garhwa", "Jharia", "Lotupur", "Pahariya", "Ramgarh", "Salkocha"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Silli",
        "panchayats": ["Amrudih", "Bhumijgarh", "Chandsara", "Dundurkala", "Icha", "Jalkera", "Korachka", "Silli", "Talabnagar"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Sonahatu",
        "panchayats": ["Aurangabad", "Bajkuli", "Chota Helu", "Duldih", "Kamtha", "Nawadih", "Sonahatu"]
        },
        {
        "district_name": "Ranchi",
        "block_name": "Tamar",
        "panchayats": ["Bahadurpur", "Bara Tatu", "Charbari", "Hathnia", "Jarmundi", "Kabirpur", "Khuntitoli", "Lohandih", "Tamar"]
        },
        
        {
        "district_name": "Saraikela Kharsawan",
        "block_name": "Saraikela",
        "panchayats": ["Banksai", "Bara Bana", "Bara Daona", "Bara Tengrani", "Chandpura", "Chandpur", "Chhatkeshwa", "Duldih", "Gamharia", "Jawaharpur", "Kaliari", "Kumhari", "Lakhanpur", "Madhuban", "Nawadih", "Rajpur", "Sahpur", "Sundari"]
        },
        {
        "district_name": "Saraikela Kharsawan",
        "block_name": "Kharsawan",
        "panchayats": ["Asankera", "Barunbari", "Chandil", "Haldipokhar", "Hezampur", "Ikhagra", "Jalia", "Jambhadih", "Kharsawan", "Khadin", "Lohbara", "Mara", "Nawadih", "Pakridih", "Sikraur"]
        },
        {
        "district_name": "Saraikela Kharsawan",
        "block_name": "Gamharia",
        "panchayats": ["Bandhdih", "Birbansh", "Burudih", "Chamaru", "Dudra", "Dugdha", "Dugni", "Dumra", "Itagarh", "Jagannathpur", "Jaikan", "Kalikapur", "Kandra", "Muria", "Narayanpur", "Nuagarh", "Rapcha", "Tentoposi", "Yashpur"]
        },
        {
        "district_name": "Saraikela Kharsawan",
        "block_name": "Ichagarh",
        "panchayats": ["Asanbani", "Badalkolha", "Badalkolha South", "Bakarwa", "Baruadih", "Chhupra", "Dumardih", "Ichagarh", "Jaganathpur", "Jamshedpur", "Kandra", "Lathidih", "Matkamdih", "Narayanpur", "Nuagarh", "Pakribera", "Pakribera South", "Parugaon", "Ramgarh", "Sawali"]
        },
        {
        "district_name": "Saraikela Kharsawan",
        "block_name": "Nimdih",
        "panchayats": ["Andharia", "Bhajji", "Chhota Kumarpur", "Gamharia", "Genda", "Gua", "Harla", "Jagannathpur", "Jharia", "Karamtoli", "Katkarai", "Kunkuri", "Lalpur", "Mugma", "Nimdih", "Panki", "Rajpur"]
        },
        {
        "district_name": "Saraikela Kharsawan",
        "block_name": "Kukru",
        "panchayats": ["Aunpani", "Balrampur", "Basaidih", "Basanga", "Bhunwa", "Chakradih", "Chama", "Damar", "Dandasol", "Demri", "Dhudi", "Gamharia", "Jarali", "Jikki", "Kukru", "Lena", "Manko", "Nirajpur", "Pithoria", "Tarha"]
        },
        {
        "district_name": "Saraikela Kharsawan",
        "block_name": "Chandil",
        "panchayats": ["Asanbani", "Bhadudih", "Chandil", "Chilgu", "Chowka", "Chowlibasa", "Dhunaburu", "Ghoranegi", "Hensakocha", "Jhabri", "Kapali Northeast", "Kapali Northwest", "Kapali Southeast", "Kapali Southwest", "Khunti", "Matkamdih", "Rasuniya", "Ruchap", "Rudiya", "Tamuliya", "Urmal"]
        },
        {
        "district_name": "Simdega",
        "block_name": "Bano",
        "panchayats": ["Badkaduel", "Banki", "Bano", "Bera Ergi", "Bintuka", "Dumariya", "Genmer", "Jamtai", "Kanarowan", "Konsodey", "Pabura", "Raikera", "Sahubera", "Simhatu", "Soy", "Ukouli"]
        },
        {
        "district_name": "Simdega",
        "block_name": "Bolba",
        "panchayats": ["Behrinbasa", "Kadopani", "Malsara", "Pidiyaponch", "Samsera"]
        },
        {
        "district_name": "Simdega",
        "block_name": "Jaldega",
        "panchayats": ["Jaldega", "Konmerla", "Kutungiya", "Lamboi", "Lamdega", "Orga", "Parba", "Patiamba", "Tati", "Tingina"]
        },
        {
        "district_name": "Simdega",
        "block_name": "Kolebira",
        "panchayats": ["Agharma", "Aidega", "Bandarchuwan", "Barasloya", "Domtoli", "Kolebira", "Lachragarh", "Nawatoli", "Rainsiya", "Shahpur", "Tutikel"]
        },
        {
        "district_name": "Simdega",
        "block_name": "Kurdeg",
        "panchayats": ["Bara Duga", "Basantpur", "Barkchipara", "Belpahari", "Bhikampura", "Birbanki", "Chhata", "Dugdatra", "Gamharia", "Gudum", "Jharia", "Kandpur", "Khelma", "Kunda", "Kurdeg", "Lohra", "Maranghada", "Nandpur", "Orwa", "Pabura", "Pusungai", "Raghunathpur", "Saranda", "Sikurdihi", "Singhbani"]
        },
        {
        "district_name": "Simdega",
        "block_name": "Simdega",
        "panchayats": ["Akura", "Arani", "Baghlata", "Bakatangar", "Belgarh", "Chahada", "Chubka", "Dibadih", "Dumar", "Gamharia", "Gumla", "Jainagar", "Jaldega", "Joradih", "Karkatai", "Kundru", "Loteria", "Malam", "Munjapara", "Nayadih", "PakarTanr", "Panchbaria", "Patratu", "Phulabani"]
        },
        {
        "district_name": "Simdega",
        "block_name": "Thethaitangar",
        "panchayats": ["Arli", "Arliapur", "Bandarchuwan", "Barew", "Barkach", "Chakatoli", "Dumartoli", "Jamkahara", "Jaridih", "Kaladang", "Kansokala", "Karmtoli", "Karkach", "Kuraki", "Lachragarh", "Lohardaga", "Lumphatoli"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Chakradharpur",
        "panchayats": ["Gopinathpur", "Jorro", "Kotpad", "Pusma", "Urdikera"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Chaibasa",
        "panchayats": ["Barkundia", "Tuibir", "Pampara", "Baitulbir", "Tergo"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Goilkera",
        "panchayats": ["Rairowa", "Dalaikela", "Jaransha", "Jijuria", "Shivnathpur"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Gudri",
        "panchayats": ["Gudri East", "Gudri West", "Gamaria", "Rairowa"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Jhinkpani",
        "panchayats": ["Jhinkpani East", "Jhinkpani West", "Mohammadganj", "Jarudi", "Kundra"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Khuntpani",
        "panchayats": ["Khuntpani", "Nawagarh", "Tailbani", "Jalboni", "Thakurgarh"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Manjhari",
        "panchayats": ["Panga", "Papagara", "Rankui", "Tengrai"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Manoharpur",
        "panchayats": ["Manoharpur East", "Manoharpur West", "Bundu", "Sakchi", "Jakran"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Noamundi",
        "panchayats": ["Gua East", "Gua West", "Diriburu", "Takura", "Bokna"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Sonua",
        "panchayats": ["Sonua East", "Sonua West", "Pusika", "Kumardungi"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Tantnagar",
        "panchayats": ["Tantnagar East", "Tantnagar West", "Bariatu"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Tonto",
        "panchayats": ["Tonto East", "Tonto West", "Baranduda"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Kumardungi",
        "panchayats": ["Kumardungi East", "Kumardungi West", "Kasidih"]
        },
        {
        "district_name": "West Singhbhum",
        "block_name": "Anjadbera",
        "panchayats": ["Anjadbera East", "Anjadbera West"]
        }
    
        
       
        
    ]


    # ✅ All India States list (28 states + UTs agar chahiye to add kar sakte hain)
    states_list = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
        "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
        "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
    ]

    # Bihar ke liye districts aur blocks jaise abhi aapke paas hai usi ko use karenge

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
        'states': states_list,  # ✅ States dropdown ke liye
        'locations_jharkhand': jharkhand_locations,  # ✅ Jharkhand ka district+block data
        'locations': bihar_locations  # ✅ Bihar ka district+block data
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
    form = AdminMessageForm(request.POST or None)
    levels_selected = request.POST.getlist("level[]") if request.method == "POST" else []

    if request.method == "POST" and form.is_valid():
        receiver_username = form.cleaned_data.get("receiver_username")
        group_choice = form.cleaned_data.get("group_choice")
        state = request.POST.get("state_filter")
        district = request.POST.get("district_filter")
        levels = levels_selected
        message_text = form.cleaned_data.get("message")

        users = User.objects.none()  # final queryset

        # --- 1. Single user ---
        if receiver_username:
            try:
                receiver = User.objects.get(username=receiver_username)
                users |= User.objects.filter(id=receiver.id)
            except User.DoesNotExist:
                messages.error(request, f"User '{receiver_username}' does not exist!")

        # --- 2. Group choice ---
        if group_choice:
            if group_choice == "state":
                users |= User.objects.filter(state__isnull=False)
            elif group_choice == "district":
                users |= User.objects.filter(assigned_district__isnull=False)
            elif group_choice == "block":
                users |= User.objects.filter(assigned_block__isnull=False)
            elif group_choice == "booth":
                users |= User.objects.filter(booth_number__isnull=False)

        # --- 3. State & District filter + checkboxes ---
        if state and district and levels:
            filtered_users = User.objects.none()
            
            for lvl in levels:
                if lvl == "district":
                    filtered_users |= User.objects.filter(state=state, assigned_district=district)
                elif lvl == "block":
                    filtered_users |= User.objects.filter(state=state, assigned_district=district, assigned_block__isnull=False)
                elif lvl == "booth":
                    filtered_users |= User.objects.filter(state=state, assigned_district=district, booth_number__isnull=False)

            users |= filtered_users


        # --- 4. Agar koi user nahi mila ---
        if not users.exists():
            messages.error(request, "No users found for the selected option or filter.")
            return redirect("send_admin_message")

        # --- 5. Send messages ---
        for u in users.distinct():
            AdminMessage.objects.create(sender=request.user, receiver=u, message=message_text)

        messages.success(request, f"Message sent to {users.distinct().count()} user(s) successfully!")
        return redirect("send_admin_message")

    # --- Sent messages ---
    sent_msgs = AdminMessage.objects.filter(sender=request.user).order_by("-created_at")

    # --- State & district choices ---
    state_choices = ["Bihar", "Jharkhand"]
    district_choices = {
        "Bihar": [
            "Araria","Arwal","Aurangabad","Banka","Begusarai","Bhagalpur","Bhojpur","Buxar",
            "Darbhanga","Gaya","Gopalganj","Jamui","Jehanabad","Kaimur","Katihar","Khagaria",
            "Kishanganj","Lakhisarai","Madhepura","Madhubani","Munger","Muzaffarpur","Nalanda",
            "Nawada","Patna","Purnia","Rohtas","Saharsa","Samastipur","Saran","Sheikhpura",
            "Sheohar","Sitamarhi","Siwan","Supaul","Vaishali","West Champaran","East Champaran"
        ],
        "Jharkhand": [
            "Bokaro","Chatra","Deoghar","Dhanbad","Dumka","East Singhbhum","Garhwa","Giridih",
            "Godda","Gumla","Hazaribagh","Jamtara","Khunti","Koderma","Latehar","Lohardaga",
            "Pakur","Palamu","Ramgarh","Ranchi","Sahibganj","Saraikela-Kharsawan","Simdega","West Singhbhum"
        ]
    }

    return render(request, "core/admin/send_admin_message.html", {
        "form": form,
        "sent_msgs": sent_msgs,
        "state_choices": state_choices,
        "district_choices": district_choices,
        "levels_selected": levels_selected,       # ✅ template me checked dikhe
        "selected_state": state if request.method == "POST" else "",
        "selected_district": district if request.method == "POST" else "",
    })


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


    # -------- Complaint Stats --------
    # State-wise complaints
    state_complaints = (
        Complaint.objects
        .values("state")
        .annotate(
            total=Count("id"),
            accepted=Count("id", filter=Q(status="Accepted")),
            rejected=Count("id", filter=Q(status="Rejected")),
            solved=Count("id", filter=Q(status="Solved"))
        )
        .order_by("state")
    )


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


# -------------------- Bihar + Jharkhand Locations --------------------
# Bihar locations
bihar_locations = [
    {"district_name": "Araria", "blocks": ["Araria", "Forbesganj", "Jokihat", "Kursakatta", "Narpatganj", "Palasi", "Raniganj", "Sikti"], "state": "Bihar"},
    {"district_name": "Arwal", "blocks": ["Arwal", "Kaler", "Karpi", "Kurtha", "Sonbhadra Banshi Suryapur"], "state": "Bihar"},
    {"district_name": "Aurangabad", "blocks": ["Aurangabad", "Barun", "Daudnagar", "Deo", "Goh", "Haspura", "Kutumba", "Madanpur", "Nabinagar", "Obra", "Rafiganj"], "state": "Bihar"},
    {"district_name": "Banka", "blocks": ["Banka", "Amarpur", "Dhoraiya", "Katoria", "Bausi", "Shambhuganj", "Barahat", "Belhar"], "state": "Bihar"},
    {"district_name": "Begusarai", "blocks": ["Begusarai", "Barauni", "Teghra", "Matihani", "Bachhwara", "Mansurchak", "Naokothi", "Sahebpur Kamal"], "state": "Bihar"},
    {"district_name": "Bhagalpur", "blocks": ["Pirpainti", "Kahalgaon", "Sanhaula", "Sabour", "Nathnagar", "Jagdishpur", "Sultanganj", "Sahkund", "Bihpur"], "state": "Bihar"},
    {"district_name": "Bhojpur", "blocks": ["Arrah", "Jagdishpur", "Koilwar", "Sahar", "Barhara", "Sandesh", "Piro", "Udwantnagar", "Bihiya", "Agiaon"], "state": "Bihar"},
    {"district_name": "Buxar", "blocks": ["Buxar", "Chausa", "Rajpur", "Sikandarpur", "Nawanagar", "Dumraon"], "state": "Bihar"},
    {"district_name": "Darbhanga", "blocks": ["Darbhanga", "Hayaghat", "Jale", "Bahadurpur", "Keoti", "Biraul", "Kusheswar Asthan", "Alinagar", "Benipur"], "state": "Bihar"},
    {"district_name": "East Champaran", "blocks": ["Motihari", "Sugauli", "Harsiddhi", "Pakridayal", "Maheshi", "Kotwa", "Banjaria", "Piprakothi"], "state": "Bihar"},
    {"district_name": "Gaya", "blocks": ["Gaya", "Barachatti", "Sherghati", "Tekari", "Dumaria", "Mohanpur", "Aurai", "Katra"], "state": "Bihar"},
    {"district_name": "Gopalganj", "blocks": ["Gopalganj", "Manjha", "Bhore", "Barauli", "Kuchaikote", "Sadar"], "state": "Bihar"},
    {"district_name": "Jamui", "blocks": ["Jamui", "Chakai", "Jhajha", "Gidhaur", "Lakhisarai", "Khaira"], "state": "Bihar"},
    {"district_name": "Jehanabad", "blocks": ["Jehanabad", "Makhdumpur", "Kako", "Hulasganj", "Modanganj"], "state": "Bihar"},
    {"district_name": "Kaimur (Bhabua)", "blocks": ["Bhabua", "Kaimur", "Kudra", "Ramgarh"], "state": "Bihar"},
    {"district_name": "Katihar", "blocks": ["Katihar", "Kadwa", "Balrampur", "Pranpur", "Manihari", "Barari", "Korha", "Alamnagar"], "state": "Bihar"},
    {"district_name": "Khagaria", "blocks": ["Khagaria", "Alauli", "Chautham", "Beldaur", "Mansi"], "state": "Bihar"},
    {"district_name": "Kishanganj", "blocks": ["Kishanganj", "Kochadhaman", "Amour", "Baisi", "Kasba", "Banmankhi", "Rupauli"], "state": "Bihar"},
    {"district_name": "Lakhisarai", "blocks": ["Lakhisarai", "Chanan Banu Bagicha", "Raigarh Chowk", "Piparia"], "state": "Bihar"},
    {"district_name": "Madhepura", "blocks": ["Madhepura", "Alamnagar", "Singheshwar", "Murliganj", "Shankarpur", "Kataharia"], "state": "Bihar"},
    {"district_name": "Madhubani", "blocks": ["Madhubani", "Bisfi", "Benipatti", "Basopatti", "Babubarhi", "Patori", "Khajauli"], "state": "Bihar"},
    {"district_name": "Munger", "blocks": ["Munger", "Jamalpur", "Kharagpur", "Sadar"], "state": "Bihar"},
    {"district_name": "Muzaffarpur", "blocks": ["Muzaffarpur", "Kanti", "Motipur", "Paru", "Bandra", "Marawan"], "state": "Bihar"},
    {"district_name": "Nalanda", "blocks": ["Nalanda", "Rajgir", "Hilsa", "Islampur", "Noorsarai", "Tharthari"], "state": "Bihar"},
    {"district_name": "Nawada", "blocks": ["Nawada", "Rajouli", "Akbarpur", "Warisaliganj", "Hisua"], "state": "Bihar"},
    {"district_name": "Patna", "blocks": ["Patna Sadar", "Paliganj", "Danapur", "Dhanarua", "Maner", "Bihta", "Barh"], "state": "Bihar"},
    {"district_name": "Purnia", "blocks": ["Purnia", "Banmankhi", "Dhamdaha", "Krityanand Nagar", "Rupauli", "Amour", "Barhara Kothi"], "state": "Bihar"},
    {"district_name": "Rohtas", "blocks": ["Rohtas", "Sasaram", "Dehri", "Nauhatta", "Akbarpur", "Suryapura"], "state": "Bihar"},
    {"district_name": "Saharsa", "blocks": ["Saharsa", "Simri Bakhtiyarpur", "Mahishi", "Kusheshwar Asthan", "Sonbarsha"], "state": "Bihar"},
    {"district_name": "Samastipur", "blocks": ["Samastipur", "Morwa", "Sakra", "Patori", "Rosera", "Katarpur", "Ujiyarpur"], "state": "Bihar"},
    {"district_name": "Saran", "blocks": ["Chhapra", "Marhaura", "Garkha", "Pachrukhi", "Taraiya", "Mashrakh"], "state": "Bihar"},
    {"district_name": "Sheikhpura", "blocks": ["Sheikhpura", "Amla", "Chewara", "Parbatti", "Barbigha"], "state": "Bihar"},
    {"district_name": "Sitamarhi", "blocks": ["Sitamarhi", "Bathnaha", "Bairgania", "Riga", "Pupri", "Sursand"], "state": "Bihar"},
    {"district_name": "Siwan", "blocks": ["Siwan", "Maharajganj", "Barharia", "Goriyakothi", "Hussainganj", "Raghunathpur"], "state": "Bihar"},
    {"district_name": "Supaul", "blocks": ["Supaul", "Tribeniganj", "Nirmali", "Bariyarpur", "Basantpur", "Chhatapur"], "state": "Bihar"},
    {"district_name": "Vaishali", "blocks": ["Hajipur", "Bidupur", "Goraul", "Chehrakala", "Patepur", "Mahnar", "Desri"], "state": "Bihar"},
    {"district_name": "West Champaran", "blocks": ["Bettiah", "Narkatiaganj", "Pipra", "Bagaha", "Sidhwalia", "Marwan"], "state": "Bihar"},
]


# Jharkhand locations
jharkhand_locations = [
    {"district_name": "Ranchi", "blocks": ["Ranchi Sadar", "Kanke", "Angara", "Burmu", "Bundu", "Namkum", "Ormanjhi", "Rahe", "Silli", "Sonahatu", "Tamar"], "state": "Jharkhand"},
    {"district_name": "Bokaro", "blocks": ["Bermo", "Chandankiyari", "Chas", "Gomia", "Kasmar", "Nawadih", "Petarwar"], "state": "Jharkhand"},
    {"district_name": "Dhanbad", "blocks": ["Baghmara", "Baliapur", "Dhanbad", "Gobindpur", "Jharia", "Kenduadih", "Nirsa", "Purbi Tundi", "Tundi", "Topchanchi"], "state": "Jharkhand"},
    {"district_name": "East Singhbhum", "blocks": ["Jamshedpur East", "Jamshedpur West", "Ghatshila", "Chakulia", "Dhalbhumgarh", "Musabani", "Potka"], "state": "Jharkhand"},
    {"district_name": "Garhwa", "blocks": ["Garhwa", "Bhawanathpur", "Danda", "Palkot", "Bhandaria"], "state": "Jharkhand"},
    {"district_name": "Giridih", "blocks": ["Giridih", "Barkatha", "Dumri", "Pirtand", "Tisri", "Jamua", "Deori"], "state": "Jharkhand"},
    {"district_name": "Godda", "blocks": ["Godda", "Poraiyahat", "Mahagama", "Pathargama", "Boarijor", "Sunderpahari"], "state": "Jharkhand"},
    {"district_name": "Gumla", "blocks": ["Gumla", "Bharno", "Bishunpur", "Chainpur", "Albert Ekka", "Sisai", "Raidih"], "state": "Jharkhand"},
    {"district_name": "Hazaribagh", "blocks": ["Hazaribagh", "Barkagaon", "Chowki", "Dadi", "Keredari", "Petarwar", "Padma", "Ichak"], "state": "Jharkhand"},
    {"district_name": "Jamtara", "blocks": ["Jamtara", "Nala", "Karmatanr", "Narayanpur"], "state": "Jharkhand"},
    {"district_name": "Khunti", "blocks": ["Khunti", "Murhu", "Karra", "Torpa", "Bandgaon", "Konchu"], "state": "Jharkhand"},
    {"district_name": "Koderma", "blocks": ["Koderma", "Markacho", "Jhumri Tilaiya", "Domchanch"], "state": "Jharkhand"},
    {"district_name": "Latehar", "blocks": ["Latehar", "Balumath", "Manika", "Chhatarpur", "Bariyatu"], "state": "Jharkhand"},
    {"district_name": "Lohardaga", "blocks": ["Lohardaga", "Kisko", "Kisko", "Barkatha", "Pirtand"], "state": "Jharkhand"},
    {"district_name": "Pakur", "blocks": ["Pakur", "Amrapara", "Hiranpur", "Maheshpur", "Pakaur"], "state": "Jharkhand"},
    {"district_name": "Palamu", "blocks": ["Daltonganj", "Chhatarpur", "Hesla", "Hariharganj", "Panki", "Pipra"], "state": "Jharkhand"},
    {"district_name": "Ramgarh", "blocks": ["Ramgarh", "Gola", "Mandu", "Chitarpur", "Patratu"], "state": "Jharkhand"},
    {"district_name": "Ranchi", "blocks": ["Ranchi Sadar", "Kanke", "Angara", "Burmu", "Bundu", "Namkum", "Ormanjhi", "Rahe", "Silli", "Sonahatu", "Tamar"], "state": "Jharkhand"},
    {"district_name": "Sahibganj", "blocks": ["Sahibganj", "Mahuwa", "Taljhari", "Rajnagar", "Mandro", "Barhait"], "state": "Jharkhand"},
    {"district_name": "Saraikela-Kharsawan", "blocks": ["Saraikela", "Kharsawan", "Rajnagar", "Gamharia"], "state": "Jharkhand"},
    {"district_name": "Simdega", "blocks": ["Simdega", "Bano", "Thethaitangar", "Bansjore", "Bolba", "Kolebira"], "state": "Jharkhand"},
    {"district_name": "West Singhbhum", "blocks": ["Chaibasa", "Chakradharpur", "Goilkera", "Majhgaon", "Sonahatu", "Tantidih"], "state": "Jharkhand"},
    {"district_name": "Saraikela", "blocks": ["Saraikela", "Kharsawan", "Gamharia"], "state": "Jharkhand"},
    {"district_name": "Jamtara", "blocks": ["Jamtara", "Karmatanr", "Nala", "Narayanpur"], "state": "Jharkhand"},
    {"district_name": "Deoghar", "blocks": ["Deoghar", "Mohanpur", "Bariyarpur", "Pathia", "Madar"], "state": "Jharkhand"},
]

# Combine Bihar + Jharkhand
DISTRICT_BLOCKS = bihar_locations + jharkhand_locations



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

    # Filter parameters from GET
    state = request.GET.get('state')
    district = request.GET.get('district')
    block = request.GET.get('block')
    panchayat = request.GET.get('panchayat')

    if state:
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
        {
            "district_name": "Araria",
            "block_name": "Araria",
            "panchayats": [
            "Araria Basti", "Azamnagar Kusiyar Gawon", "Azmatpur Basantpur", "Bahgi Pokharia",
            "Bairgachhi Belwa", "Bangawan Bangama", "Bansbari Bansbari", "Barakamatchistipur Haria",
            "Basantpur Basantpur", "Baturbari Baturbari", "Belbari Araria Basti", "Belsandi Araria Basti",
            "Belwa Araria Basti", "Bhadwar Araria Basti", "Bhairoganj Araria Basti", "Bhanghi Araria Basti",
            "Bhawanipur Araria Basti", "Bhorhar Araria Basti", "Chakorwa Araria Basti", "Dahrahra Araria Basti",
            "Damiya Araria Basti", "Dargahiganj Araria Basti", "Dombana Araria Basti", "Dumari Araria Basti",
            "Fatehpur Araria Basti", "Gadhgawan Araria Basti", "Gandhi Araria Basti", "Gangauli Araria Basti",
            "Ganj Araria Basti", "Gogri Araria Basti", "Gopalpur Araria Basti"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Forbesganj",
            "panchayats": [
            "Forbesganj", "Araria", "Bhargama", "Raniganj", "Sikti", "Palasi",
            "Jokihat", "Kursakatta", "Narpatganj", "Hanskosa", "Hardia", "Haripur",
            "Hasanpur Khurd", "Hathwa", "Gadaha", "Ganj Bhag", "Ghiwba", "Ghoraghat",
            "Gogi", "Gopalpur", "Gurmahi", "Halhalia", "Halhalia Jagir"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Jokihat",
            "panchayats": [
            "Jokihat", "Artia Simaria", "Bagdahara", "Bagesari", "Bagmara", "Bagnagar",
            "Baharbari", "Bairgachhi", "Bankora", "Bara Istamrar", "Bardenga", "Barhuwa",
            "Bazidpur", "Beldanga", "Bela", "Belsandi", "Belwa", "Bhatkuri", "Bharwara",
            "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri", "Dundbahadur Chakla", "Gamharia"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Kursakatta",
            "panchayats": [
            "Kursakatta", "Kamaldaha", "Kuari", "Lailokhar", "Sikti", "Singhwara", "Sukhasan", "Bairgachhi"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Narpatganj",
            "panchayats": [
            "Narpatganj", "Ajitnagar", "Amrori", "Anchraand Hanuman Nagar", "Baghua Dibiganj",
            "Bardaha", "Barhara", "Barhepara", "Bariarpur", "Barmotra Arazi", "Basmatiya", "Bela",
            "Belsandi", "Belwa"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Palasi",
            "panchayats": [
            "Palasi", "Bakainia", "Balua", "Bangawan", "Baradbata", "Baraili", "Bargaon",
            "Barkumba", "Behari", "Belbari", "Belsari", "Beni", "Beni Pakri"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Raniganj",
            "panchayats": [
            "Raniganj", "Asabhag", "Asura Kalan Khola", "Bakhri Milik", "Balchanda", "Banmali",
            "Batraha", "Bhag Parasi", "Bhagtira", "Bhaloa", "Bhimpur Khar", "Bhishunpur",
            "Bhorha", "Bhutahi", "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri",
            "Dundbahadur Chakla", "Gamharia", "Gamharia Milik"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Sikti",
            "panchayats": [
            "Sikti", "Asabhag", "Asura Kalan Khola", "Bakhri Milik", "Balchanda", "Banmali",
            "Batraha", "Bhag Parasi", "Bhagtira", "Bhaloa", "Bhimpur Khar", "Bhishunpur",
            "Bhorha", "Bhutahi", "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri",
            "Dundbahadur Chakla", "Gamharia", "Gamharia Milik"
            ]
        },
            
        {
            "district_name": "Arwal",
            "block_name": "Arwal",
            "panchayats": ["Abgila", "Amara", "Arwal Sipah", "Basilpur", "Bhadasi", "Fakharpur", "Khamaini", "Makhdumpur", "Muradpur Hujara", "Parasi", "Payarechak", "Rampur Baina"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Kaler",
            "panchayats": ["Sakri Khurd", "Balidad", "Belawan", "Belsar", "Injor", "Ismailpur Koyal", "Jaipur", "Kaler", "Kamta", "Mainpura", "North Kaler", "Pahleja"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Karpi",
            "panchayats": ["Khajuri", "Kochahasa", "Aiyara", "Bambhi", "Belkhara", "Chauhar", "Dorra", "Kapri", "Karpi", "Keyal", "Kinjar", "Murarhi"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Kurtha",
            "panchayats": ["Ahmadpur Harna", "Alawalpur", "Bahbalpur", "Baid Bigha", "Bara", "Barahiya", "Basatpur", "Benipur", "Bishunpur", "Chhatoi", "Dakra", "Darheta", "Dhamaul", "Dhondar", "Gangapur", "Gangea", "Gauhara", "Gokhulpur", "Harpur", "Helalpur", "Ibrahimpur", "Jagdispur", "Khaira", "Khemkaran Saray", "Kimdar Chak", "Kod marai", "Koni", "Kothiya", "Kubri", "Kurkuri", "Kurthadih", "Lari", "Lodipur", "Madarpur", "Mahmadpur", "Makhdumpur", "Manikpur", "Manikpur", "Milki", "Mobarakpur", "Molna Chak", "Motipur", "Musarhi", "Nadaura", "Narhi", "Nezampur", "Nighwan"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Sonbhadra Banshi Suryapur",
            "panchayats": ["Sonbhadra", "Banshi", "Suryapur"]
        },
         {
            "district_name": "Aurangabad",
            "block_name": "Aurangabad",
            "panchayats": ["Aurangabad Sadar", "Barun", "Karmabad", "Bachra", "Bhawanipur", "Chakibazar", "Dhanauti", "Jaitpur", "Khurampur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Barun",
            "panchayats": ["Barun", "Bhagwanpur", "Kundahar", "Laxmanpur", "Rampur", "Sasaram", "Senga", "Tandwa"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Deo",
            "panchayats": ["Deo", "Bakar", "Chakand", "Gopalpur", "Jamalpur", "Kachhahi", "Kekri", "Manjhi"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Goh",
            "panchayats": ["Goh", "Kachhawa", "Kanchanpur", "Khirpai", "Makhdumpur", "Rajnagar", "Rampur", "Sarwa"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Haspura",
            "panchayats": ["Haspura", "Barauli", "Belwar", "Bichkoi", "Chandi", "Khapri", "Mahmoodpur", "Nuaon"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Kutumba",
            "panchayats": ["Kutumba", "Brajpura", "Chak Mukundpur", "Daharpur", "Gopalpur", "Jhunjhunu", "Rampur", "Sahar"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Madanpur",
            "panchayats": ["Madanpur", "Amra", "Bajidpur", "Barachatti", "Chakiya", "Dhanpur", "Kachhawa", "Rampur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Nabinagar",
            "panchayats": ["Nabinagar", "Alipur", "Chhatauni", "Deohra", "Jafarpur", "Rampur", "Shivpur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Obra",
            "panchayats": ["Obra", "Biharichak", "Chhata", "Harikala", "Kandua", "Rampur", "Sakra"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Rafiganj",
            "panchayats": ["Rafiganj", "Barauni", "Bhagwanpur", "Chakuli", "Deoghar", "Mohanpur", "Rampur", "Sikta"]
        },
        


        {
            "district_name": "Banka",
            "block_name": "Amarpur",
            "panchayats": ["Amarpur", "Chouka", "Dhamua", "Gopalpur", "Haripur", "Jagdishpur", "Kharagpur", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Banka",
            "panchayats": ["Banka Sadar", "Barhampur", "Chandipur", "Dumaria", "Kharik", "Maheshpur", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Barahat",
            "panchayats": ["Barahat", "Chakpura", "Durgapur", "Jagdishpur", "Kudra", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Belhar",
            "panchayats": ["Belhar", "Chakbhabani", "Durgapur", "Maheshpur", "Rampur", "Sahapur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Bausi",
            "panchayats": ["Bausi", "Chakla", "Dhanpur", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Bihat",
            "panchayats": ["Bihat", "Chakra", "Durgapur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Chandan",
            "panchayats": ["Chandan", "Gopalpur", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Dhuraiya",
            "panchayats": ["Dhuraiya", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Katoria",
            "panchayats": ["Katoria", "Rampur", "Chakla", "Maheshpur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Rajauli",
            "panchayats": ["Rajauli", "Chakbhabani", "Rampur", "Durgapur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Shambhuganj",
            "panchayats": ["Shambhuganj", "Rampur", "Chakla", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Sultanganj",
            "panchayats": ["Sultanganj", "Rampur", "Chakbhabani", "Durgapur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Tola",
            "panchayats": ["Tola", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Udwantnagar",
            "panchayats": ["Udwantnagar", "Rampur", "Chakla", "Durgapur", "Maheshpur"]
        },
        

            
        {
            "district_name": "Begusarai",
            "block_name": "Bachhwara",
            "panchayats": ["Bachhwara", "Chowki", "Kachhwa", "Mahamadpur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bakhri",
            "panchayats": ["Bakhri", "Chakla", "Dhanpur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Balia",
            "panchayats": ["Balia", "Chakbhabani", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Barauni",
            "panchayats": ["Barauni", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Begusarai",
            "panchayats": ["Begusarai Sadar", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bhagwanpur",
            "panchayats": ["Bhagwanpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Birpur",
            "panchayats": ["Birpur", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Cheria Bariyarpur",
            "panchayats": ["Cheria Bariyarpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Dandari",
            "panchayats": ["Dandari", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Garhpura",
            "panchayats": ["Garhpura", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Khodawandpur",
            "panchayats": ["Khodawandpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Mansurchak",
            "panchayats": ["Mansurchak", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Matihani",
            "panchayats": ["Matihani", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Naokothi",
            "panchayats": ["Naokothi", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Sahebpur Kamal",
            "panchayats": ["Sahebpur Kamal", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Teghra",
            "panchayats": ["Teghra", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bihat",
            "panchayats": ["Bihat", "Chakla", "Rampur", "Sahpur"]
        },
        

        
        {
            "district_name": "Bhagalpur",
            "block_name": "Bihpur",
            "panchayats": ["Bihpur", "Rampur", "Chakla", "Sundarpur", "Maheshpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Colgong",
            "panchayats": ["Colgong", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Goradih",
            "panchayats": ["Goradih", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Ismailpur",
            "panchayats": ["Ismailpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Jagdishpur",
            "panchayats": ["Jagdishpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Kahalgaon",
            "panchayats": ["Kahalgaon", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Kharik",
            "panchayats": ["Kharik", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Nathnagar",
            "panchayats": ["Nathnagar", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Naugachhia",
            "panchayats": ["Naugachhia", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Pirpainty",
            "panchayats": ["Pirpainty", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Rangra Chowk",
            "panchayats": ["Rangra Chowk", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sabour",
            "panchayats": ["Sabour", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sanhaula",
            "panchayats": ["Sanhaula", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Shahkund",
            "panchayats": ["Shahkund", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sultanganj",
            "panchayats": ["Sultanganj", "Chakla", "Rampur", "Sahpur"]
        },
        
        
        {
            "district_name": "Bhojpur",
            "block_name": "Agiaon",
            "panchayats": ["Agiaon", "Sahpur", "Rampur", "Chakla"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Arrah",
            "panchayats": ["Arrah", "Barhara", "Chakla", "Rampur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Barhara",
            "panchayats": ["Barhara", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Behea",
            "panchayats": ["Behea", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Charpokhari",
            "panchayats": ["Charpokhari", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Garhani",
            "panchayats": ["Garhani", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Jagdishpur",
            "panchayats": ["Jagdishpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Koilwar",
            "panchayats": ["Koilwar", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Piro",
            "panchayats": ["Piro", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Sahar",
            "panchayats": ["Sahar", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Sandesh",
            "panchayats": ["Sandesh", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Shahpur",
            "panchayats": ["Shahpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Tarari",
            "panchayats": ["Tarari", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Udwantnagar",
            "panchayats": ["Udwantnagar", "Rampur", "Chakla", "Sahpur"]
        },
        
        
        {
            "district_name": "Buxar",
            "block_name": "Buxar",
            "panchayats": ["Buxar", "Chaugain", "Parashpur", "Kaharpur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Itarhi",
            "panchayats": ["Itarhi", "Srikhand", "Lohna", "Nagar Panchayat Itarhi"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chausa",
            "panchayats": ["Chausa", "Rajpur", "Mahuli", "Khawaspur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Rajpur",
            "panchayats": ["Rajpur", "Chausa", "Brahmapur", "Kesath"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Dumraon",
            "panchayats": ["Dumraon", "Bharathar", "Chakand", "Rajpur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Nawanagar",
            "panchayats": ["Nawanagar", "Kesath", "Chauki"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Brahampur",
            "panchayats": ["Brahampur", "Simri", "Chakki"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Kesath",
            "panchayats": ["Kesath", "Chakki", "Brahampur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chakki",
            "panchayats": ["Chakki", "Kesath", "Simri"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chougain",
            "panchayats": ["Chougain", "Rajpur", "Buxar"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Simri",
            "panchayats": ["Simri", "Brahampur", "Chakki"]
        },
        
                
        {
            "district_name": "Darbhanga",
            "block_name": "Alinagar",
            "panchayats": ["Alinagar", "Bhuapur", "Chakmiyan", "Mahadevpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Benipur",
            "panchayats": ["Benipur", "Biraul", "Bahadurpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Biraul",
            "panchayats": ["Biraul", "Kalyanpur", "Bheja"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Baheri",
            "panchayats": ["Baheri", "Chandih", "Sarsar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Bahadurpur",
            "panchayats": ["Bahadurpur", "Biraul", "Maheshpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Darbhanga Sadar",
            "panchayats": ["Darbhanga Sadar", "Bachhwara", "Madhopur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Ghanshyampur",
            "panchayats": ["Ghanshyampur", "Chhatauni", "Dhunra"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Hayaghat",
            "panchayats": ["Hayaghat", "Biraul", "Maheshpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Jale",
            "panchayats": ["Jale", "Bhagwanpur", "Chhatauni"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Keotirunway",
            "panchayats": ["Keotirunway", "Muraul", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Kusheshwar Asthan",
            "panchayats": ["Kusheshwar Asthan", "Bahadurpur", "Rajpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Manigachhi",
            "panchayats": ["Manigachhi", "Mahishi", "Chhatauni"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Kiratpur",
            "panchayats": ["Kiratpur", "Chhatauni", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Khutauna",
            "panchayats": ["Khutauna", "Rajnagar", "Tardih"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Muraul",
            "panchayats": ["Muraul", "Singhwara", "Purnahiya"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Purnahiya",
            "panchayats": ["Purnahiya", "Gaurabauram", "Khamhria"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Rajnagar",
            "panchayats": ["Rajnagar", "Shivnagar", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Shivnagar",
            "panchayats": ["Shivnagar", "Tardih", "Wazirganj"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Singhwara",
            "panchayats": ["Singhwara", "Muraul", "Rajnagar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Tardih",
            "panchayats": ["Tardih", "Khutauna", "Shivnagar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Wazirganj",
            "panchayats": ["Wazirganj", "Gaurabauram", "Khamhria"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Gaurabauram",
            "panchayats": ["Gaurabauram", "Khamhria", "Purnahiya"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Khamhria",
            "panchayats": ["Khamhria", "Gaurabauram", "Wazirganj"]
        },
        

                
        {
            "district_name": "Gaya",
            "block_name": "Gaya Sadar",
            "panchayats": ["Gaya Sadar", "Kumahar", "Chandauti", "Barkachha"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Belaganj",
            "panchayats": ["Belaganj", "Araj", "Belsand", "Sariya"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Wazirganj",
            "panchayats": ["Wazirganj", "Madhuban", "Bhurpur", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Manpur",
            "panchayats": ["Manpur", "Kabra", "Chandpura", "Balki"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Bodhgaya",
            "panchayats": ["Bodhgaya", "Gorawan", "Barachatti", "Ratanpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Tekari",
            "panchayats": ["Tekari", "Kharar", "Chakpar", "Barhi"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Konch",
            "panchayats": ["Konch", "Rampur", "Barhampur", "Chhatauni"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Guraru",
            "panchayats": ["Guraru", "Chakbar", "Sikandarpur", "Mohanpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Paraiya",
            "panchayats": ["Paraiya", "Dumariya", "Belsand", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Neemchak Bathani",
            "panchayats": ["Neemchak Bathani", "Sikandarpur", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Khizarsarai",
            "panchayats": ["Khizarsarai", "Chakpar", "Balki"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Atri",
            "panchayats": ["Atri", "Barachatti", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Bathani",
            "panchayats": ["Bathani", "Barachatti", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Mohra",
            "panchayats": ["Mohra", "Rampur", "Guraru"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Sherghati",
            "panchayats": ["Sherghati", "Belsand", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Gurua",
            "panchayats": ["Gurua", "Bodhgaya", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Amas",
            "panchayats": ["Amas", "Sikandarpur", "Chakpar"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Banke Bazar",
            "panchayats": ["Banke Bazar", "Rampur", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Imamganj",
            "panchayats": ["Imamganj", "Belsand", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Dumariya",
            "panchayats": ["Dumariya", "Rampur", "Guraru"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Dobhi",
            "panchayats": ["Dobhi", "Bodhgaya", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Mohanpur",
            "panchayats": ["Mohanpur", "Belsand", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Barachatti",
            "panchayats": ["Barachatti", "Rampur", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Fatehpur",
            "panchayats": ["Fatehpur", "Chakpar", "Gurua"]
        },
        

                
        {
            "district_name": "Gopalganj",
            "block_name": "Gopalganj",
            "panchayats": ["Gopalganj", "Narkatiaganj", "Bairia", "Chapra", "Fatehpur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Thawe",
            "panchayats": ["Thawe", "Parsa", "Bamahi", "Chhaprauli"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Kuchaikote",
            "panchayats": ["Kuchaikote", "Kalyanpur", "Sikati", "Belsand"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Manjha",
            "panchayats": ["Manjha", "Babhnauli", "Rampur", "Chhapra"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Sidhwaliya",
            "panchayats": ["Sidhwaliya", "Belha", "Parmanpur", "Rampur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Hathua",
            "panchayats": ["Hathua", "Bhanpura", "Ramnagar", "Chakpar"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Baikunthpur",
            "panchayats": ["Baikunthpur", "Rampur", "Belsand", "Sikandarpur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Barauli",
            "panchayats": ["Barauli", "Rampur", "Chakpar", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Kateya",
            "panchayats": ["Kateya", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Phulwariya",
            "panchayats": ["Phulwariya", "Rampur", "Chakpar", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Panchdewari",
            "panchayats": ["Panchdewari", "Rampur", "Belsand", "Chakpar"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Uchkagaon",
            "panchayats": ["Uchkagaon", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Vijayipur",
            "panchayats": ["Vijayipur", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Bhorey",
            "panchayats": ["Bhorey", "Rampur", "Belsand", "Chakpar"]
        },
        

        
        {
            "district_name": "Jamui",
            "block_name": "Jamui",
            "panchayats": ["Jamui", "Chakai", "Barhampur", "Dumri", "Sikandra"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Sikandra",
            "panchayats": ["Sikandra", "Bharwaliya", "Khaira", "Chakai", "Sono"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Khaira",
            "panchayats": ["Khaira", "Chakai", "Jamui", "Gidhour"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Chakai",
            "panchayats": ["Chakai", "Khaira", "Jamui", "Barhat"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Sono",
            "panchayats": ["Sono", "Laxmipur", "Jhajha", "Gidhour"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Laxmipur",
            "panchayats": ["Laxmipur", "Barhat", "Jhajha", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Jhajha",
            "panchayats": ["Jhajha", "Barhat", "Gidhour", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Barhat",
            "panchayats": ["Barhat", "Jhajha", "Gidhour", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Gidhour",
            "panchayats": ["Gidhour", "Jhajha", "Barhat", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Islamnagar Aliganj",
            "panchayats": ["Islamnagar Aliganj", "Gidhour", "Barhat", "Jhajha"]
        },
        
        
        {
            "district_name": "Jehanabad",
            "block_name": "Jehanabad",
            "panchayats": ["Jehanabad", "Kachhiyar", "Barkagaon", "Fatuha", "Sukhi"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Makhdumpur",
            "panchayats": ["Makhdumpur", "Daukar", "Gopalpur", "Arajpura"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Ghosi",
            "panchayats": ["Ghosi", "Nawada", "Sukhpura", "Barhampur"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Hulasganj",
            "panchayats": ["Hulasganj", "Barharwa", "Saraiya", "Rampur"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Ratni Faridpur",
            "panchayats": ["Ratni", "Faridpur", "Kamlapur", "Sultanganj"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Modanganj",
            "panchayats": ["Modanganj", "Bhagwanpur", "Bachhwara", "Barai"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Kako",
            "panchayats": ["Kako", "Belwa", "Chakbhabani", "Naugarh"]
        },
        
        
        {
            "district_name": "Kaimur",
            "block_name": "Adhaura",
            "panchayats": ["Adhaura", "Katahariya", "Chakari", "Rampur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Bhabua",
            "panchayats": ["Bhabua", "Kalyanpur", "Gahmar", "Rajpur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Bhagwanpur",
            "panchayats": ["Bhagwanpur", "Chauki", "Chakradharpur", "Sukari"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Chainpur",
            "panchayats": ["Chainpur", "Nautan", "Chakaria", "Belwa"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Chand",
            "panchayats": ["Chand", "Rampur", "Maharajganj", "Sukahi"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Rampur",
            "panchayats": ["Rampur", "Karhi", "Bhagwanpur", "Beldar"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Durgawati",
            "panchayats": ["Durgawati", "Chainpur", "Bhelwara", "Rampur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Kudra",
            "panchayats": ["Kudra", "Patna", "Chakari", "Barauli"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Mohania",
            "panchayats": ["Mohania", "Gamharia", "Rampur", "Barauli"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Nuaon",
            "panchayats": ["Nuaon", "Chak", "Rampur", "Belwa"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Ramgarh",
            "panchayats": ["Ramgarh", "Rampur", "Chakra", "Sukahi"]
        },
        
        
        {
            "district_name": "Katihar",
            "block_name": "Katihar",
            "panchayats": ["Katihar Sadar", "Chhota Gamharia", "Puraini", "Sundarpur", "Balua", "Kharhara", "Rajpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Barsoi",
            "panchayats": ["Barsoi", "Sahibganj", "Bhurkunda", "Baksara", "Jamalpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Manihari",
            "panchayats": ["Manihari", "Sikandarpur", "Gopi Bigha", "Rampur", "Chakuli"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Falka",
            "panchayats": ["Falka", "Bhurkunda", "Dhamdaha", "Beldaur", "Jalalpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Kadwa",
            "panchayats": ["Kadwa", "Chakki", "Rampur", "Sikandarpur", "Mahadeopur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Kursela",
            "panchayats": ["Kursela", "Baksara", "Chhapra", "Belwa", "Gajha"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Hasanganj",
            "panchayats": ["Hasanganj", "Rampur", "Chakuli", "Puraini", "Sikandarpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Sameli",
            "panchayats": ["Sameli", "Chhapra", "Rampur", "Beldaur", "Bhagwanpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Pranpur",
            "panchayats": ["Pranpur", "Rampur", "Chakuli", "Baksara", "Belwa"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Korha",
            "panchayats": ["Korha", "Rampur", "Belwa", "Chakuli", "Sameli"]
        },
        
        
        {
            "district_name": "Khagaria",
            "block_name": "Khagaria",
            "panchayats": ["Khagaria Sadar", "Pachkuli", "Bhagwanpur", "Kothia", "Rampur"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Beldaur",
            "panchayats": ["Beldaur", "Chakparan", "Bariarpur", "Rajpur", "Gopalpur"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Parbatta",
            "panchayats": ["Parbatta", "Barhampur", "Chakua", "Rampur", "Kothi"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Bariyarpur", "Rampur", "Chakuli", "Belwa"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Chautham",
            "panchayats": ["Chautham", "Rampur", "Bhagwanpur", "Baksara", "Belwa"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Mansi",
            "panchayats": ["Mansi", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Gogri",
            "panchayats": ["Gogri", "Rampur", "Chakuli", "Belwa", "Sameli"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Simri Bakhtiyarpur",
            "panchayats": ["Simri Bakhtiyarpur", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        
        
        {
            "district_name": "Kishanganj",
            "block_name": "Kishanganj",
            "panchayats": ["Kishanganj Sadar", "Jagdishpur", "Haripur", "Rampur", "Belwa"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Bahadurganj",
            "panchayats": ["Bahadurganj", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Dighalbank",
            "panchayats": ["Dighalbank", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Thakurganj",
            "panchayats": ["Thakurganj", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Goalpokhar",
            "panchayats": ["Goalpokhar", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Islampur",
            "panchayats": ["Islampur", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        
            
        {
            "district_name": "Lakhisarai",
            "block_name": "Lakhisarai",
            "panchayats": ["Lakhisarai Sadar", "Bhatpur", "Rampur", "Chhatwan", "Nawanagar"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Ramgarh Chowk",
            "panchayats": ["Ramgarh Chowk", "Siyalchak", "Chakbahadur", "Kumhar", "Bhagwanpur"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Surajgarha",
            "panchayats": ["Surajgarha", "Chakmohammad", "Mohanpur", "Rampur", "Ghoramara"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Barahiya",
            "panchayats": ["Barahiya", "Chandan", "Kailashganj", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Chanan",
            "panchayats": ["Chanan", "Rampur", "Chakbahadur", "Siyalchak", "Bhagwanpur"]
        },
        

        {
        
            "district_name": "Madhepura",
            "block_name": "Madhepura",
            "panchayats": ["Madhepura Sadar", "Bhawanipur", "Rampur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Kumargram",
            "panchayats": ["Kumargram", "Chakdah", "Rampur", "Bhawanipur", "Chhatarpur"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Singheshwar",
            "panchayats": ["Singheshwar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Murliganj",
            "panchayats": ["Murliganj", "Rampur", "Chakbahadur", "Bhawanipur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Gopalpur",
            "panchayats": ["Gopalpur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Udaipur",
            "panchayats": ["Udaipur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Alamnagar",
            "panchayats": ["Alamnagar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Shankarpur",
            "panchayats": ["Shankarpur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Madhepura Sadar",
            "panchayats": ["Madhepura Sadar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        
        
        {
            "district_name": "Madhubani",
            "block_name": "Andhratharhi",
            "panchayats": ["Andhratharhi", "Chhota Babhani", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Babubarhi",
            "panchayats": ["Babubarhi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Basopatti",
            "panchayats": ["Basopatti", "Rampur", "Bhawanipur", "Chakbahadur"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Benipatti",
            "panchayats": ["Benipatti", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Bisfi",
            "panchayats": ["Bisfi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Ghoghardiha",
            "panchayats": ["Ghoghardiha", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Harlakhi",
            "panchayats": ["Harlakhi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Jhanjharpur",
            "panchayats": ["Jhanjharpur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Kaluahi",
            "panchayats": ["Kaluahi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Khajauli",
            "panchayats": ["Khajauli", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Ladania",
            "panchayats": ["Ladania", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Laukahi",
            "panchayats": ["Laukahi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Madhepur",
            "panchayats": ["Madhepur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Madhwapur",
            "panchayats": ["Madhwapur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Pandaul",
            "panchayats": ["Pandaul", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Phulparas",
            "panchayats": ["Phulparas", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Rajnagar",
            "panchayats": ["Rajnagar", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Sakri",
            "panchayats": ["Sakri", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Shankarpur",
            "panchayats": ["Shankarpur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Tardih",
            "panchayats": ["Tardih", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Lakhnaur",
            "panchayats": ["Lakhnaur", "Rampur", "Bhawanipur", "Chhata"]
        },
        
                
        {
            "district_name": "Munger",
            "block_name": "Munger Sadar",
            "panchayats": ["Munger Sadar", "Gunjaria", "Jorhat", "Chakmoh"]
        },
        {
            "district_name": "Munger",
            "block_name": "Bariyarpur",
            "panchayats": ["Bariyarpur", "Chakla", "Parsa", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Chandan",
            "panchayats": ["Chandan", "Sikta", "Barauli", "Gajni"]
        },
        {
            "district_name": "Munger",
            "block_name": "Sangrampur",
            "panchayats": ["Sangrampur", "Bhagwanpur", "Chhitauni", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Tarapur",
            "panchayats": ["Tarapur", "Paharpur", "Chakbigha", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Jamalpur",
            "panchayats": ["Jamalpur", "Chakgawan", "Bhawanipur", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Kharagpur",
            "panchayats": ["Kharagpur", "Chakra", "Rampur", "Barauli"]
        },
        {
            "district_name": "Munger",
            "block_name": "Hathidah",
            "panchayats": ["Hathidah", "Chakmoh", "Rampur", "Bhawanipur"]
        },
        

        
        {
            "district_name": "Muzaffarpur",
            "block_name": "Muzaffarpur Sadar",
            "panchayats": ["Muzaffarpur Sadar", "Kohra", "Sahibganj", "Barauli", "Bhagwanpur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Musahari",
            "panchayats": ["Musahari", "Chakna", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Marwan",
            "panchayats": ["Marwan", "Barauli", "Chakla", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Bochahan",
            "panchayats": ["Bochahan", "Bhawanipur", "Chakmoh", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Katra",
            "panchayats": ["Katra", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Saraiya",
            "panchayats": ["Saraiya", "Rampur", "Chakmoh", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Paroo",
            "panchayats": ["Paroo", "Chakra", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Sakra",
            "panchayats": ["Sakra", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Gorhara",
            "panchayats": ["Gorhara", "Rampur", "Bhawanipur", "Chakmoh"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Motipur",
            "panchayats": ["Motipur", "Chakra", "Barauli", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Barahiya",
            "panchayats": ["Barahiya", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Minapur",
            "panchayats": ["Minapur", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Meenapur",
            "panchayats": ["Meenapur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Aurai",
            "panchayats": ["Aurai", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Piprahi",
            "panchayats": ["Piprahi", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        
        
        {
            "district_name": "Nalanda",
            "block_name": "Bihar Sharif",
            "panchayats": ["Bihar Sharif", "Rampur", "Barhampur", "Chakla", "Sultanpur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Rajgir",
            "panchayats": ["Rajgir", "Bhawanipur", "Rampur", "Chakmoh"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Harnaut",
            "panchayats": ["Harnaut", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Islampur",
            "panchayats": ["Islampur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Hilsa",
            "panchayats": ["Hilsa", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Noorsarai",
            "panchayats": ["Noorsarai", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Ekangarsarai",
            "panchayats": ["Ekangarsarai", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Asthawan",
            "panchayats": ["Asthawan", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Katri",
            "panchayats": ["Katri", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Silao",
            "panchayats": ["Silao", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Nalanda Sadar",
            "panchayats": ["Nalanda Sadar", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Nawada",
            "block_name": "Nawada Sadar",
            "panchayats": ["Nawada Sadar", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Akbarpur",
            "panchayats": ["Akbarpur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Narhat",
            "panchayats": ["Narhat", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Pakribarawan",
            "panchayats": ["Pakribarawan", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Hisua",
            "panchayats": ["Hisua", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Warisaliganj",
            "panchayats": ["Warisaliganj", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Kawakol",
            "panchayats": ["Kawakol", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Roh",
            "panchayats": ["Roh", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Rajauli",
            "panchayats": ["Rajauli", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Patna",
            "block_name": "Patna Sadar",
            "panchayats": ["Patna Sadar", "Rampur", "Chakmoh", "Khalilpur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Daniyaw",
            "panchayats": ["Daniyaw", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Bakhtiyarpur",
            "panchayats": ["Bakhtiyarpur", "Rampur", "Chakmoh", "Saraiya"]
        },
        {
            "district_name": "Patna",
            "block_name": "Fatuha",
            "panchayats": ["Fatuha", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Paliganj",
            "panchayats": ["Paliganj", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Danapur",
            "panchayats": ["Danapur", "Rampur", "Chakla", "Kharika"]
        },
        {
            "district_name": "Patna",
            "block_name": "Maner",
            "panchayats": ["Maner", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Naubatpur",
            "panchayats": ["Naubatpur", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Sampatchak",
            "panchayats": ["Sampatchak", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Masaurhi",
            "panchayats": ["Masaurhi", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Khusrupur",
            "panchayats": ["Khusrupur", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Bihta",
            "panchayats": ["Bihta", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Punpun",
            "panchayats": ["Punpun", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Barh",
            "panchayats": ["Barh", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Phulwari",
            "panchayats": ["Phulwari", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Dhanarua",
            "panchayats": ["Dhanarua", "Rampur", "Chakla", "Barauli"]
        },
        
        
        {
            "district_name": "Purnia",
            "block_name": "Purnia Sadar",
            "panchayats": ["Purnia Sadar", "Rampur", "Chakla", "Murliganj", "Banmankhi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Banmankhi",
            "panchayats": ["Banmankhi", "Rampur", "Chakla", "Baisi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Dhamdaha",
            "panchayats": ["Dhamdaha", "Rampur", "Chakla", "Rupauli"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Rupauli",
            "panchayats": ["Rupauli", "Rampur", "Chakla", "Baisi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Baisi",
            "panchayats": ["Baisi", "Rampur", "Chakla", "Banmankhi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Kasba",
            "panchayats": ["Kasba", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Bhawanipur",
            "panchayats": ["Bhawanipur", "Rampur", "Chakla", "Barhara Kothi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Barhara Kothi",
            "panchayats": ["Barhara Kothi", "Rampur", "Chakla", "Sukhasan"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Sukhasan",
            "panchayats": ["Sukhasan", "Rampur", "Chakla", "Amour"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Amour",
            "panchayats": ["Amour", "Rampur", "Chakla", "Krityanand Nagar"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Krityanand Nagar",
            "panchayats": ["Krityanand Nagar", "Rampur", "Chakla", "Jalalgarh"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Jalalgarh",
            "panchayats": ["Jalalgarh", "Rampur", "Chakla", "Bhagalpur"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Bhagalpur",
            "panchayats": ["Bhagalpur", "Rampur", "Chakla", "Purnia City"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Purnia City",
            "panchayats": ["Purnia City", "Rampur", "Chakla", "Purnia Sadar"]
        },
        
        
        {
            "district_name": "Rohtas",
            "block_name": "Rohtas Sadar",
            "panchayats": ["Rohtas Sadar", "Barauli", "Chandpur", "Bikramganj", "Dehri"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Sasaram",
            "panchayats": ["Sasaram", "Kashwan", "Chitbara Gaon", "Karbasawan"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Nokha",
            "panchayats": ["Nokha", "Dumri", "Khirkiya", "Chakia"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Dehri",
            "panchayats": ["Dehri", "Chakai", "Akrua", "Dumari"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Akbarpur",
            "panchayats": ["Akbarpur", "Rajpur", "Chunarughat", "Tilouthu"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Nauhatta",
            "panchayats": ["Nauhatta", "Chakla", "Rajpur", "Dumraon"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Rajpur",
            "panchayats": ["Rajpur", "Tilouthu", "Chand", "Sasaram"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Chenari",
            "panchayats": ["Chenari", "Karbasawan", "Bhabhua", "Chakia"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Tilouthu",
            "panchayats": ["Tilouthu", "Rajpur", "Akbarpur", "Rohtas Sadar"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Dumraon",
            "panchayats": ["Dumraon", "Nokha", "Sasaram", "Chakla"]
        },
        
        
        {
            "district_name": "Saharsa",
            "block_name": "Saharsa Sadar",
            "panchayats": ["Saharsa Sadar", "Bachhwara", "Kothia", "Bajitpur", "Gamhariya"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Mahishi",
            "panchayats": ["Mahishi", "Banwaria", "Barari", "Mahisar"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Simri Bakhtiyarpur",
            "panchayats": ["Simri Bakhtiyarpur", "Nagar", "Parsauni", "Bapudih"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Sonbarsa",
            "panchayats": ["Sonbarsa", "Belha", "Rampur", "Chandwara"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Madhepur",
            "panchayats": ["Madhepur", "Sakra", "Kothia", "Bachhwara"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Pipra",
            "panchayats": ["Pipra", "Kosi", "Bajitpur", "Narayanpur"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Salkhua",
            "panchayats": ["Salkhua", "Rampur", "Chakla", "Bapudih"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Patarghat",
            "panchayats": ["Patarghat", "Belha", "Mahisham", "Rampur"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Alamnagar",
            "panchayats": ["Alamnagar", "Kothia", "Banwaria", "Rampur"]
        },
        
        
        {
            "district_name": "Samastipur",
            "block_name": "Samastipur Sadar",
            "panchayats": ["Samastipur Sadar", "Dighalbank", "Kachharauli", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Ujiarpur",
            "panchayats": ["Ujiarpur", "Barauli", "Bhawanipur", "Chakuli"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Morwa",
            "panchayats": ["Morwa", "Mahishi", "Rampur", "Sakra"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Sarairanjan",
            "panchayats": ["Sarairanjan", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Warisnagar",
            "panchayats": ["Warisnagar", "Barauli", "Maheshpur", "Rampur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Kalyanpur",
            "panchayats": ["Kalyanpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Dalsinghsarai",
            "panchayats": ["Dalsinghsarai", "Barauli", "Rampur", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Patori",
            "panchayats": ["Patori", "Barauli", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Vidyapati Nagar",
            "panchayats": ["Vidyapati Nagar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Tajpur",
            "panchayats": ["Tajpur", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Makhdumpur",
            "panchayats": ["Makhdumpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Musrigharari",
            "panchayats": ["Musrigharari", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Shivajinagar",
            "panchayats": ["Shivajinagar", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Goriakothi",
            "panchayats": ["Goriakothi", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Saran",
            "block_name": "Chapra Sadar",
            "panchayats": ["Chapra Sadar", "Chhapra Bazar", "Rampur", "Belha"]
        },
        {
            "district_name": "Saran",
            "block_name": "Marhaura",
            "panchayats": ["Marhaura", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Dighwara",
            "panchayats": ["Dighwara", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Parsa",
            "panchayats": ["Parsa", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Sonpur",
            "panchayats": ["Sonpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Saran",
            "block_name": "Garkha",
            "panchayats": ["Garkha", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Amnour",
            "panchayats": ["Amnour", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Dariapur",
            "panchayats": ["Dariapur", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Taraiya",
            "panchayats": ["Taraiya", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Manjhi",
            "panchayats": ["Manjhi", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Sonepur",
            "panchayats": ["Sonepur", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Masrakh",
            "panchayats": ["Masrakh", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Parsauni",
            "panchayats": ["Parsauni", "Rampur", "Belha", "Chakla"]
        },
        
        
        {
            "district_name": "Sheikhpura",
            "block_name": "Sheikhpura Sadar",
            "panchayats": ["Sheikhpura Sadar", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Chewara",
            "panchayats": ["Chewara", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Ariari",
            "panchayats": ["Ariari", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Barbigha",
            "panchayats": ["Barbigha", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Pirpainti",
            "panchayats": ["Pirpainti", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Sheikhpura",
            "panchayats": ["Sheikhpura", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Nathnagar",
            "panchayats": ["Nathnagar", "Rampur", "Belha", "Chakla"]
        },
        
        
        {
            "district_name": "Sheohar",
            "block_name": "Sheohar Sadar",
            "panchayats": ["Sheohar Sadar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Purnahiya",
            "panchayats": ["Purnahiya", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Dumri Katsari",
            "panchayats": ["Dumri Katsari", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Piprarhi",
            "panchayats": ["Piprarhi", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Mehsi",
            "panchayats": ["Mehsi", "Chakla", "Rampur", "Belha"]
        },
        
        
        {
            "district_name": "Sitamarhi",
            "block_name": "Sitamarhi Sadar",
            "panchayats": ["Sitamarhi Sadar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Belsand",
            "panchayats": ["Belsand", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bajpatti",
            "panchayats": ["Bajpatti", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Choraut",
            "panchayats": ["Choraut", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bathnaha",
            "panchayats": ["Bathnaha", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Suppi",
            "panchayats": ["Suppi", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Riga",
            "panchayats": ["Riga", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Runnisaidpur",
            "panchayats": ["Runnisaidpur", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Pupri",
            "panchayats": ["Pupri", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Sursand",
            "panchayats": ["Sursand", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bairgania",
            "panchayats": ["Bairgania", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Nanpur",
            "panchayats": ["Nanpur", "Chakla", "Rampur", "Belha"]
        },
        
        
        {
            "district_name": "Siwan",
            "block_name": "Siwan Sadar",
            "panchayats": ["Siwan Sadar", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Barharia",
            "panchayats": ["Barharia", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Bhagwanpur Hat",
            "panchayats": ["Bhagwanpur Hat", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Daraundha",
            "panchayats": ["Daraundha", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Goriakothi",
            "panchayats": ["Goriakothi", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Guthani",
            "panchayats": ["Guthani", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Hussainganj",
            "panchayats": ["Hussainganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Lakri Nabiganj",
            "panchayats": ["Lakri Nabiganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Maharajganj",
            "panchayats": ["Maharajganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Nautan",
            "panchayats": ["Nautan", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Pachrukhi",
            "panchayats": ["Pachrukhi", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Raghunathpur",
            "panchayats": ["Raghunathpur", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Mairwa",
            "panchayats": ["Mairwa", "Chakari", "Rampur", "Maheshpur"]
        },
        
        
        {
            "district_name": "Vaishali",
            "block_name": "Hajipur",
            "panchayats": ["Hajipur", "Chaksikandar", "Bidupur", "Mahua"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Lalganj",
            "panchayats": ["Lalganj", "Saraiya", "Bigha", "Raghunathpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Mahua",
            "panchayats": ["Mahua", "Mahammadpur", "Khesraha", "Sikandarpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Mahnar",
            "panchayats": ["Mahnar", "Barauli", "Chakhandi", "Bharawan"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Patepur",
            "panchayats": ["Patepur", "Chaksikandar", "Gokulpur", "Basantpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Rajapakar",
            "panchayats": ["Rajapakar", "Chakandarpur", "Katauli", "Kanchanpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Bidupur",
            "panchayats": ["Bidupur", "Mahua", "Chaksikandar", "Paterpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Chehrakala",
            "panchayats": ["Chehrakala", "Dighari", "Mahmoodpur", "Barauli"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Desari",
            "panchayats": ["Desari", "Barauli", "Chakandarpur", "Katauli"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Goraul",
            "panchayats": ["Goraul", "Basantpur", "Chaksikandar", "Mahua"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Jandaha",
            "panchayats": ["Jandaha", "Mahnar", "Barauli", "Chakhandi"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Sahdei Buzurg",
            "panchayats": ["Sahdei Buzurg", "Chaksikandar", "Mahammadpur", "Raghunathpur"]
        },
        
                
        {
            "district_name": "Forbesganj",
            "block_name": "Forbesganj",
            "panchayats": ["Forbesganj", "Araria Basti", "Bahgi Pokharia", "Belbari Araria Basti", "Bansbari Bansbari", "Barakamatchistipur Haria"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Araria",
            "panchayats": ["Araria Basti", "Azamnagar Kusiyar Gawon", "Azmatpur Basantpur", "Bahgi Pokharia", "Bairgachhi Belwa"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Bhargama",
            "panchayats": ["Bhargama", "Bairgachhi", "Bangawan", "Belsandi", "Belwa"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Raniganj",
            "panchayats": ["Raniganj", "Chakorwa", "Dahrahra", "Damiya", "Dargahiganj"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Palasi",
            "panchayats": ["Palasi", "Fatehpur", "Gadhgawan", "Gandhi", "Gangauli"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Sikti",
            "panchayats": ["Sikti", "Ganj", "Gogri", "Gopalpur", "Baturbari"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Jokihat",
            "panchayats": ["Jokihat", "Bhadwar", "Bhairoganj", "Bhawanipur", "Bhanghi"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Kursakatta",
            "panchayats": ["Kursakatta", "Dombana", "Dumari", "Fatehpur", "Gadhgawan"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Narpatganj",
            "panchayats": ["Narpatganj", "Nabinagar", "Obra", "Rafiganj", "Haspura"]
        }
    
        

    ]


    # -----------------------
    # Jharkhand districts + blocks
    # -----------------------
    jharkhand_locations = [
        {
            "district_name": "Bokaro",
            "block_name": "Bermo",
            "panchayats": ["Bermo", "Tetulmari", "Barmasia", "Jaridih", "Karo"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chas",
            "panchayats": ["Chas", "Chandrapura", "Bandhgora", "Bermo", "Tetulmari"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chandankiyari",
            "panchayats": ["Chandankiyari", "Kundri", "Jhalda", "Panchbaria", "Nawadih"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chandrapura",
            "panchayats": ["Chandrapura", "Gomia", "Bermo", "Chas", "Tetulmari"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Gomia",
            "panchayats": ["Gomia", "Chandrapura", "Bermo", "Kasmar", "Nawadih"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Jaridih",
            "panchayats": ["Jaridih", "Bermo", "Chas", "Tetulmari", "Barmasia"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Kasmar",
            "panchayats": ["Kasmar", "Gomia", "Chandankiyari", "Bermo", "Petarwar"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Nawadih",
            "panchayats": ["Nawadih", "Chandankiyari", "Gomia", "Kasmar", "Bermo"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Petarwar",
            "panchayats": ["Petarwar", "Kasmar", "Gomia", "Nawadih", "Chandankiyari"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Chatra",
            "panchayats": ["Chatra", "Chhatarpur", "Bhaupur", "Patratu", "Bhaluadih"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Hunterganj",
            "panchayats": ["Hunterganj", "Dhauraiya", "Pipra", "Chandwa", "Kalyanpur"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Itkhori",
            "panchayats": ["Itkhori", "Kundru", "Lohardaga", "Bagodar", "Sadar Itkhori"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Kunda",
            "panchayats": ["Kunda", "Chirgaon", "Bhelwadih", "Kundru", "Barachatti"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Lawalong",
            "panchayats": ["Lawalong", "Birsanagar", "Chakradih", "Barauli", "Simaria"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Mayurhand",
            "panchayats": ["Mayurhand", "Ratanpur", "Pipra", "Sundarpur", "Harhar"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Pathalgora",
            "panchayats": ["Pathalgora", "Sadar Pathalgora", "Kumradih", "Kumra", "Badiya"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Pratappur",
            "panchayats": ["Pratappur", "Mugma", "Bokaro", "Sadar Pratappur", "Chhota Pratappur"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Simaria",
            "panchayats": ["Simaria", "Bara Simaria", "Chhota Simaria", "Bagha", "Paharpur"]
        },
        {
            "district_name": "Chatra",
            "block_name": "Tandwa",
            "panchayats": ["Tandwa", "Chhota Tandwa", "Bara Tandwa", "Kumardih", "Bari Tandwa"]
        },
        
        
        {
            "district_name": "Deoghar",
            "block_name": "Deoghar",
            "panchayats": ["Deoghar Sadar", "Bardih", "Bangaon", "Barhara", "Kundahit", "Bagodar"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Devipur",
            "panchayats": ["Devipur", "Kushma", "Kheria", "Bara Devipur", "Chhota Devipur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Madhupur",
            "panchayats": ["Madhupur Sadar", "Sakri", "Radhanagar", "Chhota Madhupur", "Bara Madhupur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Mohanpur",
            "panchayats": ["Mohanpur", "Bara Mohanpur", "Chhota Mohanpur", "Tilhar", "Paharpur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Palojori",
            "panchayats": ["Palojori", "Bara Palojori", "Chhota Palojori", "Rampur", "Bhurkunda"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Sarath",
            "panchayats": ["Sarath", "Bara Sarath", "Chhota Sarath", "Bagodar", "Rasikpur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Sonaraithari",
            "panchayats": ["Sonaraithari", "Bara Sonaraithari", "Chhota Sonaraithari", "Rampur", "Chakla"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Margomunda",
            "panchayats": ["Margomunda", "Bara Margomunda", "Chhota Margomunda", "Paharpur", "Sundarpur"]
        },
        {
            "district_name": "Deoghar",
            "block_name": "Karon",
            "panchayats": ["Karon", "Bara Karon", "Chhota Karon", "Rampur", "Baghar"]
        },
        
       
    

        {
            "district_name": "Dumka",
            "block_name": "Dumka",
            "panchayats": ["Dumka Sadar", "Sanjhariya", "Ramnagar", "Chopadih", "Bhaluadih"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Jarmundi",
            "panchayats": ["Jarmundi", "Tilma", "Chilla", "Karmatanr", "Saraiya"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Jama",
            "panchayats": ["Jama", "Barahat", "Nandni", "Sahibganj", "Bishunpur"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Kathikund",
            "panchayats": ["Kathikund", "Rampur", "Karia", "Chandrapur", "Sundarpur"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Masalia",
            "panchayats": ["Masalia", "Bara Masalia", "Chhota Masalia", "Ramnagar", "Baghar"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Ramgarh",
            "panchayats": ["Ramgarh", "Bara Ramgarh", "Chhota Ramgarh", "Chopadih", "Saraiya"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Ranishwar",
            "panchayats": ["Ranishwar", "Bara Ranishwar", "Chhota Ranishwar", "Rampur", "Bhaluadih"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Saraiyahat",
            "panchayats": ["Saraiyahat", "Bara Saraiyahat", "Chhota Saraiyahat", "Ramnagar", "Baghar"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Shikaripara",
            "panchayats": ["Shikaripara", "Bara Shikaripara", "Chhota Shikaripara", "Rampur", "Chopadih"]
        },
        {
            "district_name": "Dumka",
            "block_name": "Gopikandar",
            "panchayats": ["Gopikandar", "Bara Gopikandar", "Chhota Gopikandar", "Ramnagar", "Baghar"]
        },
        
        
        
    ]
    # State options for dropdown
    states = ["Bihar", "Jharkhand"]

    # Districts for default display (Bihar by default)
    districts = [loc['district_name'] for loc in bihar_locations]

    if request.method == 'POST':
        location_level = request.POST.get('location_level')
        form = UserForm(request.POST, request.FILES, location_level=location_level)

        if form.is_valid():
            member = form.save(commit=False)
            password = form.cleaned_data.get('password')

            if not password:
                password = generate_random_password()
                messages.success(request, f"Member added. Auto-generated password: {password}")
            else:
                messages.success(request, "Member added successfully.")

            # Save hashed password for login
            member.set_password(password)

            # Save plain password for manage page display
            member.plain_password = password  # <-- Add this line

            # ✅ Yaha assigned_state set karo agar blank hai
            if not member.assigned_state:
                member.assigned_state = member.state

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

                # Select correct location list
                locations_list = bihar_locations if state_name == "Bihar" else jharkhand_locations

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
                return render(request, 'core/admin/add_state_member.html', {
                    'form': form,
                    'states': states,
                    'districts': districts,
                    'bihar_locations': bihar_locations,
                    'jharkhand_locations': jharkhand_locations
                })
            except ValueError as e:
                messages.error(request, str(e))
                return render(request, 'core/admin/add_state_member.html', {
                    'form': form,
                    'states': states,
                    'districts': districts,
                    'bihar_locations': bihar_locations,
                    'jharkhand_locations': jharkhand_locations
                })

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
        'states': states,
        'districts': districts,
        'bihar_locations': bihar_locations,
        'jharkhand_locations': jharkhand_locations
    })

@superuser_required
def manage_state_member(request):
    state_roles = Role.objects.filter(role_name__startswith='State')

    # Unique states (only Bihar & Jharkhand)
    states = ["Bihar", "Jharkhand"]

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

    # States, districts, blocks
    states = [
        {
            "name": "Bihar",
            "districts": [
            {"name": "Araria", "blocks": ["Araria", "Forbesganj", "Jokihat", "Kursakatta", "Narpatganj"]},
            {"name": "Arwal", "blocks": ["Arwal", "Obra", "Kaler"]},
            {"name": "Aurangabad", "blocks": ["Aurangabad", "Barun", "Daudnagar", "Obra", "Kutumbba"]},
            {"name": "Banka", "blocks": ["Banka", "Amarpur", "Dhoraiya", "Katoria", "Belhar", "Shambhuganj", "Barahat"]},
            {"name": "Begusarai", "blocks": ["Begusarai", "Barauni", "Teghra", "Bakhri", "Gidhaur", "Birpur"]},
            {"name": "Bhagalpur", "blocks": ["Bhagalpur Sadar", "Nathnagar", "Sabour", "Kahalgaon", "Pirpainti"]},
            {"name": "Bhojpur", "blocks": ["Arrah", "Jagdishpur", "Piro", "Bihiya", "Koilwar", "Agiaon"]},
            {"name": "Buxar", "blocks": ["Buxar", "Chausa", "Dumraon", "Rajpur", "Sikandarpur", "Nawanagar"]},
            {"name": "Darbhanga", "blocks": ["Darbhanga Sadar", "Hayaghat", "Keoti", "Bahadurpur", "Alinagar", "Benipur"]},
            {"name": "Gaya", "blocks": ["Gaya Sadar", "Barachatti", "Tekari", "Sherghati", "Bodh Gaya"]},
            {"name": "Gopalganj", "blocks": ["Gopalganj", "Manjha", "Bhore", "Baniyapur", "Ekma", "Garkha"]},
            {"name": "Jamui", "blocks": ["Jamui", "Jhajha", "Chakai", "Gidhaur", "Lachhuar"]},
            {"name": "Jehanabad", "blocks": ["Jehanabad", "Makhdumpur", "Kako", "Hulasganj", "Modanganj"]},
            {"name": "Kaimur (Bhabua)", "blocks": ["Bhabua", "Ramgarh", "Mohania", "Chand"]},
            {"name": "Katihar", "blocks": ["Katihar", "Kishanganj", "Balrampur", "Pranpur", "Manihari"]},
            {"name": "Khagaria", "blocks": ["Khagaria", "Alauli", "Chautham", "Beldaur", "Mansi"]},
            {"name": "Kishanganj", "blocks": ["Kishanganj", "Kochadhaman", "Amour", "Baisi", "Kasba"]},
            {"name": "Lakhisarai", "blocks": ["Lakhisarai", "Sheikhpura", "Chandramandi", "Barbigha"]},
            {"name": "Madhepura", "blocks": ["Madhepura", "Murliganj", "Shankarpur", "Gwalpara", "Singheshwar"]},
            {"name": "Madhubani", "blocks": ["Madhubani", "Jainagar", "Pandaul", "Rahika", "Bisfi", "Benipatti"]},
            {"name": "Munger", "blocks": ["Munger", "Lakhisarai", "Sheikhpura"]},
            {"name": "Muzaffarpur", "blocks": ["Muzaffarpur", "Mushahari", "Kanti", "Motipur", "Paru"]},
            {"name": "Nalanda", "blocks": ["Nalanda", "Rajgir", "Bihar Sharif", "Islampur", "Hilsa", "Harnaut"]},
            {"name": "Nawada", "blocks": ["Nawada", "Hisua", "Akbarpur", "Narhat", "Govindpur"]},
            {"name": "Patna", "blocks": ["Patna Sadar", "Fatuha", "Paliganj", "Masaurhi", "Dhanarua"]},
            {"name": "Purnia", "blocks": ["Purnia", "Kishanganj", "Katihar", "Banmankhi", "Alamnagar"]},
            {"name": "Rohtas", "blocks": ["Rohtas", "Sasaram", "Dehri", "Karakat", "Kargahar"]},
            {"name": "Saran", "blocks": ["Chapra", "Manjhi", "Dighwara", "Rivilganj", "Parsa", "Baniyapur"]},
            {"name": "Sheohar", "blocks": ["Sheohar", "Piprahi", "Dumrikatsari", "Puranhia"]},
            {"name": "Sheikhpura", "blocks": ["Sheikhpura", "Barbigha", "Ghatkusumba", "Chebara"]},
            {"name": "Supaul", "blocks": ["Supaul", "Triveniganj", "Nirmali", "Chhatapur"]},
            {"name": "Vaishali", "blocks": ["Vaishali", "Bidupur", "Goraul", "Raghopur", "Lalganj"]},
            {"name": "West Champaran", "blocks": ["Motihari", "Sugauli", "Harsiddhi", "Pakridayal"]},
            {"name": "East Champaran", "blocks": ["Motihari", "Chakia", "Dhaka", "Harsidhi", "Sugauli"]},
            {"name": "Sitamarhi", "blocks": ["Sitamarhi", "Bairgania", "Runni Saidpur", "Belsand"]},
            {"name": "Siwan", "blocks": ["Siwan", "Goriakothi", "Barharia", "Hussainganj"]},
            {"name": "Supaul", "blocks": ["Supaul", "Triveniganj", "Nirmali", "Chhatapur"]},
            {"name": "Saharsa", "blocks": ["Saharsa", "Sonbarsha", "Simri Bakhtiarpur", "Mahishi"]}
        ]
        },
        {
            "name": "Jharkhand",
            "districts": [
            {"name": "Bokaro", "blocks": ["Bermo", "Bokaro Steel City", "Chas", "Gomia", "Petarwar"]},
            {"name": "Deoghar", "blocks": ["Babhangaon", "Deoghar Sadar", "Madhupur", "Madar"]},
            {"name": "Dhanbad", "blocks": ["Baliapur", "Dhanbad Sadar", "Govindpur", "Jharia", "Topchanchi", "Tundi"]},
            {"name": "Dumka", "blocks": ["Dumka Sadar", "Jarmundi", "Masalia", "Shikaripara"]},
            {"name": "East Singhbhum", "blocks": ["Ghatshila", "Jamshedpur", "Musabani", "Potka"]},
            {"name": "Garhwa", "blocks": ["Bhawanathpur", "Chinia", "Garhwa Sadar", "Palamu"]},
            {"name": "Giridih", "blocks": ["Dumri", "Gawan", "Giridih Sadar", "Jamua"]},
            {"name": "Godda", "blocks": ["Godda Sadar", "Mahagama", "Pathargama", "Poreyahat"]},
            {"name": "Hazaribagh", "blocks": ["Barkatha", "Churchu", "Hazaribagh Sadar", "Katkamsandi"]},
            {"name": "Jamtara", "blocks": ["Jamtara Sadar", "Karmatanr", "Nala"]},
            {"name": "Latehar", "blocks": ["Balumath", "Latehar Sadar", "Manika"]},
            {"name": "Palamu", "blocks": ["Chhatarpur", "Daltonganj", "Medininagar", "Panki"]},
            {"name": "Pakur", "blocks": ["Hiranpur", "Maheshpur", "Pakur Sadar"]},
            {"name": "Ramgarh", "blocks": ["Barkagaon", "Gola", "Mandu", "Ramgarh Sadar"]},
            {"name": "Saraikela-Kharsawan", "blocks": ["Chandil", "Gamharia", "Kharsawan", "Saraikela"]},
            {"name": "Simdega", "blocks": ["Kolebira", "Simdega Sadar", "Thethaitangar"]},
            {"name": "West Singhbhum", "blocks": ["Bandgaon", "Chaibasa", "Majhgaon", "Manoharpur"]},
            {"name": "Jamshedpur", "blocks": ["Jamshedpur East", "Jamshedpur West", "Musabani", "Potka"]},
            {"name": "Ranchi", "blocks": ["Kanke", "Namkum", "Ormanjhi", "Ranchi Sadar", "Silli"]}
        ]
        }
    ]

    if request.method == "POST":
        email = request.POST.get('email')
        if User.objects.filter(email=email).exclude(id=member_id).exists():
            messages.error(request, "Email already exists!")
            return render(request, 'core/admin/edit_state_member.html', {'member': member, 'states': states})

        member.full_name = request.POST.get('full_name')
        member.email = email
        member.state = request.POST.get('state')
        member.district = request.POST.get('district')
        member.block_tehsil_taluka = request.POST.get('block_tehsil_taluka')
        member.permanent_address = request.POST.get('permanent_address', '')
        member.current_address = request.POST.get('current_address', '')
        member.save()

        messages.success(request, "State member updated successfully.")
        return redirect('manage_state_member')

    return render(request, 'core/admin/edit_state_member.html', {
        'member': member,
        'states': states
    })


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
        complaint = get_object_or_404(Complaint, pk=pk)
        complaint.status = 'Accepted'
        complaint.backend_response = 'Accepted'
        complaint.save()
        messages.success(request, 'Complaint accepted successfully.')
    return redirect('state_admin_complaints')


@login_required
def state_complaints_reject(request, pk):
    if request.method == 'POST':
        # send_to check remove kar diya
        complaint = get_object_or_404(Complaint, pk=pk, state=request.user.state)
        complaint.status = 'Rejected'
        complaint.backend_response = 'Rejected'
        complaint.save()
        messages.success(request, 'Complaint rejected.')
    return redirect('state_admin_complaints')


@login_required
def state_complaints_solve(request, pk):
    if request.method == 'POST':
        complaint = get_object_or_404(Complaint, pk=pk, state=request.user.state)
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

    jharkhand_locations = [
        {"district_name": "Bokaro", "block_name": "Bermo, Chandankiyari, Chas, Gomia, Kasmar, Nawadih, Peterwar"},
        {"district_name": "Chatra", "block_name": "Chatra, Hunterganj, Itkhori, Kunda, Lawalong, Mayurhand, Pathalgada, Pratappur, Simaria, Tandwa"},
        {"district_name": "Deoghar", "block_name": "Deoghar, Devipur, Madhupur, Mohanpur, Palojori, Sarath, Sonaraithari, Margomunda, Karon, Sarwan"},
        {"district_name": "Dhanbad", "block_name": "Baghmara, Baliapur, Dhanbad, Govindpur, Nirsa, Tundi, Topchanchi, Egarkund, Jharia"},
        {"district_name": "Dumka", "block_name": "Dumka, Gopikandar, Jama, Jarmundi, Kathikund, Masalia, Ramgarh, Raneshwar, Shikaripara, Saraiyahat"},
        {"district_name": "East Singhbhum", "block_name": "Baharagora, Chakulia, Dhalbhumgarh, Dumaria, Ghatshila, Ghurabandha, Musabani, Patamda, Potka"},
        {"district_name": "Garhwa", "block_name": "Bardiha, Bhawnathpur, Bishunpura, Chinia, Danda, Garhwa, Kandi, Ketar, Majhiaon, Meral, Nagaruntari, Ramna, Ranka, Sagma"},
        {"district_name": "Giridih", "block_name": "Bagodar, Bengabad, Birni, Deori, Dumri, Gandey, Giridih, Gomia, Jamua, Pirtand, Sariya, Tisri"},
        {"district_name": "Godda", "block_name": "Bashant Rai, Boarijor, Godda, Mahagama, Meharma, Pathargama, Poreyahat, Sundarpahari, Thakurgangti"},
        {"district_name": "Gumla", "block_name": "Albert Ekka(Jari), Basia, Bharno, Bishunpur, Chainpur, Dumri, Gumla, Kamdara, Palkot, Raidih, Sisai"},
        {"district_name": "Hazaribagh", "block_name": "Barhi, Barkagaon, Bishnugarh, Churchu, Daru, Hazaribagh, Ichak, Katkamsandi, Keredari, Padma, Katkamsandi"},
        {"district_name": "Jamtara", "block_name": "Fatehpur, Jamtara, Karmatanr, Kundhit, Nala, Narayanpur"},
        {"district_name": "Khunti", "block_name": "Arki, Khunti, Karra, Murhu, Rania, Torpa"},
        {"district_name": "Koderma", "block_name": "Chandwara, Domchanch, Jainagar, Koderma, Markacho, Satgawan"},
        {"district_name": "Latehar", "block_name": "Balumath, Barwadih, Chandwa, Garu, Herhanj, Latehar, Mahuadanr, Manika"},
        {"district_name": "Lohardaga", "block_name": "Bhandra, Kisko, Kuru, Lohardaga, Peshrar, Senha"},
        {"district_name": "Pakur", "block_name": "Amrapara, Hiranpur, Littipara, Maheshpur, Pakur, Pakuria"},
        {"district_name": "Palamu", "block_name": "Bishrampur, Chainpur, Chhatarpur, Hariharganj, Hussainabad, Manatu, Medininagar, Mohammad Ganj, Nawagarh, Panki, Patan, Satbarwa"},
        {"district_name": "Ramgarh", "block_name": "Barkagaon, Dulmi, Gola, Mandu, Patratu, Ramgarh"},
        {"district_name": "Ranchi", "block_name": "Angara, Bedo, Bero, Bundu, Burmu, Chanho, Itki, Kanke, Lapung, Mandar, Namkum, Ormanjhi, Ratu, Silli, Tamar"},
        {"district_name": "Sahebganj", "block_name": "Barhait, Borio, Mandro, Pathna, Rajmahal, Sahebganj, Taljhari, Udhwa"},
        {"district_name": "Saraikela Kharsawan", "block_name": "Chandil, Gamharia, Ichagarh, Kharsawan, Kuchai, Kukru, Nimdih, Rajnagar, Saraikela"},
        {"district_name": "Simdega", "block_name": "Bano, Bolba, Jaldega, Kolebira, Kurdeg, Pakartanr, Simdega, Thethaitangar"},
        {"district_name": "West Singhbhum", "block_name": "Bandgaon, Chakradharpur, Goelkera, Gudri, Khuntpani, Majhgaon, Manoharpur, Noamundi, Sonua, Tonto, Chaibasa Sadar, Jagannathpur, Anandpur"}
    ]

  # -----------------------
    # Locations dict for JS (✅ FIXED)
    # -----------------------
    locations_dict = {"Bihar": {}, "Jharkhand": {}}
    for state, loc_list in {"Bihar": bihar_locations, "Jharkhand": jharkhand_locations}.items():
        for loc in loc_list:
            district = loc["district_name"]
            blocks = [b.strip() for b in loc["block_name"].split(",")]
            locations_dict[state][district] = blocks

    locations_json = json.dumps(locations_dict)

    # -----------------------
    # Insert locations into DB if not exists (✅ FIXED INDENT)
    # -----------------------
    for state, loc_list in {"Bihar": bihar_locations, "Jharkhand": jharkhand_locations}.items():
        for loc in loc_list:
            for block in loc["block_name"].split(","):
                block = block.strip()
                if not Location.objects.filter(state_name=state, district_name=loc["district_name"], block_name=block).exists():
                    Location.objects.create(state_name=state, district_name=loc["district_name"], block_name=block)

    # -----------------------
# GET selected state (for both GET and POST)
# -----------------------
    selected_state = request.POST.get('state') or 'Bihar'
    state_name = selected_state

    # Fetch districts and initialize blocks
    districts = list(Location.objects.filter(state_name=selected_state).values_list('district_name', flat=True).distinct())
    blocks = []  # initially empty, JS will populate based on district selection

    if request.method == "POST":
        username = request.POST.get('username')  # ✅ yaha pehle define karo

        email = request.POST['email']
        
            # -----------------------
        # Username duplicate check (NEW ✅)
        # -----------------------
        if User.objects.filter(username=username).exists():
            messages.error(request, "This username is already taken. Please choose another one.")
            return render(request, 'core/admin/add_district_member.html', {
                'roles': roles,
                'roles_json': roles_json,
                'districts': districts,
                'blocks': blocks,
                'generated_password': request.POST.get('password', ''),
                'locations_json': locations_json,
                'state_name': selected_state
            })


        # Email duplicate check
        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, 'core/admin/add_district_member.html', {
                'roles': roles,
                'roles_json': roles_json,
                'districts': districts,
                'blocks': blocks,
                'generated_password': request.POST.get('password', ''),
                'locations_json': locations_json,
                'state_name': selected_state
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
                    'roles': roles,
                    'roles_json': roles_json,
                    'districts': districts,
                    'blocks': blocks,
                    'generated_password': request.POST.get('password', ''),
                    'locations_json': locations_json,
                    'state_name': selected_state
                })

        district_name = request.POST.get('district')
        if not district_name:
            messages.error(request, "Please provide the district name.")
            return render(request, 'core/admin/add_district_member.html', {
                'roles': roles,
                'roles_json': roles_json,
                'districts': districts,
                'blocks': blocks,
                'generated_password': request.POST.get('password', ''),
                'locations_json': locations_json,
                'state_name': selected_state
            })

        block_name = request.POST.get('block') or "N/A"

        # -----------------------
        # Location fetch/create safely
        # -----------------------
        location = Location.objects.filter(
            state_name=state_name,
            district_name=district_name,
            block_name=block_name
        ).first()

        if not location:
            location = Location.objects.create(
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
            assigned_blocks=request.POST.get('assigned_block'),
            local_area_knowledge=request.POST.get('local_area_knowledge') == 'Yes',
            political_experience_years=request.POST.get('political_experience_years'),
            is_active='is_active' in request.POST
        )

        # Handle uploaded files
        member.photo = request.FILES.get('photo')
        member.id_proof = request.FILES.get('id_proof')

        member.set_password(password)
        member.plain_password = password  

        member.save()

        messages.success(request, f"District member added successfully. Generated password: {password}")
        return redirect('manage_district_member')

    # -----------------------
    # GET request
    # -----------------------
    generated_password = generate_random_password()
    return render(request, 'core/admin/add_district_member.html', {
        'roles': roles,
        'roles_json': roles_json,
        'districts': districts,
        'blocks': blocks,
        'generated_password': generated_password,
        'locations_json': locations_json,
        'state': selected_state
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




import json

@superuser_required
def manage_district_member(request):
    members = User.objects.filter(role__level='district').order_by('created_at')

    username = request.GET.get('username')
    state = request.GET.get('state')
    district = request.GET.get('district')

    if username:
        members = members.filter(username__icontains=username)
    if state:
        members = members.filter(state__icontains=state)
    if district:
        members = members.filter(district__icontains=district)

    # States and districts dictionary
    states_and_districts = {
        "Bihar": [
            "Araria","Arwal","Aurangabad","Banka","Begusarai","Bhagalpur","Bhojpur",
            "Buxar","Darbhanga","Gaya","Gopalganj","Jamui","Jehanabad","Kaimur",
            "Katihar","Khagaria","Kishanganj","Lakhisarai","Madhepura","Madhubani",
            "Munger","Muzaffarpur","Nalanda","Nawada","Patna","Purnia","Rohtas",
            "Saharsa","Samastipur","Saran","Sheikhpura","Sheohar","Sitamarhi","Siwan",
            "Vaishali","Forbesganj","Mokama","Bettiah"
        ],
        "Jharkhand": [
            "Ranchi","Bokaro","Dhanbad","Hazaribagh","Jamshedpur","Deoghar","Giridih",
            "Chatra","Garhwa","Gumla","Godda","Khunti","Latehar","Lohardaga","Pakur",
            "Palamu","Ramgarh","Sahebganj","Simdega","West Singhbhum"
        ]
    }

    return render(request, 'core/admin/manage_district_member.html', {
        'members': members,
        'username': username or "",
        'state': state or "",
        'district': district or "",
        'states': list(states_and_districts.keys()),
        'districts': states_and_districts.get(state, []) if state else [],
        'states_and_districts': json.dumps(states_and_districts)  # <-- JSON pass
    })




@superuser_required
def edit_district_member(request, member_id):
    member = get_object_or_404(User, id=member_id)
    roles = Role.objects.all()

    # ----------------------- Bihar Locations -----------------------
    bihar_locations = [
        {"district_name": "Araria", "block_name": "Araria, Bhargama, Forbesganj, Jokihat, Kursakatta, Narpatganj, Palasi, Raniganj, Sikti"},
        {"district_name": "Aurangabad", "block_name": "Aurangabad, Barun, Deo, Goh, Haspura, Kutumba, Madanpur, Nabinagar, Obra, Rafiganj"},
        {"district_name": "Patna", "block_name": "Patna Sadar, Daniyaw, Bakhtiyarpur, Fatuha, Paliganj, Danapur, Maner, Naubatpur, Sampatchak, Masaurhi, Khusrupur, Bihta, Punpun, Barh, Phulwari, Dhanarua"},
        # ... baaki district yaha add karo
    ]

    # ----------------------- Jharkhand Locations -----------------------
    jharkhand_locations = [
        {"district_name": "Deoghar", "block_name": "Deoghar, Mohanpur, Sarath, Palojori, Margomunda, Karon, Madhupur, Devipur, Sonaraithari"},
        {"district_name": "Giridih", "block_name": "Bagodar, Bengabad, Birni, Deori, Dhanwar, Dumri, Gandey, Giridih, Jamua, Pirtand, Sariya, Tisri"},
        {"district_name": "Godda", "block_name": "Bashant Rai, Boarijor, Godda, Mahagama, Meherma, Pathargama, Poraiyahat, Sunderpahari, Thakurgangti"},
        # ... baaki district yaha add karo
    ]

    # ✅ Ab states banayein (bihar/jharkhand ka data use karke)
    states = [
        {"state_name": "Bihar", "districts": bihar_locations},
        {"state_name": "Jharkhand", "districts": jharkhand_locations},
    ]

    if request.method == "POST":
        email = request.POST['email']
        if User.objects.filter(email=email).exclude(id=member_id).exists():
            messages.error(request, "Email already exists.")
            return render(request, 'core/admin/edit_district_member.html', {
                'member': member,
                'roles': roles,
                'states': states
            })

        role_id = request.POST.get('role')
        role = None
        if role_id:
            try:
                role = Role.objects.get(id=role_id)
            except ObjectDoesNotExist:
                messages.error(request, "Selected role does not exist.")
                return render(request, 'core/admin/edit_district_member.html', {
                    'member': member,
                    'roles': roles,
                    'states': states
                })

        member.username = request.POST['username']
        member.email = email
        member.district = request.POST['district']
        member.address = request.POST['address']
        member.role = role
        member.save()

        messages.success(request, "District member updated successfully.")
        return redirect('manage_district_member')

    return render(request, 'core/admin/edit_district_member.html', {
        'member': member,
        'roles': roles,
        'states': states
    })


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

    # -----------------------
    # Bihar locations
    # -----------------------
    bihar_locations = [
        
        {"district_name": "Araria", "block_name": "Araria, Bhargama, Forbesganj, Jokihat, Kursakatta, Narpatganj, Palasi, Raniganj, Sikti"},
        {"district_name": "Arwal", "block_name": "Arwal, Karpi, Kaler, Kurtha, Sonbhadra Banshi Suryapur"},
        {"district_name": "Aurangabad", "block_name": "Aurangabad, Barun, Deo, Goh, Haspura, Kutumba, Madanpur, Nabinagar, Obra, Rafiganj"},
        {"district_name": "Banka", "block_name": "Amarpur, Banka, Barahat, Belhar, Chanan, Dhoraiya, Fullidumar, Katoria, Phulidumar, Rajoun, Shambhuganj"},
        {"district_name": "Begusarai", "block_name": "Bachhwara, Barauni, Begusarai, Bakhri, Bhagwanpur, Birpur, Cheria Bariarpur, Chhorahi, Dandari, Garhpura, Khodawandpur, Mansurchak, Matihani, Naokothi, Sahebpur Kamal, Samho Akha Kurha, Teghra"},
        {"district_name": "Bhagalpur", "block_name": "Bihpur, Gopalpur, Goradih, Ismailpur, Jagdishpur, Kahalgaon, Kharik, Narayanpur, Nathnagar, Pirpainti, Sabour, Sanhoula, Shahkund, Sonhaula"},
        {"district_name": "Bhojpur", "block_name": "Agiaon, Ara Sadar, Barhara, Bihia, Charpokhari, Garhani, Jagdishpur, Koilwar, Piro, Sahar, Sandesh, Shahpur, Tarari, Udwantnagar"},
        {"district_name": "Buxar", "block_name": "Buxar, Brahmpur, Chausa, Chakki, Chaugain, Dumraon, Itarhi, Kesath, Nawanagar, Rajpur, Simri"},
        {"district_name": "Darbhanga", "block_name": "Alinagar, Bahadurpur, Baheri, Benipur, Biraul, Darbhanga Sadar, Ghanshyampur, Hanuman Nagar, Hayaghat, Jale, Keoti, Kusheshwar Asthan, Kusheshwar Asthan Purbi, Manigachhi, Singhwara, Tardih"},
        {"district_name": "Gaya", "block_name": "Atri, Banke Bazar, Barachatti, Belaganj, Bodh Gaya, Dobhi, Fatehpur, Guraru, Gurua, Gaya Town, Imamganj, Khijarsarai, Konch, Manpur, Mohanpur, Neem Chak Bathani, Paraiya, Sherghati, Tankuppa, Wazirganj"},
        {"district_name": "Gopalganj", "block_name": "Baikunthpur, Barauli, Bhorey, Bijaipur, Gopalganj, Hathua, Kuchaikote, Manjha, Panchdeori, Phulwaria, Sidhwalia, Thawe, Uchkagaon"},
        {"district_name": "Jamui", "block_name": "Barhat, Chakai, Gidhaur, Islamnagar Aliganj, Jamui, Jhajha, Khaira, Laxmipur, Sikandra"},
        {"district_name": "Jehanabad", "block_name": "Ghoshi, Hulasganj, Jehanabad, Kako, Makhdumpur, Modanganj, Ratni Faridpur"},
        {"district_name": "Kaimur", "block_name": "Adhaura, Bhagwanpur, Chainpur, Chand, Durgawati, Kudra, Mohania, Rampur, Ramgarh, Bhabhua"},
        {"district_name": "Katihar", "block_name": "Amdabad, Azamnagar, Balrampur, Barari, Dandkhora, Falka, Hasanganj, Kadwa, Katihar, Korha, Kursela, Mansahi, Manihari, Pranpur, Sameli"},
        {"district_name": "Khagaria", "block_name": "Alauli, Beldaur, Chautham, Gogri, Khagaria, Mansi, Parbatta"},
        {"district_name": "Kishanganj", "block_name": "Bahadurganj, Dighalbank, Kochadhaman, Kishanganj, Pothia, Terhagachh, Thakurganj"},
        {"district_name": "Lakhisarai", "block_name": "Barahiya, Chanan, Halsi, Lakhisarai, Pipariya, Ramgarh Chowk, Surajgarha"},
        {"district_name": "Madhepura", "block_name": "Alamnagar, Bihariganj, Chausa, Gamharia, Ghailarh, Kishanganj, Kumarkhand, Madhepura, Murliganj, Puraini, Shankarpur, Singheshwar"},
        {"district_name": "Madhubani", "block_name": "Andhratharhi, Babubarhi, Basopatti, Benipatti, Bisfi, Ghoghardiha, Harlakhi, Jainagar, Jhanjharpur, Khajauli, Ladania, Laukaha, Madhepur, Madhwapur, Pandaul, Phulparas, Rajnagar"},
        {"district_name": "Munger", "block_name": "Asarganj, Bariarpur, Dharhara, Jamalpur, Kharagpur, Munger, Tarapur, Tetiabambar"},
        {"district_name": "Muzaffarpur", "block_name": "Aurai, Bochaha, Gaighat, Kanti, Katara, Kudhani, Kurhani, Minapur, Motipur, Musahari, Paroo, Sakra, Sahebganj, Saraiya"},
        {"district_name": "Nalanda", "block_name": "Asthawan, Ben, Bihar Sharif, Bind, Ekangarsarai, Giriyak, Harnaut, Hilsa, Islampur, Karai Parsurai, Katrisarai, Nagarnausa, Noorsarai, Parbalpur, Rajgir, Silao, Tharthari"},
        {"district_name": "Nawada", "block_name": "Akbarpur, Hisua, Govindpur, Kauwakol, Narhat, Nawada, Pakribarawan, Rajauli, Roh, Sirdala, Warisaliganj"},
        {"district_name": "Patna", "block_name": "Patna Sadar, Daniyaw, Bakhtiyarpur, Fatuha, Paliganj, Danapur, Maner, Naubatpur, Sampatchak, Masaurhi, Khusrupur, Bihta, Punpun, Barh, Phulwari, Dhanarua"},
        {"district_name": "Purnia", "block_name": "Amour, Baisa, Baisi, Banmankhi, Barhara, Bhawanipur, Dagarua, Dhamdaha, Kasba, Krityanand Nagar, Purnia East, Rupauli, Srinagar"},
        {"district_name": "Rohtas", "block_name": "Akorhi Gola, Chenari, Dehri, Dawath, Dinara, Karakat, Kochas, Nasriganj, Nokha, Rajpur, Rohtas, Sasaram, Sheosagar, Suryapura, Tilouthu"},
        {"district_name": "Saharsa", "block_name": "Banma Itahari, Kahara, Mahishi, Nauhatta, Patarghat, Salkhua, Simri Bakhtiarpur, Sonbarsa, Satar Kataiya"},
        {"district_name": "Samastipur", "block_name": "Bibhutipur, Bithan, Dalsinghsarai, Hasanpur, Kalyanpur, Khanpur, Mohiuddinnagar, Morwa, Patori, Pusa, Rosera, Samastipur, Sarairanjan, Singhia, Shivaji Nagar, Tajpur, Ujiarpur, Vidyapati Nagar, Warisnagar"},
        {"district_name": "Saran", "block_name": "Amnour, Baniapur, Chapra, Dariapur, Dighwara, Ekma, Garkha, Ishuapur, Jalalpur, Lahladpur, Maker, Manjhi, Marhaura, Mashrakh, Nagra, Panapur, Parsagarh, Revelganj, Sonepur, Taraiya"},
        {"district_name": "Sheikhpura", "block_name": "Ariari, Barbigha, Chewara, Ghatkusumbha, Sheikhpura, Shekhopur Sarai"},
        {"district_name": "Sheohar", "block_name": "Dumri Katsari, Purnahiya, Piprahi, Sheohar, Tariyani"},
        {"district_name": "Sitamarhi", "block_name": "Bairgania, Bajpatti, Bathnaha, Bokhara, Choraut, Dumra, Majorganj, Nanpur, Parihar, Pupri, Runnisaidpur, Riga, Sonbarsa, Suppi"},
        {"district_name": "Siwan", "block_name": "Andar, Barharia, Basantpur, Bhagwanpur Hat, Darauli, Daraundha, Goriakothi, Guthani, Hasanpura, Hussainganj, Lakri Nabiganj, Maharajganj, Mairwa, Nautan, Pachrukhi, Raghunathpur, Siswan, Siwan, Ziradei"},
        {"district_name": "Vaishali", "block_name": "Bhagwanpur, Bidupur, Chehrakala, Desri, Goraul, Hajipur, Jandaha, Lalganj, Mahnar, Mahua, Patepur, Raghopur, Raja Pakar, Sahdei Buzurg"},
        {"district_name": "West Champaran", "block_name": "Bagaha-1, Bagaha-2, Bettiah, Bairia, Bhitaha, Chanpatia, Gaunaha, Jogapatti, Lauriya, Mainatand, Majhaulia, Nautan, Narkatiaganj, Ramnagar, Sikta, Thakrahan"},
        {"district_name": "East Champaran", "block_name": "Adapur, Areraj, Banjariya, Chakia, Chiraia, Dhaka, Ghorasahan, Harsidhi, Kesariya, Kotwa, Mehsi, Motihari, Pakridayal, Patahi, Pipal Bani, Patahi, Raxaul, Sugauli, Tetaria, Turkaulia"}


        # ... add remaining districts & blocks
    ]

    # -----------------------
    # Jharkhand locations
    # -----------------------
    jharkhand_locations = [
        {"district_name": "Bokaro", "block_name": "Bermo, Chas, Jaridih, Gomia, Kasmar, Petarwar, Chandrapura, Baghmara, Jharia, Nirsa"},
        {"district_name": "Chatra", "block_name": "Chatra, Simaria, Lawalong, Kunda, Pratappur, Panki, Giddhor, Itkhori, Jainagar, Mandu, Pathalgada, Keredari"},
        {"district_name": "Deoghar", "block_name": "Deoghar, Mohanpur, Sarath, Palojori, Margomunda, Karon, Madhupur, Devipur, Sonaraithari"},
        {"district_name": "Dhanbad", "block_name": "Dhanbad, Baghmara, Baliapur, Govindpur, Nirsa, Topchanchi, Tundi, Purvi Tundi, Egarkund, Kaliasole"},
        {"district_name": "Dumka", "block_name": "Dumka, Jarmundi, Gopikandar, Shikaripara, Sarsabad, Rajnagar, Massanjore, Jama, Ranishwar, Jamtara, Kundhit, Nala, Fatehpur"},
        {"district_name": "East Singhbhum", "block_name": "Jamshedpur, Dhalbhumgarh, Ghatshila, Potka, Baharagora, Chakulia, Patamda, Musabani, Golmuri-cum-Jugsalai, Bagbera, Mango, Sidhgora, Sonari"},
        {"district_name": "Garhwa", "block_name": "Garhwa, Nagaruntari, Ranka, Chinia, Meral, Bhawnathpur, Bardiha, Kandi, Rajpur, Shankarpur, Bhandaria, Ramkanda, Chhatarpur"},
        {"district_name": "Giridih", "block_name": "Bagodar, Bengabad, Birni, Deori, Dhanwar, Dumri, Gandey, Giridih, Jamua, Pirtand, Sariya, Tisri"},
        {"district_name": "Godda", "block_name": "Bashant Rai, Boarijor, Godda, Mahagama, Meherma, Pathargama, Poraiyahat, Sunderpahari, Thakurgangti"},
        {"district_name": "Gumla", "block_name": "Gumla, Raidih, Basia, Bharno, Palkot, Sisai, Chainpur, Rarh, Karanjia, Dumri, Kamdara, Palkot, Simdega"},
        {"district_name": "Hazaribagh", "block_name": "Hazaribagh, Barhi, Barkagaon, Bishnugarh, Churchu, Daru, Ichak, Katkamsandi, Keredari, Padma, Sadar, Chalkusha, Tati Jhariya"},
        {"district_name": "Jamtara", "block_name": "Jamtara, Nala, Fatehpur, Kundhit, Karawan, Karmatar, Jarmundi, Ghatshila"},
        {"district_name": "Khunti", "block_name": "Khunti, Murhu, Torpa, Rania, Arki, Karra, Kamdara, Simdega"},
        {"district_name": "Koderma", "block_name": "Koderma, Jainagar, Chandwara, Satgawan, Markacho, Domchanch, Dhanwar"},
        {"district_name": "Latehar", "block_name": "Latehar, Mahuadand, Manika, Balumath, Barwadih, Chandwa, Garu, Kuru, Lesliganj, Barwadih"},
        {"district_name": "Lohardaga", "block_name": "Lohardaga, Kairo, Kisko, Senha, Bhandra, Jari, Bansjore, Kuru"},
        {"district_name": "Pakur", "block_name": "Pakur, Amrapara, Hiranpur, Maheshpur, Pakuria, Littipara, Murarai, Rajgram"},
        {"district_name": "Palamu", "block_name": "Medininagar, Chhatarpur, Panki, Patan, Manatu, Lesliganj, Bishrampur, Hussainabad, Satbarwa, Daltonganj, Garhwa, Nagaruntari"},
        {"district_name": "Ramgarh", "block_name": "Ramgarh, Mandu, Gola, Patratu, Ormanjhi, Silli, Rajrappa, Palkot, Barkagaon"},
        {"district_name": "Ranchi", "block_name": "Ranchi, Bundu, Kanke, Khunti, Namkum, Ratu, Nagri, Mandar, Chanho, Bero, Itki, Lapung, Burmu, Khelari, Rahe, Silli, Sonahatu, Tamar, Nagri"},
        {"district_name": "Sahibganj", "block_name": "Sahibganj, Taljhari, Borio, Mandro, Udhwa, Rajmahal, Pathna, Borio, Rajmahal"},
        {"district_name": "Saraikela-Kharsawan", "block_name": "Saraikela, Chandil, Kharsawan, Kuchai, Gamharia, Nimdih, Kharsawan, Kuchai"},
        {"district_name": "Simdega", "block_name": "Simdega, Thethaitangar, Bansjore, Jaldega, Kersai, Bolba, Kurdeg, Palkot, Bano, Kersai"},
        {"district_name": "West Singhbhum", "block_name": "Chaibasa, Manoharpur, Chakradharpur, Khuntpani, Jagannathpur, Sonua, Kumardungi, Goilkera, Tonto, Bandgaon, Noamundi, Kolhan, Khuntpani"},
    ]


    # ✅ Insert into Location model if not exists (for both states)
    for state, loc_list in {"Bihar": bihar_locations, "Jharkhand": jharkhand_locations}.items():
        for loc in loc_list:
            for block in loc["block_name"].split(","):
                block = block.strip()
                if not Location.objects.filter(state_name=state, district_name=loc["district_name"], block_name=block).exists():
                    Location.objects.create(state_name=state, district_name=loc["district_name"], block_name=block)

    # Get distinct states & districts
    states = list(Location.objects.values_list("state_name", flat=True).distinct())
    selected_state = request.GET.get("state", "Bihar")  # Default Bihar

    districts = list(Location.objects.filter(state_name=selected_state).values_list("district_name", flat=True).distinct())

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

        # ✅ State selection dynamic
        state_name = request.POST.get('state_name', '').strip()
        district_name = request.POST.get('district', '').strip() or ''
        block_name = request.POST.get('block_name', '').strip() or ''

        if not state_name:
            messages.error(request, "State name is required.")
            roles = Role.objects.filter(level=level_map.get(location_level, 'block'))
            return render(request, 'core/admin/add_block_member.html', {
                'roles': roles,
                'states': states,
                'districts': districts,
                'selected_state': selected_state,
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
                'states': states,
                'districts': districts,
                'selected_state': selected_state,
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

        try:
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
                is_active=is_active,
                plain_password=password   # ← yaha directly set kar do

                
            )

            user.location_level = location_level
            user.save()

            messages.success(request, f"{location_level.capitalize()} Member added successfully with username: {username}")
            return redirect('add_block_member')

        except Exception as e:
            messages.error(request, f"Error while saving user: {e}")

    roles = Role.objects.filter(level='block')
    return render(request, 'core/admin/add_block_member.html', {
        'roles': roles,
        'states': states,
        'districts': districts,
        'selected_state': selected_state
    })


@superuser_required
def manage_block_member(request):
    block_roles = Role.objects.filter(level='block')
    if not block_roles.exists():
        messages.error(request, "No roles found for 'block' level.")
        members = User.objects.none()
    else:
        members = User.objects.filter(role__in=block_roles)

    # ---------------- Locations ----------------
 # ---------------- Locations ----------------
    locations = {         
        "Bihar": {
            "Araria": ["Araria", "Bhargama", "Forbesganj", "Jokihat", "Kursakatta", "Narpatganj", "Palasi", "Raniganj", "Sikti"],
            "Arwal": ["Arwal", "Karpi", "Kaler", "Kurtha", "Sonbhadra Banshi Suryapur"],
            "Aurangabad": ["Aurangabad", "Barun", "Deo", "Goh", "Haspura", "Kutumba", "Madanpur", "Nabinagar", "Obra", "Rafiganj"],
            "Banka": ["Amarpur", "Banka", "Barahat", "Belhar", "Chanan", "Dhoraiya", "Fullidumar", "Katoria", "Phulidumar", "Rajoun", "Shambhuganj"],
            "Begusarai": ["Bachhwara", "Barauni", "Begusarai", "Bakhri", "Bhagwanpur", "Birpur", "Cheria Bariarpur", "Chhorahi", "Dandari", "Garhpura", "Khodawandpur", "Mansurchak", "Matihani", "Naokothi", "Sahebpur Kamal", "Samho Akha Kurha", "Teghra"],
            "Bhagalpur": ["Bihpur", "Gopalpur", "Goradih", "Ismailpur", "Jagdishpur", "Kahalgaon", "Kharik", "Narayanpur", "Nathnagar", "Pirpainti", "Sabour", "Sanhoula", "Shahkund", "Sonhaula"],
            "Bhojpur": ["Agiaon", "Ara Sadar", "Barhara", "Bihia", "Charpokhari", "Garhani", "Jagdishpur", "Koilwar", "Piro", "Sahar", "Sandesh", "Shahpur", "Tarari", "Udwantnagar"],
            "Buxar": ["Buxar", "Brahmpur", "Chausa", "Chakki", "Chaugain", "Dumraon", "Itarhi", "Kesath", "Nawanagar", "Rajpur", "Simri"],
            "Darbhanga": ["Alinagar", "Bahadurpur", "Baheri", "Benipur", "Biraul", "Darbhanga Sadar", "Ghanshyampur", "Hanuman Nagar", "Hayaghat", "Jale", "Keoti", "Kusheshwar Asthan", "Kusheshwar Asthan Purbi", "Manigachhi", "Singhwara", "Tardih"],
            "Gaya": ["Atri", "Banke Bazar", "Barachatti", "Belaganj", "Bodh Gaya", "Dobhi", "Fatehpur", "Guraru", "Gurua", "Gaya Town", "Imamganj", "Khijarsarai", "Konch", "Manpur", "Mohanpur", "Neem Chak Bathani", "Paraiya", "Sherghati", "Tankuppa", "Wazirganj"],
            "Gopalganj": ["Baikunthpur", "Barauli", "Bhorey", "Bijaipur", "Gopalganj", "Hathua", "Kuchaikote", "Manjha", "Panchdeori", "Phulwaria", "Sidhwalia", "Thawe", "Uchkagaon"],
            "Jamui": ["Barhat", "Chakai", "Gidhaur", "Islamnagar Aliganj", "Jamui", "Jhajha", "Khaira", "Laxmipur", "Sikandra"],
            "Jehanabad": ["Ghoshi", "Hulasganj", "Jehanabad", "Kako", "Makhdumpur", "Modanganj", "Ratni Faridpur"],
            "Kaimur": ["Adhaura", "Bhagwanpur", "Chainpur", "Chand", "Durgawati", "Kudra", "Mohania", "Rampur", "Ramgarh", "Bhabhua"],
            "Katihar": ["Amdabad", "Azamnagar", "Balrampur", "Barari", "Dandkhora", "Falka", "Hasanganj", "Kadwa", "Katihar", "Korha", "Kursela", "Mansahi", "Manihari", "Pranpur", "Sameli"],
            "Khagaria": ["Alauli", "Beldaur", "Chautham", "Gogri", "Khagaria", "Mansi", "Parbatta"],
            "Kishanganj": ["Bahadurganj", "Dighalbank", "Kochadhaman", "Kishanganj", "Pothia", "Terhagachh", "Thakurganj"],
            "Lakhisarai": ["Barahiya", "Chanan", "Halsi", "Lakhisarai", "Pipariya", "Ramgarh Chowk", "Surajgarha"],
            "Madhepura": ["Alamnagar", "Bihariganj", "Chausa", "Gamharia", "Ghailarh", "Kishanganj", "Kumarkhand", "Madhepura", "Murliganj", "Puraini", "Shankarpur", "Singheshwar"],
            "Madhubani": ["Andhratharhi", "Babubarhi", "Basopatti", "Benipatti", "Bisfi", "Ghoghardiha", "Harlakhi", "Jainagar", "Jhanjharpur", "Khajauli", "Ladania", "Laukaha", "Madhepur", "Madhwapur", "Pandaul", "Phulparas", "Rajnagar"],
            "Munger": ["Asarganj", "Bariarpur", "Dharhara", "Jamalpur", "Kharagpur", "Munger", "Tarapur", "Tetiabambar"],
            "Muzaffarpur": ["Aurai", "Bochaha", "Gaighat", "Kanti", "Katara", "Kudhani", "Kurhani", "Minapur", "Motipur", "Musahari", "Paroo", "Sakra", "Sahebganj", "Saraiya"],
            "Nalanda": ["Asthawan", "Ben", "Bihar Sharif", "Bind", "Ekangarsarai", "Giriyak", "Harnaut", "Hilsa", "Islampur", "Karai Parsurai", "Katrisarai", "Nagarnausa", "Noorsarai", "Parbalpur", "Rajgir", "Silao", "Tharthari"],
            "Nawada": ["Akbarpur", "Hisua", "Govindpur", "Kauwakol", "Narhat", "Nawada", "Pakribarawan", "Rajauli", "Roh", "Sirdala", "Warisaliganj"],
            "Patna": ["Patna Sadar", "Daniyaw", "Bakhtiyarpur", "Fatuha", "Paliganj", "Danapur", "Maner", "Naubatpur", "Sampatchak", "Masaurhi", "Khusrupur", "Bihta", "Punpun", "Barh", "Phulwari", "Dhanarua"],
            "Purnia": ["Amour", "Baisa", "Baisi", "Banmankhi", "Barhara", "Bhawanipur", "Dagarua", "Dhamdaha", "Kasba", "Krityanand Nagar", "Purnia East", "Rupauli", "Srinagar"],
            "Rohtas": ["Akorhi Gola", "Chenari", "Dehri", "Dawath", "Dinara", "Karakat", "Kochas", "Nasriganj", "Nokha", "Rajpur", "Rohtas", "Sasaram", "Sheosagar", "Suryapura", "Tilouthu"],
            "Saharsa": ["Banma Itahari", "Kahara", "Mahishi", "Nauhatta", "Patarghat", "Salkhua", "Simri Bakhtiarpur", "Sonbarsa", "Satar Kataiya"],
            "Samastipur": ["Bibhutipur", "Bithan", "Dalsinghsarai", "Hasanpur", "Kalyanpur", "Khanpur", "Mohiuddinnagar", "Morwa", "Patori", "Pusa", "Rosera", "Samastipur", "Sarairanjan", "Singhia", "Shivaji Nagar", "Tajpur", "Ujiarpur", "Vidyapati Nagar", "Warisnagar"],
            "Saran": ["Amnour", "Baniapur", "Chapra", "Dariapur", "Dighwara", "Ekma", "Garkha", "Ishuapur", "Jalalpur", "Lahladpur", "Maker", "Manjhi", "Marhaura", "Mashrakh", "Nagra", "Panapur", "Parsagarh", "Revelganj", "Sonepur", "Taraiya"],
            "Sheikhpura": ["Ariari", "Barbigha", "Chewara", "Ghatkusumbha", "Sheikhpura", "Shekhopur Sarai"],
            "Sheohar": ["Dumri Katsari", "Purnahiya", "Piprahi", "Sheohar", "Tariyani"],
            "Sitamarhi": ["Bairgania", "Bajpatti", "Bathnaha", "Bokhara", "Choraut", "Dumra", "Majorganj", "Nanpur", "Parihar", "Pupri", "Runnisaidpur", "Riga", "Sonbarsa", "Suppi"],
            "Siwan": ["Andar", "Barharia", "Basantpur", "Bhagwanpur Hat", "Darauli", "Daraundha", "Goriakothi", "Guthani", "Hasanpura", "Hussainganj", "Lakri Nabiganj", "Maharajganj", "Mairwa", "Nautan", "Pachrukhi", "Raghunathpur", "Siswan", "Siwan", "Ziradei"],
            "Vaishali": ["Bhagwanpur", "Bidupur", "Chehrakala", "Desri", "Goraul", "Hajipur", "Jandaha", "Lalganj", "Mahnar", "Mahua", "Patepur", "Raghopur", "Raja Pakar", "Sahdei Buzurg"],
            "West Champaran": ["Bagaha-1", "Bagaha-2", "Bettiah", "Bairia", "Bhitaha", "Chanpatia", "Gaunaha", "Jogapatti", "Lauriya", "Mainatand", "Majhaulia", "Nautan", "Narkatiaganj", "Ramnagar", "Sikta", "Thakrahan"],
            "East Champaran": ["Adapur", "Areraj", "Banjariya", "Chakia", "Chiraia", "Dhaka", "Ghorasahan", "Harsidhi", "Kesariya", "Kotwa", "Mehsi", "Motihari", "Pakridayal", "Patahi", "Pipal Bani", "Patahi", "Raxaul", "Sugauli", "Tetaria", "Turkaulia"]
        
        },

        "Jharkhand": {
            "Bokaro": ["Bermo", "Chas", "Jaridih", "Gomia", "Kasmar", "Petarwar", "Chandrapura", "Baghmara", "Jharia", "Nirsa"],
            "Chatra": ["Chatra", "Simaria", "Lawalong", "Kunda", "Pratappur", "Panki", "Giddhor", "Itkhori", "Jainagar", "Mandu", "Pathalgada", "Keredari"],
            "Deoghar": ["Deoghar", "Mohanpur", "Sarath", "Palojori", "Margomunda", "Karon", "Madhupur", "Devipur", "Sonaraithari"],
            "Dhanbad": ["Dhanbad", "Baghmara", "Baliapur", "Govindpur", "Nirsa", "Topchanchi", "Tundi", "Purvi Tundi", "Egarkund", "Kaliasole"],
            "Dumka": ["Dumka", "Jarmundi", "Gopikandar", "Shikaripara", "Sarsabad", "Rajnagar", "Massanjore", "Jama", "Ranishwar", "Jamtara", "Kundhit", "Nala", "Fatehpur"],
            "East Singhbhum": ["Jamshedpur", "Dhalbhumgarh", "Ghatshila", "Potka", "Baharagora", "Chakulia", "Patamda", "Musabani", "Golmuri-cum-Jugsalai", "Bagbera", "Mango", "Sidhgora", "Sonari"],
            "Garhwa": ["Garhwa", "Nagaruntari", "Ranka", "Chinia", "Meral", "Bhawnathpur", "Bardiha", "Kandi", "Rajpur", "Shankarpur", "Bhandaria", "Ramkanda", "Chhatarpur"],
            "Giridih": ["Bagodar", "Bengabad", "Birni", "Deori", "Dhanwar", "Dumri", "Gandey", "Giridih", "Jamua", "Pirtand", "Sariya", "Tisri"],
            "Godda": ["Bashant Rai", "Boarijor", "Godda", "Mahagama", "Meherma", "Pathargama", "Poraiyahat", "Sunderpahari", "Thakurgangti"],
            "Gumla": ["Gumla", "Raidih", "Basia", "Bharno", "Palkot", "Sisai", "Chainpur", "Rarh", "Karanjia", "Dumri", "Kamdara", "Palkot", "Simdega"],
            "Hazaribagh": ["Hazaribagh", "Barhi", "Barkagaon", "Bishnugarh", "Churchu", "Daru", "Ichak", "Katkamsandi", "Keredari", "Padma", "Sadar", "Chalkusha", "Tati Jhariya"],
            "Jamtara": ["Jamtara", "Nala", "Fatehpur", "Kundhit", "Karawan", "Karmatar", "Jarmundi", "Ghatshila"],
            "Khunti": ["Khunti", "Murhu", "Torpa", "Rania", "Arki", "Karra", "Kamdara", "Simdega"],
            "Koderma": ["Koderma", "Jainagar", "Chandwara", "Satgawan", "Markacho", "Domchanch", "Dhanwar"],
            "Latehar": ["Latehar", "Mahuadand", "Manika", "Balumath", "Barwadih", "Chandwa", "Garu", "Kuru", "Lesliganj", "Barwadih"],
            "Lohardaga": ["Lohardaga", "Kairo", "Kisko", "Senha", "Bhandra", "Jari", "Bansjore", "Kuru"],
            "Pakur": ["Pakur", "Amrapara", "Hiranpur", "Maheshpur", "Pakuria", "Littipara", "Murarai", "Rajgram"],
            "Palamu": ["Medininagar", "Chhatarpur", "Panki", "Patan", "Manatu", "Lesliganj", "Bishrampur", "Hussainabad", "Satbarwa", "Daltonganj", "Garhwa", "Nagaruntari"],
            "Ramgarh": ["Ramgarh", "Mandu", "Gola", "Patratu", "Ormanjhi", "Silli", "Rajrappa", "Palkot", "Barkagaon"],
            "Ranchi": ["Ranchi", "Bundu", "Kanke", "Khunti", "Namkum", "Ratu", "Nagri", "Mandar", "Chanho", "Bero", "Itki", "Lapung", "Burmu", "Khelari", "Rahe", "Silli", "Sonahatu", "Tamar", "Nagri"],
            "Sahibganj": ["Sahibganj", "Taljhari", "Borio", "Mandro", "Udhwa", "Rajmahal", "Pathna", "Borio", "Rajmahal"],
            "Saraikela-Kharsawan": ["Saraikela", "Chandil", "Kharsawan", "Kuchai", "Gamharia", "Nimdih", "Kharsawan", "Kuchai"],
            "Simdega": ["Simdega", "Thethaitangar", "Bansjore", "Jaldega", "Kersai", "Bolba", "Kurdeg", "Palkot", "Bano", "Kersai"],
            "West Singhbhum": ["Chaibasa", "Manoharpur", "Chakradharpur", "Khuntpani", "Jagannathpur", "Sonua", "Kumardungi", "Goilkera", "Tonto", "Bandgaon", "Noamundi", "Kolhan", "Khuntpani"]
        }

    }
        
    # ---------------- GET Filters ----------------
    state_query = request.GET.get('state')
    district_query = request.GET.get('district')
    block_query = request.GET.get('block')
    username_query = request.GET.get('username')

    # Filter members based on state
    if state_query:
        members = members.filter(assigned_state__icontains=state_query)

    # Filter members based on district
    if district_query:
        members = members.filter(assigned_district__icontains=district_query)

    # Filter members based on block
    if block_query:
        members = members.filter(assigned_block__icontains=block_query)

    # Filter by username
    if username_query:
        members = members.filter(username__icontains=username_query)

     # ---------------- Prepare Dropdowns ----------------
    states = sorted(locations.keys())

    if state_query and state_query in locations:
        districts = sorted(locations[state_query].keys())

        if district_query:
            district_query_clean = next(
                (d for d in locations[state_query] if d.lower() == district_query.lower()), None
            )
            if district_query_clean:
                blocks = sorted(locations[state_query][district_query_clean])
            else:
                blocks = []
        else:
            blocks = []
    else:
        districts = []
        blocks = []


    # ---------------- Prepare dropdown data ----------------
    states = sorted(locations.keys())
    districts = sorted(locations[state_query].keys()) if state_query and state_query in locations else []
    blocks = sorted(locations[state_query][district_query]) if state_query and district_query and district_query in locations[state_query] else []

    return render(request, 'core/admin/manage_block_member.html', {
        'members': members,
        'states': states,
        'districts': districts,
        'blocks': blocks,
        'state': state_query or "",
        'district': district_query or "",
        'block': block_query or "",
        'username': username_query or "",
        'locations_json': json.dumps(locations)
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



# -------------------------------------------
# TOGGLE ACTIVE STATUS (AJAX)
# -------------------------------------------

@login_required
@csrf_exempt
@require_POST
def toggle_active_status(request, member_id):
    try:
        data = json.loads(request.body)
        is_active = data.get("active", True)

        member = User.objects.get(id=member_id)
        member.is_active = is_active
        member.save(update_fields=["is_active"])  # ✅ efficient update

        return JsonResponse({"success": True, "is_active": member.is_active})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "Member not found."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)



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

    if request.method == "POST":
        # Get uploaded files
        solve_image = request.FILES.get("solve_image")
        solve_video = request.FILES.get("solve_video")

        complaint.status = "Solved"
        complaint.resolved_at = timezone.now()

        # Save files if uploaded
        if solve_image:
            complaint.solve_image = solve_image
        if solve_video:
            complaint.solve_video = solve_video

        complaint.save()
        messages.success(request, "Complaint marked as solved with proof.")
    else:
        messages.error(request, "Invalid request method.")

    return redirect("block_admin_complaints")


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
   
    # ----------------------- Locations -----------------------
    # Bihar locations
    bihar_locations = [
        {
            "district_name": "Araria",
            "block_name": "Araria",
            "panchayats": [
            "Araria Basti", "Azamnagar Kusiyar Gawon", "Azmatpur Basantpur", "Bahgi Pokharia",
            "Bairgachhi Belwa", "Bangawan Bangama", "Bansbari Bansbari", "Barakamatchistipur Haria",
            "Basantpur Basantpur", "Baturbari Baturbari", "Belbari Araria Basti", "Belsandi Araria Basti",
            "Belwa Araria Basti", "Bhadwar Araria Basti", "Bhairoganj Araria Basti", "Bhanghi Araria Basti",
            "Bhawanipur Araria Basti", "Bhorhar Araria Basti", "Chakorwa Araria Basti", "Dahrahra Araria Basti",
            "Damiya Araria Basti", "Dargahiganj Araria Basti", "Dombana Araria Basti", "Dumari Araria Basti",
            "Fatehpur Araria Basti", "Gadhgawan Araria Basti", "Gandhi Araria Basti", "Gangauli Araria Basti",
            "Ganj Araria Basti", "Gogri Araria Basti", "Gopalpur Araria Basti"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Forbesganj",
            "panchayats": [
            "Forbesganj", "Araria", "Bhargama", "Raniganj", "Sikti", "Palasi",
            "Jokihat", "Kursakatta", "Narpatganj", "Hanskosa", "Hardia", "Haripur",
            "Hasanpur Khurd", "Hathwa", "Gadaha", "Ganj Bhag", "Ghiwba", "Ghoraghat",
            "Gogi", "Gopalpur", "Gurmahi", "Halhalia", "Halhalia Jagir"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Jokihat",
            "panchayats": [
            "Jokihat", "Artia Simaria", "Bagdahara", "Bagesari", "Bagmara", "Bagnagar",
            "Baharbari", "Bairgachhi", "Bankora", "Bara Istamrar", "Bardenga", "Barhuwa",
            "Bazidpur", "Beldanga", "Bela", "Belsandi", "Belwa", "Bhatkuri", "Bharwara",
            "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri", "Dundbahadur Chakla", "Gamharia"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Kursakatta",
            "panchayats": [
            "Kursakatta", "Kamaldaha", "Kuari", "Lailokhar", "Sikti", "Singhwara", "Sukhasan", "Bairgachhi"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Narpatganj",
            "panchayats": [
            "Narpatganj", "Ajitnagar", "Amrori", "Anchraand Hanuman Nagar", "Baghua Dibiganj",
            "Bardaha", "Barhara", "Barhepara", "Bariarpur", "Barmotra Arazi", "Basmatiya", "Bela",
            "Belsandi", "Belwa"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Palasi",
            "panchayats": [
            "Palasi", "Bakainia", "Balua", "Bangawan", "Baradbata", "Baraili", "Bargaon",
            "Barkumba", "Behari", "Belbari", "Belsari", "Beni", "Beni Pakri"
            ]
        },
        {
            "district_name": "Araria",
            "block_name": "Raniganj",
            "panchayats": [
            "Raniganj", "Asabhag", "Asura Kalan Khola", "Bakhri Milik", "Balchanda", "Banmali",
            "Batraha", "Bhag Parasi", "Bhagtira", "Bhaloa", "Bhimpur Khar", "Bhishunpur",
            "Bhorha", "Bhutahi", "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri",
            "Dundbahadur Chakla", "Gamharia", "Gamharia Milik"
            ]
        },
         {
            "district_name": "Araria",
            "block_name": "Sikti",
            "panchayats": [
            "Sikti", "Asabhag", "Asura Kalan Khola", "Bakhri Milik", "Balchanda", "Banmali",
            "Batraha", "Bhag Parasi", "Bhagtira", "Bhaloa", "Bhimpur Khar", "Bhishunpur",
            "Bhorha", "Bhutahi", "Bishunpur", "Chandni", "Chaura", "Chiraiya", "Dhanesri",
            "Dundbahadur Chakla", "Gamharia", "Gamharia Milik"
            ]
        },
            
        {
            "district_name": "Arwal",
            "block_name": "Arwal",
            "panchayats": ["Abgila", "Amara", "Arwal Sipah", "Basilpur", "Bhadasi", "Fakharpur", "Khamaini", "Makhdumpur", "Muradpur Hujara", "Parasi", "Payarechak", "Rampur Baina"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Kaler",
            "panchayats": ["Sakri Khurd", "Balidad", "Belawan", "Belsar", "Injor", "Ismailpur Koyal", "Jaipur", "Kaler", "Kamta", "Mainpura", "North Kaler", "Pahleja"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Karpi",
            "panchayats": ["Khajuri", "Kochahasa", "Aiyara", "Bambhi", "Belkhara", "Chauhar", "Dorra", "Kapri", "Karpi", "Keyal", "Kinjar", "Murarhi"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Kurtha",
            "panchayats": ["Ahmadpur Harna", "Alawalpur", "Bahbalpur", "Baid Bigha", "Bara", "Barahiya", "Basatpur", "Benipur", "Bishunpur", "Chhatoi", "Dakra", "Darheta", "Dhamaul", "Dhondar", "Gangapur", "Gangea", "Gauhara", "Gokhulpur", "Harpur", "Helalpur", "Ibrahimpur", "Jagdispur", "Khaira", "Khemkaran Saray", "Kimdar Chak", "Kod marai", "Koni", "Kothiya", "Kubri", "Kurkuri", "Kurthadih", "Lari", "Lodipur", "Madarpur", "Mahmadpur", "Makhdumpur", "Manikpur", "Manikpur", "Milki", "Mobarakpur", "Molna Chak", "Motipur", "Musarhi", "Nadaura", "Narhi", "Nezampur", "Nighwan"]
        },
        {
            "district_name": "Arwal",
            "block_name": "Sonbhadra Banshi Suryapur",
            "panchayats": ["Sonbhadra", "Banshi", "Suryapur"]
        },
         {
            "district_name": "Aurangabad",
            "block_name": "Aurangabad",
            "panchayats": ["Aurangabad Sadar", "Barun", "Karmabad", "Bachra", "Bhawanipur", "Chakibazar", "Dhanauti", "Jaitpur", "Khurampur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Barun",
            "panchayats": ["Barun", "Bhagwanpur", "Kundahar", "Laxmanpur", "Rampur", "Sasaram", "Senga", "Tandwa"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Deo",
            "panchayats": ["Deo", "Bakar", "Chakand", "Gopalpur", "Jamalpur", "Kachhahi", "Kekri", "Manjhi"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Goh",
            "panchayats": ["Goh", "Kachhawa", "Kanchanpur", "Khirpai", "Makhdumpur", "Rajnagar", "Rampur", "Sarwa"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Haspura",
            "panchayats": ["Haspura", "Barauli", "Belwar", "Bichkoi", "Chandi", "Khapri", "Mahmoodpur", "Nuaon"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Kutumba",
            "panchayats": ["Kutumba", "Brajpura", "Chak Mukundpur", "Daharpur", "Gopalpur", "Jhunjhunu", "Rampur", "Sahar"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Madanpur",
            "panchayats": ["Madanpur", "Amra", "Bajidpur", "Barachatti", "Chakiya", "Dhanpur", "Kachhawa", "Rampur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Nabinagar",
            "panchayats": ["Nabinagar", "Alipur", "Chhatauni", "Deohra", "Jafarpur", "Rampur", "Shivpur"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Obra",
            "panchayats": ["Obra", "Biharichak", "Chhata", "Harikala", "Kandua", "Rampur", "Sakra"]
        },
        {
            "district_name": "Aurangabad",
            "block_name": "Rafiganj",
            "panchayats": ["Rafiganj", "Barauni", "Bhagwanpur", "Chakuli", "Deoghar", "Mohanpur", "Rampur", "Sikta"]
        },
        


        {
            "district_name": "Banka",
            "block_name": "Amarpur",
            "panchayats": ["Amarpur", "Chouka", "Dhamua", "Gopalpur", "Haripur", "Jagdishpur", "Kharagpur", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Banka",
            "panchayats": ["Banka Sadar", "Barhampur", "Chandipur", "Dumaria", "Kharik", "Maheshpur", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Barahat",
            "panchayats": ["Barahat", "Chakpura", "Durgapur", "Jagdishpur", "Kudra", "Rampur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Belhar",
            "panchayats": ["Belhar", "Chakbhabani", "Durgapur", "Maheshpur", "Rampur", "Sahapur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Bausi",
            "panchayats": ["Bausi", "Chakla", "Dhanpur", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Bihat",
            "panchayats": ["Bihat", "Chakra", "Durgapur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Chandan",
            "panchayats": ["Chandan", "Gopalpur", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Dhuraiya",
            "panchayats": ["Dhuraiya", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Katoria",
            "panchayats": ["Katoria", "Rampur", "Chakla", "Maheshpur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Rajauli",
            "panchayats": ["Rajauli", "Chakbhabani", "Rampur", "Durgapur", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Shambhuganj",
            "panchayats": ["Shambhuganj", "Rampur", "Chakla", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Sultanganj",
            "panchayats": ["Sultanganj", "Rampur", "Chakbhabani", "Durgapur", "Maheshpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Tola",
            "panchayats": ["Tola", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Banka",
            "block_name": "Udwantnagar",
            "panchayats": ["Udwantnagar", "Rampur", "Chakla", "Durgapur", "Maheshpur"]
        },
        

            
        {
            "district_name": "Begusarai",
            "block_name": "Bachhwara",
            "panchayats": ["Bachhwara", "Chowki", "Kachhwa", "Mahamadpur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bakhri",
            "panchayats": ["Bakhri", "Chakla", "Dhanpur", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Balia",
            "panchayats": ["Balia", "Chakbhabani", "Rampur", "Sahpur", "Maheshpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Barauni",
            "panchayats": ["Barauni", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Begusarai",
            "panchayats": ["Begusarai Sadar", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bhagwanpur",
            "panchayats": ["Bhagwanpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Birpur",
            "panchayats": ["Birpur", "Chakbhabani", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Cheria Bariyarpur",
            "panchayats": ["Cheria Bariyarpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Dandari",
            "panchayats": ["Dandari", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Garhpura",
            "panchayats": ["Garhpura", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Khodawandpur",
            "panchayats": ["Khodawandpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Mansurchak",
            "panchayats": ["Mansurchak", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Matihani",
            "panchayats": ["Matihani", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Naokothi",
            "panchayats": ["Naokothi", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Sahebpur Kamal",
            "panchayats": ["Sahebpur Kamal", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Teghra",
            "panchayats": ["Teghra", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Begusarai",
            "block_name": "Bihat",
            "panchayats": ["Bihat", "Chakla", "Rampur", "Sahpur"]
        },
        

        
        {
            "district_name": "Bhagalpur",
            "block_name": "Bihpur",
            "panchayats": ["Bihpur", "Rampur", "Chakla", "Sundarpur", "Maheshpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Colgong",
            "panchayats": ["Colgong", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Goradih",
            "panchayats": ["Goradih", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Ismailpur",
            "panchayats": ["Ismailpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Jagdishpur",
            "panchayats": ["Jagdishpur", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Kahalgaon",
            "panchayats": ["Kahalgaon", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Kharik",
            "panchayats": ["Kharik", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Nathnagar",
            "panchayats": ["Nathnagar", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Naugachhia",
            "panchayats": ["Naugachhia", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Pirpainty",
            "panchayats": ["Pirpainty", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Rangra Chowk",
            "panchayats": ["Rangra Chowk", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sabour",
            "panchayats": ["Sabour", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sanhaula",
            "panchayats": ["Sanhaula", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Shahkund",
            "panchayats": ["Shahkund", "Chakla", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Bhagalpur",
            "block_name": "Sultanganj",
            "panchayats": ["Sultanganj", "Chakla", "Rampur", "Sahpur"]
        },
        
        
        {
            "district_name": "Bhojpur",
            "block_name": "Agiaon",
            "panchayats": ["Agiaon", "Sahpur", "Rampur", "Chakla"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Arrah",
            "panchayats": ["Arrah", "Barhara", "Chakla", "Rampur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Barhara",
            "panchayats": ["Barhara", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Behea",
            "panchayats": ["Behea", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Charpokhari",
            "panchayats": ["Charpokhari", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Garhani",
            "panchayats": ["Garhani", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Jagdishpur",
            "panchayats": ["Jagdishpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Koilwar",
            "panchayats": ["Koilwar", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Piro",
            "panchayats": ["Piro", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Sahar",
            "panchayats": ["Sahar", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Sandesh",
            "panchayats": ["Sandesh", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Shahpur",
            "panchayats": ["Shahpur", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Tarari",
            "panchayats": ["Tarari", "Rampur", "Chakla", "Sahpur"]
        },
        {
            "district_name": "Bhojpur",
            "block_name": "Udwantnagar",
            "panchayats": ["Udwantnagar", "Rampur", "Chakla", "Sahpur"]
        },
        
        
        {
            "district_name": "Buxar",
            "block_name": "Buxar",
            "panchayats": ["Buxar", "Chaugain", "Parashpur", "Kaharpur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Itarhi",
            "panchayats": ["Itarhi", "Srikhand", "Lohna", "Nagar Panchayat Itarhi"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chausa",
            "panchayats": ["Chausa", "Rajpur", "Mahuli", "Khawaspur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Rajpur",
            "panchayats": ["Rajpur", "Chausa", "Brahmapur", "Kesath"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Dumraon",
            "panchayats": ["Dumraon", "Bharathar", "Chakand", "Rajpur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Nawanagar",
            "panchayats": ["Nawanagar", "Kesath", "Chauki"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Brahampur",
            "panchayats": ["Brahampur", "Simri", "Chakki"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Kesath",
            "panchayats": ["Kesath", "Chakki", "Brahampur"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chakki",
            "panchayats": ["Chakki", "Kesath", "Simri"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Chougain",
            "panchayats": ["Chougain", "Rajpur", "Buxar"]
        },
        {
            "district_name": "Buxar",
            "block_name": "Simri",
            "panchayats": ["Simri", "Brahampur", "Chakki"]
        },
        
                
        {
            "district_name": "Darbhanga",
            "block_name": "Alinagar",
            "panchayats": ["Alinagar", "Bhuapur", "Chakmiyan", "Mahadevpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Benipur",
            "panchayats": ["Benipur", "Biraul", "Bahadurpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Biraul",
            "panchayats": ["Biraul", "Kalyanpur", "Bheja"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Baheri",
            "panchayats": ["Baheri", "Chandih", "Sarsar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Bahadurpur",
            "panchayats": ["Bahadurpur", "Biraul", "Maheshpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Darbhanga Sadar",
            "panchayats": ["Darbhanga Sadar", "Bachhwara", "Madhopur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Ghanshyampur",
            "panchayats": ["Ghanshyampur", "Chhatauni", "Dhunra"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Hayaghat",
            "panchayats": ["Hayaghat", "Biraul", "Maheshpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Jale",
            "panchayats": ["Jale", "Bhagwanpur", "Chhatauni"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Keotirunway",
            "panchayats": ["Keotirunway", "Muraul", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Kusheshwar Asthan",
            "panchayats": ["Kusheshwar Asthan", "Bahadurpur", "Rajpur"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Manigachhi",
            "panchayats": ["Manigachhi", "Mahishi", "Chhatauni"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Kiratpur",
            "panchayats": ["Kiratpur", "Chhatauni", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Khutauna",
            "panchayats": ["Khutauna", "Rajnagar", "Tardih"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Muraul",
            "panchayats": ["Muraul", "Singhwara", "Purnahiya"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Purnahiya",
            "panchayats": ["Purnahiya", "Gaurabauram", "Khamhria"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Rajnagar",
            "panchayats": ["Rajnagar", "Shivnagar", "Singhwara"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Shivnagar",
            "panchayats": ["Shivnagar", "Tardih", "Wazirganj"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Singhwara",
            "panchayats": ["Singhwara", "Muraul", "Rajnagar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Tardih",
            "panchayats": ["Tardih", "Khutauna", "Shivnagar"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Wazirganj",
            "panchayats": ["Wazirganj", "Gaurabauram", "Khamhria"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Gaurabauram",
            "panchayats": ["Gaurabauram", "Khamhria", "Purnahiya"]
        },
        {
            "district_name": "Darbhanga",
            "block_name": "Khamhria",
            "panchayats": ["Khamhria", "Gaurabauram", "Wazirganj"]
        },
        

                
        {
            "district_name": "Gaya",
            "block_name": "Gaya Sadar",
            "panchayats": ["Gaya Sadar", "Kumahar", "Chandauti", "Barkachha"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Belaganj",
            "panchayats": ["Belaganj", "Araj", "Belsand", "Sariya"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Wazirganj",
            "panchayats": ["Wazirganj", "Madhuban", "Bhurpur", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Manpur",
            "panchayats": ["Manpur", "Kabra", "Chandpura", "Balki"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Bodhgaya",
            "panchayats": ["Bodhgaya", "Gorawan", "Barachatti", "Ratanpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Tekari",
            "panchayats": ["Tekari", "Kharar", "Chakpar", "Barhi"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Konch",
            "panchayats": ["Konch", "Rampur", "Barhampur", "Chhatauni"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Guraru",
            "panchayats": ["Guraru", "Chakbar", "Sikandarpur", "Mohanpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Paraiya",
            "panchayats": ["Paraiya", "Dumariya", "Belsand", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Neemchak Bathani",
            "panchayats": ["Neemchak Bathani", "Sikandarpur", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Khizarsarai",
            "panchayats": ["Khizarsarai", "Chakpar", "Balki"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Atri",
            "panchayats": ["Atri", "Barachatti", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Bathani",
            "panchayats": ["Bathani", "Barachatti", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Mohra",
            "panchayats": ["Mohra", "Rampur", "Guraru"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Sherghati",
            "panchayats": ["Sherghati", "Belsand", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Gurua",
            "panchayats": ["Gurua", "Bodhgaya", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Amas",
            "panchayats": ["Amas", "Sikandarpur", "Chakpar"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Banke Bazar",
            "panchayats": ["Banke Bazar", "Rampur", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Imamganj",
            "panchayats": ["Imamganj", "Belsand", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Dumariya",
            "panchayats": ["Dumariya", "Rampur", "Guraru"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Dobhi",
            "panchayats": ["Dobhi", "Bodhgaya", "Rampur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Mohanpur",
            "panchayats": ["Mohanpur", "Belsand", "Barachatti"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Barachatti",
            "panchayats": ["Barachatti", "Rampur", "Sikandarpur"]
        },
        {
            "district_name": "Gaya",
            "block_name": "Fatehpur",
            "panchayats": ["Fatehpur", "Chakpar", "Gurua"]
        },
        

                
        {
            "district_name": "Gopalganj",
            "block_name": "Gopalganj",
            "panchayats": ["Gopalganj", "Narkatiaganj", "Bairia", "Chapra", "Fatehpur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Thawe",
            "panchayats": ["Thawe", "Parsa", "Bamahi", "Chhaprauli"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Kuchaikote",
            "panchayats": ["Kuchaikote", "Kalyanpur", "Sikati", "Belsand"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Manjha",
            "panchayats": ["Manjha", "Babhnauli", "Rampur", "Chhapra"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Sidhwaliya",
            "panchayats": ["Sidhwaliya", "Belha", "Parmanpur", "Rampur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Hathua",
            "panchayats": ["Hathua", "Bhanpura", "Ramnagar", "Chakpar"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Baikunthpur",
            "panchayats": ["Baikunthpur", "Rampur", "Belsand", "Sikandarpur"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Barauli",
            "panchayats": ["Barauli", "Rampur", "Chakpar", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Kateya",
            "panchayats": ["Kateya", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Phulwariya",
            "panchayats": ["Phulwariya", "Rampur", "Chakpar", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Panchdewari",
            "panchayats": ["Panchdewari", "Rampur", "Belsand", "Chakpar"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Uchkagaon",
            "panchayats": ["Uchkagaon", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Vijayipur",
            "panchayats": ["Vijayipur", "Rampur", "Belsand", "Rampur Gopalganj"]
        },
        {
            "district_name": "Gopalganj",
            "block_name": "Bhorey",
            "panchayats": ["Bhorey", "Rampur", "Belsand", "Chakpar"]
        },
        

        
        {
            "district_name": "Jamui",
            "block_name": "Jamui",
            "panchayats": ["Jamui", "Chakai", "Barhampur", "Dumri", "Sikandra"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Sikandra",
            "panchayats": ["Sikandra", "Bharwaliya", "Khaira", "Chakai", "Sono"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Khaira",
            "panchayats": ["Khaira", "Chakai", "Jamui", "Gidhour"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Chakai",
            "panchayats": ["Chakai", "Khaira", "Jamui", "Barhat"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Sono",
            "panchayats": ["Sono", "Laxmipur", "Jhajha", "Gidhour"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Laxmipur",
            "panchayats": ["Laxmipur", "Barhat", "Jhajha", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Jhajha",
            "panchayats": ["Jhajha", "Barhat", "Gidhour", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Barhat",
            "panchayats": ["Barhat", "Jhajha", "Gidhour", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Gidhour",
            "panchayats": ["Gidhour", "Jhajha", "Barhat", "Islamnagar Aliganj"]
        },
        {
            "district_name": "Jamui",
            "block_name": "Islamnagar Aliganj",
            "panchayats": ["Islamnagar Aliganj", "Gidhour", "Barhat", "Jhajha"]
        },
        
        
        {
            "district_name": "Jehanabad",
            "block_name": "Jehanabad",
            "panchayats": ["Jehanabad", "Kachhiyar", "Barkagaon", "Fatuha", "Sukhi"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Makhdumpur",
            "panchayats": ["Makhdumpur", "Daukar", "Gopalpur", "Arajpura"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Ghosi",
            "panchayats": ["Ghosi", "Nawada", "Sukhpura", "Barhampur"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Hulasganj",
            "panchayats": ["Hulasganj", "Barharwa", "Saraiya", "Rampur"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Ratni Faridpur",
            "panchayats": ["Ratni", "Faridpur", "Kamlapur", "Sultanganj"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Modanganj",
            "panchayats": ["Modanganj", "Bhagwanpur", "Bachhwara", "Barai"]
        },
        {
            "district_name": "Jehanabad",
            "block_name": "Kako",
            "panchayats": ["Kako", "Belwa", "Chakbhabani", "Naugarh"]
        },
        
        
        {
            "district_name": "Kaimur",
            "block_name": "Adhaura",
            "panchayats": ["Adhaura", "Katahariya", "Chakari", "Rampur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Bhabua",
            "panchayats": ["Bhabua", "Kalyanpur", "Gahmar", "Rajpur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Bhagwanpur",
            "panchayats": ["Bhagwanpur", "Chauki", "Chakradharpur", "Sukari"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Chainpur",
            "panchayats": ["Chainpur", "Nautan", "Chakaria", "Belwa"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Chand",
            "panchayats": ["Chand", "Rampur", "Maharajganj", "Sukahi"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Rampur",
            "panchayats": ["Rampur", "Karhi", "Bhagwanpur", "Beldar"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Durgawati",
            "panchayats": ["Durgawati", "Chainpur", "Bhelwara", "Rampur"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Kudra",
            "panchayats": ["Kudra", "Patna", "Chakari", "Barauli"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Mohania",
            "panchayats": ["Mohania", "Gamharia", "Rampur", "Barauli"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Nuaon",
            "panchayats": ["Nuaon", "Chak", "Rampur", "Belwa"]
        },
        {
            "district_name": "Kaimur",
            "block_name": "Ramgarh",
            "panchayats": ["Ramgarh", "Rampur", "Chakra", "Sukahi"]
        },
        
        
        {
            "district_name": "Katihar",
            "block_name": "Katihar",
            "panchayats": ["Katihar Sadar", "Chhota Gamharia", "Puraini", "Sundarpur", "Balua", "Kharhara", "Rajpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Barsoi",
            "panchayats": ["Barsoi", "Sahibganj", "Bhurkunda", "Baksara", "Jamalpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Manihari",
            "panchayats": ["Manihari", "Sikandarpur", "Gopi Bigha", "Rampur", "Chakuli"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Falka",
            "panchayats": ["Falka", "Bhurkunda", "Dhamdaha", "Beldaur", "Jalalpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Kadwa",
            "panchayats": ["Kadwa", "Chakki", "Rampur", "Sikandarpur", "Mahadeopur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Kursela",
            "panchayats": ["Kursela", "Baksara", "Chhapra", "Belwa", "Gajha"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Hasanganj",
            "panchayats": ["Hasanganj", "Rampur", "Chakuli", "Puraini", "Sikandarpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Sameli",
            "panchayats": ["Sameli", "Chhapra", "Rampur", "Beldaur", "Bhagwanpur"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Pranpur",
            "panchayats": ["Pranpur", "Rampur", "Chakuli", "Baksara", "Belwa"]
        },
        {
            "district_name": "Katihar",
            "block_name": "Korha",
            "panchayats": ["Korha", "Rampur", "Belwa", "Chakuli", "Sameli"]
        },
        
        
        {
            "district_name": "Khagaria",
            "block_name": "Khagaria",
            "panchayats": ["Khagaria Sadar", "Pachkuli", "Bhagwanpur", "Kothia", "Rampur"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Beldaur",
            "panchayats": ["Beldaur", "Chakparan", "Bariarpur", "Rajpur", "Gopalpur"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Parbatta",
            "panchayats": ["Parbatta", "Barhampur", "Chakua", "Rampur", "Kothi"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Bariyarpur", "Rampur", "Chakuli", "Belwa"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Chautham",
            "panchayats": ["Chautham", "Rampur", "Bhagwanpur", "Baksara", "Belwa"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Mansi",
            "panchayats": ["Mansi", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Gogri",
            "panchayats": ["Gogri", "Rampur", "Chakuli", "Belwa", "Sameli"]
        },
        {
            "district_name": "Khagaria",
            "block_name": "Simri Bakhtiyarpur",
            "panchayats": ["Simri Bakhtiyarpur", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        
        
        {
            "district_name": "Kishanganj",
            "block_name": "Kishanganj",
            "panchayats": ["Kishanganj Sadar", "Jagdishpur", "Haripur", "Rampur", "Belwa"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Bahadurganj",
            "panchayats": ["Bahadurganj", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Dighalbank",
            "panchayats": ["Dighalbank", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Thakurganj",
            "panchayats": ["Thakurganj", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Goalpokhar",
            "panchayats": ["Goalpokhar", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        {
            "district_name": "Kishanganj",
            "block_name": "Islampur",
            "panchayats": ["Islampur", "Rampur", "Chakuli", "Belwa", "Baksara"]
        },
        
            
        {
            "district_name": "Lakhisarai",
            "block_name": "Lakhisarai",
            "panchayats": ["Lakhisarai Sadar", "Bhatpur", "Rampur", "Chhatwan", "Nawanagar"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Ramgarh Chowk",
            "panchayats": ["Ramgarh Chowk", "Siyalchak", "Chakbahadur", "Kumhar", "Bhagwanpur"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Surajgarha",
            "panchayats": ["Surajgarha", "Chakmohammad", "Mohanpur", "Rampur", "Ghoramara"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Barahiya",
            "panchayats": ["Barahiya", "Chandan", "Kailashganj", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Lakhisarai",
            "block_name": "Chanan",
            "panchayats": ["Chanan", "Rampur", "Chakbahadur", "Siyalchak", "Bhagwanpur"]
        },
        

        {
        
            "district_name": "Madhepura",
            "block_name": "Madhepura",
            "panchayats": ["Madhepura Sadar", "Bhawanipur", "Rampur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Kumargram",
            "panchayats": ["Kumargram", "Chakdah", "Rampur", "Bhawanipur", "Chhatarpur"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Singheshwar",
            "panchayats": ["Singheshwar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Murliganj",
            "panchayats": ["Murliganj", "Rampur", "Chakbahadur", "Bhawanipur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Gopalpur",
            "panchayats": ["Gopalpur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Udaipur",
            "panchayats": ["Udaipur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Alamnagar",
            "panchayats": ["Alamnagar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Shankarpur",
            "panchayats": ["Shankarpur", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        {
            "district_name": "Madhepura",
            "block_name": "Madhepura Sadar",
            "panchayats": ["Madhepura Sadar", "Rampur", "Bhawanipur", "Chakbahadur", "Siyalchak"]
        },
        
        
        {
            "district_name": "Madhubani",
            "block_name": "Andhratharhi",
            "panchayats": ["Andhratharhi", "Chhota Babhani", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Babubarhi",
            "panchayats": ["Babubarhi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Basopatti",
            "panchayats": ["Basopatti", "Rampur", "Bhawanipur", "Chakbahadur"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Benipatti",
            "panchayats": ["Benipatti", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Bisfi",
            "panchayats": ["Bisfi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Ghoghardiha",
            "panchayats": ["Ghoghardiha", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Harlakhi",
            "panchayats": ["Harlakhi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Jhanjharpur",
            "panchayats": ["Jhanjharpur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Kaluahi",
            "panchayats": ["Kaluahi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Khajauli",
            "panchayats": ["Khajauli", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Ladania",
            "panchayats": ["Ladania", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Laukahi",
            "panchayats": ["Laukahi", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Madhepur",
            "panchayats": ["Madhepur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Madhwapur",
            "panchayats": ["Madhwapur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Pandaul",
            "panchayats": ["Pandaul", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Phulparas",
            "panchayats": ["Phulparas", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Rajnagar",
            "panchayats": ["Rajnagar", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Sakri",
            "panchayats": ["Sakri", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Shankarpur",
            "panchayats": ["Shankarpur", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Tardih",
            "panchayats": ["Tardih", "Rampur", "Bhawanipur", "Chhata"]
        },
        {
            "district_name": "Madhubani",
            "block_name": "Lakhnaur",
            "panchayats": ["Lakhnaur", "Rampur", "Bhawanipur", "Chhata"]
        },
        
                
        {
            "district_name": "Munger",
            "block_name": "Munger Sadar",
            "panchayats": ["Munger Sadar", "Gunjaria", "Jorhat", "Chakmoh"]
        },
        {
            "district_name": "Munger",
            "block_name": "Bariyarpur",
            "panchayats": ["Bariyarpur", "Chakla", "Parsa", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Chandan",
            "panchayats": ["Chandan", "Sikta", "Barauli", "Gajni"]
        },
        {
            "district_name": "Munger",
            "block_name": "Sangrampur",
            "panchayats": ["Sangrampur", "Bhagwanpur", "Chhitauni", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Tarapur",
            "panchayats": ["Tarapur", "Paharpur", "Chakbigha", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Jamalpur",
            "panchayats": ["Jamalpur", "Chakgawan", "Bhawanipur", "Rampur"]
        },
        {
            "district_name": "Munger",
            "block_name": "Kharagpur",
            "panchayats": ["Kharagpur", "Chakra", "Rampur", "Barauli"]
        },
        {
            "district_name": "Munger",
            "block_name": "Hathidah",
            "panchayats": ["Hathidah", "Chakmoh", "Rampur", "Bhawanipur"]
        },
        

        
        {
            "district_name": "Muzaffarpur",
            "block_name": "Muzaffarpur Sadar",
            "panchayats": ["Muzaffarpur Sadar", "Kohra", "Sahibganj", "Barauli", "Bhagwanpur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Musahari",
            "panchayats": ["Musahari", "Chakna", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Marwan",
            "panchayats": ["Marwan", "Barauli", "Chakla", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Bochahan",
            "panchayats": ["Bochahan", "Bhawanipur", "Chakmoh", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Katra",
            "panchayats": ["Katra", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Saraiya",
            "panchayats": ["Saraiya", "Rampur", "Chakmoh", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Paroo",
            "panchayats": ["Paroo", "Chakra", "Rampur", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Sakra",
            "panchayats": ["Sakra", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Gorhara",
            "panchayats": ["Gorhara", "Rampur", "Bhawanipur", "Chakmoh"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Motipur",
            "panchayats": ["Motipur", "Chakra", "Barauli", "Rampur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Barahiya",
            "panchayats": ["Barahiya", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Minapur",
            "panchayats": ["Minapur", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Meenapur",
            "panchayats": ["Meenapur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Aurai",
            "panchayats": ["Aurai", "Chakla", "Rampur", "Barauli"]
        },
        {
            "district_name": "Muzaffarpur",
            "block_name": "Piprahi",
            "panchayats": ["Piprahi", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        
        
        {
            "district_name": "Nalanda",
            "block_name": "Bihar Sharif",
            "panchayats": ["Bihar Sharif", "Rampur", "Barhampur", "Chakla", "Sultanpur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Rajgir",
            "panchayats": ["Rajgir", "Bhawanipur", "Rampur", "Chakmoh"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Harnaut",
            "panchayats": ["Harnaut", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Islampur",
            "panchayats": ["Islampur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Hilsa",
            "panchayats": ["Hilsa", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Noorsarai",
            "panchayats": ["Noorsarai", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Ekangarsarai",
            "panchayats": ["Ekangarsarai", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Asthawan",
            "panchayats": ["Asthawan", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Katri",
            "panchayats": ["Katri", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Silao",
            "panchayats": ["Silao", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nalanda",
            "block_name": "Nalanda Sadar",
            "panchayats": ["Nalanda Sadar", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Nawada",
            "block_name": "Nawada Sadar",
            "panchayats": ["Nawada Sadar", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Akbarpur",
            "panchayats": ["Akbarpur", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Narhat",
            "panchayats": ["Narhat", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Pakribarawan",
            "panchayats": ["Pakribarawan", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Hisua",
            "panchayats": ["Hisua", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Warisaliganj",
            "panchayats": ["Warisaliganj", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Kawakol",
            "panchayats": ["Kawakol", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Roh",
            "panchayats": ["Roh", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Nawada",
            "block_name": "Rajauli",
            "panchayats": ["Rajauli", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Patna",
            "block_name": "Patna Sadar",
            "panchayats": ["Patna Sadar", "Rampur", "Chakmoh", "Khalilpur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Daniyaw",
            "panchayats": ["Daniyaw", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Bakhtiyarpur",
            "panchayats": ["Bakhtiyarpur", "Rampur", "Chakmoh", "Saraiya"]
        },
        {
            "district_name": "Patna",
            "block_name": "Fatuha",
            "panchayats": ["Fatuha", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Paliganj",
            "panchayats": ["Paliganj", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Danapur",
            "panchayats": ["Danapur", "Rampur", "Chakla", "Kharika"]
        },
        {
            "district_name": "Patna",
            "block_name": "Maner",
            "panchayats": ["Maner", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Naubatpur",
            "panchayats": ["Naubatpur", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Sampatchak",
            "panchayats": ["Sampatchak", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Masaurhi",
            "panchayats": ["Masaurhi", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Khusrupur",
            "panchayats": ["Khusrupur", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Patna",
            "block_name": "Bihta",
            "panchayats": ["Bihta", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Punpun",
            "panchayats": ["Punpun", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Barh",
            "panchayats": ["Barh", "Rampur", "Chakmoh", "Bhawanipur"]
        },
        {
            "district_name": "Patna",
            "block_name": "Phulwari",
            "panchayats": ["Phulwari", "Rampur", "Chakla", "Rampur Gopal"]
        },
        {
            "district_name": "Patna",
            "block_name": "Dhanarua",
            "panchayats": ["Dhanarua", "Rampur", "Chakla", "Barauli"]
        },
        
        
        {
            "district_name": "Purnia",
            "block_name": "Purnia Sadar",
            "panchayats": ["Purnia Sadar", "Rampur", "Chakla", "Murliganj", "Banmankhi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Banmankhi",
            "panchayats": ["Banmankhi", "Rampur", "Chakla", "Baisi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Dhamdaha",
            "panchayats": ["Dhamdaha", "Rampur", "Chakla", "Rupauli"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Rupauli",
            "panchayats": ["Rupauli", "Rampur", "Chakla", "Baisi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Baisi",
            "panchayats": ["Baisi", "Rampur", "Chakla", "Banmankhi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Kasba",
            "panchayats": ["Kasba", "Rampur", "Chakla", "Bhawanipur"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Bhawanipur",
            "panchayats": ["Bhawanipur", "Rampur", "Chakla", "Barhara Kothi"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Barhara Kothi",
            "panchayats": ["Barhara Kothi", "Rampur", "Chakla", "Sukhasan"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Sukhasan",
            "panchayats": ["Sukhasan", "Rampur", "Chakla", "Amour"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Amour",
            "panchayats": ["Amour", "Rampur", "Chakla", "Krityanand Nagar"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Krityanand Nagar",
            "panchayats": ["Krityanand Nagar", "Rampur", "Chakla", "Jalalgarh"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Jalalgarh",
            "panchayats": ["Jalalgarh", "Rampur", "Chakla", "Bhagalpur"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Bhagalpur",
            "panchayats": ["Bhagalpur", "Rampur", "Chakla", "Purnia City"]
        },
        {
            "district_name": "Purnia",
            "block_name": "Purnia City",
            "panchayats": ["Purnia City", "Rampur", "Chakla", "Purnia Sadar"]
        },
        
        
        {
            "district_name": "Rohtas",
            "block_name": "Rohtas Sadar",
            "panchayats": ["Rohtas Sadar", "Barauli", "Chandpur", "Bikramganj", "Dehri"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Sasaram",
            "panchayats": ["Sasaram", "Kashwan", "Chitbara Gaon", "Karbasawan"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Nokha",
            "panchayats": ["Nokha", "Dumri", "Khirkiya", "Chakia"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Dehri",
            "panchayats": ["Dehri", "Chakai", "Akrua", "Dumari"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Akbarpur",
            "panchayats": ["Akbarpur", "Rajpur", "Chunarughat", "Tilouthu"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Nauhatta",
            "panchayats": ["Nauhatta", "Chakla", "Rajpur", "Dumraon"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Rajpur",
            "panchayats": ["Rajpur", "Tilouthu", "Chand", "Sasaram"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Chenari",
            "panchayats": ["Chenari", "Karbasawan", "Bhabhua", "Chakia"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Tilouthu",
            "panchayats": ["Tilouthu", "Rajpur", "Akbarpur", "Rohtas Sadar"]
        },
        {
            "district_name": "Rohtas",
            "block_name": "Dumraon",
            "panchayats": ["Dumraon", "Nokha", "Sasaram", "Chakla"]
        },
        
        
        {
            "district_name": "Saharsa",
            "block_name": "Saharsa Sadar",
            "panchayats": ["Saharsa Sadar", "Bachhwara", "Kothia", "Bajitpur", "Gamhariya"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Mahishi",
            "panchayats": ["Mahishi", "Banwaria", "Barari", "Mahisar"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Simri Bakhtiyarpur",
            "panchayats": ["Simri Bakhtiyarpur", "Nagar", "Parsauni", "Bapudih"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Sonbarsa",
            "panchayats": ["Sonbarsa", "Belha", "Rampur", "Chandwara"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Madhepur",
            "panchayats": ["Madhepur", "Sakra", "Kothia", "Bachhwara"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Pipra",
            "panchayats": ["Pipra", "Kosi", "Bajitpur", "Narayanpur"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Salkhua",
            "panchayats": ["Salkhua", "Rampur", "Chakla", "Bapudih"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Patarghat",
            "panchayats": ["Patarghat", "Belha", "Mahisham", "Rampur"]
        },
        {
            "district_name": "Saharsa",
            "block_name": "Alamnagar",
            "panchayats": ["Alamnagar", "Kothia", "Banwaria", "Rampur"]
        },
        
        
        {
            "district_name": "Samastipur",
            "block_name": "Samastipur Sadar",
            "panchayats": ["Samastipur Sadar", "Dighalbank", "Kachharauli", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Ujiarpur",
            "panchayats": ["Ujiarpur", "Barauli", "Bhawanipur", "Chakuli"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Morwa",
            "panchayats": ["Morwa", "Mahishi", "Rampur", "Sakra"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Sarairanjan",
            "panchayats": ["Sarairanjan", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Warisnagar",
            "panchayats": ["Warisnagar", "Barauli", "Maheshpur", "Rampur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Kalyanpur",
            "panchayats": ["Kalyanpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Dalsinghsarai",
            "panchayats": ["Dalsinghsarai", "Barauli", "Rampur", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Patori",
            "panchayats": ["Patori", "Barauli", "Rampur", "Sahpur"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Vidyapati Nagar",
            "panchayats": ["Vidyapati Nagar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Tajpur",
            "panchayats": ["Tajpur", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Makhdumpur",
            "panchayats": ["Makhdumpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Musrigharari",
            "panchayats": ["Musrigharari", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Shivajinagar",
            "panchayats": ["Shivajinagar", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Samastipur",
            "block_name": "Goriakothi",
            "panchayats": ["Goriakothi", "Rampur", "Barauli", "Chakla"]
        },
        
        
        {
            "district_name": "Saran",
            "block_name": "Chapra Sadar",
            "panchayats": ["Chapra Sadar", "Chhapra Bazar", "Rampur", "Belha"]
        },
        {
            "district_name": "Saran",
            "block_name": "Marhaura",
            "panchayats": ["Marhaura", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Dighwara",
            "panchayats": ["Dighwara", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Parsa",
            "panchayats": ["Parsa", "Rampur", "Barauli", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Sonpur",
            "panchayats": ["Sonpur", "Rampur", "Chakla", "Belha"]
        },
        {
            "district_name": "Saran",
            "block_name": "Garkha",
            "panchayats": ["Garkha", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Amnour",
            "panchayats": ["Amnour", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Dariapur",
            "panchayats": ["Dariapur", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Taraiya",
            "panchayats": ["Taraiya", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Manjhi",
            "panchayats": ["Manjhi", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Sonepur",
            "panchayats": ["Sonepur", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Saran",
            "block_name": "Masrakh",
            "panchayats": ["Masrakh", "Rampur", "Chakla", "Barauli"]
        },
        {
            "district_name": "Saran",
            "block_name": "Parsauni",
            "panchayats": ["Parsauni", "Rampur", "Belha", "Chakla"]
        },
        
        
        {
            "district_name": "Sheikhpura",
            "block_name": "Sheikhpura Sadar",
            "panchayats": ["Sheikhpura Sadar", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Chewara",
            "panchayats": ["Chewara", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Ariari",
            "panchayats": ["Ariari", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Barbigha",
            "panchayats": ["Barbigha", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Hasanpur",
            "panchayats": ["Hasanpur", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Pirpainti",
            "panchayats": ["Pirpainti", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Sheikhpura",
            "panchayats": ["Sheikhpura", "Rampur", "Belha", "Chakla"]
        },
        {
            "district_name": "Sheikhpura",
            "block_name": "Nathnagar",
            "panchayats": ["Nathnagar", "Rampur", "Belha", "Chakla"]
        },
        
        
        {
            "district_name": "Sheohar",
            "block_name": "Sheohar Sadar",
            "panchayats": ["Sheohar Sadar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Purnahiya",
            "panchayats": ["Purnahiya", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Dumri Katsari",
            "panchayats": ["Dumri Katsari", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Piprarhi",
            "panchayats": ["Piprarhi", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sheohar",
            "block_name": "Mehsi",
            "panchayats": ["Mehsi", "Chakla", "Rampur", "Belha"]
        },
        
        
        {
            "district_name": "Sitamarhi",
            "block_name": "Sitamarhi Sadar",
            "panchayats": ["Sitamarhi Sadar", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Belsand",
            "panchayats": ["Belsand", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bajpatti",
            "panchayats": ["Bajpatti", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Choraut",
            "panchayats": ["Choraut", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bathnaha",
            "panchayats": ["Bathnaha", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Suppi",
            "panchayats": ["Suppi", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Riga",
            "panchayats": ["Riga", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Runnisaidpur",
            "panchayats": ["Runnisaidpur", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Pupri",
            "panchayats": ["Pupri", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Sursand",
            "panchayats": ["Sursand", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Bairgania",
            "panchayats": ["Bairgania", "Chakla", "Rampur", "Belha"]
        },
        {
            "district_name": "Sitamarhi",
            "block_name": "Nanpur",
            "panchayats": ["Nanpur", "Chakla", "Rampur", "Belha"]
        },
        
        
        {
            "district_name": "Siwan",
            "block_name": "Siwan Sadar",
            "panchayats": ["Siwan Sadar", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Barharia",
            "panchayats": ["Barharia", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Bhagwanpur Hat",
            "panchayats": ["Bhagwanpur Hat", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Daraundha",
            "panchayats": ["Daraundha", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Goriakothi",
            "panchayats": ["Goriakothi", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Guthani",
            "panchayats": ["Guthani", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Hussainganj",
            "panchayats": ["Hussainganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Lakri Nabiganj",
            "panchayats": ["Lakri Nabiganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Maharajganj",
            "panchayats": ["Maharajganj", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Nautan",
            "panchayats": ["Nautan", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Pachrukhi",
            "panchayats": ["Pachrukhi", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Raghunathpur",
            "panchayats": ["Raghunathpur", "Chakari", "Rampur", "Maheshpur"]
        },
        {
            "district_name": "Siwan",
            "block_name": "Mairwa",
            "panchayats": ["Mairwa", "Chakari", "Rampur", "Maheshpur"]
        },
        
        
        {
            "district_name": "Vaishali",
            "block_name": "Hajipur",
            "panchayats": ["Hajipur", "Chaksikandar", "Bidupur", "Mahua"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Lalganj",
            "panchayats": ["Lalganj", "Saraiya", "Bigha", "Raghunathpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Mahua",
            "panchayats": ["Mahua", "Mahammadpur", "Khesraha", "Sikandarpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Mahnar",
            "panchayats": ["Mahnar", "Barauli", "Chakhandi", "Bharawan"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Patepur",
            "panchayats": ["Patepur", "Chaksikandar", "Gokulpur", "Basantpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Rajapakar",
            "panchayats": ["Rajapakar", "Chakandarpur", "Katauli", "Kanchanpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Bidupur",
            "panchayats": ["Bidupur", "Mahua", "Chaksikandar", "Paterpur"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Chehrakala",
            "panchayats": ["Chehrakala", "Dighari", "Mahmoodpur", "Barauli"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Desari",
            "panchayats": ["Desari", "Barauli", "Chakandarpur", "Katauli"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Goraul",
            "panchayats": ["Goraul", "Basantpur", "Chaksikandar", "Mahua"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Jandaha",
            "panchayats": ["Jandaha", "Mahnar", "Barauli", "Chakhandi"]
        },
        {
            "district_name": "Vaishali",
            "block_name": "Sahdei Buzurg",
            "panchayats": ["Sahdei Buzurg", "Chaksikandar", "Mahammadpur", "Raghunathpur"]
        },
        
                
        {
            "district_name": "Forbesganj",
            "block_name": "Forbesganj",
            "panchayats": ["Forbesganj", "Araria Basti", "Bahgi Pokharia", "Belbari Araria Basti", "Bansbari Bansbari", "Barakamatchistipur Haria"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Araria",
            "panchayats": ["Araria Basti", "Azamnagar Kusiyar Gawon", "Azmatpur Basantpur", "Bahgi Pokharia", "Bairgachhi Belwa"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Bhargama",
            "panchayats": ["Bhargama", "Bairgachhi", "Bangawan", "Belsandi", "Belwa"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Raniganj",
            "panchayats": ["Raniganj", "Chakorwa", "Dahrahra", "Damiya", "Dargahiganj"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Palasi",
            "panchayats": ["Palasi", "Fatehpur", "Gadhgawan", "Gandhi", "Gangauli"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Sikti",
            "panchayats": ["Sikti", "Ganj", "Gogri", "Gopalpur", "Baturbari"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Jokihat",
            "panchayats": ["Jokihat", "Bhadwar", "Bhairoganj", "Bhawanipur", "Bhanghi"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Kursakatta",
            "panchayats": ["Kursakatta", "Dombana", "Dumari", "Fatehpur", "Gadhgawan"]
        },
        {
            "district_name": "Forbesganj",
            "block_name": "Narpatganj",
            "panchayats": ["Narpatganj", "Nabinagar", "Obra", "Rafiganj", "Haspura"]
        },
        
    
    ]

    jharkhand_locations = [
        {
            "district_name": "Bokaro",
            "block_name": "Bermo",
            "panchayats": ["Bermo", "Tetulmari", "Barmasia", "Jaridih", "Karo"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chas",
            "panchayats": ["Chas", "Chandrapura", "Bandhgora", "Bermo", "Tetulmari"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chandankiyari",
            "panchayats": ["Chandankiyari", "Kundri", "Jhalda", "Panchbaria", "Nawadih"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Chandrapura",
            "panchayats": ["Chandrapura", "Gomia", "Bermo", "Chas", "Tetulmari"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Gomia",
            "panchayats": ["Gomia", "Chandrapura", "Bermo", "Kasmar", "Nawadih"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Jaridih",
            "panchayats": ["Jaridih", "Bermo", "Chas", "Tetulmari", "Barmasia"]
        },
        {
            "district_name": "Bokaro",
            "block_name": "Kasmar",
            "panchayats": ["Kasmar", "Gomia", "Chandankiyari", "Bermo", "Petarwar"]
        },
    ]

# ----------------------- Flatten locations for DB -----------------------
    locations_data = []

    for state_name, state_locations in [("Bihar", bihar_locations), ("Jharkhand", jharkhand_locations)]:
        for block in state_locations:   # ← each block is already a dict
            district_name = block["district_name"]
            block_name = block["block_name"]
            for panchayat in block["panchayats"]:
                locations_data.append({
                    "state_name": state_name,
                    "district_name": district_name,
                    "block_name": block_name,
                    "panchayat_name": panchayat
                })


    # ----------------------- Save locations in DB -----------------------

    # Save locations in DB if not exists
    for loc in locations_data:
        Location.objects.get_or_create(
            state_name=loc["state_name"],
            district_name=loc["district_name"],
            block_name=loc["block_name"],
            panchayat_name=loc["panchayat_name"]
        )

    # States for dropdown
    states = list(Location.objects.values_list("state_name", flat=True).distinct())

    # Password generator
    def generate_password(length=10):
        chars = string.ascii_letters + string.digits + "@#$!"
        return ''.join(secrets.choice(chars) for _ in range(length))

    if request.method == 'POST':
        username = request.POST.get('username')
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please choose another.")
            return redirect('add_booth_member')

        # Personal info
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

        # Location info
        state = request.POST.get('state')
        district = request.POST.get('district')
        block_tehsil_taluka = request.POST.get('block_tehsil_taluka')
        assigned_panchayat = request.POST.get('assigned_panchayat') or None

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

        # Files
        photo = request.FILES.get('photo')
        id_proof = request.FILES.get('id_proof')
        address_proof = request.FILES.get('address_proof')
        digital_signature = request.FILES.get('digital_signature')

        # Role
        role_id = request.POST.get('designation')
        role_instance = get_object_or_404(Role, id=role_id) if role_id else None
        designation = role_instance.role_name if role_instance else None

        # Password
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
            photo=photo,
            id_proof=id_proof,
            address_proof=address_proof,
            digital_signature=digital_signature,
            is_active=True,
            plain_password=password   # ← yaha directly set kar do

        )
        user.set_password(password)

        user.save()
        messages.success(request, f"Booth Member successfully created. Password: {password}")
        return redirect('manage_booth_member')

    # GET request → send states + generated password
    return render(request, 'core/admin/add_booth_member.html', {
        'booth_roles': Role.objects.filter(level='booth'),
        'states': states,
        'generated_password': generate_password(),
        'locations': Location.objects.all()  # <-- ye add karna zaruri hai

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
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":
        # ✅ Solve image/video upload handle
        solve_image = request.FILES.get('solve_image')
        solve_video = request.FILES.get('solve_video')

        if solve_image:
            complaint.solve_image = solve_image  # Model me field hona chahiye: ImageField
        if solve_video:
            complaint.solve_video = solve_video  # Model me field hona chahiye: FileField/VideoField

        # ✅ Status update
        complaint.status = "Solved"
        complaint.save()

        messages.success(request, f"Complaint #{complaint.pk} marked as solved successfully.")
        return redirect('booth_complaints')

    # Agar GET request aayi to wapas redirect
    messages.error(request, "Invalid request method.")
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



from django.http import JsonResponse
@login_required
def get_districts(request):
    state = request.GET.get('state')
    bihar_districts = [
        "Araria","Arwal","Aurangabad","Banka","Begusarai","Bhagalpur","Bhojpur","Buxar",
        "Darbhanga","Gaya","Gopalganj","Jamui","Jehanabad","Kaimur","Katihar","Khagaria",
        "Kishanganj","Lakhisarai","Madhepura","Madhubani","Munger","Muzaffarpur","Nalanda",
        "Nawada","Patna","Purnia","Rohtas","Saharsa","Samastipur","Saran","Sheikhpura",
        "Sheohar","Sitamarhi","Siwan","Supaul","Vaishali","West Champaran","East Champaran"
    ]
    
    jharkhand_districts = [
        "Bokaro","Chatra","Deoghar","Dhanbad","Dumka","East Singhbhum","Garhwa","Giridih",
        "Godda","Gumla","Hazaribagh","Jamtara","Khunti","Koderma","Latehar","Lohardaga",
        "Pakur","Palamu","Ramgarh","Ranchi","Sahibganj","Saraikela-Kharsawan","Simdega","West Singhbhum"
    ]

    if state == "Bihar":
        districts = bihar_districts
    elif state == "Jharkhand":
        districts = jharkhand_districts
    else:
        districts = []

    return JsonResponse({"districts": districts})