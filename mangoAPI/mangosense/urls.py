from django.urls import path
from .views import (
    register_api, login_api, logout_api,
    admin_login_api, admin_refresh_token,
    predict_image, test_model_status
)

app_name = 'mangosense'

urlpatterns = [
    # Mobile app authentication endpoints
    path('register/', register_api, name='register_api'),
    path('login/', login_api, name='login_api'),
    path('logout/', logout_api, name='logout_api'),
    
    # Admin authentication endpoints for Angular
    path('auth/login/', admin_login_api, name='admin_login'),
    path('auth/refresh/', admin_refresh_token, name='admin_refresh'),
    
    # ML prediction endpoints
    path('predict/', predict_image, name='predict_image'),
    path('test-model/', test_model_status, name='test_model_status'),
]