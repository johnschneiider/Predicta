from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('betfair', '0002_betfairticksnapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='betfairevent',
            name='competition_id',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='betfairevent',
            name='competition_name',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
