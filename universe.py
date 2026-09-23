"""
Universo de ações B3 acompanhado pelo painel, agrupado por setor.

Códigos conferidos na lista da brapi (https://brapi.dev/api/available)
em 2026-09-23. Saíram códigos que não negociam mais: BRFS3 (BRF, hoje
MBRF3), JBSS3 (JBS, hoje BDR JBSS32), EMBR3 (Embraer, hoje EMBJ3) e AZUL4.

Orçamento brapi (plano gratuito, 15 mil req/mês): cada varredura faz
1 requisição por ação; 26 ações x 16 varreduras/dia x 22 pregões
≈ 9,2 mil req/mês. Acima de ~40 ações, o plano gratuito não comporta.
"""

B3_SECTORS = {
    # Agro: grãos, açúcar/etanol, sementes, insumos, armazenagem
    "SLCE3": "Agro",    # SLC Agrícola
    "AGRO3": "Agro",    # BrasilAgro
    "TTEN3": "Agro",    # 3tentos
    "SOJA3": "Agro",    # Boa Safra Sementes
    "SMTO3": "Agro",    # São Martinho
    "JALL3": "Agro",    # Jalles Machado
    "RAIZ4": "Agro",    # Raízen
    "CAML3": "Agro",    # Camil
    "VITT3": "Agro",    # Vittia
    "KEPL3": "Agro",    # Kepler Weber
    # Proteína animal
    "MBRF3": "Proteína",   # MBRF (Marfrig + BRF)
    "BEEF3": "Proteína",   # Minerva
    "JBSS32": "Proteína",  # JBS (BDR)
    # Papel e celulose
    "SUZB3": "Papel e celulose",   # Suzano
    "KLBN11": "Papel e celulose",  # Klabin
    # Logística
    "RAIL3": "Logística",  # Rumo
    # Referências de mercado
    "PETR4": "Outros", "VALE3": "Outros", "ITUB4": "Outros", "BBDC4": "Outros",
    "BBAS3": "Outros", "ABEV3": "Outros", "GGBR4": "Outros", "RENT3": "Outros",
    "WEGE3": "Outros", "EMBJ3": "Outros",
}

SECTOR_ORDER = ["Agro", "Proteína", "Papel e celulose", "Logística", "Outros"]
