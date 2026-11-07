import fs from "node:fs/promises";
import { constants } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SOURCES = [
    "00_core/color.json",
    "00_core/layout.json",
    "00_core/motion.json",
    "00_core/radius.json",
    "00_core/shadow.json",
    "00_core/spacing.json",
    "00_core/typography.json",
    "10_semantic/color.json",
    "20_product/color.json",
    "30_platform/ios.json",
    "30_platform/web.json",
];
const UNSAFE = new Set(["__proto__", "prototype", "constructor"]);
const own = (object, key) => Object.hasOwn(object, key);
const fail = (context) => {
    throw new Error(`Invalid token source: ${context}`);
};

// JSON.parse owns JSON syntax; this bounded walk detects decoded duplicate keys
// before its last-member-wins result can enter the token tree.
function decode(text, label) {
    const result = JSON.parse(text);
    let cursor = 0;
    const space = () => {
        while (/[\x20\t\r\n]/.test(text[cursor] ?? "x")) cursor++;
    };
    function string() {
        const start = cursor++;
        while (text[cursor] !== '"') {
            if (text[cursor] === "\\") cursor++;
            cursor++;
        }
        cursor++;
        return JSON.parse(text.slice(start, cursor));
    }
    function value(depth) {
        if (depth > 64) fail(`${label}: depth`);
        space();
        if (text[cursor] === '"') {
            string();
            return;
        }
        if (text[cursor] === "{") {
            cursor++;
            space();
            const keys = new Set();
            if (text[cursor] !== "}") {
                for (;;) {
                    space();
                    const key = string();
                    if (keys.has(key) || UNSAFE.has(key)) fail(`${label}: duplicate or unsafe key`);
                    keys.add(key);
                    space();
                    cursor++;
                    value(depth + 1);
                    space();
                    if (text[cursor] !== ",") break;
                    cursor++;
                }
            }
            cursor++;
        } else if (text[cursor] === "[") {
            cursor++;
            space();
            if (text[cursor] !== "]") {
                for (;;) {
                    value(depth + 1);
                    space();
                    if (text[cursor] !== ",") break;
                    cursor++;
                }
            }
            cursor++;
        } else {
            while (cursor < text.length && !/[\x20\t\r\n,}\]]/.test(text[cursor])) cursor++;
        }
    }
    value(0);
    space();
    if (cursor !== text.length) fail(`${label}: incomplete JSON`);
    return result;
}

function validateShape(node, label) {
    if (node === null || typeof node !== "object" || Array.isArray(node)) fail(label);
    if (own(node, "value") || own(node, "$value")) {
        if (own(node, "value") && own(node, "$value")) fail(`${label}: ambiguous value`);
        if (
            Object.keys(node).some(
                (key) => !["value", "$value", "$type", "$description"].includes(key),
            )
        )
            fail(`${label}: metadata`);
        if (own(node, "$description") && typeof node.$description !== "string")
            fail(`${label}: description`);
        const value = own(node, "$value") ? node.$value : node.value;
        if (node.$type === "number") {
            if (typeof value !== "number" || !Number.isFinite(value)) fail(`${label}: number`);
        } else if (node.$type === "typography") {
            if (value === null || typeof value !== "object" || Array.isArray(value))
                fail(`${label}: typography`);
            const required = ["fontFamily", "fontWeight", "lineHeight"];
            if (
                required.some((key) => !own(value, key)) ||
                Object.keys(value).some(
                    (key) =>
                        ![...required, "fontSize"].includes(key) || typeof value[key] !== "string",
                )
            )
                fail(`${label}: typography fields`);
        } else if (
            !["color", "dimension", "duration", "string"].includes(node.$type) ||
            typeof value !== "string"
        ) {
            fail(`${label}: type`);
        }
        return;
    }
    for (const [key, child] of Object.entries(node)) {
        if (key.startsWith("$")) fail(`${label}: group metadata`);
        validateShape(child, `${label}.${key}`);
    }
}

export async function loadTokenTree() {
    const root = path.join(repoRoot, "tokens");
    const inventory = [];
    async function enumerate(directory, relative = "") {
        const stat = await fs.lstat(directory);
        if (!stat.isDirectory() || stat.isSymbolicLink()) fail("non-directory source root");
        for (const name of await fs.readdir(directory)) {
            const member = relative ? `${relative}/${name}` : name;
            const file = path.join(directory, name);
            const entry = await fs.lstat(file);
            if (entry.isSymbolicLink()) fail(`${member}: symlink`);
            if (entry.isDirectory()) {
                if (!["00_core", "10_semantic", "20_product", "30_platform"].includes(member))
                    fail(`${member}: directory membership`);
                await enumerate(file, member);
            } else if (entry.isFile()) inventory.push(member);
            else fail(`${member}: nonregular`);
        }
    }
    await enumerate(root);
    if (JSON.stringify(inventory.sort()) !== JSON.stringify(SOURCES)) fail("source membership");
    const tree = Object.create(null);
    const snapshots = [];
    const identities = new Set();
    let total = 0;
    for (const source of SOURCES) {
        const file = path.join(root, source);
        const handle = await fs.open(file, constants.O_RDONLY | constants.O_NOFOLLOW);
        let bytes;
        try {
            const before = await handle.stat();
            if (!before.isFile() || before.size > 1024 * 1024) fail(`${source}: size/type`);
            const identity = `${before.dev}:${before.ino}`;
            if (identities.has(identity)) fail(`${source}: aliased file identity`);
            identities.add(identity);
            bytes = await handle.readFile();
            const after = await handle.stat();
            if (
                before.size !== after.size ||
                before.mtimeMs !== after.mtimeMs ||
                bytes.length !== before.size
            )
                fail(`${source}: changed during read`);
        } finally {
            await handle.close();
        }
        total += bytes.length;
        if (total > 8 * 1024 * 1024) fail("aggregate bytes");
        const parsed = decode(new TextDecoder("utf-8", { fatal: true }).decode(bytes), source);
        validateShape(parsed, source);
        for (const [key, child] of Object.entries(parsed)) {
            if (own(tree, key)) {
                if (key !== "platform") fail(`${source}: colliding group`);
                for (const [platform, tokens] of Object.entries(child)) {
                    if (!["ios", "web"].includes(platform) || own(tree.platform, platform))
                        fail(`${source}: colliding platform`);
                    tree.platform[platform] = tokens;
                }
            } else tree[key] = child;
        }
        snapshots.push([file, bytes]);
    }
    if (JSON.stringify(Object.keys(tree.platform).sort()) !== '["ios","web"]')
        fail("platform membership");
    // Detect observed source drift; this is not a filesystem transaction guarantee.
    inventory.length = 0;
    await enumerate(root);
    if (JSON.stringify(inventory.sort()) !== JSON.stringify(SOURCES))
        fail("source membership changed");
    for (const [file, bytes] of snapshots) {
        if (!(await fs.readFile(file)).equals(bytes)) fail("source bytes changed");
    }
    return tree;
}
