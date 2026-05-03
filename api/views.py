from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.db import transaction, models
from decimal import Decimal

from .models import BankAccount, Transaction
from .serializers import UserSerializer, BankAccountSerializer, TransactionSerializer


# 1. USER APIs
class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

# 3. BANK ACCOUNT APIs
class BankAccountListCreateView(generics.ListCreateAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if BankAccount.objects.filter(user=self.request.user).count() >= 3:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"error": "Maximum of 3 bank accounts allowed."})
        serializer.save(user=self.request.user)

class BankAccountDeleteView(generics.DestroyAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

class BankAccountTopUpView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            account = BankAccount.objects.get(id=pk, user=request.user)
            amount = Decimal(request.data.get('amount', 0))
            if amount <= 0:
                return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)
            account.balance += amount
            account.save()
            return Response({"message": "Top-up successful", "new_balance": account.balance})
        except BankAccount.DoesNotExist:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

# 4. PAYMENT APIs
class DoPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sender_id = request.data.get('sender_account_id')
        receiver_id = request.data.get('receiver_account_id')
        amount = Decimal(request.data.get('amount', 0))

        if amount <= 0:
            return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                sender = BankAccount.objects.select_for_update().get(id=sender_id, user=request.user)
                receiver = BankAccount.objects.select_for_update().get(id=receiver_id)

                if sender.balance < amount:
                    Transaction.objects.create(sender_account=sender, receiver_account=receiver, amount=amount, status='FAILED')
                    return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

                sender.balance -= amount
                sender.save()
                receiver.balance += amount
                receiver.save()

                Transaction.objects.create(sender_account=sender, receiver_account=receiver, amount=amount, status='SUCCESS')
                return Response({"message": "Payment successful"})

        except BankAccount.DoesNotExist:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accounts = BankAccount.objects.filter(user=self.request.user)
        return Transaction.objects.filter(
            models.Q(sender_account__in=accounts) | models.Q(receiver_account__in=accounts)
        ).order_by('-created_at')