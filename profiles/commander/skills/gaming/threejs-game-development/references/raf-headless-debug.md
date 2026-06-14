# RAF Startup in Headless/CI Browsers

## Problem
`requestAnimationFrame` callbacks never fire after `gameLoop()` is called, even though `gameState` is 'playing' and no JS errors occur. Speed stays at 0; minimap never updates.

## Root Cause
Two distinct failure modes:

### Mode 1: Direct `gameLoop()` call without RAF wrapper
```typescript
// BROKEN — RAF never starts in some browser contexts
this.gameLoop();
```
Some browser contexts (headless mode, fresh page load without user interaction) do not begin the RAF cycle when the first call is direct rather than via `requestAnimationFrame`.

**Fix:**
```typescript
// FIXED — always wrap the first call in RAF
requestAnimationFrame(() => this.gameLoop());
```

### Mode 2: Exception before RAF call
If `initFullScene()` (or equivalent setup function) throws an exception before reaching the `requestAnimationFrame` call, the game loop never starts. Example: `initMinimap()` calls `getContext('2d')` on a non-`<canvas>` element obtained via `document.getElementById('minimap')`, which crashes.

**Fix:** Guard the setup code with try/catch and verify element types:
```typescript
const el = document.getElementById('minimap');
if (!el || !(el instanceof HTMLCanvasElement)) {
    // Create a new canvas element instead
}
```

## Detection
1. Run `window.__rafCount = 0; window.requestAnimationFrame = function(cb) { __rafCount++; return originalRAF.call(window, cb); };`
2. After 500ms, check `window.__rafCount`
3. If 0, the RAF chain was never initiated

## Verification Fix Worked
1. Manually call `window.game.gameLoop()` once (this will trigger the RAF chain if gameState is correct)
2. After 500ms, speed should increase from 0
3. Subsequent page loads should work automatically
