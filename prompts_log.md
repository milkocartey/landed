# Prompt log — AAA Group 42 project

Prompts sent to Claude (Anthropic) during the design and build of the application.
Kept verbatim (original language: French) for the "show us where and how you used AI tools" requirement.

---

## 1 — 2026-10-24 22:16
> retiens tous mes prompts au fil de la conv dans un endroit à part qui ne te rempli pas ton contexte.
>
> j'ai ça à faire, on va déjà essayer de determiner une idée : [assignment brief pasted: Peer assessment - Advanced AI Algorithms (AAA) — create your own AI application with existing tools, 5-min demo video, code + data + user guide, cite packages, report prompts used]

## 2 — 2026-10-24 22:19
> pitchperfect on peut aller le chercher sur hugginface ?

## 3 — 2026-10-24 22:22
> ok explorons d'autres idées. Il faut partir d'un besoin réel. Aide moi à trouver. J'ai bien dit aide moi, pas trouve

## 4 — 2026-10-24 22:25
> les candidatures pour trouver nos stages. Un enfer

## 5 — 2026-10-24 22:29
> il faudrait une app qui : charge ton cv, l'analyse, lance des recherches sur différents sites pour trouver des offres qui matchent avc ton cv, te sors des cv modifiés + ldm adaptés à chaque offre et idéalement qui peut tourner sur un abonnement claude gratuit pour que tout le monde puisse en profiter. Il faut aussi qu'il te fasse un onglet tracking de tes offres, afin qu'on puisse renseigner les avancements de nos recherches clairement (un dashboard/crm quoi). On va utiliser huggingface (j'ai un compte, est ce que je peux le plug à toi?) et motion.dev afin d'avoir des animations stylées pour l'app. Comme tu l'a dis, le but c'est aussi d'avoir une app avec un bon visuel donc passe du temps là dessus.

## 6 — 2026-10-24 22:33
> ok bon open source alors, pour les recherches d'offres, est ce que y'a pas d'autres API gratuites qui peuvent être utiles ? Jobteaser par exemple serait bien pcq c'est une boite de l'école. C'est quoi react ? tu peux pas le faire toi meme ?

## 7 — 2026-10-24 22:40
> oui en anglais stp

## 8 — 2026-10-25 (session 2 — live offers debugging)
> pourquoi est ce que les offres sont fictives ?

## 9 — 2026-10-25
> y'a pas un autre moyen pour recup les offres légalement ? Parce que là c'est très institutionnel adzuna, un projet open source or something

## 10 — 2026-10-25
> ma filière c'est Strategy and Management of International Business à l'ESSEC Business School, il faut des offres qui correspondent aux différents secteurs qu'attendent les étudiant (Cabinet de conseil, startup tech, Paris ou Singapour)

## 11 — 2026-10-25
> les offres apparaissent mais sont fausses : This job may have expired...

## 12 — 2026-10-25
> y'a pas le meme type d'api pour Paris ou la France spécifiquement ?

---

## 13 — 2026-10-26 (session 3 — comprehensive refactor, phases 0-4)
> [Large structured prompt specifying a 4-phase refactor with a deadline of October 29, 23:59:
> Phase 0: safety net (git init, audit, plan);
> Phase 1: fix live offers / remove broken sources;
> Phase 2: clean interface (paste CV text, paste offer inline, remove broken source buttons);
> Phase 3: bias check (offer wording analysis EN+FR, counterfactual fairness test, Amazon replay);
> Phase 4: verify, document, package.]

## 14 — 2026-10-26
> supprime les 3
> [Remove Arbeitnow, France Travail, MyCareersFuture — confirmed after Claude proposed it]

## 15 — 2026-10-26
> phase 2

## 16 — 2026-10-26
> phase 3

## 17 — 2026-10-27
> phase 4
