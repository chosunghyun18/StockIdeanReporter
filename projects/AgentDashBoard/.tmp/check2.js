const fs = require('fs');
const path = require('path');
const AGENTS_DIR = '/Users/jo/Desktop/josh/agents';

function parseFrontmatter(content) {
  const meta = {};
  const m = content.match(/^---\n([\s\S]*?)\n---/);
  if (m == null) return meta;
  for (const line of m[1].split('\n')) {
    if (line.indexOf(':') === -1) continue;
    const colonIdx = line.indexOf(':');
    const key = line.slice(0, colonIdx).trim();
    const raw = line.slice(colonIdx + 1).trim().replace(/^"|"$/g, '');
    if (raw.startsWith('[') && raw.endsWith(']')) {
      meta[key] = raw.slice(1, -1).split(',').map(x => x.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean);
    } else {
      meta[key] = raw;
    }
  }
  return meta;
}

const files = fs.readdirSync(AGENTS_DIR).filter(f => f.endsWith('.md')).sort();
const agents = [];
for (const f of files) {
  const slug = f.replace('.md', '');
  const content = fs.readFileSync(path.join(AGENTS_DIR, f), 'utf-8');
  const meta = parseFrontmatter(content);
  agents.push({ slug, name: meta.name || slug, calls: meta.calls || [] });
}

const found = agents.find(a => a.slug === 'it-orchestrator');
console.log('Total agents:', agents.length);
console.log('it-orchestrator found:', found ? JSON.stringify(found) : 'NOT FOUND');
