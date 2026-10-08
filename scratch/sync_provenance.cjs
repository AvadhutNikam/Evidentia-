const fs = require('fs');
const path = require('path');

const files = [
  'src/pages/case/Hypotheses.tsx',
  'src/pages/case/Contradictions.tsx',
  'src/pages/case/AnalysisWorkspace.tsx',
  'src/pages/case/EvidenceDetails.tsx',
  'src/services/index.ts',
  'src/engine/CaseStateEngine.ts'
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
console.log('Sync finished successfully.');
