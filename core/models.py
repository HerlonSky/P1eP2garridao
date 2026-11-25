"""Modelos transversais do sistema: a organização (o "inquilino") e o perfil do usuário.

Estratégia de multi-tenancy: coluna discriminadora. Todos os dados ficam no mesmo
banco e cada model de negócio tem uma FK para Organizacao. Toda consulta filtra
por ela (ver core.utils.org_atual).
"""

from django.contrib.auth.models import User
from django.db import models


class Organizacao(models.Model):
    """O dono dos dados: uma família, uma república, um casal que divide as contas..."""

    nome = models.CharField(max_length=120)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'organização'
        verbose_name_plural = 'organizações'

    def __str__(self):
        return self.nome


class DaOrganizacao(models.Model):
    """Base abstrata: todo model de negócio herda daqui e ganha a FK da organização.

    abstract = True: o Django não cria tabela para esta classe, só copia o campo
    para cada model filho. Menos repetição, menos chance de esquecer a FK.
    """

    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.PROTECT,
        verbose_name='organização',
    )

    class Meta:
        abstract = True


class Perfil(models.Model):
    """Liga o User do Django (sem alterá-lo) a uma organização."""

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    organizacao = models.ForeignKey(
        Organizacao, on_delete=models.PROTECT, related_name='perfis', verbose_name='organização',
    )

    class Meta:
        verbose_name_plural = 'perfis'

    def __str__(self):
        return f'{self.usuario.username} ({self.organizacao})'
