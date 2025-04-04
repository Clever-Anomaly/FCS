from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q, Subquery, OuterRef
from api.models import User, Profile, ChatMessage, FriendRequest, EmailOTP

from api.serializer import MyTokenObtainPairSerializer, RegisterSerializer, UserSerializer, ProfileSerializer, MessageSerializer, FriendRequestSerializer, SimpleProfileSerializer, SendOTPSerializer, VerifyOTPSerializer

from rest_framework import serializers 

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, BasePermission
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.views import APIView

from rest_framework import viewsets, permissions
from .models import Post, Reaction, Comment, Profile
from .serializer import PostSerializer, CommentSerializer, ReactionSerializer, ProfileSerializer
from django.shortcuts import get_object_or_404


from rest_framework.generics import ListAPIView
from api.models import Comment, Report, Group, GroupMessage
from api.serializer import CommentSerializer, ProfileVerifySerializer, VerificationPendingProfileSerializer, ReportSerializer, GroupSerializer, GroupMessageSerializer, ListingSerializer
import random
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Listing
from .models import Order
from .serializer import ListingSerializer, OrderSerializer
from rest_framework import generics, permissions

from .models import Listing, Order, Withdrawal
from .serializer import (
    ListingSerializer, 
    OrderSerializer,
    WithdrawalSerializer
)



class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow DELETE only if the logged-in user is the post owner
        return obj.user == request.user

class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            now = timezone.now()

            # Check if OTP was already sent recently
            try:
                otp_record = EmailOTP.objects.get(email=email)
                time_since_last_otp = (now - otp_record.created_at).total_seconds()

                if time_since_last_otp < 30:
                    wait_time = int(30 - time_since_last_otp)
                    return Response({
                        "error": f"OTP already sent. Please wait {wait_time} more seconds."
                    }, status=429)  # 429 Too Many Requests

            except EmailOTP.DoesNotExist:
                pass  # No previous OTP, safe to create

            # Generate and send new OTP
            otp = f"{random.randint(100000, 999999)}"
            EmailOTP.objects.update_or_create(email=email, defaults={'otp': otp, 'created_at': now})

            # Replace with actual send_mail setup
            send_mail(
                subject="Verify Your Email - OTP",
                message=f"""
                Hi there,

                Thanks for signing up! Please use the following OTP to verify your email:

                    {otp}

                This code will expire in 5 minutes.

                If you didn’t request this, just ignore this message.

                """,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({"message": "OTP sent to email."})
        return Response(serializer.errors, status=400)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"verified": True})
        return Response(serializer.errors, status=400)

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        email = request.data.get("email")
        otp = request.data.get("otp")
        try:
            record = EmailOTP.objects.get(email=email)
            if record.otp != otp or record.is_expired():
                return Response({"otp": "Invalid or expired OTP."}, status=400)
        except EmailOTP.DoesNotExist:
            return Response({"otp": "OTP not found."}, status=400)

        # If OTP valid, delete it and proceed
        record.delete()
        return super().create(request, *args, **kwargs)


# Get All Routes

@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/api/token/',
        '/api/register/',
        '/api/token/refresh/'
    ]
    return Response(routes)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def testEndPoint(request):
    if request.method == 'GET':
        data = f"Congratulation {request.user}, your API just responded to GET request"
        return Response({'response': data}, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        text = "Hello buddy"
        data = f'Congratulation your API just responded to POST request with text: {text}'
        return Response({'response': data}, status=status.HTTP_200_OK)
    return Response({}, status.HTTP_400_BAD_REQUEST)


class AdminDashboard(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all()
        messages = ChatMessage.objects.all()
        profiles = Profile.objects.all()

        user_data = UserSerializer(users, many=True).data
        message_data = MessageSerializer(messages, many=True).data
        profile_data = ProfileSerializer(profiles, many=True).data

        return Response({
            "users": user_data,
            "messages": message_data,
            "profiles": profile_data
        })
    
class ToggleUserVerification(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, profile_id):
        try:
            profile = Profile.objects.get(id=profile_id)
            profile.verified = not profile.verified  # Toggle verification
            profile.save()
            return Response({"message": "Verification status updated", "verified": profile.verified}, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
    


class GetMessages(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        sender_id = self.kwargs['sender_id']
        reciever_id = self.kwargs['reciever_id']
        user_id = str(self.request.user.id)

        if user_id not in [str(sender_id), str(reciever_id)]:
            raise PermissionDenied("You are not allowed to view these messages.")

        return ChatMessage.objects.filter(
            sender__in=[sender_id, reciever_id],
            reciever__in=[sender_id, reciever_id]
        )


class SendMessages(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    parser_classes = [MultiPartParser, FormParser] 

    def perform_create(self, serializer):
        sender = self.request.user
        reciever = self.request.data.get("reciever")

        if not reciever:
            raise PermissionDenied("Receiver is required.")
        if str(sender.id) == str(reciever):
            raise PermissionDenied("You cannot send messages to yourself.")

        serializer.save(sender=sender)

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    # permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # def get_queryset(self):
    #     return Post.objects.all()

class ReactToPost(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        post_id = request.data.get("post")
        post = get_object_or_404(Post, id=post_id)
        reaction, created = Reaction.objects.get_or_create(user=request.user, post=post)
        if not created:
            reaction.delete()
            return Response({"message": "Like removed"})
        return Response({"message": "Post liked"})


class AddComment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ProfileDetail(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = [IsAuthenticated]  

    def get_object(self):
        # Ensure that the profile being fetched belongs to the logged-in user
        return self.request.user.profile

    def perform_update(self, serializer):
        # Perform the update on the profile
        profile = serializer.save()
        # Optionally, you can add more custom logic here if needed
        return profile


class SearchUser(generics.ListAPIView):
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = [IsAuthenticated]  

    def list(self, request, *args, **kwargs):
        username = self.kwargs['username']
        logged_in_user = self.request.user
        users = Profile.objects.filter(Q(user__username__icontains=username) | Q(full_name__icontains=username) | Q(user__email__icontains=username) )

        if not users.exists():
            return Response(
                {"detail": "No users found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
    

# View to list current user's friends
class FriendListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SimpleProfileSerializer

    def get_queryset(self):
        return self.request.user.profile.friends.all()

# View to list pending friend requests received by the current user
class PendingFriendRequestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendRequestSerializer

    def get_queryset(self):
        return FriendRequest.objects.filter(to_user=self.request.user, status='pending')

# View to send a friend request to another user
class SendFriendRequestView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendRequestSerializer

    def create(self, request, *args, **kwargs):
        target_user_id = request.data.get("to_user_id")
        if not target_user_id:
            return Response({"error": "to_user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Check for duplicate request or if already friends
        if FriendRequest.objects.filter(from_user=request.user, to_user=target_user, status="pending").exists():
            return Response({"error": "Friend request already sent."}, status=status.HTTP_400_BAD_REQUEST)
        if target_user.profile in request.user.profile.friends.all():
            return Response({"error": "You are already friends."}, status=status.HTTP_400_BAD_REQUEST)

        friend_request = FriendRequest.objects.create(from_user=request.user, to_user=target_user)
        serializer = self.get_serializer(friend_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# View to respond to a friend request (accept or reject)
class RespondFriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        action = request.data.get("action")
        if action not in ["accept", "reject"]:
            return Response({"error": "Invalid action. Must be 'accept' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            friend_request = FriendRequest.objects.get(id=request_id, to_user=request.user, status="pending")
        except FriendRequest.DoesNotExist:
            return Response({"error": "Friend request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if action == "accept":
            friend_request.status = "accepted"
            friend_request.save()
            # Add each other as friends (symmetric)
            request.user.profile.friends.add(friend_request.from_user.profile)
            return Response({"message": "Friend request accepted."}, status=status.HTTP_200_OK)
        else:
            friend_request.status = "rejected"
            friend_request.save()
            return Response({"message": "Friend request rejected."}, status=status.HTTP_200_OK)

# Optional: View to list all registered users (for browsing and sending friend requests)
class AllUsersListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()


# @api_view(['GET'])
# def public_profile_view(request, user_id):
#     try:
#         profile = Profile.objects.get(user__id=user_id)
#         serializer = ProfileSerializer(profile)
#         return Response(serializer.data)
#     except Profile.DoesNotExist:
#         return Response({"error": "User not found"}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensures the user is authenticated
def public_profile_view(request, user_id):
    if not request.user.is_authenticated:
        # If the user is not authenticated, return generic data or a message
        return Response({
            'message': 'Please log in to view the profile.',
            'image_url': '/media/default_placeholder_image.jpg'  # Example placeholder image
        }, status=403)  # Forbidden status
    
    try:
        # If authenticated, fetch the profile and return the actual data
        profile = Profile.objects.get(user__id=user_id)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)
    except Profile.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

class LimitedCommentsView(ListAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post_id=post_id).order_by('-created_at')[:3]  # last 3

class AllCommentsView(ListAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post_id=post_id).order_by('-created_at')

class ProfileVerificationUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, user_id):
        try:
            profile = Profile.objects.get(user__id=user_id)

            if profile.user != request.user:
                return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

            serializer = ProfileVerifySerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"detail": "Document uploaded. Awaiting verification."}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Profile.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)


class PendingVerificationsView(ListAPIView):
    queryset = Profile.objects.filter(is_verification_pending=True)
    serializer_class = VerificationPendingProfileSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_context(self):
        return {"request": self.request}  



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_verification_doc(request):
    profile = request.user.profile
    if 'document' not in request.FILES:
        return Response({'error': 'No document provided.'}, status=400)

    profile.verified_doc = request.FILES['document']
    profile.save()
    return Response({'message': 'Document uploaded, awaiting admin verification.'})



class ReportPostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        post_id = request.data.get('post')  # The post ID being reported
        reason = request.data.get('reason')  # The reason for reporting

        if not post_id or not reason:
            return Response({"error": "Post ID and reason are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        # Create the report object
        report = Report.objects.create(
            post=post,
            user=request.user,
            reason=reason,
            status="pending"
        )

        return Response({"message": "Report submitted successfully."}, status=status.HTTP_201_CREATED)

class ResolveReport(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, report_id):
        try:
            report = Report.objects.get(id=report_id)
            # Mark the report as resolved
            report.status = 'resolved'  # Add a status field to your Report model if not present
            report.save()

            return Response({"message": "Report resolved successfully."}, status=status.HTTP_200_OK)
        except Report.DoesNotExist:
            return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)


class TakeDownPost(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, report_id):
        try:
            report = Report.objects.get(id=report_id)
            report.status = 'taken_down'
            report.save()
            post = report.post 
            post.delete()  # Take down the post by deleting it

            # Mark the report as taken down (we could also add a status field in the report model to track this)

            # Return a success response
            return Response({"message": "Post has been taken down successfully."}, status=status.HTTP_200_OK)

        except Report.DoesNotExist:
            return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class ReportListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]  # Ensure only admins can access this view
    serializer_class = ReportSerializer

    def get_queryset(self):
        return Report.objects.all().order_by('-created_at')  # Order by the most recent reports


# class CreateGroupView(generics.CreateAPIView):
#     serializer_class = GroupSerializer
#     # permission_classes = [IsAuthenticated]

#     def perform_create(self, serializer):
#         serializer.save(created_by=self.request.user)

# class CreateGroupView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         data = request.data
#         group_name = request.data.get('name')
#         group_bio = request.data.get('bio')
#         members = request.data.get('members')
        
#         if not members:
#             return Response({"error": "Group must have at least one member."}, status=status.HTTP_400_BAD_REQUEST)

#         # Add the creator (current user) to the members list
#         members.append(request.user.id)
        
#         group = Group.objects.create(name=group_name, bio=group_bio, created_by=request.user)

#         # Your other logic to create a group
#         group.members.set(members)

#         # Save the group instance
#         group.save()

#         # Return a success response
#         return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)

class CreateGroupView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        name = request.data.get("name")
        bio = request.data.get("bio")
        members = request.data.getlist("members")
        image = request.FILES.get("image")

        if not members:
            return Response({"error": "Group must have at least one member."}, status=400)

        members = list(set(members + [str(request.user.id)]))

        group = Group.objects.create(
            name=name,
            bio=bio,
            image=image,
            created_by=request.user
        )
        group.members.set(members)
        return Response(GroupSerializer(group).data, status=201)


class GroupListView(ListAPIView):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(members=self.request.user)


# views.py
class GroupChatMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        # Fetch messages for a group
        group = get_object_or_404(Group, id=group_id)
        messages = group.messages.all().order_by('created_at')
        serializer = GroupMessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request, group_id):
        # Send a new message to the group
        group = get_object_or_404(Group, id=group_id)
        content = request.data.get("content")
        media = request.FILES.get("media")

        if not content and not media:
            return Response({"error": "Content or media required"}, status=status.HTTP_400_BAD_REQUEST)

        message = GroupMessage.objects.create(
            group=group,
            sender=request.user,
            content=content,
            media=media
        )
        return Response(GroupMessageSerializer(message).data, status=status.HTTP_201_CREATED)



# class MarketplaceListAPI(generics.ListAPIView):
#     """
#     Public marketplace view for all users
#     """
#     serializer_class = ListingSerializer
#     queryset = Listing.objects.filter(status='active')  # Only show active listings
    
#     def get_queryset(self):
#         queryset = super().get_queryset()
#         # Add simple search functionality
#         search_query = self.request.query_params.get('search', None)
#         if search_query:
#             queryset = queryset.filter(title__icontains=search_query)
#         return queryset
    
class SellerListingsAPI(generics.ListCreateAPIView):
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.profile.verified:
            raise PermissionDenied("You must verify your account to access marketplace features")
        return Listing.objects.filter(seller=self.request.user)

class MarketplaceListAPI(generics.ListAPIView):
    serializer_class = ListingSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated and not self.request.user.profile.verified:
            raise PermissionDenied("You must verify your account to access marketplace features")
        return Listing.objects.filter(status='active')

class ListingDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Ensures users can only access their own listings"""
        return Listing.objects.filter(seller=self.request.user)

from .models import Listing, Order

class SellerDashboardAPI(APIView):
    def get(self, request):
        seller = request.user
        listings = Listing.objects.filter(seller=seller)
        orders = Order.objects.filter(listing__seller=seller)
        
        return Response({
            'stats': {
                'totalSales': orders.filter(status='completed').count(),
                'pendingOrders': orders.filter(status='pending').count(),
                'completedOrders': orders.filter(status='completed').count(),
                'balance': sum(order.price_at_purchase for order in orders.filter(status='completed'))
            },
            'listings': ListingSerializer(listings, many=True).data,
            'orders': OrderSerializer(orders.order_by('-created_at'), many=True).data
        })
    
class BuyerMarketplaceAPI(APIView):
    """
    API endpoint for buyers to view active marketplace listings
    """
    def get(self, request):
        try:
            active_listings = Listing.objects.filter(status='active')
            serializer = ListingSerializer(active_listings, many=True)
            return Response({
                'success': True,
                'listings': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CreateListingAPI(APIView):
    """
    API endpoint for creating new listings
    """
    def post(self, request):
        try:
            serializer = ListingSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(seller=request.user)
                return Response({
                    'success': True,
                    'listing': serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class OrderSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='buyer.username', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    thumbnail = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'buyer',
            'buyer_name',
            'listing',
            'listing_title',
            'thumbnail',
            'status',
            'quantity',
            'price_at_purchase',
            'created_at',
            'shipping_address',
            'payment_method'
        ]
        read_only_fields = [
            'buyer',
            'seller',
            'price_at_purchase',
            'created_at'
        ]

    def get_thumbnail(self, obj):
        if obj.listing.thumbnail:
            return obj.listing.thumbnail.url
        return None
    

# class SellerDashboardAPI(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         seller = request.user
#         listings = Listing.objects.filter(seller=seller)
#         orders = Order.objects.filter(seller=seller)
        
#         return Response({
#             'stats': {
#                 'totalSales': orders.filter(status='completed').count(),
#                 'pendingOrders': orders.filter(status='pending').count(),
#                 'completedOrders': orders.filter(status='completed').count(),
#                 'balance': sum(
#                     order.price_at_purchase * order.quantity 
#                     for order in orders.filter(status='completed')
#                 )
#             },
#             'listings': ListingSerializer(listings, many=True).data,
#             'orders': OrderSerializer(orders.order_by('-created_at'), many=True).data
#         })

class SellerListingsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        listings = Listing.objects.filter(seller=request.user)
        serializer = ListingSerializer(listings, many=True)
        return Response({
            'success': True,
            'listings': serializer.data
        })

    def post(self, request):
        serializer = ListingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(seller=request.user)
            return Response({
                'success': True,
                'listing': serializer.data
            }, status=201)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

class SellerListingDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Listing.objects.get(pk=pk, seller=self.request.user)
        except Listing.DoesNotExist:
            return None

    def get(self, request, pk):
        listing = self.get_object(pk)
        if not listing:
            return Response({'success': False, 'error': 'Not found'}, status=404)
        serializer = ListingSerializer(listing)
        return Response({'success': True, 'listing': serializer.data})

    def put(self, request, pk):
        listing = self.get_object(pk)
        if not listing:
            return Response({'success': False, 'error': 'Not found'}, status=404)
        
        serializer = ListingSerializer(listing, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'listing': serializer.data})
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

    def delete(self, request, pk):
        listing = self.get_object(pk)
        if not listing:
            return Response({'success': False, 'error': 'Not found'}, status=404)
        listing.delete()
        return Response({'success': True}, status=204)

class SellerOrdersAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(listing__seller=request.user)
        serializer = OrderSerializer(orders, many=True)
        return Response({
            'success': True,
            'orders': serializer.data
        })

class SellerOrderDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Order.objects.get(pk=pk, listing__seller=self.request.user)
        except Order.DoesNotExist:
            return None

    def get(self, request, pk):
        order = self.get_object(pk)
        if not order:
            return Response({'success': False, 'error': 'Not found'}, status=404)
        serializer = OrderSerializer(order)
        return Response({'success': True, 'order': serializer.data})

    def patch(self, request, pk):
        order = self.get_object(pk)
        if not order:
            return Response({'success': False, 'error': 'Not found'}, status=404)
        
        serializer = OrderSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'order': serializer.data})
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

class SellerStatsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        completed_orders = Order.objects.filter(
            listing__seller=request.user,
            status='completed'
        )
        pending_orders = Order.objects.filter(
            listing__seller=request.user,
            status='pending'
        )
        
        total_sales = sum(order.price_at_purchase for order in completed_orders)
        available_balance = total_sales * 0.85  # Assuming 15% platform fee
        
        return Response({
            'success': True,
            'stats': {
                'total_sales': total_sales,
                'pending_orders': pending_orders.count(),
                'completed_orders': completed_orders.count(),
                'balance': available_balance
            }
        })

class WithdrawalAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WithdrawalSerializer(data=request.data)
        if serializer.is_valid():
            # Check available balance
            stats = SellerStatsAPI().get(request).data['stats']
            if serializer.validated_data['amount'] > stats['balance']:
                return Response({
                    'success': False,
                    'error': 'Amount exceeds available balance'
                }, status=400)
                
            serializer.save(seller=request.user)
            return Response({
                'success': True,
                'withdrawal': serializer.data
            }, status=201)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)