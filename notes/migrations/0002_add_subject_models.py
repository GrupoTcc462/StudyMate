# notes/migrations/0002_add_subject_models.py
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def migrate_subjects_to_fk(apps, schema_editor):
    """
    Migra matérias de CharField para ForeignKey
    """
    Note = apps.get_model('notes', 'Note')
    Subject = apps.get_model('notes', 'Subject')
    
    # Coletar matérias únicas dos notes existentes
    subject_names = set()
    for note in Note.objects.all():
        if note.subject_text and note.subject_text.strip():
            subject_names.add(note.subject_text.strip())
    
    # Criar objetos Subject
    subject_map = {}
    for name in subject_names:
        slug = slugify(name)
        # Garantir slug único
        base_slug = slug
        counter = 1
        while Subject.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        subject_obj = Subject.objects.create(
            name=name,
            slug=slug,
            is_active=True
        )
        subject_map[name] = subject_obj
    
    # Associar notes aos subjects
    for note in Note.objects.all():
        if note.subject_text and note.subject_text.strip():
            subject_obj = subject_map.get(note.subject_text.strip())
            if subject_obj:
                note.subject_fk = subject_obj
                note.save(update_fields=['subject_fk'])


def reverse_migration(apps, schema_editor):
    """
    Reverte: copia nome do Subject de volta para texto
    """
    Note = apps.get_model('notes', 'Note')
    
    for note in Note.objects.all():
        if note.subject_fk:
            note.subject_text = note.subject_fk.name
            note.save(update_fields=['subject_text'])


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0001_initial'),
    ]

    operations = [
        # 1. Criar modelo Subject
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60, unique=True, verbose_name='Nome')),
                ('slug', models.SlugField(max_length=80, unique=True, verbose_name='Slug')),
                ('is_active', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Matéria',
                'verbose_name_plural': 'Matérias',
                'ordering': ['name'],
            },
        ),
        
        # 2. Criar NoteView
        migrations.CreateModel(
            name='NoteView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('viewed_at', models.DateTimeField(auto_now_add=True, verbose_name='Visualizado em')),
                ('note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='views_log', to='notes.note', verbose_name='Note')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.user', verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Visualização',
                'verbose_name_plural': 'Visualizações',
            },
        ),
        
        # 3. Criar NoteRecommendation
        migrations.CreateModel(
            name='NoteRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Recomendado em')),
                ('note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendations', to='notes.note', verbose_name='Note')),
                ('professor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='given_recommendations', to='accounts.user', verbose_name='Professor')),
                ('subject', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='notes.subject', verbose_name='Matéria')),
            ],
            options={
                'verbose_name': 'Recomendação',
                'verbose_name_plural': 'Recomendações',
                'ordering': ['-created_at'],
            },
        ),
        
        # 4. Renomear campo subject para subject_text (temporário)
        migrations.RenameField(
            model_name='note',
            old_name='subject',
            new_name='subject_text',
        ),
        
        # 5. Remover índice antigo do subject
        migrations.RemoveIndex(
            model_name='note',
            name='notes_note_subject_435eb9_idx',
        ),
        
        # 6. Adicionar novo campo subject_fk (FK temporária)
        migrations.AddField(
            model_name='note',
            name='subject_fk',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='notes_temp',
                to='notes.subject',
                verbose_name='Matéria'
            ),
        ),
        
        # 7. Migrar dados
        migrations.RunPython(migrate_subjects_to_fk, reverse_migration),
        
        # 8. Remover campo antigo subject_text
        migrations.RemoveField(
            model_name='note',
            name='subject_text',
        ),
        
        # 9. Renomear subject_fk para subject
        migrations.RenameField(
            model_name='note',
            old_name='subject_fk',
            new_name='subject',
        ),
        
        # 10. Atualizar related_name
        migrations.AlterField(
            model_name='note',
            name='subject',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='notes',
                to='notes.subject',
                verbose_name='Matéria'
            ),
        ),
        
        # 11. Adicionar índice no novo campo subject
        migrations.AddIndex(
            model_name='note',
            index=models.Index(fields=['subject'], name='notes_note_subject_new_idx'),
        ),
        
        # 12. Adicionar constraints
        migrations.AlterUniqueTogether(
            name='noteview',
            unique_together={('user', 'note')},
        ),
        migrations.AlterUniqueTogether(
            name='noterecommendation',
            unique_together={('note', 'professor')},
        ),
        migrations.AddIndex(
            model_name='noteview',
            index=models.Index(fields=['note', 'user'], name='notes_notev_note_user_idx'),
        ),
    ]