from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path('token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.RegisterView.as_view(), name='auth_register'),
    path('test/', views.testEndPoint, name='test'),
    path('', views.getRoutes),

    # Chat/Text Messaging Functionality
    path("my-messages/<user_id>/", views.MyInbox.as_view()),
    path("get-messages/<sender_id>/<reciever_id>/", views.GetMessages.as_view()),
    path("send-messages/", views.SendMessages.as_view()),

    # Get profile
    path("profile/<int:pk>/", views.ProfileDetail.as_view(), name="profile_detail"),
    path("search/<username>/", views.SearchUser.as_view()),

    #Admin routes
    path('admin-dashboard/', views.AdminDashboard.as_view(), name='admin_dashboard'),
    path('toggle-verification/<int:profile_id>/', views.ToggleUserVerification.as_view(), name='toggle_verification'),

    path("friends/", views.FriendListView.as_view(), name="friend_list"),
    path("friend-requests/", views.PendingFriendRequestsView.as_view(), name="pending_friend_requests"),
    path("friend-requests/send/", views.SendFriendRequestView.as_view(), name="send_friend_request"),
    path("friend-requests/respond/<int:request_id>/", views.RespondFriendRequestView.as_view(), name="respond_friend_request"),
    path("all-users/", views.AllUsersListView.as_view(), name="all_users"),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)