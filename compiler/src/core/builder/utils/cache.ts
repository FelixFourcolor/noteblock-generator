import { isEqual } from "lodash";
import type { Slice } from "@/core/layout";
import type { TPosition } from "@/types/schema";
import type { Building } from "../builder";
import type { BlockMap } from "./block-placer";
import type { Cursor } from "./cursor";
import type { Size } from "./size";

type Key = {
	type: TPosition;
	height: number;
	width: number;
};

type SliceCache = {
	slice: Slice;
	cursor: Cursor;
};

export class BuilderCache {
	private key: Key | undefined;
	private slices: SliceCache[] = [];
	private blocks: BlockMap = {};

	private previousLength: number | undefined;
	private currentLength: number | undefined;
	get length() {
		return this.previousLength;
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
		const key = { type, height: size.height, width: size.width };
		if (!isEqual(this.key, key)) {
			this.key = key;
			this.slices = [];
			this.blocks = {};
			this.previousLength = undefined;
		} else {
			this.previousLength = this.currentLength;
		}
		this.currentLength = size.length;
	}

	merge(building: Building) {
		Object.assign(this.blocks, building.blocks);
		return { size: building.size, blocks: this.blocks };
	}
}
