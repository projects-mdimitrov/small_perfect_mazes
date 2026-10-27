/* Export or verify the EXACT saved-study controls. No maze generation. */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');
const readline = require('readline');

const ROOT = path.resolve(__dirname, '..');
const ART = path.join(ROOT, 'article_all_algorithms_v1');
const RAW = path.join(ART, 'data/crossed_v1/runs.csv');
const MANIFEST = path.join(ART, 'data/crossed_v1/manifest.json');
const HTML = path.join(ROOT, 'maze_analytics_lab-15.html');
const STUDY_ID = 'maze-crossed-algorithms-constants-2026-v1';
const BLOCKS = 192000, DIGITS = BLOCKS * 5;
const DESIGNS = [
  {series:'primary_10x10', grid:'10x10', corpora:64, windows:32, budget:6000, filename:'control_10x10.jsonl'},
  {series:'secondary_20x20', grid:'20x20', corpora:16, windows:16, budget:12000, filename:'control_20x20.jsonl'}
];
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const fileSha = filename => sha(fs.readFileSync(filename));
function check(value, message) { if (!value) throw new Error(message); }
function seedFor(index) { return `${STUDY_ID}/pseudo-iid/${String(index).padStart(3, '0')}`; }

function csvLine(line) {
  const fields = []; let field = '', quoted = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') {
      if (quoted && line[i+1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (c === ',' && !quoted) { fields.push(field); field = ''; }
    else field += c;
  }
  check(!quoted, 'Unexpected multiline CSV field');
  fields.push(field); return fields;
}

function loadCore() {
  const html = fs.readFileSync(HTML, 'utf8');
  const context = vm.createContext({console, performance, crypto:crypto.webcrypto,
    TextEncoder, Uint8Array, Uint32Array, Int32Array, DataView, Map, Set});
  vm.runInContext(html.slice(html.indexOf('<script>')+8, html.lastIndexOf('</script>')), context);
  check(context.MazeLabCore, 'Missing frozen core export');
  return context.MazeLabCore;
}

async function references() {
  const manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
  check(fileSha(RAW) === manifest.runs_csv_sha256, 'Raw CSV hash mismatch');
  check(fileSha(HTML) === manifest.html_sha256, 'HTML hash mismatch');
  check(fileSha(path.join(ART, 'run_crossed_study.js')) === manifest.runner_sha256, 'Runner hash mismatch');
  const populations = new Map(DESIGNS.map(d => [d.series, new Map()]));
  let columns = null, rawRows = 0, controls = 0;
  const lines = readline.createInterface({input:fs.createReadStream(RAW, {encoding:'utf8'}), crlfDelay:Infinity});
  for await (const line of lines) {
    if (!columns) { columns = csvLine(line); continue; }
    if (!line) continue;
    const values = csvLine(line); rawRows++;
    check(values.length === columns.length, `CSV width at row ${rawRows}`);
    const r = Object.fromEntries(columns.map((c, i) => [c, values[i]]));
    if (r.source_role !== 'pseudo_iid_control') continue;
    controls++;
    const design = DESIGNS.find(d => d.series === r.series);
    check(design, 'Unexpected control series');
    const index = Number(r.corpus_seed.split('/').at(-1));
    check(Number.isInteger(index) && index >= 1 && index <= design.corpora && r.corpus_seed === seedFor(index), 'Unexpected seed');
    check(r.source_id === 'control_pseudo_iid_decimal', 'Unexpected source ID');
    const w = Number(r.window_index);
    check(Number.isInteger(w) && w >= 0 && w < design.windows, 'Bad window index');
    check(Number(r.units_budget) === design.budget && Number(r.digit_start) === w*design.budget*5 &&
      Number(r.digit_end_exclusive) === (w+1)*design.budget*5, 'Bad window boundaries');
    const population = populations.get(design.series);
    if (!population.has(r.corpus_seed)) population.set(r.corpus_seed, {sha256:r.source_sha256, keys:new Set()});
    const item = population.get(r.corpus_seed), key = `${r.algorithm}/${w}`;
    check(item.sha256 === r.source_sha256 && !item.keys.has(key), 'Inconsistent corpus hash or duplicate run');
    check(manifest.algorithms.includes(r.algorithm), 'Unknown algorithm');
    item.keys.add(key);
  }
  check(rawRows === manifest.rows && controls === 32256, 'Wrong archived population count');
  for (const d of DESIGNS) {
    const population = populations.get(d.series);
    check(population.size === d.corpora, 'Wrong number of corpora');
    for (let i = 1; i <= d.corpora; i++) {
      const item = population.get(seedFor(i));
      check(item && item.keys.size === manifest.algorithms.length*d.windows, 'Wrong per-corpus attempt count');
    }
  }
  return {manifest, populations, controls};
}

function record(index, digits) {
  return {corpus_index:index, corpus_seed:seedFor(index), source_sha256:sha(digits), digits};
}

async function exportFiles(out, refs, Core) {
  // Refuse existing targets; never replace an archived corpus file.
  for (const d of DESIGNS) check(!fs.existsSync(path.join(out, d.filename)), `Output already exists: ${d.filename}`);
  check(!fs.existsSync(path.join(out, 'manifest.json')), 'Output manifest already exists');
  fs.mkdirSync(out, {recursive:true});
  const handles = DESIGNS.map(d => fs.openSync(path.join(out, d.filename), 'wx'));
  const details = [];
  try {
    for (let i = 1; i <= 64; i++) {
      const telemetry = {raw_draws:0, rejected_draws:0};
      const digits = Core.makeIidDecimal5Digits(BLOCKS, new Core.Xoshiro128StarStar(seedFor(i)), telemetry);
      check(digits.length === DIGITS && /^[0-9]+$/.test(digits), 'Generated digit format mismatch');
      const entry = record(i, digits);
      for (let j = 0; j < DESIGNS.length; j++) {
        const d = DESIGNS[j];
        if (i > d.corpora) continue;
        check(entry.source_sha256 === refs.populations.get(d.series).get(entry.corpus_seed).sha256, 'Generated corpus differs from frozen experiment');
        fs.writeSync(handles[j], JSON.stringify(entry) + '\n');
      }
      details.push({corpus_index:i, corpus_seed:entry.corpus_seed, source_sha256:entry.source_sha256,
        digits:DIGITS, decimal5_blocks:BLOCKS, prng_raw_draws:telemetry.raw_draws, prng_rejected_draws:telemetry.rejected_draws});
    }
  } finally { for (const fd of handles) fs.closeSync(fd); }
  const manifest = {format_version:'control-decimal-jsonl-v1', encoding:'UTF-8 without BOM; LF line endings',
    record_fields:['corpus_index', 'corpus_seed', 'source_sha256', 'digits'],
    digit_encoding:'digits is an exact ASCII decimal string, not a numeric JSON value; leading zeros preserved',
    source_digits_per_corpus:DIGITS, decimal5_blocks_per_corpus:BLOCKS,
    generator:'cyrb128(text seed) -> xoshiro128** -> uniformUintBelow(100000), padded to five decimal digits',
    source_html_sha256:refs.manifest.html_sha256, frozen_runner_sha256:refs.manifest.runner_sha256,
    frozen_runs_csv_sha256:refs.manifest.runs_csv_sha256,
    files:DESIGNS.map(d => ({...d, bytes:fs.statSync(path.join(out, d.filename)).size,
      sha256:fileSha(path.join(out, d.filename))})),
    overlap:'The complete 16 records for 20x20 are identical to the first 16 records for 10x10; they are not independent new corpora.',
    corpora:details};
  fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify(manifest, null, 2)+'\n', {flag:'wx'});
}

async function verifyFiles(out, refs, Core) {
  const manifest = JSON.parse(fs.readFileSync(path.join(out, 'manifest.json'), 'utf8'));
  check(manifest.frozen_runs_csv_sha256 === refs.manifest.runs_csv_sha256 && manifest.source_html_sha256 === refs.manifest.html_sha256,
    'Export manifest source mismatch');
  const hashes10 = new Map(); let records = 0;
  for (const d of DESIGNS) {
    const filename = path.join(out, d.filename);
    const info = manifest.files.find(f => f.filename === d.filename);
    check(info && fileSha(filename) === info.sha256 && fs.statSync(filename).size === info.bytes, 'Export file checksum mismatch');
    const head = Buffer.alloc(3); const fd = fs.openSync(filename, 'r');
    try { fs.readSync(fd, head, 0, 3, 0); } finally { fs.closeSync(fd); }
    check(!(head[0] === 0xef && head[1] === 0xbb && head[2] === 0xbf), 'Unexpected BOM');
    let count = 0;
    const lines = readline.createInterface({input:fs.createReadStream(filename, {encoding:'utf8'}), crlfDelay:Infinity});
    for await (const line of lines) {
      check(line.length > 0, 'Blank JSONL record');
      const r = JSON.parse(line); count++; records++;
      check(r.corpus_index === count && r.corpus_seed === seedFor(count), 'Wrong record ordering');
      check(typeof r.digits === 'string' && r.digits.length === DIGITS && /^[0-9]+$/.test(r.digits), 'Wrong saved digit string');
      const hash = sha(r.digits), source = refs.populations.get(d.series).get(r.corpus_seed);
      check(source && hash === r.source_sha256 && hash === source.sha256, 'Saved source hash mismatch');
      const regenerated = Core.makeIidDecimal5Digits(BLOCKS,
        new Core.Xoshiro128StarStar(r.corpus_seed), {raw_draws:0, rejected_draws:0});
      check(r.digits === regenerated, 'Saved sequence does not equal frozen PRNG replay');
      if (d.grid === '10x10') hashes10.set(count, hash);
      else check(hashes10.get(count) === hash, 'Shared control corpus differs across sizes');
    }
    check(count === d.corpora, 'Wrong saved corpus count');
  }
  return {status:'pass', files:2, saved_records:records, unique_corpora:64,
    digits_per_corpus:DIGITS, control_rows_checked:refs.controls,
    all_saved_source_hashes_match_raw:true, all_saved_digits_match_seed_replay:true,
    secondary_matches_primary_first_16:true, raw_csv_sha256:refs.manifest.runs_csv_sha256,
    file_checks:manifest.files.map(f => ({filename:f.filename, records:f.corpora, bytes:f.bytes, sha256:f.sha256}))};
}

async function main() {
  const mode = process.argv[2];
  check(['--export', '--verify'].includes(mode), 'Use --export or --verify, optionally followed by --out NEW_DIRECTORY');
  check(process.argv.length === 3 || (process.argv.length === 5 && process.argv[3] === '--out'), 'Unexpected arguments');
  const out = process.argv.length === 5 ? path.resolve(process.argv[4]) : path.join(ROOT, 'control_corpora');
  const refs = await references(), Core = loadCore();
  if (mode === '--export') await exportFiles(out, refs, Core);
  const result = await verifyFiles(out, refs, Core);
  if (mode === '--export') {
    fs.writeFileSync(path.join(out, 'export_check.json'), JSON.stringify(result, null, 2)+'\n', {flag:'wx'});
  }
  check(fileSha(RAW) === refs.manifest.runs_csv_sha256 && fileSha(HTML) === refs.manifest.html_sha256, 'A scientific input changed');
  console.log(JSON.stringify(result, null, 2));
}

main().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
