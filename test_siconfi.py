import asyncio
from app.services.siconfi.siconfi_service import SiconfiService
import json

async def main():
    print("Iniciando teste da API SICONFI...\n")
    service = SiconfiService()
    
    try:
        # 1. Testar Entes (pegar apenas os 2 primeiros para não poluir o terminal)
        print("--- Teste 1: Buscar Entes Federativos ---")
        entes = await service.get_entes()
        print(f"Total de entes retornados: {len(entes)}")
        print("Exemplo dos 2 primeiros entes:")
        print(json.dumps(entes[:2], indent=2, ensure_ascii=False))
        
        print("\n" + "="*50 + "\n")
        
        # 2. Testar RREO (Município de São Paulo - IBGE 3550308, ano 2023, período 1)
        print("--- Teste 2: Buscar RREO (São Paulo - SP, Ano 2023, 1º Bimestre) ---")
        rreo = await service.get_rreo(an_exercicio=2023, nr_periodo=1, co_tipo_demonstrativo='RREO', id_ente='3550308')
        print(f"Total de registros/linhas retornados no RREO: {len(rreo)}")
        if rreo:
            print("Exemplo das 2 primeiras linhas do RREO:")
            print(json.dumps(rreo[:2], indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Erro ao testar a API: {e}")

if __name__ == "__main__":
    asyncio.run(main())
