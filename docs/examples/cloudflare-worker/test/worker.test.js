import assert from "node:assert/strict";
import test from "node:test";
import worker from "../src/index.js";

test("a request without a name gets a friendly default", async () => {
  const response = await worker.fetch(new Request("https://example.test/hello"));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { message: "Hello, WORLD!" });
});

test("a supplied name still works", async () => {
  const response = await worker.fetch(new Request("https://example.test/hello?name=Ada"));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { message: "Hello, ADA!" });
});

test("unmatched paths stay not found", async () => {
  const response = await worker.fetch(new Request("https://example.test/missing"));
  assert.equal(response.status, 404);
});
