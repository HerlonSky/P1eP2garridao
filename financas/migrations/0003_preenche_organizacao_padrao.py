"""Etapa 2 de 3 da migração para multi-organização.

Os dados da P1 foram criados antes de existir Organizacao. Esta migração cria
uma "Organização padrão" e atribui a ela todos os registros que ainda estão
sem organização. Depois disso a etapa 3 pode tornar a FK obrigatória sem
perder nenhuma linha.
"""

from django.db import migrations

MODELS_DE_NEGOCIO = ['Conta', 'Categoria', 'Lancamento', 'Orcamento']


def preencher_organizacao_padrao(apps, schema_editor):
    # apps.get_model (e não import direto): a migração enxerga o model
    # como ele era neste ponto do histórico.
    Organizacao = apps.get_model('core', 'Organizacao')
    sem_org = [
        apps.get_model('financas', nome).objects.filter(organizacao__isnull=True)
        for nome in MODELS_DE_NEGOCIO
    ]
    if not any(qs.exists() for qs in sem_org):
        return  # banco vazio: não cria organização à toa

    org, _ = Organizacao.objects.get_or_create(nome='Organização padrão')
    for qs in sem_org:
        qs.update(organizacao=org)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('financas', '0002_organizacao_opcional'),
    ]

    operations = [
        migrations.RunPython(preencher_organizacao_padrao, migrations.RunPython.noop),
    ]
