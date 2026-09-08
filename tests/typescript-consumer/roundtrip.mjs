import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import ts from 'typescript';

const directory = process.argv[2] ? resolve(process.argv[2])
  : resolve(dirname(fileURLToPath(import.meta.url)), '../../vocabulary/generated');
const expected = JSON.parse(readFileSync(join(directory, 'wire-cases.json'), 'utf8')).values;
const temporary = mkdtempSync(join(tmpdir(), 'wire-typescript-'));
try {
  const source = readFileSync(join(directory, 'wire.ts'), 'utf8');
  writeFileSync(join(temporary, 'wire.ts'), source);
  writeFileSync(join(temporary, 'package.json'), '{"type":"commonjs"}');
  writeFileSync(join(temporary, 'consumer.ts'), `
import { POLICY_DECISIONS, DECISIONS, CAPTURE_TOPOLOGIES } from './wire';
import type { PolicyDecision, Decision, CaptureTopology } from './wire';
const policy: PolicyDecision = POLICY_DECISIONS[0];
const decision: Decision = DECISIONS[0];
const topology: CaptureTopology = CAPTURE_TOPOLOGIES[0];
// @ts-expect-error Literal membership excludes arbitrary strings.
const badPolicy: PolicyDecision = 'unregistered-fixture';
// @ts-expect-error Literal membership excludes arbitrary strings.
const badDecision: Decision = 'unregistered-fixture';
// @ts-expect-error Literal membership excludes arbitrary strings.
const badTopology: CaptureTopology = 'unregistered-fixture';
`);
  const program = ts.createProgram(['wire.ts', 'consumer.ts'].map(name => join(temporary, name)), {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
    strict: true, declaration: true, noEmitOnError: true,
  });
  const diagnostics = ts.getPreEmitDiagnostics(program);
  assert.deepEqual(diagnostics.map(d => ts.flattenDiagnosticMessageText(d.messageText, '\n')), []);
  assert.equal(program.emit().emitSkipped, false);
  const actual = createRequire(import.meta.url)(join(temporary, 'wire.js'));
  assert.deepEqual(actual, expected);
  assert.deepEqual(Object.keys(actual.METADATA), expected.METADATA_ORDER);
  assert.deepEqual(Object.keys(actual.FIELDS), expected.TAXONOMY_ORDER);
  const declarations = readFileSync(join(temporary, 'wire.d.ts'), 'utf8');
  for (const name of ['PolicyDecision', 'Decision', 'CaptureTopology']) {
    assert.match(declarations, new RegExp(`export type ${name} = \\(typeof [A-Z_]+\\)\\[number\\]`));
  }
  console.log(JSON.stringify({ compiler: ts.version, exports: Object.keys(actual).length,
    runtimeRoundtrip: true, declarations: true }));
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
