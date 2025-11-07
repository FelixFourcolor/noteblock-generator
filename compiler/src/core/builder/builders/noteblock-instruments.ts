import type { InstrumentName } from "#schema/@";
import type { BlockName } from "../block.js";

export const instrumentBase = {
	bass: "oak_log",
	didgeridoo: "pumpkpin",
	guitar: "white_wool",
	banjo: "hay_block",
	bit: "emerald_block",
	harp: "air",
	iron_xylophone: "iron_block",
	pling: "glowstone",
	cow_bell: "soul_sand",
	flute: "clay",
	bell: "gold_block",
	chime: "packed_ice",
	xylophone: "bone_block",
} as const satisfies Record<InstrumentName, BlockName>;
