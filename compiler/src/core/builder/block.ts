import type { NoteBlock } from "#core/resolver/@";
import type { Delay } from "#schema/@";
import { Direction } from "./direction.js";
import type { BlockType } from "./types.js";

export function Block(
	name: string,
	properties: Record<string, unknown> | undefined = undefined,
): BlockType {
	if (!properties) {
		return name;
	}
	return { name, properties };
}

export namespace Block {
	// chosen by the user when generating
	export const Generic = null satisfies BlockType;

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
