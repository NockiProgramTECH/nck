// Extension VS Code pour NCK : lance `nck serveur` (Python) et lui délègue
// l'autocomplétion, le survol, l'aide à la signature, la définition et les diagnostics.
// Aucune dépendance npm : le protocole est une ligne JSON par requête.

const vscode = require("vscode");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

let serveur = null;
let tampon = "";
let prochainId = 1;
const enAttente = new Map();
let diagnostics;
let sortie;
const minuteries = new Map();

const GENRES = {
  Variable: vscode.CompletionItemKind.Variable,
  Constant: vscode.CompletionItemKind.Constant,
  Function: vscode.CompletionItemKind.Function,
  Class: vscode.CompletionItemKind.Class,
  Module: vscode.CompletionItemKind.Module,
  Field: vscode.CompletionItemKind.Field,
  Method: vscode.CompletionItemKind.Method,
  Keyword: vscode.CompletionItemKind.Keyword,
  TypeParameter: vscode.CompletionItemKind.TypeParameter,
  Text: vscode.CompletionItemKind.Text,
};

function trouverNck() {
  // Cherche l'exécutable autonome « nck » (installé par NCK-Setup / installer.sh) dans le PATH.
  const noms = process.platform === "win32" ? ["nck.exe", "nck.cmd", "nck.bat"] : ["nck"];
  for (const dossier of (process.env.PATH || "").split(path.delimiter)) {
    if (!dossier) continue;
    for (const nom of noms) {
      const chemin = path.join(dossier, nom);
      try { fs.accessSync(chemin, fs.constants.X_OK); return chemin; } catch (e) { /* suivant */ }
    }
  }
  return null;
}

// Retourne { programme, args, dossierRepo, affichage } : la commande à lancer pour obtenir « nck <sous-commande> ».
// Priorité : réglage nck.commande > exécutable nck du PATH > python -m nck.
function commandeNck() {
  const config = vscode.workspace.getConfiguration("nck");
  const dossierRepo = config.get("dossierNck") || "";
  const commande = (config.get("commande") || "").trim();
  if (commande) return { programme: commande, args: [], dossierRepo, affichage: commande };
  if (!dossierRepo) {
    const exe = trouverNck();
    if (exe) return { programme: exe, args: [], dossierRepo, affichage: exe };
  }
  const python = config.get("python") || (process.platform === "win32" ? "python" : "python3");
  return { programme: python, args: ["-m", "nck"], dossierRepo, affichage: `${python} -m nck` };
}

function demarrerServeur(contexte) {
  if (serveur) return;
  const { programme, args, dossierRepo, affichage } = commandeNck();
  const options = { env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" } };
  if (dossierRepo) {
    options.cwd = dossierRepo;
    options.env.PYTHONPATH = dossierRepo + (process.env.PYTHONPATH ? path.delimiter + process.env.PYTHONPATH : "");
  }
  sortie.appendLine(`Démarrage : ${affichage} serveur` + (dossierRepo ? ` (dans ${dossierRepo})` : ""));
  try {
    serveur = spawn(programme, [...args, "serveur"], options);
  } catch (e) {
    sortie.appendLine("Impossible de lancer NCK : " + e.message);
    serveur = null;
    return;
  }
  serveur.stdout.setEncoding("utf-8");
  serveur.stdout.on("data", (morceau) => {
    tampon += morceau;
    let i;
    while ((i = tampon.indexOf("\n")) >= 0) {
      const ligne = tampon.slice(0, i).trim();
      tampon = tampon.slice(i + 1);
      if (!ligne) continue;
      let rep;
      try { rep = JSON.parse(ligne); } catch (e) { sortie.appendLine("Réponse illisible : " + ligne); continue; }
      const p = enAttente.get(rep.id);
      if (!p) continue;
      enAttente.delete(rep.id);
      if (rep.erreur) { sortie.appendLine("Erreur serveur : " + rep.erreur + "\n" + (rep.trace || "")); p.resolve(null); }
      else p.resolve(rep.resultat);
    }
  });
  serveur.stderr.setEncoding("utf-8");
  serveur.stderr.on("data", (d) => sortie.appendLine("[python] " + d));
  serveur.on("exit", (code) => {
    sortie.appendLine(`Le serveur NCK s'est arrêté (code ${code}).`);
    serveur = null;
    for (const p of enAttente.values()) p.resolve(null);
    enAttente.clear();
    if (code !== 0) {
      vscode.window.showWarningMessage(
        "Le serveur NCK n'a pas pu démarrer. Vérifiez que Python est installé et que le paquet nck est accessible " +
        "(pip install -e . dans le dépôt, ou réglez « nck.dossierNck »). Voir le panneau de sortie « NCK ».");
    }
  });
}

function requete(methode, params) {
  return new Promise((resolve) => {
    if (!serveur) demarrerServeur();
    if (!serveur) return resolve(null);
    const id = prochainId++;
    enAttente.set(id, { resolve });
    serveur.stdin.write(JSON.stringify({ id, methode, ...params }) + "\n");
    setTimeout(() => { if (enAttente.has(id)) { enAttente.delete(id); resolve(null); } }, 5000);
  });
}

function fichierDe(document) { return document.uri.fsPath || document.uri.toString(); }

async function analyser(document) {
  if (document.languageId !== "nck") return;
  const res = await requete("analyser", { fichier: fichierDe(document), texte: document.getText() });
  if (!res) return;
  const liste = (res.diagnostics || []).map((d) => {
    const ligne = Math.max(d.ligne - 1, 0), col = Math.max(d.colonne - 1, 0);
    const plage = new vscode.Range(ligne, col, ligne, col + Math.max(d.longueur, 1));
    const diag = new vscode.Diagnostic(plage, d.message,
      d.gravite === "avertissement" ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error);
    diag.source = "nck";
    return diag;
  });
  diagnostics.set(document.uri, liste);
}

function analyserBientot(document) {
  const cle = document.uri.toString();
  clearTimeout(minuteries.get(cle));
  minuteries.set(cle, setTimeout(() => analyser(document), 300));
}

function activate(contexte) {
  sortie = vscode.window.createOutputChannel("NCK");
  diagnostics = vscode.languages.createDiagnosticCollection("nck");
  contexte.subscriptions.push(sortie, diagnostics);
  demarrerServeur(contexte);

  const selecteur = { language: "nck" };

  contexte.subscriptions.push(vscode.languages.registerCompletionItemProvider(selecteur, {
    async provideCompletionItems(document, position) {
      const res = await requete("completer", {
        fichier: fichierDe(document), texte: document.getText(), ligne: position.line + 1, colonne: position.character + 1,
      });
      if (!res) return [];
      return res.items.map((it) => {
        const item = new vscode.CompletionItem(it.nom, GENRES[it.genre] || vscode.CompletionItemKind.Text);
        item.detail = it.detail;
        if (it.doc) item.documentation = new vscode.MarkdownString(it.doc);
        item.insertText = it.insertion;
        if (it.insertion.endsWith("(")) item.command = { command: "editor.action.triggerParameterHints", title: "" };
        return item;
      });
    },
  }, "."));

  contexte.subscriptions.push(vscode.languages.registerHoverProvider(selecteur, {
    async provideHover(document, position) {
      const res = await requete("survoler", {
        fichier: fichierDe(document), texte: document.getText(), ligne: position.line + 1, colonne: position.character + 1,
      });
      if (!res || !res.survol) return null;
      const s = res.survol;
      const plage = new vscode.Range(s.ligne - 1, s.colonne - 1, s.ligne - 1, s.colonne - 1 + s.longueur);
      return new vscode.Hover(new vscode.MarkdownString(s.contenu), plage);
    },
  }));

  contexte.subscriptions.push(vscode.languages.registerSignatureHelpProvider(selecteur, {
    async provideSignatureHelp(document, position) {
      const res = await requete("signature", {
        fichier: fichierDe(document), texte: document.getText(), ligne: position.line + 1, colonne: position.character + 1,
      });
      if (!res || !res.signature) return null;
      const s = res.signature;
      const info = new vscode.SignatureInformation(s.label, s.doc ? new vscode.MarkdownString(s.doc) : undefined);
      info.parameters = s.parametres.map((p) => new vscode.ParameterInformation(p));
      const aide = new vscode.SignatureHelp();
      aide.signatures = [info];
      aide.activeSignature = 0;
      aide.activeParameter = s.actif;
      return aide;
    },
  }, "(", ","));

  contexte.subscriptions.push(vscode.languages.registerDefinitionProvider(selecteur, {
    async provideDefinition(document, position) {
      const res = await requete("definition", {
        fichier: fichierDe(document), texte: document.getText(), ligne: position.line + 1, colonne: position.character + 1,
      });
      if (!res || !res.definition) return null;
      const d = res.definition;
      const uri = d.fichier.startsWith("<") ? document.uri : vscode.Uri.file(d.fichier);
      return new vscode.Location(uri, new vscode.Position(d.ligne - 1, d.colonne - 1));
    },
  }));

  contexte.subscriptions.push(vscode.commands.registerCommand("nck.executer", () => {
    const editeur = vscode.window.activeTextEditor;
    if (!editeur || editeur.document.languageId !== "nck") return;
    editeur.document.save().then(() => {
      const { affichage, dossierRepo } = commandeNck();
      const terminal = vscode.window.terminals.find((t) => t.name === "NCK") || vscode.window.createTerminal("NCK");
      terminal.show();
      const env = dossierRepo ? (process.platform === "win32" ? `$env:PYTHONPATH="${dossierRepo}"; ` : `PYTHONPATH="${dossierRepo}" `) : "";
      const prog = affichage.includes(" ") && !affichage.includes(" -m ") ? `& "${affichage}"` : affichage;
      terminal.sendText(`${env}${prog} "${editeur.document.uri.fsPath}"`);
    });
  }));

  contexte.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(analyser),
    vscode.workspace.onDidChangeTextDocument((e) => analyserBientot(e.document)),
    vscode.workspace.onDidCloseTextDocument((doc) => {
      diagnostics.delete(doc.uri);
      requete("fermer", { fichier: fichierDe(doc) });
    }),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("nck") && serveur) { serveur.kill(); serveur = null; demarrerServeur(); }
    }),
  );
  vscode.workspace.textDocuments.forEach(analyser);
}

function deactivate() {
  if (serveur) { serveur.kill(); serveur = null; }
}

module.exports = { activate, deactivate };
