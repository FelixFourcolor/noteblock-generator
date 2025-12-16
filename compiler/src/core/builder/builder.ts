import { forEachRight } from "lodash";
import type { NoteCluster, Slice, SongLayout } from "@/core/layout";
import type { TPosition } from "@/types/schema";
import { Block } from "./utils/block";
import { type BlockMap, BlockPlacer } from "./utils/block-placer";
import { addBuffer } from "./utils/buffer";
import type { BuilderCache } from "./utils/cache";
import type { ReadonlyCursor } from "./utils/cursor";
import { Direction } from "./utils/direction";
import { baseBlock } from "./utils/instruments";
import { getSize, type Size, SLICE_SIZE } from "./utils/size";

export type Building = {
	size: Size;
	blocks: BlockMap;
};

export abstract class Builder<T extends TPosition> extends BlockPlacer {
	protected abstract buildPlayButton(): void;
	protected abstract buildSlice(slice: Slice<T>): void;

	protected readonly song: SongLayout<T>;
	protected readonly size: Size;
	protected get rowCounter() {
		return Math.floor(this.stepCounter / this.song.width);
	}

	private stepCounter = 0;

	constructor(
		song: SongLayout<T>,
		private cache?: BuilderCache,
	) {
		super();
		this.song = addBuffer(song);
		this.size = getSize(this.song);
		cache?.invalidate(song.type, this.size);
	}

	build(): Building {
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

	private buildSong() {
		let previousDelay = 1;
		let lastCachedCursor: ReadonlyCursor | undefined;

		this.at({ x: 3, z: 2 }, (self) => {
			this.song.slices.forEach(({ delay, levels }, index) => {
				this.stepCounter = index;
				const slice = { delay: previousDelay, levels };
				previousDelay = delay;

				const cachedCursor = this.cache?.match(index, slice);
				if (cachedCursor) {
					// cache hit
					lastCachedCursor = cachedCursor;
					return;
				}
				if (lastCachedCursor) {
					// cache miss, update cursor to last time cache hit
					this.cursor = lastCachedCursor.clone();
					lastCachedCursor = undefined;
				}

				if (this.isStartOfRow) {
					self.buildPlayButton();
				}
				self.buildSlice(slice);

				if (this.cache) {
					this.cache.set(index, { slice, cursor: self.cursor.clone() });
				}
			});
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
		const isTurning = this.isEndOfRow && this.hasNext;
		// biome-ignore format: .
		const placements: [number, number][] = [
			    [-1, 1],
				[1, 1],
				[-2, 1],
				[2, 1],
   !isTurning ? [-1, 2] : [3, 1],
   !isTurning ? [1, 2]  : [5, 1],
		];

		// With instrument base blocks, the space above may be occupied.
		// Prioritize unoccupied slots.
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
			this.setOffset([dx, -1, dz], baseBlock[note.instrument]);
			this.setOffset([dx, 0, dz], Block.Note(note));
			this.setOffset([dx, 1, dz], "air");
		});

		if (this.cache) {
			// clear unused placements for partial update
			notePlacements.slice(notes.length).forEach(([dx, dz]) => {
				this.setOffset([dx, 0, dz], null);
			});
		}

		// If x = +/-2 has a noteblock,
		// there must be something at x = +/-1 to conduct redstone.
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
