const fs = require('fs');
const content = fs.readFileSync('/Users/jo/Desktop/josh/agents/it-orchestrator.md', 'utf-8');
const m = content.match(/^---\n([\s\S]*?)\n---/);
console.log('frontmatter:', m ? 'FOUND' : 'NOT FOUND');
if (m) {
  for (const line of m[1].split('\n')) {
    if (line.indexOf(':') === -1) continue;
    const idx = line.indexOf(':');
    const key = line.slice(0, idx).trim();
    const raw = line.slice(idx + 1).trim();
    console.log(key, '->', raw.slice(0, 80));
  }
}
