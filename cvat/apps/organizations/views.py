# Copyright (C) 2021 Intel Corporation
#
# SPDX-License-Identifier: MIT

from rest_framework import mixins, viewsets
from rest_framework.permissions import SAFE_METHODS
from django.utils.crypto import get_random_string
from cvat.apps.iam.permissions import (
    InvitationPermission, MembershipPermission, OrganizationPermission)
from .models import Invitation, Membership, Organization

from .serializers import (
    InvitationReadSerializer, InvitationWriteSerializer,
    MembershipReadSerializer, MembershipWriteSerializer,
    OrganizationReadSerializer, OrganizationWriteSerializer)

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    ordering = ['-id']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        permission = OrganizationPermission(self.request, self, None)
        return permission.filter(queryset)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return OrganizationReadSerializer
        else:
            return OrganizationWriteSerializer

    def perform_create(self, serializer):
        extra_kwargs = { 'owner': self.request.user }
        if not serializer.validated_data.get('name'):
            extra_kwargs.update({ 'name': serializer.validated_data['slug'] })
        serializer.save(**extra_kwargs)

class MembershipViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
    mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = Membership.objects.all()
    ordering = ['-id']
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return MembershipReadSerializer
        else:
            return MembershipWriteSerializer


    def get_queryset(self):
        queryset = super().get_queryset()
        organization = self.request.iam_context['organization']
        if organization:
            queryset = queryset.filter(organization=organization)
        permission = MembershipPermission(self.request, self, None)
        return permission.filter(queryset)


class InvitationViewSet(viewsets.ModelViewSet):
    queryset = Invitation.objects.all()
    ordering = ['-created_date']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return InvitationReadSerializer
        else:
            return InvitationWriteSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        permission = InvitationPermission(self.request, self, None)
        return permission.filter(queryset)

    def perform_create(self, serializer):
        extra_kwargs = {
            'owner': self.request.user,
            'key': get_random_string(length=64),
        }
        serializer.save(**extra_kwargs)