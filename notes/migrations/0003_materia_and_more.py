# Generated manually for Materia model
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0002_alter_note_description_alter_note_file_type_and_more'),
    ]

    operations = [
        # 1. Criar model Materia
        migrations.CreateModel(
            name='Materia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=50, unique=True, verbose_name='Nome da Matéria')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
            ],
            options={
                'verbose_name': 'Matéria',
                'verbose_name_plural': 'Matérias',
                'ordering': ['nome'],
            },
        ),
        
        # 2. Adicionar novo campo subject_new (ForeignKey) mantendo o antigo
        migrations.AddField(
            model_name='note',
            name='subject_new',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='notes',
                to='notes.materia',
                verbose_name='Matéria'
            ),
        ),
    ]