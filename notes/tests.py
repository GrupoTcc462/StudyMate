from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from notes.models import Note, Subject, NoteView, NoteRecommendation, NoteLike


class SubjectModelTest(TestCase):
    """Testes para o modelo Subject"""
    
    def setUp(self):
        self.subject = Subject.objects.create(
            name='Matemática',
            slug='matematica',
            is_active=True
        )
    
    def test_subject_creation(self):
        """Testa criação de matéria"""
        self.assertEqual(self.subject.name, 'Matemática')
        self.assertEqual(str(self.subject), 'Matemática')
    
    def test_subject_unique_name(self):
        """Testa unicidade do nome"""
        with self.assertRaises(Exception):
            Subject.objects.create(name='Matemática', slug='matematica2')


class NoteViewCountTest(TestCase):
    """Testes para contagem de visualizações"""
    
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.professor = User.objects.create_user(
            username='prof1', 
            password='pass123',
            user_type='professor'
        )
        
        self.subject = Subject.objects.create(name='Física', slug='fisica')
        self.note = Note.objects.create(
            author=self.professor,
            title='Test Note',
            description='Test',
            file_type='TXT',
            subject=self.subject
        )
    
    def test_view_count_authenticated_user(self):
        """Testa que visualização é contada uma vez por usuário"""
        self.client.login(username='user1', password='pass123')
        
        # Primeira visualização
        response = self.client.get(reverse('notes:detail', args=[self.note.pk]))
        self.assertEqual(response.status_code, 200)
        self.note.refresh_from_db()
        first_views = self.note.views
        
        # Segunda visualização (mesmo usuário)
        response = self.client.get(reverse('notes:detail', args=[self.note.pk]))
        self.note.refresh_from_db()
        
        # Views não deve aumentar
        self.assertEqual(self.note.views, first_views)
        
        # Verificar que NoteView foi criado
        self.assertTrue(NoteView.objects.filter(user=self.user1, note=self.note).exists())
    
    def test_view_count_different_users(self):
        """Testa que diferentes usuários aumentam views"""
        initial_views = self.note.views
        
        # User 1 visualiza
        self.client.login(username='user1', password='pass123')
        self.client.get(reverse('notes:detail', args=[self.note.pk]))
        self.note.refresh_from_db()
        views_after_user1 = self.note.views
        
        # User 2 visualiza
        self.client.logout()
        self.client.login(username='user2', password='pass123')
        self.client.get(reverse('notes:detail', args=[self.note.pk]))
        self.note.refresh_from_db()
        views_after_user2 = self.note.views
        
        # Ambos devem ter aumentado views
        self.assertGreater(views_after_user1, initial_views)
        self.assertGreater(views_after_user2, views_after_user1)


class NoteRecommendationTest(TestCase):
    """Testes para sistema de recomendações"""
    
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student1',
            password='pass123',
            user_type='estudante'
        )
        self.professor = User.objects.create_user(
            username='prof1',
            password='pass123',
            user_type='professor'
        )
        
        self.subject = Subject.objects.create(name='Química', slug='quimica')
        self.note = Note.objects.create(
            author=self.student,
            title='Resumo Química',
            description='Test',
            file_type='TXT',
            subject=self.subject
        )
    
    def test_only_professor_can_recommend(self):
        """Testa que apenas professores podem recomendar"""
        # Estudante tenta recomendar
        self.client.login(username='student1', password='pass123')
        response = self.client.post(reverse('notes:recommend', args=[self.note.pk]))
        self.assertEqual(response.status_code, 403)
        
        # Professor pode recomendar
        self.client.logout()
        self.client.login(username='prof1', password='pass123')
        response = self.client.post(reverse('notes:recommend', args=[self.note.pk]))
        self.assertEqual(response.status_code, 200)
        
        # Verificar que recomendação foi criada
        self.assertTrue(
            NoteRecommendation.objects.filter(
                note=self.note, 
                professor=self.professor
            ).exists()
        )
    
    def test_toggle_recommendation(self):
        """Testa adicionar e remover recomendação"""
        self.client.login(username='prof1', password='pass123')
        
        # Adicionar recomendação
        response = self.client.post(reverse('notes:recommend', args=[self.note.pk]))
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'added')
        self.assertEqual(data['total'], 1)
        
        # Remover recomendação (toggle)
        response = self.client.post(reverse('notes:recommend', args=[self.note.pk]))
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'removed')
        self.assertEqual(data['total'], 0)


class NoteLikeTest(TestCase):
    """Testes para sistema de likes"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user1', password='pass123')
        self.note = Note.objects.create(
            author=self.user,
            title='Test Note',
            description='Test',
            file_type='TXT'
        )
    
    def test_like_toggle(self):
        """Testa curtir e descurtir"""
        self.client.login(username='user1', password='pass123')
        
        initial_likes = self.note.likes
        
        # Curtir
        response = self.client.post(reverse('notes:like', args=[self.note.pk]))
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['liked'])
        self.assertGreater(data['likes'], initial_likes)
        
        # Descurtir
        response = self.client.post(reverse('notes:like', args=[self.note.pk]))
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['liked'])
        self.assertEqual(data['likes'], initial_likes)


class NoteFilterTest(TestCase):
    """Testes para filtros de notes"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user1', password='pass123')
        
        self.subject1 = Subject.objects.create(name='História', slug='historia')
        self.subject2 = Subject.objects.create(name='Geografia', slug='geografia')
        
        self.note1 = Note.objects.create(
            author=self.user,
            title='Note História',
            file_type='PDF',
            subject=self.subject1
        )
        self.note2 = Note.objects.create(
            author=self.user,
            title='Note Geografia',
            file_type='DOC',
            subject=self.subject2
        )
    
    def test_filter_by_subject(self):
        """Testa filtro por matéria"""
        response = self.client.get(reverse('notes:list') + '?subject=historia')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Note História')
        self.assertNotContains(response, 'Note Geografia')
    
    def test_filter_by_file_type(self):
        """Testa filtro por tipo de arquivo"""
        response = self.client.get(reverse('notes:list') + '?file_type=PDF')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Note História')
        self.assertNotContains(response, 'Note Geografia')


class RootRedirectTest(TestCase):
    """Testa redirecionamento da raiz"""
    
    def test_root_redirects_to_study(self):
        """Testa que / redireciona para /study"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/study/', response.url)