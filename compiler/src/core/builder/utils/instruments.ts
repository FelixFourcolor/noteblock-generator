import type { InstrumentName } from "@/types/schema";
import type { BlockName } from "./block";

export const baseBlock = {
	bass: "oak_log",
	didgeridoo: "pumpkin",
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
