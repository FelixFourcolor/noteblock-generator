import type { Slice, SongLayout } from "#core/assembler/@";
import type { NoteBlock } from "#core/resolver/@";
import type { TPosition } from "#types/schema/@";
import { Block } from "../block.js";
import { BlockPlacer } from "../block-placer.js";
import { addBuffer } from "../buffer.js";
import { getSize, SLICE_SIZE } from "../size.js";
import type { BuildingDTO, Size } from "../types.js";

export abstract class Builder<T extends TPosition> extends BlockPlacer {
	protected abstract buildPlayButton(): void;
	protected abstract buildSlice(slice: Slice<T>): void;

	protected readonly song: SongLayout<T>;
	protected readonly size: Size;

	private stepCounter = 0;

	constructor(song: SongLayout<T>) {
		super();
		this.song = addBuffer(song);
		this.size = getSize(this.song);
	}

	build(): BuildingDTO {
		this.buildWalkSpace();
		this.buildGrid();

		return { size: this.size, blocks: this.exportBlocks() };
	}

	protected get isStartOfRow() {
		const { width } = this.song;
		return this.stepCounter % width === 0;
	}

	protected get hasPrevious() {
		return this.stepCounter > 0;
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

		levels.forEach((notes, level) => {
			newCursor = this.at({ y: 1 + SLICE_SIZE.height * level }, (self) => {
				self.buildClusterStructure(delay);
				if (notes) {
					self.buildNotes(notes);
				}
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

	private buildWalkSpace() {
		const { length, width, height } = this.size;
		for (let x = 0; x < length; ++x) {
			for (let z = 0; z < width; ++z) {
				this.set([x, height - 1, z], Block("air"));
				this.set([x, height - 2, z], Block("air"));
				this.set([x, height - 3, z], Block("glass"));
			}
		}
	}

	private buildGrid() {
		let previousDelay = 1;

		this.at({ x: 3, z: 2 }, (self) => {
			for (const { delay, levels } of this.song.slices) {
				if (this.isStartOfRow) {
					self.buildPlayButton();
				}
				self.buildSlice({ delay: previousDelay, levels });
				previousDelay = delay;
				this.stepCounter += 1;
			}
		});
	}

	private buildClusterStructure(delay: number) {
		this.setOffset([0, 0, 0], Block.Generic);
		this.setOffset([0, 1, 0], this.Repeater(delay));
		this.setOffset([0, -1, 1], Block.Generic);
		this.setOffset([0, 0, 1], Block.Redstone());
		this.setOffset([0, 1, 1], Block.Generic);
		this.setOffset([0, 0, 2], Block.Generic);
	}

	private buildNotes(notes: NoteBlock[]) {
		const notePlacements: [number, number][] = [
			[1, 1],
			[-1, 1],
			[2, 1],
			[-2, 1],
		];
		if (this.isEndOfRow && this.hasNext) {
			notePlacements.push([3, 1], [5, 1]);
		} else {
			notePlacements.push([1, 2], [-1, 2]);
		}

		notes.forEach((note, i) => {
			const [dx, dz] = notePlacements[i]!;
			this.setOffset([dx, -1, dz], Block("air"));
			this.setOffset([dx, 0, dz], Block.Note(note));
			this.setOffset([dx, 1, dz], Block("air"));
		});
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
		});

		const [dx, dz] = placements.at(-1)!;
		this.cursor.move({ dx, dz });
		this.cursor.flipDirection();
	}
}
