import logging
from django.db.models import Q
from .models import *
from .serializers import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ChatFilter, MessageFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.request import Request
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.authentication import SessionAuthentication


logger = logging.getLogger(__name__)

class SignUpView(generics.GenericAPIView):
    serializer_class = SignUpSerializer
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="SignUp a new user",
        operation_description="Create a new user account by providing the required user information.",
        request_body=SignUpSerializer,
        responses={
            201: "User Created Successfully",
            400: "Bad Request - Invalid input data"
        }
    )
    def post(self, request: Request):
        data = request.data
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            user = serializer.save()
            user.save()
            response_data = {
                "message": "User Created Successfully",
                "data": serializer.data,
            }
            return Response(data=response_data, status=status.HTTP_201_CREATED)

        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogInView(APIView):
    """
    A View to handle user login and retrieve JWT tokens.

    Supported HTTP methods: POST, GET.
    """

    permission_classes = []

    @swagger_auto_schema(
        operation_summary="Login authenticated users",
        operation_description="Login a user with the provided email and password, and return JWT tokens.",
        responses={
            200: "Login Successful",
            401: "Invalid email or password",
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="User's email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="User's password"),
            },
            required=["email", "password"],
        ),
    )
    def post(self, request):
        """
        Login a user with the provided email and password, and return JWT tokens.
        """
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(email=email, password=password)
        login(request, user)
        if user is not None:
            response_data = {
                "message": "Login Successful",
            }
            return Response(data=response_data, status=status.HTTP_200_OK)
        else:
            return Response(data={"message": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(
        operation_summary="Get User Info",
        operation_description="Get information about the current authenticated user and their authentication status.",
        responses={200: "User information"},
    )
    def get(self, request):
        """
        Get information about the current authenticated user and their authentication status.
        """
        response_data = {
            "user": str(request.user),
            "auth": str(request.auth)
        }
        return Response(data=response_data, status=status.HTTP_200_OK)


class SearchUserView(APIView):
    """
    A view to search for users based on a query.
    """

    @swagger_auto_schema(
        operation_summary="Search Users",
        operation_description="Search for users based on a query.",
        responses={200: "User search results"},
        manual_parameters=[
            openapi.Parameter(
                "query",
                openapi.IN_QUERY,
                description="Search query",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
    )
    def get(self, request):
        # Get the query parameter from the request
        query = request.query_params.get('query')

        if not query:
            return Response({'type': 'error', 'data': {'message': 'Invalid email query'}}, status=status.HTTP_400_BAD_REQUEST)

        # Search for users whose username contains the query
        users = get_user_model().objects.filter(email__icontains=query)

        # Serialize the found users
        user_serializer = UserSerializer(instance=users, many=True)

        return Response(user_serializer.data, status=status.HTTP_200_OK)


class ProfileViewSet(ModelViewSet):
    """
    A ViewSet for managing Cartitems.

    Supported HTTP methods: GET, POST, PATCH, DELETE.

    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    parser_classes = (MultiPartParser, FormParser)

    http_method_names = ["get", "put", "delete"]

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List User Profile",
        operation_description="Retrieve a list of authenicated User profile.",
        responses={200: ProfileSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        user = request.user
        if user.is_anonymous:
            raise PermissionDenied("Authentication required to access profile")
        if user.is_staff:
            queryset = Profile.objects.all()
        else:
            queryset = Profile.objects.filter(user=user)

        serializer = ProfileSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Retrieve a User Profile",
        operation_description="Retrieve details of a User Profile.",
        responses={200: ProfileSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update of a User Profile",
        operation_description="Update specific fields of a User Profile.",
        responses={200: ProfileSerializer()}
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Delete a User Profile",
        operation_description="Delete a specific User Profile.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        user = request.user
        profile = self.get_object()
        if not user.is_staff and profile.user != user:
            raise PermissionDenied("You do not have permission to delete this profile")
            
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    http_method_names = ["get", "put", "post", "delete", "options", "head"]

    serializer_class = MessageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['name']
    
    @swagger_auto_schema(
        operation_summary="List messages in a chat",
        operation_description="Retrieve a list of messages for the authenticated user in a chat.",
        responses={200: MessageSerializer(many=True), 400: "Bad Request", 403: "Forbidden", 404: "Not Found"}
    )
    def list(self, request, *args, **kwargs):
        chat_id = self.kwargs['chat_id']
        user = request.user
        if user.is_anonymous:
            raise PermissionDenied("Authentication required to access messages.")
        queryset = Message.objects.filter(chat__id=chat_id)
        serializer = MessageSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Retrieve a message",
        operation_description="Retrieve a specific message.",
        responses={200: MessageSerializer(), 400: "Bad Request", 403: "Forbidden", 404: "Not Found"}
    )
    def retrieve(self, request, *args, **kwargs):
        message = get_object_or_404(Message, pk=kwargs['pk'])
        serializer = MessageSerializer(message)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update a message",
        operation_description="Update specific fields of a message.",
        request_body=MessageSerializer,
        responses={200: MessageSerializer()}
    )
    def update(self, request, *args, **kwargs):
        message = get_object_or_404(Message, pk=kwargs['pk'])
        serializer = MessageSerializer(message, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Delete a message",
        operation_description="Delete a specific message.",
        responses={
            204: "No Content",
            404: "Not Found",
            403: "Forbidden",
        }
    )
    def destroy(self, request, *args, **kwargs):
        message = get_object_or_404(Message, pk=kwargs['pk'])
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary="Create a message",
        operation_description="Create a message with the given data.",
        request_body=MessageSerializer,
        responses={201: MessageSerializer(), 400: "Bad Request"}
    )
    def create(self, request, *args, **kwargs): 
        chat_id = self.kwargs['chat_id']
        serializer = MessageSerializer(data=request.data, context={"user_id": request.user.id, "chat_id": chat_id})
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated()]

    def get_serializer_class(self):
        return MessageSerializer

    def get_serializer_context(self):
        return {"chat_id": self.kwargs["chat_pk"]}

    def get_queryset(self):
        return Message.objects.filter(chat_id=self.kwargs['chat_pk']).order_by('-timestamp')


class ChatViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ChatFilter
    search_fields = ['name']

    http_method_names = ["get", "patch", "post", "delete", "options", "head"]

    @swagger_auto_schema(
        operation_summary="List chats",
        operation_description="Retrieve a list of chats for the authenticated user.",
        responses={200: ChatSerializer(many=True), 400: "Bad Request", 403: "Forbidden", 404: "Not Found"}
    )
    def list(self, request, *args, **kwargs):
        user = request.user
        if user.is_anonymous:
            raise PermissionDenied("Authentication required to access chats.")
        queryset = Chat.objects.filter(Q(msg_receiver=user) | Q(msg_sender=user))
        serializer = ChatSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Retrieve a chat",
        operation_description="Retrieve a specific chat.",
        responses={200: ChatSerializer(), 400: "Bad Request", 403: "Forbidden", 404: "Not Found"}
    )
    def retrieve(self, request, *args, **kwargs):
        chat = get_object_or_404(Chat, pk=kwargs['pk'])
        serializer = ChatSerializer(chat)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Partial Update of a Chat",
        operation_description="Update specific fields of a chat.",
        request_body=ChatSerializer,
        responses={200: ChatSerializer()}
    )
    def update(self, request, *args, **kwargs):
        chat = get_object_or_404(Chat, pk=kwargs['pk'])
        serializer = ChatSerializer(chat, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Delete a Chat",
        operation_description="Delete a specific chat.",
        responses={
            204: "No Content",
            404: "Not Found",
            403: "Forbidden",
        }
    )
    def destroy(self, request, *args, **kwargs):
        chat = get_object_or_404(Chat, pk=kwargs['pk'])
        chat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary="Create a Chat",
        operation_description="Create a chat with the given data.",
        request_body=ChatSerializer,
        responses={201: ChatSerializer(), 400: "Bad Request"}
    )
    def create(self, request, *args, **kwargs): 
        serializer = ChatSerializer(data=request.data, context={"user_id": request.user.id})
        serializer.is_valid(raise_exception=True)
        chat = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.request.method in ["PUT", "DELETE"]:
            return [IsAuthenticated()]

    def get_queryset(self):
        return Chat.objects.filter(Q(msg_receiver=user) | Q(msg_sender=user))
    