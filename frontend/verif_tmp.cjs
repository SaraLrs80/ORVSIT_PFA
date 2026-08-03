// Fichier temporaire de vérification — supprimable.
const p=require("@babel/parser"), fs=require("fs");
for (const f of process.argv.slice(2)) {
  try { p.parse(fs.readFileSync(f,"utf8"), {sourceType:"module", plugins:["jsx"]}); console.log("OK  ", f); }
  catch(e) { console.log("ERR ", f, "->", e.message); process.exitCode=1; }
}
