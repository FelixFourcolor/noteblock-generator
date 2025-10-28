import { match, P } from "ts-pattern";
import { Block, type BlockType } from "./block.js";
import type { XYZ } from "./block-placer.js";
import { Direction } from "./direction.js";

type Value = "wire" | "repeater" | null;

export class Wire {
	private readonly data: [XYZ, Value][] = [];

	constructor(
		private apply: (coord: XYZ, value: BlockType) => void,
		private base: BlockType = "glass",
	) {}

	add(coord: XYZ, value: Value = "wire") {
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
		this.data.forEach(([[x, y, z], value], index) => {
			if (!value) {
				return;
			}

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
			const prev = this.data[index - 1];
			const next = this.data[index + 1];

			const inDir = match(prev)
				.with(undefined, () => undefined)
				.otherwise(([prevCoords]) => this.getDirection(prevCoords, coords));

			const outDir = match(next)
				.with(undefined, () => undefined)
				.otherwise(([nextCoords]) => this.getDirection(coords, nextCoords));

			wireLength = value === "wire" ? wireLength + 1 : 0;

			if (wireLength >= 15) {
				match(next)
					.with([[P._, coords[1] - 1, P._], P._], ([[nextX, _, nextZ]]) => {
						value = "repeater";
						wireLength = 0;
						this.apply([nextX, coords[1], nextZ], Block.Generic);
					})
					.otherwise(() => {
						if (wireLength > 15) {
							value = "repeater";
							wireLength = 0;
						}
					});
			}

			this.placeRedstone(coords, value, [inDir, outDir]);
		});
	}

	private getDirection = (from: XYZ, to: XYZ) => {
		const [fromX, , fromZ] = from;
		const [toX, , toZ] = to;
		return Direction.fromCoords(toX - fromX, toZ - fromZ);
	};

	private placeRedstone = (
		coords: XYZ,
		value: Value,
		[inDir, outDir]: [Direction | undefined, Direction | undefined],
	) => {
		if (value === "wire") {
			const connections = [inDir, outDir].filter((dir) => dir !== undefined);
			this.apply(coords, Block.Redstone(...new Set(connections)));
		} else if (value !== null) {
			const direction = outDir ?? inDir;
			if (direction === undefined) {
				throw new Error("Cannot place repeater without direction");
			}
			this.apply(coords, Block.Repeater({ direction }));
		}
	};
}
