# Godot 4 reference port of gathering / inventory / journal (UNVALIDATED)

Port of `preview/gather.js`, which is the tested implementation. Data is shared:
`assets/items/items.json` (50 item definitions), `tools.json`, `nodes.json` (30 world
nodes with drop tables, tool requirements, respawn and discovery conditions),
`icons_idx.png` (12 px indexed icons), `nodes_idx.png` + `nodes_atlas.json` (node states).

Suggested nodes: `ItemDB` (autoload, loads items/tools JSON into Dictionaries; expose as
Resources later via a generated `.tres` per item if the editor workflow needs it),
`Inventory` (autoload), `ToolBelt` (autoload), `ResourceNode` (Area2D scene instanced from
nodes.json; swaps its Sprite2D region per state; `interacted` → `Gathering.attempt`),
`Journal` (autoload), `GatherUI` (CanvasLayer: pack + field guide panels). All time and
energy go through `Survival.perform(activity)` exactly once per gather.
