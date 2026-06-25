from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Like',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('post_id', models.UUIDField()),
                ('user_id', models.UUIDField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'likes',
            },
        ),
        migrations.AddIndex(
            model_name='like',
            index=models.Index(fields=['post_id'], name='likes_post_id_idx'),
        ),
        migrations.AddConstraint(
            model_name='like',
            constraint=models.UniqueConstraint(fields=('post_id', 'user_id'), name='uniq_like'),
        ),
    ]
