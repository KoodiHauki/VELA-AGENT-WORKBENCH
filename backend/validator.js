#!/usr/bin/env node
/**
 * Headless Pine Script v5 / PineTS syntax validator
 */

const fs = require('fs');
const path = require('path');

let pinetsModule = null;
const possiblePaths = [
  path.join(__dirname, '..', 'frontend', 'node_modules', 'pinets'),
  'pinets',
];

for (const p of possiblePaths) {
  try {
    pinetsModule = require(p);
    break;
  } catch (_) {}
}

function readInput() {
  if (process.argv[2] && process.argv[2] !== '-') {
    if (fs.existsSync(process.argv[2])) {
      return fs.readFileSync(process.argv[2], 'utf8');
    }
    return process.argv[2];
  }
  return fs.readFileSync(0, 'utf8');
}

async function validate(sourceCode) {
  if (!sourceCode || !sourceCode.trim()) {
    return {
      valid: false,
      error: 'Tyhjä skripti. Anna validi Pine Script v5 -koodi.',
      line: 1,
    };
  }

  // Pre-check for Pine Script version
  const lines = sourceCode.split('\n');
  const hasVersion = lines.slice(0, 5).some(l => l.includes('//@version=5'));
  if (!hasVersion) {
    return {
      valid: false,
      error: "Puuttuva versiotunniste: Skriptin tulee alkaa rivillä '//@version=5'",
      line: 1,
    };
  }

  // Basic structure check
  const hasDeclaration = lines.some(l => {
    const t = l.trim();
    return t.startsWith('indicator(') || t.startsWith('strategy(');
  });
  if (!hasDeclaration) {
    return {
      valid: false,
      error: "Puuttuva deklaraatio: Skriptissä tulee olla 'indicator(...)' tai 'strategy(...)'",
      line: 1,
    };
  }

  if (!pinetsModule || !pinetsModule.PineTS) {
    return {
      valid: true,
      message: 'Perussyntaksi tarkistettu.',
    };
  }

  try {
    const { PineTS } = pinetsModule;
    // Provide a small array of 5 valid synthetic candles
    const now = Date.now();
    const mockCandles = [
      { openTime: now - 4000, open: 100, high: 105, low: 98, close: 102, volume: 10 },
      { openTime: now - 3000, open: 102, high: 107, low: 101, close: 106, volume: 15 },
      { openTime: now - 2000, open: 106, high: 108, low: 103, close: 104, volume: 12 },
      { openTime: now - 1000, open: 104, high: 109, low: 103, close: 108, volume: 18 },
      { openTime: now, open: 108, high: 110, low: 105, close: 107, volume: 14 },
    ];

    const engine = new PineTS(mockCandles);
    if (typeof engine.ready === 'function') {
      await engine.ready();
    }
    await engine.run(sourceCode);

    return {
      valid: true,
      message: 'Pine Script v5 -syntaksi ja ajo validoitu onnistuneesti.',
      transpiledLines: typeof engine.transpiledCode === 'string' ? engine.transpiledCode.split('\n').length : 1,
    };
  } catch (err) {
    let line = err.line;
    if (!line && err.loc && err.loc.line) {
      line = err.loc.line;
    }
    if (!line) {
      const matchAt = (err.message || '').match(/at\s+(\d+):(\d+)/i);
      const matchLine = (err.message || '').match(/line\s+(\d+)/i);
      if (matchAt) {
        line = parseInt(matchAt[1], 10);
      } else if (matchLine) {
        line = parseInt(matchLine[1], 10);
      }
    }
    return {
      valid: false,
      error: err.message || String(err),
      line: line || 1,
    };
  }
}

async function main() {
  try {
    const code = readInput();
    const result = await validate(code);
    process.stdout.write(JSON.stringify(result));
  } catch (e) {
    process.stdout.write(JSON.stringify({
      valid: false,
      error: e.message || String(e),
      line: 1,
    }));
  }
}

main();
