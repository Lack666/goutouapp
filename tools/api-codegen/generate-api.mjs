import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { pathToFileURL } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";
import ts from "typescript";
import prettier from "prettier";

export const input = new URL(
  "../../docs/contracts/openapi.json",
  import.meta.url,
);
export const output = new URL(
  "../../apps/mobile/src/api/generated/client.ts",
  import.meta.url,
);
export async function generate(bytes) {
  const schema = JSON.parse(bytes.toString("utf8"));
  const ast = await openapiTS(schema, {
    transform(node) {
      if (node.format === "uuid" || node.format === "uuid4") {
        return ts.factory.createTypeReferenceNode("UUID");
      }
    },
  });
  const inventory = Object.entries(schema.paths).flatMap(([path, ops]) =>
    Object.entries(ops)
      .filter(([method]) =>
        ["get", "post", "put", "patch", "delete", "head", "options"].includes(
          method,
        ),
      )
      .map(([method, op]) => ({
        method,
        path,
        operationId: op.operationId,
        bearer: !!op.security,
      })),
  );
  const uuidType = "`${string}-${string}-${string}-${string}-${string}`";
  const source = `// Generated from docs/contracts/openapi.json. DO NOT EDIT.
// Input SHA256: ${createHash("sha256").update(bytes).digest("hex")}
import createClient, { type ClientOptions } from 'openapi-fetch';
export type UUID = ${uuidType};
${astToString(ast)}
export const createApiClient = (options: ClientOptions) => createClient<paths>(options);
export const operationInventory = ${JSON.stringify(inventory, null, 2)} as const;
`;
  const config = JSON.parse(
    await readFile(
      new URL("../../apps/mobile/.prettierrc.json", import.meta.url),
      "utf8",
    ),
  );
  return prettier.format(source, {
    ...config,
    parser: "typescript",
    endOfLine: "lf",
  });
}
export function assertCurrent(expected, actual) {
  if (expected !== actual)
    throw new Error("Generated API client drift. Run pnpm api:generate.");
}
if (
  process.argv[1] &&
  pathToFileURL(process.argv[1]).href === import.meta.url
) {
  const generated = await generate(await readFile(input));
  if (process.argv.includes("--check")) {
    assertCurrent(generated, await readFile(output, "utf8"));
    process.stdout.write(
      "PASS: deterministic generated client (36 operations)\n",
    );
  } else {
    await mkdir(
      new URL("../../apps/mobile/src/api/generated/", import.meta.url),
      { recursive: true },
    );
    await writeFile(output, generated);
  }
}
