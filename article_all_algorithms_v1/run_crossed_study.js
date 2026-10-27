/* New crossed study. Loads, but never modifies, Maze Analytics Lab v15. */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..');
const HTML_PATH = path.join(ROOT, 'maze_analytics_lab-15.html');
const PROTOCOL_PATH = path.join(HERE, 'protocol.md');
const OUT = path.join(HERE, 'data', 'crossed_v1');
const ALGORITHMS = Object.freeze([
  'dfs', 'prim', 'kruskal', 'wilson', 'aldous', 'hunt', 'growing',
  'division', 'eller', 'sidewinder', 'binary_ur', 'binary_dr',
  'binary_ul', 'binary_dl'
]);
const IRRATIONALS = Object.freeze([
  'pi', 'e', 'phi', 'sqrt2', 'sqrt3', 'sqrt5', 'sqrt7',
  'ln2', 'inv_pi', 'inv_e', 'apery'
]);
const ADDITIONAL = Object.freeze(['euler_m']);
const SIZES = Object.freeze([
  Object.freeze({series:'primary_10x10', cols:10, rows:10, windows:32, budget:6000, controls:64}),
  Object.freeze({series:'secondary_20x20', cols:20, rows:20, windows:16, budget:12000, controls:16})
]);
const STUDY_ID = 'maze-crossed-algorithms-constants-2026-v1';

function sha256(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function csvCell(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '';
  const s = String(value);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
function loadCore() {
  const html = fs.readFileSync(HTML_PATH, 'utf8');
  const start = html.indexOf('<script>');
  const end = html.lastIndexOf('</script>');
  if (start < 0 || end <= start) throw new Error('Cannot locate v15 inline JavaScript');
  const context = vm.createContext({console, performance, crypto:crypto.webcrypto,
    TextEncoder, Uint8Array, Uint32Array, Int32Array, DataView, Map, Set});
  vm.runInContext(html.slice(start + 8, end), context, {filename:path.basename(HTML_PATH)});
  if (!context.MazeLabCore) throw new Error('v15 core export missing');
  return context.MazeLabCore;
}
class CsvWriter {
  constructor(filename) {
    this.fd = fs.openSync(filename, 'wx');
    this.columns = null;
    this.rows = 0;
    this.statuses = {};
  }
  write(record) {
    if (!this.columns) {
      this.columns = Object.keys(record);
      fs.writeSync(this.fd, this.columns.join(',') + '\n');
    }
    fs.writeSync(this.fd, this.columns.map(key => csvCell(record[key])).join(',') + '\n');
    this.rows++;
    this.statuses[record.status] = (this.statuses[record.status] || 0) + 1;
    if (this.rows % 1000 === 0) console.log(`Completed ${this.rows} attempts`);
  }
  close() { fs.closeSync(this.fd); }
}

function verifiedSources(Core) {
  const result = new Map();
  for (const id of [...IRRATIONALS, ...ADDITIONAL]) {
    const spec = Core.SOURCES[id];
    if (!spec) throw new Error(`Missing source ${id}`);
    const raw = fs.readFileSync(path.join(ROOT, spec.file));
    const actualHash = sha256(raw);
    const digits = raw.toString('ascii');
    if (raw.length !== spec.length || actualHash !== spec.sha256 || !/^[0-9]+$/.test(digits)) {
      throw new Error(`Source identity/format mismatch for ${id}`);
    }
    if (digits.length < 960000) throw new Error(`Source ${id} is too short for the fixed schedule`);
    result.set(id, {digits, file:spec.file, length:digits.length, sha256:actualHash,
      arithmetic_status:id === 'euler_m' ? 'unknown' : 'proven_irrational'});
  }
  return result;
}

function one(Core, source, sourceId, size, algorithm, index, corpusSeed = '') {
  const startBlock = index * size.budget;
  const endBlock = startBlock + size.budget;
  const digitStart = startBlock * 5;
  const digitEnd = endBlock * 5;
  const stream = new Core.DigitStream(source.digits, digitStart, digitEnd);
  const design = Core.designForRun('balanced_opposite', index, size.cols, size.rows, algorithm);
  const maze = new Core.Maze(size.cols, size.rows);
  let status = 'ok', errorCode = '', graph = null, metrics = null, completed = false;
  try {
    Core.generateMaze(algorithm, maze, stream,
      {constructionRootIndex:design.construction_root_index});
    completed = true;
    graph = Core.buildValidatedGraph(maze, true,
      design.solution_start_index, design.solution_goal_index);
    if (!graph.validation.perfect_maze) {
      status = 'invalid_topology';
      errorCode = graph.validation.validation_errors.join('|');
    } else {
      metrics = Core.analyzeMaze(maze, graph,
        design.solution_start_index, design.solution_goal_index);
    }
  } catch (error) {
    status = error instanceof Core.DigitStreamExhaustedError ? 'stream_exhausted' : 'generation_error';
    errorCode = error.code || error.name;
  }
  const wallCode = Core.wallCodeHex(maze);
  const wallSha = metrics ? sha256(`maze-wall-hex-v1\n${size.cols}x${size.rows}\n${wallCode}`) : '';
  const record = {
    study_id:STUDY_ID,
    series:size.series,
    source_id:sourceId,
    source_role:source.arithmetic_status === 'pseudo_iid_control' ? 'pseudo_iid_control' :
      source.arithmetic_status === 'unknown' ? 'unknown_irrationality' : 'known_irrational',
    source_sha256:source.sha256,
    corpus_seed:corpusSeed,
    algorithm,
    cols:size.cols,
    rows:size.rows,
    window_index:index,
    digit_phase:0,
    digit_start:digitStart,
    digit_end_exclusive:digitEnd,
    units_budget:size.budget,
    endpoint_pair_id:design.endpoint_pair_id,
    solution_start_index:design.solution_start_index,
    solution_goal_index:design.solution_goal_index,
    construction_root_index:design.construction_root_index,
    status,
    error_code:errorCode,
    algorithm_completed:completed,
    perfect_maze:Boolean(graph && graph.validation.perfect_maze),
    units_read:stream.unitsRead,
    rejected_units:stream.rejectedUnits,
    next_int_calls:stream.nextIntCalls,
    wall_code_hex:metrics ? wallCode : '',
    wall_sha256:wallSha,
    maze_hash_fnv1a32:metrics ? metrics.maze_hash_fnv1a32 : '',
  };
  for (const metric of Core.METRIC_COLUMNS) record[metric] = metrics ? metrics[metric] : null;
  return record;
}

function selfTest(Core) {
  if (ALGORITHMS.length !== Object.keys(Core.GENERATORS).length ||
      ALGORITHMS.some(id => !Core.GENERATORS[id])) throw new Error('Algorithm list no longer matches HTML');
  const sources = verifiedSources(Core);
  const mock = {digits:Core.makeIidDecimal5Digits(12000,
    new Core.Xoshiro128StarStar(`${STUDY_ID}/self-test`), {raw_draws:0,rejected_draws:0}),
    sha256:'self-test', arithmetic_status:'pseudo_iid_control'};
  const issues = [];
  for (const algorithm of ALGORITHMS) {
    const row = one(Core, mock, 'self_test', SIZES[0], algorithm, 0);
    if (row.status !== 'ok' || row.degree_1_count < 2 || row.units_read > SIZES[0].budget)
      issues.push(`${algorithm}:${row.status}:${row.error_code}`);
  }
  if (issues.length) throw new Error(`Self-test failed: ${issues.join(', ')}`);
  console.log(JSON.stringify({self_test:'pass', algorithms:ALGORITHMS.length,
    sources:sources.size, test_grid:'10x10', test_budget:6000}));
}

function main() {
  const mode = process.argv[2];
  if (!['--self-test', '--run'].includes(mode) || process.argv.length !== 3)
    throw new Error('Use --self-test or --run');
  const Core = loadCore();
  if (mode === '--self-test') { selfTest(Core); return; }
  if (fs.existsSync(OUT)) throw new Error(`Output already exists: ${OUT}`);
  const sources = verifiedSources(Core);
  if (ALGORITHMS.length !== Object.keys(Core.GENERATORS).length ||
      ALGORITHMS.some(id => !Core.GENERATORS[id])) throw new Error('Algorithm list no longer matches HTML');
  fs.mkdirSync(OUT, {recursive:true});
  const writer = new CsvWriter(path.join(OUT, 'runs.csv'));
  const sourceManifest = {};
  try {
    for (const [sourceId, source] of sources) {
      sourceManifest[sourceId] = {file:source.file, digit_count:source.length,
        sha256:source.sha256, arithmetic_status:source.arithmetic_status};
      for (const size of SIZES) {
        for (const algorithm of ALGORITHMS) {
          for (let index = 0; index < size.windows; index++)
            writer.write(one(Core, source, sourceId, size, algorithm, index));
        }
      }
      console.log(`Finished source ${sourceId}`);
    }
    for (let seedIndex = 1; seedIndex <= 64; seedIndex++) {
      const seed = `${STUDY_ID}/pseudo-iid/${String(seedIndex).padStart(3, '0')}`;
      const digits = Core.makeIidDecimal5Digits(192000,
        new Core.Xoshiro128StarStar(seed), {raw_draws:0,rejected_draws:0});
      const control = {digits, sha256:sha256(digits), arithmetic_status:'pseudo_iid_control'};
      for (const size of SIZES) {
        if (seedIndex > size.controls) continue;
        for (const algorithm of ALGORITHMS) {
          for (let index = 0; index < size.windows; index++)
            writer.write(one(Core, control, 'control_pseudo_iid_decimal', size,
              algorithm, index, seed));
        }
      }
      console.log(`Finished control corpus ${seedIndex}/64`);
    }
  } finally { writer.close(); }
  const expected = 14 * 12 * 48 + 14 * (64 * 32 + 16 * 16);
  if (writer.rows !== expected) throw new Error(`Attempt count ${writer.rows} != ${expected}`);
  const manifest = {
    study_id:STUDY_ID,
    status:'complete',
    timestamp_utc:new Date().toISOString(),
    core_app_version:Core.APP_VERSION,
    decoder_version:Core.DECODER_VERSION,
    html_sha256:sha256(fs.readFileSync(HTML_PATH)),
    protocol_sha256:sha256(fs.readFileSync(PROTOCOL_PATH)),
    runner_sha256:sha256(fs.readFileSync(__filename)),
    node_version:process.version,
    sources:sourceManifest,
    algorithms:ALGORITHMS,
    size_design:SIZES,
    rows:writer.rows,
    statuses:writer.statuses,
    runs_csv_sha256:sha256(fs.readFileSync(path.join(OUT, 'runs.csv')))
  };
  fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n', {flag:'wx'});
  console.log(JSON.stringify({rows:manifest.rows,statuses:manifest.statuses,
    output:OUT,runs_csv_sha256:manifest.runs_csv_sha256}));
}

main();
