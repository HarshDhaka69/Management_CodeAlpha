from django.contrib import admin
from .models import Project, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    fields = ('user', 'role', 'joined_at')
    readonly_fields = ('joined_at',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'get_member_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'owner__username')
    inlines = [ProjectMemberInline]
    readonly_fields = ('created_at', 'updated_at')

    def get_member_count(self, obj):
        return obj.get_member_count()
    get_member_count.short_description = 'Members'


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'role', 'joined_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'project__name')
