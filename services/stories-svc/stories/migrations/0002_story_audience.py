from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='audience',
            field=models.CharField(
                choices=[('public', 'Public'), ('close_friends', 'Close friends')],
                default='public',
                max_length=16,
            ),
        ),
    ]
