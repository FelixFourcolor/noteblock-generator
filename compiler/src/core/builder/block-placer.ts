import { Block, type BlockType } from "./block.js";
import { Cursor } from "./cursor.js";
import { Wire } from "./wire.js";

export type XYZ = [number, number, number];
export type StrCoord = `${number} ${number} ${number}`;
export type BlockMap = Record<StrCoord, BlockType>;

export class BlockPlacer {
	private readonly blocks: Map<StrCoord, BlockType> = new Map();
	protected cursor = new Cursor();

	protected exportBlocks(): BlockMap {
		return Object.fromEntries(this.blocks.entries());
	}

	protected Repeater(delay: number) {
		return Block.Repeater({ delay, direction: this.cursor.direction });
	}

	protected set([x, y, z]: XYZ, value: BlockType) {
		this.blocks.set(`${x} ${y} ${z}`, value);
	}

	protected get([x, y, z]: XYZ): BlockType | undefined {
		return this.blocks.get(`${x} ${y} ${z}`);
	}

	protected setOffset([dx, dy, dz]: XYZ, value: BlockType) {
		this.set(this.cursor.getOffset({ dx, dy, dz }), value);
	}

	protected getOffset([dx, dy, dz]: XYZ): BlockType | undefined {
		return this.get(this.cursor.getOffset({ dx, dy, dz }));
	}

	protected useWireOffset<T>(callback: (wire: Wire) => T, base?: BlockType): T {
		const setter = this.setOffset.bind(this);
		return new Wire(setter, base).build(callback);
	}

	protected withCursor<T>(cursor: Cursor, callback: (self: this) => T): T {
		const originalCursor = this.cursor;
		this.cursor = cursor;
		try {
			return callback(this);
		} finally {
			this.cursor = originalCursor;
		}
	}

	protected at<T = void>(
		coords: { x?: number; y?: number; z?: number },
		callback: (self: this) => T,
	): T {
		return this.withCursor(this.cursor.at(coords), callback);
	}

	protected offset<T = void>(
		offsets: {
			dx?: number;
			dy?: number;
			dz?: number;
			respectDirection?: boolean;
		},
		callback: (self: this) => T,
	): T {
		return this.withCursor(this.cursor.offset(offsets), callback);
	}
}
