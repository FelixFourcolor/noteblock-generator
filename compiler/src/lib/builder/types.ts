export type Size = {
	width: number;
	length: number;
	height: number;
};

export type BlockName = string;

export type BlockData = {
	name: BlockName;
	properties: Record<string, unknown>;
};

export type BlockType = BlockName | BlockData | null;

export type BlockMap = Record<string, BlockType>;

export type BuildingDTO = {
	size: Size;
	blocks: BlockMap;
};
