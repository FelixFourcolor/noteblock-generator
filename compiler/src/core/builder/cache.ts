import { isEqual } from "lodash";
import type { Slice } from "#core/assembler/@";
import type { TPosition } from "#schema/@";
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
		if (
			this.type !== type ||
			this.size?.height !== size.height ||
			this.size?.width !== size.width
			// length change does not invalidate cache
		) {
			this.type = type;
			this.slices = [];
		}
		this.size = size;
	}
}
