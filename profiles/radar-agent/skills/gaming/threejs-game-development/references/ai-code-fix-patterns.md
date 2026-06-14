# AI-Generated TypeScript Code Fix Patterns

Common structural errors found in AI-generated game codebases and their fixes.

## 1. Brace Mismatch

The most common error. AI generates methods/blocks that don't close properly.

**Pattern**: A method body has missing closing `}`, causing the compiler to interpret subsequent code as part of that method.

**Fix**: Read the file from the first error position, look for where a method should end but doesn't. Example: `toggle()` method with else block missing a closing `}` before `enable()`.

## 2. Stub Objects Instead of Real Assets

AI generates placeholder files that look real but are empty:

```json
{"type": "placeholder", "description": "GLB model placeholder", "vertices": 0, "faces": 0}
```

**Fix**: For GLB models, generate procedural geometry in code (BoxGeometry + CylinderGeometry). For fonts, use system fonts. Mark stubs in the audit.

## 3. Import Path Inconsistency

AI references files at paths that don't match the actual directory structure:

| Broken Path | Fixed Path |
|-------------|------------|
| `./levels/LevelManager` | `./managers/LevelManager` |
| `../engine/RenderEngine` | `../engine/RenderEngine3D` |
| `../physics/PhysicsEngine` | `../engine/PhysicsEngine3D` |

## 4. Missing CANNON Import

Files reference `CANNON.Body`, `CANNON.World`, etc. without importing cannon-es.

**Fix**: Add `import * as CANNON from 'cannon-es';` to files that contain `CANNON.` but no cannon-es import.

## 5. Undefined Exported Symbols

Interface/enum is referenced in index.ts or config files but never declared.

| Missing Symbol | Fix |
|----------------|-----|
| `VehicleClass` | Add `export enum VehicleClass { D, C, B, A, S, SS }` |
| `VehicleTemplate` | Add `export interface VehicleTemplate { id, name, type, description, baseConfig, variants }` |
| `VehicleData` (as type) | Rename usage to `VehicleConfig` |
| `DecalConfig.texture` | Make optional: `texture?: string` |

## 6. Dual Architecture Cleanup

When the HTML file has its own inline game engine AND there's a separate src/ directory:

### Files to Modify in dist/index.html

1. Remove CDN script tags (three.js, cannon.js) — these are now bundled
2. Remove the cannon check inline script block
3. Remove the entire `const Game = { ... }` object (can be 60KB+)
4. Remove the `window.addEventListener('load', ...)` event — it conflicts with bundle.js
5. Add `<script src="bundle.js"></script>` before `</body>`

### Wiring the Bundle to HTML

The HTML buttons use `onclick="Game.startRace()"`. The bundle needs to expose this:

```typescript
window.Game = {
    startRace: () => game.startGame(),
    showCharacterSelect: () => PlushRacingGame.selectCharacter(),
    showVehicleSelect: () => PlushRacingGame.selectCar(),
    showSettings: () => PlushRacingGame.openSettings(),
    showCredits: () => PlushRacingGame.showCredits(),
    closeMenus: () => {},
    confirmCharacter: () => {},
    confirmVehicle: () => {},
    resumeRace: () => {},
    restartRace: () => game.startGame(),
    returnToMenu: () => { ... },
};
```

Note: `PlushRacingGame` is NOT global — it's a webpack module. Use the static methods of the class (if available) or the exported instance.

## 7. Three.js Bundled != Global

When Three.js is bundled via webpack, it is NOT available as `window.THREE`. Any inline HTML code that calls `new THREE.Scene()` or `THREE.Color()` will fail with "THREE is not defined".

**Fix**: Remove ALL inline script blocks that reference THREE directly. The only script tag in the final HTML should be `<script src="bundle.js"></script>`.

## 8. HTML Element ID Mismatches

AI-generated game code may reference HTML element IDs that don't exist in the actual HTML:

- `#speed-value` — doesn't exist; use `#speed-gauge text` (SVG text element)
- `#lap-value` — doesn't exist; search for `.hud-item` containing "圈数"

**Fix**: Update DOM selectors in the updateHUD method to match actual HTML structure.

## 9. webpack Configuration Fixes

```javascript
// BROKEN: ES module syntax with type:module in package.json
export default { ... }

// FIXED: CommonJS syntax
const path = require('path');
module.exports = { ... };

// Add loaders for game assets:
{
    test: /\.(glb|gltf)$/,
    type: 'asset/resource'
}
```

## 10. Dependency Conflict Resolution

When `postprocessing` requires `three >= 0.168.0` but project uses `three@0.160.0`:

```bash
npm install --legacy-peer-deps
```

Or remove the conflicting dependency if it's unused.

## 11. Canvas Element Type Guard

When `document.getElementById('minimap')` might return a non-canvas element (e.g. a `<div>` with that ID):

```typescript
const el = document.getElementById('minimap');
const canvas = el as HTMLCanvasElement;
// WRONG: canvas.getContext('2d') throws if el is not a canvas:
// "TypeError: this.minimapCanvas.getContext is not a function"

// RIGHT: guard first:
if (!canvas || !(canvas instanceof HTMLCanvasElement)) {
    canvas = document.createElement('canvas');
    canvas.id = 'minimap-canvas';
    canvas.width = 150;
    canvas.height = 150;
    document.body.appendChild(canvas);
}
const ctx = canvas.getContext('2d');
```

Always guard with `instanceof HTMLCanvasElement` before calling `.getContext()`. The `as HTMLCanvasElement` TypeScript cast does NOT verify the runtime type — it just suppresses the type error.

## 12. Duplicate Line Artifacts from Patch Tool

When using the `patch` tool to insert code into large methods, verify no duplicate lines were created:

```typescript
// BAD — duplicate progress update (patch artifact):
this.aiProgress[i] += aiSpeed * delta / 500;
this.aiProgress[i] += aiSpeed * delta / 500; // ← redundant!
```

**Fix**: After patching a method, search for exact duplicate adjacent lines. If found, remove one.

## 14. Menu Button Stubs (console.log Only)

AI-generated games frequently create menu callbacks that only `console.log(...)` without any user-facing feedback:

```typescript
static selectCar(): void { console.log('选择车辆'); }        // broken — does nothing visible
static selectCharacter(): void { console.log('选择角色'); }   // broken
static openSettings(): void { console.log('游戏设置'); }      // broken
static showCredits(): void { console.log('游戏制作信息'); }    // broken
```

These are called from HTML `onclick="Game.showVehicleSelect()"` via `window.Game` object. **Users will report 'buttons don't work'** because console.log is invisible without DevTools open.

**Fix**: Replace stubs with `alert()` calls that describe the feature or redirect to keyboard controls:

```typescript
static selectCar(): void { 
    alert('🚗 车辆选择\n\n即将推出: 从130辆车中选择您的座驾！');
}
static openSettings(): void {
    alert('⚙️ 设置\n\n难度: D键 | 视角: C键\n喷涂: P键 | 改装: M键');
}
```

This gives immediate visual feedback and lets users know the feature exists but isn't fully implemented yet.

## 15. Empty Arrow Functions in window.Game Callbacks

Related to Pattern 14, the `window.Game` object in `main.ts` often has empty arrow function stubs:

```typescript
resumeRace: () => {},          // broken — does nothing
closeMenus: () => {},          // broken
confirmCharacter: () => {},    // broken
confirmVehicle: () => {},      // broken
```

**Fix for resumeRace**: Must hide pause menu and set gameState back to 'playing':
```typescript
resumeRace: () => {
    document.getElementById('pause-menu')!.style.display = 'none';
    const g = game as any;
    if (g && g.gameState === 'paused') g.gameState = 'playing';
}
```

**Fix for restartRace**: Call instance method on the singleton:
```typescript
restartRace: () => {
    ['pause-menu', 'results-screen'].forEach(id => 
        document.getElementById(id)!.style.display = 'none');
    const g = game as any;
    g.gameState = 'menu';
    g.startGame();  // instance method, NOT static
}
```

**Fix for returnToMenu**: Clear all overlays:
```typescript
returnToMenu: () => {
    ['results-screen', 'pause-menu', 'hud'].forEach(id => 
        document.getElementById(id)!.style.display = 'none');
    document.getElementById('menu-overlay')!.style.display = 'flex';
    const g = game as any;
    if (g) g.gameState = 'menu';
}
```

## 16. Multiple Overlays Stacking (display: flex collision)

When `finishRace()` shows the results screen without hiding the pause menu, both have `position: fixed; inset: 0; display: flex` — they stack on top of each other. The user sees both or one partially covering the other.

**Fix**: Always call `hideAllOverlays()` before showing any menu screen. This function iterates all known overlay IDs and sets `display: 'none'` on each:
```typescript
private hideAllOverlays(): void {
    ['menu-overlay', 'pause-menu', 'results-screen', 'upgrade-menu']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
}
```

Then in `finishRace()`:
```typescript
private finishRace(): void {
    this.hideAllOverlays();  // <-- MUST be first
    // ... compute results ...
    document.getElementById('results-screen')!.style.display = 'flex';
}
```


AI-generated `package.json` may reference packages that don't exist on npm:

- `"lil": "^0.6.0"` — this package does not exist (likely confused with `lil-gui`)
- `"postprocessing": "^6.34.1"` may conflict with three.js version range

**Fix**: Remove non-existent packages. Check each one against npm registry before assuming it exists.
