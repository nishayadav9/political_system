

from django.urls import path
from core.views import admin_login
from core import views
from .views import generate_password_api  # <-- yahan import karo
from .views import state_dashboard
from core.views import state_profile
from core.views import block_dashboard, block_profile,  block_admin_complaints  # block_complaints agar nahi hai toh hata do
from django.contrib.auth import views as auth_views

from .views import view_complaints
from core.views import public_otp_login_view
from .views import district_complaints_forward
from core.views import get_districts_by_state, get_blocks_by_district, get_pincode_by_block

urlpatterns = [
    path('', views.home, name='home'),
    path('crime/', views.crime_view, name='crime'),
    path('road/', views.road, name='road'),
    path('water/', views.water, name='water'),
    path('electricity/', views.electricity_page, name='electricity_page'),
    path('health/', views.health_page, name='health_page'),
    path('education/', views.education_view, name='education'),
    path('corruption/', views.corruption_page, name='corruption_page'),
    path('public-safety/', views.public_safety_page, name='public_safety_page'),
    path('transportation/', views.transportation_view, name='transportation'),
    path('environment/', views.environment_page, name='environment_page'),

    path('about/', views.about, name='about'),
    path('register/', views.register_view, name='register'),


path('complaint-form/', views.complaint_form_view, name='complaint_form'),
    path('track-complaint/', views.track_complaint, name='track_complaint'),


    path('public-otp-login/', public_otp_login_view, name='public_otp_login'),

    path('set-language/', views.set_language, name='set_language'),




    # HOD
# For HOD
path('complaints/edit/<int:complaint_id>/', views.complaint_edit, name='complaint_edit'),
    path('complaints/delete/<int:complaint_id>/', views.complaint_delete, name='complaint_delete'),
# For State Level Party Member
path('state-member/add/', views.add_state_member, name='add_state_member'),
path('state-member/manage/', views.manage_state_member, name='manage_state_member'),
path('state-member/edit/<int:member_id>/', views.edit_state_member, name='edit_state_member'),
path('state-member/delete/<int:member_id>/', views.delete_state_member, name='delete_state_member'),


# For District Level Party Member
path('district-member/add/', views.add_district_member, name='add_district_member'),
path('district-member/manage/', views.manage_district_member, name='manage_district_member'),
path('district-member/edit/<int:member_id>/', views.edit_district_member, name='edit_district_member'),
path('district-member/delete/<int:member_id>/', views.delete_district_member, name='delete_district_member'),


# For Block Level Party Member
path('block-member/add/', views.add_block_member, name='add_block_member'),
path('block-member/manage/', views.manage_block_member, name='manage_block_member'),
path('block-member/add/', views.add_block_member, name='add_block_member'),
path('block-member/edit/<int:member_id>/', views.edit_block_member, name='edit_block_member'),
path('block-member/delete/<int:member_id>/', views.delete_block_member, name='delete_block_member'),


# For Core Member
path('core-member/add/', views.add_core_member, name='add_core_member'),
path('core-member/manage/', views.manage_core_member, name='manage_core_member'),


    # Logout
path('hod/logout/', views.hod_logout, name='hod_logout'),


    path('admin-login/', admin_login, name='admin_login'),
    path('hod-dashboard/', views.hod_dashboard, name='hod_dashboard'),
path('toggle-active/<int:member_id>/', views.toggle_active_status, name='toggle_active_status'),


    



    path('district-dashboard/', views.district_dashboard, name='district_dashboard'),

    # Add District Member
path('district-member/add/', views.add_district_member, name='add_district_member'),

    path('district-member/edit/<int:member_id>/', views.edit_district_member, name='edit_district_member'),
    path('district-member/delete/<int:member_id>/', views.delete_district_member, name='delete_district_member'),

    # Manage District Members (This is the one for listing)
    path('district-members/', views.manage_district_member, name='manage_district_member'),
path('add-core-member/', views.add_core_member, name='add_core_member'),


    path('block-dashboard/', views.block_dashboard, name='block_dashboard'),






    path('api/generate-password/', views.generate_random_password, name='generate_password_api'),
    path('api/generate-password/', generate_password_api, name='generate_password_api'),













path('dashboard/complaints/', view_complaints, name='view_complaints'),

   path('state-admin/dashboard/', views.state_admin_dashboard, name='state_admin_dashboard'),
path('state-admin/profile/', views.state_admin_profile, name='state_admin_profile'),
path('state-admin/complaints/', views.state_admin_complaints, name='state_admin_complaints'),
path('state-admin/logout/', views.state_admin_logout, name='state_admin_logout'),
path('state-admin/change-password/', views.state_admin_change_password, name='state_admin_change_password'),
# urls.py


    path('state-dashboard/', state_dashboard, name='state_dashboard'),
    path('state-profile/', state_profile, name='state_profile'),
    path('state-admin/forwarded-complaints/', views.state_admin_forwarded_complaints, name='state_admin_forwarded_complaints'),
# urls.py

path('state/complaints/edit/<int:pk>/', views.state_complaints_edit, name='state_complaints_edit'),
    path('state/complaints/delete/<int:pk>/', views.state_complaints_delete, name='state_complaints_delete'),
     path('complaints/<int:pk>/accept/', views.state_complaints_accept, name='state_complaints_accept'),
    path('complaints/<int:pk>/reject/', views.state_complaints_reject, name='state_complaints_reject'),
    path('complaints/<int:pk>/solve/', views.state_complaints_solve, name='state_complaints_solve'),



path('district-admin/logout/', views.district_admin_logout, name='district_admin_logout'),
 path('district-dashboard/', views.district_dashboard, name='district_dashboard'),
path('district-profile/', views.district_profile, name='district_profile'),
path('district/complaints/', views.district_admin_complaints, name='district_admin_complaints'),
    path('district/complaints/delete/<int:pk>/', views.district_complaints_delete, name='district_complaints_delete'),
    path('district/complaints/accept/<int:pk>/', views.district_complaints_accept, name='district_complaints_accept'),
    path('district/complaints/reject/<int:pk>/', views.district_complaints_reject, name='district_complaints_reject'),
path(
    'district/forward/<int:complaint_id>/',
    views.district_complaints_forward,
    name='district_complaints_forward'
),
path(
    'district/resolve/<int:pk>/',
    views.district_complaints_resolve,
    name='district_complaints_resolve'
),

    path('district/complaints/solve/<int:pk>/', views.district_complaints_solve, name='district_complaints_solve'),



path('block-admin/logout/', views.block_admin_logout, name='block_admin_logout'),
 path('block-dashboard/', block_dashboard, name='block_dashboard'),
    path('profile/', block_profile, name='profile'),  # <-- ye check karo
  path('block/complaints/', views.block_admin_complaints, name='block_admin_complaints'),
    path('block/complaints/delete/<int:pk>/', views.block_complaints_delete, name='block_complaints_delete'),
    path('block/complaints/accept/<int:pk>/', views.block_complaints_accept, name='block_complaints_accept'),
    path('block/complaints/reject/<int:pk>/', views.block_complaints_reject, name='block_complaints_reject'),
    path('block/complaints/solve/<int:pk>/', views.block_complaints_solve, name='block_complaints_solve'),
path('complaints/<int:complaint_id>/forward/', views.forward_complaint_to_district, name='block_complaints_forward'),

path('district/forward/<int:complaint_id>/', views.district_complaints_forward, name='district_complaints_forward'),


 path(
        'district/forwarded-complaints/',
        views.district_forwarded_complaints,
        name='district_forwarded_complaints'
    ),







path('logout/', views.logout_view, name='logout'),
path('complaints/', views.complaint_list_view, name='complaint_list'),

# urls.py
    path('ajax/load-users/', views.ajax_load_users, name='ajax_load_users'),














path('district/forwarded-complaints/', views.district_forwarded_complaints, name='district_forwarded_complaints'),

path('district/complaints/forward/<int:complaint_id>/', 
         views.district_complaints_forward, 
         name='district_complaints_forward'),



    

    # District complaints list page (example)
    path('district/complaints/', views.district_complaints_list, name='district_complaints_list'),






# Booth Member URLs
path('booth-member/add/', views.add_booth_member, name='add_booth_member'),
path('booth-member/manage/', views.manage_booth_member, name='manage_booth_member'),
path('booth-member/edit/<int:id>/', views.edit_booth_member, name='edit_booth_member'),
    path('booth-member/delete/<int:id>/', views.delete_booth_member, name='delete_booth_member'),
    # Other paths

 path('booth/dashboard/', views.booth_dashboard, name='booth_dashboard'),
    path('booth/forward-complaints/', views.booth_forward_complaints, name='booth_forward_complaints'),
    path('logout/', auth_views.LogoutView.as_view(next_page='admin_login'), name='logout'),
    path('booth/complaints/edit/<int:pk>/', views.booth_complaints_edit, name='booth_complaints_edit'),
    path('booth/complaints/delete/<int:pk>/', views.booth_complaints_delete, name='booth_complaints_delete'),
    path('booth/complaints/accept/<int:pk>/', views.booth_complaints_accept, name='booth_complaints_accept'),
    path('booth/complaints/reject/<int:pk>/', views.booth_complaints_reject, name='booth_complaints_reject'),
    path('booth/complaints/solve/<int:pk>/', views.booth_complaints_solve, name='booth_complaints_solve'),
path('booth/complaints/', views.booth_complaints, name='booth_complaints'),
    path('booth/complaints/forward/<int:complaint_id>/', views.booth_complaints_forward, name='booth_complaints_forward'),
path('block/complaints/forward/', views.block_forward_complaints, name='block_forward_complaints'),

path("block/complaints/<int:pk>/delete/", views.block_complaint_delete, name="block_complaint_delete"),
path("block/complaints/<int:pk>/pending/", views.block_complaint_pending, name="block_complaint_pending"),
path(
    "block/complaints/<int:pk>/reject/",
    views.block_complaints_reject,  # s ke saath
    name="block_complaints_reject"
),
# urls.py
path(
    "block/complaints/<int:pk>/accept/",
    views.block_complaints_accept,  # note the 's' at the end
    name="block_complaint_accept"
),
path("block/complaints/<int:pk>/solve/", views.block_complaints_solve, name="block_complaints_solve"),







path('ajax/get-districts/', get_districts_by_state, name='ajax_get_districts'),
path('ajax/get-blocks/', get_blocks_by_district, name='ajax_get_blocks'),
path('ajax/get-pincode/', get_pincode_by_block, name='ajax_get_pincode'),

    path('booth/complaints/public-notice/<int:pk>/', views.booth_complaints_public_notice, name='booth_complaints_public_notice'),
path('complaint/<int:pk>/update-notice/', views.update_public_notice, name='update_public_notice'),
    path('complaint/<int:complaint_id>/feedback/', views.submit_feedback, name='submit_feedback'),

    path('send-message/', views.send_admin_message, name='send_admin_message'),
path('messages/reply/<int:msg_id>/', views.message_reply, name='message_reply'),
path('messages/edit/<int:msg_id>/', views.message_edit, name='message_edit'),
    path('messages/delete/<int:msg_id>/', views.message_delete, name='message_delete'),
path('messages/', views.receive_messages, name='messages_view'),

path('state-admin/messages/received/', views.receive_messages, name='receive_messages'),
    path('state-admin/messages/send/', views.send_message, name='send_message'),

   

   path('district/messages/received/', views.district_receive_messages, name='district_receive_messages'),
    path('district/messages/send/', views.district_send_message, name='district_send_message'),

    path('block/messages/received/', views.block_receive_messages, name='block_receive_messages'),
path('block/messages/send/', views.block_send_message, name='block_send_message'),


path('booth/messages/received/', views.booth_receive_messages, name='booth_receive_messages'),

    path('hod/receive-messages/', views.hod_receive_messages, name='hod_receive_messages'),

    path('complaints/<int:pk>/update-notice/', views.district_update_public_notice, name='district_update_public_notice'),





]


