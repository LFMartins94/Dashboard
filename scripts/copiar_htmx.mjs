import { copyFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const origem = resolve("node_modules/htmx.org/dist/htmx.min.js");
const destino = resolve("web/static/vendor/htmx.min.js");

await mkdir(dirname(destino), { recursive: true });
await copyFile(origem, destino);
console.log("HTMX copiado para o diretório estático.");
