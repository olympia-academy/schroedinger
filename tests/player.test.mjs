import test from "node:test";
import assert from "node:assert/strict";
import { advanceFrame, PlaybackClock, colorValue, axisTicks } from "../src/schroedinger/player.mjs";

test("elapsed clock retains fractional time and clamps at last saved frame", () => {
  const next = advanceFrame(0, 10000, 10600, 4, 10);
  assert.deepEqual(next, {index: 2, updated: 10500, playing: true});
  assert.equal(advanceFrame(next.index, next.updated, 10760, 4, 10).index, 3);
  assert.equal(advanceFrame(3, 10750, 100000, 4, 10).index, 9);
  assert.equal(advanceFrame(3, 10750, 100000, 4, 10).playing, false);
  assert.equal(advanceFrame(0, 10000, 9000, 4, 10).index, 0);
});

test("play resets from end, pauses immediately and resumes without jumping", () => {
  const clock = new PlaybackClock(100, 12);
  clock.play(1000);
  assert.equal(clock.frame, 0);
  assert.equal(clock.tick(1500), 6);
  clock.pause();
  assert.equal(clock.tick(100000), 6);
  clock.play(100000);
  assert.equal(clock.tick(100100), 7);
});

test("seek pauses and clamps; restart returns immediately to first frame", () => {
  const clock = new PlaybackClock(10);
  clock.play(0); clock.seek(3);
  assert.equal(clock.playing, false);
  assert.equal(clock.tick(1000), 3);
  clock.seek(100); assert.equal(clock.frame, 9);
  clock.seek(-5); assert.equal(clock.frame, 0);
  clock.restart(1000);
  assert.equal(clock.playing, true);
  assert.equal(clock.frame, 0);
  assert.equal(clock.tick(1250), 3);
});

test("changing rate preserves frame and stops automatically at end", () => {
  const clock = new PlaybackClock(10, 4);
  clock.restart(0); clock.tick(500);
  clock.setRate(2, 500);
  assert.equal(clock.frame, 2);
  assert.equal(clock.tick(1000), 3);
  clock.tick(10000);
  assert.equal(clock.frame, 9);
  assert.equal(clock.playing, false);
  clock.play(10000);
  assert.equal(clock.frame, 0);
});

test("invalid rates and empty playback are rejected", () => {
  for (const fps of [0, -1, NaN, Infinity]) {
    assert.throws(() => new PlaybackClock(10, fps));
    assert.throws(() => advanceFrame(0, 0, 1000, fps, 10));
  }
  assert.throws(() => new PlaybackClock(0));
});

test("colorbar inverts gamma and axis ticks keep physical values", () => {
  assert.equal(colorValue(0.5, 8, 0.5), 2);
  assert.equal(colorValue(0.5, 8, 1), 4);
  assert.deepEqual(axisTicks(-15.039, 24.961), [-10, 0, 10, 20]);
  assert.deepEqual(axisTicks(0, 0.02), [0, 0.005, 0.01, 0.015, 0.02]);
});
