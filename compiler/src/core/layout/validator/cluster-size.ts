import type { NoteEvent } from "@/core/resolver";

const MAX_SIZE = 6;

export function validateCluster(
	noteGroups: Record<string, NoteEvent[]>,
	onError: (e: [string, { voices: string[]; size: number }]) => void,
) {
	for (const [groupKey, notes] of Object.entries(noteGroups)) {
		const size = notes.length;
		if (size > MAX_SIZE) {
			const voices = Array.from(new Set(notes.map(({ voice }) => voice)));
			onError([groupKey, { voices, size }]);
		}
	}
}
