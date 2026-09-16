import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";

const root = normalize(process.argv[2]);
const mime = { ".css": "text/css", ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml" };

createServer((request, response) => {
  const rawPath = new URL(request.url, "http://127.0.0.1").pathname;
  let path = join(root, rawPath);
  if (existsSync(path) && statSync(path).isDirectory()) path = join(path, "index.html");
  if (!path.startsWith(root) || !existsSync(path)) {
    response.writeHead(404).end("not found");
    return;
  }
  response.writeHead(200, { "Content-Type": mime[extname(path)] ?? "application/octet-stream" });
  createReadStream(path).pipe(response);
}).listen(8000, "127.0.0.1", () => console.log("documentation server ready"));
