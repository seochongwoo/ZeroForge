from django.contrib import admin

from .models import Entry


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("written_at", "source", "created_at")
    list_filter = ("source",)
    search_fields = ("content",)
    ordering = ("-written_at",)

    # Entry는 불변이다
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [f.name for f in self.model._meta.fields]
        return []
