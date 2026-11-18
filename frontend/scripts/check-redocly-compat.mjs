// Finite @redocly/openapi-core 1.34.15 installed-source transition only.
import fs from "node:fs";
import path from "node:path";
import { createHash, randomBytes } from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const frontend = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const parent = path.join(frontend, "node_modules/@redocly/openapi-core");
const target = path.join(parent, "lib/utils.js");
const dataPath = path.join(frontend, "patches/redocly-1.34.15-minimatch11.inventory.json");
const patchPath = path.join(frontend, "patches/redocly-1.34.15-minimatch11.patch");
const fail = (message) => {
    throw new Error(`Redocly compatibility: ${message}`);
};
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const same = (a, b) =>
    a.dev === b.dev &&
    a.ino === b.ino &&
    a.size === b.size &&
    a.mode === b.mode &&
    a.mtimeMs === b.mtimeMs &&
    a.ctimeMs === b.ctimeMs;

function directories(directory) {
    const absolute = path.resolve(directory);
    let current = path.parse(absolute).root;
    for (const part of absolute.slice(current.length).split(path.sep).filter(Boolean)) {
        current = path.join(current, part);
        const info = fs.lstatSync(current);
        if (!info.isDirectory() || info.isSymbolicLink()) fail("directory alias/type");
    }
    if (fs.realpathSync(absolute) !== absolute) fail("noncanonical directory");
}

function read(file, maximum) {
    directories(path.dirname(file));
    const before = fs.lstatSync(file);
    if (
        !before.isFile() ||
        before.isSymbolicLink() ||
        before.nlink !== 1 ||
        before.size > maximum ||
        before.mode & 0o7022
    )
        fail("file identity/mode/size");
    const descriptor = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    try {
        if (!same(before, fs.fstatSync(descriptor))) fail("opened file changed");
        const bytes = fs.readFileSync(descriptor);
        if (
            bytes.length !== before.size ||
            !same(before, fs.fstatSync(descriptor)) ||
            !same(before, fs.lstatSync(file))
        )
            fail("file changed during read");
        return { bytes, info: before };
    } finally {
        fs.closeSync(descriptor);
    }
}

function payload(data) {
    directories(parent);
    const expected = new Map(data.files.map((row) => [row.path, row]));
    if (expected.size !== 687 || data.files.length !== 687) fail("inventory cardinality");
    const allowedDirectories = new Set();
    for (const name of expected.keys()) {
        if (
            name.includes("\\") ||
            name.startsWith("/") ||
            name.split("/").some((part) => !part || part === "." || part === "..") ||
            name.split("/").includes("node_modules")
        )
            fail("inventory path");
        let dir = path.posix.dirname(name);
        while (dir !== ".") {
            allowedDirectories.add(dir);
            dir = path.posix.dirname(dir);
        }
    }
    const observed = new Map();
    function walk(directory, relative = "") {
        for (const name of fs.readdirSync(directory).sort()) {
            const rel = relative ? `${relative}/${name}` : name;
            const full = path.join(directory, name);
            const info = fs.lstatSync(full);
            if (info.isSymbolicLink()) fail("payload symlink");
            if (rel === "node_modules") {
                if (!info.isDirectory()) fail("dependency subtree type");
                continue;
            }
            if (info.isDirectory()) {
                if (!allowedDirectories.has(rel)) fail("extra payload directory");
                walk(full, rel);
            } else {
                const row = expected.get(rel);
                if (!row || ![0o644, 0o755].includes(row.mode) || (info.mode & 0o7777) !== row.mode)
                    fail("payload membership/mode");
                observed.set(rel, read(full, Math.max(row.bytes, row.derived_bytes)));
            }
        }
    }
    walk(parent);
    if (observed.size !== expected.size) fail("missing payload");
    const matches = (derived) =>
        data.files.every((row) => {
            const raw = observed.get(row.path).bytes;
            return (
                raw.length === (derived ? row.derived_bytes : row.bytes) &&
                digest(raw) === (derived ? row.derived_sha256 : row.sha256)
            );
        });
    const state = matches(true)
        ? "after"
        : matches(false)
          ? "original"
          : fail("unknown or mixed payload");
    return { state, observed };
}

function ordinaryObject(value) {
    return (
        value !== null &&
        typeof value === "object" &&
        !Array.isArray(value) &&
        Object.getPrototypeOf(value) === Object.prototype
    );
}

function admitRecord(record) {
    if (!ordinaryObject(record)) fail("record must be an object");
    for (const field of [
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
        "overrides",
    ]) {
        if (Object.hasOwn(record, field) && !ordinaryObject(record[field]))
            fail(`${field} must be an object`);
    }
    for (const field of ["link", "inBundle", "hasShrinkwrap"]) {
        if (!Object.hasOwn(record, field)) continue;
        if (typeof record[field] !== "boolean") fail(`${field} must be an exact boolean`);
        if (record[field]) fail(`${field} opaque graph forbidden`);
    }
    for (const field of ["bundleDependencies", "bundledDependencies"]) {
        if (!Object.hasOwn(record, field)) continue;
        const value = record[field];
        if (
            typeof value !== "boolean" &&
            (!Array.isArray(value) || value.some((name) => typeof name !== "string" || !name))
        )
            fail(`${field} must be boolean or an array of nonempty names`);
        if (value === true || (Array.isArray(value) && value.length !== 0))
            fail(`${field} opaque graph forbidden`);
    }
    const peers = Object.hasOwn(record, "peerDependenciesMeta") ? record.peerDependenciesMeta : {};
    if (!ordinaryObject(peers)) fail("peerDependenciesMeta must be an object");
    for (const [name, metadata] of Object.entries(peers)) {
        if (!name || !ordinaryObject(metadata)) fail("peer metadata name/object");
        if (Object.keys(metadata).some((key) => key !== "optional"))
            fail("unknown peer metadata field");
        if (Object.hasOwn(metadata, "optional") && typeof metadata.optional !== "boolean")
            fail("peer optional must be an exact boolean");
    }
}

function admitSha512(value) {
    if (typeof value !== "string" || !value.startsWith("sha512-"))
        fail("integrity must use sha512 SRI");
    const encoded = value.slice(7);
    if (!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encoded))
        fail("integrity must contain valid base64");
    const bytes = Buffer.from(encoded, "base64");
    if (bytes.length !== 64) fail("integrity sha512 digest must be 64 bytes");
    if (bytes.toString("base64") !== encoded) fail("integrity must contain canonical base64");
}

function dependency(data) {
    if (process.env.NODE_PATH || process.env.NODE_OPTIONS) fail("ambient Node resolution");
    const lock = JSON.parse(read(path.join(frontend, "package-lock.json"), 16 * 1024 * 1024).bytes);
    if (!ordinaryObject(lock) || lock.lockfileVersion !== 3 || !ordinaryObject(lock.packages))
        fail("lock graph");
    const packages = lock.packages;
    for (const row of Object.values(packages)) admitRecord(row);
    const parentRecord = packages["node_modules/@redocly/openapi-core"];
    if (
        !parentRecord ||
        parentRecord.version !== "1.34.15" ||
        parentRecord.resolved !== data.url ||
        parentRecord.integrity !== data.integrity
    )
        fail("original acquisition binding");
    // Reconcile the one excluded parent dependency subtree, not arbitrary nested payloads.
    function reconcileNested(packageRoot, depth = 0) {
        if (depth > 32) fail("nested dependency depth");
        const nested = path.join(packageRoot, "node_modules");
        if (!fs.existsSync(nested)) return;
        directories(nested);
        for (const entry of fs.readdirSync(nested)) {
            if (entry === ".bin") fail("unaccounted parent dependency bin");
            if (entry.startsWith("@")) directories(path.join(nested, entry));
            const candidates = entry.startsWith("@")
                ? fs.readdirSync(path.join(nested, entry)).map((name) => `${entry}/${name}`)
                : [entry];
            for (const name of candidates) {
                const root = path.join(nested, name);
                directories(root);
                const key = path.relative(frontend, root).split(path.sep).join("/");
                const record = packages[key];
                const metadata = JSON.parse(
                    read(path.join(root, "package.json"), 1024 * 1024).bytes,
                );
                if (!record || metadata.name !== name || metadata.version !== record.version)
                    fail("nested dependency graph differs");
                admitRecord(metadata);
                if (fs.existsSync(path.join(root, "npm-shrinkwrap.json")))
                    fail("hidden nested dependency graph");
                reconcileNested(root, depth + 1);
            }
        }
    }
    reconcileNested(parent);
    const requireParent = createRequire(target);
    const entry = requireParent.resolve("minimatch");
    const candidates = [
        "node_modules/@redocly/openapi-core/node_modules/minimatch",
        "node_modules/minimatch",
    ];
    const selected = candidates.find((key) =>
        entry.startsWith(path.join(frontend, key) + path.sep),
    );
    if (!selected) fail("foreign minimatch resolution");
    const root = path.join(frontend, selected);
    directories(root);
    read(entry, 1024 * 1024);
    const metadata = JSON.parse(read(path.join(root, "package.json"), 1024 * 1024).bytes);
    const record = packages[selected];
    if (
        !record ||
        metadata.name !== "minimatch" ||
        metadata.version !== "11.0.1" ||
        record.version !== "11.0.1" ||
        (Object.hasOwn(record, "name") && record.name !== "minimatch") ||
        record.resolved !== "https://registry.npmjs.org/minimatch/-/minimatch-11.0.1.tgz"
    )
        fail("minimatch provenance/version");
    admitSha512(record.integrity);
    admitRecord(metadata);
    if (fs.existsSync(path.join(root, "npm-shrinkwrap.json"))) fail("hidden minimatch graph");
    if (typeof requireParent("minimatch").minimatch !== "function") fail("minimatch named export");
}

function main() {
    const mode = process.argv[2];
    if (process.argv.length !== 3 || !["apply", "verify"].includes(mode))
        fail("expected apply or verify");
    directories(frontend);
    if (fs.readdirSync(frontend).some((name) => name.endsWith(".redocly-tmp")))
        fail("interrupted transition residue");
    const inventoryBytes = read(dataPath, 1024 * 1024).bytes;
    if (
        digest(inventoryBytes) !==
        "097d507767c77aa0ad0a359f36415bc05407f5e7d941dd9ec81945c77c022434"
    )
        fail("fixed inventory identity");
    const data = JSON.parse(inventoryBytes);
    if (
        data.upstream_version !== "1.34.15" ||
        digest(read(patchPath, 4096).bytes) !==
            "cb808b31c5dc55edd2d86485f4298b0f2b5dcaacf2f69803c71966be1c842804"
    )
        fail("fixed patch identity");
    transition(data, mode);
}

function transition(data, mode) {
    const first = payload(data);
    dependency(data);
    if (first.state === "after") return;
    if (mode !== "apply") fail("original payload requires explicit apply");
    const original = first.observed.get("lib/utils.js");
    const needle = 'const minimatch = require("minimatch");';
    const source = original.bytes.toString("utf8");
    if (source.split(needle).length !== 2) fail("exact replacement count");
    const replacement = Buffer.from(
        source.replace(needle, 'const { minimatch } = require("minimatch");'),
    );
    const row = data.files.find((item) => item.path === "lib/utils.js");
    if (replacement.length !== row.derived_bytes || digest(replacement) !== row.derived_sha256)
        fail("derived target identity");
    const temporary = path.join(frontend, `.${randomBytes(16).toString("hex")}.redocly-tmp`);
    let owned;
    let primary;
    try {
        const fd = fs.openSync(
            temporary,
            fs.constants.O_CREAT |
                fs.constants.O_EXCL |
                fs.constants.O_WRONLY |
                fs.constants.O_NOFOLLOW,
            row.mode,
        );
        owned = fs.fstatSync(fd);
        try {
            fs.fchmodSync(fd, row.mode);
            fs.writeFileSync(fd, replacement);
            fs.fsyncSync(fd);
            owned = fs.fstatSync(fd);
        } finally {
            fs.closeSync(fd);
        }
        if (!read(temporary, replacement.length).bytes.equals(replacement)) fail("temporary write");
        const again = payload(data);
        if (
            again.state !== "original" ||
            [...first.observed].some(
                ([name, item]) => !same(item.info, again.observed.get(name).info),
            )
        )
            fail("payload changed before replacement");
        if (!same(original.info, fs.lstatSync(target))) fail("target changed before replacement");
        fs.renameSync(temporary, target);
        owned = undefined;
        if (payload(data).state !== "after") fail("post-write inventory");
        dependency(data);
    } catch (error) {
        primary = error;
        throw error;
    } finally {
        if (owned) {
            try {
                const current = fs.lstatSync(temporary);
                if (
                    current.dev !== owned.dev ||
                    current.ino !== owned.ino ||
                    !current.isFile() ||
                    current.nlink !== 1
                )
                    fail("temporary ownership changed");
                fs.unlinkSync(temporary);
            } catch (error) {
                if (primary)
                    throw new AggregateError(
                        [primary, error],
                        "Redocly transition and cleanup failed",
                    );
                throw error;
            }
        }
    }
}
// REDOCLY_FIXED_CLI_BOUNDARY
try {
    main();
} catch (error) {
    console.error(error.message);
    process.exitCode = 1;
}
