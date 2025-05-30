from django.db import models
from django.contrib.auth.models import User
import random
import datetime
from django.utils import timezone

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def generate_otp(cls, user):
        # Delete any existing OTPs for this user
        cls.objects.filter(user=user).delete()
        
        # Generate a new 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Create new OTP record
        otp_record = cls.objects.create(
            user=user,
            otp=otp
        )
        return otp
    
    def is_valid(self):
        # OTP is valid for 5 minutes
        now = timezone.now()
        time_diff = now - self.created_at
        return time_diff.total_seconds() < 300  # 5 minutes in seconds
