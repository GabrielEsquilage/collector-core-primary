from enum import Enum
from typing import Dict, Any

class IndicadorMacro(str, Enum):
    # Arrecadação e Saúde Financeira Geral
    RECEITA_TOTAL = "receita_total"
    DESPESA_TOTAL = "despesa_total"
    RECEITA_CORRENTE_LIQUIDA = "receita_corrente_liquida"
    
    # Despesas Estratégicas (Funções de Governo)
    DESPESA_SAUDE = "despesa_saude"
    DESPESA_EDUCACAO = "despesa_educacao"
    DESPESA_SANEAMENTO = "despesa_saneamento"
    DESPESA_URBANISMO = "despesa_urbanismo"
    DESPESA_SEGURANCA = "despesa_seguranca"
    
    # Perfil de Gastos e Endividamento
    INVESTIMENTOS = "investimentos"
    DESPESA_PESSOAL = "despesa_pessoal"
    DIVIDA_CONSOLIDADA = "divida_consolidada"
    
    # Inteligência e Risco Fiscal (Avançado)
    RESTOS_A_PAGAR = "restos_a_pagar"
    RESULTADO_PRIMARIO = "resultado_primario"
    RESULTADO_PREVIDENCIARIO = "resultado_previdenciario"
    PPP_CONTRATADAS = "ppp_contratadas"

# Catálogo Semântico do SICONFI
# Mapeia nomes limpos para as colunas reais e caóticas da API do governo
SICONFI_CATALOG: Dict[IndicadorMacro, Dict[str, str]] = {
    # --- RREO: Execução Orçamentária Básica ---
    IndicadorMacro.RECEITA_TOTAL: {
        "anexo": "RREO-Anexo 01",
        "coluna_like": "%RECEITAS REALIZADAS%",
        "conta_like": "RECEITAS (EXCETO%"
    },
    IndicadorMacro.DESPESA_TOTAL: {
        "anexo": "RREO-Anexo 01",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "DESPESAS (EXCETO%"
    },
    IndicadorMacro.RECEITA_CORRENTE_LIQUIDA: {
        "anexo": "RREO-Anexo 03",
        "coluna_like": "%TOTAL%",
        "conta_like": "RECEITA CORRENTE LÍQUIDA (III)%"
    },
    IndicadorMacro.INVESTIMENTOS: {
        "anexo": "RREO-Anexo 01",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "Investimentos"
    },
    
    # --- RREO Anexo 02: Gastos por Setor/Função ---
    IndicadorMacro.DESPESA_SAUDE: {
        "anexo": "RREO-Anexo 02",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "10 - Saúde"
    },
    IndicadorMacro.DESPESA_EDUCACAO: {
        "anexo": "RREO-Anexo 02",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "12 - Educação"
    },
    IndicadorMacro.DESPESA_SANEAMENTO: {
        "anexo": "RREO-Anexo 02",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "17 - Saneamento"
    },
    IndicadorMacro.DESPESA_URBANISMO: {
        "anexo": "RREO-Anexo 02",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "15 - Urbanismo"
    },
    IndicadorMacro.DESPESA_SEGURANCA: {
        "anexo": "RREO-Anexo 02",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "06 - Segurança Pública"
    },
    
    # --- Inteligência Fiscal (Avançado) ---
    IndicadorMacro.RESTOS_A_PAGAR: {
        "anexo": "RREO-Anexo 07",
        "coluna_like": "%Saldo%",
        "conta_like": "RESTOS A PAGAR%"
    },
    IndicadorMacro.RESULTADO_PRIMARIO: {
        "anexo": "RREO-Anexo 06",
        "coluna_like": "%Até o Bimestre%",
        "conta_like": "RESULTADO PRIMÁRIO%"
    },
    IndicadorMacro.RESULTADO_PREVIDENCIARIO: {
        "anexo": "RREO-Anexo 04",
        "coluna_like": "%Até o Bimestre%",
        "conta_like": "RESULTADO PREVIDENCIÁRIO%"
    },
    IndicadorMacro.PPP_CONTRATADAS: {
        "anexo": "RREO-Anexo 13",
        "coluna_like": "%SALDO TOTAL%",
        "conta_like": "TOTAL DE ATIVOS%"
    },
    
    # --- RGF: Gestão Fiscal e Limites (Endividamento e Pessoal) ---
    IndicadorMacro.DESPESA_PESSOAL: {
        "anexo": "RGF-Anexo 01",
        "coluna_like": "%VALOR%",
        "conta_like": "DESPESA TOTAL COM PESSOAL - DTP (V) = (III a + III b)"
    },
    IndicadorMacro.DIVIDA_CONSOLIDADA: {
        "anexo": "RGF-Anexo 02",
        "coluna_like": "%VALOR%",
        "conta_like": "DÍVIDA CONSOLIDADA - DC (I)"
    }
}
