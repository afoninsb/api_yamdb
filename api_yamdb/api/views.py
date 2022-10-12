from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, mixins, viewsets, filters
from rest_framework.decorators import api_view
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from api.filters import TitleFilter
from api.permissions import (
    IsAdmin,
    IsAdminOrReadOnly,
    IsAuthorModeratorAdminOrReadOnly
)
from api.serializers import (
    CategorySerializer,
    GenreSerializer,
    TitleReadSerializer,
    TitleWriteSerializer,
    ReviewSerializer,
    CommentSerializer,
    SignupSerializer,
    UserSerializer,
    TokenSerializer,
    # UserMePatchSerializer,
)
from reviews.models import (
    Category,
    Genre,
    Title,
    Review,
)
from users.models import User


@api_view(('POST',))
def signup(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = serializer.validated_data['username']
    email = serializer.validated_data['email']
    try:
        user, _ = User.objects.get_or_create(
            username=username,
            email=email,
        )
    except IntegrityError:
        return Response(
            'Такой пары username-email нет в базе данных',
            status=status.HTTP_400_BAD_REQUEST
        )

    confirmation_code = default_token_generator.make_token(user)
    send_mail(
        subject='confirmation_code',
        message=f"{username} - {confirmation_code}",
        from_email=settings.FROM,
        recipient_list=[email],
        fail_silently=False,
    )
    return Response(serializer.validated_data, status=status.HTTP_200_OK)


@api_view(('POST',))
def get_token(request):
    serializer = TokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = get_object_or_404(
        User, username=serializer.validated_data['username'])
    confirmation_code = serializer.validated_data['confirmation_code']
    if not default_token_generator.check_token(user, confirmation_code):
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    token = AccessToken.for_user(user)
    return Response(
        {'token': str(token.access_token)},
        status=status.HTTP_200_OK
    )


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdmin,)
    search_fields = ('username',)
    lookup_field = 'username'

    @action(
        detail=False,
        methods=('get', 'patch'),
        url_path='me',
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        instance = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        serializer = self.get_serializer(
            instance,
            request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['role'] = instance.role
        serializer.save()
        return Response(serializer.validated_data)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = (IsAuthorModeratorAdminOrReadOnly,
                          IsAuthenticatedOrReadOnly)

    def get_queryset(self):
        title = get_object_or_404(Title, pk=self.kwargs.get("title_id"))

        return title.reviews.all()

    def perform_create(self, serializer):
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, id=title_id)
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = (IsAuthorModeratorAdminOrReadOnly,
                          IsAuthenticatedOrReadOnly)

    def get_queryset(self):
        review = get_object_or_404(Review, pk=self.kwargs.get("review_id"))
        return review.comments.all()

    def perform_create(self, serializer):
        title_id = self.kwargs.get('title_id')
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(Review, id=review_id, title=title_id)
        serializer.save(author=self.request.user, review=review)


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
    permission_classes = (IsAdminOrReadOnly,)


class GenreViewSet(CreateRetrieveViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'
    ordering_fields = ('name')
    permission_classes = (IsAdminOrReadOnly,)


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.all().annotate(
        Avg("reviews__score")
    ).order_by("name")
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitleFilter
    permission_classes = (IsAdminOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return TitleReadSerializer
        return TitleWriteSerializer
