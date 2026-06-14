# Batch Vehicle Generation: Python → TypeScript Pipeline

## Pattern

When the user asks to create many vehicle configs for a racing game:

1. Define vehicles as Python tuples (40+ fields each)
2. Generate TypeScript exports with a Python script that writes to a `.ts` file
3. Register the new file in the index (add export line)
4. Build-validate (webpack)

## Tuple structure

```
(const_id, name, mfr, country, year, price, drive, trans, engine, layout, color,
 ms, accel, braking, ts, hnd, stb, grip, steer, df, power, torque, redline, disp, weight, pw, wb, tw,
 drag, fa, lift, gears, fd, dlock, susp, sh, camber, toe, tire, tgrip, twear, fuel, cons, boost, nitro, diff,
 kit, spoiler, wheels, wcolor, wsize, tpro, aia, aid, aic, aico, aio, ulv, umoney, rel, com, eff, aest, inn, col)
```

Total ~55 fields per tuple. Unpack with position indexing in the generation loop.

## Pitfalls

### Python f-string backslash
```python
# CRASHES:
f'neonLights: {"true" if cond else "false"}'
# ^^ SyntaxError: f-string expression part cannot include a backslash

# WORKS:
neon_str = "true" if cond else "false"
neon_colors_str = '["#ff0000"]' if cond else "[]"
f'neonLights: {neon_str}, neonColors: {neon_colors_str}'
```
Rule: compute ALL conditional expressions as variables BEFORE the f-string. Never inline ternaries with quotes inside f-strings.

### Invalid Python identifier `u$`
`u$` is not a valid Python variable name. Tuples unpacking into `u$` crashes with SyntaxError. Use `umoney` or `unlockCost` instead.

### Nested f-string with dynamic HTML
When generating TypeScript template literals from Python (which is already an f-string), escape braces by doubling them: `{{` and `}}`. If you also need dynamic content inside the template literal, break it into concatenated strings rather than nested f-strings.

```python
# SAFE: concatenation instead of nested f-strings
part_name = '引擎 ENGINE'
level = 3
html_line = f'<td>{part_name}</td><td>Lv.{level}</td>'
```

### TypeScript string escaping
If the vehicle name has special characters (e.g. `'BMW M2 (G87)'`), the TypeScript string delimiter matters:
- Single-quoted: `name: 'BMW M2 (G87)'` - can't have inner single quotes or apostrophes
- Double-quoted: `name: "BMW M2 (G87)"` - can't have inner double quotes
- Backtick template: safe but verbose

Use double quotes in the TypeScript export for safety: `name: "BMW M2 (G87)"`

### Coordinate scaling for circuit control points
Real tracks are 3-20km. Multiply all coordinates by a scale factor (30-60) to get reasonable game units. A 5.8km track yields approximately 174-348 game units.

## Verification
After generating, run `npx webpack --mode production` and check for zero errors. Then count exported vehicles to confirm the expected total.
