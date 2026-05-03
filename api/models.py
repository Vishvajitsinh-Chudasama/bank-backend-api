from django.db import models
from django.contrib.auth.models import User
import random
import string

def generate_account_number():
    return ''.join(random.choices(string.digits, k=10))

class BankAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=20, unique=True, default=generate_account_number)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"

class Transaction(models.Model):
    STATUS_CHOICES = [('SUCCESS', 'Success'), ('FAILED', 'Failed')]
    
    sender_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='sent_transactions')
    receiver_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='received_transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} from {self.sender_account.id} to {self.receiver_account.id} - {self.status}"