from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

class CoreMemberAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # CoreLevelPartyMember ya jo bhi tumhara user model hoga, usme username se user dhundo
            user = UserModel.objects.get(username=username)
            # Password check karo aur user active bhi hona chahiye
            if user.check_password(password) and user.is_active:
                return user
        except UserModel.DoesNotExist:
            return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
