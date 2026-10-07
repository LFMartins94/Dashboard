"""Modelos internos da aplicação web."""

import uuid

from django.conf import settings
from django.db import models


class TentativaLogin(models.Model):
    """Contador sem dados pessoais brutos para limitar tentativas de acesso."""

    chave_hash = models.CharField(max_length=64, primary_key=True)
    tentativas = models.PositiveSmallIntegerField(default=0)
    janela_iniciada_em = models.DateTimeField()
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_tentativas_login"
        verbose_name = "tentativa de login"
        verbose_name_plural = "tentativas de login"
        indexes = [
            models.Index(fields=["bloqueado_ate"], name="idx_login_bloqueio"),
        ]


class EstadoOperacional(models.TextChoices):
    AGUARDANDO = "aguardando", "Aguardando"
    RECEBIDO = "recebido", "Recebido"
    EM_CONFERENCIA = "em_conferencia", "Em conferência"
    COM_DIVERGENCIA = "com_divergencia", "Com divergência"
    REVISADO = "revisado", "Revisado"
    ENTREGUE = "entregue", "Entregue"


class CompetenciaTrabalho(models.Model):
    """Ciclo operacional de uma empresa em uma competência."""

    empresa_id = models.PositiveIntegerField()
    competencia = models.CharField(max_length=7)
    estado = models.CharField(
        max_length=20,
        choices=EstadoOperacional.choices,
        default=EstadoOperacional.AGUARDANDO,
    )
    prazo_entrega = models.DateField(null=True, blank=True)
    iniciado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="competencias_iniciadas",
    )
    iniciado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_competencias_trabalho"
        verbose_name = "competência de trabalho"
        verbose_name_plural = "competências de trabalho"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_id", "competencia"], name="uq_comp_empresa_periodo"
            ),
            models.CheckConstraint(
                condition=models.Q(empresa_id__gt=0), name="ck_comp_empresa_pos"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    competencia__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"
                ),
                name="ck_comp_periodo",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoOperacional.values),
                name="ck_comp_estado",
            ),
        ]
        indexes = [
            models.Index(
                fields=["empresa_id", "estado", "competencia"],
                name="idx_comp_empresa_estado",
            ),
        ]

    @property
    def competencia_exibicao(self) -> str:
        return f"{self.competencia[5:]}/{self.competencia[:4]}"


class CategoriaChecklist(models.TextChoices):
    DOCUMENTO = "documento", "Documento"
    CONFERENCIA = "conferencia", "Conferência"
    DIVERGENCIA = "divergencia", "Divergência"
    ENTREGA = "entrega", "Entrega"


class ItemChecklistTrabalho(models.Model):
    """Item recorrente copiado para uma competência específica."""

    competencia_trabalho = models.ForeignKey(
        CompetenciaTrabalho,
        on_delete=models.CASCADE,
        related_name="itens",
    )
    titulo = models.CharField(max_length=160)
    categoria = models.CharField(max_length=20, choices=CategoriaChecklist.choices)
    estado = models.CharField(
        max_length=20,
        choices=EstadoOperacional.choices,
        default=EstadoOperacional.AGUARDANDO,
    )
    ordem = models.PositiveSmallIntegerField(default=0)
    obrigatorio = models.BooleanField(default=True)
    rota_destino = models.CharField(max_length=80)
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="itens_checklist_atualizados",
    )
    concluido_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_itens_checklist_trabalho"
        verbose_name = "item do checklist"
        verbose_name_plural = "itens do checklist"
        constraints = [
            models.UniqueConstraint(
                fields=["competencia_trabalho", "titulo"],
                name="uq_item_comp_titulo",
            ),
            models.CheckConstraint(
                condition=models.Q(categoria__in=CategoriaChecklist.values),
                name="ck_item_categoria",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoOperacional.values),
                name="ck_item_estado",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    rota_destino__in=(
                        "nucleo:entradas",
                        "nucleo:conferencia",
                        "nucleo:entregas",
                    )
                ),
                name="ck_item_rota",
            ),
        ]
        indexes = [
            models.Index(
                fields=["competencia_trabalho", "estado", "ordem"],
                name="idx_item_comp_estado",
            ),
        ]


class EstadoArquivoEntrada(models.TextChoices):
    RECEBIDO = "recebido", "Recebido"
    EM_MAPEAMENTO = "em_mapeamento", "Em mapeamento"
    PREPARADO = "preparado", "Preparado"
    DESCARTADO = "descartado", "Descartado"


class ModoPerfilOrigemEntrada(models.TextChoices):
    TRANSACIONAL = "transacional", "Transacional"
    CONTABIL_ESTRUTURADO = "contabil_estruturado", "Contábil estruturado"


class RegraCompetenciaOrigem(models.TextChoices):
    RESTRITA = "restrita", "Restrita à competência"
    AMPLIADA = "ampliada", "Competência ampliada"
    LIVRE = "livre", "Sem bloqueio de competência"


class ArquivoEntradaTemporario(models.Model):
    """Arquivo preservado enquanto a contadora confirma como interpretá-lo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="arquivos_entrada_temporarios",
    )
    empresa_id = models.PositiveIntegerField()
    competencia = models.CharField(max_length=7)
    nome_original = models.CharField(max_length=255)
    extensao = models.CharField(max_length=5)
    tamanho_bytes = models.PositiveIntegerField()
    arquivo_sha256 = models.CharField(max_length=64)
    conteudo = models.BinaryField()
    inspecao = models.JSONField(default=dict)
    perfil_origem = models.ForeignKey(
        "PerfilOrigemEntrada",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="arquivos_identificados",
    )
    status = models.CharField(
        max_length=20,
        choices=EstadoArquivoEntrada.choices,
        default=EstadoArquivoEntrada.RECEBIDO,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_arquivos_entrada_temporarios"
        verbose_name = "arquivo temporário de entrada"
        verbose_name_plural = "arquivos temporários de entrada"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(empresa_id__gt=0), name="ck_arq_ent_empresa_pos"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    competencia__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"
                ),
                name="ck_arq_ent_periodo",
            ),
            models.CheckConstraint(
                condition=models.Q(extensao__in=("xlsx", "xls", "csv", "ofx")),
                name="ck_arq_ent_extensao",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=EstadoArquivoEntrada.values),
                name="ck_arq_ent_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=["usuario", "empresa_id", "competencia", "status"],
                name="idx_arq_ent_contexto",
            ),
            models.Index(
                fields=["empresa_id", "arquivo_sha256"],
                name="idx_arq_ent_hash",
            ),
        ]


class ModeloMapeamentoEntrada(models.Model):
    """Mapeamento confirmado e reutilizável para uma estrutura de planilha."""

    empresa_id = models.PositiveIntegerField()
    assinatura_estrutura = models.CharField(max_length=64)
    tipo_documento = models.CharField(max_length=20)
    aba = models.CharField(max_length=255)
    linha_cabecalho = models.PositiveIntegerField(default=0)
    mapeamento = models.JSONField(default=dict)
    vezes_utilizado = models.PositiveIntegerField(default=1)
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modelos_mapeamento_confirmados",
    )
    perfil_origem = models.ForeignKey(
        "PerfilOrigemEntrada",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modelos_mapeamento",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_modelos_mapeamento_entrada"
        verbose_name = "modelo de mapeamento de entrada"
        verbose_name_plural = "modelos de mapeamento de entrada"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_id", "assinatura_estrutura", "tipo_documento"],
                condition=models.Q(perfil_origem__isnull=True),
                name="uq_mod_map_empresa_estrutura_tipo_generico",
            ),
            models.UniqueConstraint(
                fields=[
                    "empresa_id", "perfil_origem", "assinatura_estrutura",
                    "tipo_documento",
                ],
                condition=models.Q(perfil_origem__isnull=False),
                name="uq_mod_map_empresa_perfil_estrutura_tipo",
            ),
            models.CheckConstraint(
                condition=models.Q(empresa_id__gt=0), name="ck_mod_map_empresa_pos"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    tipo_documento__in=(
                        "extrato", "folha", "notas", "lancamentos", "outro"
                    )
                ),
                name="ck_mod_map_tipo",
            ),
        ]
        indexes = [
            models.Index(
                fields=["empresa_id", "assinatura_estrutura"],
                name="idx_mod_map_estrutura",
            ),
        ]


class DecisaoConciliacao(models.TextChoices):
    CONFIRMADA = "confirmada", "Confirmada"
    REJEITADA = "rejeitada", "Rejeitada"
    MANUAL = "manual", "Ajuste manual"


class RevisaoConciliacao(models.Model):
    """Decisão humana para um candidato de conciliação entre dois lotes."""

    empresa_id = models.PositiveIntegerField()
    competencia = models.CharField(max_length=7)
    lote_extrato_id = models.BigIntegerField()
    lote_referencia_id = models.BigIntegerField()
    linha_extrato_id = models.BigIntegerField()
    linha_referencia_id = models.BigIntegerField()
    decisao = models.CharField(max_length=15, choices=DecisaoConciliacao.choices)
    justificativa = models.CharField(max_length=500, blank=True)
    decidido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="revisoes_conciliacao",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_revisoes_conciliacao"
        verbose_name = "revisão de conciliação"
        verbose_name_plural = "revisões de conciliação"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "empresa_id", "competencia", "lote_extrato_id",
                    "lote_referencia_id", "linha_extrato_id", "linha_referencia_id",
                ],
                name="uq_rev_conc_linhas",
            ),
            models.CheckConstraint(
                condition=models.Q(empresa_id__gt=0), name="ck_rev_conc_empresa_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    competencia__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"
                ),
                name="ck_rev_conc_periodo",
            ),
            models.CheckConstraint(
                condition=models.Q(decisao__in=DecisaoConciliacao.values),
                name="ck_rev_conc_decisao",
            ),
        ]
        indexes = [
            models.Index(
                fields=["empresa_id", "competencia", "lote_extrato_id", "lote_referencia_id"],
                name="idx_rev_conc_contexto",
            ),
        ]


class EstadoOcorrenciaAuditoria(models.Model):
    """Complementa a ocorrência legada com resolução atribuída a usuário."""

    ocorrencia_id = models.BigIntegerField(unique=True)
    empresa_id = models.PositiveIntegerField()
    competencia = models.CharField(max_length=7)
    resolvida = models.BooleanField(default=False)
    justificativa = models.CharField(max_length=500, blank=True)
    resolvida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ocorrencias_auditoria_resolvidas",
    )
    resolvida_em = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_estados_ocorrencias_auditoria"
        verbose_name = "estado de ocorrência de auditoria"
        verbose_name_plural = "estados de ocorrências de auditoria"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(empresa_id__gt=0), name="ck_est_aud_empresa_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    competencia__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"
                ),
                name="ck_est_aud_periodo",
            ),
        ]
        indexes = [
            models.Index(
                fields=["empresa_id", "competencia", "resolvida"],
                name="idx_est_aud_contexto",
            ),
        ]


class CategoriaDre(models.TextChoices):
    RECEITA = "receita", "Receita"
    CUSTO = "custo", "Custo"
    DESPESA = "despesa", "Despesa"
    OUTRO = "outro", "Outro"


class ClassificacaoDre(models.Model):
    """Regra confirmada pela contadora para classificar prefixos de conta."""

    empresa_id = models.PositiveIntegerField()
    prefixo_conta = models.CharField(max_length=50)
    grupo = models.CharField(max_length=120)
    categoria = models.CharField(max_length=20, choices=CategoriaDre.choices)
    ordem = models.PositiveSmallIntegerField(default=100)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_classificacoes_dre"
        verbose_name = "classificação de DRE"
        verbose_name_plural = "classificações de DRE"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_id", "prefixo_conta"], name="uq_dre_empresa_prefixo",
            ),
            models.CheckConstraint(
                condition=models.Q(empresa_id__gt=0), name="ck_dre_empresa_pos",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa_id", "ordem"], name="idx_dre_empresa_ordem"),
        ]


class PerfilExportacao(models.Model):
    """Ordem de campos visíveis em uma exportação de lançamentos."""

    empresa_id = models.PositiveIntegerField(null=True, blank=True)
    nome = models.CharField(max_length=80)
    campos = models.JSONField(default=list)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="perfis_exportacao_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "django_perfis_exportacao"
        verbose_name = "perfil de exportação"
        verbose_name_plural = "perfis de exportação"
        indexes = [
            models.Index(fields=["empresa_id", "nome"], name="idx_perfil_empresa_nome"),
        ]


class GeracaoRelatorio(models.Model):
    """Registro suficiente para reproduzir uma entrega no mesmo contexto."""

    empresa_id = models.PositiveIntegerField()
    competencia = models.CharField(max_length=7)
    tipo_relatorio = models.CharField(max_length=20)
    formato = models.CharField(max_length=10)
    parametros = models.JSONField(default=dict)
    versao_calculo = models.CharField(max_length=20)
    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="relatorios_gerados",
    )
    gerado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "django_geracoes_relatorios"
        verbose_name = "geração de relatório"
        verbose_name_plural = "gerações de relatórios"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(empresa_id__gt=0), name="ck_ger_rel_empresa_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    competencia__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"
                ), name="ck_ger_rel_periodo",
            ),
        ]
        indexes = [
            models.Index(
                fields=["empresa_id", "competencia", "gerado_em"],
                name="idx_ger_rel_contexto",
            ),
        ]


class ModeloDocumentoEsperado(models.Model):
    """Documento recorrente que deve aparecer no checklist de uma empresa."""

    empresa_id = models.PositiveIntegerField()
    nome = models.CharField(max_length=160)
    tipo_documento = models.CharField(max_length=20, default="outro")
    dia_limite = models.PositiveSmallIntegerField(null=True, blank=True)
    obrigatorio = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_modelos_documentos_esperados"
        verbose_name = "modelo de documento esperado"
        verbose_name_plural = "modelos de documentos esperados"
        constraints = [
            models.UniqueConstraint(fields=["empresa_id", "nome"], name="uq_doc_esperado_empresa_nome"),
            models.CheckConstraint(condition=models.Q(empresa_id__gt=0), name="ck_doc_esperado_empresa_pos"),
            models.CheckConstraint(
                condition=models.Q(dia_limite__isnull=True) | models.Q(dia_limite__gte=1, dia_limite__lte=31),
                name="ck_doc_esperado_dia_limite",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa_id", "ativo"], name="idx_doc_esperado_empresa"),
        ]


class PerfilOrigemEntrada(models.Model):
    """Regra local de nome e pasta de referência para arquivos recebidos."""

    empresa_id = models.PositiveIntegerField()
    nome = models.CharField(max_length=80)
    prefixo_nome = models.CharField(max_length=80)
    pasta_referencia = models.CharField(max_length=255, blank=True)
    tipo_documento = models.CharField(max_length=20, default="outro")
    modo = models.CharField(
        max_length=25,
        choices=ModoPerfilOrigemEntrada.choices,
        default=ModoPerfilOrigemEntrada.TRANSACIONAL,
    )
    regra_competencia = models.CharField(
        max_length=12,
        choices=RegraCompetenciaOrigem.choices,
        default=RegraCompetenciaOrigem.RESTRITA,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "django_perfis_origem_entrada"
        verbose_name = "perfil de origem de entrada"
        verbose_name_plural = "perfis de origem de entrada"
        constraints = [
            models.UniqueConstraint(fields=["empresa_id", "nome"], name="uq_perfil_origem_empresa_nome"),
            models.CheckConstraint(condition=models.Q(empresa_id__gt=0), name="ck_perfil_origem_empresa_pos"),
        ]
        indexes = [
            models.Index(fields=["empresa_id", "ativo", "prefixo_nome"], name="idx_perfil_origem_empresa"),
        ]


class TipoTarefaAutomacao(models.TextChoices):
    PROCESSAR_ARQUIVO = "processar_arquivo", "Processar arquivo"
    VERIFICAR_PENDENCIAS = "verificar_pendencias", "Verificar pendências"


class EstadoTarefaAutomacao(models.TextChoices):
    AGUARDANDO = "aguardando", "Aguardando"
    PROCESSANDO = "processando", "Processando"
    CONCLUIDA = "concluida", "Concluída"
    FALHA = "falha", "Falha"


class TarefaAutomacao(models.Model):
    """Fila persistida e visível para tarefas que podem exigir nova execução."""

    empresa_id = models.PositiveIntegerField()
    competencia = models.CharField(max_length=7)
    tipo = models.CharField(max_length=30, choices=TipoTarefaAutomacao.choices)
    estado = models.CharField(
        max_length=20, choices=EstadoTarefaAutomacao.choices,
        default=EstadoTarefaAutomacao.AGUARDANDO,
    )
    arquivo_entrada = models.ForeignKey(
        ArquivoEntradaTemporario, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tarefas_automacao",
    )
    detalhes = models.JSONField(default=dict)
    tentativas = models.PositiveSmallIntegerField(default=0)
    mensagem_erro = models.CharField(max_length=500, blank=True)
    solicitada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tarefas_automacao_solicitadas",
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    iniciada_em = models.DateTimeField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "django_tarefas_automacao"
        verbose_name = "tarefa de automação"
        verbose_name_plural = "tarefas de automação"
        constraints = [
            models.CheckConstraint(condition=models.Q(empresa_id__gt=0), name="ck_tarefa_auto_empresa_pos"),
            models.CheckConstraint(
                condition=models.Q(competencia__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"),
                name="ck_tarefa_auto_periodo",
            ),
            models.CheckConstraint(
                condition=models.Q(tipo__in=TipoTarefaAutomacao.values), name="ck_tarefa_auto_tipo",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoTarefaAutomacao.values), name="ck_tarefa_auto_estado",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa_id", "competencia", "estado"], name="idx_tarefa_auto_contexto"),
        ]


class RegistroConsultaAssistente(models.Model):
    """Rastreabilidade das consultas que receberam contexto contábil agregado."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="consultas_assistente",
    )
    conversa_id = models.PositiveIntegerField()
    empresa_id = models.PositiveIntegerField()
    competencia = models.CharField(max_length=7)
    pergunta = models.TextField()
    resposta = models.TextField()
    filtros = models.JSONField(default=dict)
    fontes = models.JSONField(default=list)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "django_registros_consultas_assistente"
        verbose_name = "registro de consulta do assistente"
        verbose_name_plural = "registros de consultas do assistente"
        constraints = [
            models.CheckConstraint(condition=models.Q(conversa_id__gt=0), name="ck_consulta_assist_conversa_pos"),
            models.CheckConstraint(condition=models.Q(empresa_id__gt=0), name="ck_consulta_assist_empresa_pos"),
            models.CheckConstraint(
                condition=models.Q(competencia__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"),
                name="ck_consulta_assist_periodo",
            ),
        ]
        indexes = [
            models.Index(
                fields=["empresa_id", "competencia", "conversa_id", "criado_em"],
                name="idx_consulta_assist_contexto",
            ),
        ]
