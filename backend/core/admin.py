from django.contrib import admin

from .models import Entry, EntryLink, Naming, NamingLink, NamingVersion


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


class NamingVersionInline(admin.TabularInline):
    model = NamingVersion
    extra = 0
    readonly_fields = ("label", "created_at")
    can_delete = False  # 이름의 변천은 지우지 않는다

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Naming)
class NamingAdmin(admin.ModelAdmin):
    list_display = ("label", "created_at")
    search_fields = ("label", "versions__label")
    readonly_fields = ("label", "created_at")
    inlines = [NamingVersionInline]


@admin.register(NamingLink)
class NamingLinkAdmin(admin.ModelAdmin):
    list_display = ("naming", "entry", "author", "status", "created_at")
    list_filter = ("author", "status")


@admin.register(EntryLink)
class EntryLinkAdmin(admin.ModelAdmin):
    list_display = ("from_entry", "to_entry", "author", "status", "created_at")
    list_filter = ("author", "status")
