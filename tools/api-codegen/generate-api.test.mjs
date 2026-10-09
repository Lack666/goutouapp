import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { generate, assertCurrent, input, output } from "./generate-api.mjs";
const committed = await readFile(output, "utf8");
test("same authoritative input generates byte-identical client twice", async () => {
  const bytes = await readFile(input);
  const first = await generate(bytes);
  assert.equal(first, await generate(bytes));
  assertCurrent(first, committed);
});
test("input drift fails the same check without modifying the authority file", async () => {
  const schema = JSON.parse(await readFile(input, "utf8"));
  schema.components.schemas.PersonResponse.properties.display_name.type =
    "integer";
  const changed = await generate(Buffer.from(JSON.stringify(schema)));
  assert.throws(() => assertCurrent(changed, committed), /client drift/);
});
test("manual generated output changes fail check", () => {
  assert.throws(
    () => assertCurrent(committed, `${committed}\n`),
    /client drift/,
  );
});
