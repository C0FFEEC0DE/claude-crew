"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { add, subtract, multiply } = require("../src/calculator");

test("adds numbers", () => {
  assert.equal(add(2, 3), 5);
});

test("subtracts numbers", () => {
  assert.equal(subtract(9, 4), 5);
});

test("multiplies numbers", () => {
  assert.equal(multiply(3, 4), 12);
});

test("multiplies by zero", () => {
  assert.equal(multiply(7, 0), 0);
});
