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
	height: 2,
} as const;

const PADDING = 2;

export function getSize(song: SongLayout): Size {
	const { type, height, width, slices } = song;
	const length = Math.ceil(slices.length / width);

	const size = {
		height: PADDING + OVERHEAD.height + SLICE_SIZE.height * height,
		length: PADDING + OVERHEAD.length + SLICE_SIZE.length * length,
		width: PADDING + OVERHEAD.width + SLICE_SIZE.width * width,
	};
	if (type === "double") {
		size.width = 2 * size.width - 1;
	}

	return size;
}
