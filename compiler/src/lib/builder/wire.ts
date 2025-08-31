import { match } from "ts-pattern";
import { Block } from "./block.js";
import type { Coord } from "./block-placer.js";
import { Direction } from "./direction.js";
import type { BlockType } from "./types.js";

type Value = "wire" | "repeater" | null;

export class Wire {
	private readonly data: [Coord, Value][] = [];
	private readonly apply: (coord: Coord, value: BlockType) => void;

	constructor(applicator: (coord: Coord, value: BlockType) => void) {
		this.apply = applicator;
	}

	add(coord: Coord, value: Value = "wire") {
		this.data.push([coord, value]);
	}

	build<T>(callback: (wire: this) => T): T {
		try {
			return callback(this);
		} finally {
			this.buildBase();
			this.buildRedstones();
		}
	}

	private buildBase() {
		this.data.forEach(([[x, y, z]], index) => {
			let base: BlockType = Block("glass");

			const next = this.data[index + 1];
			if (next !== undefined) {
				const [[, nextY]] = next;
				if (nextY < y) {
					base = Block.Generic;
				}
			}

			this.apply([x, y - 1, z], base);
		});
	}

	private buildRedstones() {
		this.data.forEach(([coords, value], index) => {
			const inputDir = match(this.data[index - 1])
				.with(undefined, () => undefined)
				.otherwise(([prevCoords]) => this.getDirection(prevCoords, coords));

			const outputDir = match(this.data[index + 1])
				.with(undefined, () => undefined)
				.otherwise(([nextCoords]) => this.getDirection(coords, nextCoords));

			this.placeRedstone(coords, value, { inputDir, outputDir });
		});
	}

	private getDirection = (from: Coord, to: Coord) => {
		const [fromX, , fromZ] = from;
		const [toX, , toZ] = to;
		return Direction.fromCoords(toX - fromX, toZ - fromZ);
	};

	private placeRedstone = (
		coords: Coord,
		value: Value,
		{
			inputDir,
			outputDir,
		}: { inputDir: Direction | undefined; outputDir: Direction | undefined },
	) => {
		if (value === "wire") {
			const connections = [inputDir, outputDir].filter(
				(dir): dir is Direction => dir !== undefined,
			);
			this.apply(coords, Block.Redstone(...connections));
		} else if (value !== null) {
			const direction = outputDir ?? inputDir;
			if (direction === undefined) {
				throw new Error("Cannot place repeater without direction");
			}
			this.apply(coords, Block.Repeater({ direction }));
		}
	};
}
