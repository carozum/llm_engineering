# duel_orchestrator.py
# pip install openai anthropic python-dotenv

import os, textwrap
from typing import Dict, Optional
from dataclasses import dataclass
from call_anthropic import call_anthropic
from call_openai import call_openai

# ========= 1) Systèmes génériques paramétrables =========

SYSTEM_A_BASE = """Vous êtes Expert A : {role_a}.
Style: {style_a}

Règles du débat (5 tours maximum):
1) Tour 1: proposez votre plan (3–6 étapes) + micro-exemple d’implémentation.
2) Tour 2: réfutez la proposition de B (faiblesses/risques), proposez des garde-fous.
3) Tour 3: révisez votre plan (compromis concrets).
4) Tour 4: converge avec B vers un plan commun (décisions tranchées).
5) Tour 5: si l’orchestrateur dit “CONCLUSION”, écrivez la réponse finale actionnable (≤15 lignes).

Contraintes:
- Toujours concret (étapes, commandes, snippet).
- Hypothèses explicites.
- Format concis, listes numérotées.
"""

SYSTEM_B_BASE = """Vous êtes Expert B : {role_b}.
Style: {style_b}

Règles du débat (5 tours maximum):
1) Tour 1: proposez votre plan (3–6 étapes) + micro-exemple d’implémentation.
2) Tour 2: réfutez la proposition de A (précision, scalabilité, conformité), proposez des garde-fous.
3) Tour 3: révisez votre plan avec concessions pragmatiques.
4) Tour 4: converge avec A vers un plan commun (décisions explicites).
5) Tour 5: si l’orchestrateur dit “CONCLUSION”, répondez uniquement “OK”.

Contraintes:
- Spécifique et mesurable (outils, variables, métriques).
- Risques + tests rapides.
- Format concis, listes numérotées.
"""

# ========= 2) Templates de tours (agnostiques au sujet) =========

def tour1_prompt(sujet, contexte, intrants, contraintes, annexe: str | None = None):
    base = textwrap.dedent(f"""
    SUJET: {sujet}
    CONTEXTE: {contexte}
    INTRANTS CLES: {intrants}
    CONTRAINTES: {contraites if (contraites := contraintes) else "Aucune précisée"}

    OBJECTIF (tour 1):
    - Plan d’action (3–6 étapes) + micro-exemple d’implémentation.
    - N’exprimez PAS de critiques sur l’autre expert.
    - Mentionnez clairement vos hypothèses.
    """).strip()

    if annexe:
        base += textwrap.dedent(f"""

        ANNEXE (source officielle à utiliser si utile; ne pas tout paraphraser):
        <<<ANNEXE_DEBUT>>>
        {annexe}
        <<<ANNEXE_FIN>>>
        """)
    return base


def t2_prompt(other):
    return f"""Voici la proposition de l’autre expert:
---
{other}
---
Consignes (tour 2):
- Réfutez (précision, risques, coûts, scalabilité).
- Proposez 1–2 garde-fous/test rapides.
"""

def t3_prompt(recap):
    return f"""Récap objections et points de l’autre:
---
{recap}
---
Consignes (tour 3):
- Révisez votre plan (compromis concrets).
- Ajoutez une check-list de validation POC (≤6 items).
"""

def t4_prompt():
    return """Objectif (tour 4): produire ensemble un plan commun.
Consignes:
- Listez 5–10 décisions tranchées (outil, modèle/solveur, métriques, données, livrables).
- Si un désaccord persiste: Option A / Option B + critère de choix.
Répondez en ≤12 lignes.
"""

def t5_conclusion_prompt():
    return """CONCLUSION (tour 5):
- Synthèse finale actionnable (≤15 lignes).
- Étapes techniques ordonnées + commandes/snippets.
- Métriques d’acceptation + jalons par semaine (S1/S2/S3).
"""


# ========= 4) Scénarios prêts à l’emploi =========

@dataclass
class Scenario:
    role_a: str
    style_a: str
    role_b: str
    style_b: str

SCENARIOS: Dict[str, Scenario] = {
    # POC planification sous contrainte (A=lean IA générative, B=solveur robuste)
    "planning": Scenario(
        role_a="architecte IA lean orienté POC rapide, IA générative + heuristiques",
        style_a="concret, frugal, itératif, MVP first",
        role_b="ingénieur optimisation/programmation par contraintes (ex: OR-Tools)",
        style_b="robustesse, conformité, scalabilité, qualité de solution"
    ),
    # Investment (A= Bull, B= Bear)
    "investissement": Scenario(
        role_a="investisseur growth (Bull), thèse orientée upside et time-to-value",
        style_a="chiffré, jalons clairs, mitigation pragmatique",
        role_b="analyste risques/compliance (Bear), focalisé downside et gouvernance",
        style_b="risques mesurables, clauses, kill criteria"
    ),
    # Exemple recrutement
    "recrutement": Scenario(
        role_a="recruteur pragmatique court terme (time-to-impact, fit opérationnel)",
        style_a="orienté delivery/production, compromis budget/délais",
        role_b="talent strategist long terme (potentiel, trajectoire, culture)",
        style_b="structure RH, bar de compétences, plan de ramp-up"
    ),
}

# ========= 5) Utilitaires contexte =========

def safe_clip(text: str, limit: int = 1200) -> str:
    return text if len(text) <= limit else text[:limit] + "\n[...troncature...]"

def summarize_for_exchange(a: str, b: str) -> str:
    return f"- Points A: {safe_clip(a)}\n- Points B: {safe_clip(b)}"

# ========= 6) La FONCTION UNIQUE demandée =========

def run_duel(
    scenario: str,
    sujet: str,
    contexte: str,
    intrants: str,
    contraintes: str,
    *,
    temperature: float = 0.35,
    max_tokens: int = 900,
    rounds: int = 5
) -> Dict[str, str]:
    """
    Orchestration générique A (OpenAI) <-> B (Anthropic) en 5 tours.
    - scenario: clé dans SCENARIOS (ex: "planning", "investissement", "recrutement")
    - sujet/contexte/intrants/contraintes: strings spécifiques à ton cas
    - rounds: laisse 5 (protocole prévu). Si <5, coupe logiquement.
    Retourne toutes les sorties + 'FINAL' comme conclusion d'Expert A.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"Scenario inconnu '{scenario}'. Choisis parmi: {list(SCENARIOS.keys())}")

    sc = SCENARIOS[scenario]
    system_a = SYSTEM_A_BASE.format(role_a=sc.role_a, style_a=sc.style_a)
    system_b = SYSTEM_B_BASE.format(role_b=sc.role_b, style_b=sc.style_b)

    # Tour 1: propositions initiales
    p1 = t1_prompt(sujet, contexte, intrants, contraintes)
    A1 = call_openai(system_a, p1, temperature, max_tokens)
    B1 = call_anthropic(system_b, p1, temperature, max_tokens)
    if rounds == 1: return {"A1": A1, "B1": B1}

    # Tour 2: réfutations
    A2 = call_openai(system_a, t2_prompt(B1), temperature, max_tokens)
    B2 = call_anthropic(system_b, t2_prompt(A1), temperature, max_tokens)
    if rounds == 2: return {"A1": A1, "B1": B1, "A2": A2, "B2": B2}

    # Tour 3: révisions
    recap_for_a = summarize_for_exchange(B2, B1)
    recap_for_b = summarize_for_exchange(A2, A1)
    A3 = call_openai(system_a, t3_prompt(recap_for_a), temperature, max_tokens)
    B3 = call_anthropic(system_b, t3_prompt(recap_for_b), temperature, max_tokens)
    if rounds == 3: return {"A1": A1, "B1": B1, "A2": A2, "B2": B2, "A3": A3, "B3": B3}

    # Tour 4: convergence
    A4 = call_openai(system_a, t4_prompt(), temperature, max_tokens)
    B4 = call_anthropic(system_b, t4_prompt(), temperature, max_tokens)
    if rounds == 4: return {"A1": A1, "B1": B1, "A2": A2, "B2": B2, "A3": A3, "B3": B3, "A4": A4, "B4": B4}

    # Tour 5: conclusion (A écrit, B dit OK)
    FINAL = call_openai(system_a, t5_conclusion_prompt(), temperature, max_tokens)
    _ = call_anthropic(system_b, "CONCLUSION — répondez « OK » et rien d’autre.", temperature, 64)

    return {"A1": A1, "B1": B1, "A2": A2, "B2": B2, "A3": A3, "B3": B3, "A4": A4, "B4": B4, "FINAL": FINAL}


# ========= 7) EXEMPLES D’USAGE =========
if __name__ == "__main__":
    # --- Exemple PLANNING
    # out = run_duel(
    #     scenario="planning",
    #     sujet="POC planification jour/nuit pour 50 employés sur 4 semaines.",
    #     contexte="Equipe 2 pers., deadline 2 semaines, Python+Docker, CPU-only.",
    #     intrants="CSV employés/compétences/contrats, CSV shifts, CSV règles.",
    #     contraintes="Audit contraintes violées, livrables: planning.csv + score + rapport HTML."
    # )
    # print("\n=== CONCLUSION (planning) ===\n", out["FINAL"])

    # --- Exemple INVESTISSEMENT (décommente pour tester)
    out2 = run_duel(
        scenario="investissement",
        sujet="Faut-il investir dans la société Octime ?",
        contexte="Horizon 18–24 mois, ticket 300–500k, SaaS B2B EU.",
        intrants="Pros/cons brochure, KPIs (MRR, NRR, churn, ARPA), équipe, GTM, marché & concurrence.",
        contraintes="RGPD minimal; runway >12m post-invest; seuils: NRR≥110%, payback CAC ≤12m; DD 2 semaines."
    )
    print("\n=== CONCLUSION (investissement) ===\n", out2["FINAL"])
