import type { NoteBlock } from "#core/resolver/@";
import type { Delay } from "#schema/@";
import { Direction } from "./direction.js";

export type BlockName = string;
export type BlockType = BlockName | null | 0;

export function Block(
	name: BlockName,
	properties: Record<string, string | number | undefined>,
): BlockName {
	const strProperties = Object.entries(properties)
		.filter(([_, value]) => value !== undefined)
		.map(([key, value]) => `${key}=${value}`)
		.join(",");
	return strProperties ? `${name}[${strProperties}]` : name;
}

export namespace Block {
	// chosen by the user when generating
	export const Generic = 0 satisfies BlockType;

	export function Note({ note, instrument }: NoteBlock) {
		return Block("note_block", {
			// omit default values to optimize output size
			note: note !== 0 ? note : undefined,
			instrument: instrument !== "harp" ? instrument : undefined,
		});
	}

	export function Repeater(props: { delay?: Delay; direction: Direction }) {
		const { delay, direction } = props;
		return Block("repeater", {
			// omit default value to optimize output size
			delay: delay !== 1 ? delay : undefined,
			// Minecraft's own bug causes repeater direction to be reverted
			facing: Direction.name(Direction.revert(direction)),
		});
	}

	export function Redstone(...sides: Direction[]) {
		if (sides.length === 1) {
			const side = sides[0]!;
			sides = [side, Direction.revert(side)];
		}
		const props = Object.fromEntries(
			sides.map(Direction.name).map((name) => [name, "side"]),
		);
		return Block("redstone_wire", props);
	}

	export const Button = Block("oak_button", {
		face: "floor",
		facing: Direction.name(Direction.fromCoords(1, 0)),
	});
}
