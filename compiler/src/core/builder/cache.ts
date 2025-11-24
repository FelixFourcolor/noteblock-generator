import { isEqual } from "lodash";
import type { Slice } from "#core/assembler/@";
import type { TPosition } from "#schema/@";
import type { BlockMap } from "./block-placer.js";
import type { Building } from "./builders/builder.js";
import type { Cursor } from "./cursor.js";
import type { Size } from "./size.js";

type SliceCache = {
	slice: Slice;
	cursor: Cursor;
};

export class BuilderCache {
	private type: TPosition | undefined;
	private size: Size | undefined;
	private slices: SliceCache[] = [];
	private blocks: BlockMap = {};

	get length() {
		return this.size?.length;
	}

	set(index: number, data: SliceCache) {
		this.slices[index] = data;
	}

	match(index: number, slice: Slice) {
		const cached = this.slices[index];
		if (!cached) {
			return undefined;
		}
		if (!isEqual(cached.slice, slice)) {
			return undefined;
		}
		return cached.cursor;
	}

	invalidate(type: TPosition, size: Size) {
		const invalidated =
			this.type !== type ||
			this.size?.height !== size.height ||
			this.size?.width !== size.width;
		if (invalidated) {
			this.slices = [];
			this.blocks = {};
		}
		this.type = type;
		this.size = size;
	}

	update(building: Building) {
		Object.assign(this.blocks, building.blocks);
		return { size: building.size, blocks: this.blocks };
	}
}
