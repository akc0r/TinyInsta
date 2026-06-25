import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('author_id', models.UUIDField()),
                ('media_id', models.UUIDField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
            ],
            options={
                'db_table': 'stories',
            },
        ),
        migrations.CreateModel(
            name='StoryView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('viewer_id', models.UUIDField()),
                ('viewed_at', models.DateTimeField(auto_now_add=True)),
                ('story', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='views', to='stories.story')),
            ],
            options={
                'db_table': 'story_views',
            },
        ),
        migrations.AddIndex(
            model_name='story',
            index=models.Index(fields=['author_id', 'expires_at'], name='stories_author_expires_idx'),
        ),
        migrations.AddConstraint(
            model_name='storyview',
            constraint=models.UniqueConstraint(fields=('story', 'viewer_id'), name='uniq_story_view'),
        ),
    ]
