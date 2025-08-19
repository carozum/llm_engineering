import os, time, textwrap
from typing import Dict, List

# ---- Clients
from call_openai import call_openai
from call_anthropic import call_anthropic
from dotenv import load_dotenv
load_dotenv()


# ---- System prompts
SYSTEM_A = """Vous êtes Expert A : architecte IA “lean” orienté POC rapide.
Votre style : concret, frugal, itératif. Vous cherchez la solution minimale viable.

Règles du débat (5 tours maximum):
1) Tour 1: proposez votre plan (3–6 étapes) + micro-exemple d’implémentation.
2) Tour 2: réfutez la proposition de B (faiblesses, risques), proposez des garde-fous.
3) Tour 3: révisez votre plan à la lumière des objections de B (compromis).
4) Tour 4: converge avec B vers un plan commun (liste de décisions tranchées).
5) Tour 5: si l’orchestrateur dit “CONCLUSION”, écrivez la réponse finale actionnable (≤15 lignes).

Contraintes générales:
- Pas de généralités creuses: toujours un livrable (étapes, commande, snippet).
- Citez les hypothèses lorsque vous en faites.
- En cas d’info manquante, proposez un défaut raisonnable.
- Format concis, listes d’étapes numérotées.

"""
SYSTEM_B = """Vous êtes Expert B : ingénieur optimisation/programmation par contraintes.
Votre style : robustesse, conformité, scalabilité, qualité de solution.

Règles du débat (5 tours maximum):
1) Tour 1: proposez votre plan (3–6 étapes) + micro-exemple d’implémentation.
2) Tour 2: réfutez la proposition de A (précision, scalabilité, conformité), proposez des garde-fous.
3) Tour 3: révisez votre plan avec des concessions pragmatiques pour le POC.
4) Tour 4: converge avec A vers un plan commun (décisions explicites).
5) Tour 5: si l’orchestrateur dit “CONCLUSION”, n’écrivez rien à part “OK” (A sera le scribe final).

Contraintes générales:
- Soyez spécifique (solveur, variables, domaines, contraintes).
- Décrivez des métriques d’évaluation (faisabilité, optimalité, temps de calcul).
- Indiquez les risques et comment les tester rapidement.
- Format concis, listes d’étapes numérotées.

"""


# ---- Prompts de tour (templates)
def tour1_prompt(sujet, contexte, intrants, contraintes):
    return textwrap.dedent(f"""
    SUJET: {sujet}
    CONTEXTE: {contexte}
    INTRANTS CLES: {intrants}
    CONTRAINTES: {contraintes}
    OBJECTIF: produire un plan d’action (3–6 étapes) + micro-exemple d’implémentation.

    Consignes tour 1:
    - Proposez votre plan sans critiquer l’autre expert.
    - Mentionnez clairement vos hypothèses.
    """).strip()

def tour2_prompt(other):
    return textwrap.dedent(f"""
    Voici la proposition de l’autre expert :
    ---
    {other}
    ---
    Consignes tour 2:
    - Réfutez (précision, risques, coûts, scalabilité).
    - Proposez 1–2 garde-fous/test rapides.
    """).strip()

def tour3_prompt(summary_points):
    return textwrap.dedent(f"""
    Récap objections de l’autre:
    ---
    {summary_points}
    ---
    Consignes tour 3:
    - Révisez votre plan (compromis concrets).
    - Ajoutez une check-list de validation POC (≤6 items).
    """).strip()

def tour4_prompt():
    return textwrap.dedent("""
    Objectif tour 4: produire ensemble un plan commun.
    Consignes:
    - Listez 5–10 décisions tranchées (outil, modèle, solveur, métriques, données, livrables).
    - Si désaccord persiste: exposer l’option A, l’option B et un critère de choix.
    Répondez en ≤12 lignes.
    """).strip()

def tour5_conclusion_prompt():
    return textwrap.dedent("""
    CONCLUSION:
    - Synthèse finale actionnable (≤15 lignes).
    - Étapes techniques ordonnées + commandes/snippets.
    - Métriques d’acceptation du POC + jalons (Semaine 1/2/3).
    """).strip()

def summarize_for_exchange(text_a, text_b):
    """Mini résumé pour ne pas gonfler le contexte. (Optionnel: tu peux appeler A pour résumer.)"""
    return f"- Points A: {text_a[:800]}\n- Points B: {text_b[:800]}"

# ---- Orchestrateur 5 tours
def duel_llm(sujet, contexte, intrants, contraintes) -> Dict[str, str]:
    # Tour 1
    p1 = tour1_prompt(sujet, contexte, intrants, contraintes)
    out_a1 = call_openai(SYSTEM_A, p1)
    out_b1 = call_anthropic(SYSTEM_B, p1)

    # Tour 2 (réfutations)
    out_a2 = call_openai(SYSTEM_A, tour2_prompt(out_b1))
    out_b2 = call_anthropic(SYSTEM_B, tour2_prompt(out_a1))

    # Tour 3 (révisions)
    recap_for_a = summarize_for_exchange(out_b2, out_b1)
    recap_for_b = summarize_for_exchange(out_a2, out_a1)
    out_a3 = call_openai(SYSTEM_A, tour3_prompt(recap_for_a))
    out_b3 = call_anthropic(SYSTEM_B, tour3_prompt(recap_for_b))

    # Tour 4 (convergence)
    out_a4 = call_openai(SYSTEM_A, tour4_prompt())
    out_b4 = call_anthropic(SYSTEM_B, tour4_prompt())

    # Tour 5 (conclusion) -> A écrit, B dit OK
    out_a5 = call_openai(SYSTEM_A, tour5_conclusion_prompt())
    _ = call_anthropic(SYSTEM_B, "CONCLUSION — répondez « OK » et rien d’autre.")

    return {
        "A1": out_a1, "B1": out_b1,
        "A2": out_a2, "B2": out_b2,
        "A3": out_a3, "B3": out_b3,
        "A4": out_a4, "B4": out_b4,
        "FINAL": out_a5
    }

if __name__ == "__main__":
    sujet = "POC de planification sous contrainte (jour/nuit) pour 50 employés sur 4 semaines."
    contexte = "Equipe 2 personnes, deadline 2 semaines, infra Python + Docker, CPU-only."
    intrants = "CSV employés (id, compétence, contrat), CSV shifts (date,type,besoin), CSV règles métier."
    contraintes = "Audit des contraintes violées; livrables: planning.csv + score + rapport HTML."

    result = duel_llm(sujet, contexte, intrants, contraintes)
    print("\n=== TOUR 1 A ===\n", result["A1"])
    print("\n=== TOUR 1 B ===\n", result["B1"])
    print("\n=== TOUR 2 A ===\n", result["A2"])
    print("\n=== TOUR 2 B ===\n", result["B2"])
    print("\n=== TOUR 3 A ===\n", result["A3"])
    print("\n=== TOUR 3 B ===\n", result["B3"])
    print("\n=== TOUR 4 A ===\n", result["A4"])
    print("\n=== TOUR 4 B ===\n", result["B4"])
    print("\n=== CONCLUSION ===\n", result["FINAL"])

