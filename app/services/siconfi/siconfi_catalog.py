from enum import Enum
from typing import Dict, Any

class IndicadorMacro(str, Enum):
    RECEITA_TOTAL = "receita_total"
    DESPESA_TOTAL = "despesa_total"
    RECEITA_CORRENTE_LIQUIDA = "receita_corrente_liquida"
    
    DESPESA_SAUDE = "despesa_saude"
    DESPESA_EDUCACAO = "despesa_educacao"
    DESPESA_SANEAMENTO = "despesa_saneamento"
    DESPESA_URBANISMO = "despesa_urbanismo"
    DESPESA_SEGURANCA = "despesa_seguranca"
    
    INVESTIMENTOS = "investimentos"
    DESPESA_PESSOAL = "despesa_pessoal"
    DIVIDA_CONSOLIDADA = "divida_consolidada"
    
    RESTOS_A_PAGAR = "restos_a_pagar"
    RESULTADO_PRIMARIO = "resultado_primario"
    RESULTADO_PREVIDENCIARIO = "resultado_previdenciario"
    PPP_CONTRATADAS = "ppp_contratadas"

SICONFI_CATALOG: Dict[IndicadorMacro, Dict[str, str]] = {
    IndicadorMacro.RECEITA_TOTAL: {
        "anexo": "RREO-Anexo 01",
        "coluna_like": "%Bimestre%",
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
        "conta_like": "%Investimentos%"
    },
    
    IndicadorMacro.DESPESA_SAUDE: {
        "anexo": "RREO-Anexo 02",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "%Sa_de%"
    },
    IndicadorMacro.DESPESA_EDUCACAO: {
        "anexo": "RREO-Anexo 02",
        "coluna_like": "%DESPESAS LIQUIDADAS%",
        "conta_like": "%Educa%"
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
