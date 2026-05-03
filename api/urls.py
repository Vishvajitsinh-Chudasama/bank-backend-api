from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('users/register/', views.UserCreateView.as_view(), name='user-register'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/', views.UserListView.as_view(), name='user-list'),

    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    
    path('accounts/', views.BankAccountListCreateView.as_view(), name='account-list-create'),
    path('accounts/<int:pk>/', views.BankAccountDeleteView.as_view(), name='account-delete'),
    path('accounts/<int:pk>/topup/', views.BankAccountTopUpView.as_view(), name='account-topup'),

    path('payments/transfer/', views.DoPaymentView.as_view(), name='payment-transfer'),
    path('payments/transactions/', views.TransactionListView.as_view(), name='transaction-list'),
]