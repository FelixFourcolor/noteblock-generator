import { match } from "ts-pattern";
import { Block } from "./block.js";
import type { Coord } from "./block-placer.js";
import { Direction } from "./direction.js";
import type { BlockType } from "./types.js";

type Value = "wire" | "repeater" | null;

export class Wire {
	private readonly data: [Coord, Value][] = [];

	constructor(
		private apply: (coord: Coord, value: BlockType) => void,
		private base: BlockType = Block("glass"),
	) {}

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
			let base = this.base;

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
		let wireLength = 0;

		this.data.forEach(([coords, value], index) => {
			const inDir = match(this.data[index - 1])
				.with(undefined, () => undefined)
				.otherwise(([prevCoords]) => this.getDirection(prevCoords, coords));

			const outDir = match(this.data[index + 1])
				.with(undefined, () => undefined)
				.otherwise(([nextCoords]) => this.getDirection(coords, nextCoords));

			if (value !== "wire") {
				wireLength = 0;
			} else if (++wireLength >= 15) {
				value = "repeater";
				wireLength = 0;
			}

			this.placeRedstone(coords, value, [inDir, outDir]);
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
		[inDir, outDir]: [Direction | undefined, Direction | undefined],
	) => {
		if (value === "wire") {
			const connections = [inDir, outDir].filter(
				(dir): dir is Direction => dir !== undefined,
			);
			this.apply(coords, Block.Redstone(...connections));
		} else if (value !== null) {
			const direction = outDir ?? inDir;
			if (direction === undefined) {
				throw new Error("Cannot place repeater without direction");
			}
			this.apply(coords, Block.Repeater({ direction }));
		}
	};
}
