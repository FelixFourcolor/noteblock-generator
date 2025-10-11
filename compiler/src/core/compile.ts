import { assemble, type SongLayout } from "#core/assembler/@";
import { type BuildingDTO, build } from "#core/builder/@";
import { resolve, type SongResolution, type Tick } from "#core/resolver/@";
import type { FileRef, JsonData } from "#schema/@";

type SongResolutionSerialized = SongResolution & { ticks: Tick[] };

export function compile(
	src: FileRef | JsonData,
	mode: "resolve",
): Promise<SongResolutionSerialized>;

export function compile(
	src: FileRef | JsonData,
	mode: "assemble",
): Promise<SongLayout>;

export function compile(
	src: FileRef | JsonData,
	mode: "compile",
): Promise<BuildingDTO>;

export async function compile(
	src: FileRef | JsonData,
	mode?: "resolve" | "assemble" | "compile",
): Promise<SongResolutionSerialized | SongLayout | BuildingDTO>;

export async function compile(
	src: FileRef | JsonData,
	mode?: "resolve" | "assemble" | "compile",
) {
	const resolution = await resolve(src);
	if (mode === "resolve") {
		const { ticks, ...rest } = resolution;
		return { ticks: await Array.fromAsync(ticks), ...rest };
	}

	const layout = await assemble(resolution);
	if (mode === "assemble") {
		return layout;
	}

	return build(layout);
}
