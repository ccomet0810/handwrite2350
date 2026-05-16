export function parseCmap(buffer) {
  const dv = new DataView(buffer);
  const numTables = readU16(dv, 4);
  let cmapOffset = 0;

  for (let i = 0; i < numTables; i += 1) {
    const offset = 12 + i * 16;
    if (tag(dv, offset) === "cmap") cmapOffset = readU32(dv, offset + 8);
  }

  if (!cmapOffset) return new Set();

  const count = readU16(dv, cmapOffset + 2);
  const subtables = [];

  for (let i = 0; i < count; i += 1) {
    subtables.push({
      platform: readU16(dv, cmapOffset + 4 + i * 8),
      encoding: readU16(dv, cmapOffset + 6 + i * 8),
      offset: readU32(dv, cmapOffset + 8 + i * 8),
    });
  }

  subtables.sort((a, b) => scoreSubtable(b) - scoreSubtable(a));

  for (const subtable of subtables) {
    const cps = new Set();
    const offset = cmapOffset + subtable.offset;
    const format = readU16(dv, offset);

    try {
      if (format === 12) parseFormat12(dv, offset, cps);
      if (format === 4) parseFormat4(dv, offset, cps);
    } catch (error) {
      console.warn("cmap parse failed", subtable, error);
    }

    if (cps.size) return cps;
  }

  return new Set();
}

function readU16(dv, offset) {
  return dv.getUint16(offset, false);
}

function readI16(dv, offset) {
  return dv.getInt16(offset, false);
}

function readU32(dv, offset) {
  return dv.getUint32(offset, false);
}

function tag(dv, offset) {
  return String.fromCharCode(dv.getUint8(offset), dv.getUint8(offset + 1), dv.getUint8(offset + 2), dv.getUint8(offset + 3));
}

function scoreSubtable(subtable) {
  if (subtable.platform === 3 && subtable.encoding === 10) return 4;
  if (subtable.platform === 0) return 3;
  if (subtable.platform === 3 && subtable.encoding === 1) return 2;
  return 1;
}

function parseFormat12(dv, offset, cps) {
  const groupCount = readU32(dv, offset + 12);
  let cursor = offset + 16;

  for (let i = 0; i < groupCount; i += 1, cursor += 12) {
    const start = readU32(dv, cursor);
    const end = readU32(dv, cursor + 4);
    for (let cp = start; cp <= end && cp < 0x110000; cp += 1) cps.add(cp);
  }
}

function parseFormat4(dv, offset, cps) {
  const length = readU16(dv, offset + 2);
  const segCount = readU16(dv, offset + 6) / 2;
  const endOffset = offset + 14;
  const startOffset = endOffset + 2 * segCount + 2;
  const deltaOffset = startOffset + 2 * segCount;
  const rangeOffset = deltaOffset + 2 * segCount;

  for (let i = 0; i < segCount; i += 1) {
    const end = readU16(dv, endOffset + i * 2);
    const start = readU16(dv, startOffset + i * 2);
    const delta = readI16(dv, deltaOffset + i * 2);
    const range = readU16(dv, rangeOffset + i * 2);

    for (let cp = start; cp <= end && cp !== 0xffff; cp += 1) {
      let gid = 0;
      if (range === 0) {
        gid = (cp + delta) & 0xffff;
      } else {
        const location = rangeOffset + i * 2 + range + 2 * (cp - start);
        if (location < offset + length) gid = (readU16(dv, location) + delta) & 0xffff;
      }
      if (gid) cps.add(cp);
    }
  }
}
