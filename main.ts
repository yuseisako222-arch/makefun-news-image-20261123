const { spawnSync } = require('node:child_process');
const { existsSync, mkdirSync, readFileSync, writeFileSync } = require('node:fs');
const { join, resolve } = require('node:path');

const outputDir = resolve(process.env.MAKEFUN_OUTPUT_DIR ?? '/output');
const renderer = join(__dirname, 'build_image.py');
const venvPython = resolve(__dirname, '../build-venv/bin/python');
const python = existsSync(venvPython) ? venvPython : 'python3';

const render = spawnSync(python, ['-B', renderer, '--stdout'], {
    stdio: ['ignore', 'pipe', 'inherit'],
    maxBuffer: 2 * 1024 * 1024,
});

let image;
if (render.error?.code === 'ENOENT' || render.status === 69) {
    // The contest runner provides Node, but may lack Pillow or the edition's fonts.
    image = readFileSync(join(__dirname, 'entry.png'));
} else if (render.error) {
    throw render.error;
} else if (render.status !== 0) {
    throw new Error(`Pillow render failed (${render.signal ?? render.status})`);
} else {
    image = render.stdout;
}

const pngSignature = Buffer.from('89504e470d0a1a0a', 'hex');
if (image.length < 33 || image.length > 1024 * 1024 ||
    !image.subarray(0, 8).equals(pngSignature) ||
    image.readUInt32BE(16) !== 1024 || image.readUInt32BE(20) !== 1024) {
    throw new Error('Expected an entry PNG of 1024 × 1024 pixels and at most 1 MiB');
}

mkdirSync(outputDir, { recursive: true });
writeFileSync(join(outputDir, 'entry.png'), image);
