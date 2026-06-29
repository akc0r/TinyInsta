from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("realtime", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("like", "Like"),
                    ("comment", "Comment"),
                    ("follow", "Follow"),
                    ("mention", "Mention"),
                    ("repost", "Repost"),
                ],
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="UserHandle",
            fields=[
                ("user_id", models.UUIDField(primary_key=True, serialize=False)),
                ("username", models.CharField(db_index=True, max_length=150, unique=True)),
            ],
            options={"db_table": "user_handles"},
        ),
    ]
