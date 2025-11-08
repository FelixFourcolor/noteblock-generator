import { forEachRight, range } from "lodash";
import type { NoteCluster, Slice, SongLayout } from "#core/assembler/@";
import type { TPosition } from "#schema/@";
import { Block } from "../block.js";
import { type BlockMap, BlockPlacer } from "../block-placer.js";
import { addBuffer } from "../buffer.js";
import { Direction } from "../direction.js";
import { getSize, type Size, SLICE_SIZE } from "../size.js";
import { instrumentBase } from "./noteblock-instruments.js";

export type Building = {
	size: Size;
	blocks: BlockMap;
};

export abstract class Builder<T extends TPosition> extends BlockPlacer {
	protected abstract buildPlayButton(index: number): void;
	protected abstract buildSlice(slice: Slice<T>): void;

	protected readonly song: SongLayout<T>;
	protected readonly size: Size;

	private stepCounter = 0;

	constructor(song: SongLayout<T>) {
		super();
		this.song = addBuffer(song);
		this.size = getSize(this.song);
	}

	build(): Building {
		this.buildSpace();
		this.buildSong();
		return { size: this.size, blocks: this.exportBlocks() };
	}

	protected get isStartOfRow() {
		const { width } = this.song;
		return this.stepCounter % width === 0;
	}

	protected get isEndOfRow() {
		const { width } = this.song;
		return this.stepCounter % width === width - 1;
	}

	protected get hasNext() {
		return this.stepCounter < this.song.slices.length - 1;
	}

	protected buildSingleSlice({ delay, levels }: Slice<"single">) {
		let newCursor = this.cursor;

		// Must build from top to bottom.
		// Because the row below calculates where to place the noteblocks
		// based on whether the space above is occupied.
		forEachRight(levels, (notes = [], level) => {
			newCursor = this.at({ y: 1 + SLICE_SIZE.height * level }, (self) => {
				self.buildClusterStructure(delay, notes);
				self.buildNotes(notes);
				if (self.isEndOfRow && self.hasNext) {
					self.buildRowBridge();
				} else {
					self.cursor.move({ dz: SLICE_SIZE.width });
				}
				return self.cursor;
			});
		});

		this.cursor = newCursor;
	}

	private buildSpace() {
		const { height, width, length } = this.size;

		const isPadding = (x: number, z: number) => {
			return [0, length - 1].includes(x) || [0, width - 1].includes(z);
		};

		const isMidpoint = (z: number) => {
			if (width % 2 === 1) {
				return z === Math.floor(width / 2);
			} else {
				const mid = width / 2;
				return z === mid - 1 || z === mid;
			}
		};

		range(0, length).forEach((x) => {
			range(0, width).forEach((z) => {
				if (isPadding(x, z)) {
					range(0, height).forEach((y) => {
						this.set([x, y, z], "air");
					});
				}
				if (isMidpoint(z)) {
					this.set([x, height - 1, z], "air");
					this.set([x, height - 2, z], "air");
					this.set([x, height - 3, z], "glass");
				} else if (x > 0) {
					this.set([x, height - 3, z], "glass");
				}
			});
		});
	}

	private buildSong() {
		let previousDelay = 1;

		this.at({ x: 3, z: 2 }, (self) => {
			let rowCounter = 0;
			for (const { delay, levels } of this.song.slices) {
				if (this.isStartOfRow) {
					self.buildPlayButton(rowCounter++);
				}
				self.buildSlice({ delay: previousDelay, levels });
				previousDelay = delay;
				this.stepCounter += 1;
			}
		});
	}

	private buildClusterStructure(delay: number, notes: NoteCluster) {
		const wireDirection = notes.length ? [Direction.fromCoords(1, 0)] : [];
		this.setOffset([0, 0, 0], Block.Generic);
		this.setOffset([0, 1, 0], this.Repeater(delay));
		this.setOffset([0, -1, 1], Block.Generic);
		this.setOffset([0, 0, 1], Block.Redstone(...wireDirection));
		this.setOffset([0, 1, 1], Block.Generic);
		this.setOffset([0, 0, 2], Block.Generic);
	}

	private getNotePlacements(): [number, number][] {
		const placements: [number, number][] = [
			[-1, 1],
			[1, 1],
			[-1, 2], // special handling required
			[1, 2], // when is end of row
			[-2, 1],
			[2, 1],
		];
		if (this.isEndOfRow && this.hasNext) {
			placements[2] = [3, 1];
			placements[3] = [5, 1];
		}

		// Priorize placements that are not blocked from above.
		// Validity is not guaranteed (unless limiting cluster size to 3).
		// We just try our best to *appear* valid.
		return placements.sort(([xA, zA], [xB, zB]) => {
			const aboveA = this.getOffset([xA, 1, zA]);
			const aboveB = this.getOffset([xB, 1, zB]);

			const occupiedA = aboveA != null && aboveA !== "air";
			const occupiedB = aboveB != null && aboveB !== "air";

			return occupiedA === occupiedB ? 0 : occupiedA ? 1 : -1;
		});
	}
	private buildNotes(notes: NoteCluster) {
		const notePlacements = this.getNotePlacements();
		notes.forEach((note, i) => {
			const [dx, dz] = notePlacements[i]!;
			this.setOffset([dx, -1, dz], instrumentBase[note.instrument]);
			this.setOffset([dx, 0, dz], Block.Note(note));
			this.setOffset([dx, 1, dz], "air");
		});
		// clear unused placements (necessary for partial updates)
		notePlacements.slice(notes.length).forEach(([dx, dz]) => {
			this.setOffset([dx, 0, dz], null);
		});

		// If x=-2 or x=2 has a noteblock,
		// x=-1 or x=1 (respectively) must be present to conduct redstone.
		if (this.getOffset([-2, 1, 1])) {
			if (!this.getOffset([-1, 0, 1])) {
				this.setOffset([-1, 0, 1], Block.Generic);
			}
		}
		if (this.getOffset([2, 1, 1])) {
			if (!this.getOffset([1, 0, 1])) {
				this.setOffset([1, 0, 1], Block.Generic);
			}
		}
	}

	private buildRowBridge() {
		const placements = [
			[0, 2],
			[1, 2],
			[2, 2],
			[3, 2],
			[4, 2],
			[4, 1],
		] as const;

		this.useWireOffset((wire) => {
			for (const [dx, dz] of placements.slice(0, -1)) {
				wire.add([dx, 1, dz]);
			}
			const [dx, dz] = placements.at(-1)!;
			wire.add([dx, 1, dz], null);
		}, Block.Generic);

		const [dx, dz] = placements.at(-1)!;
		this.cursor.move({ dx, dz });
		this.cursor.flipDirection();
	}
}
