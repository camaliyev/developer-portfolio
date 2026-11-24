from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "ip_address", "created_at")
    fields = ("name", "email", "subject", "message", "is_read", "ip_address", "created_at")
    date_hierarchy = "created_at"
    actions = ["mark_read", "mark_unread"]

    def has_add_permission(self, request):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        # Opening a message marks it as read.
        ContactMessage.objects.filter(pk=object_id, is_read=False).update(is_read=True)
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.action(description="Mark selected messages as read")
    def mark_read(self, request, queryset):
        self.message_user(request, f"Marked {queryset.update(is_read=True)} message(s) as read.")

    @admin.action(description="Mark selected messages as unread")
    def mark_unread(self, request, queryset):
        self.message_user(request, f"Marked {queryset.update(is_read=False)} message(s) as unread.")
