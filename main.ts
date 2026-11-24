const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const entryName = "entry.png";
const pngLimit = 1024 * 1024;
const canvasSize = 1024;

function renderEdition() {
    const localPython = path.resolve(__dirname, "../build-venv/bin/python");
    const interpreter = fs.existsSync(localPython) ? localPython : "python3";
    const script = path.join(__dirname, "build_image.py");
    try {
        return execFileSync(interpreter, ["-B", script, "--stdout"], {
            stdio: ["ignore", "pipe", "inherit"],
            maxBuffer: 2 * pngLimit,
        });
    } catch (error) {
        if (error.code === "ENOENT" || error.status === 69) {
            return fs.readFileSync(path.join(__dirname, entryName));
        }
        if (error.code || (error.status == null && !error.signal)) {
            throw error;
        }
        throw new Error(`Pillow render failed (${error.signal ?? error.status})`);
    }
}

function isEntryPng(bytes) {
    return bytes.length >= 33
        && bytes.length <= pngLimit
        && bytes.toString("hex", 0, 8) === "89504e470d0a1a0a"
        && bytes.readUInt32BE(16) === canvasSize
        && bytes.readUInt32BE(20) === canvasSize;
}

const destination = path.resolve(process.env.MAKEFUN_OUTPUT_DIR ?? "/output");
const png = renderEdition();
if (!isEntryPng(png)) {
    throw new Error("Expected an entry PNG of 1024 × 1024 pixels and at most 1 MiB");
}

fs.mkdirSync(destination, { recursive: true });
fs.writeFileSync(path.join(destination, entryName), png);
