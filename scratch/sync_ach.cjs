const fs = require('fs');
const path = require('path');

const files = [
  'backend/ach_engine.py',
  'backend/models.py',
  'backend/schemas.py',
  'backend/app.py',
  'src/types/index.ts',
  'src/services/index.ts',
  'src/pages/case/Hypotheses.tsx',
  'scratch/migrate_ach.py'
];

const targets = [
  'D:/Avadhut/project/major/new v2/Evidentia-AI-main',
  'D:/Avadhut/project/major/new/Evidentia-AI-main/Evidentia-AI-main'
];

const srcBase = 'd:/Avadhut/project/Evidentia-AI-main/Evidentia-AI-main';

for (const target of targets) {
  for (const rel of files) {
    const srcPath = path.join(srcBase, rel);
    const destPath = path.join(target, rel);
    try {
      fs.mkdirSync(path.dirname(destPath), { recursive: true });
      fs.copyFileSync(srcPath, destPath);
      console.log(`Synced: ${rel} -> ${target}`);
    } catch (e) {
      console.error(`Failed to sync ${rel} to ${target}:`, e.message);
    }
  }
}
console.log('ACH Engine sync finished successfully.');
