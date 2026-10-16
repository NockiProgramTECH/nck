---
title: Accueil
hide: [navigation]
---

# NCK — un langage simple, typé et en français

**NCK** est un langage de programmation pensé pour apprendre et produire vite : des mots-clés en français,
un typage statique clair (comme TypeScript ou Pydantic) qui attrape les erreurs *avant* l'exécution,
et rien à installer d'autre que `nck`.

```nck
classe Personne:
    nom: texte
    age: entier = 0

    fonction saluer() -> texte:
        retourner f"Bonjour, je suis {soi.nom} ({soi.age} ans)"
    fin
fin

variable amis: liste<Personne> = [Personne("Awa", 31), Personne(nom="Issa")]
pour p dans amis:
    ecrire(p.saluer())
fin
```

```text
Bonjour, je suis Awa (31 ans)
Bonjour, je suis Issa (0 ans)
```

<div class="grid cards" markdown>

-   :material-download: **Installer**

    ---

    Un installateur pour Windows et Linux — sans Python. Exécutables macOS reportés.

    [:octicons-arrow-right-24: Installation](INSTALLATION.md)

-   :material-school: **Apprendre**

    ---

    Un premier programme en 5 minutes, puis le tutoriel complet.

    [:octicons-arrow-right-24: Premier programme](tutoriel/premier-programme.md)

-   :material-book-open-variant: **Guide du langage**

    ---

    Chaque notion expliquée avec de petits exemples exécutables.

    [:octicons-arrow-right-24: Guide](guide/index.md)

-   :material-function: **Référence**

    ---

    Toutes les fonctions natives, la grammaire, les messages d'erreur.

    [:octicons-arrow-right-24: Fonctions natives](NATIFS.md)

</div>

## Pourquoi NCK ?

| | |
|---|---|
| **Lisible** | `si age >= 18: ecrire("majeur") fin` — les mots-clés sont ceux que vous pensez déjà. |
| **Sûr** | Les types sont vérifiés avant d'exécuter la première ligne : `age = "vingt"` est refusé avec la ligne et la colonne. |
| **Complet** | Classes, héritage, énumérations, erreurs `essayer`/`attraper`, modules, fonctions anonymes, dictionnaires, JSON, fichiers, dates. |
| **Outillé** | Extension VS Code (coloration, erreurs en direct, autocomplétion, survol, `F5`), REPL, vérificateur `nck verifier`. |
| **Portable** | Exécutables officiels Windows et Linux ; fichiers `.nck` ; support autonome macOS reporté. |

## En trois commandes

```bash
nck info                   # vérifie l'installation
nck verifier programme.nck # vérifie types et syntaxe sans exécuter
nck programme.nck          # exécute
```

!!! tip "Besoin d'un aperçu rapide ?"
    La page [Venir de Python ou JavaScript](tutoriel/depuis-python-js.md) montre les équivalences en une table.
