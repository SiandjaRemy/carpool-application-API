from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from django.utils import timezone


from passengers.serializers import (
    PassengerModelSerializer,
)

from utils.permissions import IsCreator, IsCreatorOrReadOnly
from utils.paginators import CustomPageNumberPagination



# class GetUserReviewGenericView(generics.ListAPIView):
#     serializer_class = ViewReviewModelSerializer
#     pagination_class = CustomPageNumberPagination
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         user_pk = self.kwargs.get("user_pk")
#         queryset = Review.objects.select_related("reviewer", "reviewed_user", "transaction").filter(reviewed_user_id=user_pk).order_by("-created_at")
#         # Think about annotating the count and reusing it below
#         return queryset

    
#     """Get all the reviews received by a particular user"""
#     def get(self, request, user_pk=None):
#         if not user_pk:
#             raise ValidationError({"message": "user id required"})

#         user_reviews = self.get_queryset()

#         if len(user_reviews) == 0:
#             user_exist = User.objects.filter(id=user_pk).exists()
#             if not user_exist:
#                 raise ValidationError({"message": "Corresponding user does not exist"})

#         paginator = self.pagination_class()
#         page = paginator.paginate_queryset(user_reviews, request=request)

#         if page is not None:
#             serializer = ViewReviewModelSerializer(page, many=True)
#             return paginator.get_paginated_response(serializer.data)

#         serializer = ViewReviewModelSerializer(user_reviews, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
# class CreateReviewForTransactionGenericView(generics.CreateAPIView):
#     serializer_class = CreateReviewModelSerializer
#     pagination_class = CustomPageNumberPagination
#     permission_classes = [IsAuthenticated]
    
#     def get_queryset(self):
#         user = self.request.user
#         transaction_pk = self.kwargs.get("transaction_pk")
#         # queryset = Review.objects.filter(Q(reviewer=user) | Q(reviewed_user=user), transaction_id=transaction_pk).order_by("-created_at")
#         queryset = Review.objects.filter(Q(reviewer=user) | Q(reviewed_user=user)).order_by("-created_at")
#         return queryset
    
#     def get_serializer_context(self):
#         user = self.request.user
#         context = {
#             "user": user,
#         }
#         return context

    
#     """Allow transaction participant to review the other transaction participant"""
#     def post(self, request):
#         data = self.request.data

#         serializer = self.get_serializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
# class GetReviewsForTransactionGenericView(generics.ListAPIView):
#     serializer_class = ViewReviewModelSerializer
#     pagination_class = CustomPageNumberPagination
#     # No pagination needed sinc the max count is 2
    
#     def get_queryset(self):
#         user = self.request.user
#         transaction_pk = self.kwargs.get("transaction_pk")
#         queryset = Review.objects.select_related("reviewer", "reviewed_user", "transaction").filter(Q(reviewer=user) | Q(reviewed_user=user), transaction_id=transaction_pk).order_by("-created_at")
#         # Think about annotating the count and reusing it below
#         return queryset
    
#     """Allow transaction participant to view the reviews made for that transaction ie his and that of the other participant"""
#     def get(self, request, transaction_pk=None):
#         if not transaction_pk:
#             raise ValidationError({"message": "transaction id required"})

#         transaction_reviews = self.get_queryset()

#         if len(transaction_reviews) == 0:
#             transaction_exists = Transaction.objects.filter(id=transaction_pk).exists()
#             if not transaction_exists:
#                 raise ValidationError(
#                     {"message": "Corresponding transaction does not exist"}
#                 )

#         # No pagination needed sinc the max count is 2

#         # paginator = self.pagination_class()
#         # page = paginator.paginate_queryset(transaction_reviews, request=request)

#         # if page is not None:
#         #     serializer = ViewReviewModelSerializer(page, many=True)
#         #     return paginator.get_paginated_response(serializer.data)

#         serializer = ViewReviewModelSerializer(transaction_reviews, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

