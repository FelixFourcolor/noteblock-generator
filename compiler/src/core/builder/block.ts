import type { NoteBlock } from "#core/resolver/@";
import type { Delay } from "#schema/@";
import { Direction } from "./direction.js";

export type BlockName = string;
export type BlockType = BlockName | null | 0;

export function Block(
	name: BlockName,
	properties: Record<string, string | number>,
): BlockName {
	const strProperties = Object.entries(properties)
		.map(([key, value]) => `${key}=${value}`)
		.join(",");
	return `${name}[${strProperties}]`;
}

export namespace Block {
	// chosen by the user when generating
	export const Generic = 0 satisfies BlockType;

	export function Note(props: NoteBlock) {
		return Block("note_block", props);
	}

	export function Repeater(props: { delay?: Delay; direction: Direction }) {
		const { delay = 1, direction } = props;
		const facing = Direction.name(
			// Minecraft's own bug causes repeater direction to be reverted
			Direction.revert(direction),
		);
		return Block("repeater", { delay, facing });
	}

	export function Redstone(...sides: Direction[]) {
		if (!sides.length) {
			sides = Direction.ALL;
		}
		if (sides.length === 1) {
			const side = sides[0]!;
			sides = [side, Direction.revert(side)];
		}
		const props = Object.fromEntries(
			sides.map(Direction.name).map((name) => [name, "side"] as const),
		);
		return Block("redstone_wire", props);
	}

	export const Button = Block("oak_button", {
		face: "floor",
		facing: Direction.name(Direction.west),
	});
}
