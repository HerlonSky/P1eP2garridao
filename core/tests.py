from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from .models import Organizacao, Perfil
from .utils import org_atual, perfil_do_usuario


class PerfilTest(TestCase):
    def setUp(self):
        self.org = Organizacao.objects.create(nome='Casa')
        self.user = User.objects.create_user('ana')

    def test_papel_padrao_e_operador(self):
        perfil = Perfil.objects.create(usuario=self.user, organizacao=self.org)
        self.assertEqual(perfil.papel, Perfil.OPERADOR)
        self.assertFalse(perfil.eh_admin)

    def test_eh_admin(self):
        perfil = Perfil.objects.create(usuario=self.user, organizacao=self.org, papel=Perfil.ADMIN)
        self.assertTrue(perfil.eh_admin)

    def test_org_atual_vem_do_perfil(self):
        Perfil.objects.create(usuario=self.user, organizacao=self.org)
        request = RequestFactory().get('/')
        request.user = self.user
        self.assertEqual(org_atual(request), self.org)

    def test_usuario_sem_perfil(self):
        self.assertIsNone(perfil_do_usuario(self.user))
        request = RequestFactory().get('/')
        request.user = self.user
        self.assertIsNone(org_atual(request))
