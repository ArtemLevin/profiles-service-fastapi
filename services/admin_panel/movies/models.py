import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class TimeStampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Genre(UUIDMixin, TimeStampedMixin):
    name = models.CharField("name", max_length=255)
    description = models.TextField("description", blank=True)

    class Meta:
        db_table = 'content"."genre'
        verbose_name = "genre"
        verbose_name_plural = "genres"

    def __str__(self) -> str:
        return self.name


class Filmwork(UUIDMixin, TimeStampedMixin):
    class ContentType(models.TextChoices):
        MOVIE = "movie", "movie"
        TV_SHOW = "tv_show", "tv_show"

    title = models.CharField("title", max_length=255)
    description = models.TextField("description", blank=True)
    creation_date = models.DateField("creation_date", null=True, blank=True)
    file_path = models.CharField("file_path", max_length=255, blank=True)
    rating = models.FloatField(
        "rating", blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    type = models.CharField(max_length=255, choices=ContentType.choices, default=ContentType.MOVIE)
    genres = models.ManyToManyField(Genre, through="GenreFilmwork", related_name="filmworks")

    class Meta:
        db_table = 'content"."film_work'
        verbose_name = "film_work"
        verbose_name_plural = "film_works"

    def __str__(self):
        return self.title


class GenreFilmwork(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    film_work = models.ForeignKey(Filmwork, on_delete=models.CASCADE, related_name="genre_links")
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, related_name="filmwork_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'content"."genre_film_work'
        constraints = [
            models.UniqueConstraint(fields=["film_work", "genre"], name="unique_genre_film_work")
        ]


class Person(UUIDMixin, TimeStampedMixin):
    full_name = models.CharField("full_name", max_length=255)

    class Meta:
        db_table = 'content"."person'
        verbose_name = "person"
        verbose_name_plural = "persons"

    def __str__(self):
        return self.full_name


class PersonFilmwork(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="filmwork_links")
    film_work = models.ForeignKey(Filmwork, on_delete=models.CASCADE, related_name="person_links")
    role = models.CharField(max_length=255, choices=[("actor", "actor"), ("director", "director")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'content"."person_film_work'
        constraints = [
            models.UniqueConstraint(
                fields=["person", "film_work", "role"], name="unique_person_film_work_role"
            )
        ]
