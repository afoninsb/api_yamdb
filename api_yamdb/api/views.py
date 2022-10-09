from django.shortcuts import get_object_or_404
from django.db.models import Avg
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, mixins, viewsets, filters
from django.core import mail
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from django.contrib.auth.tokens import default_token_generator
from rest_framework_simplejwt.tokens import RefreshToken
from reviews.models import (
    Category,
    Genre,
    Title,
    Review,
    Comment,
    User,
)
from .serializers import (
    CategorySerializer,
    GenreSerializer,
    TitleSerializer,
    ReviewSerializer,
    CommentSerializer,
    SignupSerializer,
    UserSerializer,
    TokenSerializer,
    UserMePatchSerializer,
)
from api.permissions import (
    IsAdmin,
    IsAuthorOrReadOnly,
    IsModerator,
    IsAdminOrReadOnly
)
from rest_framework.decorators import action


@api_view(['POST'])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():

        user, obj = User.objects.get_or_create(
            username=serializer.data['username'],
            email=serializer.data['email'],
        )

        confirmation_code = default_token_generator.make_token(user)
        with mail.get_connection() as connection:
            mail.EmailMessage(
                'confirmation_code',
                f"{serializer.data['username']} - {confirmation_code}",
                'as@sdasd.ru',
                [serializer.data['email']],
                connection=connection,
            ).send()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_token(request):
    serializer = TokenSerializer(data=request.data)
    if serializer.is_valid():
        user = get_object_or_404(
            User, username=serializer.data['username'])
        confirmation_code = serializer.data['confirmation_code']
        if default_token_generator.check_token(user, confirmation_code):
            token = RefreshToken.for_user(user)
            return Response(
                {'token': str(token.access_token)},
                status=status.HTTP_200_OK
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdmin,)
    pagination_class = LimitOffsetPagination
    search_fields = ('username',)
    lookup_field = 'username'

    @action(
        detail=False, methods=['get', 'patch'],
        url_path='me', permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        if request.method == 'GET':
            user = request.user
            serializer = self.get_serializer(user, many=False)
            return Response(serializer.data)
        if request.method == 'PATCH':
            instance = request.user
            user = request.data
            serializer = UserMePatchSerializer(
                instance, user, many=False, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthorOrReadOnly, IsAdmin, IsModerator]
    ordering_fields = ('pub_date')


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthorOrReadOnly, IsAdmin, IsModerator]
    ordering_fields = ('pub_date')


class CreateRetrieveViewSet(
        mixins.CreateModelMixin,
        mixins.DestroyModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet):
    pass


class CategoryViewSet(CreateRetrieveViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'
    ordering_fields = ('name')
    permission_classes = (
        IsAdminOrReadOnly,
    )


class GenreViewSet(CreateRetrieveViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'
    ordering_fields = ('name')
    permission_classes = (
        IsAdminOrReadOnly,
    )


class TitleViewSet(CreateRetrieveViewSet):
    queryset = Title.objects.all().annotate(
        Avg("reviews__score")
    ).order_by("name")
    serializer_class = TitleSerializer
