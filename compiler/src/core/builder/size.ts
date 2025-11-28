import type { SongLayout } from "#core/layout/@";

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

const OFFSET = {
	length: 1,
	width: 2,
	height: 3,
} as const;

const PADDING = {
	length: 2,
	width: 2,
	height: 1,
};

export function getSize(song: SongLayout): Size {
	const { type, height, width, slices } = song;
	const length = Math.ceil(slices.length / width);

	const size = {
		height: PADDING.height + OFFSET.height + SLICE_SIZE.height * height,
		length: PADDING.length + OFFSET.length + SLICE_SIZE.length * length,
		width: PADDING.width + OFFSET.width + SLICE_SIZE.width * width,
	};
	if (type === "double") {
		size.width = 2 * size.width - 1;
	}

	return size;
}
