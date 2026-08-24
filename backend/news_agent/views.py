from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import NewsAlert
from .serializers import NewsAlertSerializer

class NewsAlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NewsAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NewsAlert.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        alert = self.get_object()
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        return Response({"status": "ok"})