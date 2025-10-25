import type { SongLayout } from "#core/assembler/@";

export type Size = {
	width: number;
	length: number;
	height: number;
};

export const SLICE_SIZE = {
	length: 4,
	width: 2,
	height: 2,
} as const;

const OVERHEAD = {
	length: 1,
	width: 2,
	height: 3,
} as const;

const PADDING = {
	length: 2,
	width: 2,
	height: 0, // controlled by noteblock-generator (+1 if it's walkable)
};

export function getSize(song: SongLayout): Size {
	const { type, height, width, slices } = song;
	const length = Math.ceil(slices.length / width);

	const size = {
		height: PADDING.height + OVERHEAD.height + SLICE_SIZE.height * height,
		length: PADDING.length + OVERHEAD.length + SLICE_SIZE.length * length,
		width: PADDING.width + OVERHEAD.width + SLICE_SIZE.width * width,
	};
	if (type === "double") {
		size.width = 2 * size.width - 1;
	}

	return size;
}
