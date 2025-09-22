from django.db import migrations, models
import uuid
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Genre",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255, verbose_name="name")),
                ("description", models.TextField(blank=True, verbose_name="description")),
            ],
            options={
                "verbose_name": "genre",
                "verbose_name_plural": "genres",
                "db_table": 'content"."genre',
            },
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=255, verbose_name="full_name")),
            ],
            options={
                "verbose_name": "person",
                "verbose_name_plural": "persons",
                "db_table": 'content"."person',
            },
        ),
        migrations.CreateModel(
            name="Filmwork",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=255, verbose_name="title")),
                ("description", models.TextField(blank=True, verbose_name="description")),
                (
                    "creation_date",
                    models.DateField(blank=True, null=True, verbose_name="creation_date"),
                ),
                (
                    "file_path",
                    models.CharField(blank=True, max_length=255, verbose_name="file_path"),
                ),
                (
                    "rating",
                    models.FloatField(
                        blank=True,
                        null=True,
                        validators=[models.Min(0), models.Max(100)],
                        verbose_name="rating",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("movie", "movie"), ("tv_show", "tv_show")],
                        default="movie",
                        max_length=255,
                    ),
                ),
            ],
            options={
                "verbose_name": "film_work",
                "verbose_name_plural": "film_works",
                "db_table": 'content"."film_work',
            },
        ),
        migrations.CreateModel(
            name="GenreFilmwork",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "film_work",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="genre_links",
                        to="movies.filmwork",
                    ),
                ),
                (
                    "genre",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="filmwork_links",
                        to="movies.genre",
                    ),
                ),
            ],
            options={
                "db_table": 'content"."genre_film_work',
            },
        ),
        migrations.CreateModel(
            name="PersonFilmwork",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[("actor", "actor"), ("director", "director")], max_length=255
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "film_work",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="person_links",
                        to="movies.filmwork",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="filmwork_links",
                        to="movies.person",
                    ),
                ),
            ],
            options={
                "db_table": 'content"."person_film_work',
            },
        ),
        migrations.AddField(
            model_name="filmwork",
            name="genres",
            field=models.ManyToManyField(
                related_name="filmworks", through="movies.GenreFilmwork", to="movies.genre"
            ),
        ),
        migrations.AddConstraint(
            model_name="genrefilmwork",
            constraint=models.UniqueConstraint(
                fields=("film_work", "genre"), name="unique_genre_film_work"
            ),
        ),
        migrations.AddConstraint(
            model_name="personfilmwork",
            constraint=models.UniqueConstraint(
                fields=("person", "film_work", "role"), name="unique_person_film_work_role"
            ),
        ),
    ]
