from django.contrib import admin
from .models import Genre, Filmwork, GenreFilmwork, Person, PersonFilmwork


class GenreFilmworkInline(admin.TabularInline):
    model = GenreFilmwork
    extra = 0


class PersonFilmworkInline(admin.TabularInline):
    model = PersonFilmwork
    extra = 0
    autocomplete_fields = ("person",)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Filmwork)
class FilmworkAdmin(admin.ModelAdmin):
    inlines = (GenreFilmworkInline, PersonFilmworkInline)
    search_fields = ("title", "description")
    list_display = ("title", "creation_date", "rating", "get_genres")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("genres")

    def get_genres(self, obj):
        return ", ".join((g.name for g in obj.genres.all()))

    get_genres.short_description = "Жанры фильма"


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("full_name",)
    search_fields = ("full_name",)
