import { times } from "lodash";

import type { SongLayout } from "#core/layout/@";

export function addBuffer<S extends SongLayout>(song: S): S {
	const { width, height, slices } = song;

	const bufferSlice = {
		delay: 1,
		levels: times(height, () => undefined),
	};

	const preBufferLen = calculateInitBuffer(song);
	const preBufferSlices = times(preBufferLen, () => bufferSlice);

	const postBufferLen = roundToMultiple(slices.length, width) - slices.length;
	const postBufferSlices = times(postBufferLen, () => bufferSlice);

	const bufferedSlices = [...preBufferSlices, ...slices, ...postBufferSlices];
	return { ...song, slices: bufferedSlices };
}

function calculateInitBuffer({ height, width, slices }: SongLayout): number {
	let maxBuffer = 0;
	for (let i = 0; i < height - 1; i++) {
		let localBuffer = height - i - 1;
		for (const { levels } of slices) {
			if (localBuffer <= maxBuffer || levels[i]) {
				break;
			}
			localBuffer--;
		}
		maxBuffer = Math.max(maxBuffer, localBuffer);
	}
	return roundToMultiple(maxBuffer, width);
}

function roundToMultiple(value: number, multiple: number): number {
	return Math.ceil(value / multiple) * multiple;
}
